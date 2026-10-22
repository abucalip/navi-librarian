"""Direct-import regressions for Deezer artwork selection policy."""
import unittest

from app.services.deezer_artwork import select_album_artwork, select_artist_artwork


class DeezerArtworkTests(unittest.TestCase):
    def test_card_artwork_prefers_the_500px_cover_over_the_1000px_one(self):
        album = {
            "artist": {"name": "Artist"}, "title": "Album", "release_date": "2002-03-04",
            "cover_xl": "http://images.test/xl.jpg", "cover_big": "http://images.test/big.jpg",
            "cover_medium": "http://images.test/medium.jpg",
        }
        self.assertEqual(select_album_artwork([album], "Artist", "Album")["artwork_url"], "https://images.test/big.jpg")
        del album["cover_big"]
        self.assertEqual(select_album_artwork([album], "Artist", "Album")["artwork_url"], "https://images.test/xl.jpg")
        artist = [{"name": "Artist", "picture_xl": "http://images.test/pxl.jpg", "picture_big": "http://images.test/pbig.jpg"}]
        self.assertEqual(select_artist_artwork(artist, "Artist")["artwork_url"], "https://images.test/pbig.jpg")

    def test_album_selection_uses_best_relevant_candidate_and_card_sized_cover(self):
        result = select_album_artwork([
            {
                "artist": {"name": "Artist"}, "title": "Album Deluxe",
                "cover_xl": "http://images.test/xl.jpg", "cover_big": "https://images.test/big.jpg",
                "release_date": "2002-03-04",
            },
            {
                "artist": {"name": "Artist"}, "title": "Album",
                "cover_big": "https://images.test/exact.jpg", "release_date": "1998-01-01",
            },
        ], "Artist", "Album")

        self.assertEqual(result, {
            "artwork_url": "https://images.test/exact.jpg",
            "image_kind": "album",
            "source": "Deezer",
            "matched_artist": "Artist",
            "matched_album": "Album",
            "year": 1998,
        })

    def test_album_selection_rejects_irrelevant_or_empty_results(self):
        self.assertIsNone(select_album_artwork([], "Artist", "Album"))
        self.assertIsNone(select_album_artwork([
            {"artist": {"name": "Other"}, "title": "Unrelated", "cover_xl": "https://images.test/x.jpg"},
        ], "Artist", "Album"))

    def test_album_selection_preserves_missing_artwork_and_invalid_year_semantics(self):
        result = select_album_artwork([
            {"artist": {"name": "Artist"}, "title": "Album", "release_date": "not-a-date"},
        ], "Artist", "Album")
        self.assertIsNotNone(result)
        self.assertIsNone(result["artwork_url"])
        self.assertIsNone(result["year"])

    def test_artist_selection_requires_case_insensitive_exact_name_and_photo(self):
        result = select_artist_artwork([
            {"name": "Artist Tribute", "picture_xl": "https://images.test/wrong.jpg"},
            {"name": "ARTIST", "picture_big": "http://images.test/artist.jpg"},
        ], "Artist", year=2001)
        self.assertEqual(result, {
            "artwork_url": "https://images.test/artist.jpg",
            "image_kind": "artist",
            "source": "Deezer",
            "matched_artist": "ARTIST",
            "year": 2001,
        })
        self.assertIsNone(select_artist_artwork([
            {"name": "Artist Tribute", "picture_xl": "https://images.test/wrong.jpg"},
        ], "Artist"))
        self.assertIsNone(select_artist_artwork([
            {"name": "Artist", "picture_xl": ""},
        ], "Artist"))

    def test_artist_selection_without_query_name_returns_none(self):
        self.assertIsNone(select_artist_artwork([{"name": "Artist", "picture_xl": "https://images.test/a.jpg"}], ""))


if __name__ == "__main__":
    unittest.main()
