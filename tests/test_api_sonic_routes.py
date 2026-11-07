"""Route tests for GET /api/sonic/similar and /api/sonic/path (Server V2 Phase 7, slice 2).

Covers each status code, count bounds, the one-hour cache (hit, expiry) and that errors are never cached.
"""
import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.sonic as routes
from app.api.dependencies import get_librarian
from intelligence.sonic.cache import TTLCache

NOT_FOUND = "Navidrome API error 70: data not found"
PLUGIN_FAILED = "Navidrome API error 0: plugin call failed"
REFUSED = "Navidrome API error 40: Wrong username or password for user owner-secret"


def song(i, title="Song", artist="A"):
    return {"id": i, "title": title, "artist": artist, "artistId": f"ar-{artist}", "album": "LP", "albumId": "al"}


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class FakeLibrarian:
    """Stands in for navidrome_server: records calls and answers like Navidrome's client does."""

    def __init__(self):
        self.songs = {"s": song("s", "Seed")}
        self.matches = [{"entry": song("1", "One", "B"), "similarity": 0.95}]
        self.fail = {}
        self.calls = []

    def api_call(self, method, **params):
        self.calls.append((method, params))
        if method in self.fail:
            raise RuntimeError(self.fail[method])
        if method == "getSong":
            if params["id"] not in self.songs:
                raise RuntimeError(NOT_FOUND)
            return {"song": self.songs[params["id"]]}
        return {"sonicMatch": self.matches}

    def sonic_calls(self):
        return [c for c in self.calls if c[0] != "getSong"]


class SonicRoutes(unittest.TestCase):
    def setUp(self):
        self.lib = FakeLibrarian()
        self.clock = Clock()
        patcher = mock.patch.object(routes, "CACHE", TTLCache(clock=self.clock))
        patcher.start()
        self.addCleanup(patcher.stop)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: self.lib
        self.client = TestClient(api)

    def similar(self, **params):
        return self.client.get("/api/sonic/similar", params={"id": "s", **params})

    def path(self, **params):
        return self.client.get("/api/sonic/path", params={"start": "s", "end": "e", **params})


class Similar(SonicRoutes):
    def test_ok_returns_the_payload(self):
        r = self.similar(count=5)
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["seed"]["navidrome_id"], "s")
        self.assertEqual([t["navidrome_id"] for t in body["tracks"]], ["1"])
        self.assertEqual(body["tracks"][0]["similarity"], 0.95)
        self.assertEqual(set(body), {"status", "seed", "tracks", "dropped"})

    def test_empty_is_200(self):
        self.lib.matches = []
        r = self.similar()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "empty")

    def test_unknown_song_is_404(self):
        r = self.similar(id="nope")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.json()["detail"], "Unknown song.")

    def test_sonic_not_found_is_404(self):
        self.lib.fail["getSonicSimilarTracks"] = NOT_FOUND
        self.assertEqual(self.similar().status_code, 404)

    def test_unavailable_is_502_with_plain_detail(self):
        self.lib.fail["getSonicSimilarTracks"] = PLUGIN_FAILED
        r = self.similar()
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["detail"], "Sonic similarity is unavailable.")

    def test_refused_login_is_502_and_does_not_leak_the_message(self):
        self.lib.fail["getSong"] = REFUSED
        r = self.similar()
        self.assertEqual(r.status_code, 502)
        self.assertNotIn("owner-secret", r.text)
        self.assertNotIn("Wrong username", r.text)

    def test_count_defaults_to_ten(self):
        self.similar()
        self.assertEqual(self.lib.sonic_calls()[0][1]["count"], 30)

    def test_count_bounds(self):
        for bad in ("0", "51", "-1", "abc"):
            self.assertEqual(self.similar(count=bad).status_code, 422, bad)
        for good in ("1", "50"):
            self.assertEqual(self.similar(count=good).status_code, 200, good)

    def test_id_is_required(self):
        self.assertEqual(self.client.get("/api/sonic/similar").status_code, 422)
        self.assertEqual(self.client.get("/api/sonic/similar", params={"id": ""}).status_code, 422)


