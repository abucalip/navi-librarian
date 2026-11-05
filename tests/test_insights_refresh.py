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
        self.assertEqual(insights_refresh.refresh_once(self.lib, env), {"forgotten_gem": "succeeded"})
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


class ProviderWiring(unittest.TestCase):
    def test_provider_lenses_ingest_navidrome_then_use_the_budgeted_tick(self):
        from unittest import mock

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)

        class Lib(FakeLibrarian):
            def api_call(self, method, **params):
                self.calls += 1
                if method == "getArtists":
                    return {"artists": {"index": [{"artist": [
                        {"id": "ar1", "name": "A", "musicBrainzId": "11111111-1111-4111-8111-111111111111"},
                        {"id": "ar2", "name": "Various Artists", "musicBrainzId": "22222222-2222-4222-8222-222222222222"},
                        {"id": "ar3", "name": "No Mbid"}]}]}}
                if method == "getArtist":
                    return {"artist": {"album": [{"id": "al1"}]}}
                return {"album": {"id": "al1", "name": "X", "artistId": "ar1", "artist": "A",
                                  "musicBrainzId": "aaaaaaaa-0000-4000-8000-000000000001", "song": []}}

            def _discovery_settings_read(self):
                return {"listenbrainz_token": "tok"}

        lib = Lib(tmp.name, [])
        seen = []

        class Resp:
            status_code = 404

            def json(self):
                return {}

        def fake_get(url, **kw):
            seen.append((url, kw.get("headers", {})))
            return Resp()

        env = {insight_routes.LENSES_ENV: "blind_spot"}
        with mock.patch.object(insights_refresh.httpx, "get", fake_get), \
                mock.patch.object(insights_refresh.time, "sleep"):
            out = insights_refresh.refresh_once(lib, env)
        self.assertEqual(out, {"provider_lenses": "succeeded"})
        self.assertTrue(seen)
        self.assertTrue(all(h.get("User-Agent") for _, h in seen))
        self.assertTrue(all(("Authorization" in h) == ("listenbrainz" in u) for u, h in seen))
        self.assertLessEqual(len(seen), insights_refresh.PROVIDER_BUDGET)


class SeriesWiring(unittest.TestCase):
    def test_series_lens_is_a_provider_lens_and_turns_series_on(self):
        from unittest import mock
        self.assertIn("series_completion", insights_refresh.PROVIDER_LENSES)
        seen = {}

        def fake_refresh(db, **kw):
            seen.update(kw)
            return type("R", (), {"state": "succeeded"})()

        for lenses, expected in (("series_completion", True), ("blind_spot", False)):
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            with mock.patch.object(insights_refresh, "refresh_provider_lenses", fake_refresh):
                insights_refresh.refresh_once(FakeLibrarian(tmp.name, []), {insight_routes.LENSES_ENV: lenses})
            self.assertEqual(seen["series"], expected)
