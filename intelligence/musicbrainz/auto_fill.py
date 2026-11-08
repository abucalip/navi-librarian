"""Automatic enrichment of newly added owned albums (Server V2 Phase 4/7, carry-over "automatic API fill").

One poll, run every few seconds by ``app/services/library_enrich.py``, never by a request:

1. **Gate.** ``getScanStatus`` (about 300 bytes) is compared with the last seen ``lastScan`` and track
   count. Nothing changed and nothing is queued: the poll ends here. A running scan is waited out.
2. **Additions.** ``getAlbumList2 type=newest`` pages are read until one holds an album id already seen.
   Once a day, on the first poll after local midnight (and on the very first run), the full inventory is read instead; it also finds albums the
   incremental path missed, removes deleted albums from the seen set, and re-ingests albums that were
   seen without an MBID and have one now.
3. **Ingest.** Each new album is fetched with ``getAlbum`` (artist MBID from ``getArtist``) and recorded
   through :func:`intelligence.ingest.navidrome.ingest_album` (Navidrome only, no provider traffic).
4. **Coverage check.** A new release is *covered* when the loaded MusicBrainz slice already has an edge
   touching it; a new artist is covered when it already has a life span. Only the rest is queued.
5. **Fill.** :func:`api_fill.run_api_fill` runs restricted to the queued MBIDs, within its own request
   budget and pacing; it is only started when a queued entity is due, so idle polls leave no job rows.
6. **Publish to Paths.** When the fill wrote anything, the ``musicbrainz_slice`` data version is bumped
   (the counter a dump import bumps, which the Paths cache is keyed on) and the paths of the new albums'
   artists are rebuilt at once.

An album added without a release MBID tag is counted as ``no_mbid`` and remembered. In the daily pass it
gets the identity ladder's MusicBrainz search (:mod:`.release_search`) as a fallback, but only when at
least one of its tracks already carries an MBID, i.e. after it has been through MBID tagging such as
``find_missing_mbid.py`` (the server never runs that script or writes tags). The ladder accepts a result
only when exactly one release matches artist, title, track count and every duration. Each album is tried
at most once per 30 days and at most 25 albums per pass. Albums already in the library at the first run
are not part of this.

State lives in the store's ``meta`` table. The first run only records the current library as the baseline
(the existing library is covered by ``scripts/server_v2_mb_slice_import.py --ingest``).
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from typing import Any, Callable, Mapping

from ..graph import paths
from ..ingest.navidrome import REL_CREDITED_TO, ingest_album
from ..store import generations, repositories as repo, source_state
from . import api_fill
from .release_search import make_search

SEEN_KEY = "auto_fill.seen_albums"      # {navidrome album id: release MBID or ""}
MARKER_KEY = "auto_fill.scan_marker"    # {"lastScan", "count"} of the last fully handled scan
FULL_KEY = "auto_fill.last_full_at"
QUEUE_KEY = "auto_fill.queue"
LAST_KEY = "auto_fill.last_cycle"
RETRY_KEY = "auto_fill.retry_after"
UNTAGGED_KEY = "auto_fill.untagged"    # {album id: first seen} added without a release MBID
OP_SEARCH = "release_search"
SEARCH_TTL = 30 * 86400.0
SEARCH_ALBUMS_PER_PASS = 25  # albums given the search fallback per daily pass
NEWEST_PAGE = 20
MAX_NEWEST_PAGES = 25     # 500 albums; a bigger burst is finished by the daily full pass
MAX_NEW_ALBUMS = 25       # getAlbum calls per cycle; the rest wait for the next poll
MAX_REQUESTS = 40         # MusicBrainz requests per cycle (about 45 s at the 1.1 s pacing)
RETRY_SECONDS = 60.0
WARM_MAX_SECONDS = 20.0   # time allowed for rebuilding the new artists' paths


def _get(db: sqlite3.Connection, key: str, default: Any) -> Any:
    row = db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    try:
        return json.loads(row["value"]) if row else default
    except ValueError:
        return default


def _put(db: sqlite3.Connection, key: str, value: Any) -> None:
    with db:
        db.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
                   "ON CONFLICT (key) DO UPDATE SET value = excluded.value", (key, json.dumps(value, sort_keys=True)))


def _unfilled_releases(db: sqlite3.Connection, mbids) -> list[str]:
    """Queued releases the dump does not cover and the API has not yet answered for."""
    pending = {m for _, m in api_fill.pending_releases(db, float("inf"))}
    return [m for m in mbids if m in pending]


def _unfilled_artists(db: sqlite3.Connection, mbids) -> list[str]:
    pending = {m for _, m in api_fill.pending_artists(db, float("inf"))}
    return [m for m in mbids if m in pending]


def _credited_artists(db: sqlite3.Connection, release_mbids) -> set[int]:
    """Owned artists credited on the given releases (the starting points of the paths to rebuild)."""
    found: set[int] = set()
    for mbid in release_mbids:
        for row in db.execute(
                "SELECT e.to_id FROM edges e JOIN entities r ON r.id = e.from_id "
                "WHERE r.mbid = ? AND e.relation = ?", (mbid, REL_CREDITED_TO)):
            found.add(row["to_id"])
    return found


def _is_final(db: sqlite3.Connection, operation: str, mbid: str) -> bool:
    return source_state.status(db, api_fill.SOURCE, operation, mbid) in ("ok", "not_found")


def _due_queue(db, releases, artists, now):
    due = {m for _, m in api_fill.pending_releases(db, now)} | {m for _, m in api_fill.pending_artists(db, now)}
    return due & (set(releases) | set(artists))


def _search_sweep(db, summary, seen, untagged, releases, artists, touched_artists, get_album, get_artist, paced, now) -> None:
    """Daily pass: give the identity ladder's search to albums added without a release MBID.

    Only albums whose tracks already carry MBIDs qualify (they have been through MBID tagging, for
    example ``find_missing_mbid.py``); an album with no MBID anywhere keeps waiting for its tags. Each
    album is tried once per ``SEARCH_TTL`` and at most ``SEARCH_ALBUMS_PER_PASS`` per pass.
    """
    inner, failed = make_search(paced), []

    def search(ref):
        try:
            return inner(ref)
        except api_fill.ApiError:
            failed.append(ref)  # the ladder will swallow this as "deferred"; remember it was not a real miss
            raise
    for album_id in sorted(untagged, key=untagged.get):
        if summary["searched"] >= SEARCH_ALBUMS_PER_PASS:
            break
        state = source_state.get_state(db, api_fill.SOURCE, OP_SEARCH, album_id)
        if album_id not in seen or seen[album_id] or (
                state and state["next_refresh_at"] is not None and state["next_refresh_at"] > now):
            continue
        album = get_album(album_id)
        if not album or not any((song or {}).get("musicBrainzId") for song in album.get("song") or []):
            continue  # no track has been tagged yet
        summary["searched"] += 1
        album = dict(album)
        artist = get_artist(str(album.get("artistId") or "")) if album.get("artistId") else None
        if artist and artist.get("musicBrainzId"):
            album["artists"] = [{"id": album["artistId"], "name": artist.get("name", ""),
                                 "musicBrainzId": artist["musicBrainzId"]}]
        failed.clear()
        result = ingest_album(db, album, now=now, search=search)
        if failed:
            source_state.record_outcome(db, api_fill.SOURCE, OP_SEARCH, album_id, "error", now=now)
            continue
        entity = repo.get_entity(db, result.release_entity_id) if result.release_entity_id else None
        if entity and entity.get("mbid"):
            summary["resolved_by_search"] += 1
            seen[album_id] = entity["mbid"].lower()
            untagged.pop(album_id, None)
            releases.add(entity["mbid"].lower())
            if result.artist_entity_id:
                touched_artists.add(result.artist_entity_id)
            outcome = "ok"
        else:
            outcome = "not_found"
        source_state.record_outcome(db, api_fill.SOURCE, OP_SEARCH, album_id, outcome, now=now, ttl=SEARCH_TTL)


def run_cycle(
    db: sqlite3.Connection,
    *,
    scan_status: Callable[[], Mapping[str, Any]],
    newest: Callable[[int, int], list[Mapping[str, Any]]],
    full: Callable[[], list[Mapping[str, Any]]],
    get_album: Callable[[str], Mapping[str, Any] | None],
    get_artist: Callable[[str], Mapping[str, Any] | None],
    fetch: api_fill.Fetch | None = None,
    paced: api_fill.Paced | None = None,
    max_new: int = MAX_NEW_ALBUMS,
    max_requests: int = MAX_REQUESTS,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """One poll. Returns a small summary (counts only; no names, paths or secrets); ``{"idle": True}``
    when nothing needed doing.

    ``newest(offset, size)`` and ``full()`` return album stubs (``id``, ``artistId``, ``musicBrainzId``);
    ``get_album`` / ``get_artist`` return the Subsonic ``album`` / ``artist`` object or None.
    """
    now = clock()
    paced = paced or api_fill.Paced(fetch or api_fill.http_fetch)
    queue = _get(db, QUEUE_KEY, {"releases": [], "artists": []})
    releases, artists = set(queue["releases"]), set(queue["artists"])
    status = scan_status() or {}
    if status.get("scanning"):
        return {"idle": True, "scanning": True}
    marker = {"lastScan": status.get("lastScan"), "count": status.get("count")}
    seen_raw = _get(db, SEEN_KEY, None)
    last_full = _get(db, FULL_KEY, 0.0)
    do_full = seen_raw is None or datetime.fromtimestamp(now).date() > datetime.fromtimestamp(last_full).date()
    changed = marker != _get(db, MARKER_KEY, None) and now >= _get(db, RETRY_KEY, 0.0)
    fill_due = bool(_due_queue(db, releases, artists, now))
    if not (do_full or changed or fill_due):
        return {"idle": True}

    summary: dict[str, Any] = {"mode": "full" if do_full else "incremental", "new": 0, "ingested": 0,
                               "no_mbid": 0, "removed": 0, "queued_releases": 0, "queued_artists": 0,
                               "covered": 0, "filled": None, "paths_rebuilt": 0}
    seen: dict[str, str] = dict(seen_raw) if isinstance(seen_raw, dict) else {}
    fresh: list[Mapping[str, Any]] = []
    if do_full:
        everything = full()
        if seen_raw is None:                      # first run: baseline only
            seen = {str(a["id"]): str(a.get("musicBrainzId") or "") for a in everything if a.get("id")}
            summary["baseline"] = True
        else:
            now_ids = {str(a["id"]) for a in everything if a.get("id")}
            summary["removed"] = len(set(seen) - now_ids)
            seen = {k: v for k, v in seen.items() if k in now_ids}
            fresh = [a for a in everything if a.get("id") and (
                str(a["id"]) not in seen or (not seen[str(a["id"])] and a.get("musicBrainzId")))]
        _put(db, FULL_KEY, now)
    elif changed:
        for page in range(MAX_NEWEST_PAGES):
            stubs = newest(page * NEWEST_PAGE, NEWEST_PAGE)
            fresh += [a for a in stubs if a.get("id") and str(a["id"]) not in seen]
            if len(stubs) < NEWEST_PAGE or any(str(a.get("id")) in seen for a in stubs):
                break
    summary["new"] = len(fresh)

    touched_artists: set[int] = set()
    untagged: dict[str, float] = dict(_get(db, UNTAGGED_KEY, {}))
    artist_cache: dict[str, Mapping[str, Any] | None] = {}
    failed = False
    for stub in fresh[:max_new]:
        album = get_album(str(stub["id"]))
        if not album:
            failed = True
            continue
        album = dict(album)
        artist_id = str(stub.get("artistId") or album.get("artistId") or "")
        if artist_id not in artist_cache:
            artist_cache[artist_id] = get_artist(artist_id) if artist_id else None
        artist = artist_cache[artist_id]
        if artist and artist.get("musicBrainzId"):
            album["artists"] = [{"id": artist_id, "name": artist.get("name", ""),
                                 "musicBrainzId": artist["musicBrainzId"]}]
        result = ingest_album(db, album, now=now, search=None)
        summary["ingested"] += 1
        release_mbid = str(album.get("musicBrainzId") or stub.get("musicBrainzId") or "")
        seen[str(stub["id"])] = release_mbid
        if not release_mbid:
            summary["no_mbid"] += 1
            if not (seen_raw is None):
                untagged.setdefault(str(stub["id"]), now)
        else:
            untagged.pop(str(stub["id"]), None)
        for entity_id, bucket in ((result.release_entity_id, releases), (result.artist_entity_id, artists)):
            entity = repo.get_entity(db, entity_id) if entity_id else None
            if entity and entity.get("mbid"):
                bucket.add(entity["mbid"].lower())
        if result.artist_entity_id:
            touched_artists.add(result.artist_entity_id)
    summary["deferred"] = max(len(fresh) - max_new, 0)
    summary["searched"] = summary["resolved_by_search"] = 0
    if do_full and seen_raw is not None:
        _search_sweep(db, summary, seen, untagged, releases, artists, touched_artists, get_album, get_artist, paced, now)
    for gone in set(untagged) - set(seen):
        untagged.pop(gone)
    _put(db, SEEN_KEY, seen)
    _put(db, UNTAGGED_KEY, untagged)
    if failed or summary["deferred"]:
        _put(db, RETRY_KEY, now + RETRY_SECONDS)   # leave the marker: the next poll finds the rest
    else:
        _put(db, MARKER_KEY, marker)

    # Coverage check: drop what the loaded dump already answers, or the API already settled.
    open_releases = [m for m in _unfilled_releases(db, sorted(releases)) if not _is_final(db, api_fill.OP_RELEASE, m)]
    open_artists = [m for m in _unfilled_artists(db, sorted(artists)) if not _is_final(db, api_fill.OP_ARTISTS, m)]
    summary["covered"] = len(releases) - len(open_releases)
    summary["queued_releases"], summary["queued_artists"] = len(open_releases), len(open_artists)
    only = frozenset(open_releases) | frozenset(open_artists)

    if only and _due_queue(db, open_releases, open_artists, now):
        run = api_fill.run_api_fill(db, fetch=paced, max_requests=paced.requests + max_requests, only=only, clock=clock)
        progress = run.progress or {}
        summary["filled"] = {"state": run.state, **{k: progress.get(k) for k in (
            "requests", "releases_filled", "releases_absent", "artists_filled", "edges_created", "failures", "stopped")}}
        wrote = (progress.get("edges_created") or 0) + (progress.get("releases_filled") or 0) + (
            progress.get("artists_filled") or 0)
        if wrote:
            generations.bump_data_version(db, paths.SLICE_RESOURCE)
            ids_to_warm = touched_artists | _credited_artists(db, open_releases)
            started = time.monotonic()
            for entity_id in sorted(ids_to_warm):
                for kind in paths.PATH_KINDS:
                    if time.monotonic() - started > WARM_MAX_SECONDS:
                        break
                    paths.cached_path(db, entity_id, kind)
                    summary["paths_rebuilt"] += 1
        open_releases = [m for m in _unfilled_releases(db, open_releases) if not _is_final(db, api_fill.OP_RELEASE, m)]
        open_artists = [m for m in _unfilled_artists(db, open_artists) if not _is_final(db, api_fill.OP_ARTISTS, m)]
    _put(db, QUEUE_KEY, {"releases": open_releases, "artists": open_artists})
    _put(db, LAST_KEY, {**summary, "at": now})
    return summary
