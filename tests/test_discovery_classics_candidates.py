"""Direct-import contract tests for classics candidate collection."""
import unittest

from discovery_classics_candidates import collect_classic_candidates


class ClassicsCandidateCollectionTests(unittest.TestCase):
    def setUp(self):
        self.lookups = []
        self.pause_calls = []
        self.albums = {
            "Artist A": [
                {"artist": "Artist A", "album": "Shared", "lastfm_listeners": 10},
                {"artist": "Artist A", "album": "Owned", "lastfm_listeners": 99},
                {"artist": "Artist A", "album": "EP", "lastfm_listeners": 5},
            ],
            "Artist B": [
                {"artist": "artist b", "album": "shared", "lastfm_listeners": 20},
                {"artist": "Artist B", "album": "Unique", "lastfm_listeners": 7},
            ],
        }

    def lookup(self, artist, limit=8):
        self.lookups.append((artist, limit))
        return self.albums.get(artist, [])

    def collect(self, artists=None, **kwargs):
        return collect_classic_candidates(
            artists or [
                {"name": "Artist A", "album_count": 2},
                {"name": "Artist B", "album_count": 5},
            ],
            {("artist a", "owned")},
            top_albums_lookup=self.lookup,
            music_key=lambda value: value.casefold().strip(),
            is_album_candidate=lambda item: item["album"] != "EP",
            pause=lambda: self.pause_calls.append(True),
            **kwargs,
        )

    def test_visits_artists_by_library_album_count_and_requests_eight_albums(self):
        self.collect()
        self.assertEqual(self.lookups, [("Artist B", 8), ("Artist A", 8)])

    def test_owned_and_ineligible_albums_are_excluded(self):
        result = self.collect()
        self.assertNotIn(("artist a", "owned"), result)
        self.assertNotIn(("artist a", "ep"), result)

    def test_duplicate_identity_keeps_highest_listener_record_and_metadata(self):
        result = self.collect()
        shared = result[("artist a", "shared")]
        self.assertEqual(shared["lastfm_listeners"], 20)
        self.assertEqual(shared["artist"], "artist b")
        self.assertEqual(shared["discovery_type"], "classic")
        self.assertEqual(shared["discovery_source"], "Last.fm artist top albums")
        self.assertEqual(shared["artist_library_album_count"], 5)

    def test_pause_callback_keeps_original_every_fifth_artist_cadence(self):
        artists = [{"name": f"Artist {i}", "album_count": 10 - i} for i in range(7)]
        self.collect(artists)
        self.assertEqual(self.pause_calls, [True])

    def test_empty_provider_payload_returns_empty_mapping(self):
        self.albums = {}
        self.assertEqual(self.collect(), {})


if __name__ == "__main__":
    unittest.main()
