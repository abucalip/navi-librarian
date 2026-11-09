"""Album paths: ordered stops from an owned album, each with the credit that puts it there.

Kinds built here (docs/ALBUM_PATHS_PROPOSAL.md): ``album_crew`` (Studio Crew), ``album_guests``
(Guest List) and ``album_works`` (Covers and Sources). A stop is an owned album other than the start.

The rules are the artist paths' (see :mod:`intelligence.graph.paths`): credit-grade evidence only (an
``inferred`` edge, or one whose other end is ``fuzzy_unconfirmed`` or ``unresolved``, is never used, not
even as a bridge); every stop carries ``reasons[]`` and a stop without one is never produced; a start with
no stops is ``empty``; builds are bounded by rows, stops and time with a ``truncated`` flag; no provider
traffic and no write, except the optional cache (:func:`cached_album_path`).

Two rules are specific to albums (owner decisions, 2026-11-09):

* A stop the album's credited artists already reach with their five artist paths is dropped, even when
  its reason differs. ``overlap_dropped`` counts them. A build that runs out of time while measuring that
  overlap is ``truncated: "time"``; its stops may still include some the artist paths reach.
* Nothing here reads play history, similarity or any taste data. Hub people and popular works are capped
  (``PERSON_CAP``, ``WORK_CAP``) by shared credits and then release date, never by popularity, and the
  count of what the cap left out is reported in ``capped``.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import replace
from typing import Any, Callable, Iterable

from ..store import generations
from ..store import repositories as repo
from . import paths as artist_paths
from .paths import PathLimits, _REAL, _Names, _cg, _credited_names, _evidence

ALBUM_PATH_KINDS = ("album_crew", "album_guests", "album_works")
NOT_BUILT = {
    "album_room": "not built yet",
    "album_moment": "not built yet",
    "album_sonic_neighbours": "composed from the Sonic routes, not a graph path",
    "album_gaps": "not built yet",
}
CACHE_PREFIX = "path:"
PRESENTATION_VERSION = 1
PERSON_CAP = 50   # albums kept per hub person
WORK_CAP = 20     # albums kept per work
# The relations the coverage probe measured; the thresholds were fixed on these.
CREW_ROLES = ("producer", "engineer", "mix", "mastering")
GUEST_ROLES = ("instrument", "vocal", "performer")
WORK_RELATIONS = ("parts", "other version", "arrangement", "based on")
_PEOPLE = "('artist', 'person', 'group')"

_REASON_TEXT = {
    "crew_on": "{via} has a production credit on {anchor}, from the album you started from, and on this album",
    "guest_on": "{via} is credited on {anchor}, from the album you started from, as a guest, and appears on this album",
    "same_work": "this album has another recording of {via}, the work behind {anchor} on the album you started from",
    "derived_work": "this album has a recording of {via}, a work related to the work behind {anchor} on the album you started from",
}


def _in(values: Iterable[str]) -> str:
    return ", ".join("'%s'" % v for v in values)  # constants, not input


_START_RECS = (f"SELECT ap.from_id FROM edges ap WHERE ap.to_id = :a AND ap.relation = 'appears_on' "
               f"AND ap.generation = :g AND {_cg('ap')}")
_OWN_ARTISTS = (f"SELECT c.to_id FROM edges c WHERE c.from_id = :a AND c.relation IN ('credited_to', 'release_artist') "
                f"AND c.generation = :g AND {_cg('c')}")


def _credit_targets(db: sqlite3.Connection, person: int, gen: int, start_id: int, roles: tuple[str, ...], *,
                    albums: bool) -> list[sqlite3.Row]:
    """Owned albums (other than the start) a person holds a credit with one of ``roles`` on, one row per credit."""
    roles_sql = _in(roles)
    out = []
    if albums:
        out += db.execute(
            f"SELECT r.id AS stop, e.to_id AS hit, e.id AS e FROM edges e "
            f"JOIN entities r ON r.id = e.to_id AND r.type = 'release' AND r.owned = 1 "
            f"WHERE e.from_id = :p AND e.relation IN ({roles_sql}) AND e.generation = :g AND {_cg('e')} AND r.id != :a",
            {"p": person, "g": gen, "a": start_id}).fetchall()
    out += db.execute(
        f"SELECT r.id AS stop, e.to_id AS hit, e.id AS e FROM edges e "
        f"JOIN edges ap ON ap.from_id = e.to_id AND ap.relation = 'appears_on' AND ap.generation = :g AND {_cg('ap')} "
        f"JOIN entities r ON r.id = ap.to_id AND r.type = 'release' AND r.owned = 1 "
        f"WHERE e.from_id = :p AND e.relation IN ({roles_sql}) AND e.generation = :g AND {_cg('e')} AND r.id != :a",
        {"p": person, "g": gen, "a": start_id}).fetchall()
    return out


class _Dates:
    """Earliest stored release date of an album, for ordering only (a missing date sorts last)."""

    def __init__(self, db: sqlite3.Connection):
        self._db, self._memo = db, {}

    def get(self, release_id: int) -> str:
        if release_id not in self._memo:
            r = self._db.execute("SELECT date FROM release_facts WHERE entity_id = ?", (release_id,)).fetchone()
            self._memo[release_id] = (r["date"] if r and r["date"] else "9999")
        return self._memo[release_id]


class _Build:
    """State of one album path build: bounds, the deadline and what was left out."""

    def __init__(self, db: sqlite3.Connection, start_id: int, gen: int, limits: PathLimits, clock: Callable[[], float]):
        self.db, self.start, self.gen, self.limits, self.clock = db, start_id, gen, limits, clock
        self.deadline = clock() + limits.max_seconds
        self.rows: list[dict[str, Any]] = []
        self.truncated: str | None = None
        self.capped: list[tuple[int, int]] = []   # (via entity id, albums the cap left out)
        self.dates = _Dates(db)

    def out_of_time(self) -> bool:
        if self.clock() > self.deadline:
            self.truncated = "time"
        return self.truncated == "time"

    def add(self, **row: Any) -> None:
        row.setdefault("rank", 0), row.setdefault("e3", None), row.setdefault("bridge", None)
        self.rows.append(row)

    def full(self) -> bool:
        if len(self.rows) >= self.limits.max_rows:
            self.truncated = self.truncated or "rows"
        return len(self.rows) >= self.limits.max_rows


def _people_rows(b: _Build, roles: tuple[str, ...], *, album_scope: bool, exclude_own_artists: bool) -> dict[int, list[tuple[int, int]]]:
    """People credited with ``roles`` on the start (and, when asked, on its recordings): person -> [(anchor, edge)]."""
    scope = "e.to_id IN (%s)" % _START_RECS
    if album_scope:
        scope = f"(e.to_id = :a OR {scope})"
    skip = f"AND p.id NOT IN ({_OWN_ARTISTS})" if exclude_own_artists else ""
    rows = b.db.execute(
        f"SELECT p.id AS via, e.to_id AS anchor, MIN(e.id) AS e1 FROM edges e "
        f"JOIN entities p ON p.id = e.from_id AND p.type IN {_PEOPLE} AND {_REAL.format(a='p')} {skip} "
        f"WHERE e.relation IN ({_in(roles)}) AND e.generation = :g AND {_cg('e')} AND {scope} "
        f"GROUP BY p.id, e.to_id ORDER BY p.id, e.to_id LIMIT :n",
        {"a": b.start, "g": b.gen, "n": b.limits.max_rows}).fetchall()
    if len(rows) >= b.limits.max_rows:
        b.truncated = "rows"
    people: dict[int, list[tuple[int, int]]] = {}
    for r in rows:
        people.setdefault(r["via"], []).append((r["anchor"], r["e1"]))
    return people


def _person_rows(b: _Build, roles: tuple[str, ...], code: str, *, album_scope: bool, exclude_own_artists: bool) -> None:
    people = _people_rows(b, roles, album_scope=album_scope, exclude_own_artists=exclude_own_artists)
    if len(people) > b.limits.max_bridges:
        b.truncated = b.truncated or "rows"
    for person in sorted(people)[:b.limits.max_bridges]:
        if b.out_of_time() or b.full():
            return
        hits: dict[int, list[sqlite3.Row]] = {}
        for t in _credit_targets(b.db, person, b.gen, b.start, roles, albums=album_scope):
            hits.setdefault(t["stop"], []).append(t)
        # Shared credits first, then the earlier release; never popularity or similarity.
        ranked = sorted(hits, key=lambda s: (-len(hits[s]), b.dates.get(s), s))
        if len(ranked) > PERSON_CAP:
            b.capped.append((person, len(ranked) - PERSON_CAP))
        for stop in ranked[:PERSON_CAP]:
            target_edge = min(t["e"] for t in hits[stop])
            for anchor, e1 in people[person]:
                b.add(stop=stop, via=person, anchor=anchor, e1=e1, e2=target_edge, code=code)


_START_WORKS = (f"SELECT e.to_id AS work, e.from_id AS anchor, MIN(e.id) AS e0 FROM edges e "
                f"JOIN entities w ON w.id = e.to_id AND w.type = 'work' "
                f"WHERE e.relation = 'performance' AND e.generation = :g AND {_cg('e')} AND e.from_id IN ({_START_RECS}) "
                f"GROUP BY e.to_id, e.from_id ORDER BY e.to_id, e.from_id LIMIT :n")
_RELATED = (f"SELECT CASE WHEN r.from_id = :w THEN r.to_id ELSE r.from_id END AS work, r.id AS e1 FROM edges r "
            f"JOIN entities t ON t.id = CASE WHEN r.from_id = :w THEN r.to_id ELSE r.from_id END AND t.type = 'work' "
            f"WHERE (r.from_id = :w OR r.to_id = :w) AND r.relation IN ({_in(WORK_RELATIONS)}) AND r.generation = :g "
            f"AND {_cg('r')} LIMIT :k")
_PERFORMED_ON_OWNED = (
    f"SELECT ap.to_id AS stop, p.id AS e FROM edges p "
    f"JOIN edges ap ON ap.from_id = p.from_id AND ap.relation = 'appears_on' AND ap.generation = :g AND {_cg('ap')} "
    f"JOIN entities r ON r.id = ap.to_id AND r.type = 'release' AND r.owned = 1 "
    f"WHERE p.to_id = :w AND p.relation = 'performance' AND p.generation = :g AND {_cg('p')} AND ap.to_id != :a")


def _work_rows(b: _Build) -> None:
    links = b.db.execute(_START_WORKS, {"a": b.start, "g": b.gen, "n": b.limits.max_rows}).fetchall()
    if len(links) >= b.limits.max_rows:
        b.truncated = "rows"
    # target work -> [(code, anchor track, source work, relation edge, performance edge on the start)]
    targets: dict[int, list[tuple]] = {}
    by_work: dict[int, list[sqlite3.Row]] = {}
    for l in links:
        by_work.setdefault(l["work"], []).append(l)
        targets.setdefault(l["work"], []).append(("same_work", l["anchor"], None, None, l["e0"]))
    for work, own in by_work.items():
        for rel in b.db.execute(_RELATED, {"w": work, "g": b.gen, "k": b.limits.max_per_bridge}):
            for l in own:
                targets.setdefault(rel["work"], []).append(("derived_work", l["anchor"], work, rel["e1"], l["e0"]))
    order = sorted(targets, key=lambda w: (0 if any(t[0] == "same_work" for t in targets[w]) else 1, w))
    if len(order) > b.limits.max_bridges:
        b.truncated = b.truncated or "rows"
    for work in order[:b.limits.max_bridges]:
        if b.out_of_time() or b.full():
            return
        hits: dict[int, int] = {}
        for r in b.db.execute(_PERFORMED_ON_OWNED, {"w": work, "g": b.gen, "a": b.start}):
            hits.setdefault(r["stop"], r["e"])
        ranked = sorted(hits, key=lambda s: (b.dates.get(s), s))
        if len(ranked) > WORK_CAP:
            b.capped.append((work, len(ranked) - WORK_CAP))
        for stop in ranked[:WORK_CAP]:
            for code, anchor, source, e1, e0 in targets[work]:
                b.add(stop=stop, via=work, anchor=anchor, e1=hits[stop], e2=e1, e3=e0, code=code,
                      rank=0 if code == "same_work" else 1, bridge=source)


def _artist_reach(b: _Build, candidates: set[int]) -> set[int]:
    """The candidate albums the album's credited artists already reach with their five artist paths."""
    artists = [r[0] for r in b.db.execute(
        f"SELECT DISTINCT c.to_id FROM edges c JOIN entities a ON a.id = c.to_id AND a.type IN {_PEOPLE} "
        f"WHERE c.from_id = :a AND c.relation IN ('credited_to', 'release_artist') AND c.generation = :g AND {_cg('c')} "
        f"ORDER BY c.to_id", {"a": b.start, "g": b.gen})]
    reached: set[int] = set()
    for artist in artists:
        for kind in artist_paths.PATH_KINDS:
            remaining = b.deadline - b.clock()
            if remaining <= 0:
                b.truncated = "time"
                break
            b.db.set_progress_handler(lambda: 1 if b.clock() > b.deadline else 0, artist_paths.PROGRESS_OPS)
            try:
                rows, _ = artist_paths.kind_rows(b.db, artist, kind, b.gen, replace(b.limits, max_seconds=remaining))
                reached.update(r["stop"] for r in rows)
            except sqlite3.OperationalError as exc:
                if "interrupted" not in str(exc):
                    raise
                b.truncated = "time"
            finally:
                b.db.set_progress_handler(None, 0)
            if b.truncated == "time":
                break
        if b.truncated == "time":
            break
    return _reached_stops(b.db, candidates, reached, b.gen)


