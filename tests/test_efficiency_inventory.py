"""Tests for scripts/efficiency_inventory.py (efficiency K1).

The session test runs against a stub HTTP server on localhost, not the real app: it checks the script's
requests, per-request attribution, miss classes, the request cap and the output shape.
"""
import importlib.util
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("efficiency_inventory", SCRIPTS / "efficiency_inventory.py")
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
from efficiency_baseline import Client  # noqa: E402


def record(count=0, seconds=0.0, gate=0.0, cause=None, status=200, pass_number=0):
    providers = {"musicbrainz": {"count": count, "seconds": seconds, "outcomes": {"ok": count}}} if count else {}
    row = {"pass": pass_number, "kind": "owned_album", "route": "album_links", "status": status, "wall_ms": 10.0,
           "providers": providers, "navidrome": 0, "gate_wait_seconds": gate, "gate_refused": 0}
    if cause:
        row["miss_cause"] = cause
    return row


class RouteTests(unittest.TestCase):
    def test_route_sets_per_kind_and_labels_carry_no_names(self):
        owned_album = inventory.routes_for({"kind": "owned_album", "artist": "A B", "artist_key": "a b", "album": "X", "id": "i1"})
        self.assertEqual([label for label, _ in owned_album][0], "album_page")
        self.assertEqual([label for label, _ in owned_album], ["album_page", "album_reviews", "album_links"])
        self.assertIn("/api/albums/a%20b/i1?id=i1", owned_album[0][1])
        unowned = inventory.routes_for({"kind": "unowned_album", "artist": "A", "album": "X", "year": 2020, "mbid": "m1"})
        self.assertIn("year=2020", unowned[0][1])
        self.assertIn("mbid=m1", unowned[0][1])
        self.assertIn("mbid=m1", dict(unowned)["album_links"])
        self.assertEqual([label for label, _ in unowned],
                         ["album_page", "album_details", "album_artwork", "album_reviews", "album_links"])
        self.assertEqual([label for label, _ in inventory.routes_for({"kind": "unowned_artist", "artist": "A"})],
                         ["artist_page", "artist_bio", "artist_image"])
        with self.assertRaises(ValueError):
            inventory.routes_for({"kind": "other", "artist": "A"})


class AttributionTests(unittest.TestCase):
    def test_provider_use_separates_navidrome_and_sums_gate(self):
        use = inventory.provider_use({"web": {
            "requests": {"musicbrainz": {"count": 2, "seconds": 1.5, "outcomes": {"ok": 1, "rate_limited": 1}},
                         "other": {"count": 4, "seconds": 0.2, "outcomes": {"ok": 4}}, "deezer": {"count": 0}},
            "gate": {"musicbrainz": {"reservations": 2, "refused": 1, "wait_seconds": 0.75}}}})
        self.assertEqual(list(use["providers"]), ["musicbrainz"])
        self.assertEqual(use["providers"]["musicbrainz"]["outcomes"], {"ok": 1, "rate_limited": 1})
        self.assertEqual((use["navidrome"], use["gate_wait_seconds"], use["gate_refused"]), (4, 0.75, 1))
        self.assertEqual(inventory.provider_use({})["providers"], {})
        outlets = inventory.provider_use({"web": {"requests": {"other": {"count": 3, "seconds": 2.0, "outcomes": {"ok": 3}}}}}, outlets=True)
        self.assertEqual((outlets["providers"]["review_outlets"]["count"], outlets["navidrome"]), (3, 0))

    def test_classify_miss(self):
        before = {"t:a": 1.0, "t:b": 1.0}
        self.assertEqual(inventory.classify_miss(before, {**before, "t:c": 2.0}, {"ok": 1}), ("never_fetched", []))
        self.assertEqual(inventory.classify_miss(before, {"t:a": 5.5, "t:b": 1.0}, {"ok": 1}), ("expired", [4.5]))
        self.assertEqual(inventory.classify_miss(before, dict(before), {"ok": 1, "timeout": 1}), ("failed_not_cached", []))
        self.assertEqual(inventory.classify_miss(before, dict(before), {"ok": 2}), ("not_cached_ok", []))

    def test_summarize_hit_rate_waits_and_causes(self):
        rows = [record(), record(), record(2, 1.0, 0.5, "never_fetched"), record(1, 3.0, 0.0, "not_cached")]
        out = inventory.summarize(rows)
        self.assertEqual(out["requests"], 4)
        self.assertEqual(out["hit_rate"], 0.5)
        self.assertEqual(out["provider_requests_per_request"], 0.75)
        self.assertEqual(out["by_provider"], {"musicbrainz": 3})
        self.assertEqual(out["provider_seconds_median"], 2.0)
        self.assertEqual(out["provider_seconds_p95"], 3.0)
        self.assertEqual(out["miss_causes"], {"never_fetched": 1, "not_cached": 1})
        timed_out = inventory.summarize([record(status=0), record(status=200)])
        self.assertEqual(timed_out["wall_ms_median"], 10.0)

    def test_build_summary_splits_cold_and_warm(self):
        summary = inventory.build_summary([record(1, 1.0, pass_number=0), record(pass_number=1), record(pass_number=2)])
        group = summary["owned_album/album_links"]
        self.assertEqual((group["cold"]["requests"], group["warm"]["requests"]), (1, 2))
        self.assertEqual(group["warm"]["hit_rate"], 1.0)

    def test_read_cache_rows_reads_tables_read_only_and_tolerates_none(self):
        self.assertEqual(inventory.read_cache_rows(None), {})
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(inventory.read_cache_rows(Path(tmp)), {})
            con = sqlite3.connect(Path(tmp) / "navidrome_metadata_cache.sqlite3")
            con.execute("CREATE TABLE metadata_cache (cache_key TEXT PRIMARY KEY, value_json TEXT, cached_at REAL)")
            con.execute("INSERT INTO metadata_cache VALUES ('k', '{}', 5.0)")
            con.commit()
            con.close()
            self.assertEqual(inventory.read_cache_rows(Path(tmp)), {"metadata_cache:k": 5.0})


