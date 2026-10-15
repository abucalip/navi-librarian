"""Dependency-injected persistence for acquisition job state.

The legacy server supplies its existing schema initializer, database path,
identity normalization, and clock. This module intentionally owns only the
authoritative acquisition-row read/write mechanics; status transition locking
and secondary feedback projections remain with the server adapters.
"""
from __future__ import annotations

import json
import sqlite3


def save_job(artist, album, status, details=None, *, candidate=None, settings=None, services):
    """Insert/update one acquisition row while preserving saved metadata semantics."""
    init = services["init"]
    db_path = services["db_path"]
    music_key = services["music_key"]
    clock = services["clock"]
    init()
    now = clock()
    artist_key, album_key = music_key(artist), music_key(album)
    if not artist_key or not album_key:
        raise ValueError("artist and album are required")
    details = details or {}
    with sqlite3.connect(db_path, timeout=10) as db:
        if not details.get("quality_summary"):
            previous = db.execute(
                "SELECT details_json FROM discovery_acquisitions "
                "WHERE artist_key=? AND album_key=?",
                (artist_key, album_key),
            ).fetchone()
            if previous:
                try:
                    previous_details = json.loads(previous[0] or "{}")
                except (ValueError, TypeError):
                    previous_details = {}
                previous_quality = previous_details.get("quality_summary")
                if previous_quality:
                    details = {**details, "quality_summary": previous_quality}
        db.execute(
            "INSERT INTO discovery_acquisitions "
            "(artist_key, album_key, artist, album, status, details_json, candidate_json, "
            "settings_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(artist_key, album_key) DO UPDATE SET "
            "artist=excluded.artist, album=excluded.album, status=excluded.status, "
            "details_json=excluded.details_json, "
            "candidate_json=CASE WHEN excluded.candidate_json='{}' THEN discovery_acquisitions.candidate_json ELSE excluded.candidate_json END, "
            "settings_json=CASE WHEN excluded.settings_json='{}' THEN discovery_acquisitions.settings_json ELSE excluded.settings_json END, "
            "updated_at=excluded.updated_at",
            (
                artist_key, album_key, artist.strip(), album.strip(), status,
                json.dumps({"status": status, "updated_at": now, **details}, ensure_ascii=False),
                json.dumps(candidate or {}, ensure_ascii=False),
                json.dumps(settings or {}, ensure_ascii=False), now, now,
            ),
        )
        db.commit()


def list_jobs(*, services):
    """Return decoded acquisition rows in most-recently-updated order."""
    services["init"]()
    with sqlite3.connect(services["db_path"], timeout=10) as db:
        rows = db.execute(
            "SELECT artist_key, album_key, artist, album, status, details_json, "
            "candidate_json, settings_json, created_at, updated_at "
            "FROM discovery_acquisitions ORDER BY updated_at DESC"
        ).fetchall()
    jobs = []
    for row in rows:
        try:
            details = json.loads(row[5] or "{}")
        except (ValueError, TypeError):
            details = {"status": row[4]}
        try:
            candidate = json.loads(row[6] or "{}")
        except (ValueError, TypeError):
            candidate = {}
        try:
            settings = json.loads(row[7] or "{}")
        except (ValueError, TypeError):
            settings = {}
        jobs.append({
            "artist_key": row[0], "album_key": row[1], "artist": row[2],
            "album": row[3], "status": row[4], "details": details,
            "candidate": candidate, "settings": settings,
            "created_at": row[8], "updated_at": row[9],
        })
    return jobs


def reactivate_dismissed_job(artist, album, metadata=None, *, services):
    """Conditionally reopen a dismissed row and discard its stale source inventory.

    The caller owns transition-lock coordination. The conditional UPDATE is the
    authoritative guard: a missing or non-dismissed row is never reactivated.
    """
    init = services["init"]
    db_path = services["db_path"]
    music_key = services["music_key"]
    clock = services["clock"]
    init()
    artist_key, album_key = music_key(artist), music_key(album)
    now = clock()
    details = {
        "status": "retry_requested",
        "message": "Retry requested; searching for available sources.",
        "retry_requested_at": now,
        "metadata": metadata if isinstance(metadata, dict) else {},
    }
    with sqlite3.connect(db_path, timeout=10) as db:
        cursor = db.execute(
            "UPDATE discovery_acquisitions SET status=?, details_json=?, "
            "candidate_json='{}', settings_json='{}', updated_at=? "
            "WHERE artist_key=? AND album_key=? AND status='dismissed'",
            (
                "retry_requested", json.dumps(details, ensure_ascii=False), now,
                artist_key, album_key,
            ),
        )
        db.commit()
        return cursor.rowcount == 1
