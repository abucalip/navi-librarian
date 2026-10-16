"""Direct-import regressions for Deezer catalog matching policy."""

import unittest

from app.services.deezer_album_matching import (
    artwork_match_score,
    exact_album_matches,
    normalize_catalog_name,
    release_year,
)


class DeezerAlbumMatchingTests(unittest.TestCase):
    def test_normalization_ignores_punctuation_and_case(self):
        self.assertEqual(normalize_catalog_name("Björk — Debut!"), "björkdebut")

    def test_exact_match_requires_both_artist_and_album(self):
        albums = [
            {"artist": {"name": "Björk"}, "title": "Debut"},
            {"artist": {"name": "Björk"}, "title": "Post"},
            {"artist": {"name": "Björk Tribute"}, "title": "Debut"},
        ]
        self.assertEqual(exact_album_matches(albums, "BJÖRK", "Debut!"), [albums[0]])

    def test_empty_names_do_not_match_unrelated_missing_fields(self):
        self.assertEqual(exact_album_matches([{"title": "Album"}], "", "Album"), [])
        self.assertEqual(exact_album_matches([{"artist": {"name": "Artist"}}], "Artist", ""), [])

    def test_release_year_accepts_only_plausible_four_digit_year(self):
        self.assertEqual(release_year("2001-05-03"), 2001)
        for value in ("", None, "1899-01-01", "2101-01-01", "20xx-01-01", "12"):
            with self.subTest(value=value):
                self.assertIsNone(release_year(value))

    def test_artwork_score_preserves_exact_and_partial_weights(self):
        exact = {"artist": {"name": "Artist"}, "title": "Album"}
        partial = {"artist": {"name": "Artist Ensemble"}, "title": "Album Deluxe"}
        unrelated = {"artist": {"name": "Other"}, "title": "Elsewhere"}
        self.assertEqual(artwork_match_score(exact, "Artist", "Album"), 13)
        self.assertEqual(artwork_match_score(partial, "Artist", "Album"), 6)
        self.assertEqual(artwork_match_score(unrelated, "Artist", "Album"), 0)


if __name__ == "__main__":
    unittest.main()
