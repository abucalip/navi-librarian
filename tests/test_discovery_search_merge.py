"""Ownership, dedupe and result shaping for provider candidates (contract sections 3.8 and 4.2)."""

import unittest

from discovery.search.index import build_owned_data
from discovery.search.merge import OwnedKeys, fresh_candidates, same_entity, shape_result
from discovery.search.providers import album_candidate, artist_candidate


def owned(artists=(), albums=()):
    return OwnedKeys(build_owned_data(
        generation=1,
        built_at=0,
        artists=[{"id": f"ar{i}", "name": name, "album_count": 1} for i, name in enumerate(artists)],
        albums=[{"id": f"al{i}", "artist": artist, "artist_id": "ar0", "album": title, "year": year, "song_count": 1}
                for i, (artist, title, year) in enumerate(albums)],
        songs=[],
    ))


class OwnershipTests(unittest.TestCase):
    def test_provider_artist_matching_an_owned_artist_name_is_owned_and_not_emitted(self):
        emitted = []
        fresh = fresh_candidates(
            [artist_candidate("musicbrainz", "Ash", "mb-1")],
            query="ash", owned=owned(artists=["Ash"]), emitted=emitted,
        )
        self.assertEqual(fresh, [])

    def test_album_with_the_same_key_and_year_is_owned(self):
        keys = owned(albums=[("Radiohead", "Kid A", 2000)])
        same = album_candidate("musicbrainz", "Kid A", "Radiohead", 2000, "rg-1")
        other_year = album_candidate("musicbrainz", "Kid A", "Radiohead", 2011, "rg-2")
        self.assertTrue(keys.owns(same))
        self.assertFalse(keys.owns(other_year))

    def test_unknown_year_on_either_side_still_matches_by_key(self):
        keys = owned(albums=[("Radiohead", "Kid A", None)])
        self.assertTrue(keys.owns(album_candidate("lastfm", "Kid A", "Radiohead", None, None)))


class DedupeTests(unittest.TestCase):
    def test_same_mbid_is_one_entity(self):
        first = artist_candidate("musicbrainz", "Ash", "mb-1")
        second = artist_candidate("lastfm", "ASH", "mb-1")
        self.assertTrue(same_entity(first, second))

    def test_homonyms_with_different_known_mbids_stay_separate(self):
        first = artist_candidate("musicbrainz", "Ash", "mb-1")
        second = artist_candidate("musicbrainz", "Ash", "mb-2")
        self.assertFalse(same_entity(first, second))

    def test_key_and_year_decide_albums_without_mbids(self):
        first = album_candidate("musicbrainz", "Kid A", "Radiohead", 2000, None)
        same_year = album_candidate("lastfm", "Kid A", "Radiohead", 2000, None)
        other_year = album_candidate("lastfm", "Kid A", "Radiohead", 2011, None)
        self.assertTrue(same_entity(first, same_year))
        self.assertFalse(same_entity(first, other_year))

    def test_second_source_for_an_emitted_entity_is_dropped_in_the_same_request(self):
        emitted = []
        first = fresh_candidates(
            [artist_candidate("musicbrainz", "Ash", "mb-1")], query="ash", owned=owned(), emitted=emitted,
        )
        second = fresh_candidates(
            [artist_candidate("lastfm", "Ash", None)], query="ash", owned=owned(), emitted=emitted,
        )
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])


class RankingAndShapeTests(unittest.TestCase):
    def test_exact_then_prefix_then_contains_then_name(self):
        emitted = []
        fresh = fresh_candidates(
            [
                artist_candidate("musicbrainz", "Crash Test", "mb-3"),
                artist_candidate("musicbrainz", "Ashes", "mb-2"),
                artist_candidate("musicbrainz", "Ash", "mb-1"),
            ],
            query="ash", owned=owned(), emitted=emitted,
        )
        self.assertEqual([c["name"] for c in fresh], ["Ash", "Ashes", "Crash Test"])

    def test_non_matching_candidates_are_dropped(self):
        fresh = fresh_candidates(
            [artist_candidate("musicbrainz", "Radiohead", "mb-9")], query="ash", owned=owned(), emitted=[],
        )
        self.assertEqual(fresh, [])

    def test_artist_result_has_null_album_count_and_genre_because_search_does_not_report_them(self):
        result = shape_result(artist_candidate("musicbrainz", "Ash", "mb-1"))
        self.assertEqual(result["type"], "artist")
        self.assertFalse(result["owned"])
        self.assertEqual(result["sources"], ["musicbrainz"])
        self.assertIsNone(result["album_count"])
        self.assertIsNone(result["genre"])
        self.assertIsNone(result["artwork_url"])

    def test_album_result_carries_artist_year_and_release_group(self):
        result = shape_result(album_candidate("musicbrainz", "Kid A", "Radiohead", 2000, "rg-1"))
        self.assertEqual(result["key"], "radiohead/kid a")
        self.assertEqual(result["artist_key"], "radiohead")
        self.assertEqual(result["year"], 2000)
        self.assertEqual(result["release_group_mbid"], "rg-1")
        self.assertEqual(result["id"], "rg-1")

    def test_source_specific_id_when_no_mbid_is_known(self):
        result = shape_result(artist_candidate("lastfm", "Ash", None))
        self.assertEqual(result["id"], "lastfm:ash")


if __name__ == "__main__":
    unittest.main()
