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
        metadata._album_details_cache.clear()
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
            ("/api/album-years", "POST"),
            ("/api/album-details", "GET"),
            ("/api/artwork", "GET"),
            ("/api/artist-image", "GET"),
            ("/api/album-links", "GET"),
            ("/api/album-description", "GET"),
            ("/api/album-reviews", "GET"),
        })

    def test_artist_image_returns_the_large_deezer_photo_for_an_exact_name(self):
        metadata._artist_image_cache.clear()
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value.json.return_value = {"data": [
                {"name": "Other", "picture_xl": "http://x/other.jpg"},
                {"name": "Portishead", "picture_big": "http://x/big.jpg", "picture_xl": "http://x/xl.jpg"},
            ]}
            result = metadata.artist_image("portishead")
        self.assertEqual(result["artwork_url"], "https://x/xl.jpg")
        with self.assertRaises(HTTPException):
            metadata.artist_image(" ")

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

    def test_bio_route_prefers_navidrome_bio_for_library_artists_without_web_requests(self):
        class Library:
            _music_key = staticmethod(lambda value: str(value).casefold())
            calls = []

            def _discovery_library_snapshot(self):
                return {"artists": [{"id": "ar-1", "name": "Artist"}]}

            def api_call(self, method, **params):
                self.calls.append((method, params))
                return {"artistInfo2": {"biography": 'A musician. <a href="https://x">Read more</a>'}}

        library = Library()
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.artist_bio_route("Artist", library), {"artist": "Artist", "bio": "A musician."})
            self.assertEqual(metadata.artist_bio_route("Artist", library)["bio"], "A musician.")
        client.get.assert_not_called()
        self.assertEqual(library.calls, [("getArtistInfo2", {"id": "ar-1"})])

    def test_bio_route_falls_back_to_web_lookup_when_navidrome_has_nothing(self):
        class Library:
            _music_key = staticmethod(lambda value: str(value).casefold())

            def _discovery_library_snapshot(self):
                return {"artists": []}

        with patch.object(metadata, "artist_bio", return_value={"artist": "Nobody", "bio": "web"}) as web:
            self.assertEqual(metadata.artist_bio_route("Nobody", Library())["bio"], "web")
        web.assert_called_once_with("Nobody")

    def test_artist_bio_client_sends_json_accept_header(self):
        # Wikimedia returns 403 for the default `Accept: */*`; every bio was empty because of it.
        self.assertEqual(metadata._EXTERNAL_HTTP.headers["accept"], "application/json")

    def test_artist_bio_does_not_cache_a_failed_wikidata_lookup(self):
        def get(url, params=None):
            if "wikidata" in url:
                return _Response({}, status_code=403)
            return _Response({}, status_code=404)
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = get
            self.assertEqual(metadata.artist_bio("Artist")["bio"], "")
        self.assertNotIn("artist", metadata._artist_bio_cache)

    def test_artist_bio_caches_a_successful_lookup_without_a_bio(self):
        def get(url, params=None):
            if "wikidata" in url:
                return _Response({"search": []})
            return _Response({}, status_code=404)
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = get
            metadata.artist_bio("Artist")
        self.assertIn("artist", metadata._artist_bio_cache)

    def test_album_years_returns_one_entry_per_resolved_album(self):
        body = metadata.AlbumYearsRequest(items=[
            metadata.AlbumYearItem(artist=" A ", album="One"),
            metadata.AlbumYearItem(artist="B", album="Two"),
        ])
        with patch.object(metadata, "_lookup_musicbrainz_album_years",
                          return_value={("A", "One"): 1999, ("B", "Two"): None}) as lookup:
            result = metadata.album_years(body)
        lookup.assert_called_once_with([("A", "One"), ("B", "Two")])
        self.assertEqual(result["years"], [
            {"artist": "A", "album": "One", "year": 1999},
            {"artist": "B", "album": "Two", "year": None},
        ])

    def test_album_years_reuses_and_stores_years_in_the_persistent_cache(self):
        class Library:
            def __init__(self):
                self.store = {}

            def _metadata_cache_get(self, key, ttl):
                return self.store.get(key)

            def _metadata_cache_set(self, key, value):
                self.store[key] = value

        library = Library()
        body = metadata.AlbumYearsRequest(items=[{"artist": "A", "album": "One"}, {"artist": "B", "album": "Two"}])
        with patch.object(metadata, "_lookup_musicbrainz_album_years",
                          return_value={("A", "One"): 1999, ("B", "Two"): None}) as lookup:
            first = metadata.album_years(body, library)
        self.assertEqual({(e["artist"], e["album"]): e["year"] for e in first["years"]},
                         {("A", "One"): 1999, ("B", "Two"): None})
        self.assertEqual(list(library.store.values()), [1999])
        with patch.object(metadata, "_lookup_musicbrainz_album_years", return_value={("B", "Two"): 2001}) as lookup:
            second = metadata.album_years(body, library)
        lookup.assert_called_once_with([("B", "Two")])
        self.assertEqual({e["year"] for e in second["years"]}, {1999, 2001})

    def test_album_years_rejects_oversized_requests(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            metadata.AlbumYearsRequest(items=[metadata.AlbumYearItem(artist="A", album="B")] * 61)

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

    def test_album_year_uses_first_plausible_exact_deezer_fallback(self):
        response = _Response({"data": [
            {"artist": {"name": "Artist Tribute"}, "title": "Album",
             "release_date": "1990-01-01"},
            {"artist": {"name": "Artist"}, "title": "Album",
             "release_date": "unknown"},
            {"artist": {"name": "ARTIST"}, "title": "ALBUM",
             "release_date": "2004-06-01"},
            {"artist": {"name": "Artist"}, "title": "Album",
             "release_date": "2010-01-01"},
        ]})
        with patch.object(metadata, "_musicbrainz_album_year", return_value=None), \
             patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value = response
            result = metadata.album_year("Artist", "Album")
        self.assertEqual(result, {
            "artist": "Artist", "album": "Album", "year": 2004, "source": "Deezer"
        })
        client.get.assert_called_once()

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
        self.assertEqual(result["artwork_url"], "https://example.test/cover.jpg")
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


    def test_artwork_uses_extracted_album_selection_and_preserves_payload(self):
        response = _Response({"data": [{
            "artist": {"name": "Artist"}, "title": "Album",
            "cover_xl": "http://images.test/cover.jpg", "release_date": "2001-04-03",
        }]})
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.return_value = response
            result = metadata.album_artwork("Artist", "Album")
        self.assertEqual(result, {
            "artwork_url": "https://images.test/cover.jpg",
            "image_kind": "album",
            "source": "Deezer",
            "matched_artist": "Artist",
            "matched_album": "Album",
            "year": 2001,
        })
        client.get.assert_called_once()

    def test_artwork_falls_back_to_exact_artist_photo_when_album_match_is_weak(self):
        album_response = _Response({"data": [{
            "artist": {"name": "Other Artist"}, "title": "Different Album",
            "cover_xl": "https://images.test/unrelated.jpg",
        }]})
        artist_response = _Response({"data": [
            {"name": "Artist Tribute", "picture_xl": "https://images.test/wrong.jpg"},
            {"name": "Artist", "picture_big": "http://images.test/artist.jpg"},
        ]})
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = [album_response, artist_response]
            result = metadata.album_artwork("Artist", "Album")
        self.assertEqual(result, {
            "artwork_url": "https://images.test/artist.jpg",
            "image_kind": "artist",
            "source": "Deezer",
            "matched_artist": "Artist",
            "year": None,
        })
        self.assertEqual(client.get.call_count, 2)

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
