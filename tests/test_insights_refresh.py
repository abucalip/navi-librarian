"""Runtime refresh of Forgotten Gems and the capabilities route (Server V2 Phase 3)."""
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.capabilities as cap_routes
import app.api.insights as insight_routes
from app.api.dependencies import get_librarian
from app.services import insights_refresh
from intelligence.insights import dismiss_gem, list_gem_cards, refresh_forgotten_gems
from intelligence.store import open_store

NOW = 1_800_000_000.0
OLD = "2020-01-01T00:00:00Z"


def albums(n=30, plays=9):
    return [{"id": f"a{i}", "name": f"Album {i}", "artist": "Artist", "playCount": plays, "played": OLD,
             "starred": "2020-01-01T00:00:00Z" if i % 2 else None} for i in range(n)]


class FakeLibrarian:
    def __init__(self, data_dir, pages):
        self.DATA_DIR = Path(data_dir)
        self.pages = pages
        self.calls = 0

    def api_call(self, method, **params):
        self.calls += 1
        off = params["offset"]
        return {"albumList2": {"album": self.pages[off:off + params["size"]]}}

    def items(self, value):
        return value or []

    def _listenbrainz_username(self):
        return "someone"


class Refresh(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = open_store(Path(self.tmp.name) / "x.sqlite3")
        self.addCleanup(self.db.close)

    def test_saves_cards_and_keeps_dismissals(self):
        result = refresh_forgotten_gems(self.db, albums(), now=NOW)
        self.assertEqual(result.state, "succeeded")
        cards = list_gem_cards(self.db, 50)
        self.assertTrue(cards)
        key = cards[0]["subject"]["key"]
        dismiss_gem(self.db, key)
        refresh_forgotten_gems(self.db, albums(), now=NOW)
        self.assertNotIn(key, {c["subject"]["key"] for c in list_gem_cards(self.db, 50)})

    def test_empty_library_fails_and_keeps_saved_cards(self):
        refresh_forgotten_gems(self.db, albums(), now=NOW)
        before = list_gem_cards(self.db, 50)
        result = refresh_forgotten_gems(self.db, [], now=NOW)
        self.assertEqual(result.state, "failed")
        self.assertEqual(list_gem_cards(self.db, 50), before)

    def test_sparse_history_saves_nothing_with_reason(self):
        result = refresh_forgotten_gems(self.db, albums(n=3), now=NOW)
        self.assertEqual(result.state, "succeeded")
        self.assertEqual(result.progress["empty_reason"], "sparse_history")
        self.assertEqual(list_gem_cards(self.db, 5), [])

    def test_albums_without_ids_are_skipped(self):
        result = refresh_forgotten_gems(self.db, albums() + [{"name": "no id"}], now=NOW)
        self.assertEqual(result.progress["albums"], 30)


class Wiring(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lib = FakeLibrarian(self.tmp.name, albums())

    def test_lens_off_touches_nothing(self):
        self.assertIsNone(insights_refresh.refresh_once(self.lib, {}))
        self.assertEqual(self.lib.calls, 0)
        self.assertFalse((Path(self.tmp.name) / insight_routes.STORE_FILE).exists())

    def test_lens_on_fills_store_and_capabilities_show_it(self):
        env = {insight_routes.LENSES_ENV: "forgotten_gem"}
        self.assertEqual(insights_refresh.refresh_once(self.lib, env), "succeeded")
        api = FastAPI()
        api.include_router(cap_routes.router)
        api.dependency_overrides[get_librarian] = lambda: self.lib
        r = TestClient(api).get("/api/capabilities")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["cache-control"], "no-store")
        body = r.json()
        self.assertTrue(body["features"]["insights"]["available"])
        self.assertFalse(body["features"]["library_health"]["available"])
        self.assertTrue(body["listenbrainz_connected"])
        self.assertEqual(body["contract_version"], 1)


if __name__ == "__main__":
    unittest.main()
