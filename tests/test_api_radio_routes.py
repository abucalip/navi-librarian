import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import radio
from integrations.radio import logos
from integrations.radio.tile import tile_png
from app.api.dependencies import get_librarian
from app.security.app_login_middleware import create_app_login_middleware
from tests.test_radio_icy import block


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)
        self.api_call = mock.Mock()


class Chunks(httpx.AsyncByteStream):
    """A streamed body, as a real station sends it (a plain ``content=`` is marked as read)."""

    def __init__(self, data, size=5):
        self.parts = [data[i:i + size] for i in range(0, len(data), size)]

    async def __aiter__(self):
        for part in self.parts:
            yield part


def upstream_stream(metaint=8):
    return (b"A" * metaint + block("StreamTitle='Pink Floyd - Time';") + b"B" * metaint)


class RadioRouteTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        radio._STORES.clear()
        self.librarian = FakeLibrarian(self.dir.name)
        self.client = self.make_client(gated=False)
        self.gated = self.make_client(gated=True)
        self.store = radio.get_store(self.librarian)
        self.store.save_station("1", "tok", "Rock FM", "http://rock.example/live")

    def make_client(self, gated):
        app = FastAPI()
        if gated:
            app.middleware("http")(create_app_login_middleware(
                auth_configured=lambda: True, session_username=lambda token: None, cookie_name="c"))
        app.include_router(radio.router)
        app.dependency_overrides[get_librarian] = lambda: self.librarian
        return TestClient(app)

    def test_app_address_is_saved_and_read_back(self):
        self.librarian.api_call.return_value = {}
        saved = self.client.put("/api/radio/settings", json={"app_url": "http://box.tailnet.ts.net:8000/"})
        self.assertEqual(saved.json(), {"app_url": "http://box.tailnet.ts.net:8000", "moved": 0})
        self.assertEqual(self.client.get("/api/radio/settings").json(), {"app_url": "http://box.tailnet.ts.net:8000"})
        self.assertEqual(self.client.put("/api/radio/settings", json={"app_url": "ftp://x"}).status_code, 400)

    def tearDown(self):
        radio.client_factory = httpx.AsyncClient
        radio._STORES.clear()
        self.dir.cleanup()

    def serve(self, handler):
        radio.client_factory = lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(handler), **kw)

    def ok_handler(self, request):
        self.seen_headers = request.headers
        return httpx.Response(200, stream=Chunks(upstream_stream()),
                              headers={"content-type": "audio/mpeg", "icy-metaint": "8", "icy-name": "Rock FM"})

    def test_stream_needs_no_session_but_api_does(self):
        self.serve(self.ok_handler)
        self.assertEqual(self.gated.get("/radio/stream/tok").status_code, 200)
        self.assertEqual(self.gated.get("/api/radio/plays").status_code, 401)

    def test_unknown_token_is_404(self):
        self.assertEqual(self.client.get("/radio/stream/nope").status_code, 404)

    def test_client_without_metadata_gets_audio_only_and_the_title_is_logged(self):
        self.serve(self.ok_handler)
        times = iter([100.0, 200.0, 200.0, 200.0])
        real = radio.ListenTracker
        with mock.patch.object(radio, "ListenTracker",
                               lambda *a: real(*a, clock=lambda: next(times))):
            response = self.client.get("/radio/stream/tok")
        self.assertEqual(response.content, b"A" * 8 + b"B" * 8)
        self.assertNotIn("icy-metaint", response.headers)
        self.assertEqual(self.seen_headers["icy-metadata"], "1")
        plays = self.store.list_plays()
        self.assertEqual([(p["artist"], p["title"], p["station_name"]) for p in plays],
                         [("Pink Floyd", "Time", "Rock FM")])

    def test_client_asking_for_metadata_gets_the_stream_untouched(self):
        self.serve(self.ok_handler)
        response = self.client.get("/radio/stream/tok", headers={"Icy-MetaData": "1"})
        self.assertEqual(response.content, upstream_stream())
        self.assertEqual(response.headers["icy-metaint"], "8")

    def test_playlist_or_error_upstream_is_refused(self):
        for status, kind in ((200, "audio/x-mpegurl"), (200, "text/html"), (404, "audio/mpeg")):
            self.serve(lambda request, s=status, k=kind: httpx.Response(s, stream=Chunks(b"x"), headers={"content-type": k}))
            self.assertEqual(self.client.get("/radio/stream/tok").status_code, 502, (status, kind))

    def test_unreachable_upstream_is_502(self):
        def boom(request):
            raise httpx.ConnectError("down")
        self.serve(boom)
        self.assertEqual(self.client.get("/radio/stream/tok").status_code, 502)

    def logged_play(self, artist="Pink Floyd", title="Time"):
        return self.store.record_play("1", "Rock FM", f"{artist} - {title}", artist, title, 90)

    def test_get_looks_up_the_album_once_and_hands_the_song_to_the_track_get(self):
        play = self.logged_play()
        with mock.patch.object(radio, "lookup_recording_album",
                               return_value={"album": "The Dark Side of the Moon", "year": 1973}) as lookup, \
                mock.patch.object(radio.track_service, "request_track",
                                  return_value={"ok": True, "status": "downloading"}) as request:
            body = self.client.post(f"/api/radio/plays/{play}/get").json()
            self.client.post(f"/api/radio/plays/{play}/get")
        self.assertTrue(body["ok"])
        self.assertEqual(lookup.call_count, 1)
        self.assertEqual(request.call_args.args[1:], (
            "Pink Floyd", "The Dark Side of the Moon", "Time", None, 1973, None))
        self.assertEqual(self.store.get_play(play)["grabbed"], 1)

    def test_clear_all_empties_the_log(self):
        self.logged_play()
        self.store.record_play("1", "Rock FM", "Jingle", None, "Jingle", 90)
        body = self.client.delete("/api/radio/plays").json()
        self.assertEqual(body, {"ok": True, "removed": 2})
        self.assertEqual(self.store.list_plays(), [])

    def test_get_without_artist_or_album_does_not_search(self):
        unnamed = self.store.record_play("1", "Rock FM", "Jingle", None, "Jingle", 90)
        play = self.logged_play()
        with mock.patch.object(radio, "lookup_recording_album", return_value=None), \
                mock.patch.object(radio.track_service, "request_track") as request:
            self.assertFalse(self.client.post(f"/api/radio/plays/{unnamed}/get").json()["ok"])
            self.assertFalse(self.client.post(f"/api/radio/plays/{play}/get").json()["ok"])
        request.assert_not_called()
        self.assertEqual(self.store.get_play(play)["grabbed"], 0)