def _reached_stops(db: sqlite3.Connection, candidates: set[int], reached: set[int], gen: int) -> set[int]:
    """The candidate albums an artist-path stop stands for: the release itself, one of its recordings, or its artist.

    Read from the candidates' side (their tracks and credited artists), so the cost follows the few stops
    under test, not everything the artist paths reached.
    """
    out = candidates & reached
    ids = sorted(candidates - out)
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        marks = ", ".join("?" for _ in chunk)
        for r in db.execute(f"SELECT e.to_id AS album, e.from_id AS other FROM edges e WHERE e.to_id IN ({marks}) "
                            f"AND e.relation = 'appears_on' AND e.generation = ? AND {_cg('e')}", (*chunk, gen)):
            if r["other"] in reached:
                out.add(r["album"])
        for r in db.execute(f"SELECT e.from_id AS album, e.to_id AS other FROM edges e WHERE e.from_id IN ({marks}) "
                            f"AND e.relation = 'credited_to' AND e.generation = ? AND {_cg('e')}", (*chunk, gen)):
            if r["other"] in reached:
                out.add(r["album"])
    return out


def _presentation(db: sqlite3.Connection, stop_id: int, names: _Names, gen: int) -> dict[str, Any]:
    """The album and its credited artist, shaped like the label path's so clients reuse their rows."""
    name = (names.get(stop_id) or {}).get("canonical_name") or ""
    artists = _credited_names(db, stop_id, direction="release", relations=("release_artist", "credited_to"), generation=gen) \
        or artist_paths._owned_twin_artists(db, name, gen)
    return {"title": name, "context": ", ".join(artists) or "Artist credit unavailable", "album": name,
            "album_artist": artists[0] if artists else None, "artist": None}


