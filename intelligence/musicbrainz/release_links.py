"""Link the recordings the owner's artists played on to the releases that carry them, and to each release's leader.

The Phase 4 slice has recording credits but, for recordings outside the library, no release: the
Navidrome ingest is the only source of ``appears_on`` and ``credited_to`` edges, and it only knows
owned albums. That is why the ``sideman_to_leader`` path reached 17% of owned artists (3% usable).
This step reads the missing links from the export (the ``track`` and ``artist_credit_name`` tables,
filtered straight out of the archive) and stores them under their own relations and source:

* ``track_on``        recording -> release     (MusicBrainz track listing)
* ``release_artist``  release -> artist        (MusicBrainz release artist credit, one edge per credited artist)

They are deliberately not ``appears_on`` / ``credited_to``. Those two mean "in the owner's library"
and feed ownership, editions, taste and the knowledge pages; reusing them would make every
non-owned album look owned. Source is ``musicbrainz_dump_releases`` so the main slice load, which
replaces ``musicbrainz_dump`` edges, never removes these, and this step replaces only its own.

Scope, measured on the owner's real store (2026-11-07, docs/ServerV2.md Phase 7):

* **Credited recordings:** recordings an owned artist has a performer or producer credit on
  (``CREDIT_ROLES``). Writing, engineering, mixing and the like are not sideman work.
* **One release per release group:** for each recording and release group, the earliest dated
  official release (lowest id breaks ties). Other editions add nothing to a leader path and
  tripled the size. A release group with no official release is left out.
* **No compilations:** a release credited only to "Various Artists" can never be a stop and is
  not stored. A release credited to Various Artists and someone else keeps the other artists.

Everything stored is ``source_explicit`` / ``exact_mbid``. Nothing is inferred. Existing entities
(the owned ones) are matched by MBID and never renamed or flipped to unowned. A re-run replaces
this step's own edges in one transaction; a run that keeps fewer than ``min_retained`` of the
previous ones is refused and rolls back. No network and no ``navidrome_server.py`` involvement.
"""
from __future__ import annotations

import collections
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Callable

from ..store import repositories as repo
from ..store.generations import current_generation
from . import archive_filter
from .loader import SliceValidationError, _country_code, _date, _earliest
from .neighbourhood import TableReader
from .scan import RowFilter, scan_rows

SOURCE = "musicbrainz_dump_releases"
REL_TRACK_ON = "track_on"
REL_RELEASE_ARTIST = "release_artist"
CREDIT_ROLES = ("instrument", "vocal", "main performer", "performer", "performing orchestra", "producer")
VARIOUS_ARTISTS = "89ad4ac3-39f7-470e-963a-56509c546377"
DEFAULT_MIN_RETAINED = 0.5
# The two big tables are read from the archive, not the extracted folder.
ARCHIVE_TABLES = ("track", "artist_credit_name")
# Extracted tables this step reads (the main import already unpacks all of them).
READ_TABLES = ("recording", "medium", "release", "release_status", "artist", "release_country",
               "release_unknown_country", "iso_3166_1")

# (table, key column index, ids to keep, columns to return) -> rows of integers
ArchiveFilter = Callable[[str, int, frozenset, tuple], list]

_GRADE = "evidence_class != 'inferred' AND match_quality NOT IN ('fuzzy_unconfirmed', 'unresolved')"


@dataclass
class LinkPlan:
    """What would be stored; nothing here has touched the store."""
    links: list[tuple[str, str]] = field(default_factory=list)                   # (recording gid, release gid)
    releases: dict[str, tuple] = field(default_factory=dict)                     # gid -> (name, date, country, status)
    leaders: dict[str, list[str]] = field(default_factory=dict)                  # release gid -> artist gids
    artists: dict[str, tuple] = field(default_factory=dict)                      # gid -> (name, sort_name)
    stats: dict[str, int] = field(default_factory=dict)
    credited: dict[str, int] = field(default_factory=dict)                       # recording MBID -> store id


@dataclass
class LinkResult:
    plan: dict[str, int] = field(default_factory=dict)
    entities_created: dict[str, int] = field(default_factory=dict)
    entities_existing: int = 0
    edges_created: int = 0
    edges_existing: int = 0
    edges_removed: int = 0
    entities_removed: int = 0
    seconds: float = 0.0

    def summary(self) -> dict[str, object]:
        return {k: (dict(v) if isinstance(v, dict) else v) for k, v in self.__dict__.items()}


