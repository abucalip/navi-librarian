"""SQLite persistence for discovery settings, isolated from application assembly."""
import json
import os
import sqlite3
import time
from pathlib import Path


class SettingsPersistence:
    """Persist settings and apply legacy migrations through injected path callbacks."""

    def __init__(self, database_path, defaults, get_music_dir, set_music_dir, clock=time.time):
        self.database_path = Path(database_path)
        self.defaults = dict(defaults)
        self.get_music_dir = get_music_dir
        self.set_music_dir = set_music_dir
        self.clock = clock

    def initialize(self):
        with sqlite3.connect(self.database_path, timeout=10) as db:
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

    def read(self):
        self.initialize()
        settings = dict(self.defaults)
        with sqlite3.connect(self.database_path, timeout=10) as db:
            rows = db.execute(
                "SELECT setting_key, value_json FROM discovery_settings"
            ).fetchall()
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

    def write(self, values):
        self.initialize()
        with sqlite3.connect(self.database_path, timeout=10) as db:
            for key, value in values.items():
                db.execute(
                    "INSERT OR REPLACE INTO discovery_settings "
                    "(setting_key, value_json, updated_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value, ensure_ascii=False), self.clock()),
                )
            db.commit()
