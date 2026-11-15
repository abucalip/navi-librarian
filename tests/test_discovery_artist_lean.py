"""Star Operation S2b: More like this / Less like this on an artist."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import discovery as routes
from app.api.dependencies import get_librarian
from discovery import artist_lean
from discovery.allocation_contract import AllocationCandidate, OwnershipStatus
from recommendation.music_key import music_key
from recommendation_feedback import (
    ARTIST_DISMISS_PENALTY, NEGATIVE_EXPIRY_SECONDS, POSITIVE_EXPIRY_SECONDS, SAVE_ARTIST_BOOST,
    SAVE_SEED_WEIGHT, apply_feedback_signal, combined_seed_genres, combined_seed_weights,
    lean_boost, lean_penalty, more_like_this_seed_weights, saved_artist_seed_weights,
)

DAY = 24 * 60 * 60
NOW = 1_000_000_000.0


def row(artist, status, age_days=0.0, genres=None):
    return {"scope": "artist_lean", "artist_key": music_key(artist), "album_key": "", "artist": artist,
            "album": "", "status": status, "metadata": {"genres": genres} if genres else {},
            "created_at": NOW - age_days * DAY, "updated_at": NOW - age_days * DAY}


def candidate(cid, artist):
    return AllocationCandidate(candidate_id=cid, artist_key=music_key(artist), album_key=cid, score=1.0,
                               category="adjacent", tags=("jazz",), ownership=OwnershipStatus.CLEAR)


def init_db(path):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE discovery_feedback (scope TEXT NOT NULL, artist_key TEXT NOT NULL,
            album_key TEXT NOT NULL DEFAULT '', artist TEXT NOT NULL, album TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL,
            updated_at REAL NOT NULL, PRIMARY KEY (scope, artist_key, album_key))""")


class SignalTests(unittest.TestCase):
    def test_more_seed_weight_matches_a_save_and_decays_and_expires(self):
        fresh = more_like_this_seed_weights([row("A", "more_like_this")], now=NOW)
        self.assertEqual(fresh, {music_key("A"): SAVE_SEED_WEIGHT})
        half = more_like_this_seed_weights([row("A", "more_like_this", age_days=30)], now=NOW)
        self.assertAlmostEqual(half[music_key("A")], SAVE_SEED_WEIGHT / 2)
        gone = more_like_this_seed_weights([row("A", "more_like_this", age_days=POSITIVE_EXPIRY_SECONDS / DAY + 1)], now=NOW)
        self.assertEqual(gone, {})

    def test_less_does_not_seed(self):
        self.assertEqual(more_like_this_seed_weights([row("A", "less_like_this")], now=NOW), {})

    def test_boost_and_penalty_sizes_decay_and_expiry(self):
        key = music_key("A")
        self.assertAlmostEqual(lean_boost(key, [row("A", "more_like_this")], now=NOW), SAVE_ARTIST_BOOST)
        self.assertAlmostEqual(lean_penalty(key, [row("A", "less_like_this")], now=NOW), ARTIST_DISMISS_PENALTY)
        self.assertAlmostEqual(lean_penalty(key, [row("A", "less_like_this", age_days=14)], now=NOW), ARTIST_DISMISS_PENALTY / 2)
        self.assertEqual(lean_penalty(key, [row("A", "less_like_this", age_days=NEGATIVE_EXPIRY_SECONDS / DAY + 1)], now=NOW), 0.0)
        self.assertEqual(lean_boost(key, [row("A", "less_like_this")], now=NOW), 0.0)
        self.assertEqual(lean_boost(music_key("B"), [row("A", "more_like_this")], now=NOW), 0.0)

    def test_ranking_boosts_more_demotes_less_and_never_removes(self):
        cands = [candidate("a", "Alpha"), candidate("b", "Beta"), candidate("c", "Gamma")]
        by_id = {c.candidate_id: {"primary_artist": n} for c, n in zip(cands, ("Alpha", "Beta", "Gamma"))}
        out = apply_feedback_signal(cands, by_id, [row("Alpha", "more_like_this"), row("Beta", "less_like_this")], now=NOW)
        scores = {c.candidate_id: c.score for c in out}
        self.assertGreater(scores["a"], 1.0)
        self.assertLess(scores["b"], 1.0)
        self.assertGreater(scores["b"], 0.0)
        self.assertEqual(scores["c"], 1.0)
        self.assertEqual(len(out), 3)

    def test_combined_seeds_take_larger_weight_and_metadata_genres(self):
        saved = {"scope": "album", "status": "for_me", "artist_key": music_key("A"), "album_key": "x",
                 "created_at": NOW - 60 * DAY, "metadata": {"genres": ["jazz"]}}
        rows = [saved, row("A", "more_like_this", genres=["bebop", "jazz"]), row("B", "more_like_this", genres=["dub"])]
        weights = combined_seed_weights(rows, now=NOW)
        self.assertEqual(weights[music_key("A")], SAVE_SEED_WEIGHT)
        self.assertGreater(weights[music_key("A")], saved_artist_seed_weights([saved], now=NOW)[music_key("A")])
        genres = combined_seed_genres(rows, now=NOW)
        self.assertEqual(genres[music_key("A")], ["jazz", "bebop"])
        self.assertEqual(genres[music_key("B")], ["dub"])

    def test_old_clients_with_no_lean_rows_are_unaffected(self):
        cands = [candidate("a", "Alpha")]
        by_id = {"a": {"primary_artist": "Alpha"}}
        dismiss = {"scope": "artist", "artist_key": music_key("Zed"), "album_key": "", "status": "not_for_me_artist",
                   "updated_at": NOW}
        self.assertEqual(apply_feedback_signal(cands, by_id, [dismiss], now=NOW), cands)
        self.assertEqual(combined_seed_weights([dismiss], now=NOW), {})


class StoreTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / "d.sqlite3")
        init_db(self.db)

    def test_set_replaces_other_lean_and_keeps_artist_dismissal_row(self):
        with sqlite3.connect(self.db) as db:
            db.execute("INSERT INTO discovery_feedback VALUES ('artist', ?, '', 'Alpha', '', 'not_for_me_artist', '{}', 1, 1)",
                       (music_key("Alpha"),))
        artist_lean.set_lean(self.db, "Alpha", "more", music_key)
        artist_lean.set_lean(self.db, " Alpha ", "less", music_key)
        self.assertEqual([(r["artist"], r["lean"]) for r in artist_lean.list_leans(self.db)], [("Alpha", "less")])
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM discovery_feedback WHERE scope='artist'").fetchone()[0], 1)

    def test_metadata_is_filtered(self):
        self.assertEqual(artist_lean.clean_metadata({"genres": ["Jazz", 3, " "], "lens": "deep_cuts", "x": 1}),
                         {"genres": ["Jazz"], "lens": "deep_cuts"})
        self.assertEqual(artist_lean.clean_metadata("nope"), {})

    def test_clear_and_validation(self):
        artist_lean.set_lean(self.db, "Alpha", "more", music_key)
        self.assertTrue(artist_lean.clear_lean(self.db, "alpha", music_key))
        self.assertFalse(artist_lean.clear_lean(self.db, "alpha", music_key))
        with self.assertRaises(ValueError):
            artist_lean.set_lean(self.db, "Alpha", "sideways", music_key)
        with self.assertRaises(ValueError):
            artist_lean.set_lean(self.db, " ", "more", music_key)


class FakeLibrarian:
    def __init__(self, path):
        self.DISCOVERY_DB = path

    def _discovery_init(self):
        pass

    _music_key = staticmethod(music_key)


class RouteTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = str(Path(tmp.name) / "d.sqlite3")
        init_db(self.db)
        api = FastAPI()
        api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(self.db)
        self.client = TestClient(api)

    def test_set_list_clear_roundtrip(self):
        r = self.client.post("/api/discovery/artist-lean", json={"artist": "Alpha", "lean": "more", "metadata": {"genres": ["jazz"], "lens": "deep_cuts"}})
        self.assertEqual(r.json(), {"ok": True, "artist": "Alpha", "lean": "more"})
        self.client.post("/api/discovery/artist-lean", json={"artist": "Beta", "lean": "less"})
        listed = self.client.get("/api/discovery/artist-lean").json()["artists"]
        self.assertEqual({(a["artist"], a["lean"]) for a in listed}, {("Alpha", "more"), ("Beta", "less")})
        with sqlite3.connect(self.db) as db:
            meta = db.execute("SELECT metadata_json FROM discovery_feedback WHERE artist='Alpha'").fetchone()[0]
        self.assertEqual(json.loads(meta), {"genres": ["jazz"], "lens": "deep_cuts"})
        self.assertTrue(self.client.request("DELETE", "/api/discovery/artist-lean", json={"artist": "alpha"}).json()["removed"])
        self.assertEqual([a["artist"] for a in self.client.get("/api/discovery/artist-lean").json()["artists"]], ["Beta"])

    def test_validation(self):
        post = lambda body: self.client.post("/api/discovery/artist-lean", json=body).status_code
        self.assertEqual(post({"artist": " ", "lean": "more"}), 400)
        self.assertEqual(post({"artist": "A", "lean": "sideways"}), 400)
        self.assertEqual(post({"artist": "A"}), 400)
        self.assertEqual(self.client.request("DELETE", "/api/discovery/artist-lean", json={}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
