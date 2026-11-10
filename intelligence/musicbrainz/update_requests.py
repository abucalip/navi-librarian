"""Manual "Request update" queue: add one artist or album to the knowledge store on demand.

The web process only records a request row (``update_requests``); the worker loop calls
:func:`process_next`, the single writer and MusicBrainz caller. A request ingests the album (or every
album of the artist, capped) from Navidrome, fills the new entities from MusicBrainz through
:mod:`.api_fill`, bumps the slice data version and rebuilds the artist's paths. One row per subject:
asking again after ``done`` or ``failed`` re-queues it; asking while queued or running changes nothing.
"""
from __future__ import annotations

import sqlite3
import time
from typing import Any, Callable, Mapping

from ..graph import paths
from ..ingest.navidrome import ingest_album
from ..store import generations, repositories as repo
from . import api_fill

SUBJECTS = ("artist", "album")
MBID_PREFIX = "mbid:"   # an artist request keyed by MusicBrainz id instead of the Navidrome id
MAX_ARTIST_ALBUMS = 50
MAX_REQUESTS = 40
WARM_MAX_SECONDS = 20.0


def status(db: sqlite3.Connection, subject: str, navidrome_id: str) -> dict[str, Any] | None:
    row = db.execute("SELECT state, requested_at, finished_at, message FROM update_requests "
                     "WHERE subject = ? AND navidrome_id = ?", (subject, navidrome_id)).fetchone()
    return dict(row) if row else None


def enqueue(db: sqlite3.Connection, subject: str, navidrome_id: str, *, now: float | None = None) -> dict[str, Any]:
    if subject not in SUBJECTS or not navidrome_id:
        raise ValueError("subject must be artist or album, with an id")
    now = time.time() if now is None else now
    current = status(db, subject, navidrome_id)
    if current and current["state"] in ("queued", "running"):
        return current
    db.execute("INSERT INTO update_requests (subject, navidrome_id, state, requested_at) VALUES (?, ?, 'queued', ?) "
               "ON CONFLICT (subject, navidrome_id) DO UPDATE SET state = 'queued', requested_at = excluded.requested_at, "
               "finished_at = NULL, message = NULL", (subject, navidrome_id, now))
    db.commit()
    return status(db, subject, navidrome_id)


def _finish(db, row_id: int, state: str, message: str, now: float) -> None:
    db.execute("UPDATE update_requests SET state = ?, message = ?, finished_at = ? WHERE id = ?",
               (state, message[:300], now, row_id))
    db.commit()


def recover_running(db: sqlite3.Connection) -> None:
    """A request left running by a crash goes back to the queue."""
    db.execute("UPDATE update_requests SET state = 'queued' WHERE state = 'running'")
    db.commit()


def process_next(
    db: sqlite3.Connection,
    *,
    get_album: Callable[[str], Mapping[str, Any] | None],
    get_artist: Callable[[str], Mapping[str, Any] | None],
    find_artist: Callable[[str], str | None] = lambda mbid: None,
    fetch: api_fill.Fetch | None = None,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any] | None:
    """Handle the oldest queued request; None when there is none."""
    row = db.execute("SELECT id, subject, navidrome_id FROM update_requests WHERE state = 'queued' "
                     "ORDER BY requested_at LIMIT 1").fetchone()
    if not row:
        return None
    db.execute("UPDATE update_requests SET state = 'running' WHERE id = ?", (row["id"],))
    db.commit()
    now = clock()
    try:
        message = _run(db, row["subject"], row["navidrome_id"], get_album, get_artist, find_artist, fetch, clock)
        state = "done"
    except Exception as exc:  # the message is the error type only; no paths or secrets
        state, message = "failed", f"Update failed ({type(exc).__name__})."
    if state == "done" and message.startswith("Nothing"):
        state = "failed"
    _finish(db, row["id"], state, message, now)
    return {"subject": row["subject"], "navidrome_id": row["navidrome_id"], "state": state, "message": message}


def _run(db, subject, navidrome_id, get_album, get_artist, find_artist, fetch, clock) -> str:
    now = clock()
    if navidrome_id.startswith(MBID_PREFIX):   # an artist asked for by MusicBrainz id: find it in the library
        navidrome_id = find_artist(navidrome_id[len(MBID_PREFIX):]) or ""
        if not navidrome_id:
            return "Nothing found: the library has no artist with this MusicBrainz id."
    artist: Mapping[str, Any] | None = None
    if subject == "artist":
        artist = get_artist(navidrome_id)
        if not artist:
            return "Nothing found: the library has no such artist."
        album_ids = [str(a["id"]) for a in (artist.get("album") or []) if a.get("id")][:MAX_ARTIST_ALBUMS]
    else:
        album_ids = [navidrome_id]
    mbids: set[str] = set()
    artist_ids: set[int] = set()
    ingested = 0
    for album_id in album_ids:
        album = get_album(album_id)
        if not album:
            continue
        album = dict(album)
        owner = artist
        if owner is None and album.get("artistId"):
            owner = get_artist(str(album["artistId"]))
        if owner and owner.get("musicBrainzId"):
            album["artists"] = [{"id": str(album.get("artistId") or navidrome_id), "name": owner.get("name", ""),
                                 "musicBrainzId": owner["musicBrainzId"]}]
        result = ingest_album(db, album, now=now, search=None)
        ingested += 1
        for entity_id in (result.release_entity_id, result.artist_entity_id):
            entity = repo.get_entity(db, entity_id) if entity_id else None
            if entity and entity.get("mbid"):
                mbids.add(entity["mbid"].lower())
        if result.artist_entity_id:
            artist_ids.add(result.artist_entity_id)
    if not ingested:
        return "Nothing found: the library has no such album."
    if not artist_ids:
        return "Nothing added: no MusicBrainz id on this artist yet."
    wrote = 0
    if mbids:
        run = api_fill.run_api_fill(db, fetch=fetch, max_requests=MAX_REQUESTS, only=frozenset(mbids), clock=clock)
        p = run.progress or {}
        wrote = (p.get("edges_created") or 0) + (p.get("releases_filled") or 0) + (p.get("artists_filled") or 0)
    if wrote:
        generations.bump_data_version(db, paths.SLICE_RESOURCE)
    started = time.monotonic()
    for entity_id in sorted(artist_ids):
        for kind in paths.PATH_KINDS:
            if time.monotonic() - started > WARM_MAX_SECONDS:
                break
            paths.cached_path(db, entity_id, kind)
    return f"Added {ingested} album{'s' if ingested != 1 else ''} to the store."
