"""Fill the gap between two dump imports from the MusicBrainz API (Server V2 Phase 4, E8).

A newly owned MBID is not in the last dump, so its dossier would stay empty until the next
import. This worker job asks the API for just those entities, writes the answers into the one
knowledge store as ``musicbrainz_api`` edges and facts, and stops. The next dump import covers
the same entities; :func:`absorb_api_edges` then drops the API copies the dump now states.

Scope, chosen so provider traffic stays small and every request has a consumer:

* **Owned artists without a life span**: one search request per 25 artists (``arid:A OR B ...``),
  the batch form MusicBrainz offers. Fills ``artist_life_span``.
* **Owned releases the dump does not cover**: one lookup per release, which returns the release's
  and every track's artist, label and work relationships, plus date, country and status, in a
  single response. MusicBrainz has no multi-id lookup, so this is the single-lookup fallback
  (owner batching rule); it is already the whole dossier of a release in one request.

Rules: only owned entities with an MBID; nothing runs until a dump is loaded (a bare store needs
the import, not thousands of calls); at most ``max_requests`` requests per run, at most one request
per ``MIN_INTERVAL`` seconds; an entity that was fetched is not asked again before its
``source_state`` refresh time (30 days after success or absence, exponential back-off after a
failure); three failed requests in a row stop the run. Request handlers never call this: the web
process only reads. No ``navidrome_server.py`` involvement, no credentials (the API is anonymous).
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..jobs import runner
from ..store import repositories as repo
from ..store import source_state
from .loader import SOURCE as DUMP_SOURCE
from .neighbourhood import LINK_TABLES

SOURCE = "musicbrainz_api"
JOB = "musicbrainz_api_fill"
OP_RELEASE = "release_lookup"
OP_ARTISTS = "artist_search"
BASE = "https://musicbrainz.org/ws/2/"
USER_AGENT = "Discair/1.0 (personal music discovery)"
MIN_INTERVAL = 1.1
RETRY_PAUSE = 3.0
ARTIST_BATCH = 25
REFRESH_TTL = 30 * 24 * 3600.0
MAX_FAILURES_IN_A_ROW = 3
DEFAULT_MAX_REQUESTS = 150
RELEASE_INC = "artist-rels+label-rels+recordings+recording-level-rels+work-rels+work-level-rels"
RELEASE_STATUSES = frozenset({"official", "promotion", "bootleg", "pseudo-release", "withdrawn", "expunged", "cancelled"})
ENTITY_KINDS = frozenset(t for pair in LINK_TABLES.values() for t in pair)
_PAIRS = frozenset(LINK_TABLES.values())
_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")

Fetch = Callable[[str], dict]


class ApiError(Exception):
    """A request failed; ``status`` is the HTTP status (404 means the entity is absent), else None."""

    def __init__(self, status: int | None, message: str = ""):
        super().__init__(message or f"HTTP {status}")
        self.status = status


def http_fetch(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ApiError(exc.code) from exc
    except Exception as exc:  # network, timeout, bad JSON
        raise ApiError(None, type(exc).__name__) from exc


class Paced:
    """Wraps a fetch: at least ``interval`` seconds between requests, one retry after a 503/429."""

    def __init__(self, fetch: Fetch = http_fetch, *, interval: float = MIN_INTERVAL, retry_pause: float = RETRY_PAUSE,
                 sleep: Callable[[float], None] = time.sleep, monotonic: Callable[[], float] = time.monotonic):
        self._fetch, self._interval, self._pause = fetch, interval, retry_pause
        self._sleep, self._mono = sleep, monotonic
        self._last: float | None = None
        self.requests = 0

    def __call__(self, url: str) -> dict:
        for attempt in range(2):
            if self._last is not None:
                wait = (self._interval if attempt == 0 else self._pause) - (self._mono() - self._last)
                if wait > 0:
                    self._sleep(wait)
            self._last = self._mono()
            self.requests += 1
            try:
                return self._fetch(url)
            except ApiError as exc:
                if exc.status not in (429, 503) or attempt:
                    raise
        raise AssertionError("unreachable")


@dataclass
class FillResult:
    requests: int = 0
    artists_filled: int = 0
    artists_absent: int = 0
    releases_filled: int = 0
    releases_absent: int = 0
    edges_created: int = 0
    failures: int = 0
    pending_artists: int = 0
    pending_releases: int = 0
    stopped: str | None = None  # no_slice | request_budget | failures

    def summary(self) -> dict[str, Any]:
        return dict(self.__dict__)


# ------------------------------------------------------------------ candidates

def slice_loaded(db: sqlite3.Connection) -> bool:
    return db.execute("SELECT 1 FROM meta WHERE key = 'musicbrainz_slice.loaded_at'").fetchone() is not None


def _due(db, operation: str, mbid: str, now: float) -> bool:
    state = source_state.get_state(db, SOURCE, operation, mbid)
    return state is None or (state["next_refresh_at"] is not None and state["next_refresh_at"] <= now)


def pending_artists(db: sqlite3.Connection, now: float) -> list[tuple[int, str]]:
    rows = db.execute(
        "SELECT e.id, e.mbid FROM entities e WHERE e.owned = 1 AND e.type = 'artist' AND e.mbid IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM artist_life_span a WHERE a.entity_id = e.id) ORDER BY e.id").fetchall()
    return [(r["id"], r["mbid"].lower()) for r in rows if _due(db, OP_ARTISTS, r["mbid"].lower(), now)]


def pending_releases(db: sqlite3.Connection, now: float) -> list[tuple[int, str]]:
    """Owned releases no dump edge touches (the dump answers the rest with no request)."""
    rows = db.execute(
        "SELECT e.id, e.mbid FROM entities e WHERE e.owned = 1 AND e.type = 'release' AND e.mbid IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM edges d WHERE d.source = ? AND (d.from_id = e.id OR d.to_id = e.id)) "
        "ORDER BY e.id", (DUMP_SOURCE,)).fetchall()
    return [(r["id"], r["mbid"].lower()) for r in rows if _due(db, OP_RELEASE, r["mbid"].lower(), now)]


# ------------------------------------------------------------------ parsing

def _date(value) -> str | None:
    value = str(value or "").strip()
    return value if _DATE.match(value) else None


def _orient(this_kind: str, other_kind: str, direction: str) -> bool | None:
    """True when the edge runs this -> other, False when other -> this, None when the dump has no such table."""
    forward, backward = (this_kind, other_kind) in _PAIRS, (other_kind, this_kind) in _PAIRS
    if forward and backward:
        return direction != "backward"
    if forward:
        return True
    if backward:
        return False
    return None


def release_links(payload: dict) -> list[dict[str, Any]]:
    """Every relationship in a release lookup as ``{from, to, relation, role, begin, end}``.

    ``from`` and ``to`` are ``(kind, mbid, name)``, oriented like the dump's relationship tables.
    """
    found: dict[tuple, dict[str, Any]] = {}

    def walk(kind: str, mbid: str, name: str, relations) -> None:
        for rel in relations or []:
            target_kind = str(rel.get("target-type") or "").replace("-", "_")
            target = rel.get(target_kind)
            relation = str(rel.get("type") or "").strip()
            if target_kind not in ENTITY_KINDS or not isinstance(target, dict) or not target.get("id") or not relation:
                continue
            other = (target_kind, str(target["id"]).lower(), str(target.get("name") or target.get("title") or target["id"]))
            this = (kind, mbid, name)
            forward = _orient(kind, target_kind, str(rel.get("direction") or "forward"))
            if forward is None:
                continue
            role = ", ".join(sorted({str(a) for a in rel.get("attributes") or [] if a})) or None
            a, b = (this, other) if forward else (other, this)
            found.setdefault((a[:2], b[:2], relation, role or ""), {
                "from": a, "to": b, "relation": relation, "role": role,
                "begin": _date(rel.get("begin")), "end": _date(rel.get("end"))})
            walk(*other, target.get("relations"))  # work-level relationships hang off the work

    release_mbid = str(payload["id"]).lower()
    walk("release", release_mbid, str(payload.get("title") or release_mbid), payload.get("relations"))
    for medium in payload.get("media") or []:
        for track in medium.get("tracks") or []:
            recording = track.get("recording") or {}
            if recording.get("id"):
                walk("recording", str(recording["id"]).lower(), str(recording.get("title") or recording["id"]),
                     recording.get("relations"))
    return sorted(found.values(), key=lambda l: (l["from"][:2], l["to"][:2], l["relation"], l["role"] or ""))


def release_fact(payload: dict) -> tuple[str | None, str | None, str | None]:
    """``(date, country, status)`` of a release lookup, each None when absent or malformed."""
    country = str(payload.get("country") or "").strip().upper()
    status = str(payload.get("status") or "").strip().lower()
    return (_date(payload.get("date")), country if len(country) == 2 and country.isalpha() else None,
            status if status in RELEASE_STATUSES else None)


# ------------------------------------------------------------------ writing

def write_release(db: sqlite3.Connection, release_id: int, payload: dict, *, now: float) -> int:
    """Store one release lookup; returns the number of new edges. Idempotent."""
    links = release_links(payload)
    observation_id, _ = repo.add_observation(
        db, SOURCE, {"operation": OP_RELEASE, "mbid": str(payload["id"]).lower(),
                     "links": [[l["from"][:2], l["to"][:2], l["relation"], l["role"], l["begin"], l["end"]] for l in links]},
        fetched_at=now, entity_hint=str(payload["id"]).lower())
    created = 0
    for link in links:
        from_id = repo.upsert_entity(db, link["from"][0], link["from"][2], mbid=link["from"][1])[0]
        to_id = repo.upsert_entity(db, link["to"][0], link["to"][2], mbid=link["to"][1])[0]
        if from_id == to_id:
            continue
        _, new = repo.add_edge(
            db, from_id, to_id, link["relation"], role=link["role"], evidence_class="source_explicit",
            match_quality="exact_mbid", source=SOURCE, observation_id=observation_id,
            source_url=f"https://musicbrainz.org/{link['from'][0].replace('_', '-')}/{link['from'][1]}",
            valid_from=link["begin"], valid_to=link["end"])
        created += int(new)
    date, country, status = release_fact(payload)
    if date or country or status:
        with db:
            db.execute("INSERT INTO release_facts (entity_id, date, country, status) VALUES (?, ?, ?, ?) "
                       "ON CONFLICT (entity_id) DO NOTHING", (release_id, date, country, status))
    return created


def write_life_span(db: sqlite3.Connection, entity_id: int, artist: dict) -> bool:
    span = artist.get("life-span") or {}
    begin, end, ended = _date(span.get("begin")), _date(span.get("end")), bool(span.get("ended"))
    if not (begin or end or ended):
        return False
    with db:
        db.execute("INSERT INTO artist_life_span (entity_id, begin_date, end_date, ended) VALUES (?, ?, ?, ?) "
                   "ON CONFLICT (entity_id) DO NOTHING", (entity_id, begin, end, int(ended)))
    return True


def absorb_api_edges(db: sqlite3.Connection) -> int:
    """Remove API edges that a loaded dump now states identically (same ends, relation and role)."""
    with db:
        return db.execute(
            "DELETE FROM edges WHERE source = ? AND EXISTS (SELECT 1 FROM edges d WHERE d.source = ? "
            "AND d.from_id = edges.from_id AND d.to_id = edges.to_id AND d.relation = edges.relation "
            "AND COALESCE(d.role, '') = COALESCE(edges.role, ''))", (SOURCE, DUMP_SOURCE)).rowcount


# ------------------------------------------------------------------ the job

def run_api_fill(
    db: sqlite3.Connection,
    *,
    fetch: Fetch | None = None,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    require_slice: bool = True,
    only: frozenset[str] | None = None,
    clock: Callable[[], float] = time.time,
) -> runner.RunResult:
    """Fill what is missing for owned entities, within ``max_requests``; safe to repeat.

    ``only`` (lowercase MBIDs) limits the run to those entities, so a caller that knows which
    albums are new spends no requests on the rest of the library.
    """
    paced = fetch if isinstance(fetch, Paced) else Paced(fetch or http_fetch)

    def work(ctx: runner.JobContext) -> bool:
        result = FillResult()
        if require_slice and not slice_loaded(db):
            result.stopped = "no_slice"
            ctx.checkpoint(result.summary())
            return True
        def wanted(rows):
            return rows if only is None else [r for r in rows if r[1] in only]

        artists, releases = wanted(pending_artists(db, clock())), wanted(pending_releases(db, clock()))
        failures = 0  # consecutive failed requests

        def spent() -> bool:
            return paced.requests >= max_requests or failures >= MAX_FAILURES_IN_A_ROW or not ctx.has_budget()

        def record_failure(operation: str, mbids) -> None:
            nonlocal failures
            failures += 1
            result.failures += 1
            for mbid in mbids:
                source_state.record_outcome(db, SOURCE, operation, mbid, "error", now=clock())

        for start in range(0, len(artists), ARTIST_BATCH):
            if spent():
                break
            chunk = {mbid: entity_id for entity_id, mbid in artists[start:start + ARTIST_BATCH]}
            try:
                body = paced(BASE + "artist?" + urlencode(
                    {"query": "arid:(" + " OR ".join(chunk) + ")", "fmt": "json", "limit": 100}))
            except ApiError:
                record_failure(OP_ARTISTS, chunk)
                continue
            failures = 0
            returned = {str(a.get("id", "")).lower(): a for a in body.get("artists") or []}
            for mbid, entity_id in chunk.items():
                artist = returned.get(mbid)
                if artist is None:
                    result.artists_absent += 1
                    source_state.record_outcome(db, SOURCE, OP_ARTISTS, mbid, "not_found", now=clock(), ttl=REFRESH_TTL)
                    continue
                result.artists_filled += int(write_life_span(db, entity_id, artist))
                source_state.record_outcome(db, SOURCE, OP_ARTISTS, mbid, "ok", now=clock(), ttl=REFRESH_TTL)
            ctx.checkpoint(result.summary(), items=len(chunk))

        for entity_id, mbid in releases:
            if spent():
                break
            try:
                body = paced(BASE + f"release/{mbid}?" + urlencode({"inc": RELEASE_INC, "fmt": "json"}, safe="+"))
            except ApiError as exc:
                if exc.status == 404:
                    failures = 0
                    result.releases_absent += 1
                    source_state.record_outcome(db, SOURCE, OP_RELEASE, mbid, "not_found", now=clock(), ttl=REFRESH_TTL)
                else:
                    record_failure(OP_RELEASE, [mbid])
                continue
            failures = 0
            result.edges_created += write_release(db, entity_id, body, now=clock())
            result.releases_filled += 1
            source_state.record_outcome(db, SOURCE, OP_RELEASE, mbid, "ok", now=clock(), ttl=REFRESH_TTL)
            ctx.checkpoint(result.summary(), items=1)

        result.requests = paced.requests
        result.pending_artists = len(wanted(pending_artists(db, clock())))
        result.pending_releases = len(wanted(pending_releases(db, clock())))
        if failures >= MAX_FAILURES_IN_A_ROW:
            result.stopped = "failures"
        elif paced.requests >= max_requests and (result.pending_artists or result.pending_releases):
            result.stopped = "request_budget"
        ctx.checkpoint(result.summary())
        return True

    return runner.run_job(db, JOB, work, clock=clock)
