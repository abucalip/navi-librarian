"""Phase 5 discovery paths: ordered stops from an owned artist, each with the evidence that put it there.

A path starts at an artist and has a *kind* (the rules match ``path_coverage``, which measured them
on the owner's real store). Every stop carries ``reasons[]``; each reason names what links the stop
to the start (``code``), the entity in between (``via``), the start's own entity it hangs on
(``anchor``) and the stored facts behind it (``evidence``). A stop without at least one reason is
never produced, and a start with no stops yields ``status: "empty"``, not a padded list.

Evidence is credit-grade only: an ``inferred`` edge, or one whose other end is ``fuzzy_unconfirmed``
or ``unresolved``, is never used (not even as a bridge). Nothing is inferred here: a scene is a
stated non-country area, never a nationality read from names, labels or recording places.

Paths are built on demand from the knowledge store: no provider traffic and no write, except the
optional cache (:func:`cached_path`), which stores the answer in ``insights`` under the kind
``path:<kind>`` keyed by (start, kind, generation) and is stale when the MusicBrainz slice changes.
Builds are bounded by candidate rows and time (a hub label, area or session player cannot turn one
request into a full scan); ``truncated`` says which bound was hit.

``same_studio_different_decade`` is dropped (Phase 5 kill rule) and has no builder.
``sideman_to_leader`` reads the ``track_on`` / ``release_artist`` links of the Phase 7 release-links
import step: the stops are artists who lead a release carrying a recording the start is credited on.
"""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable

from ..store import generations
from ..musicbrainz.release_links import CREDIT_ROLES
from ..store import repositories as repo

PATH_KINDS = ("follow_the_musician", "sideman_to_leader", "label_path", "composition_path", "scene_path")
NOT_BUILT = {
    "same_studio_different_decade": "dropped: mostly empty on the owner's library (Phase 5 kill rule)",
}
CACHE_PREFIX = "path:"
SLICE_RESOURCE = "musicbrainz_slice"
SCENE_YEARS = 10
PROGRESS_OPS = 5000  # how many SQLite steps pass between deadline checks
PRESENTATION_VERSION = 6
COVER_CANDIDATES = 5  # releases offered per recording, so the app can try each for a cover
VARIOUS_NAMES = ("various artists", "various")
# Performer credits only: a producer is not a musician on the record, so it never bridges two recordings.
PERFORMER_ROLES = tuple(r for r in CREDIT_ROLES if r != "producer")
UNKNOWN_ARTIST_MBID = "125ec42a-7229-4250-afc5-e057484327fe"
UNRESOLVED_LABEL_ROWS = 3  # label rows whose recording artist cannot be found are capped, not listed in full
# Placeholder artists ("[unknown]", "[anonymous]", Various Artists) are never a stop or a bridge.
_REAL = ("({a}.canonical_name NOT LIKE '[%]' AND COALESCE({a}.mbid, '') NOT IN ('" + UNKNOWN_ARTIST_MBID
         + "', '89ad4ac3-39f7-470e-963a-56509c546377'))")

_CG = "{a}.evidence_class != 'inferred' AND {a}.match_quality NOT IN ('fuzzy_unconfirmed', 'unresolved')"


@dataclass(frozen=True)
class PathLimits:
    max_stops: int = 30
    max_reasons: int = 10       # reasons kept per stop (the count of all is kept as ``reason_count``)
    max_rows: int = 3000        # candidate rows read from the store
    max_seconds: float = 2.0
    max_per_bridge: int = 200   # credits read per bridge musician (a session player cannot flood a path)
    max_bridges: int = 300      # bridge musicians read, rarest first

    def __post_init__(self):
        if min(self.max_stops, self.max_reasons, self.max_rows, self.max_per_bridge, self.max_bridges) < 1 or self.max_seconds <= 0:
            raise ValueError("limits must be positive")


def _cg(*aliases: str) -> str:
    return " AND ".join(_CG.format(a=a) for a in aliases)


