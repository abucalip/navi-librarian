"""Regression tests for the metadata API router and provider adapters."""
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api import metadata


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("provider error")

    def json(self):
        return self._payload


class MetadataRoutesTests(unittest.TestCase):
    def setUp(self):
        metadata._artist_bio_cache.clear()
        metadata._artwork_cache.clear()
        metadata._musicbrainz_year_cache.clear()

    def test_router_preserves_metadata_endpoint_paths_and_methods(self):
        actual = {
            (route.path, method)
            for route in metadata.router.routes
            for method in getattr(route, "methods", set())
        }
        self.assertEqual(actual, {
            ("/api/artist-bio", "GET"),
            ("/api/album-year", "GET"),
            ("/api/album-details", "GET"),
            ("/api/artwork", "GET"),
        })

    def test_artist_bio_validates_input_and_returns_cached_bio(self):
        with self.assertRaises(HTTPException) as raised:
            metadata.artist_bio("")
        self.assertEqual(raised.exception.status_code, 400)

        metadata._artist_bio_cache["artist"] = {"time": 99.0, "bio": "A musician."}
        with patch.object(metadata, "monotonic", return_value=100.0), \
             patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.artist_bio(" Artist "), {
                "artist": "Artist", "bio": "A musician."
            })
        client.get.assert_not_called()

    def test_album_year_prefers_musicbrainz_and_validates_input(self):
        with self.assertRaises(HTTPException) as raised:
            metadata.album_year("Artist", "")
        self.assertEqual(raised.exception.status_code, 400)

        with patch.object(metadata, "_musicbrainz_album_year", return_value=1998), \
             patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.album_year("Artist", "Album"), {
                "artist": "Artist", "album": "Album", "year": 1998,
                "source": "MusicBrainz",
            })
        client.get.assert_not_called()

    def test_album_details_returns_exact_match_and_tracklist(self):
        search = _Response({"data": [{
            "artist": {"name": "Artist"}, "title": "Album",
            "release_date": "2001-04-03", "cover_xl": "https://example.test/cover.jpg",
            "id": 42,
        }]})
        details = _Response({"tracks": {"data": [
            {"track_position": 1, "title": "Opening", "duration": 123},
            {"track_position": 2, "title": "Finale", "duration": 234},
        ]}})
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = [search, details]
            result = metadata.album_details("Artist", "Album")
        self.assertEqual(result["matched_artist"], "Artist")
        self.assertEqual(result["matched_album"], "Album")
        self.assertEqual(result["year"], 2001)
        self.assertEqual(result["tracks"], [
            {"track_number": 1, "title": "Opening", "duration_seconds": 123},
            {"track_number": 2, "title": "Finale", "duration_seconds": 234},
        ])
        self.assertEqual(client.get.call_count, 2)

    def test_album_details_does_not_accept_non_exact_match(self):
        response = _Response({"data": [{
            "artist": {"name": "Artist Tribute"}, "title": "Album",
            "release_date": "2001-01-01", "id": 42,
        }]})
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value = response
            result = metadata.album_details("Artist", "Album")
        self.assertEqual(result["tracks"], [])
        self.assertIn("No exact catalog match", result["message"])
        client.get.assert_called_once()

    def test_artwork_returns_cached_result_and_rejects_empty_request(self):
        with self.assertRaises(HTTPException) as raised:
            metadata.album_artwork("", "")
        self.assertEqual(raised.exception.status_code, 400)

        cached = {"artwork_url": "https://example.test/cover.jpg", "image_kind": "album"}
        metadata._artwork_cache[("artist", "album")] = {"time": 99.0, "data": cached}
        with patch.object(metadata, "monotonic", return_value=100.0), \
             patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.album_artwork("Artist", "Album"), cached)
        client.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
