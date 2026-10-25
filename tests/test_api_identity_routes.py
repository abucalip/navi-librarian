"""Owner corrections to stored MusicBrainz identities, against a real SQLite store and a real index."""

import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.search as search_routes
from app.api.dependencies import get_librarian
from app.api.search import router as search_router
from discovery import store as discovery_store
from discovery.identity import identity_name, identity_prefix, load_identities, purge_stale_identities
from discovery.search.index import OwnedIndex, STATE_FRESH, STATE_UNAVAILABLE, build_owned_data

ASH = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"


class FakeLibrarian:
    def __init__(self, db, generation=1):
        self.DISCOVERY_DB = db
        self._generation = generation

    def _discovery_settings_read(self):
        return {"navidrome_generation": self._generation}

    def api_call(self, method, **params):
        raise AssertionError("no Navidrome call is expected in these tests")


def index_with(db, *, fail=False):
    def load_library():
        if fail:
            raise RuntimeError("library unavailable")
        return ([{"id": "ar1", "name": "Ash", "album_count": 1}],
                [{"id": "al1", "artist": "Ash", "artist_id": "ar1", "album": "1977", "year": 1977,
                  "song_count": 1, "release_mbid": None}])

    return OwnedIndex(
        load_library=load_library,
        load_songs=lambda: [],
        load_identities=lambda generation: load_identities(
            lambda prefix: discovery_store.read_prefix(db, prefix), generation,
        ),
        background=False,
    )


class IdentityCorrectionRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "discovery.sqlite3"
        self.previous = search_routes._owned_index
        search_routes._owned_index = index_with(self.db)
        search_routes._owned_index.ensure(1)
        self.app = FastAPI()
        self.app.include_router(search_router)
        self.librarian = FakeLibrarian(self.db)
        self.app.dependency_overrides[get_librarian] = lambda: self.librarian
        self.client = TestClient(self.app)

    def tearDown(self):
        search_routes._owned_index = self.previous
        self.tmp.cleanup()

    def artist_mbid(self):
        return search_routes._owned_index.view().data.artists[0]["mbid"]

    def test_a_correction_is_stored_as_manual_and_reaches_the_index_at_once(self):
        response = self.client.put("/api/identities/artist/ar1", json={"mbid": ASH})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"kind": "artist", "id": "ar1", "mbid": ASH, "source": "manual"})
        stored = discovery_store.read_prefix(self.db, identity_name(1, "artist", "ar1"))
        self.assertEqual(stored[identity_name(1, "artist", "ar1")], {"mbid": ASH, "source": "manual"})
        self.assertEqual(self.artist_mbid(), ASH)

    def test_an_album_correction_sets_the_release_group(self):
        response = self.client.put("/api/identities/album/al1", json={"mbid": OTHER})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(search_routes._owned_index.view().data.albums[0]["release_group_mbid"], OTHER)

    def test_null_marks_the_item_as_having_no_mbid(self):
        self.client.put("/api/identities/artist/ar1", json={"mbid": ASH})
        response = self.client.put("/api/identities/artist/ar1", json={"mbid": None})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(self.artist_mbid())

    def test_deleting_the_record_lets_the_next_pass_resolve_the_item_again(self):
        self.client.put("/api/identities/artist/ar1", json={"mbid": ASH})
        response = self.client.delete("/api/identities/artist/ar1")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["removed"])
        self.assertIsNone(self.artist_mbid())
        self.assertEqual(discovery_store.read_prefix(self.db, identity_name(1, "artist", "ar1")), {})

    def test_malformed_mbid_is_refused_before_anything_is_written(self):
        for bad in ("not-a-uuid", "11111111-1111-4111-8111-11111111111Z", "11111111-1111-4111-8111-111111111111 OR 1"):
            response = self.client.put("/api/identities/artist/ar1", json={"mbid": bad})
            self.assertEqual(response.status_code, 400, bad)
        self.assertEqual(discovery_store.read_prefix(self.db, identity_prefix(1)), {})

    def test_unknown_item_and_unknown_kind_are_404(self):
        self.assertEqual(self.client.put("/api/identities/artist/nobody", json={"mbid": ASH}).status_code, 404)
        self.assertEqual(self.client.put("/api/identities/track/ar1", json={"mbid": ASH}).status_code, 404)
        self.assertEqual(self.client.delete("/api/identities/track/ar1").status_code, 404)

    def test_correction_while_the_index_is_unavailable_is_409_not_a_crash(self):
        search_routes._owned_index = index_with(self.db, fail=True)
        search_routes._owned_index.ensure(1)
        self.assertEqual(search_routes._owned_index.view().state, STATE_UNAVAILABLE)
        response = self.client.put("/api/identities/artist/ar1", json={"mbid": ASH})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "index_not_ready")

    def test_correction_for_a_stale_generation_does_not_roll_the_index_back(self):
        self.librarian._generation = 2
        search_routes._owned_index.ensure(2)
        self.client.put("/api/identities/artist/ar1", json={"mbid": ASH})
        self.assertEqual(search_routes._owned_index.view().data.generation, 2)
        self.assertEqual(search_routes._owned_index.view().state, STATE_FRESH)


class IdentityPassGuardTests(unittest.TestCase):
    def test_a_pass_for_a_stale_generation_makes_no_calls_and_deletes_nothing(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "discovery.sqlite3"
        discovery_store.write_many(db, {identity_name(2, "artist", "ar1"): {"mbid": ASH, "source": "manual"}})
        data = build_owned_data(generation=1, built_at=0, artists=[{"id": "ar1", "name": "Ash", "album_count": 1}],
                                albums=[], songs=[])
        librarian = FakeLibrarian(db, generation=2)
        counts = search_routes._identity_pass(librarian, data)
        self.assertEqual(counts, {"artists": 0, "albums": 0, "unresolved": 0})
        self.assertIn(identity_name(2, "artist", "ar1"), discovery_store.read_prefix(db, identity_prefix(2)))


class PurgeStaleIdentitiesTests(unittest.TestCase):
    def test_other_generations_are_removed_and_the_current_one_is_kept(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db = Path(tmp.name) / "discovery.sqlite3"
        discovery_store.write_many(db, {
            identity_name(1, "artist", "ar1"): {"mbid": ASH, "source": "navidrome"},
            identity_name(10, "artist", "ar1"): {"mbid": OTHER, "source": "navidrome"},
            identity_name(2, "artist", "ar1"): {"mbid": ASH, "source": "navidrome"},
        })
        removed = purge_stale_identities(
            lambda prefix, keep: discovery_store.delete_prefix_except(db, prefix, keep), 1,
        )
        self.assertEqual(removed, 2)
        self.assertEqual(sorted(discovery_store.read_prefix(db, "identity:navidrome")), [identity_name(1, "artist", "ar1")])


if __name__ == "__main__":
    unittest.main()