# Each query yields rows: stop, via, anchor, rank (smaller = nearer), e1, e2 (edge ids or NULL),
# plus ``code``. ``:a`` is the start, ``:g`` the generation. The anchor's own recordings and
# releases are the owned releases credited to it and the recordings on them.
_OWN_REL = (f"SELECT DISTINCT e.from_id AS rel FROM edges e JOIN entities r ON r.id = e.from_id AND r.type = 'release' "
            f"WHERE e.to_id = :a AND e.relation = 'credited_to' AND e.generation = :g AND {_cg('e')}")
_OWN_REC = (f"SELECT DISTINCT e.from_id AS rec FROM edges e WHERE e.relation = 'appears_on' AND e.generation = :g "
            f"AND {_cg('e')} AND e.to_id IN ({_OWN_REL})")

_ROLES = ", ".join("'%s'" % r for r in CREDIT_ROLES)  # constants, not input
_PERFORMERS = ", ".join("'%s'" % r for r in PERFORMER_ROLES)

_QUERIES: dict[str, str] = {
    # The start's credited recordings -> the release that carries each (``track_on``) -> that release's
    # leader (``release_artist``). Releases the start leads itself are skipped: that is not a sideman link.
    "sideman_to_leader": f"""
        SELECT l.to_id AS stop, t.to_id AS via, c.to_id AS anchor, 0 AS rank,
               c.id AS e1, t.id AS e2, l.id AS e3, 'sideman_on' AS code, NULL AS bridge
        FROM edges c
        JOIN entities q ON q.id = c.to_id AND q.type = 'recording'
        JOIN edges t ON t.from_id = c.to_id AND t.relation = 'track_on' AND t.generation = :g AND {_cg('t')}
        JOIN edges l ON l.from_id = t.to_id AND l.relation = 'release_artist' AND l.generation = :g AND {_cg('l')}
        JOIN entities lead ON lead.id = l.to_id AND lead.type IN ('artist', 'person', 'group') AND lead.id != :a AND {_REAL.format(a='lead')}
        WHERE c.from_id = :a AND c.relation IN ({_ROLES}) AND c.generation = :g AND {_cg('c')}
          AND NOT EXISTS (SELECT 1 FROM edges m WHERE m.from_id = t.to_id AND m.to_id = :a
                          AND m.relation = 'release_artist' AND m.generation = :g AND {_cg('m')})
        ORDER BY l.to_id, t.to_id, c.to_id LIMIT :n""",
    "label_path": f"""
        WITH own AS ({_OWN_REL}),
        lab AS (
            SELECT rl.label_id AS label, rl.release_id AS anchor, NULL AS via, NULL AS e1, 'same_label' AS code
              FROM release_labels rl WHERE rl.label_id IS NOT NULL AND rl.release_id IN (SELECT rel FROM own)
            UNION
            SELECT e.to_id, l.release_id, l.label_id, e.id, 'related_label'
              FROM release_labels l JOIN edges e ON e.from_id = l.label_id AND e.generation = :g AND {_cg('e')}
              JOIN entities t ON t.id = e.to_id AND t.type = 'label'
             WHERE l.label_id IS NOT NULL AND l.release_id IN (SELECT rel FROM own)
            UNION
            SELECT e.from_id, l.release_id, l.label_id, e.id, 'related_label'
              FROM release_labels l JOIN edges e ON e.to_id = l.label_id AND e.generation = :g AND {_cg('e')}
              JOIN entities t ON t.id = e.from_id AND t.type = 'label'
             WHERE l.label_id IS NOT NULL AND l.release_id IN (SELECT rel FROM own))
        SELECT rl.release_id AS stop, lab.label AS via, lab.anchor AS anchor,
               CASE lab.code WHEN 'same_label' THEN 0 ELSE 1 END AS rank,
               lab.e1 AS e1, NULL AS e2, NULL AS e3, lab.code AS code, lab.via AS bridge
        FROM lab JOIN release_labels rl ON rl.label_id = lab.label
        WHERE rl.release_id NOT IN (SELECT rel FROM own)
        ORDER BY rank, rl.release_id, lab.label LIMIT :n""",
    "scene_path": f"""
        WITH mine AS (
            SELECT e.to_id AS area, e.id AS e0, CAST(SUBSTR(la.begin_date, 1, 4) AS INTEGER) AS y
              FROM edges e JOIN entities ar ON ar.id = e.to_id AND ar.type = 'area'
              LEFT JOIN area_facts f ON f.entity_id = ar.id
              JOIN artist_life_span la ON la.entity_id = :a AND la.begin_date IS NOT NULL
             WHERE e.from_id = :a AND e.relation IN ('area', 'begin area') AND e.generation = :g AND {_cg('e')}
               AND LOWER(COALESCE(f.kind, '')) != 'country')
        SELECT b.id AS stop, m.area AS via, :a AS anchor,
               ABS(m.y - CAST(SUBSTR(lb.begin_date, 1, 4) AS INTEGER)) AS rank,
               m.e0 AS e1, e.id AS e2, NULL AS e3, 'same_area' AS code, NULL AS bridge
        FROM mine m
        JOIN edges e ON e.to_id = m.area AND e.relation IN ('area', 'begin area') AND e.generation = :g AND {_cg('e')}
        JOIN entities b ON b.id = e.from_id AND b.type IN ('artist', 'person', 'group') AND b.id != :a AND {_REAL.format(a='b')}
        JOIN artist_life_span lb ON lb.entity_id = b.id AND lb.begin_date IS NOT NULL
        WHERE ABS(m.y - CAST(SUBSTR(lb.begin_date, 1, 4) AS INTEGER)) <= {SCENE_YEARS}
        ORDER BY rank, b.id, m.area LIMIT :n""",
}

