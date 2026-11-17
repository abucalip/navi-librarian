"""Runtime counters (efficiency M1): labels, redaction, gate and store feeds, route auth."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from app import main
from app.services import runtime_metrics as rm
from integrations import provider_gate
from intelligence.store import db as store_db


class CountersTests(unittest.TestCase):
    def setUp(self):
        rm.reset()
        self.addCleanup(rm.reset)

    def test_host_table_and_unknown_hosts(self):
        self.assertEqual(rm.provider_for_url("https://musicbrainz.org/ws/2/artist/abc?query=secret"), "musicbrainz")
        self.assertEqual(rm.provider_for_url("https://en.wikipedia.org/api/x"), "wikipedia")
        self.assertEqual(rm.provider_for_url("https://api.deezer.com/search"), "deezer")
        self.assertEqual(rm.provider_for_url("https://example.test/x"), "other")
        self.assertEqual(rm.provider_for_url("not a url"), "other")

    def test_client_counts_outcomes_without_urls(self):
        def handler(request):
            code = {"/ok": 200, "/gone": 404, "/slow": 429, "/boom": 500}.get(request.url.path)
            if request.url.path == "/timeout":
                raise httpx.ReadTimeout("t", request=request)
            return httpx.Response(code)
        client = rm.MeteredClient(transport=httpx.MockTransport(handler))
        for path in ("/ok", "/gone", "/slow", "/boom"):
            client.get("https://musicbrainz.org" + path + "?token=SECRET&mbid=1234")
        with self.assertRaises(httpx.ReadTimeout):
            client.get("https://musicbrainz.org/timeout")
        snap = rm.snapshot()
        row = snap["requests"]["musicbrainz"]
        self.assertEqual(row["count"], 5)
        self.assertEqual(row["outcomes"], {"ok": 1, "not_found": 1, "rate_limited": 1, "error": 1, "timeout": 1})
        text = json.dumps(snap)
        for leaked in ("SECRET", "1234", "/ok", "token"):
            self.assertNotIn(leaked, text)

    def test_install_counts_plain_httpx_callers_once(self):
        def handler(request):
            return httpx.Response(200)
        self.addCleanup(setattr, httpx.Client, "send", rm._ORIGINAL_SEND)
        self.addCleanup(setattr, httpx.AsyncClient, "send", rm._ORIGINAL_ASEND)
        rm.count_all_httpx()
        rm.count_all_httpx()
        with httpx.Client(transport=httpx.MockTransport(handler)) as plain:
            plain.get("https://api.deezer.com/x?q=SECRET")
        with rm.MeteredClient(transport=httpx.MockTransport(handler)) as metered:
            metered.get("https://api.deezer.com/y")
        import asyncio

        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
                await c.get("https://last.fm/z")
        asyncio.run(run())
        snap = rm.snapshot()["requests"]
        self.assertEqual(snap["deezer"]["count"], 2)
        self.assertEqual(snap["lastfm"]["count"], 1)
        self.assertNotIn("SECRET", json.dumps(snap))

    def test_install_counts_urllib_callers(self):
        import io
        import urllib.error
        import urllib.request
        self.addCleanup(setattr, urllib.request.OpenerDirector, "open", rm._ORIGINAL_OPEN)
        outcomes = iter([io.BytesIO(b"x"), urllib.error.HTTPError("u", 404, "nf", {}, None),
                         urllib.error.URLError(TimeoutError("t")), urllib.error.URLError("dns")])

        def fake(self, fullurl, *a, **k):
            item = next(outcomes)
            if isinstance(item, Exception):
                raise item
            item.status = 200
            return item
        with patch.object(rm, "_ORIGINAL_OPEN", fake):
            rm.count_all_httpx()
            self.addCleanup(rm.reset)
            for url in ("https://musicbrainz.org/ws/2/a?q=SECRET", "https://www.wikidata.org/x",
                        "https://coverartarchive.org/y", "https://example.test/z"):
                try:
                    urllib.request.urlopen(urllib.request.Request(url), timeout=1)
                except Exception:
                    pass
        snap = rm.snapshot()["requests"]
        self.assertEqual(snap["musicbrainz"]["outcomes"], {"ok": 1})
        self.assertEqual(snap["wikidata"]["outcomes"], {"not_found": 1})
        self.assertEqual(snap["coverartarchive"]["outcomes"], {"timeout": 1})
        self.assertEqual(snap["other"]["outcomes"], {"error": 1})
        self.assertNotIn("SECRET", json.dumps(snap))

    def test_statements_are_timed_by_verb_without_text_or_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "k.sqlite3"
            with patch.object(store_db, "_observer", rm.record_store):
                db = store_db.connect(path)
                db.execute("CREATE TABLE t (a TEXT)")
                db.execute("INSERT INTO t (a) VALUES (?)", ("SECRET-VALUE",))
                db.executemany("INSERT INTO t (a) VALUES (?)", [("x",), ("y",)])
                db.execute("SELECT a FROM t WHERE a = ?", ("SECRET-VALUE",)).fetchall()
                with self.assertRaises(Exception):
                    db.execute("SELECT * FROM missing_table")
                with self.assertLogs(rm.logger, "WARNING") as logs, patch.object(rm, "SLOW_STORE_SECONDS", -1):
                    db.execute("SELECT a FROM t")
                db.close()
        store = rm.snapshot()["store"]
        self.assertEqual(store["sql_insert"]["count"], 2)
        self.assertEqual(store["sql_select"]["count"], 3)
        self.assertIn("sql_other", store)
        self.assertIn("on t", logs.output[0])
        self.assertNotIn("SECRET", json.dumps(store) + "".join(logs.output))

    def test_gate_reports_waits_and_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            now = [1000.0]
            gate = provider_gate.ProviderGate(Path(tmp) / "g.sqlite3", clock=lambda: now[0],
                                              sleep=lambda s: now.__setitem__(0, now[0] + s), intervals={"musicbrainz": 1.1})
            self.addCleanup(gate.close)
            with patch.object(provider_gate, "_observer", rm.record_gate):
                self.assertTrue(gate.reserve("musicbrainz", 5))
                self.assertTrue(gate.reserve("musicbrainz", 5))
                self.assertFalse(gate.reserve("musicbrainz", 0))
        row = rm.snapshot()["gate"]["musicbrainz"]
        self.assertEqual((row["reservations"], row["refused"]), (2, 1))
        self.assertAlmostEqual(row["wait_seconds"], 1.1, places=3)

    def test_store_opens_are_counted_and_slow_and_locked_are_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "k.sqlite3"
            with patch.object(store_db, "_observer", rm.record_store):
                store_db.open_store(path).close()
                store_db.open_readonly(path).close()
                with self.assertLogs(rm.logger, "WARNING"):
                    rm.record_store("open_writer", 0.5)
                with self.assertLogs(rm.logger, "WARNING"):
                    rm.record_store("open_writer", 0.1, locked=True)
        store = rm.snapshot()["store"]
        self.assertEqual(store["open_store"]["count"], 1)
        self.assertEqual(store["open_readonly"]["count"], 1)
        self.assertEqual((store["open_writer"]["slow"], store["open_writer"]["locked"]), (1, 1))

    def test_worker_snapshot_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "k.sqlite3"
            db = store_db.open_store(path)
            self.assertIsNone(rm.load_worker_snapshot(db))
            rm.record_request("deezer", "ok", 0.1)
            rm.save_worker_snapshot(db, now=123.0)
            data = rm.load_worker_snapshot(db)
            db.close()
        self.assertEqual(data["written_at"], 123.0)
        self.assertEqual(data["requests"]["deezer"]["count"], 1)


class FakeLibrarian:
    def __init__(self, data_dir, settings):
        self.DATA_DIR = data_dir
        self.settings = settings

    def _discovery_settings_read(self):
        return dict(self.settings)

    def _discovery_settings_write(self, values):
        self.settings.update(values)


class RouteTests(unittest.TestCase):
    def test_requires_login_and_returns_both_processes(self):
        rm.reset()
        self.addCleanup(rm.reset)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        data_dir = Path(tmp.name)
        from app.api.insights import STORE_FILE
        db = store_db.open_store(data_dir / STORE_FILE)
        rm.record_request("deezer", "ok", 0.1)
        rm.save_worker_snapshot(db)
        from app import worker_schedule
        worker_schedule.record_run(db, "insights_refresh", 1234.5)
        db.close()
        librarian = FakeLibrarian(data_dir, {})
        import hashlib
        for item in (patch.object(main, "get_librarian", return_value=librarian),
                     patch.object(main, "_AUTH_SECRET", b"integration-test-signing-secret-32"),
                     patch.object(main, "_password_digest", side_effect=lambda p, s: hashlib.sha256((s + p).encode()).hexdigest())):
            item.start()
            self.addCleanup(item.stop)
        main.app.dependency_overrides[main.get_librarian] = lambda: librarian
        self.addCleanup(main.app.dependency_overrides.clear)
        from app.api.dependencies import get_librarian
        main.app.dependency_overrides[get_librarian] = lambda: librarian
        client = TestClient(main.app, follow_redirects=False)
        self.addCleanup(client.close)
        pw = "correct horse battery staple"
        client.post("/api/auth/setup", json={"username": "owner", "password": pw, "password_confirmation": pw})
        anonymous = TestClient(main.app, follow_redirects=False)
        self.addCleanup(anonymous.close)
        self.assertEqual(anonymous.get("/api/diagnostics/runtime").status_code, 401)
        body = client.get("/api/diagnostics/runtime")
        self.assertEqual(body.status_code, 200)
        data = body.json()
        self.assertEqual(data["web"]["requests"]["deezer"]["count"], 1)
        self.assertEqual(data["worker"]["requests"]["deezer"]["count"], 1)
        self.assertEqual(data["schedule"], {"insights_refresh": 1234.5})   # W1: each entry's last run


if __name__ == "__main__":
    unittest.main()
