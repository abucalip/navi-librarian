"""Load the selected MusicBrainz neighbourhood into the Server V2 store.

Input is the id sets chosen by :mod:`neighbourhood` and the same injected table reader.
Three fixed passes over the archive, never a lookup per entity:

* pass 1 reads the entity tables (rows whose id was selected become ``entities``) plus the
  small ``link_type`` and ``link_attribute_type`` tables;
* pass 2 reads the nine relationship tables and keeps links whose two ends are both selected;
* pass 3 reads ``link`` (dates, type) and ``link_attribute`` for just those links.

Provenance: every edge is ``source_explicit`` / ``exact_mbid`` from source
``musicbrainz_dump``, points at the MusicBrainz page of its first entity, and references one
observation recording the dump timestamp and schema sequence. Existing entities (the owned
ones) are matched by MBID and never renamed or flipped to unowned. Nothing is inferred: the
relation is MusicBrainz's own link type name and the role is its attributes, joined.

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
from .neighbourhood import LINK_TABLES, Neighbourhood, TableReader
from .scan import RowFilter, scan_rows

SOURCE = "musicbrainz_dump"
ENTITY_TABLES = ("artist", "label", "recording", "release", "release_group", "work")


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


def load_neighbourhood(
    db: sqlite3.Connection,
    read: TableReader,
    neighbourhood: Neighbourhood,
    *,
    dump_timestamp: str | None,
    schema_sequence: int,
    clock: Callable[[], float] = time.time,
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
    entity_requests = {
        t: RowFilter(("id", "gid", "name", "sort_name"), ints=(("id", frozenset(selected[t])),), optional=("sort_name",))
        for t in ENTITY_TABLES if selected.get(t)
    }
    db.execute("BEGIN")
    try:
        scanned = scan_rows(read, {
            **entity_requests,
            "link_type": RowFilter(("id", "name")), "link_attribute_type": RowFilter(("id", "name"))})
        for table in ("link_type", "link_attribute_type"):
            target = link_type_name if table == "link_type" else attribute_name
            for row_id, name in scanned.pop(table):
                target[int(row_id)] = name or ""
        for table, rows in scanned.items():
            for internal, raw_gid, name, sort_name in rows:
                if not raw_gid:
                    continue
                internal = int(internal)
                gid = raw_gid.lower()
                found = db.execute(
                    "SELECT id FROM entities WHERE type = ? AND mbid = ?", (table, gid)
                ).fetchone()
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
            type0, type1 = LINK_TABLES[table]
            if (type0, id0) not in store_id or (type1, id1) not in store_id:
                result.links_dropped_no_entity += 1
                continue
            role = ", ".join(sorted(set(link_attrs.get(lid, [])))) or None
            before = db.total_changes
            db.execute(
                "INSERT OR IGNORE INTO edges (from_id, to_id, relation, role, evidence_class, match_quality, "
                "source, source_url, observation_id, valid_from, valid_to, generation) "
                "VALUES (?, ?, ?, ?, 'source_explicit', 'exact_mbid', ?, ?, ?, ?, ?, ?)",
                (store_id[(type0, id0)], store_id[(type1, id1)], relation, role, SOURCE,
                 f"https://musicbrainz.org/{type0.replace('_', '-')}/{gid_of[(type0, id0)]}",
                 observation_id, info[1], info[2], generation),
            )
            if db.total_changes > before:
                result.edges_created += 1
            else:
                result.edges_existing += 1
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    result.seconds = clock() - started
    return result