_REASON_TEXT = {
    "shared_musician": "{via} is credited on {anchor} from your library and on this recording",
    "sideman_on": "led {via}, a release that carries {anchor}, a recording the artist you started from played on",
    "same_label": "released on {via}, the label of {anchor} from your library",
    "related_label": "released on {via}, a label related to the label of {anchor} from your library",
    "same_work": "another recording of {via}, the same work as {anchor}, a recording in your library",
    "related_work": "a recording of {via}, a work related to the work of {anchor}, a recording in your library",
    "same_area": "from {via}, where {anchor} is also from, starting within %d years" % SCENE_YEARS,
}


class _Names:
    def __init__(self, db: sqlite3.Connection):
        self._db, self._memo = db, {}

    def get(self, entity_id: int | None) -> dict[str, Any] | None:
        if entity_id is None:
            return None
        if entity_id not in self._memo:
            e = repo.get_entity(self._db, entity_id) or {}
            self._memo[entity_id] = {k: e.get(k) for k in ("id", "type", "mbid", "canonical_name", "owned")}
        return self._memo[entity_id]


def _evidence(db: sqlite3.Connection, edge_ids: list[int]) -> list[dict[str, Any]]:
    out = []
    for edge_id in edge_ids:
        r = db.execute("SELECT relation, role, evidence_class, match_quality, source, source_url, valid_from, valid_to "
                       "FROM edges WHERE id = ?", (edge_id,)).fetchone()
        if r:
            out.append({k: r[k] for k in r.keys()})
    return out


_MUSICIANS = f"""
    WITH own AS ({_OWN_REC})
    SELECT p.id AS via, o.rec AS anchor, e1.id AS e1
    FROM own o
    JOIN edges e1 ON e1.to_id = o.rec AND e1.generation = :g AND e1.relation IN ({_PERFORMERS}) AND {_cg('e1')}
    JOIN entities p ON p.id = e1.from_id AND p.type IN ('artist', 'person', 'group') AND p.id != :a AND {_REAL.format(a='p')}
    ORDER BY p.id, o.rec LIMIT :n"""
_OWN_RECS = f"SELECT rec FROM ({_OWN_REC})"
_CREDITS = f"""
    SELECT e2.id AS e2, q.id AS stop FROM edges e2
    JOIN entities q ON q.id = e2.to_id AND q.type = 'recording'
    WHERE e2.from_id = :p AND e2.generation = :g AND e2.relation IN ({_PERFORMERS}) AND {_cg('e2')} ORDER BY q.id LIMIT :k"""


