import hashlib
import unittest

from navidrome_client import api_call, items, search_result_payload, album_details_payload


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
        self.status_checked = False

    def raise_for_status(self):
        self.status_checked = True

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response, **kwargs):
        self.response = response
        self.options = kwargs
        self.request = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def get(self, url, *, params):
        self.request = {"url": url, "params": params}
        return self.response


class NavidromeClientTests(unittest.TestCase):
    def test_items_normalizes_optional_collection_values(self):
        self.assertEqual(items(None), [])
        self.assertEqual(items("single"), ["single"])
        self.assertEqual(items(["first", "second"]), ["first", "second"])
        self.assertEqual(items([]), [])


    def test_search_result_payload_preserves_category_and_field_contract(self):
        result = {
            "artist": [{"id": "a1", "name": "Artist", "extra": "ignored"}],
            "album": {"id": "b1", "name": "Album", "year": "2001"},
            "song": [{"id": "t1", "title": "Track", "duration": 180, "playCount": 4}],
        }
        self.assertEqual(search_result_payload(result, "artist"), {
            "artist": [{"id": "a1", "name": "Artist", "artist": None, "album": None,
                        "year": None, "duration": None, "playCount": None}],
        })
        self.assertEqual(search_result_payload(result, "album"), {
            "album": [{"id": "b1", "name": "Album", "artist": None, "album": None,
                       "year": "2001", "duration": None, "playCount": None}],
        })
        self.assertEqual(search_result_payload(result, "all")["song"], [{
            "id": "t1", "name": None, "artist": None, "album": None,
            "year": None, "duration": 180, "playCount": 4,
        }])
        self.assertEqual(list(search_result_payload(result, "all")), ["artist", "album", "song"])


    def test_album_details_payload_shapes_album_and_scalar_track(self):
        payload = album_details_payload({
            "id": "album-1", "name": "Record", "artist": "Band",
            "year": "1999", "genre": "rock", "songCount": 1,
            "song": {"id": "track-1", "title": "Opening", "track": 1,
                     "duration": 210, "playCount": 3, "ignored": True},
        })
        self.assertEqual(payload, {
            "id": "album-1", "name": "Record", "artist": "Band",
            "year": "1999", "genre": "rock", "songCount": 1,
            "songs": [{"id": "track-1", "title": "Opening", "artist": None,
                       "track": 1, "duration": 210, "playCount": 3}],
        })

    def test_album_details_payload_handles_missing_album_fields_and_tracks(self):
        self.assertEqual(album_details_payload({}), {
            "id": None, "name": None, "artist": None, "year": None,
            "genre": None, "songCount": None, "songs": [],
        })

    def test_authentication_request_and_success_response(self):
        response = FakeResponse({"subsonic-response": {"status": "ok", "artists": []}})
        client = FakeClient(response)
        config_calls = []
        result = api_call(
            "getArtists",
            lambda: config_calls.append(True) or ("http://navidrome.test", "listener", "secret"),
            client_factory=lambda **kwargs: self._configured_client(client, kwargs),
            salt_factory=lambda: "fixed-salt",
            musicFolderId="music-root",
        )

        self.assertEqual(result, {"status": "ok", "artists": []})
        self.assertEqual(config_calls, [True])
        self.assertEqual(client.options, {"timeout": 30, "follow_redirects": False})
        self.assertTrue(response.status_checked)
        self.assertEqual(client.request["url"], "http://navidrome.test/rest/getArtists.view")
        query = client.request["params"]
        self.assertEqual(query["u"], "listener")
        self.assertEqual(query["s"], "fixed-salt")
        self.assertEqual(query["t"], hashlib.md5(b"secretfixed-salt").hexdigest())
        self.assertEqual(query["v"], "1.16.1")
        self.assertEqual(query["c"], "navidrome-librarian")
        self.assertEqual(query["f"], "json")
        self.assertEqual(query["musicFolderId"], "music-root")

    def test_api_error_preserves_legacy_error_message(self):
        response = FakeResponse({
            "subsonic-response": {
                "status": "failed",
                "error": {"code": 40, "message": "Wrong username or password"},
            }
        })
        with self.assertRaisesRegex(
            RuntimeError,
            "Navidrome API error 40: Wrong username or password",
        ):
            api_call(
                "getArtists",
                lambda: ("http://navidrome.test", "listener", "secret"),
                client_factory=lambda **kwargs: self._configured_client(
                    FakeClient(response), kwargs
                ),
                salt_factory=lambda: "fixed-salt",
            )

    def test_unknown_api_error_uses_legacy_fallback(self):
        response = FakeResponse({
            "subsonic-response": {
                "status": "failed",
                "error": {"code": 70},
            }
        })
        with self.assertRaisesRegex(RuntimeError, "Navidrome API error 70: Unknown error"):
            api_call(
                "getArtists",
                lambda: ("http://navidrome.test", "listener", "secret"),
                client_factory=lambda **kwargs: self._configured_client(
                    FakeClient(response), kwargs
                ),
                salt_factory=lambda: "fixed-salt",
            )

    @staticmethod
    def _configured_client(client, options):
        client.options = options
        return client


if __name__ == "__main__":
    unittest.main()
