"""Exact album pages on music services, picked from search results."""
import unittest
from unittest.mock import patch

from app.api import metadata
from app.services import album_links


class PickerTests(unittest.TestCase):
    def test_apple_music_needs_an_exact_artist_and_album_and_drops_tracking(self):
        results = [
            {"artistName": "Tricky", "collectionName": "Maxinquaye (Deluxe)", "collectionViewUrl": "https://music.apple.com/us/album/x/1"},
            {"artistName": "Tricky", "collectionName": "Maxinquaye - EP",
             "collectionViewUrl": "https://music.apple.com/us/album/maxinquaye/2?uo=4"},
        ]
        self.assertEqual(album_links.apple_music_url(results, "Tricky", "Maxinquaye"),
                         "https://music.apple.com/us/album/maxinquaye/2")
        self.assertIsNone(album_links.apple_music_url(results, "Someone Else", "Maxinquaye"))

    def test_deezer_and_musicbrainz_need_exact_matches(self):
        albums = [{"id": 7, "title": "Dummy", "artist": {"name": "Portishead"}}]
        self.assertEqual(album_links.deezer_url(albums, "Portishead", "Dummy"), "https://www.deezer.com/album/7")
        self.assertIsNone(album_links.deezer_url(albums, "Portishead", "Third"))
        groups = [{"id": "rg-1", "title": "Dummy", "artist-credit": [{"name": "Portishead", "joinphrase": ""}]}]
        self.assertEqual(album_links.musicbrainz_group_id(groups, "Portishead", "Dummy"), "rg-1")
        self.assertIsNone(album_links.musicbrainz_group_id(groups, "Massive Attack", "Dummy"))


class RouteTests(unittest.TestCase):
    def setUp(self):
        metadata._album_links_cache.clear()

    def test_endpoint_collects_every_exact_page_and_skips_the_rest(self):
        def fake(url, **kwargs):
            if "itunes" in url:
                return {"results": [{"artistName": "Portishead", "collectionName": "Dummy",
                                     "collectionViewUrl": "https://music.apple.com/us/album/dummy/9?uo=4"}]}
            if "deezer" in url:
                return None
            return {"release-groups": []}

        with patch.object(metadata, "_json_or_none", side_effect=fake):
            links = metadata.album_page_links(artist="Portishead", album="Dummy", mbid="rg-9")
        self.assertEqual(links["apple_music"], "https://music.apple.com/us/album/dummy/9")
        self.assertEqual(links["musicbrainz"], "https://musicbrainz.org/release-group/rg-9")
        self.assertEqual(links["listenbrainz"], "https://listenbrainz.org/album/rg-9")
        self.assertNotIn("spotify", links)
        self.assertNotIn("deezer", links)
        self.assertNotIn("qobuz", links)

    def test_artist_and_album_are_required(self):
        with self.assertRaises(Exception):
            metadata.album_page_links(artist="", album="Dummy")


if __name__ == "__main__":
    unittest.main()