def _follow_the_musician_rows(db: sqlite3.Connection, start_id: int, gen: int, limits: PathLimits) -> tuple[list[dict[str, Any]], bool]:
    """Recordings credited to a musician who is also credited on a recording of the start's.

    Bounded per bridge: musicians are read rarest first (fewest credits) and each contributes at most
    ``max_per_bridge`` credits, so a session player with thousands of credits costs one small read,
    not a full expansion. Hitting either bound marks the path ``rows``-truncated.
    """
    own = {r["rec"] for r in db.execute(_OWN_RECS, {"a": start_id, "g": gen})}
    bridges: dict[int, list[tuple[int, int]]] = {}
    links = db.execute(_MUSICIANS, {"a": start_id, "g": gen, "n": limits.max_rows}).fetchall()
    for r in links:
        bridges.setdefault(r["via"], []).append((r["anchor"], r["e1"]))
    size = {p: db.execute("SELECT COUNT(*) FROM (SELECT 1 FROM edges WHERE from_id = ? LIMIT ?)",
                          (p, limits.max_per_bridge * 5)).fetchone()[0] for p in bridges}
    order = sorted(bridges, key=lambda p: (size[p], p))
    rows: list[dict[str, Any]] = []
    capped = len(links) >= limits.max_rows or len(order) > limits.max_bridges
    for p in order[:limits.max_bridges]:
        credits = db.execute(_CREDITS, {"p": p, "g": gen, "k": limits.max_per_bridge}).fetchall()
        capped = capped or len(credits) >= limits.max_per_bridge
        for c in credits:
            if c["stop"] in own:
                continue
            for anchor, e1 in bridges[p]:
                rows.append({"stop": c["stop"], "via": p, "anchor": anchor, "rank": 0, "e1": e1, "e2": c["e2"], "e3": None,
                             "code": "shared_musician", "bridge": None})
        if len(rows) >= limits.max_rows:
            return rows[:limits.max_rows], True
    return rows, capped


_OWN_WORKS = f"""
    WITH own AS ({_OWN_REC})
    SELECT e.to_id AS work, o.rec AS anchor, e.id AS e0
    FROM own o CROSS JOIN edges e INDEXED BY edges_from ON e.from_id = o.rec AND e.relation = 'performance'
     AND e.generation = :g AND {_cg('e')}
    CROSS JOIN entities w ON w.id = e.to_id AND w.type = 'work'
    ORDER BY e.to_id, o.rec LIMIT :n"""
_RELATED_WORKS = f"""
    SELECT CASE WHEN r.from_id = :w THEN r.to_id ELSE r.from_id END AS work, r.id AS e1
    FROM edges r JOIN entities t ON t.id = CASE WHEN r.from_id = :w THEN r.to_id ELSE r.from_id END AND t.type = 'work'
    WHERE (r.from_id = :w OR r.to_id = :w) AND r.generation = :g AND {_cg('r')} LIMIT :k"""
_PERFORMANCES = f"""
    SELECT p.id AS e, p.from_id AS stop FROM edges p
    WHERE p.to_id = :w AND p.relation = 'performance' AND p.generation = :g AND {_cg('p')} ORDER BY p.from_id LIMIT :k"""