class Path(SonicRoutes):
    def setUp(self):
        super().setUp()
        self.lib.songs["e"] = song("e", "End")
        self.lib.matches = [{"entry": song("s", "Seed"), "similarity": -1},
                            {"entry": song("m", "Middle", "M"), "similarity": 0.9},
                            {"entry": song("e", "End"), "similarity": 0.8}]

    def test_ok_returns_ordered_steps(self):
        r = self.path(count=3)
        self.assertEqual(r.status_code, 200, r.text)
        body = r.json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual([t["navidrome_id"] for t in body["tracks"]], ["s", "m", "e"])
        self.assertIsNone(body["tracks"][0]["similarity"])
        self.assertEqual(body["seed"]["navidrome_id"], "s")

    def test_empty_is_200(self):
        self.lib.matches = []
        r = self.path()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "empty")

    def test_same_start_and_end_is_400(self):
        r = self.client.get("/api/sonic/path", params={"start": "s", "end": "s"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(self.lib.calls, [])

    def test_unknown_song_is_404(self):
        self.lib.fail["findSonicPath"] = NOT_FOUND
        self.assertEqual(self.path().status_code, 404)

    def test_unavailable_is_502(self):
        self.lib.fail["findSonicPath"] = PLUGIN_FAILED
        r = self.path()
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["detail"], "Sonic similarity is unavailable.")

    def test_refused_login_is_502_and_does_not_leak(self):
        self.lib.fail["findSonicPath"] = REFUSED
        r = self.path()
        self.assertEqual(r.status_code, 502)
        self.assertNotIn("owner-secret", r.text)

    def test_count_bounds(self):
        for bad in ("1", "51", "0"):
            self.assertEqual(self.path(count=bad).status_code, 422, bad)
        for good in ("2", "50"):
            self.assertEqual(self.path(count=good).status_code, 200, good)

    def test_count_defaults_to_ten(self):
        self.path()
        self.assertEqual(self.lib.sonic_calls()[0][1]["count"], 10)

    def test_start_and_end_are_required(self):
        self.assertEqual(self.client.get("/api/sonic/path", params={"start": "s"}).status_code, 422)


class Caching(SonicRoutes):
    def test_repeat_request_is_served_from_cache(self):
        self.similar(count=5)
        self.similar(count=5)
        self.assertEqual(len(self.lib.sonic_calls()), 1)

    def test_cache_entry_expires_after_an_hour(self):
        self.similar()
        self.clock.now += 3599
        self.similar()
        self.assertEqual(len(self.lib.sonic_calls()), 1)
        self.clock.now += 1
        self.similar()
        self.assertEqual(len(self.lib.sonic_calls()), 2)

    def test_different_count_is_a_different_entry(self):
        self.similar(count=5)
        self.similar(count=6)
        self.assertEqual(len(self.lib.sonic_calls()), 2)

    def test_path_is_cached_by_both_ids_and_count(self):
        self.path(count=4)
        self.path(count=4)
        self.client.get("/api/sonic/path", params={"start": "e", "end": "s", "count": 4})
        self.assertEqual(len(self.lib.sonic_calls()), 2)

    def test_empty_answers_are_cached(self):
        self.lib.matches = []
        self.similar()
        self.similar()
        self.assertEqual(len(self.lib.sonic_calls()), 1)

    def test_errors_are_not_cached(self):
        self.lib.fail["getSonicSimilarTracks"] = PLUGIN_FAILED
        self.assertEqual(self.similar().status_code, 502)
        del self.lib.fail["getSonicSimilarTracks"]
        self.assertEqual(self.similar().status_code, 200)
        self.assertEqual(len(self.lib.sonic_calls()), 2)

    def test_not_found_is_not_cached(self):
        self.similar(id="nope")
        self.lib.songs["nope"] = song("nope")
        self.assertEqual(self.similar(id="nope").status_code, 200)

    def test_path_errors_are_not_cached(self):
        self.lib.fail["findSonicPath"] = NOT_FOUND
        self.assertEqual(self.path().status_code, 404)
        del self.lib.fail["findSonicPath"]
        self.assertEqual(self.path().status_code, 200)

    def test_bad_request_is_not_cached(self):
        self.client.get("/api/sonic/path", params={"start": "s", "end": "s"})
        self.client.get("/api/sonic/path", params={"start": "s", "end": "s"})
        self.assertEqual(self.lib.calls, [])


if __name__ == "__main__":
    unittest.main()
