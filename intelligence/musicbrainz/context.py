"""Context from the MusicBrainz dump for Phases 4 to 6: areas, places, events, genres, ids and more.

Runs inside :func:`loader.load_neighbourhood`, in its transaction, after the main entities exist.
Because the dump can only be read front to back and a re-import is expensive, this is the one
place that decides everything the later phases need from the dump, so the slice is not re-cut for
each phase (owner direction 2026-11-06). Every table below has a named consumer.

Two parallel passes, no provider traffic:

* pass A reads small tables whole (``area``, ``place``, ``event``, ``genre`` and their types, the
  alias tables, the area/place/event/genre links) and large ones filtered by the selected
  entities (``l_artist_url``, ``l_place_recording``, ``l_artist_event``, ``isrc``, ``release_label``,
  ``medium`` and the like);
* pass B reads the ``label`` rows of labels found only through a release or a label relationship,
  and the ``url`` rows whose ids pass A named, so the 2.8 GB ``url`` table never comes back whole.

What it adds, all ``source_explicit`` from the dump:

* ``area``, ``place``, ``event`` and ``genre`` entities with their facts (``area_facts``,
  ``place_facts``, ``event_facts``). Only what the selected entities point at is loaded, plus the
  chain of areas containing it, so a place rolls up to its country (atlas, scene and studio paths).
* ``area`` / ``begin area`` edges from artists, labels and places. They are MusicBrainz's own
  claims; no nationality is derived from a name, a label or one recording location.
* Relationship rows (recording location, artist at place or event, event place, area of
  recording, containment, subgenre, genre origin, label parent, remix/cover/sample links, release
  families) returned to the loader as ``pending`` rows, so link type name, dates and attributes
  come from the same pass as every other edge. Containment is stored child -> parent.
* Release labels with catalogue numbers (``release_labels`` and a ``release label`` edge), and
  release formats (``release_facts.formats``) for the album dossier.
* ``entities.wikidata_id`` and ``discogs_id`` from the page's URL relations (keys for later
  fetches), ``entity_identifiers`` (ISRC, ISWC), aliases (``entity_aliases``, kind
  ``mb_alias``) and ``artist_facts.kind`` (person, group, orchestra ...).

Community tags and release-group first-release dates are not in this archive (they ship in
``mbdump-derived``), and tags are opinion, so they are not loaded here.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Callable

from .scan import RowFilter, scan_rows

# Link tables that only ever connect entities already loaded: table -> (type of entity0, entity1).
CONTEXT_LINK_TABLES: dict[str, tuple[str, str]] = {
    "l_place_recording": ("place", "recording"),
    "l_artist_place": ("artist", "place"),
    "l_area_recording": ("area", "recording"),
    "l_area_area": ("area", "area"),
    "l_artist_event": ("artist", "event"),
    "l_event_place": ("event", "place"),
    "l_area_event": ("area", "event"),
    "l_event_recording": ("event", "recording"),
    "l_area_genre": ("area", "genre"),
    "l_genre_genre": ("genre", "genre"),
    "l_artist_genre": ("artist", "genre"),
    "l_label_label": ("label", "label"),
    "l_recording_recording": ("recording", "recording"),
    "l_release_group_release_group": ("release_group", "release_group"),
    "l_release_release": ("release", "release"),
}
# Everything the extraction step must unpack for this module.
CONTEXT_TABLES = (
    "area", "area_type", "place", "place_type", "url", "iso_3166_1", "event", "event_type", "genre",
    "artist_type", "medium", "medium_format", "isrc", "iswc", "release_label",
    "artist_alias", "label_alias", "area_alias", "place_alias",
    "l_area_area", "l_area_event", "l_area_genre", "l_area_recording", "l_area_url", "l_artist_event",
    "l_artist_genre", "l_artist_place", "l_artist_url", "l_event_place", "l_event_recording",
    "l_genre_genre", "l_label_label", "l_label_url", "l_place_recording", "l_place_url",
    "l_recording_recording", "l_release_group_release_group", "l_release_group_url", "l_release_release",
)

ALIAS_KIND = "mb_alias"
MAX_EVENTS = 250_000  # events kept per import; the cut is by id, so it is stable, and it is reported
MAX_ANCESTOR_DEPTH = 12  # areas nest a handful of levels; a longer chain is a data error

_WIKIDATA = re.compile(r"^https?://www\.wikidata\.org/wiki/(Q[1-9][0-9]*)$")
_DISCOGS = re.compile(r"^https?://(?:www\.)?discogs\.com/(artist|label|master)/([1-9][0-9]*)(?:[-/?#].*)?$")
_DISCOGS_FOR = {"artist": "artist", "label": "label", "master": "release_group"}
_POINT = re.compile(r"^\(\s*(-?[0-9.]+)\s*,\s*(-?[0-9.]+)\s*\)$")


@dataclass
class ContextResult:
    areas: int = 0
    places: int = 0
    events: int = 0
    events_truncated: bool = False
    genres: int = 0
    late_labels: int = 0
    area_edges: int = 0
    release_labels: int = 0
    release_formats: int = 0
    wikidata_ids: int = 0
    discogs_ids: int = 0
    identifiers: int = 0
    aliases: int = 0
    artist_kinds: int = 0

    def summary(self) -> dict[str, int]:
        return dict(self.__dict__)


def _date(year, month, day) -> str | None:
    if not year:
        return None
    text = f"{int(year):04d}"
    if month:
        text += f"-{int(month):02d}"
        if day:
            text += f"-{int(day):02d}"
    return text


def parse_point(text: str | None) -> tuple[float, float] | None:
    """MusicBrainz writes a place's coordinates as ``(latitude,longitude)``."""
    match = _POINT.match((text or "").strip())
    if not match:
        return None
    lat, lon = float(match.group(1)), float(match.group(2))
    return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None


