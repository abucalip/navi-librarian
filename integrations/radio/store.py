"""SQLite persistence for proxied stations and the log of songs that were heard."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

# A reconnect or a client that restarts the stream repeats the song it was on; the same title
# on the same station within this window extends the logged play instead of adding a second.
MERGE_WINDOW_SECONDS = 10 * 60

_SCHEMA = """
CREATE TABLE IF NOT EXISTS radio_stations (
    station_id TEXT PRIMARY KEY,
    token TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    original_url TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS radio_plays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id TEXT NOT NULL,
    station_name TEXT NOT NULL,
    raw_title TEXT NOT NULL,
    artist TEXT,
    title TEXT NOT NULL,
    album TEXT,
    year INTEGER,
    listened_seconds INTEGER NOT NULL,
    heard_at REAL NOT NULL,
    last_heard_at REAL NOT NULL,
    grabbed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS radio_plays_heard ON radio_plays (heard_at DESC);
"""


class RadioStore:
    def __init__(self, path: Path | str):
        self.path = str(path)
        with self._connect() as db:
            db.executescript(_SCHEMA)

    def _connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        return _Managed(db)

    # ---- stations ----------------------------------------------------------------------

    def get_station(self, station_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM radio_stations WHERE station_id = ?", (station_id,)).fetchone()
        return dict(row) if row else None

    def station_by_token(self, token: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM radio_stations WHERE token = ? AND enabled = 1", (token,)).fetchone()
        return dict(row) if row else None

    def save_station(self, station_id: str, token: str, name: str, original_url: str) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO radio_stations (station_id, token, name, original_url, enabled) "
                "VALUES (?, ?, ?, ?, 1) ON CONFLICT(station_id) DO UPDATE SET "
                "token = excluded.token, name = excluded.name, "
                "original_url = excluded.original_url, enabled = 1",
                (station_id, token, name, original_url))

    def disable_station(self, station_id: str) -> None:
        with self._connect() as db:
            db.execute("UPDATE radio_stations SET enabled = 0 WHERE station_id = ?", (station_id,))

    # ---- plays -------------------------------------------------------------------------

    def record_play(
        self, station_id: str, station_name: str, raw_title: str, artist: str | None,
        title: str, seconds: int, now: float | None = None,
    ) -> int:
        now = time.time() if now is None else now
        with self._connect() as db:
            last = db.execute(
                "SELECT id, raw_title, last_heard_at FROM radio_plays WHERE station_id = ? "
                "ORDER BY id DESC LIMIT 1", (station_id,)).fetchone()
            if last and last["raw_title"] == raw_title and now - last["last_heard_at"] <= MERGE_WINDOW_SECONDS:
                db.execute(
                    "UPDATE radio_plays SET listened_seconds = listened_seconds + ?, last_heard_at = ? "
                    "WHERE id = ?", (seconds, now, last["id"]))
                return last["id"]
            cursor = db.execute(
                "INSERT INTO radio_plays (station_id, station_name, raw_title, artist, title, "
                "listened_seconds, heard_at, last_heard_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (station_id, station_name, raw_title, artist, title, seconds, now - seconds, now))
            return cursor.lastrowid

    def list_plays(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM radio_plays ORDER BY heard_at DESC, id DESC LIMIT ?",
                              (limit,)).fetchall()
        return [dict(row) for row in rows]

    def get_play(self, play_id: int) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM radio_plays WHERE id = ?", (play_id,)).fetchone()
        return dict(row) if row else None

    def delete_play(self, play_id: int) -> bool:
        with self._connect() as db:
            return db.execute("DELETE FROM radio_plays WHERE id = ?", (play_id,)).rowcount > 0

    def set_album(self, play_id: int, album: str, year: int | None) -> None:
        with self._connect() as db:
            db.execute("UPDATE radio_plays SET album = ?, year = ? WHERE id = ?", (album, year, play_id))

    def mark_grabbed(self, play_id: int) -> None:
        with self._connect() as db:
            db.execute("UPDATE radio_plays SET grabbed = 1 WHERE id = ?", (play_id,))


class _Managed:
    """A connection that commits on success and always closes (sqlite3's own context manager
    only commits)."""

    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.db.commit()
            else:
                self.db.rollback()
        finally:
            self.db.close()
        return False
