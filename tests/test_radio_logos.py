import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest import mock

import httpx

from integrations.radio import logos, safe_fetch
from integrations.radio.store import RadioStore
from integrations.radio.tile import colour_for, initials, tile_png

PUBLIC_IP = "93.184.216.34"
PNG = tile_png("Logo source", 16)
STATION = {"id": "7", "name": "Rock FM", "stream_url": "http://rock.example/live",
           "homepage_url": "http://rock.example/"}


def decode_png(data):
    """Width, height and the RGB rows of a PNG this module writes (8-bit RGB, filter 0 per row)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, idat, width, height = 8, b"", None, None
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if kind == b"IHDR":
            width, height = struct.unpack(">II", body[:8])
        if kind == b"IDAT":
            idat += body
        pos += 12 + length
    raw = zlib.decompress(idat)
    stride = 1 + 3 * width
    rows = [raw[y * stride + 1:(y + 1) * stride] for y in range(height)]
    return width, height, rows


class TileTests(unittest.TestCase):
    def test_tile_is_a_png_of_the_requested_size_with_the_hashed_background(self):
        for size in (128, 512):
            with self.subTest(size=size):
                width, height, rows = decode_png(tile_png("Rock FM", size))
                self.assertEqual((width, height), (size, size))
                self.assertEqual(rows[0][:3], bytes(colour_for("Rock FM")))

    def test_initials_come_from_the_first_two_words(self):
        self.assertEqual(initials("Radio Paradise"), "RP")
        self.assertEqual(initials("BBC"), "BB")
        self.assertEqual(initials("Rock FM 1"), "RF")
        self.assertEqual(initials("  -- "), "R")
        self.assertEqual(initials(""), "R")

    def test_colour_is_stable_for_a_name(self):
        self.assertEqual(colour_for("Rock FM"), colour_for("Rock FM"))

    def test_rejects_non_positive_size(self):
        with self.assertRaises(ValueError):
            tile_png("x", 0)


class FakeWeb:
    """Serves URLs from a dict; anything else is a 404. Records every request made."""

    def __init__(self, routes):
        self.routes = routes
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        self.requests.append(url)
        if url in self.routes:
            status, ctype, body = self.routes[url]
            if isinstance(body, Exception):
                raise body
            return httpx.Response(status, headers={"content-type": ctype}, content=body)
        return httpx.Response(404, headers={"content-type": "text/plain"}, content=b"no")


class LogoResolverTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.data = Path(self.dir.name)
        self.store = RadioStore(self.data / "radio.sqlite3")
        patcher = mock.patch.object(safe_fetch, "resolve_host", lambda host: [PUBLIC_IP])
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.dir.cleanup()

    def resolve(self, web, station=STATION, now=1000.0):
        client = httpx.Client(transport=httpx.MockTransport(web), follow_redirects=False, trust_env=False)
        self.addCleanup(client.close)
        return logos.resolve(station, self.store, self.data, client, now=now)

    def radio_browser(self, favicon="http://img.example/logo.png"):
        base = logos.RADIO_BROWSER_BASE
        return {
            f"{base}/json/stations/byurl/http%3A%2F%2Frock.example%2Flive":
                (200, "application/json", f'[{{"favicon": "{favicon}"}}]'.encode()),
        }

    def test_radio_browser_favicon_is_used_and_cached(self):
        routes = self.radio_browser()
        routes["http://img.example/logo.png"] = (200, "image/png", PNG)
        web = FakeWeb(routes)
        logo = self.resolve(web)
        self.assertEqual(logo.media_type, "image/png")
        self.assertEqual(logo.path.read_bytes(), PNG)
        self.assertEqual(self.store.get_logo_state("7")["source"], "radio_browser")
        made = len(web.requests)
        self.resolve(web)
        self.assertEqual(len(web.requests), made, "a found logo is not fetched again")

    def test_falls_through_to_the_homepage_icon_when_radio_browser_has_nothing(self):
        page = b'<html><head><link rel="apple-touch-icon" href="/touch.png"></head></html>'
        routes = {
            f"{logos.RADIO_BROWSER_BASE}/json/stations/byurl/http%3A%2F%2Frock.example%2Flive":
                (200, "application/json", b"[]"),
            f"{logos.RADIO_BROWSER_BASE}/json/stations/byname/Rock%20FM": (200, "application/json", b"[]"),
            "http://rock.example/": (200, "text/html; charset=utf-8", page),
            "http://rock.example/touch.png": (200, "image/png", PNG),
        }
        logo = self.resolve(FakeWeb(routes))
        self.assertEqual(self.store.get_logo_state("7")["source"], "homepage")
        self.assertEqual(logo.path.read_bytes(), PNG)

    def test_og_image_beats_favicon_and_favicon_is_the_last_homepage_try(self):
        page = b'<meta property="og:image" content="/card.png">'
        routes = {
            "http://rock.example/": (200, "text/html", page),
            "http://rock.example/card.png": (200, "image/png", PNG),
            "http://rock.example/favicon.ico": (200, "image/x-icon", b"\x00\x00\x01\x00" + b"x" * 8),
        }
        self.resolve(FakeWeb(routes))
        self.assertEqual(self.store.get_logo_state("7")["media_type"], "image/png")

    def test_favicon_ico_is_tried_when_the_page_is_missing(self):
        routes = {"http://rock.example/favicon.ico": (200, "image/x-icon", b"\x00\x00\x01\x00" + b"x" * 8)}
        logo = self.resolve(FakeWeb(routes))
        self.assertEqual(logo.media_type, "image/x-icon")

    def test_a_non_image_answer_falls_through_and_a_source_error_never_escapes(self):
        routes = {
            f"{logos.RADIO_BROWSER_BASE}/json/stations/byurl/http%3A%2F%2Frock.example%2Flive":
                (200, "application/json", b'[{"favicon": "http://img.example/x"}]'),
            "http://img.example/x": (200, "text/html", b"<html>not an image</html>"),
            "http://rock.example/": (200, "text/html", b""),
            "http://rock.example/favicon.ico": (200, "image/png", b"<svg/>"),
        }
        logo = self.resolve(FakeWeb(routes))
        self.assertIsNone(logo.path)
        self.assertEqual(self.store.get_logo_state("7")["status"], "none")

    def test_unreachable_sources_fall_back_to_the_generated_tile_and_remember_the_miss(self):
        web = FakeWeb({"http://x.example/": (200, "text/html", b"")})
        web.routes[f"{logos.RADIO_BROWSER_BASE}/json/stations/byurl/http%3A%2F%2Frock.example%2Flive"] = (
            0, "", httpx.ConnectError("down"))
        logo = self.resolve(web)
        self.assertIsNone(logo.path)
        state = self.store.get_logo_state("7")
        self.assertEqual((state["status"], state["source"]), ("none", "generated"))
        made = len(web.requests)
        self.resolve(web, now=1000.0 + 60)
        self.assertEqual(len(web.requests), made, "a remembered miss is not retried on the next call")

    def test_a_remembered_miss_is_retried_after_it_expires(self):
        web = FakeWeb({})
        self.resolve(web, now=1000.0)
        made = len(web.requests)
        self.resolve(web, now=1000.0 + logos.NEGATIVE_TTL_SECONDS + 1)
        self.assertGreater(len(web.requests), made)

    def test_owner_override_wins_and_clearing_resolves_again(self):
        web = FakeWeb({})
        logos.set_override(self.store, self.data, "7", PNG, now=1000.0)
        logo = self.resolve(web)
        self.assertEqual(logo.path.read_bytes(), PNG)
        self.assertEqual(web.requests, [], "an override makes no outside request")
        self.assertEqual(self.store.get_logo_state("7")["source"], "override")
        logos.clear(self.store, self.data, "7")
        self.assertIsNone(self.store.get_logo_state("7"))
        self.assertFalse((self.data / "radio-logos" / "7" / "logo.bin").exists())

    def test_override_refuses_what_is_not_a_supported_image(self):
        with self.assertRaises(ValueError):
            logos.set_override(self.store, self.data, "7", b"<svg xmlns='http://www.w3.org/2000/svg'/>")
        with self.assertRaises(ValueError):
            logos.set_override(self.store, self.data, "7", b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024))

    def test_image_bytes_serves_the_tile_at_the_requested_size_when_nothing_is_found(self):
        client = httpx.Client(transport=httpx.MockTransport(FakeWeb({})), follow_redirects=False, trust_env=False)
        self.addCleanup(client.close)
        body, media_type = logos.image_bytes(STATION, self.store, self.data, 128, client=client)
        self.assertEqual(media_type, "image/png")
        self.assertEqual(decode_png(body)[:2], (128, 128))

    def test_ids_that_could_escape_the_data_folder_are_refused(self):
        for bad in ("../x", "a/b", "", "7 8"):
            with self.subTest(station_id=bad), self.assertRaises(ValueError):
                logos.logo_dir(self.data, bad)


class SafeFetchTests(unittest.TestCase):
    def client(self, handler):
        return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False, trust_env=False)

    def test_only_public_http_addresses_are_fetched(self):
        refused = [
            "file:///etc/passwd", "ftp://x.example/a", "https://user:pw@x.example/a",
            "http://127.0.0.1/a", "http://10.0.0.5/a", "http://192.168.1.9/a", "http://169.254.169.254/latest",
            "http://[::1]/a", "http://[::ffff:127.0.0.1]/a", "http://100.64.0.1/a", "http:///nohost",
        ]
        for url in refused:
            with self.subTest(url=url), self.assertRaises(safe_fetch.UnsafeURL):
                safe_fetch.check_url(url)

    def test_a_hostname_that_resolves_to_a_private_address_is_refused(self):
        with mock.patch.object(safe_fetch, "resolve_host", lambda host: ["10.1.2.3"]):
            with self.assertRaises(safe_fetch.UnsafeURL):
                safe_fetch.check_url("http://looks-public.example/a")

    def test_a_redirect_into_a_private_network_is_refused(self):
        def handler(request):
            if request.url.host == "good.example":
                return httpx.Response(302, headers={"location": "http://192.168.1.1/admin.png"})
            return httpx.Response(200, headers={"content-type": "image/png"}, content=PNG)

        def resolve(host):
            return ["192.168.1.1"] if host == "192.168.1.1" else [PUBLIC_IP]

        with mock.patch.object(safe_fetch, "resolve_host", resolve):
            with self.assertRaises(safe_fetch.UnsafeURL):
                safe_fetch.fetch("http://good.example/a", accept=("image/",), max_bytes=10_000,
                                 client=self.client(handler))

    def test_redirects_are_followed_to_a_public_target_and_capped(self):
        def handler(request):
            if request.url.path == "/loop":
                return httpx.Response(301, headers={"location": "/loop"})
            return httpx.Response(200, headers={"content-type": "image/png"}, content=PNG)

        with mock.patch.object(safe_fetch, "resolve_host", lambda host: [PUBLIC_IP]):
            body, media, final = safe_fetch.fetch("http://a.example/x", accept=("image/",), max_bytes=10_000,
                                                  client=self.client(handler))
            self.assertEqual((body, media, final), (PNG, "image/png", "http://a.example/x"))
            with self.assertRaises(safe_fetch.FetchFailed):
                safe_fetch.fetch("http://a.example/loop", accept=("image/",), max_bytes=10_000,
                                 client=self.client(handler))

    def test_size_cap_applies_to_declared_and_streamed_bodies(self):
        def big(request):
            return httpx.Response(200, headers={"content-type": "image/png"}, content=b"x" * 5000)

        with mock.patch.object(safe_fetch, "resolve_host", lambda host: [PUBLIC_IP]):
            with self.assertRaises(safe_fetch.FetchFailed):
                safe_fetch.fetch("http://a.example/x", accept=("image/",), max_bytes=4000,
                                 client=self.client(big))

    def test_content_type_must_match(self):
        def html(request):
            return httpx.Response(200, headers={"content-type": "text/html"}, content=b"<p>")

        with mock.patch.object(safe_fetch, "resolve_host", lambda host: [PUBLIC_IP]):
            with self.assertRaises(safe_fetch.FetchFailed):
                safe_fetch.fetch("http://a.example/x", accept=("image/",), max_bytes=100,
                                 client=self.client(html))

    def test_sniffing_accepts_common_raster_formats_and_refuses_svg(self):
        self.assertEqual(safe_fetch.sniff_image(PNG), "image/png")
        self.assertEqual(safe_fetch.sniff_image(b"\xff\xd8\xff\xe0rest"), "image/jpeg")
        self.assertEqual(safe_fetch.sniff_image(b"RIFF\x00\x00\x00\x00WEBPVP8 "), "image/webp")
        self.assertIsNone(safe_fetch.sniff_image(b"<svg xmlns='http://www.w3.org/2000/svg'></svg>"))