def _composition_rows(db: sqlite3.Connection, start_id: int, gen: int, limits: PathLimits) -> tuple[list[dict[str, Any]], bool]:
    """Other recordings of a work (or a related work) that the start's recordings perform.

    Bounded like :func:`_follow_the_musician_rows`: works are read rarest first (fewest recordings),
    each contributes at most ``max_per_bridge`` recordings, and at most ``max_bridges`` works are read.
    """
    own = {r["rec"] for r in db.execute(_OWN_RECS, {"a": start_id, "g": gen})}
    links = db.execute(_OWN_WORKS, {"a": start_id, "g": gen, "n": limits.max_rows}).fetchall()
    capped = len(links) >= limits.max_rows
    # target work -> [(code, anchor recording, bridge work, relation edge, performance edge)]
    targets: dict[int, list[tuple]] = {}
    by_work: dict[int, list] = {}
    for l in links:
        by_work.setdefault(l["work"], []).append(l)
        targets.setdefault(l["work"], []).append(("same_work", l["anchor"], None, None, l["e0"]))
    for work, own_links in by_work.items():
        for rel in db.execute(_RELATED_WORKS, {"w": work, "g": gen, "k": limits.max_per_bridge}):
            for l in own_links:
                targets.setdefault(rel["work"], []).append(("related_work", l["anchor"], work, rel["e1"], l["e0"]))
    size = {w: db.execute("SELECT COUNT(*) FROM (SELECT 1 FROM edges WHERE to_id = ? AND relation = 'performance' LIMIT ?)",
                          (w, limits.max_per_bridge * 5)).fetchone()[0] for w in targets}
    order = sorted(targets, key=lambda w: (0 if any(t[0] == "same_work" for t in targets[w]) else 1, size[w], w))
    capped = capped or len(order) > limits.max_bridges
    rows: list[dict[str, Any]] = []
    for w in order[:limits.max_bridges]:
        perfs = db.execute(_PERFORMANCES, {"w": w, "g": gen, "k": limits.max_per_bridge}).fetchall()
        capped = capped or len(perfs) >= limits.max_per_bridge
        for perf in perfs:
            if perf["stop"] in own:
                continue
            for code, anchor, bridge, e1, e0 in targets[w]:
                rows.append({"stop": perf["stop"], "via": w, "anchor": anchor, "rank": 0 if code == "same_work" else 1,
                             "e1": perf["e"], "e2": e1, "e3": e0, "code": code, "bridge": bridge})
        if len(rows) >= limits.max_rows:
            return rows[:limits.max_rows], True
    return rows, capped



def _credited_names(
    db: sqlite3.Connection, entity_id: int, *, direction: str, relations: tuple[str, ...], generation: int
) -> list[str]:
    """Names of explicitly credited artists on a recording or release, in stable order."""
    join = "e.from_id = a.id AND e.to_id = ?" if direction == "recording" else "e.from_id = ? AND e.to_id = a.id"
    marks = ", ".join("?" for _ in relations)
    rows = db.execute(
        f"SELECT DISTINCT a.canonical_name FROM edges e JOIN entities a ON a.type IN ('artist', 'person', 'group') "
        f"AND {join} WHERE e.relation IN ({marks}) AND e.generation = ? AND {_cg('e')} "
        "ORDER BY a.canonical_name COLLATE NOCASE",
        (entity_id, *relations, generation),
    )
    return [r["canonical_name"] for r in rows if r["canonical_name"]]


def _owned_twin_artists(db: sqlite3.Connection, title: str, generation: int) -> list[str]:
    """Credit for a release the store holds no artist for: the one owned release with the same title.

    Other editions of a library album carry label rows but no ``release_artist`` edge. A title that matches
    more than one owned release ("Greatest Hits") is ambiguous and gives nothing.
    """
    if not title:
        return []
    twins = db.execute("SELECT id FROM entities WHERE type = 'release' AND owned = 1 AND canonical_name = ? COLLATE NOCASE LIMIT 2",
                       (title,)).fetchall()
    if len(twins) != 1:
        return []
    return _credited_names(db, twins[0]["id"], direction="release", relations=("release_artist", "credited_to"),
                           generation=generation)


def _release_candidates(
    db: sqlite3.Connection, recording_id: int, generation: int, *, prefer_owned: bool = False
) -> list[tuple[str, str]]:
    """The releases that carry a recording, best cover guess first, as (album, credited artist) pairs.

    The cover lookup matches the artist and the album exactly, so a release credited to one real artist comes first;
    compilations ("Various Artists") and releases with several credited names, which rarely match, come last.
    """
    rows = db.execute(
        "SELECT DISTINCT r.id, r.canonical_name, r.owned FROM edges e JOIN entities r ON r.id = e.to_id AND r.type = 'release' "
        "WHERE e.from_id = ? AND e.relation IN ('track_on', 'appears_on') AND e.generation = ? "
        f"AND {_cg('e')} AND r.canonical_name != '' LIMIT 40",
        (recording_id, generation),
    ).fetchall()
    ranked = []
    for row in rows:
        credited = _credited_names(db, row["id"], direction="release", relations=("release_artist", "credited_to"), generation=generation)
        if not credited:
            continue
        various = any(n.casefold() in VARIOUS_NAMES for n in credited)
        ranked.append(((various, len(credited) != 1, not (prefer_owned and row["owned"]),
                        row["canonical_name"].casefold(), credited[0].casefold()), (row["canonical_name"], credited[0])))
    ranked.sort(key=lambda item: item[0])
    out: list[tuple[str, str]] = []
    for _, pair in ranked:
        if pair not in out:
            out.append(pair)
    return out[:COVER_CANDIDATES]


