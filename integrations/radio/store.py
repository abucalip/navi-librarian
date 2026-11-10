"""SQLite persistence for proxied stations and the log of songs that were heard."""
from __future__ import annotations

import json
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
    grabbed INTEGER NOT NULL DEFAULT 0,
    scrobbled INTEGER NOT NULL DEFAULT 0,
    loved INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS radio_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS radio_plays_heard ON radio_plays (heard_at DESC);
CREATE TABLE IF NOT EXISTS radio_station_prefs (
    station_id TEXT PRIMARY KEY,
    favourite INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS radio_logo_state (
    station_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    media_type TEXT,
    checked_at REAL NOT NULL,
    expires_at REAL
);
"""


# Columns added after the first release. A database made before them gets each one with ALTER
# TABLE; the change is additive, so an older image still opens the file.
_ADDED_PLAY_COLUMNS = {
    "scrobbled": "INTEGER NOT NULL DEFAULT 0",
    "loved": "INTEGER NOT NULL DEFAULT 0",
}


class RadioStore:
    def __init__(self, path: Path | str):
        self.path = str(path)
        with self._connect() as db:
            db.executescript(_SCHEMA)
            present = {row["name"] for row in db.execute("PRAGMA table_info(radio_plays)").fetchall()}
            for column, declaration in _ADDED_PLAY_COLUMNS.items():
                if column not in present:
                    db.execute(f"ALTER TABLE radio_plays ADD COLUMN {column} {declaration}")

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

    def enabled_stations(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM radio_stations WHERE enabled = 1").fetchall()
        return [dict(row) for row in rows]

    # ---- station preferences (favourite, tags) ----------------------------------------

    def station_prefs(self) -> dict[str, dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT station_id, favourite, tags FROM radio_station_prefs").fetchall()
        return {row["station_id"]: {"favourite": bool(row["favourite"]), "tags": json.loads(row["tags"])}
                for row in rows}

    def set_favourite(self, station_id: str, favourite: bool) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO radio_station_prefs (station_id, favourite) VALUES (?, ?) "
                "ON CONFLICT(station_id) DO UPDATE SET favourite = excluded.favourite",
                (station_id, 1 if favourite else 0))

    def set_tags(self, station_id: str, tags: list[str]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO radio_station_prefs (station_id, tags) VALUES (?, ?) "
                "ON CONFLICT(station_id) DO UPDATE SET tags = excluded.tags",
                (station_id, json.dumps(tags)))

    def last_played_map(self) -> dict[str, float]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT station_id, MAX(last_heard_at) AS last FROM radio_plays GROUP BY station_id").fetchall()
        return {row["station_id"]: row["last"] for row in rows}

    # ---- logo resolution state ---------------------------------------------------------

    def get_logo_state(self, station_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM radio_logo_state WHERE station_id = ?", (station_id,)).fetchone()
        return dict(row) if row else None

    def save_logo_state(self, station_id: str, source: str, status: str, media_type: str | None,
                        checked_at: float, expires_at: float | None) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO radio_logo_state (station_id, source, status, media_type, checked_at, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(station_id) DO UPDATE SET source = excluded.source, "
                "status = excluded.status, media_type = excluded.media_type, "
                "checked_at = excluded.checked_at, expires_at = excluded.expires_at",
                (station_id, source, status, media_type, checked_at, expires_at))

    def delete_logo_state(self, station_id: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM radio_logo_state WHERE station_id = ?", (station_id,))

    # ---- settings ----------------------------------------------------------------------

    def get_setting(self, key: str, default: str = "") -> str:
        with self._connect() as db:
            row = db.execute("SELECT value FROM radio_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as db:
            if value:
                db.execute("INSERT INTO radio_settings (key, value) VALUES (?, ?) "
                           "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
            else:
                db.execute("DELETE FROM radio_settings WHERE key = ?", (key,))

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

    def add_listened(self, play_id: int, seconds: int, now: float) -> None:
        """Extend a logged play by the seconds heard after it was logged (the threshold part)."""
        with self._connect() as db:
            db.execute(
                "UPDATE radio_plays SET listened_seconds = listened_seconds + ?, last_heard_at = ? "
                "WHERE id = ?", (seconds, now, play_id))

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

    def clear_plays(self) -> int:
        with self._connect() as db:
            return db.execute("DELETE FROM radio_plays").rowcount

    def set_album(self, play_id: int, album: str, year: int | None) -> None:
        with self._connect() as db:
            db.execute("UPDATE radio_plays SET album = ?, year = ? WHERE id = ?", (album, year, play_id))

    def mark_grabbed(self, play_id: int) -> None:
        with self._connect() as db:
            db.execute("UPDATE radio_plays SET grabbed = 1 WHERE id = ?", (play_id,))

    def claim_scrobble(self, play_id: int) -> bool:
        """Mark a play as scrobbled. True only for the call that made the change, so a play is
        scrobbled at most once even when the same song is logged again after a reconnect."""
        with self._connect() as db:
            return db.execute(
                "UPDATE radio_plays SET scrobbled = 1 WHERE id = ? AND scrobbled = 0", (play_id,)).rowcount > 0

    def set_loved(self, play_id: int) -> None:
        with self._connect() as db:
            db.execute("UPDATE radio_plays SET loved = 1 WHERE id = ?", (play_id,))


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
