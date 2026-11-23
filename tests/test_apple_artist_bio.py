"""Direct-import tests for Apple Music artist biography matching and fallback safety."""

import unittest

from app.services import apple_artist_bio


class AppleArtistBioTests(unittest.TestCase):
    def test_extracts_exact_artist_json_ld_description(self):
        page = """
        <script type="application/ld+json">
        {"@type":"MusicGroup","name":"Portishead","description":"English band formed in Bristol."}
        </script>
        """
        self.assertEqual(
            apple_artist_bio.parse_artist_biography(page, "PORTISHEAD"),
            "English band formed in Bristol.",
        )

    def test_rejects_a_different_artist_even_when_the_page_contains_a_description(self):
        page = """
        <script type="application/ld+json">
        {"@type":"MusicGroup","name":"Portishead Tribute","description":"A tribute band."}
        </script>
        """
        self.assertIsNone(apple_artist_bio.parse_artist_biography(page, "Portishead"))

    def test_rejects_generic_apple_music_promotion(self):
        page = """
        <script type="application/ld+json">
        {"@type":"MusicGroup","name":"Unknown Artist","description":"Listen to music by Unknown Artist on Apple Music."}
        </script>
        """
        self.assertIsNone(apple_artist_bio.parse_artist_biography(page, "Unknown Artist"))

    def test_handles_json_ld_graph_and_html_entities(self):
        page = """
        <script type="application/ld+json">
        {"@graph":[{"@type":"Person","name":"Björk","description":"Singer &amp; composer."}]}
        </script>
        """
        self.assertEqual(
            apple_artist_bio.parse_artist_biography(page, "Bjork"),
            "Singer & composer.",
        )

    def test_requires_one_unambiguous_exact_itunes_artist_id(self):
        results = [
            {"wrapperType": "artist", "artistName": "Portishead Tribute", "artistId": 1},
            {"wrapperType": "artist", "artistName": "Portishead", "artistId": 2},
            {"wrapperType": "collection", "artistName": "Portishead", "artistId": 3},
        ]
        self.assertEqual(apple_artist_bio._exact_artist_id(results, "Portishead"), 2)
        ambiguous = results + [
            {"wrapperType": "artist", "artistName": "Portishead", "artistId": 4},
        ]
        self.assertIsNone(apple_artist_bio._exact_artist_id(ambiguous, "Portishead"))

    def test_lookup_uses_itunes_id_then_the_apple_artist_page(self):
        page = """
        <script type="application/ld+json">
        {"@type":"MusicGroup","name":"Portishead","description":"English band."}
        </script>
        """
        calls = []

        class Response:
            text = page

            def __init__(self, payload=None):
                self.payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        def get(url, **kwargs):
            calls.append((url, kwargs))
            if url == apple_artist_bio.APPLE_SEARCH_URL:
                return Response({"results": [
                    {"wrapperType": "artist", "artistName": "Portishead", "artistId": 123}
                ]})
            return Response()

        self.assertEqual(apple_artist_bio.lookup_artist_biography(get, "Portishead"), ("English band.", True))
        self.assertEqual(calls[1][0], "https://music.apple.com/us/artist/-/123")
        self.assertEqual(calls[0][1]["params"]["entity"], "musicArtist")

    def test_provider_failure_is_not_reported_as_a_definitive_no_bio(self):
        def broken(*args, **kwargs):
            raise OSError("offline")

        self.assertEqual(apple_artist_bio.lookup_artist_biography(broken, "Artist"), (None, False))

    def test_no_exact_artist_match_is_a_definitive_no_bio(self):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"results": [
                    {"wrapperType": "artist", "artistName": "Artist Tribute", "artistId": 123}
                ]}

        calls = []

        def get(url, **kwargs):
            calls.append(url)
            return Response()

        self.assertEqual(apple_artist_bio.lookup_artist_biography(get, "Artist"), (None, True))
        self.assertEqual(calls, [apple_artist_bio.APPLE_SEARCH_URL])


if __name__ == "__main__":
    unittest.main()
