"""Small persistent JSON cache used by metadata/discovery services."""
import json
import sqlite3
import time


class MetadataCache:
    """SQLite-backed TTL cache with deliberately non-fatal storage failures."""

    def __init__(self, database_path, clock=time.time):
        self.database_path = database_path
        self._clock = clock

    def get(self, key, ttl_seconds):
        """Return cached JSON when present and fresh; cache errors are misses."""
        try:
            with sqlite3.connect(self.database_path, timeout=5) as db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_cache (
                        cache_key TEXT PRIMARY KEY,
                        value_json TEXT NOT NULL,
                        cached_at REAL NOT NULL
                    )
                """)
                row = db.execute(
                    "SELECT value_json, cached_at FROM metadata_cache "
                    "WHERE cache_key = ?",
                    (key,),
                ).fetchone()

            if row is None or self._clock() - row[1] > ttl_seconds:
                return None
            return json.loads(row[0])
        except (sqlite3.Error, ValueError, TypeError):
            # A cache problem must never prevent recommendations from working.
            return None

    def set(self, key, value):
        """Store JSON-compatible metadata; cache errors are non-fatal."""
        try:
            with sqlite3.connect(self.database_path, timeout=5) as db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS metadata_cache (
                        cache_key TEXT PRIMARY KEY,
                        value_json TEXT NOT NULL,
                        cached_at REAL NOT NULL
                    )
                """)
                db.execute(
                    "INSERT OR REPLACE INTO metadata_cache "
                    "(cache_key, value_json, cached_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value, ensure_ascii=False), self._clock()),
                )
        except (sqlite3.Error, TypeError, ValueError):
            pass
