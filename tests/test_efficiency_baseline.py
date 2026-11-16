"""Tests for scripts/efficiency_baseline.py (efficiency M2).

The end-to-end test runs the script against a stub HTTP server on localhost, not the real app, so it
checks the script's requests, aggregation and output shape only.
"""
import importlib.util
import io
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "efficiency_baseline.py"
spec = importlib.util.spec_from_file_location("efficiency_baseline", SCRIPT)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

PASSWORD = "stub-password-not-real"


class BaselineHelperTests(unittest.TestCase):
    def test_percentile_nearest_rank_and_empty(self):
        values = [10.0, 20.0, 30.0, 40.0]
        self.assertEqual(baseline.percentile(values, 0.5), 20.0)
        self.assertEqual(baseline.percentile(values, 0.95), 40.0)
        self.assertIsNone(baseline.percentile([], 0.95))

    def test_parse_server_timing_reads_dur_only(self):
        self.assertEqual(baseline.parse_server_timing("app;dur=123"), 123.0)
        self.assertIsNone(baseline.parse_server_timing(None))
        self.assertIsNone(baseline.parse_server_timing("db;desc=x"))

    def test_numeric_delta_subtracts_leaves_and_skips_one_sided_keys(self):
        before = {"web": {"requests": 5, "name": "a"}, "gone": 1}
        after = {"web": {"requests": 9, "name": "a"}, "new": 2}
        self.assertEqual(baseline.numeric_delta(before, after), {"web": {"requests": 4}, "new": 2})

    def test_outbound_per_run_attributes_provider_requests_to_one_route(self):
        before = {"web": {"requests": {"other": {"count": 4, "seconds": 1.0, "outcomes": {"ok": 4}}}}, "worker": None}
        after = {"web": {"requests": {
            "other": {"count": 64, "seconds": 9.0, "outcomes": {"ok": 64}},
            "listenbrainz": {"count": 3, "seconds": 0.5, "outcomes": {"ok": 3}},
        }}, "worker": {"requests": {"musicbrainz": {"count": 99, "seconds": 1.0, "outcomes": {"ok": 99}}}}}
        delta = baseline.numeric_delta(before, after)
        # Worker counters are ignored: only the web process is attributed per route.
        self.assertEqual(baseline.outbound_per_run(delta, 20), {"listenbrainz": 0.15, "other": 3.0})
        self.assertEqual(baseline.outbound_per_run(None, 20), {})

    def test_build_routes_labels_carry_no_keys(self):
        routes = baseline.build_routes("Artist Key/with slash", "album-id-123", "artist-id-9", "Artist Name")
        labels = [label for label, _ in routes]
        for label in labels:
            self.assertNotIn("album-id", label)
            self.assertNotIn("Artist", label)
        paths = dict(routes)
        self.assertEqual(paths["artist_page"], "/api/artists/Artist%20Name?id=artist-id-9")
        self.assertIn("kind=album_gaps", paths["knowledge_paths_album_gaps"])

    def test_summarize_counts_statuses_and_server_samples(self):
        stats = baseline.summarize([(10.0, 5.0, 200), (30.0, None, 200), (20.0, 7.0, 500)])
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["statuses"], {"200": 2, "500": 1})
        self.assertEqual(stats["server_median_ms"], 6.0)

    def test_parse_args_requires_keys_and_positive_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "x.json")
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                baseline.parse_args(["--username", "u", "--out", out])
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                baseline.parse_args([
                    "--username", "u", "--artist-key", "a", "--album-key", "b",
                    "--out", out, "--runs", "0",
                ])


class _StubHandler(BaseHTTPRequestHandler):
    served = [0]

    def log_message(self, *args):  # keep test output quiet
        return

    def _send(self, status, body, headers=None):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/auth/login" and payload.get("password") == PASSWORD:
            self._send(200, {"ok": True}, {"Set-Cookie": "navil_session=stub-token; Path=/; HttpOnly"})
        else:
            self._send(401, {"detail": "bad"})

    def do_GET(self):
        if self.headers.get("Cookie") != "navil_session=stub-token":
            self._send(401, {"detail": "Authentication required."})
            return
        if self.path.startswith("/api/diagnostics/runtime"):
            self._send(200, {"web": {"requests": _StubHandler.served[0]}, "worker": None})
            return
        _StubHandler.served[0] += 1
        if self.path.startswith("/api/search"):
            self._send(404, {"detail": "not here"}, {"Server-Timing": "app;dur=3"})
            return
        self._send(200, {"items": []}, {"Server-Timing": "app;dur=4"})


class StubServerBaselineTests(unittest.TestCase):
    def setUp(self):
        _StubHandler.served = [0]
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        _StubHandler.served = [0]

    def test_end_to_end_writes_comparable_json_twice(self):
        outputs = []
        with mock.patch.dict(os.environ, {"NAVI_BASELINE_PASSWORD": PASSWORD}), \
                redirect_stdout(io.StringIO()) as captured, \
                tempfile.TemporaryDirectory() as tmp:
            for name in ("first.json", "second.json"):
                out = Path(tmp) / name
                code = baseline.main([
                    "--base-url", self.base_url, "--username", "owner", "--artist-key", "a1",
                    "--album-key", "b2", "--artist-id", "c3", "--artist-name", "d4", "--runs", "3",
                    "--out", str(out),
                ])
                self.assertEqual(code, 0)
                outputs.append(json.loads(out.read_text(encoding="utf-8")))

        first, second = outputs
        self.assertEqual(set(first["routes"]), set(second["routes"]))
        self.assertEqual(set(first["routes"]), {label for label, _ in baseline.build_routes("a", "b", "c", "d")})
        for stats in first["routes"].values():
            self.assertEqual(stats["count"], 3)
            self.assertIn(stats["server_median_ms"], (3.0, 4.0))
        # 7 routes x 3 runs = 21 app requests; the diagnostics reads themselves are not counted.
        self.assertEqual(first["runtime_delta"], {"web": {"requests": 21}})
        self.assertEqual(second["runtime_delta"], {"web": {"requests": 21}})
        for label in first["routes"]:
            self.assertEqual(first["per_route_runtime"][label], {"web": {"requests": 3}})
        self.assertEqual(set(first["per_route_runtime"]), set(first["routes"]))
        # No keys, password or cookie in the output.
        text = json.dumps(first)
        self.assertNotIn("stub-token", text)
        self.assertNotIn(PASSWORD, text)
        self.assertNotIn("a1", text)
        self.assertNotIn("b2", text)
        table = captured.getvalue()
        self.assertIn("| Route |", table)
        self.assertIn("library_artists", table)
        self.assertIn("Outbound per run", table)

    def test_wrong_password_exits_without_writing(self):
        with mock.patch.dict(os.environ, {"NAVI_BASELINE_PASSWORD": "wrong"}), \
                tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "never.json"
            with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
                baseline.main([
                    "--base-url", self.base_url, "--username", "owner", "--artist-key", "a1",
                    "--album-key", "b2", "--artist-id", "c3", "--artist-name", "d4", "--out", str(out),
                ])
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
