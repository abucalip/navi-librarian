"""Efficiency P5c: an update request by MusicBrainz id finds the artist from the store first."""
import tempfile
import unittest
from pathlib import Path

from app.services.library_enrich import find_artist_id
from intelligence.store import open_store
from intelligence.store import repositories as repo

MBID = "0383dadf-2a4e-4d10-a46a-e9e041da8eb3"


class FakeLibrarian:
    def __init__(self, artists):
        self.artists = artists          # {navidrome id: musicBrainzId}
        self.calls = []

    def api_call(self, method, **params):
        self.calls.append(method)
        if method == "getArtist":
            if params["id"] not in self.artists:
                raise RuntimeError("Navidrome API error 70: Artist not found")
            return {"artist": {"id": params["id"], "musicBrainzId": self.artists[params["id"]]}}
        if method == "getArtists":
            return {"artists": {"index": [{"artist": [{"id": k, "musicBrainzId": v} for k, v in self.artists.items()]}]}}
        raise AssertionError(method)

    @staticmethod
    def items(value):
        return value or []


class FindArtistId(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "store.sqlite3")
        self.addCleanup(self.db.close)

    def remember(self, navidrome_id):
        repo.upsert_entity(self.db, "artist", "Queen", mbid=MBID, navidrome_id=navidrome_id, owned=True)

    def test_store_hit_is_confirmed_with_one_call_and_no_index_read(self):
        self.remember("ar1")
        nd = FakeLibrarian({"ar1": MBID.upper()})
        self.assertEqual(find_artist_id(nd, self.db, MBID), "ar1")
        self.assertEqual(nd.calls, ["getArtist"])

    def test_store_miss_reads_the_index(self):
        nd = FakeLibrarian({"ar9": MBID})
        self.assertEqual(find_artist_id(nd, self.db, MBID), "ar9")
        self.assertEqual(nd.calls, ["getArtists"])

    def test_a_stale_stored_id_falls_back_to_the_index(self):
        self.remember("old")
        nd = FakeLibrarian({"new": MBID})
        self.assertEqual(find_artist_id(nd, self.db, MBID), "new")
        self.assertEqual(nd.calls, ["getArtist", "getArtists"])

    def test_a_stored_id_now_naming_another_artist_falls_back(self):
        self.remember("ar1")
        nd = FakeLibrarian({"ar1": "ffffffff-2a4e-4d10-a46a-e9e041da8eb3", "ar2": MBID})
        self.assertEqual(find_artist_id(nd, self.db, MBID), "ar2")

    def test_unknown_artist_is_none(self):
        self.assertIsNone(find_artist_id(FakeLibrarian({}), self.db, MBID))


if __name__ == "__main__":
    unittest.main()