def credited_recordings(db: sqlite3.Connection) -> dict[str, int]:
    """``{recording MBID: store id}`` of recordings an owned artist has a performer or producer credit on."""
    generation = current_generation(db)
    marks = ", ".join("?" * len(CREDIT_ROLES))
    ids: set[int] = set()
    for artist in [r[0] for r in db.execute("SELECT id FROM entities WHERE type = 'artist' AND owned = 1")]:
        ids.update(r[0] for r in db.execute(
            f"SELECT to_id FROM edges WHERE from_id = ? AND relation IN ({marks}) AND generation = ? AND {_GRADE}",
            (artist, *CREDIT_ROLES, generation)))
    found: dict[str, int] = {}
    ordered = sorted(ids)
    for start in range(0, len(ordered), 500):  # by primary key: the planner scans every recording otherwise
        chunk = ordered[start:start + 500]
        for row in db.execute(f"SELECT id, type, mbid FROM entities WHERE id IN ({', '.join('?' * len(chunk))})", chunk):
            if row["type"] == "recording" and row["mbid"]:
                found[row["mbid"].lower()] = row["id"]
    return found


def plan_links(
    db: sqlite3.Connection,
    read: TableReader,
    stream: ArchiveFilter,
    *,
    log: Callable[[str], None] | None = None,
) -> LinkPlan:
    """Work out the links to store. Reads the store and the dump; writes nothing."""
    say = log or (lambda _msg: None)
    plan = LinkPlan()
    credited = plan.credited = credited_recordings(db)
    plan.stats["credited_recordings"] = len(credited)
    if not credited:
        return plan

    # recordings -> dump ids -> tracks -> media -> releases
    recording_ids = {int(i): g.lower() for i, g in scan_rows(read, {"recording": RowFilter(
        ("id", "gid"), strs=(("gid", frozenset(credited)),))})["recording"]}
    plan.stats["recordings_in_dump"] = len(recording_ids)
    tracks = stream("track", archive_filter.TRACK_RECORDING, frozenset(recording_ids),
                    (archive_filter.TRACK_RECORDING, archive_filter.TRACK_MEDIUM))
    say(f"tracks of credited recordings: {len(tracks)}")
    media = frozenset(m for _, m in tracks)
    medium_release = {int(i): int(r) for i, r in scan_rows(read, {"medium": RowFilter(
        ("id", "release"), ints=(("id", media),))})["medium"]} if media else {}
    recording_releases: dict[int, set[int]] = collections.defaultdict(set)
    for recording, medium in tracks:
        if medium in medium_release:
            recording_releases[recording].add(medium_release[medium])
    candidates = frozenset(r for rels in recording_releases.values() for r in rels)
    plan.stats["candidate_releases"] = len(candidates)
    if not candidates:
        return plan

    status_name = {int(i): (n or "").lower() for i, n in scan_rows(read, {"release_status": RowFilter(
        ("id", "name"))})["release_status"]}
    release_rows = {int(i): (g.lower(), n, int(ac), int(rg), status_name.get(int(st)) if st else None)
                    for i, g, n, ac, rg, st in scan_rows(read, {"release": RowFilter(
                        ("id", "gid", "name", "artist_credit", "release_group", "status"),
                        ints=(("id", candidates),), optional=("status",))})["release"]}
    official = {i for i, row in release_rows.items() if row[4] == "official"}
    plan.stats["official_candidates"] = len(official)

    # leaders of every official candidate (the credit table is read once)
    credits = frozenset(release_rows[i][2] for i in official)
    credit_artists: dict[int, list[int]] = collections.defaultdict(list)
    for credit, artist in stream("artist_credit_name", archive_filter.CREDIT_NAME_CREDIT, credits,
                                 (archive_filter.CREDIT_NAME_CREDIT, archive_filter.CREDIT_NAME_ARTIST)):
        credit_artists[credit].append(artist)
    artist_ids = frozenset(a for lst in credit_artists.values() for a in lst)
    artist_rows = {int(i): (g.lower(), n, s) for i, g, n, s in scan_rows(read, {"artist": RowFilter(
        ("id", "gid", "name", "sort_name"), ints=(("id", artist_ids),), optional=("sort_name",))})["artist"]} \
        if artist_ids else {}
    leaders = {i: [artist_rows[a][0] for a in credit_artists.get(release_rows[i][2], []) if a in artist_rows
                   and artist_rows[a][0] != VARIOUS_ARTISTS] for i in official}
    usable = {i for i, lst in leaders.items() if lst}  # compilations credited only to Various Artists drop out
    plan.stats["compilation_only_releases_skipped"] = len(official) - len(usable)

    # earliest stated date and country of the releases still in play
    iso = {int(a): _country_code(c) for a, c in scan_rows(read, {"iso_3166_1": RowFilter(("area", "code"))})["iso_3166_1"]}
    dated: dict[int, list[tuple[str | None, str | None]]] = collections.defaultdict(list)
    if usable:
        wanted = frozenset(usable)
        found = scan_rows(read, {
            "release_country": RowFilter(("release", "country", "date_year", "date_month", "date_day"),
                                         ints=(("release", wanted),), optional=("country",)),
            "release_unknown_country": RowFilter(("release", "date_year", "date_month", "date_day"),
                                                 ints=(("release", wanted),))})
        for rid, country, y, m, d in found["release_country"]:
            dated[int(rid)].append((_date(y, m, d), iso.get(int(country)) if country else None))
        for rid, y, m, d in found["release_unknown_country"]:
            dated[int(rid)].append((_date(y, m, d), None))
    facts = {i: _earliest(dated.get(i, [])) for i in usable}

    # one release per recording and release group: earliest dated, then lowest id
    chosen: set[tuple[int, int]] = set()
    groups_without_official = 0
    for recording, rels in recording_releases.items():
        by_group: dict[int, list[int]] = collections.defaultdict(list)
        all_groups = set()
        for rel in rels:
            if rel in release_rows:
                all_groups.add(release_rows[rel][3])
            if rel in usable:
                by_group[release_rows[rel][3]].append(rel)
        groups_without_official += len(all_groups - by_group.keys())
        for group, lst in by_group.items():
            best = min(lst, key=lambda r: (facts[r][0] or "9999", r))
            chosen.add((recording, best))
    plan.stats["recording_groups_left_out"] = groups_without_official

    used = sorted({rel for _, rel in chosen})
    for rel in used:
        gid, name, _, _, status = release_rows[rel]
        date, country = facts[rel]
        plan.releases[gid] = (name, date, country, status)
        plan.leaders[gid] = sorted(set(leaders[rel]))
    plan.links = sorted((recording_ids[rec], release_rows[rel][0]) for rec, rel in chosen)
    by_gid = {row[0]: row[1:] for row in artist_rows.values()}
    for gids in plan.leaders.values():
        for gid in gids:
            plan.artists.setdefault(gid, by_gid.get(gid, (gid, None)))
    plan.stats.update(track_on_links=len(plan.links), releases=len(plan.releases), leaders=len(plan.artists),
                      release_artist_links=sum(len(v) for v in plan.leaders.values()))
    return plan


