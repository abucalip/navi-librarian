"""Connection, schema, prune and failure rules for the metadata cache (efficiency P3)."""
import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path

import metadata_cache
from metadata_cache import MetadataCache


class RecordingConnections:
    """Injected ``connect`` that records every statement each connection runs."""

    def __init__(self):
        self.connections = []
        self.statements = []

    def __call__(self, path, timeout=5):
        conn = sqlite3.connect(path, timeout=timeout)
        conn.set_trace_callback(self.statements.append)
        self.connections.append(conn)
        return conn

    def creates(self):
        return [s for s in self.statements if s.lstrip().upper().startswith("CREATE TABLE")]


class MetadataCacheLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "metadata.sqlite3"
        self.now = 1_000_000.0
        self.recorder = RecordingConnections()
        self.cache = MetadataCache(self.database, clock=lambda: self.now, connect=self.recorder)

    def test_prune_cutoff_is_longer_than_the_longest_ttl_in_use(self):
        year_store_ttl = 365 * 24 * 60 * 60  # app/api/metadata.py::_YEAR_STORE_TTL
        self.assertGreater(metadata_cache.PRUNE_AFTER_SECONDS, year_store_ttl)

    def test_table_is_created_once_per_process_across_threads(self):
        self.cache.set("first", {"n": 1})
        self.assertEqual(len(self.recorder.creates()), 1)

        def work():
            for i in range(20):
                self.cache.set(f"thread:{i}", i)
                self.cache.get(f"thread:{i}", 60)

        thread = threading.Thread(target=work)
        thread.start()
        thread.join()
        for i in range(20):
            self.cache.get("first", 60)
            self.cache.set(f"main:{i}", i)

        self.assertEqual(len(self.recorder.creates()), 1)

    def test_each_thread_keeps_its_own_connection(self):
        self.cache.get("a", 60)
        self.cache.get("b", 60)
        self.assertEqual(len(self.recorder.connections), 1)

        thread = threading.Thread(target=lambda: self.cache.get("c", 60))
        thread.start()
        thread.join()
        self.assertEqual(len(self.recorder.connections), 2)

    def test_database_is_in_wal_mode_with_an_index_on_cached_at(self):
        self.cache.set("seed", {})
        with sqlite3.connect(self.database) as db:
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'index'")}
        self.assertIn("metadata_cache_cached_at", names)

    def test_prune_removes_only_rows_older_than_the_cutoff(self):
        self.cache.set("old", {"v": 1})
        self.now += metadata_cache.PRUNE_AFTER_SECONDS + 10
        self.cache.set("fresh", {"v": 2})

        removed = self.cache.prune(metadata_cache.PRUNE_AFTER_SECONDS)

        self.assertEqual(removed, 1)
        self.assertEqual(self.cache.get("fresh", 10 ** 9), {"v": 2})
        with sqlite3.connect(self.database) as db:
            keys = [row[0] for row in db.execute("SELECT cache_key FROM metadata_cache")]
        self.assertEqual(keys, ["fresh"])

    def test_prune_deletes_in_batches_and_reports_the_total(self):
        for i in range(1_200):
            self.cache.set(f"old:{i}", i)
        self.now += 500 * 24 * 60 * 60
        self.cache.set("fresh", 1)

        removed = self.cache.prune(400 * 24 * 60 * 60, batch=500)

        self.assertEqual(removed, 1_200)
        self.assertEqual(self.cache.get("fresh", 10 ** 9), 1)

    def test_set_is_non_fatal_while_another_connection_holds_the_write_lock(self):
        self.cache.set("key", "before")
        busy = MetadataCache(self.database, clock=lambda: self.now, timeout=0.05)
        busy.get("warm", 60)  # create its schema before the lock is taken
        blocker = sqlite3.connect(self.database, isolation_level=None)
        self.addCleanup(blocker.close)
        blocker.execute("BEGIN IMMEDIATE")

        busy.set("key", "during")  # must not raise

        # WAL lets readers continue while the writer is blocked, so the old value is still served.
        self.assertEqual(busy.get("key", 60), "before")
        blocker.execute("ROLLBACK")
        busy.set("key", "after")
        self.assertEqual(busy.get("key", 60), "after")

    def test_garbage_file_is_a_miss_and_the_cache_recovers_when_it_is_replaced(self):
        self.database.write_bytes(b"not a database at all, " * 100)

        self.assertIsNone(self.cache.get("key", 60))
        self.cache.set("key", {"ok": True})  # must not raise

        os.remove(self.database)
        self.cache.set("key", {"ok": True})
        self.assertEqual(self.cache.get("key", 60), {"ok": True})

    def test_deleted_database_is_recreated_on_the_next_call(self):
        self.cache.set("gone", 1)
        for path in self.database.parent.glob(self.database.name + "*"):
            os.remove(path)

        self.assertIsNone(self.cache.get("gone", 60))
        self.cache.set("again", 2)
        self.assertEqual(self.cache.get("again", 60), 2)
        self.assertEqual(len(self.recorder.creates()), 2)


if __name__ == "__main__":
    unittest.main()