def build_album_path(db: sqlite3.Connection, start_id: int, kind: str, *, limits: PathLimits = PathLimits(),
                     generation: int | None = None, clock: Callable[[], float] = time.monotonic) -> dict[str, Any] | None:
    """The path of ``kind`` from an album, built now from the store; None when the start is unknown.

    Raises ``ValueError`` for a kind with no builder or a start that is not a release.
    """
    if kind not in ALBUM_PATH_KINDS:
        raise ValueError(NOT_BUILT.get(kind) or f"unknown album path kind: {kind!r}")
    start = repo.get_entity(db, start_id)
    if start is None:
        return None
    if start["type"] != "release":
        raise ValueError("an album path starts at a release")
    gen = generation if generation is not None else generations.current_generation(db)
    b = _Build(db, start_id, gen, limits, clock)
    db.set_progress_handler(lambda: 1 if clock() > b.deadline else 0, artist_paths.PROGRESS_OPS)
    try:
        if kind == "album_crew":
            _person_rows(b, CREW_ROLES, "crew_on", album_scope=True, exclude_own_artists=False)
        elif kind == "album_guests":
            _person_rows(b, GUEST_ROLES, "guest_on", album_scope=False, exclude_own_artists=True)
        else:
            _work_rows(b)
    except sqlite3.OperationalError as exc:
        if "interrupted" not in str(exc):
            raise
        b.truncated = "time"
    finally:
        db.set_progress_handler(None, 0)
    rows = b.rows
    stops_found = {r["stop"] for r in rows}
    reached = _artist_reach(b, stops_found) if stops_found and b.truncated != "time" else set()
    dropped = stops_found & reached

    names = _Names(db)
    stops: dict[int, dict[str, Any]] = {}
    for r in rows:
        if r["stop"] in reached:
            continue
        stop = stops.setdefault(r["stop"], {"rank": r["rank"], "reasons": [], "seen": set(), "via": set()})
        stop["rank"] = min(stop["rank"], r["rank"])
        key = (r["code"], r["via"], r["anchor"])
        if key in stop["seen"]:
            continue
        stop["seen"].add(key)
        stop["via"].add(r["via"])
        stop["reasons"].append(r)
    # Most distinct people (or works) first, then the nearer kind of link, then the earlier release.
    ordered = sorted(stops.items(), key=lambda kv: (-len(kv[1]["via"]), kv[1]["rank"], b.dates.get(kv[0]), kv[0]))
    result_stops = []
    for stop_id, info in ordered[:limits.max_stops]:
        reasons = []
        for r in info["reasons"][:limits.max_reasons]:
            via, anchor = names.get(r["via"]), names.get(r["anchor"])
            reasons.append({
                "code": r["code"],
                "text": _REASON_TEXT[r["code"]].format(via=(via or {}).get("canonical_name", "?"),
                                                       anchor=(anchor or {}).get("canonical_name", "?")),
                "via": via, "anchor": anchor,
                "evidence": _evidence(db, [e for e in (r["e1"], r["e2"], r["e3"]) if e is not None]),
            })
        result_stops.append({"entity": names.get(stop_id), "presentation": _presentation(db, stop_id, names, gen),
                             "reason_count": len(info["reasons"]), "reasons": reasons})
    truncated = b.truncated
    if truncated is None and len(ordered) > limits.max_stops:
        truncated = "stops"
    return {
        "kind": kind,
        "start": names.get(start_id),
        "generation": gen,
        "status": "ok" if result_stops else "empty",
        "stops": result_stops,
        "truncated": truncated,
        "overlap_dropped": len(dropped),
        "capped": [{"via": names.get(v), "more": n} for v, n in b.capped],
        "built_from": {artist_paths.SLICE_RESOURCE: generations.data_version(db, artist_paths.SLICE_RESOURCE)},
        "presentation_version": PRESENTATION_VERSION,
    }