def _recording_album(
    db: sqlite3.Connection, recording_id: int, generation: int, *, prefer_owned: bool = False
) -> tuple[str | None, str | None]:
    """A recording's best release and that release's credited artist, so the Android pane can look up a cover."""
    found = _release_candidates(db, recording_id, generation, prefer_owned=prefer_owned)
    return found[0] if found else (None, None)


def _anchor_presentation(
    db: sqlite3.Connection, kind: str, anchor_id: int | None, names: _Names, generation: int
) -> dict[str, str | None] | None:
    """The album and artist of a reason's library anchor, for the paths whose pane shows it with a cover.

    Label path: the anchor is a release (the album itself). Composition path: the anchor is a recording (its release).
    """
    anchor = names.get(anchor_id)
    if not anchor:
        return None
    if kind == "label_path":
        name = anchor.get("canonical_name")
        artists = _credited_names(db, anchor_id, direction="release", relations=("release_artist", "credited_to"), generation=generation) \
            or _owned_twin_artists(db, name or "", generation)
        return {"album": name, "album_artist": artists[0] if artists else None}
    if kind == "composition_path":
        album, album_artist = _recording_album(db, anchor_id, generation, prefer_owned=True)
        return {"album": album, "album_artist": album_artist}
    return None


def _path_presentation(
    db: sqlite3.Connection, kind: str, stop_id: int, reasons: list[dict[str, Any]],
    names: _Names, generation: int,
) -> dict[str, Any]:
    """Separate the artist from the recording/release title for the Android Paths sheet."""
    stop = names.get(stop_id) or {}
    stop_name = stop.get("canonical_name") or ""
    title, context = stop_name, None
    album = album_artist = artist = None
    albums_out: list[dict[str, str]] = []
    begin_year = None
    if kind == "follow_the_musician":
        # The song's own album (and its credited artist), so the sheet can write "Song (Album)" and open the album;
        # more releases follow so the app can try each for a cover.
        candidates = _release_candidates(db, stop_id, generation)
        if candidates:
            album, album_artist = candidates[0]
            albums_out = [{"album": a, "album_artist": b} for a, b in candidates]
        musicians, albums = [], []
        for reason in reasons:
            via = names.get(reason["via"]) or {}
            if via.get("type") in ("artist", "person", "group") and via.get("canonical_name") not in musicians:
                musicians.append(via["canonical_name"])
            if reason["anchor"] is not None:
                row = db.execute(
                    "SELECT r.canonical_name FROM edges e JOIN entities r ON r.id = e.to_id AND r.type = 'release' "
                    "WHERE e.from_id = ? AND e.relation = 'appears_on' AND e.generation = ? "
                    f"AND {_cg('e')} ORDER BY r.canonical_name COLLATE NOCASE LIMIT 1",
                    (reason["anchor"], generation),
                ).fetchone()
                if row and row["canonical_name"] and row["canonical_name"] not in albums:
                    albums.append(row["canonical_name"])
        title = ", ".join(musicians) or "Musician credit unavailable"
        context = ", ".join(albums) or None
    elif kind == "label_path":
        artists = _credited_names(
            db, stop_id, direction="release", relations=("release_artist", "credited_to"), generation=generation,
        ) or _owned_twin_artists(db, stop_name, generation)
        context = ", ".join(artists) or "Artist credit unavailable"
        album, album_artist = stop_name, (artists[0] if artists else None)
    elif kind == "composition_path":
        artists = _credited_names(
            db, stop_id, direction="recording",
            relations=("instrument", "vocal", "main performer", "performer", "performing orchestra"),
            generation=generation,
        )
        title = ", ".join(artists)
        context = stop_name or None
        artist = artists[0] if artists else None
        album, album_artist = _recording_album(db, stop_id, generation)
    elif kind == "scene_path":
        begin_year = _begin_year(db, stop_id)
    out = {"title": title, "context": context, "album": album, "album_artist": album_artist, "artist": artist}
    if albums_out:
        out["albums"] = albums_out
    if begin_year:
        out["begin_year"] = begin_year
        anchors = [r["anchor"] for r in reasons if r["anchor"] is not None]
        anchor_year = _begin_year(db, anchors[0]) if anchors else None
        if anchor_year:
            out["anchor_begin_year"] = anchor_year
    return out


