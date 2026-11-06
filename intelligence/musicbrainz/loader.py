"""Load the selected MusicBrainz neighbourhood into the Server V2 store.

Input is the id sets chosen by :mod:`neighbourhood` and the same injected table reader.
A fixed number of passes over the archive (the context step adds two scans), never a lookup per entity:

* pass 1 reads the entity tables (rows whose id was selected become ``entities``) plus the
  small ``link_type`` and ``link_attribute_type`` tables, and the facts kept beside an entity: an
  artist's life span, and a release's date, country and status (earliest dated row wins);
* pass 2 reads the nine relationship tables and keeps links whose two ends are both selected;
* between passes 2 and 3, :mod:`context` runs its own two scans (areas, places, events, genres,
  release labels and formats, Wikidata and Discogs ids, ISRC/ISWC, aliases, artist kind) and adds
  its link rows to the ones pass 3 types and dates;
* pass 3 reads ``link`` (dates, type) and ``link_attribute`` for just those links.

Provenance: every edge is ``source_explicit`` / ``exact_mbid`` from source
``musicbrainz_dump``, points at the MusicBrainz page of its first entity, and references one
observation recording the dump timestamp and schema sequence. Existing entities (the owned
ones) are matched by MBID and never renamed or flipped to unowned. Nothing is inferred: the
relation is MusicBrainz's own link type name and the role is its attributes, joined.

Replacement: the ids of the dump edges this load created or matched are collected, so any
``musicbrainz_dump`` edge this load did not see has left the dump and is removed in the same
transaction, together with entities that only it connected (not owned, no other id, no edge, no
insight). A load that keeps fewer than ``min_retained`` of the previous dump edges is refused with
:class:`SliceValidationError` and rolls back, so the previous slice stays as the last known good.

No network and no ``navidrome_server.py`` involvement; re-running is safe (edges are unique
per endpoints, relation, role, source and generation).
"""
from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from typing import Callable

from ..store import repositories as repo
from ..store.generations import current_generation
from . import context
from .neighbourhood import LINK_TABLES, Neighbourhood, TableReader
from .scan import RowFilter, scan_rows

SOURCE = "musicbrainz_dump"
ENTITY_TABLES = ("artist", "label", "recording", "release", "release_group", "work")
# Tables read only for the facts above; the extraction step must unpack them too.
FACT_TABLES = ("release_country", "release_unknown_country", "release_status", "iso_3166_1", *context.CONTEXT_TABLES)
ARTIST_FACT_COLUMNS = ("begin_date_year", "begin_date_month", "begin_date_day",
                       "end_date_year", "end_date_month", "end_date_day", "ended", "area", "begin_area", "type")
ALL_LINK_TABLES = {**LINK_TABLES, **context.CONTEXT_LINK_TABLES}
RELEASE_STATUSES = frozenset({"official", "promotion", "bootleg", "pseudo-release", "withdrawn", "expunged", "cancelled"})


DEFAULT_MIN_RETAINED = 0.5


class SliceValidationError(RuntimeError):
    """The new dump keeps too little of the previous slice to be trusted; nothing was changed."""


@dataclass
class LoadResult:
    passes: int = 0
    entities_created: int = 0
    entities_existing: int = 0
    edges_created: int = 0
    edges_existing: int = 0
    links_seen: int = 0
    links_dropped_no_type: int = 0
    links_dropped_no_entity: int = 0
    life_spans: int = 0
    release_facts: int = 0
    context: dict[str, int] = field(default_factory=dict)
    edges_removed: int = 0
    entities_removed: int = 0
    seconds: float = 0.0
    by_type: dict[str, int] = field(default_factory=dict)

    def summary(self) -> dict[str, object]:
        return {k: (dict(v) if isinstance(v, dict) else v) for k, v in self.__dict__.items()}


def _date(year, month, day) -> str | None:
    if not year:
        return None
    text = f"{int(year):04d}"
    if month:
        text += f"-{int(month):02d}"
        if day:
            text += f"-{int(day):02d}"
    return text


