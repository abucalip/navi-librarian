"""Direct-import tests for Apple Music artist biography matching and fallback safety."""

import unittest

import httpx

from app.services import apple_artist_bio


class AppleArtistBioTests(unittest.TestCase):
    def test_extracts_full_artist_page_bio_and_preserves_paragraphs(self):
        page = """
        <script type="application/json" id="serialized-server-data">
        {"data":[{"data":{"sections":[{"items":[
          {"title":"Fela Kuti","contentDescriptor":{"kind":"artist","identifiers":{"storeAdamID":"55088"}},
           "bio":"First paragraph.<br />Second <i>paragraph</i>.\\n\\nThird paragraph.","circleArtwork":{}}
        ]}]}}]}
        </script>
        <script type="application/ld+json">
        {"@type":"MusicGroup","name":"Fela Kuti","description":"Short summary."}
        </script>
        """
        self.assertEqual(
            apple_artist_bio.parse_artist_biography(page, "Fela Kuti", 55088),
            "First paragraph.\nSecond paragraph.\n\nThird paragraph.",
        )

    def test_full_artist_bio_is_selected_by_artist_id_not_a_repeated_link(self):
        page = """
        <script type="application/json" id="serialized-server-data">
        {"data":[{"data":{"sections":[{"items":[
          {"title":"Wrong link","contentDescriptor":{"kind":"artist","identifiers":{"storeAdamID":"123"}}},
          {"title":"Another artist","contentDescriptor":{"kind":"artist","identifiers":{"storeAdamID":"456"}},
           "bio":"Wrong biography.","circleArtwork":{}}
        ]}]}}]}
        </script>
        """
        self.assertIsNone(apple_artist_bio.parse_artist_biography(page, "Requested Artist", 123))

    def test_full_artist_bio_requires_artist_content_descriptor(self):
        page = """
        <script type="application/json" id="serialized-server-data">
        {"data":[{"data":{"sections":[{"items":[
          {"title":"Not an artist","contentDescriptor":{"kind":"album","identifiers":{"storeAdamID":"123"}},
           "bio":"Not an artist biography.","circleArtwork":{}}
        ]}]}}]}
        </script>
        """
        self.assertIsNone(apple_artist_bio.parse_artist_biography(page, "Requested Artist", 123))

    def test_preserves_paragraph_breaks_in_json_ld_fallback(self):
        page = """
        <script type="application/ld+json">
        {"@type":"MusicGroup","name":"Portishead","description":"First paragraph.\\n\\nSecond paragraph."}
        </script>
        """
        self.assertEqual(
            apple_artist_bio.parse_artist_biography(page, "Portishead"),
            "First paragraph.\n\nSecond paragraph.",
        )

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
        {"@graph":[{"@type":"https://schema.org/Person","name":"Björk","description":"Singer &amp; composer."}]}
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
        <script type="application/json" id="serialized-server-data">
        {"data":[{"title":"Portishead","contentDescriptor":{"kind":"artist","identifiers":{"storeAdamID":"123"}},
         "bio":"Long artist biography.","circleArtwork":{}}]}
        </script>
        <script type="application/ld+json">
        {"@type":"MusicGroup","name":"Portishead","description":"Short summary."}
        </script>
        """
        calls = []
        id_page = "https://music.apple.com/us/artist/x/123"
        artist_page = "https://music.apple.com/us/artist/portishead/123"

        def respond(request):
            calls.append(request.url)
            if request.url.host == "itunes.apple.com":
                return httpx.Response(200, json={"results": [
                    {"wrapperType": "artist", "artistName": "Portishead", "artistId": 123}
                ]})
            if str(request.url) == id_page:
                return httpx.Response(301, headers={"Location": artist_page})
            self.assertEqual(str(request.url), artist_page)
            return httpx.Response(200, text=page)

        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            result = apple_artist_bio.lookup_artist_biography(client.get, "Portishead")
        self.assertEqual(result, ("Long artist biography.", True))
        self.assertEqual([str(url) for url in calls[1:]], [id_page, artist_page])
        self.assertEqual(calls[0].params["entity"], "musicArtist")

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