def _begin_year(db: sqlite3.Connection, entity_id: int) -> int | None:
    """The year an artist's career began, from the stored life span."""
    row = db.execute("SELECT begin_date FROM artist_life_span WHERE entity_id = ?", (entity_id,)).fetchone()
    text = (row["begin_date"] or "")[:4] if row else ""
    return int(text) if text.isdigit() else None


def kind_rows(db: sqlite3.Connection, start_id: int, kind: str, gen: int, limits: PathLimits) -> tuple[list[Any], bool]:
    """The candidate rows of an artist path kind, before grouping and presentation; ``capped`` when a bound cut them."""
    if kind == "follow_the_musician":
        return _follow_the_musician_rows(db, start_id, gen, limits)
    if kind == "composition_path":
        return _composition_rows(db, start_id, gen, limits)
    return db.execute(_QUERIES[kind], {"a": start_id, "g": gen, "n": limits.max_rows}).fetchall(), False


def build_path(db: sqlite3.Connection, start_id: int, kind: str, *, limits: PathLimits = PathLimits(),
               generation: int | None = None, clock: Callable[[], float] = time.monotonic) -> dict[str, Any] | None:
    """The path of ``kind`` from an artist, built now from the store; None when the start is unknown.

    Raises ``ValueError`` for a kind with no builder or a start that is not an artist, person or group.
    """
    if kind not in PATH_KINDS:
        raise ValueError(NOT_BUILT.get(kind) or f"unknown path kind: {kind!r}")
    start = repo.get_entity(db, start_id)
    if start is None:
        return None
    if start["type"] not in ("artist", "person", "group"):
        raise ValueError("a path starts at an artist, person or group")
    gen = generation if generation is not None else generations.current_generation(db)
    started = clock()
    deadline = started + limits.max_seconds
    db.set_progress_handler(lambda: 1 if clock() > deadline else 0, PROGRESS_OPS)
    truncated: str | None = None
    capped = False
    try:
        rows, capped = kind_rows(db, start_id, kind, gen, limits)
    except sqlite3.OperationalError as exc:
        if "interrupted" not in str(exc):
            raise
        rows, truncated = [], "time"
    finally:
        db.set_progress_handler(None, 0)
    if truncated is None and (capped or len(rows) >= limits.max_rows):
        truncated = "rows"

    names = _Names(db)
    stops: dict[int, dict[str, Any]] = {}
    for r in rows:
        stop = stops.setdefault(r["stop"], {"rank": r["rank"], "reasons": [], "seen": set()})
        stop["rank"] = min(stop["rank"], r["rank"])
        key = (r["code"], r["via"], r["anchor"])
        if key in stop["seen"]:
            continue
        stop["seen"].add(key)
        stop["reasons"].append(r)

    ordered = sorted(stops.items(), key=lambda kv: (-len(kv[1]["reasons"]), kv[1]["rank"], kv[0]))
    result_stops = []
    seen_groups: set[str] = set()
    unresolved = 0
    examined = 0
    for stop_id, info in ordered:
        if len(result_stops) >= limits.max_stops:
            break
        examined += 1
        if examined > limits.max_stops * 20:
            break
        presentation = _path_presentation(db, kind, stop_id, info["reasons"], names, gen)
        if kind == "composition_path" and not presentation["artist"]:
            continue  # "performing artist not credited" tells the owner nothing
        if kind in ("follow_the_musician", "label_path"):
            who = (presentation["album_artist"] or "").casefold()
            if not who and kind == "follow_the_musician":
                who = "song:" + ((names.get(stop_id) or {}).get("canonical_name") or "").casefold()
            if who:
                if who in seen_groups:
                    continue  # one row per artist the row leads to
                seen_groups.add(who)
            elif kind == "label_path":
                if unresolved >= UNRESOLVED_LABEL_ROWS:
                    continue
                unresolved += 1
        reasons = []
        for r in info["reasons"][:limits.max_reasons]:
            via, anchor = names.get(r["via"]), names.get(r["anchor"])
            edge_ids = [e for e in (r["e1"], r["e2"], r["e3"]) if e is not None]
            reasons.append({
                "code": r["code"],
                "text": _REASON_TEXT[r["code"]].format(via=(via or {}).get("canonical_name", "?"),
                                                       anchor=(anchor or {}).get("canonical_name", "?")),
                "via": via, "anchor": anchor,
                "evidence": _evidence(db, edge_ids) + _label_evidence(db, r),
            })
            anchor_presentation = _anchor_presentation(db, kind, r["anchor"], names, gen)
            if anchor_presentation is not None:
                reasons[-1]["anchor_presentation"] = anchor_presentation
        result_stops.append({
            "entity": names.get(stop_id),
            "presentation": presentation,
            "reason_count": len(info["reasons"]),
            "reasons": reasons,
        })
    if len(result_stops) >= limits.max_stops and examined < len(ordered) and truncated is None:
        truncated = "stops"
    return {
        "kind": kind,
        "start": names.get(start_id),
        "generation": gen,
        "status": "ok" if result_stops else "empty",
        "stops": result_stops,
        "truncated": truncated,
        "built_from": {SLICE_RESOURCE: generations.data_version(db, SLICE_RESOURCE)},
        "presentation_version": PRESENTATION_VERSION,
    }