class StubHandler(BaseHTTPRequestHandler):
    calls = 0

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.startswith("/api/diagnostics/runtime"):
            body = {"web": {"requests": {"musicbrainz": {"count": StubHandler.calls, "seconds": StubHandler.calls * 0.5,
                                                         "outcomes": {"ok": StubHandler.calls}}}, "gate": {}}}
        else:
            if "baseline" not in self.path and not self.server.cached:
                StubHandler.calls += 1  # a cold request calls the provider once; later ones are cache hits
                self.server.cached = True
            body = {"ok": True}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class SessionTests(unittest.TestCase):
    def setUp(self):
        StubHandler.calls = 0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), StubHandler)
        self.server.cached = False
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.client = Client(f"http://127.0.0.1:{self.server.server_address[1]}")
        self.client.cookie = "navil_session=stub"
        self.addCleanup(self.server.shutdown)
        self.addCleanup(self.server.server_close)

    def test_cold_then_warm_attribution(self):
        targets = [{"kind": "unowned_artist", "artist": "A"}]
        result = inventory.run_session(self.client, targets, 2, None, 100, log=lambda *_: None)
        self.assertFalse(result["stopped_at_cap"])
        self.assertEqual(len(result["records"]), 9)  # 3 routes, 1 cold + 2 warm passes
        self.assertEqual(result["provider_requests"], 1)
        self.assertEqual(sum(total for total in map(inventory.total_provider_requests, result["records"][3:])), 0)
        summary = inventory.build_summary(result["records"])
        self.assertEqual(summary["unowned_artist/artist_page"]["cold"]["by_provider"], {"musicbrainz": 1})
        self.assertEqual(summary["unowned_artist/artist_page"]["warm"]["hit_rate"], 1.0)

    def test_settled_runtime_waits_until_provider_counts_stop_moving(self):
        StubHandler.calls = 0
        reads = iter([1, 2, 2])  # a late provider call lands twice, then the counter is still

        def late_sleep(_):
            StubHandler.calls = next(reads)

        snapshot = inventory.settled_runtime(self.client, 0.1, 5.0, sleep=late_sleep)
        self.assertEqual(inventory.provider_counts(snapshot), {"musicbrainz": 2})

    def test_request_cap_stops_the_session(self):
        StubHandler.calls = 0
        self.server.cached = False
        result = inventory.run_session(self.client, [{"kind": "unowned_artist", "artist": "A"}], 2, None, 0, log=lambda *_: None)
        self.assertTrue(result["stopped_at_cap"])
        self.assertLess(len(result["records"]), 9)


if __name__ == "__main__":
    unittest.main()