def _int(value) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _truthy(value) -> bool:
    return str(value).lower() in ("t", "true", "1")


def _country_code(code) -> str | None:
    code = (code or "").strip().upper()
    return code if len(code) == 2 and code.isalpha() else None


def _earliest(candidates: list[tuple[str, str | None]]) -> tuple[str | None, str | None]:
    """``(date, country)`` of the earliest dated row; a dated row beats an undated one."""
    dated = sorted((c for c in candidates if c[0]), key=lambda c: (c[0], c[1] or "~"))
    if dated:
        return dated[0]
    return (None, candidates[0][1]) if candidates else (None, None)


def load_neighbourhood(
    db: sqlite3.Connection,
    read: TableReader,
    neighbourhood: Neighbourhood,
    *,
    dump_timestamp: str | None,
    schema_sequence: int,
    clock: Callable[[], float] = time.time,
    min_retained: float = DEFAULT_MIN_RETAINED,
) -> LoadResult:
    started = clock()
    result = LoadResult()
    selected = neighbourhood.selected
    generation = current_generation(db)
    observation_id, _ = repo.add_observation(
        db, SOURCE,
        {"dump_timestamp": dump_timestamp, "schema_sequence": schema_sequence},
        fetched_at=started, entity_hint="mbdump",
    )

    # --- pass 1: entities and the two small lookup tables
    store_id: dict[tuple[str, int], int] = {}
    gid_of: dict[tuple[str, int], str] = {}
    link_type_name: dict[int, str] = {}
    attribute_name: dict[int, str] = {}
    extra = {"artist": ARTIST_FACT_COLUMNS, "label": ("area",), "release": ("status",)}
    entity_requests = {
        t: RowFilter(("id", "gid", "name", "sort_name", *extra.get(t, ())), ints=(("id", frozenset(selected[t])),),
                     optional=("sort_name", *extra.get(t, ())))
        for t in ENTITY_TABLES if selected.get(t)
    }
    fact_requests: dict[str, RowFilter] = {}
    if selected.get("release"):
        releases = frozenset(selected["release"])
        fact_requests = {
            "release_country": RowFilter(("release", "country", "date_year", "date_month", "date_day"),
                                         ints=(("release", releases),), optional=("country",)),
            "release_unknown_country": RowFilter(("release", "date_year", "date_month", "date_day"),
                                                 ints=(("release", releases),)),
            "release_status": RowFilter(("id", "name")),
            "iso_3166_1": RowFilter(("area", "code")),
        }
    def ensure_entity(table: str, internal: int, gid: str, name: str | None, sort_name: str | None = None) -> int:
        found = db.execute("SELECT id FROM entities WHERE type = ? AND mbid = ?", (table, gid)).fetchone()
        if found:
            store_id[(table, internal)] = found["id"]
            result.entities_existing += 1
        else:
            cur = db.execute(
                "INSERT INTO entities (type, mbid, canonical_name, sort_name, owned, created_generation) "
                "VALUES (?, ?, ?, ?, 0, ?)",
                (table, gid, name or gid, sort_name, generation),
            )
            store_id[(table, internal)] = cur.lastrowid
            result.entities_created += 1
            result.by_type[table] = result.by_type.get(table, 0) + 1
        gid_of[(table, internal)] = gid
        return store_id[(table, internal)]

    seen_edges: set[int] = set()
    entity_area: dict[tuple[str, int], tuple[int | None, int | None]] = {}
    artist_types: dict[int, int] = {}

    def put_edge(from_store: int, to_store: int, relation: str, first_type: str, first_internal: int,
                 role: str | None = None, valid_from: str | None = None, valid_to: str | None = None) -> None:
        cur = db.execute(
            "INSERT OR IGNORE INTO edges (from_id, to_id, relation, role, evidence_class, match_quality, "
            "source, source_url, observation_id, valid_from, valid_to, generation) "
            "VALUES (?, ?, ?, ?, 'source_explicit', 'exact_mbid', ?, ?, ?, ?, ?, ?)",
            (from_store, to_store, relation, role, SOURCE,
             f"https://musicbrainz.org/{first_type.replace('_', '-')}/{gid_of[(first_type, first_internal)]}",
             observation_id, valid_from, valid_to, generation),
        )
        if cur.rowcount:
            result.edges_created += 1
            seen_edges.add(cur.lastrowid)
        else:
            result.edges_existing += 1
            seen_edges.add(db.execute(
                "SELECT id FROM edges WHERE from_id = ? AND to_id = ? AND relation = ? "
                "AND COALESCE(role, '') = ? AND source = ? AND generation = ?",
                (from_store, to_store, relation, role or "", SOURCE, generation)).fetchone()[0])

    db.execute("BEGIN")
    try:
        previous_edges = db.execute("SELECT COUNT(*) FROM edges WHERE source = ?", (SOURCE,)).fetchone()[0]
        scanned = scan_rows(read, {
            **entity_requests,
            **fact_requests,
            "link_type": RowFilter(("id", "name")), "link_attribute_type": RowFilter(("id", "name"))})
        status_name = {int(i): (n or "").lower() for i, n in scanned.pop("release_status", [])}
        iso = {int(a): _country_code(c) for a, c in scanned.pop("iso_3166_1", [])}
        release_rows: dict[int, list[tuple[str, str | None]]] = {}
        for rid, country, y, m, d in scanned.pop("release_country", []):
            release_rows.setdefault(int(rid), []).append((_date(y, m, d), iso.get(int(country)) if country else None))
        for rid, y, m, d in scanned.pop("release_unknown_country", []):
            release_rows.setdefault(int(rid), []).append((_date(y, m, d), None))
        for table in ("link_type", "link_attribute_type"):
            target = link_type_name if table == "link_type" else attribute_name
            for row_id, name in scanned.pop(table):
                target[int(row_id)] = name or ""
        for table, rows in scanned.items():
            for internal, raw_gid, name, sort_name, *facts in rows:
                if not raw_gid:
                    continue
                internal = int(internal)
                gid = raw_gid.lower()
                ensure_entity(table, internal, gid, name, sort_name)
                gid_of[(table, internal)] = gid
                if table == "artist" and facts:
                    entity_area[(table, internal)] = (_int(facts[7]), _int(facts[8]))
                    if _int(facts[9]) is not None:
                        artist_types[internal] = _int(facts[9])
                elif table == "label" and facts:
                    entity_area[(table, internal)] = (_int(facts[0]), None)
                begin = end = None
                if table == "artist" and facts:
                    begin, end = _date(*facts[0:3]), _date(*facts[3:6])
                if table == "artist" and facts and (begin or end or _truthy(facts[6])):
                    db.execute(
                        "INSERT INTO artist_life_span (entity_id, begin_date, end_date, ended) VALUES (?, ?, ?, ?) "
                        "ON CONFLICT (entity_id) DO UPDATE SET begin_date = excluded.begin_date, "
                        "end_date = excluded.end_date, ended = excluded.ended",
                        (store_id[(table, internal)], begin, end, int(_truthy(facts[6]))))
                    result.life_spans += 1
                elif table == "release":
                    date, country = _earliest(release_rows.get(internal, []))
                    status = status_name.get(int(facts[0])) if facts and facts[0] else None
                    status = status if status in RELEASE_STATUSES else None
                    if date or country or status:
                        db.execute(
                            "INSERT INTO release_facts (entity_id, date, country, status) VALUES (?, ?, ?, ?) "
                            "ON CONFLICT (entity_id) DO UPDATE SET date = excluded.date, "
                            "country = excluded.country, status = excluded.status",
                            (store_id[(table, internal)], date, country, status))
                        result.release_facts += 1
        result.passes += 1

        # --- pass 2: relationships with both ends selected
        pending: list[tuple[str, int, int, int]] = []  # table, entity0, entity1, link id
        link_requests = {}
        for table, (type0, type1) in LINK_TABLES.items():
            have0, have1 = selected.get(type0), selected.get(type1)
            if have0 and have1:
                link_requests[table] = RowFilter(
                    ("entity0", "entity1", "link"),
                    ints=(("entity0", frozenset(have0)), ("entity1", frozenset(have1))))
        for table, rows in scan_rows(read, link_requests).items():
            pending.extend((table, int(e0), int(e1), int(lid)) for e0, e1, lid in rows)
        result.passes += 1
        result.passes += 1
        result.context = context.load_context(
            db, read, selected, entity_area, artist_types, store_id, gid_of, pending,
            ensure_entity=ensure_entity, put_edge=put_edge).summary()
        result.links_seen = len(pending)

        # --- pass 3: dates, type and attributes of just those links
        link_ids = frozenset(p[3] for p in pending)
        link_info: dict[int, tuple[int, str | None, str | None]] = {}
        link_attrs: dict[int, list[str]] = {}
        if link_ids:
            found = scan_rows(read, {
                "link": RowFilter(("id", "link_type", "begin_date_year", "begin_date_month", "begin_date_day",
                                   "end_date_year", "end_date_month", "end_date_day"), ints=(("id", link_ids),)),
                "link_attribute": RowFilter(("link", "attribute_type"), ints=(("link", link_ids),)),
            })
            for lid, link_type, by, bm, bd, ey, em, ed in found["link"]:
                link_info[int(lid)] = (int(link_type), _date(by, bm, bd), _date(ey, em, ed))
            for lid, attribute_type in found["link_attribute"]:
                name = attribute_name.get(int(attribute_type))
                if name:
                    link_attrs.setdefault(int(lid), []).append(name)
            result.passes += 1

        for table, id0, id1, lid in pending:
            info = link_info.get(lid)
            relation = link_type_name.get(info[0]) if info else None
            if not relation:
                result.links_dropped_no_type += 1
                continue
            type0, type1 = ALL_LINK_TABLES[table]
            if (type0, id0) not in store_id or (type1, id1) not in store_id:
                result.links_dropped_no_entity += 1
                continue
            role = ", ".join(sorted(set(link_attrs.get(lid, [])))) or None
            put_edge(store_id[(type0, id0)], store_id[(type1, id1)], relation, type0, id0, role, info[1], info[2])
        kept = result.edges_created + result.edges_existing
        if previous_edges and kept < previous_edges * min_retained:
            raise SliceValidationError(
                f"new dump keeps {kept} of {previous_edges} previous edges (minimum share {min_retained})")
        _remove_stale(db, seen_edges, result)
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    result.seconds = clock() - started
    return result


def _remove_stale(db: sqlite3.Connection, seen_edges: set[int], result: LoadResult) -> None:
    """Drop dump edges the new load did not see, then the entities only those edges connected."""
    stale = [r for r in db.execute("SELECT id, from_id, to_id FROM edges WHERE source = ?", (SOURCE,))
             if r["id"] not in seen_edges]
    if not stale:
        return
    candidates = {r["from_id"] for r in stale} | {r["to_id"] for r in stale}
    db.executemany("DELETE FROM edges WHERE id = ?", [(r["id"],) for r in stale])
    result.edges_removed = len(stale)
    for entity_id in sorted(candidates):
        removed = db.execute(
            "DELETE FROM entities WHERE id = ? AND owned = 0 AND navidrome_id IS NULL AND discogs_id IS NULL "
            "AND wikidata_id IS NULL "
            "AND NOT EXISTS (SELECT 1 FROM edges WHERE from_id = entities.id OR to_id = entities.id) "
            "AND NOT EXISTS (SELECT 1 FROM insights WHERE subject_id = entities.id)", (entity_id,)).rowcount
        result.entities_removed += removed