def _label_evidence(db: sqlite3.Connection, r: sqlite3.Row) -> list[dict[str, Any]]:
    """Label paths rest on ``release_labels`` rows (a release issued on a label), not only on edges."""
    if r["code"] not in ("same_label", "related_label"):
        return []
    bridge = r["bridge"] if r["bridge"] is not None else r["via"]
    rows = db.execute("SELECT release_id, label_id, catalogue_number FROM release_labels "
                      "WHERE (label_id = ? AND release_id = ?) OR (label_id = ? AND release_id = ?)",
                      (r["via"], r["stop"], bridge, r["anchor"])).fetchall()
    return [{"relation": "released_on", "catalogue_number": x["catalogue_number"], "source": "musicbrainz_dump"}
            for x in rows]


def cached_path(db: sqlite3.Connection, start_id: int, kind: str, *, limits: PathLimits = PathLimits(),
                refresh: bool = False, clock: Callable[[], float] = time.monotonic,
                now: Callable[[], float] = time.time) -> dict[str, Any] | None:
    """The cached path for (start, kind, generation), building and saving it when missing or stale.

    Needs a writable connection. A path cut short by time is returned but not saved, so a later
    request with more room can complete it.
    """
    if kind not in PATH_KINDS:
        raise ValueError(NOT_BUILT.get(kind) or f"unknown path kind: {kind!r}")
    gen = generations.current_generation(db)
    version = {SLICE_RESOURCE: generations.data_version(db, SLICE_RESOURCE)}
    if not refresh:
        row = db.execute("SELECT payload FROM insights WHERE kind = ? AND subject_id = ? AND generation = ?",
                         (CACHE_PREFIX + kind, start_id, gen)).fetchone()
        if row:
            cached = json.loads(row["payload"])
            if (
                cached.get("built_from") == version
                and cached.get("presentation_version") == PRESENTATION_VERSION
            ):
                return cached
    path = build_path(db, start_id, kind, limits=limits, generation=gen, clock=clock)
    if path is None or path["truncated"] == "time":
        return path
    with db:
        db.execute("DELETE FROM insights WHERE kind = ? AND subject_id = ?", (CACHE_PREFIX + kind, start_id))
        db.execute("INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at) "
                   "VALUES (?, ?, ?, '[]', ?, ?)",
                   (CACHE_PREFIX + kind, start_id, json.dumps(path, sort_keys=True), gen, now()))
    return path
