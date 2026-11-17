"""SQLite persistence for discovery settings, isolated from application assembly.

Reads are cached per process. One long-lived read connection checks
``PRAGMA data_version`` on every ``read()``: SQLite changes that value when
any other connection, in this or another process, commits to the file, so a
write by the worker or the web process is seen on the next read. A local
``write()`` clears the cache directly, because a connection's own commits do
not change its ``data_version``. The read connection is reopened when the
file is replaced or the process changes, so a swapped-in file is never
shadowed by the old one.
"""
import copy
import json
import os
import sqlite3
import threading
import time
from pathlib import Path


class SettingsPersistence:
    """Persist settings and apply legacy migrations through injected path callbacks."""

    def __init__(self, database_path, defaults, get_music_dir, set_music_dir, clock=time.time,
                 connect=sqlite3.connect):
        self.database_path = Path(database_path)
        self.defaults = dict(defaults)
        self.get_music_dir = get_music_dir
        self.set_music_dir = set_music_dir
        self.clock = clock
        self._connect = connect
        # Re-entrant: a reload can run the legacy migration, which writes.
        self._lock = threading.RLock()
        self._reader = None
        self._reader_identity = None
        self._data_version = None
        self._cached = None

    def initialize(self):
        with self._connect(self.database_path, timeout=10) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS discovery_settings (
                    setting_key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            db.commit()
        # The database contains credentials; retain the existing restrictive mode.
        try:
            os.chmod(self.database_path, 0o600)
        except OSError:
            pass

    def close(self):
        """Close the cached read connection; the next read reopens it."""
        with self._lock:
            self._drop_reader()

    def read(self):
        with self._lock:
            try:
                reader = self._reader_connection()
                version = reader.execute("PRAGMA data_version").fetchone()[0]
                if self._cached is None or version != self._data_version:
                    rows = reader.execute(
                        "SELECT setting_key, value_json FROM discovery_settings"
                    ).fetchall()
                    settings = self._load(rows)
                    self._cached = settings
                    self._data_version = version
            except sqlite3.Error:
                self._drop_reader()
                raise
            # Callers may mutate the result, including nested lists.
            return copy.deepcopy(self._cached)

    def write(self, values):
        with self._lock:
            # Ensures the file and table exist (once per file and process).
            self._reader_connection()
            try:
                with self._connect(self.database_path, timeout=10) as db:
                    for key, value in values.items():
                        db.execute(
                            "INSERT OR REPLACE INTO discovery_settings "
                            "(setting_key, value_json, updated_at) VALUES (?, ?, ?)",
                            (key, json.dumps(value, ensure_ascii=False), self.clock()),
                        )
                    db.commit()
            finally:
                self._cached = None

    def _file_identity(self):
        try:
            status = os.stat(self.database_path)
        except OSError:
            return None
        return (os.getpid(), status.st_dev, status.st_ino)

    def _reader_connection(self):
        identity = self._file_identity()
        if self._reader is not None and identity is not None and identity == self._reader_identity:
            return self._reader
        self._drop_reader()
        self.initialize()
        self._reader = self._connect(
            self.database_path, timeout=10, check_same_thread=False, isolation_level=None,
        )
        self._reader_identity = self._file_identity()
        return self._reader

    def _drop_reader(self):
        reader = self._reader
        self._reader = None
        self._reader_identity = None
        self._data_version = None
        self._cached = None
        if reader is not None:
            try:
                reader.close()
            except sqlite3.Error:
                pass

    def _load(self, rows):
        """Decode rows over the defaults and apply the legacy migrations."""
        settings = dict(self.defaults)
        for key, value in rows:
            try:
                settings[key] = json.loads(value)
            except (ValueError, TypeError):
                continue

        configured_music_path = str(settings.get("music_library_path") or "").strip()
        if configured_music_path:
            candidate_music_path = Path(configured_music_path).expanduser()
            if candidate_music_path.is_absolute():
                self.set_music_dir(candidate_music_path)

        # Append supported quality tiers without disturbing the saved order.
        legacy_quality_tiers = {"mp3_320", "mp3_193_319", "mp3_192", "flac_cd"}
        saved_quality = settings.get("quality_priority")
        if isinstance(saved_quality, list):
            if len(saved_quality) == 4 and set(saved_quality) == legacy_quality_tiers:
                settings["quality_priority"] = [*saved_quality, "flac_16_44", "flac_hires"]
            elif len(saved_quality) == 5 and set(saved_quality) == legacy_quality_tiers | {"flac_16_44"}:
                settings["quality_priority"] = [*saved_quality, "flac_hires"]

        # Migrate known legacy defaults only when the configured destination exists.
        music_dir = self.get_music_dir()
        saved_path = str(settings.get("slskd_downloads_path") or "")
        legacy_paths = {
            str(music_dir.parent.parent / "downloads"),
            "/Volumes/media/downloads",
            "/media/downloads",
        }
        current_default = self.defaults["slskd_downloads_path"]
        if saved_path in legacy_paths and saved_path != current_default and Path(current_default).is_dir():
            settings["slskd_downloads_path"] = current_default
            self.write({"slskd_downloads_path": current_default})
        return settings
