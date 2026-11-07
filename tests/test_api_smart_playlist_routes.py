"""Route and body tests for the smart playlist routes (Server V2 Phase 6 slice 14)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.smart_playlists as routes
from app.api.dependencies import get_librarian
from intelligence.api.smart_playlists import songs_from_subsonic

NOW = 1_700_000_000.0
RID = "00000001-0000-4000-8000-00000005ba17"
RULES = {"name": "Rock", "match": "all", "order": "title", "rules": [{"field": "genre", "op": "contains", "value": "rock"}]}


class FakeLibrarian:
    def __init__(self, data_dir, songs=()):
        self.DATA_DIR = Path(data_dir)
        self.songs = list(songs)
        self.calls = []

    def api_call(self, method, **params):
        self.calls.append((method, params))
        offset = params["songOffset"]
        return {"searchResult3": {"song": self.songs[offset:offset + params["songCount"]]}}

    def items(self, value):
        return value or []


def song(n, genre="Rock"):
    return {"id": f"tr-{n:05d}", "title": f"T{n}", "genre": genre, "playCount": 1}


class SmartPlaylistRoutes(unittest.TestCase):
    def build(self, songs=()):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lib = FakeLibrarian(self.tmp.name, songs)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: self.lib
        patch = mock.patch.object(routes, "_now", lambda: NOW)
        patch.start()
        self.addCleanup(patch.stop)
        self.client = TestClient(api)
        return self.client

    def url(self, rid=RID):
        return f"/api/playlists/smart/{rid}"

    def test_empty_list(self):
        body = self.build().get("/api/playlists/smart").json()
        self.assertEqual((body["playlists"], body["total"]), ([], 0))

    def test_put_create_replay_replace_list_get_delete(self):
        c = self.build()
        self.assertEqual(c.put(self.url(), json=RULES).json()["status"], "created")
        replay = c.put(self.url(), json=RULES).json()
        self.assertEqual(replay["status"], "unchanged")
        self.assertEqual(replay["playlist"]["updated_at"], NOW)
        self.assertEqual(c.put(self.url(), json={**RULES, "name": "Rock 2"}).json()["status"], "replaced")
        self.assertEqual(c.get("/api/playlists/smart").json()["total"], 1)
        self.assertEqual(c.get(self.url()).json()["name"], "Rock 2")
        self.assertEqual(c.delete(self.url()).json(), {"deleted": True})
        self.assertEqual(c.get(self.url()).status_code, 404)
        self.assertEqual(c.delete(self.url()).status_code, 404)

    def test_bad_input_is_400_and_stores_nothing(self):
        c = self.build()
        r = c.put(self.url(), json={"name": "", "match": "some"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["status"], "rejected")
        self.assertEqual(c.get("/api/playlists/smart").json()["total"], 0)
        self.assertEqual(c.put("/api/playlists/smart/NOT-A-UUID", json=RULES).status_code, 400)
        self.assertEqual(c.get("/api/playlists/smart/nope").status_code, 400)
        self.assertEqual(c.put(self.url(), json=[1]).status_code, 422)

    def test_result_evaluates_on_request_and_reports_missing_data(self):
        c = self.build([song(1), song(2, "Jazz"), song(3)])
        c.put(self.url(), json={**RULES, "rules": RULES["rules"] + [{"field": "obscurity_band", "op": "equals", "value": "x"}]})
        body = c.get(self.url() + "/result").json()
        self.assertEqual(body["song_ids"], ["tr-00001", "tr-00003"])
        self.assertEqual((body["unfinished"], body["missing_data"]), ([1], ["obscurity_band"]))
        self.assertFalse(body["stored"])
        self.assertEqual(body["evaluated_at"], NOW)

    def test_result_pages_through_the_song_list(self):
        c = self.build([song(n) for n in range(routes.SONG_PAGE + 5)])
        c.put(self.url(), json=RULES)
        self.assertEqual(c.get(self.url() + "/result").json()["songs_considered"], routes.SONG_PAGE + 5)
        self.assertEqual([p["songOffset"] for _, p in self.lib.calls], [0, routes.SONG_PAGE])

    def test_result_for_unknown_id_is_404_without_calling_navidrome(self):
        c = self.build([song(1)])
        self.assertEqual(c.get(self.url() + "/result").status_code, 404)
        self.assertEqual(self.lib.calls, [])

    def test_navidrome_failure_is_502_with_fixed_message(self):
        c = self.build()
        c.put(self.url(), json=RULES)
        self.lib.api_call = mock.Mock(side_effect=RuntimeError("secret"))
        r = c.get(self.url() + "/result")
        self.assertEqual(r.status_code, 502)
        self.assertNotIn("secret", r.text)

    def test_subsonic_mapping_keeps_unknowns_absent(self):
        rows = songs_from_subsonic([
            {"id": "a", "suffix": "flac", "created": "2024-01-01T00:00:00Z", "played": "bad", "userRating": 4},
            {"title": "no id"}, "junk",
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["format"], rows[0]["rating"]), ("flac", 4))
        self.assertEqual(rows[0]["added_at"], 1704067200.0)
        self.assertNotIn("played_at", rows[0])
        self.assertNotIn("year", rows[0])


if __name__ == "__main__":
    unittest.main()
