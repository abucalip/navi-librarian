"""Direct-import regressions for matched Deezer album-details shaping."""
import unittest

from app.services.deezer_album_details import shape_album_match


class DeezerAlbumDetailsTests(unittest.TestCase):
    def test_prefers_xl_artwork_and_preserves_existing_payload_fields(self):
        self.assertEqual(shape_album_match({
            "artist": {"name": "Artist"},
            "title": "Album",
            "release_date": "2001-04-03",
            "cover_xl": "http://images.test/xl.jpg",
            "cover_big": "https://images.test/big.jpg",
            "cover_medium": "https://images.test/medium.jpg",
        }), {
            "matched_artist": "Artist",
            "matched_album": "Album",
            "year": 2001,
            "artwork_url": "https://images.test/xl.jpg",
        })

    def test_falls_back_through_cover_sizes_and_normalizes_http(self):
        self.assertEqual(
            shape_album_match({"artist": {"name": "Artist"}, "title": "Album",
                               "cover_big": "http://images.test/big.jpg"}),
            {"matched_artist": "Artist", "matched_album": "Album",
             "year": None, "artwork_url": "https://images.test/big.jpg"},
        )
        self.assertEqual(
            shape_album_match({"cover_medium": "https://images.test/medium.jpg"})["artwork_url"],
            "https://images.test/medium.jpg",
        )

    def test_missing_fields_and_invalid_release_date_keep_safe_defaults(self):
        self.assertEqual(shape_album_match({"release_date": "unknown"}), {
            "matched_artist": None,
            "matched_album": None,
            "year": None,
            "artwork_url": None,
        })


if __name__ == "__main__":
    unittest.main()