ROWS = [{"id": "1", "name": "Rock FM", "streamUrl": "http://rock.example/live", "homepageUrl": ""}]


def navidrome(method, **params):
    if method == "getInternetRadioStations":
        return {"internetRadioStations": {"internetRadioStation": ROWS}}
    return {}


class StationFieldRouteTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        radio._STORES.clear()
        self.librarian = FakeLibrarian(self.dir.name)
        self.librarian.api_call = mock.Mock(side_effect=navidrome)
        self.store = radio.get_store(self.librarian)
        app = FastAPI()
        app.include_router(radio.router)
        app.dependency_overrides[get_librarian] = lambda: self.librarian
        self.client = TestClient(app)
        # No outside request is made by any route test; logos come from the generated tile.
        patcher = mock.patch.object(logos, "_find_remote", return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.dir.cleanup()

    def test_favourite_and_tags_are_saved_and_listed(self):
        self.assertEqual(self.client.put("/api/radio/stations/1/favourite", json={"favourite": True}).json(),
                         {"id": "1", "favourite": True})
        self.assertEqual(self.client.put("/api/radio/stations/1/tags", json={"tags": ["rock", "Rock"]}).json(),
                         {"id": "1", "tags": ["rock"]})
        row = self.client.get("/api/radio/stations").json()["items"][0]
        self.assertEqual((row["favourite"], row["tags"], row["logo_url"]),
                         (True, ["rock"], "/api/radio/stations/1/logo"))
        self.assertEqual(row["playable_url"], "http://rock.example/live")

    def test_bad_favourite_or_tags_are_400(self):
        self.assertEqual(self.client.put("/api/radio/stations/1/favourite", json={"favourite": "yes"}).status_code,
                         400)
        self.assertEqual(self.client.put("/api/radio/stations/1/tags", json={"tags": "rock"}).status_code, 400)
        self.assertEqual(self.client.put("/api/radio/stations/99/favourite", json={"favourite": True}).status_code,
                         400)

    def test_logo_without_a_found_image_is_the_generated_png_tile(self):
        for size in (128, 512):
            with self.subTest(size=size):
                response = self.client.get(f"/api/radio/stations/1/logo?size={size}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.headers["content-type"], "image/png")
                self.assertEqual(response.content[:8], b"\x89PNG\r\n\x1a\n")
                self.assertIn("max-age", response.headers["cache-control"])
        self.assertEqual(self.client.get("/api/radio/stations/1/logo?size=100").status_code, 400)

    def test_logo_for_an_unknown_station_is_400_and_bad_ids_are_refused(self):
        self.assertEqual(self.client.get("/api/radio/stations/99/logo").status_code, 400)
        self.assertEqual(self.client.get("/api/radio/stations/..%2Fx/logo").status_code, 404)

    def test_owner_logo_is_stored_served_and_cleared(self):
        png = tile_png("Upload", 16)
        put = self.client.put("/api/radio/stations/1/logo", content=png,
                              headers={"content-type": "image/png"})
        self.assertEqual(put.json(), {"id": "1", "logo_url": "/api/radio/stations/1/logo", "source": "override"})
        got = self.client.get("/api/radio/stations/1/logo?size=512")
        self.assertEqual((got.headers["content-type"], got.content), ("image/png", png))
        self.assertEqual(self.client.delete("/api/radio/stations/1/logo").json()["ok"], True)
        self.assertIsNone(self.store.get_logo_state("1"))
        self.assertEqual(self.client.get("/api/radio/stations/1/logo").headers["content-type"], "image/png")

    def test_logo_upload_refuses_other_content_and_oversize_bodies(self):
        svg = b"<svg xmlns='http://www.w3.org/2000/svg'/>"
        self.assertEqual(self.client.put("/api/radio/stations/1/logo", content=svg).status_code, 400)
        too_big = b"\x89PNG\r\n\x1a\n" + b"0" * (logos.MAX_UPLOAD_BYTES + 1)
        self.assertEqual(self.client.put("/api/radio/stations/1/logo", content=too_big).status_code, 413)
        self.assertIsNone(self.store.get_logo_state("1"))


if __name__ == "__main__":
    unittest.main()
