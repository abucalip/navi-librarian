"""Tests for scripts/efficiency_baseline.py (efficiency M2).

The end-to-end test runs the script against a stub HTTP server on localhost, not the real app, so it
checks the script's requests, aggregation and output shape only.
"""
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "efficiency_baseline.py"
spec = importlib.util.spec_from_file_location("efficiency_baseline", SCRIPT)
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

PASSWORD = "stub-password-not-real"


def test_percentile_nearest_rank_and_empty():
    values = [10.0, 20.0, 30.0, 40.0]
    assert baseline.percentile(values, 0.5) == 20.0
    assert baseline.percentile(values, 0.95) == 40.0
    assert baseline.percentile([], 0.95) is None


def test_parse_server_timing_reads_dur_only():
    assert baseline.parse_server_timing("app;dur=123") == 123.0
    assert baseline.parse_server_timing(None) is None
    assert baseline.parse_server_timing("db;desc=x") is None


def test_numeric_delta_subtracts_leaves_and_skips_one_sided_keys():
    before = {"web": {"requests": 5, "name": "a"}, "gone": 1}
    after = {"web": {"requests": 9, "name": "a"}, "new": 2}
    assert baseline.numeric_delta(before, after) == {"web": {"requests": 4}}


def test_build_routes_labels_carry_no_keys():
    routes = baseline.build_routes("Artist Key/with slash", "album-id-123")
    labels = [label for label, _ in routes]
    assert all("album-id" not in label and "Artist" not in label for label in labels)
    paths = dict(routes)
    assert paths["artist_page"] == "/api/artists/Artist%20Key%2Fwith%20slash"
    assert "kind=album_gaps" in paths["knowledge_paths_album_gaps"]


def test_summarize_counts_statuses_and_server_samples():
    stats = baseline.summarize([(10.0, 5.0, 200), (30.0, None, 200), (20.0, 7.0, 500)])
    assert stats["count"] == 3
    assert stats["statuses"] == {"200": 2, "500": 1}
    assert stats["server_median_ms"] == 6.0


def test_parse_args_requires_keys_and_positive_runs(tmp_path):
    with pytest.raises(SystemExit):
        baseline.parse_args(["--username", "u", "--out", str(tmp_path / "x.json")])
    with pytest.raises(SystemExit):
        baseline.parse_args([
            "--username", "u", "--artist-key", "a", "--album-key", "b",
            "--out", str(tmp_path / "x.json"), "--runs", "0",
        ])


class _StubHandler(BaseHTTPRequestHandler):
    snapshots = [0]

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
            _StubHandler.snapshots[0] += 1
            self._send(200, {"web": {"requests": _StubHandler.snapshots[0] * 10}, "worker": None})
            return
        if self.path.startswith("/api/search"):
            self._send(404, {"detail": "not here"}, {"Server-Timing": "app;dur=3"})
            return
        self._send(200, {"items": []}, {"Server-Timing": "app;dur=4"})


@pytest.fixture()
def stub_server():
    _StubHandler.snapshots = [0]
    server = ThreadingHTTPServer(("127.0.0.1", 0), _StubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def test_end_to_end_writes_comparable_json_twice(stub_server, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("NAVI_BASELINE_PASSWORD", PASSWORD)
    outputs = []
    for name in ("first.json", "second.json"):
        out = tmp_path / name
        code = baseline.main([
            "--base-url", stub_server, "--username", "owner", "--artist-key", "a1",
            "--album-key", "b2", "--runs", "3", "--out", str(out),
        ])
        assert code == 0
        outputs.append(json.loads(out.read_text(encoding="utf-8")))

    first, second = outputs
    assert set(first["routes"]) == set(second["routes"]) == {label for label, _ in baseline.build_routes("a", "b")}
    for stats in first["routes"].values():
        assert stats["count"] == 3
        assert stats["server_median_ms"] in (3.0, 4.0)
    assert first["runtime_delta"] == {"web": {"requests": 10}}
    assert second["runtime_delta"] == {"web": {"requests": 10}}
    # No keys, password or cookie in the output.
    text = json.dumps(first)
    assert "stub-token" not in text and PASSWORD not in text and "a1" not in text and "b2" not in text
    table = capsys.readouterr().out
    assert "| Route |" in table and "library_artists" in table


def test_wrong_password_exits_without_writing(stub_server, tmp_path, monkeypatch):
    monkeypatch.setenv("NAVI_BASELINE_PASSWORD", "wrong")
    out = tmp_path / "never.json"
    with pytest.raises(SystemExit):
        baseline.main([
            "--base-url", stub_server, "--username", "owner", "--artist-key", "a1",
            "--album-key", "b2", "--out", str(out),
        ])
    assert not out.exists()
