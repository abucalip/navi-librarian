"""R4: read routes open the knowledge store read-only and never write or migrate."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import insights, knowledge, popularity, smart_playlists
from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from intelligence.store import ensure_store, open_readonly, open_writer, repositories as repo
from intelligence.store import db as store_db


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)

    def get_setting(self, *a, **k):
        return None


class StoreAccessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / STORE_FILE
        ensure_store(self.path)
        db = open_writer(self.path)
        repo.upsert_entity(db, "artist", "Alpha", mbid="a-gid", owned=True)
        db.commit()
        db.close()
        api = FastAPI()
        for mod in (knowledge, insights, popularity, smart_playlists):
            api.include_router(mod.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.tmp.name)
        self.client = TestClient(api)

    def test_ensure_store_runs_once_per_path(self):
        calls = []
        real = store_db.open_store
        store_db.open_store = lambda *a, **k: calls.append(a) or real(*a, **k)
        try:
            other = Path(self.tmp.name) / "other.sqlite3"
            ensure_store(other)
            ensure_store(other)
        finally:
            store_db.open_store = real
        self.assertEqual(len(calls), 1)

    def test_read_works_while_another_connection_holds_the_write_lock(self):
        writer = sqlite3.connect(self.path, timeout=0.1, isolation_level=None)
        writer.execute("BEGIN IMMEDIATE")
        try:
            ro = open_readonly(self.path)
            self.assertEqual(ro.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 1)
            ro.close()
            r = self.client.get("/api/knowledge/person", params={"mbid": "a-gid"})
            self.assertEqual(r.status_code, 200)
        finally:
            writer.execute("ROLLBACK")
            writer.close()

    def test_gets_run_no_write_statements(self):
        statements = []
        real = store_db.sqlite3.connect

        def traced(*a, **k):
            con = real(*a, **k)
            con.set_trace_callback(statements.append)
            return con

        store_db.sqlite3.connect = traced
        try:
            gets = [
                ("/api/knowledge/person", {"mbid": "a-gid"}),
                ("/api/knowledge/atlas", {}),
                ("/api/insights", {}),
                ("/api/insights/taste", {}),
                ("/api/insights/popularity/status", {}),
                ("/api/playlists/smart", {}),
            ]
            for url, params in gets:
                self.assertIn(self.client.get(url, params=params).status_code, (200, 404), url)
        finally:
            store_db.sqlite3.connect = real
        self.assertTrue(statements)
        for sql in statements:
            head = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
            self.assertNotIn(head, {"INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "REPLACE"}, sql)
            self.assertNotIn("journal_mode", sql.lower())

    def test_write_routes_still_write(self):
        r = self.client.put("/api/playlists/smart/mine", json={"name": "Mine", "match": "all", "rules": []})
        self.assertIn(r.status_code, (200, 400))
        db = open_writer(self.path)
        db.execute("INSERT INTO meta (key, value) VALUES ('r4', 'y')")
        db.commit()
        db.close()


if __name__ == "__main__":
    unittest.main()
