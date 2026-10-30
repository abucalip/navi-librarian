"""The metadata routes read and fill the attached persistent store, so a restart re-asks no provider."""
import unittest
from unittest.mock import patch

from app.api import metadata
from app.services import persistent_metadata


class _Store:
    def __init__(self):
        self.data = {}

    def get(self, key, ttl_seconds):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


def _restart():
    """What a process restart does to the route caches: the in-memory ones are empty again."""
    for cache in (metadata._artist_bio_cache, metadata._artwork_cache, metadata._artist_image_cache,
                  metadata._album_links_cache, metadata._album_description_cache,
                  metadata._apple_url_cache, metadata._album_details_cache,
                  metadata._musicbrainz_year_cache):
        cache.clear()


class PersistentMetadataCacheTests(unittest.TestCase):
    def setUp(self):
        self.store = _Store()
        persistent_metadata.attach(self.store.get, self.store.set)
        self.addCleanup(persistent_metadata.detach)
        _restart()

    def _deezer(self, client, payloads):
        client.get.side_effect = [type("R", (), {
            "raise_for_status": lambda self: None, "json": lambda self, p=p: p})() for p in payloads]

    def test_unattached_store_is_a_miss_and_a_dropped_write(self):
        persistent_metadata.detach()
        self.assertIsNone(persistent_metadata.read("k"))
        persistent_metadata.write("k", 1)

    def test_a_failing_store_never_breaks_a_read_or_write(self):
        def boom(*args):
            raise RuntimeError("disk")
        persistent_metadata.attach(boom, boom)
        self.assertIsNone(persistent_metadata.read("k"))
        persistent_metadata.write("k", 1)

    def test_album_details_with_a_tracklist_survive_a_restart(self):
        album = {"id": 7, "title": "Dummy", "artist": {"name": "Portishead"}, "release_date": "1994-08-22",
                 "cover_xl": "https://x/c.jpg"}
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self._deezer(client, [{"data": [album]},
                                  {"tracks": {"data": [{"title": "Mysterons", "duration": 300}]}}])
            first = metadata.album_details(artist="Portishead", album="Dummy")
            self.assertTrue(first["tracks"])
            calls = client.get.call_count
            self.assertEqual(metadata.album_details(artist="Portishead", album="Dummy"), first)
            _restart()
            self.assertEqual(metadata.album_details(artist="Portishead", album="Dummy"), first)
            self.assertEqual(client.get.call_count, calls)

    def test_a_provider_failure_in_album_details_is_not_cached(self):
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            client.get.side_effect = RuntimeError("down")
            result = metadata.album_details(artist="A", album="B")
            self.assertEqual(result["tracks"], [])
            self.assertEqual(self.store.data, {})
            self.assertEqual(metadata._album_details_cache, {})

    def test_a_definite_catalog_miss_is_kept_in_memory_only(self):
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self._deezer(client, [{"data": []}])
            metadata.album_details(artist="A", album="B")
            metadata.album_details(artist="A", album="B")
            self.assertEqual(client.get.call_count, 1)
            self.assertEqual(self.store.data, {})

    def test_found_artist_bio_survives_a_restart_and_a_missing_one_is_not_stored(self):
        metadata._artist_bio_cache.clear()
        persistent_metadata.write("artist-bio:v1:portishead", "A band from Bristol.")
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.artist_bio("Portishead")["bio"], "A band from Bristol.")
            client.get.assert_not_called()

    def test_found_artist_image_survives_a_restart(self):
        stored = {"artwork_url": "https://x/xl.jpg", "image_kind": "artist", "source": "Deezer"}
        persistent_metadata.write("artist-image:v1:portishead", stored)
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.artist_image("Portishead"), stored)
            client.get.assert_not_called()

    def test_found_album_artwork_survives_a_restart(self):
        stored = {"artwork_url": "https://x/c.jpg", "image_kind": "album", "source": "Deezer"}
        persistent_metadata.write("album-artwork:v1:portishead:dummy", stored)
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.album_artwork("Portishead", "Dummy"), stored)
            client.get.assert_not_called()

    def test_stored_album_description_and_links_skip_the_providers(self):
        description = {"paragraphs": ["Notes."], "source": "Apple Music", "url": "https://a/x"}
        persistent_metadata.write("album-description:v1:portishead:dummy", description)
        links = {"apple_music": "https://a/x"}
        persistent_metadata.write("album-links:v1:portishead|dummy|", links)
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.album_description("Portishead", "Dummy"), description)
            self.assertEqual(metadata.album_page_links("Portishead", "Dummy", ""), links)
            client.get.assert_not_called()

    def test_year_lookup_without_a_librarian_uses_the_attached_store(self):
        persistent_metadata.write(metadata._year_store_key("Portishead", "Dummy"), 1994)
        with patch.object(metadata, "_EXTERNAL_HTTP") as client:
            self.assertEqual(metadata.album_year(artist="Portishead", album="Dummy", librarian=None)["year"], 1994)
            client.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
