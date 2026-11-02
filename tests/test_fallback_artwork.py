import html
import json
import unittest
from unittest.mock import patch

from app.api import metadata
from app.services.fallback_artwork import parse_qobuz_albums, select_apple_artwork, select_qobuz_artwork


def _qobuz_page(albums):
    props = html.escape(json.dumps({"mode": "grid", "albums": json.dumps(albums)}), quote=True)
    return f'<div data-live-props-value="{props}"></div>'


QOBUZ = {"1": {"title": "Ok Computer", "artists": [{"name": "Radiohead"}], "releasedAt": "898000000",
               "image": {"small": "https://s/1_230.jpg", "large": "https://s/1_600.jpg"}},
         "2": {"title": "OK Computer OKNOTOK", "artists": [{"name": "Radiohead"}],
               "image": {"large": "https://s/2_600.jpg"}}}


class AppleTests(unittest.TestCase):
    def test_exact_match_gets_a_600px_cover_and_ignores_single_suffix(self):
        results = [
            {"artistName": "Other", "collectionName": "Album", "artworkUrl100": "https://i/a/100x100bb.jpg"},
            {"artistName": "Artist", "collectionName": "Album - EP", "releaseDate": "2019-05-01T07:00:00Z",
             "artworkUrl100": "https://i/a/100x100bb.jpg"},
        ]
        found = select_apple_artwork(results, "ARTIST", "album")
        self.assertEqual(found["artwork_url"], "https://i/a/600x600bb.jpg")
        self.assertEqual((found["source"], found["year"]), ("Apple Music", 2019))

    def test_near_matches_and_empty_names_return_nothing(self):
        results = [{"artistName": "Artist", "collectionName": "Album (Deluxe)", "artworkUrl100": "https://i/100x100bb.jpg"}]
        self.assertIsNone(select_apple_artwork(results, "Artist", "Album"))
        self.assertIsNone(select_apple_artwork(results, "", "Album"))


class QobuzTests(unittest.TestCase):
    def test_parses_embedded_albums_and_selects_exact_match(self):
        albums = parse_qobuz_albums(_qobuz_page(QOBUZ))
        found = select_qobuz_artwork(albums, "Radiohead", "OK Computer")
        self.assertEqual(found["artwork_url"], "https://s/1_600.jpg")
        self.assertEqual((found["source"], found["year"]), ("Qobuz", 1998))
        self.assertIsNone(select_qobuz_artwork(albums, "Radiohead", "Kid A"))

    def test_unrecognised_page_gives_no_albums(self):
        self.assertEqual(parse_qobuz_albums("<html>nothing</html>"), [])
        self.assertEqual(parse_qobuz_albums('<div data-live-props-value="{bad"></div>'), [])


class _Resp:
    def __init__(self, payload=None, text=""):
        self._p, self.text = payload, text
    def raise_for_status(self): pass
    def json(self): return self._p


class RouteFallbackTests(unittest.TestCase):
    def setUp(self):
        metadata._artwork_cache.clear()

    def _run(self, responses):
        with patch.object(metadata, "_EXTERNAL_HTTP") as client, \
             patch.object(metadata.persistent_metadata, "read", return_value=None), \
             patch.object(metadata.persistent_metadata, "write"):
            client.get.side_effect = responses
            return metadata.album_artwork("Radiohead", "OK Computer"), client

    def test_apple_is_used_when_deezer_has_nothing(self):
        apple = {"results": [{"artistName": "Radiohead", "collectionName": "OK Computer",
                              "artworkUrl100": "https://i/100x100bb.jpg"}]}
        result, client = self._run([_Resp({"data": []}), _Resp(apple)])
        self.assertEqual(result["source"], "Apple Music")
        self.assertEqual(client.get.call_count, 2)

    def test_qobuz_is_used_when_apple_has_nothing(self):
        result, client = self._run([_Resp({"data": []}), _Resp({"results": []}), _Resp(text=_qobuz_page(QOBUZ))])
        self.assertEqual(result["source"], "Qobuz")
        self.assertEqual(result["artwork_url"], "https://s/1_600.jpg")

    def test_no_provider_match_gives_no_cover_and_never_an_artist_photo(self):
        result, client = self._run([_Resp({"data": []}), _Resp({"results": []}), _Resp(text="<html></html>")])
        self.assertIsNone(result["artwork_url"])
        self.assertEqual(client.get.call_count, 3)

    def test_provider_outage_is_retryable(self):
        result, _ = self._run([_Resp({"data": []}), RuntimeError("down")])
        self.assertTrue(result.get("retryable"))


if __name__ == "__main__":
    unittest.main()