def wikidata_id(url: str | None) -> str | None:
    match = _WIKIDATA.match((url or "").strip())
    return match.group(1) if match else None


def discogs_ref(url: str | None) -> tuple[str, str] | None:
    """``(entity type, discogs id)`` for an artist, label or master page URL."""
    match = _DISCOGS.match((url or "").strip())
    return (_DISCOGS_FOR[match.group(1)], match.group(2)) if match else None


def _int(value) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _truthy(value) -> bool:
    return str(value).lower() in ("t", "true", "1")


def load_context(
    db: sqlite3.Connection,
    read,
    selected: dict[str, set[int]],
    entity_area: dict[tuple[str, int], tuple[int | None, int | None]],
    artist_types: dict[int, int],
    store_id: dict[tuple[str, int], int],
    gid_of: dict[tuple[str, int], str],
    pending: list[tuple[str, int, int, int]],
    *,
    ensure_entity: Callable[..., int],
    put_edge: Callable[..., None],
) -> ContextResult:
    """Create the context entities and facts; append their link rows to ``pending``.

    ``entity_area`` maps ``(type, internal id)`` of a selected artist or label to its
    ``(area, begin_area)`` dump ids; ``artist_types`` maps an artist's dump id to its type id.
    ``ensure_entity(type, internal, gid, name)`` returns the store id, creating the entity when
    needed; ``put_edge(from_store, to_store, relation, first_type, first_internal)`` writes one
    column-derived edge.
    """
    result = ContextResult()
    artists = frozenset(selected.get("artist", ()))
    labels = frozenset(selected.get("label", ()))
    recordings = frozenset(selected.get("recording", ()))
    releases = frozenset(selected.get("release", ()))
    groups = frozenset(selected.get("release_group", ()))
    works = frozenset(selected.get("work", ()))
    LINK = ("entity0", "entity1", "link")
    PAIR = ("entity0", "entity1")

    # ---------------------------------------------------------------- pass A
    wholes: dict[str, RowFilter] = {
        "area": RowFilter(("id", "gid", "name", "type"), optional=("type",)),
        "area_type": RowFilter(("id", "name")),
        "place": RowFilter(("id", "gid", "name", "type", "area", "coordinates", "begin_date_year",
                            "begin_date_month", "begin_date_day", "end_date_year", "end_date_month",
                            "end_date_day"),
                           optional=("type", "area", "coordinates", "begin_date_year", "begin_date_month",
                                     "begin_date_day", "end_date_year", "end_date_month", "end_date_day")),
        "place_type": RowFilter(("id", "name")),
        "iso_3166_1": RowFilter(("area", "code")),
        "event": RowFilter(("id", "gid", "name", "begin_date_year", "begin_date_month", "begin_date_day",
                            "end_date_year", "end_date_month", "end_date_day", "type", "cancelled"),
                           optional=("type", "cancelled", "begin_date_year", "begin_date_month",
                                     "begin_date_day", "end_date_year", "end_date_month", "end_date_day")),
        "event_type": RowFilter(("id", "name")),
        "genre": RowFilter(("id", "gid", "name")),
        "artist_type": RowFilter(("id", "name")),
        "medium_format": RowFilter(("id", "name")),
        "l_area_area": RowFilter(LINK), "l_area_event": RowFilter(LINK), "l_area_genre": RowFilter(LINK),
        "l_artist_genre": RowFilter(LINK), "l_event_place": RowFilter(LINK), "l_genre_genre": RowFilter(LINK),
        "l_area_url": RowFilter(PAIR), "l_place_url": RowFilter(PAIR), "l_label_url": RowFilter(PAIR),
        "area_alias": RowFilter(("area", "name")), "place_alias": RowFilter(("place", "name")),
        "label_alias": RowFilter(("label", "name")),
    }
    filtered: dict[str, RowFilter] = {}
    if recordings:
        filtered["l_place_recording"] = RowFilter(LINK, ints=(("entity1", recordings),))
        filtered["l_area_recording"] = RowFilter(LINK, ints=(("entity1", recordings),))
        filtered["l_event_recording"] = RowFilter(LINK, ints=(("entity1", recordings),))
        filtered["l_recording_recording"] = RowFilter(  # both ends selected
            LINK, ints=(("entity0", recordings), ("entity1", recordings)))
        filtered["isrc"] = RowFilter(("recording", "isrc"), ints=(("recording", recordings),))
    if artists:
        filtered["l_artist_place"] = RowFilter(LINK, ints=(("entity0", artists),))
        filtered["l_artist_event"] = RowFilter(LINK, ints=(("entity0", artists),))
        filtered["l_artist_url"] = RowFilter(PAIR, ints=(("entity0", artists),))
        filtered["artist_alias"] = RowFilter(("artist", "name"), ints=(("artist", artists),))
    if labels:  # either end: the other end may be a label outside the selection
        filtered["l_label_label"] = RowFilter(LINK, ints=(("entity0", labels), ("entity1", labels)), any_=True)
    if releases:
        filtered["release_label"] = RowFilter(("release", "label", "catalog_number"),
                                              ints=(("release", releases),), optional=("catalog_number",))
        filtered["medium"] = RowFilter(("release", "position", "format"), ints=(("release", releases),),
                                       optional=("format",))
        filtered["l_release_release"] = RowFilter(LINK, ints=(("entity0", releases), ("entity1", releases)))
    if groups:
        filtered["l_release_group_url"] = RowFilter(PAIR, ints=(("entity0", groups),))
        filtered["l_release_group_release_group"] = RowFilter(
            LINK, ints=(("entity0", groups), ("entity1", groups)))
    if works:
        filtered["iswc"] = RowFilter(("work", "iswc"), ints=(("work", works),))
    a = scan_rows(read, {**wholes, **filtered})

    # ---------------------------------------------------------------- what is wanted
    # Events: the ones the selected artists took part in, capped by id so the cut is stable.
    event_ids = sorted({int(e1) for _, e1, _ in a.get("l_artist_event", [])})
    if len(event_ids) > MAX_EVENTS:
        event_ids, result.events_truncated = event_ids[:MAX_EVENTS], True
    event_set = set(event_ids)
    event_rows = {int(r[0]): r for r in a["event"] if int(r[0]) in event_set}

    # Labels beyond the selection: those a release names, and the other end of a label relationship.
    late_labels = {int(r[1]) for r in a.get("release_label", []) if r[1] and int(r[1]) not in labels}
    label_links = [(int(x), int(y), int(z)) for x, y, z in a.get("l_label_label", [])]
    for e0, e1, _ in label_links:
        late_labels.update(x for x in (e0, e1) if x not in labels)

    places: set[int] = {int(e0) for e0, _, _ in a.get("l_place_recording", [])}
    places |= {int(e1) for _, e1, _ in a.get("l_artist_place", [])}
    event_places = [(int(e0), int(e1), int(z)) for e0, e1, z in a["l_event_place"] if int(e0) in event_set]
    places |= {p for _, p, _ in event_places}
    place_rows = {int(r[0]): r for r in a["place"] if int(r[0]) in places}
    genre_rows = {int(r[0]): r for r in a["genre"]}

    # ---------------------------------------------------------------- pass B
    b_requests: dict[str, RowFilter] = {}
    if late_labels:
        b_requests["label"] = RowFilter(("id", "gid", "name", "sort_name", "area"),
                                        ints=(("id", frozenset(late_labels)),), optional=("sort_name", "area"))
    url_ids = {int(e1) for t in ("l_artist_url", "l_label_url", "l_area_url", "l_place_url", "l_release_group_url")
               for _, e1 in a.get(t, [])}
    if url_ids:
        b_requests["url"] = RowFilter(("id", "url"), ints=(("id", frozenset(url_ids)),))
    b = scan_rows(read, b_requests) if b_requests else {}
    label_rows = {int(r[0]): r for r in b.get("label", [])}

    # ---------------------------------------------------------------- areas wanted
    wanted_areas: set[int] = {int(e0) for e0, _, _ in a.get("l_area_recording", [])}
    wanted_areas |= {int(e0) for e0, e1, _ in a["l_area_event"] if int(e1) in event_set}
    wanted_areas |= {int(e0) for e0, _, _ in a["l_area_genre"]}  # where a genre began
    for pair in entity_area.values():
        wanted_areas.update(x for x in pair if x)
    for row in label_rows.values():
        if row[4]:
            wanted_areas.add(int(row[4]))
    for row in place_rows.values():
        if row[4]:
            wanted_areas.add(int(row[4]))
    parent_of: dict[int, list[tuple[int, int]]] = {}  # child -> [(parent, link id)]
    for e0, e1, lid in a["l_area_area"]:
        parent_of.setdefault(int(e1), []).append((int(e0), int(lid)))
    frontier, depth = set(wanted_areas), 0
    contains: list[tuple[int, int, int]] = []
    while frontier and depth < MAX_ANCESTOR_DEPTH:
        depth += 1
        nxt: set[int] = set()
        for child in frontier:
            for parent, lid in parent_of.get(child, ()):
                contains.append((parent, child, lid))
                if parent not in wanted_areas:
                    wanted_areas.add(parent)
                    nxt.add(parent)
        frontier = nxt
    area_rows = {int(r[0]): r for r in a["area"] if int(r[0]) in wanted_areas}
    area_kind = {int(i): (n or "").lower() for i, n in a["area_type"]}
    place_kind = {int(i): (n or "").lower() for i, n in a["place_type"]}
    event_kind = {int(i): (n or "").lower() for i, n in a["event_type"]}
    artist_kind = {int(i): (n or "").lower() for i, n in a["artist_type"]}
    iso = {int(x): (c or "").strip().upper() for x, c in a.get("iso_3166_1", [])}

    # ---------------------------------------------------------------- entities and facts
    for label_id, (_, gid, name, sort_name, area) in sorted(label_rows.items()):
        if gid:
            ensure_entity("label", label_id, gid.lower(), name, sort_name)
            entity_area[("label", label_id)] = (_int(area), None)
            result.late_labels += 1
    for area_id, (_, gid, name, kind) in sorted(area_rows.items()):
        if not gid:
            continue
        sid = ensure_entity("area", area_id, gid.lower(), name)
        code = iso.get(area_id)
        db.execute(
            "INSERT INTO area_facts (entity_id, kind, iso_code) VALUES (?, ?, ?) "
            "ON CONFLICT (entity_id) DO UPDATE SET kind = excluded.kind, iso_code = excluded.iso_code",
            (sid, area_kind.get(int(kind)) if kind else None, code if len(code or "") == 2 else None))
        result.areas += 1
    for place_id, row in sorted(place_rows.items()):
        _, gid, name, kind, area, coordinates, by, bm, bd, ey, em, ed = row
        if not gid:
            continue
        sid = ensure_entity("place", place_id, gid.lower(), name)
        point = parse_point(coordinates)
        db.execute(
            "INSERT INTO place_facts (entity_id, kind, latitude, longitude, begin_date, end_date) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (entity_id) DO UPDATE SET kind = excluded.kind, "
            "latitude = excluded.latitude, longitude = excluded.longitude, "
            "begin_date = excluded.begin_date, end_date = excluded.end_date",
            (sid, place_kind.get(int(kind)) if kind else None, point[0] if point else None,
             point[1] if point else None, _date(by, bm, bd), _date(ey, em, ed)))
        result.places += 1
    for event_id, row in sorted(event_rows.items()):
        _, gid, name, by, bm, bd, ey, em, ed, kind, cancelled = row
        if not gid:
            continue
        sid = ensure_entity("event", event_id, gid.lower(), name)
        db.execute(
            "INSERT INTO event_facts (entity_id, kind, begin_date, end_date, cancelled) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (entity_id) DO UPDATE SET kind = excluded.kind, begin_date = excluded.begin_date, "
            "end_date = excluded.end_date, cancelled = excluded.cancelled",
            (sid, event_kind.get(int(kind)) if kind else None, _date(by, bm, bd), _date(ey, em, ed),
             int(_truthy(cancelled))))
        result.events += 1
    for genre_id, (_, gid, name) in sorted(genre_rows.items()):
        if gid:
            ensure_entity("genre", genre_id, gid.lower(), name)
            result.genres += 1

    # ---------------------------------------------------------------- edges from a column
    def area_edge(table: str, internal: int, area: int | None, relation: str) -> None:
        if area and ("area", int(area)) in store_id and (table, internal) in store_id:
            put_edge(store_id[(table, internal)], store_id[("area", int(area))], relation, table, internal)
            result.area_edges += 1

    for (table, internal), (area, begin_area) in sorted(entity_area.items()):
        area_edge(table, internal, area, "area")
        area_edge(table, internal, begin_area, "begin area")
    for place_id, row in sorted(place_rows.items()):
        area_edge("place", place_id, _int(row[4]), "area")

    # ---------------------------------------------------------------- link rows for the loader
    def known(kind: str, internal: int) -> bool:
        return (kind, internal) in store_id

    def add(table: str, rows) -> None:
        type0, type1 = CONTEXT_LINK_TABLES[table]
        pending.extend((table, int(x), int(y), int(z)) for x, y, z in rows
                       if known(type0, int(x)) and known(type1, int(y)))

    add("l_place_recording", a.get("l_place_recording", []))
    add("l_area_recording", a.get("l_area_recording", []))
    add("l_artist_place", a.get("l_artist_place", []))
    add("l_artist_event", [r for r in a.get("l_artist_event", []) if int(r[1]) in event_set])
    add("l_event_place", event_places)
    add("l_area_event", [r for r in a["l_area_event"] if int(r[1]) in event_set])
    add("l_event_recording", [r for r in a.get("l_event_recording", []) if int(r[0]) in event_set])
    add("l_area_genre", a["l_area_genre"])
    add("l_genre_genre", a["l_genre_genre"])
    add("l_artist_genre", a["l_artist_genre"])
    add("l_label_label", label_links)
    add("l_recording_recording", a.get("l_recording_recording", []))
    add("l_release_group_release_group", a.get("l_release_group_release_group", []))
    add("l_release_release", a.get("l_release_release", []))
    # Containment is stored child -> parent, so "part of" reads the right way round.
    add("l_area_area", [(child, parent, lid) for parent, child, lid in contains])

    # ---------------------------------------------------------------- release labels and formats
    by_release: dict[int, list[tuple[int | None, str | None]]] = {}
    for rel, lab, cat in a.get("release_label", []):
        cat = (cat or "").strip()
        by_release.setdefault(int(rel), []).append(
            (int(lab) if lab else None, None if cat.lower() in ("", "[none]") else cat))
    for rel, rows in sorted(by_release.items()):
        if not known("release", rel):
            continue
        sid = store_id[("release", rel)]
        db.execute("DELETE FROM release_labels WHERE release_id = ?", (sid,))
        for lab, cat in sorted(set(rows), key=lambda r: (r[0] or 0, r[1] or "")):
            label_sid = store_id.get(("label", lab)) if lab else None
            if label_sid is None and not cat:
                continue
            db.execute("INSERT OR IGNORE INTO release_labels (release_id, label_id, catalogue_number) "
                       "VALUES (?, ?, ?)", (sid, label_sid, cat))
            result.release_labels += 1
            if label_sid is not None:
                put_edge(label_sid, sid, "release label", "label", lab)
    format_name = {int(i): n or "" for i, n in a["medium_format"]}
    media: dict[int, list[tuple[int, str]]] = {}
    for rel, position, fmt in a.get("medium", []):
        media.setdefault(int(rel), []).append((_int(position) or 0, format_name.get(_int(fmt) or -1, "") or "unknown"))
    for rel, rows in sorted(media.items()):
        if not known("release", rel):
            continue
        order: list[str] = []
        counts: dict[str, int] = {}
        for _, name in sorted(rows):
            if name not in counts:
                order.append(name)
            counts[name] = counts.get(name, 0) + 1
        text = " + ".join(f"{counts[n]}×{n}" if counts[n] > 1 else n for n in order)
        db.execute("INSERT INTO release_facts (entity_id, formats) VALUES (?, ?) "
                   "ON CONFLICT (entity_id) DO UPDATE SET formats = excluded.formats",
                   (store_id[("release", rel)], text))
        result.release_formats += 1

    # ---------------------------------------------------------------- Wikidata and Discogs ids
    refs: dict[int, list[tuple[str, str, str]]] = {}  # url id -> [(scheme, type, value)]
    for url_id, url in b.get("url", []):
        found = wikidata_id(url)
        if found:
            refs.setdefault(int(url_id), []).append(("wikidata", "", found))
        discogs = discogs_ref(url)
        if discogs:
            refs.setdefault(int(url_id), []).append(("discogs", discogs[0], discogs[1]))
    for table, kind in (("l_artist_url", "artist"), ("l_label_url", "label"), ("l_area_url", "area"),
                        ("l_place_url", "place"), ("l_release_group_url", "release_group")):
        best_wikidata: dict[int, str] = {}
        best_discogs: dict[int, str] = {}
        for e0, e1 in a.get(table, []):
            internal = int(e0)
            if not known(kind, internal):
                continue
            for scheme, typ, value in refs.get(int(e1), ()):
                if scheme == "wikidata":
                    current = best_wikidata.get(internal)
                    best_wikidata[internal] = value if current is None or int(value[1:]) < int(current[1:]) else current
                elif typ == kind:
                    current = best_discogs.get(internal)
                    best_discogs[internal] = value if current is None or int(value) < int(current) else current
        for internal, qid in sorted(best_wikidata.items()):
            result.wikidata_ids += db.execute(
                "UPDATE entities SET wikidata_id = ? WHERE id = ? AND wikidata_id IS NOT ?",
                (qid, store_id[(kind, internal)], qid)).rowcount
        for internal, value in sorted(best_discogs.items()):  # an id someone already set is kept
            result.discogs_ids += db.execute(
                "UPDATE entities SET discogs_id = ? WHERE id = ? AND discogs_id IS NULL",
                (value, store_id[(kind, internal)])).rowcount

    # ---------------------------------------------------------------- identifiers, aliases, kinds
    codes: dict[int, set[tuple[str, str]]] = {}
    for rec, code in a.get("isrc", []):
        if known("recording", int(rec)):
            codes.setdefault(store_id[("recording", int(rec))], set()).add(("isrc", (code or "").strip().upper()))
    for work, code in a.get("iswc", []):
        if known("work", int(work)):
            codes.setdefault(store_id[("work", int(work))], set()).add(("iswc", (code or "").strip().upper()))
    for sid, pairs in sorted(codes.items()):
        db.execute("DELETE FROM entity_identifiers WHERE entity_id = ?", (sid,))
        for scheme, value in sorted(pairs):
            if value:
                db.execute("INSERT OR IGNORE INTO entity_identifiers (entity_id, scheme, value) VALUES (?, ?, ?)",
                           (sid, scheme, value))
                result.identifiers += 1

    alias_rows: dict[int, set[str]] = {}
    for table, kind in (("artist_alias", "artist"), ("label_alias", "label"), ("area_alias", "area"),
                        ("place_alias", "place")):
        for owner, name in a.get(table, []):
            if name and known(kind, int(owner)):
                alias_rows.setdefault(store_id[(kind, int(owner))], set()).add(name)
    for sid, names in sorted(alias_rows.items()):
        db.execute("DELETE FROM entity_aliases WHERE entity_id = ? AND kind = ?", (sid, ALIAS_KIND))
        for name in sorted(names):
            result.aliases += db.execute(
                "INSERT OR IGNORE INTO entity_aliases (entity_id, alias, kind) "
                "SELECT ?, ?, ? WHERE ? != (SELECT canonical_name FROM entities WHERE id = ?)",
                (sid, name, ALIAS_KIND, name, sid)).rowcount

    for internal, type_id in sorted(artist_types.items()):
        kind_name = artist_kind.get(type_id)
        if kind_name and known("artist", internal):
            db.execute("INSERT INTO artist_facts (entity_id, kind) VALUES (?, ?) "
                       "ON CONFLICT (entity_id) DO UPDATE SET kind = excluded.kind",
                       (store_id[("artist", internal)], kind_name))
            result.artist_kinds += 1
    return result
