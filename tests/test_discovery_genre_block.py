"""Star Operation S2a: block a genre (selection time, read time, API)."""
import json
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import discovery as routes
from app.api.dependencies import get_librarian
from discovery import genre_block
from discovery.allocation_contract import AllocationCandidate
from discovery.list_payload import build_cached_discovery_list_response, build_lens_list_response, dismissed_predicate
from recommendation.music_key import music_key

BLOCK = {"scope": "genre", "artist_key": music_key("Shoegaze"), "album_key": "", "artist": "Shoegaze",
         "album": "", "status": "blocked_genre"}


class FakeCandidate:
    def __init__(self, *tags):
        self.tags = tags


def init_db(path):
    import sqlite3
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE discovery_feedback (scope TEXT NOT NULL, artist_key TEXT NOT NULL,
            album_key TEXT NOT NULL DEFAULT '', artist TEXT NOT NULL, album TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL,
            updated_at REAL NOT NULL, PRIMARY KEY (scope, artist_key, album_key))""")


class SelectionTests(unittest.TestCase):
    def test_keys_only_from_blocked_genre_rows(self):
        rows = [BLOCK, {"scope": "artist", "artist_key": "x", "status": "not_for_me_artist"}]
        self.assertEqual(genre_block.blocked_genre_keys(rows, music_key), frozenset({"shoegaze"}))

    def test_drops_candidates_with_a_blocked_genre_and_keeps_the_rest(self):
        keep, drop = FakeCandidate("jazz"), FakeCandidate("Jazz", "Shoegaze")
        blocked = genre_block.blocked_genre_keys([BLOCK], music_key)
        self.assertEqual(genre_block.drop_blocked_candidates([keep, drop], blocked, music_key), [keep])

    def test_no_block_changes_nothing(self):
        cands = [FakeCandidate("shoegaze")]
        self.assertEqual(genre_block.drop_blocked_candidates(cands, frozenset(), music_key), cands)

    def test_prepare_ranking_inputs_drops_blocked_genre(self):
        from discovery.cooldown import prepare_ranking_inputs
        c1 = AllocationCandidate(candidate_id="a", artist_key="a", album_key="a", score=1.0,
                                 category="adjacent", tags=("shoegaze",), ownership=_clear())
        c2 = AllocationCandidate(candidate_id="b", artist_key="b", album_key="b", score=1.0,
                                 category="adjacent", tags=("jazz",), ownership=_clear())
        with tempfile.TemporaryDirectory() as tmp:
            out, _ = prepare_ranking_inputs(
                [c1, c2], {}, str(Path(tmp) / "x.sqlite3"), None,
                now_fn=lambda: 1.0, diversity_setting_fn=lambda: 3, feedback_fn=lambda: [BLOCK])
        self.assertEqual([c.candidate_id for c in out], ["b"])


def _clear():
    from discovery.allocation_contract import OwnershipStatus
    return OwnershipStatus.CLEAR


class BuilderExclusionTests(unittest.TestCase):
    """Classics and Deep Dives drop blocked-genre candidates before choosing the list."""

    def test_dict_items_with_a_blocked_genre_are_dropped(self):
        blocked = genre_block.blocked_genre_keys([BLOCK], music_key)
        items = [{"artist": "A", "genres": ["Shoegaze", "rock"]}, {"artist": "B", "genres": ["jazz"]},
                 {"artist": "C", "tags": ["shoegaze"]}, {"artist": "D"}]
        kept = genre_block.drop_blocked_items(iter(items), blocked, music_key)
        self.assertEqual([i["artist"] for i in kept], ["B", "D"])

    def test_nothing_blocked_keeps_every_item(self):
        items = [{"artist": "A", "genres": ["shoegaze"]}]
        self.assertEqual(genre_block.drop_blocked_items(items, frozenset(), music_key), items)

    def test_unreadable_feedback_blocks_nothing(self):
        def broken():
            raise RuntimeError("db locked")
        self.assertEqual(genre_block.current_blocked_keys(broken, music_key), frozenset())
        self.assertEqual(genre_block.current_blocked_keys(lambda: [BLOCK], music_key), frozenset({music_key("Shoegaze")}))


class ReadTimeTests(unittest.TestCase):
    def test_personal_classics_hide_blocked_genre_and_owned_albums_untouched(self):
        rows = [{"artist": "A", "album": "Dreamy", "genres": ["Shoegaze"]},
                {"artist": "B", "album": "Plain", "genres": ["jazz"]}]
        read = lambda _n: {"generated_at": 1, "payload": {"items": rows}}
        for name in ("classics", "new_releases"):
            got = json.loads(build_cached_discovery_list_response(
                name, 10, read, [BLOCK], {}, music_key, lambda i: True))
            self.assertEqual([i["album"] for i in got["items"]], ["Plain"])
        got = json.loads(build_cached_discovery_list_response(
            "classics", 10, read, [], {}, music_key, lambda i: True))
        self.assertEqual(len(got["items"]), 2)

    def test_lens_list_hides_by_tags_and_ranks_without_gap(self):
        payload = {"albums": [{"rank": 1, "artist": "A", "album": "X", "tags": ["shoegaze"]},
                              {"rank": 2, "artist": "B", "album": "Y", "tags": ["jazz"]}]}
        out = json.loads(build_lens_list_response(
            "l", 10, {"generated_at": 1, "payload": payload}, lambda i: False,
            dismissed_predicate([BLOCK], music_key)))
        self.assertEqual([(i["album"], i["rank"]) for i in out["items"]], [("Y", 1)])


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

    def test_block_list_unblock_roundtrip_and_idempotence(self):
        for _ in range(2):
            self.assertEqual(self.client.post("/api/discovery/blocked-genres", json={"genre": "  Post  Punk "}).json(),
                             {"ok": True, "genre": "Post Punk"})
        listed = self.client.get("/api/discovery/blocked-genres").json()["genres"]
        self.assertEqual([g["genre"] for g in listed], ["Post Punk"])
        self.assertTrue(self.client.request("DELETE", "/api/discovery/blocked-genres", json={"genre": "post punk"}).json()["removed"])
        self.assertEqual(self.client.get("/api/discovery/blocked-genres").json()["genres"], [])

    def test_empty_genre_rejected(self):
        self.assertEqual(self.client.post("/api/discovery/blocked-genres", json={"genre": " "}).status_code, 400)
        self.assertEqual(self.client.request("DELETE", "/api/discovery/blocked-genres", json={}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