def cached_album_path(db: sqlite3.Connection, start_id: int, kind: str, *, limits: PathLimits = PathLimits(),
                      refresh: bool = False, clock: Callable[[], float] = time.monotonic,
                      now: Callable[[], float] = time.time) -> dict[str, Any] | None:
    """The cached path for (start, kind, generation), building and saving it when missing or stale.

    Needs a writable connection. A path cut short by time is returned but not saved.
    """
    if kind not in ALBUM_PATH_KINDS:
        raise ValueError(NOT_BUILT.get(kind) or f"unknown album path kind: {kind!r}")
    gen = generations.current_generation(db)
    version = {artist_paths.SLICE_RESOURCE: generations.data_version(db, artist_paths.SLICE_RESOURCE)}
    if not refresh:
        row = db.execute("SELECT payload FROM insights WHERE kind = ? AND subject_id = ? AND generation = ?",
                         (CACHE_PREFIX + kind, start_id, gen)).fetchone()
        if row:
            cached = json.loads(row["payload"])
            if cached.get("built_from") == version and cached.get("presentation_version") == PRESENTATION_VERSION:
                return cached
    path = build_album_path(db, start_id, kind, limits=limits, generation=gen, clock=clock)
    if path is None or path["truncated"] == "time":
        return path
    with db:
        db.execute("DELETE FROM insights WHERE kind = ? AND subject_id = ?", (CACHE_PREFIX + kind, start_id))
        db.execute("INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at) "
                   "VALUES (?, ?, ?, '[]', ?, ?)",
                   (CACHE_PREFIX + kind, start_id, json.dumps(path, sort_keys=True), gen, now()))
    return path
