import hashlib
import http.server
import json
import threading
import time
import unittest
from unittest import mock

import integrations.navidrome.client as nav_client
from navidrome_client import api_call as legacy_api_call
from integrations.navidrome.client import (
    api_call, cover_art, items,
)


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

    def get(self, url, *, params, extensions=None):
        self.request = {"url": url, "params": params, "extensions": extensions}
        return self.response


class NavidromeClientTests(unittest.TestCase):
    def test_items_normalizes_optional_collection_values(self):
        self.assertEqual(items(None), [])
        self.assertEqual(items("single"), ["single"])
        self.assertEqual(items(["first", "second"]), ["first", "second"])
        self.assertEqual(items([]), [])


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
        self.assertEqual(query["c"], "discair")
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


class NavidromeClientImportCompatibilityTests(unittest.TestCase):
    def test_legacy_module_reexports_packaged_client(self):
        from integrations.navidrome.client import api_call

        self.assertIs(legacy_api_call, api_call)


class _SharedResponse:
    """Answers both a Subsonic JSON call and a cover-art call."""

    status_code = 200
    headers = {"content-type": "image/png"}
    content = b"png-bytes"

    def raise_for_status(self):
        pass

    def json(self):
        return {"subsonic-response": {"status": "ok"}}


class _CountingClient:
    """Stands in for the shared ``httpx.Client``: records each GET and each close."""

    def __init__(self):
        self.urls = []
        self.closed = 0

    def get(self, url, *, params):
        self.urls.append(url)
        return _SharedResponse()

    def close(self):
        self.closed += 1


def _config():
    return ("http://navidrome.test", "listener", "secret")


class SharedNavidromeClientTests(unittest.TestCase):
    def setUp(self):
        nav_client._reset_shared_client()
        self.addCleanup(nav_client._reset_shared_client)

    def test_api_calls_share_one_client_and_leave_it_open(self):
        shared = _CountingClient()
        builds = []
        with mock.patch.object(nav_client, "_build_shared_client",
                               side_effect=lambda: builds.append(1) or shared):
            api_call("ping", _config, salt_factory=lambda: "salt")
            api_call("ping", _config, salt_factory=lambda: "salt")
        self.assertEqual(len(builds), 1)
        self.assertEqual(shared.urls, [
            "http://navidrome.test/rest/ping.view",
            "http://navidrome.test/rest/ping.view",
        ])
        self.assertEqual(shared.closed, 0)

    def test_cover_art_and_api_call_use_the_same_client(self):
        shared = _CountingClient()
        builds = []
        with mock.patch.object(nav_client, "_build_shared_client",
                               side_effect=lambda: builds.append(1) or shared):
            api_call("ping", _config, salt_factory=lambda: "salt")
            content_type, body = cover_art(_config, "cover-1", size=300,
                                           salt_factory=lambda: "salt")
        self.assertEqual((content_type, body), ("image/png", b"png-bytes"))
        self.assertEqual(len(builds), 1)
        self.assertEqual(shared.urls[-1], "http://navidrome.test/rest/getCoverArt.view")
        self.assertEqual(shared.closed, 0)

    def test_explicit_client_factory_bypasses_the_shared_client(self):
        fake = FakeClient(FakeResponse({"subsonic-response": {"status": "ok"}}))
        with mock.patch.object(nav_client, "_build_shared_client") as build:
            result = api_call("ping", _config, client_factory=lambda **kwargs: fake,
                              salt_factory=lambda: "salt")
        build.assert_not_called()
        self.assertEqual(result, {"status": "ok"})

    def test_explicit_client_factory_labels_its_request_navidrome(self):
        # Efficiency M1: a call outside the shared client is counted as navidrome, not by host as other.
        fake = FakeClient(FakeResponse({"subsonic-response": {"status": "ok"}}))
        api_call("ping", _config, client_factory=lambda **kwargs: fake, salt_factory=lambda: "salt")
        self.assertEqual(fake.request["extensions"], {"metrics_provider": "navidrome"})

    def test_explicit_httpx_client_is_counted_as_navidrome(self):
        import httpx

        from app.services import runtime_metrics

        def handler(request):
            return httpx.Response(200, json={"subsonic-response": {"status": "ok"}})

        runtime_metrics.reset()
        self.addCleanup(runtime_metrics.reset)
        api_call("ping", lambda: ("http://192.168.1.20:4533", "listener", "secret"),
                 client_factory=lambda **kwargs: runtime_metrics.MeteredClient(
                     transport=httpx.MockTransport(handler), **kwargs),
                 salt_factory=lambda: "salt")
        requests = runtime_metrics.snapshot()["requests"]
        self.assertEqual(requests["navidrome"]["count"], 1)
        self.assertNotIn("other", requests)

    def test_shared_client_is_built_with_timeout_redirects_and_keepalive_limits(self):
        with mock.patch.object(nav_client.httpx, "Client") as constructor:
            nav_client._build_shared_client()
        options = constructor.call_args.kwargs
        self.assertEqual(options["timeout"], 30)
        self.assertIs(options["follow_redirects"], False)
        self.assertEqual(options["limits"].max_keepalive_connections, 10)
        self.assertEqual(options["limits"].keepalive_expiry, 30.0)

    def test_concurrent_first_use_builds_one_client(self):
        def slow_build():
            builds.append(1)
            time.sleep(0.05)
            return _CountingClient()

        builds = []
        found = []
        threads = [threading.Thread(target=lambda: found.append(nav_client._shared_client()))
                   for _ in range(8)]
        with mock.patch.object(nav_client, "_build_shared_client", side_effect=slow_build):
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        self.assertEqual(len(builds), 1)
        self.assertEqual(len(found), 8)
        self.assertEqual(len({id(client) for client in found}), 1)

    def test_second_call_reuses_the_first_connection(self):
        # A real loopback server: the same client port on both requests means one reused TCP connection.
        ports = []

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self):
                ports.append(self.client_address[1])
                body = json.dumps({"subsonic-response": {"status": "ok"}}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(server.server_close)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.shutdown)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        for _ in range(2):
            api_call("ping", lambda: (base_url, "listener", "secret"), salt_factory=lambda: "salt")

        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0], ports[1])


if __name__ == "__main__":
    unittest.main()
