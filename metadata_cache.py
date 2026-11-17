"""Small persistent JSON cache used by metadata/discovery services.

Efficiency P3: each thread keeps one connection, the table and index are created once per process, and the
file runs in WAL mode. A replaced or deleted file is noticed by its inode, so the next call reconnects and
recreates the table. ``prune`` removes rows older than a cutoff so the file stops growing.
"""
import json
import os
import sqlite3
import threading
import time

DAY_SECONDS = 24 * 60 * 60
# Rows older than this are pruned. It must stay above the longest TTL any caller passes (365 days, the year
# store in app/api/metadata.py); a test pins it.
PRUNE_AFTER_SECONDS = 400 * DAY_SECONDS
PRUNE_BATCH = 500

_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS metadata_cache (
        cache_key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        cached_at REAL NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS metadata_cache_cached_at ON metadata_cache (cached_at)",
)


def _file_identity(path):
    try:
        status = os.stat(path)
    except OSError:
        return None
    return (status.st_dev, status.st_ino)


def _close_quietly(conn):
    try:
        conn.close()
    except sqlite3.Error:
        pass


class MetadataCache:
    """SQLite-backed TTL cache with deliberately non-fatal storage failures."""

    def __init__(self, database_path, clock=time.time, connect=sqlite3.connect, timeout=5):
        self.database_path = database_path
        self._clock = clock
        self._connect = connect
        self._timeout = timeout
        self._local = threading.local()
        self._schema_lock = threading.Lock()
        self._schema_ready = None  # (pid, file identity) the schema was created for in this process

    def get(self, key, ttl_seconds):
        """Return cached JSON when present and fresh; cache errors are misses."""
        try:
            rows = self._execute(
                "SELECT value_json, cached_at FROM metadata_cache WHERE cache_key = ?",
                (key,),
            )
            if not rows or self._clock() - rows[0][1] > ttl_seconds:
                return None
            return json.loads(rows[0][0])
        except (sqlite3.Error, ValueError, TypeError):
            # A cache problem must never prevent recommendations from working.
            return None

    def get_with_age(self, key, max_age_seconds):
        """``(value, age_seconds)`` for a row no older than ``max_age_seconds``, else None.

        For stale-while-revalidate (efficiency K2): the caller decides whether the age is fresh or
        stale. ``get`` is unchanged. Cache errors are misses.
        """
        try:
            rows = self._execute(
                "SELECT value_json, cached_at FROM metadata_cache WHERE cache_key = ?",
                (key,),
            )
            if not rows:
                return None
            age = max(0.0, self._clock() - rows[0][1])
            if age > max_age_seconds:
                return None
            return json.loads(rows[0][0]), age
        except (sqlite3.Error, ValueError, TypeError):
            return None

    def set(self, key, value):
        """Store JSON-compatible metadata; cache errors are non-fatal."""
        try:
            self._execute(
                "INSERT OR REPLACE INTO metadata_cache (cache_key, value_json, cached_at) VALUES (?, ?, ?)",
                (key, json.dumps(value, ensure_ascii=False), self._clock()),
                write=True,
            )
        except (sqlite3.Error, TypeError, ValueError):
            pass

    def prune(self, older_than_seconds, batch=PRUNE_BATCH):
        """Delete rows cached more than ``older_than_seconds`` ago and return how many were removed.

        Deletes in batches, each committed, so a concurrent writer waits only briefly. Storage errors are
        raised, unlike ``get``/``set``, so the caller can log them.
        """
        cutoff = self._clock() - older_than_seconds
        removed = 0
        while True:
            deleted = self._execute(
                "DELETE FROM metadata_cache WHERE rowid IN "
                "(SELECT rowid FROM metadata_cache WHERE cached_at < ? LIMIT ?)",
                (cutoff, batch),
                write=True,
            )
            removed += deleted
            if deleted < batch:
                return removed

    def _execute(self, sql, params=(), write=False):
        conn = self._connection()
        try:
            cursor = conn.execute(sql, params)
            # Read every row now: a half-read statement would hold a WAL read snapshot open.
            rows = cursor.fetchall()
            if write:
                conn.commit()
                return cursor.rowcount
            return rows
        except sqlite3.Error as exc:
            self._local.conn = None
            _close_quietly(conn)
            if "no such table" in str(exc):
                self._schema_ready = None
            raise

    def _connection(self):
        local = self._local
        conn = getattr(local, "conn", None)
        identity = (os.getpid(), _file_identity(self.database_path))
        if conn is not None and local.identity == identity and identity[1] is not None:
            return conn
        if conn is not None:
            local.conn = None
            _close_quietly(conn)
        conn = self._connect(self.database_path, timeout=self._timeout)
        try:
            conn.execute("PRAGMA synchronous = NORMAL")
            identity = (os.getpid(), _file_identity(self.database_path))
            self._ensure_schema(conn, identity)
        except sqlite3.Error:
            _close_quietly(conn)
            raise
        local.conn = conn
        local.identity = identity
        return conn

    def _ensure_schema(self, conn, identity):
        with self._schema_lock:
            if self._schema_ready == identity:
                return
            for statement in _SCHEMA:
                conn.execute(statement)
            conn.execute("PRAGMA journal_mode = WAL").fetchall()
            conn.commit()
            self._schema_ready = identity