def _find_or_create(db: sqlite3.Connection, entity_type: str, gids: dict[str, tuple], generation: int,
                    result: LinkResult) -> dict[str, int]:
    """Store ids for ``{gid: (name, sort_name)}``, creating the missing entities (never touching existing ones)."""
    ids: dict[str, int] = {}
    wanted = sorted(gids)
    for start in range(0, len(wanted), 500):
        chunk = wanted[start:start + 500]
        for row in db.execute(
                f"SELECT id, mbid FROM entities WHERE type = ? AND mbid IN ({', '.join('?' * len(chunk))})",
                (entity_type, *chunk)):
            ids[row["mbid"].lower()] = row["id"]
    result.entities_existing += len(ids)
    for gid in wanted:
        if gid in ids:
            continue
        name, sort_name = gids[gid][0], (gids[gid][1] if len(gids[gid]) > 1 else None)
        cur = db.execute(
            "INSERT INTO entities (type, mbid, canonical_name, sort_name, owned, created_generation) "
            "VALUES (?, ?, ?, ?, 0, ?)", (entity_type, gid, name or gid, sort_name, generation))
        ids[gid] = cur.lastrowid
        result.entities_created[entity_type] = result.entities_created.get(entity_type, 0) + 1
    return ids


def apply_links(
    db: sqlite3.Connection,
    plan: LinkPlan,
    *,
    dump_timestamp: str | None,
    schema_sequence: int,
    clock: Callable[[], float] = time.time,
    min_retained: float = DEFAULT_MIN_RETAINED,
) -> LinkResult:
    """Store the plan in one transaction, replacing this step's own edges from an earlier run."""
    started = clock()
    result = LinkResult(plan=dict(plan.stats))
    generation = current_generation(db)
    observation_id, _ = repo.add_observation(
        db, SOURCE, {"dump_timestamp": dump_timestamp, "schema_sequence": schema_sequence},
        fetched_at=started, entity_hint="mbdump-releases")
    db.execute("BEGIN")
    try:
        previous = db.execute("SELECT COUNT(*) FROM edges WHERE source = ?", (SOURCE,)).fetchone()[0]
        release_ids = _find_or_create(db, "release", {g: (v[0], None) for g, v in plan.releases.items()}, generation, result)
        artist_ids = _find_or_create(db, "artist", plan.artists, generation, result)
        for gid, (name, date, country, status) in plan.releases.items():
            if date or country or status:  # an existing row (an owned release) keeps what it has
                db.execute("INSERT INTO release_facts (entity_id, date, country, status) VALUES (?, ?, ?, ?) "
                           "ON CONFLICT (entity_id) DO NOTHING", (release_ids[gid], date, country, status))
        wanted: dict[tuple[int, int, str], str] = {}
        for recording, release in plan.links:
            wanted[(plan.credited[recording], release_ids[release], REL_TRACK_ON)] = f"https://musicbrainz.org/release/{release}"
        for release, artists in plan.leaders.items():
            for artist in artists:
                wanted[(release_ids[release], artist_ids[artist], REL_RELEASE_ARTIST)] = \
                    f"https://musicbrainz.org/release/{release}"
        existing = {(r["from_id"], r["to_id"], r["relation"]): r["id"] for r in db.execute(
            "SELECT id, from_id, to_id, relation FROM edges WHERE source = ? AND generation = ?", (SOURCE, generation))}
        new = [(f, t, rel, url) for (f, t, rel), url in wanted.items() if (f, t, rel) not in existing]
        db.executemany(
            "INSERT OR IGNORE INTO edges (from_id, to_id, relation, role, evidence_class, match_quality, source, "
            "source_url, observation_id, generation) VALUES (?, ?, ?, NULL, 'source_explicit', 'exact_mbid', ?, ?, ?, ?)",
            [(f, t, rel, SOURCE, url, observation_id, generation) for f, t, rel, url in new])
        result.edges_created = len(new)
        result.edges_existing = len(wanted) - len(new)
        stale = [(key, i) for key, i in existing.items() if key not in wanted]
        if previous and len(wanted) < previous * min_retained:
            raise SliceValidationError(
                f"release links keep {len(wanted)} of {previous} previous edges (minimum share {min_retained})")
        db.executemany("DELETE FROM edges WHERE id = ?", [(i,) for _, i in stale])
        result.edges_removed = len(stale)
        for entity in sorted({k[0] for k, _ in stale} | {k[1] for k, _ in stale}):
            result.entities_removed += db.execute(
                "DELETE FROM entities WHERE id = ? AND owned = 0 AND navidrome_id IS NULL AND discogs_id IS NULL "
                "AND wikidata_id IS NULL "
                "AND NOT EXISTS (SELECT 1 FROM edges WHERE from_id = entities.id OR to_id = entities.id) "
                "AND NOT EXISTS (SELECT 1 FROM insights WHERE subject_id = entities.id)", (entity,)).rowcount
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    result.seconds = clock() - started
    return result


def build_release_links(
    db: sqlite3.Connection,
    read: TableReader,
    stream: ArchiveFilter,
    *,
    dump_timestamp: str | None,
    schema_sequence: int,
    clock: Callable[[], float] = time.time,
    min_retained: float = DEFAULT_MIN_RETAINED,
    log: Callable[[str], None] | None = None,
) -> LinkResult:
    """Plan and store in one call (the import job's step)."""
    plan = plan_links(db, read, stream, log=log)
    return apply_links(db, plan, dump_timestamp=dump_timestamp, schema_sequence=schema_sequence,
                       clock=clock, min_retained=min_retained)
