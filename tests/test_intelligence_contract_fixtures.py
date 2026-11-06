"""Server V2 contract fixtures match the builders and carry no secrets (docs/SERVER_V2_CONTRACT.md)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from intelligence.api import build_unresolved_body
from intelligence.api.fixture_set import build_fixtures
from intelligence.resolution import unresolved
from intelligence.store import open_store

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "intelligence" / "contract-fixtures"
sys.path.insert(0, str(ROOT / "scripts"))
from write_intelligence_fixtures import render  # noqa: E402


class FixtureFileTests(unittest.TestCase):
    def test_files_match_the_builders(self):
        built = build_fixtures()
        self.assertEqual(sorted(p.name for p in FIXTURES.glob("*.json")), sorted(built))
        for name, document in built.items():
            with self.subTest(fixture=name):
                self.assertEqual((FIXTURES / name).read_text(encoding="utf-8"), render(document),
                                 "run scripts/write_intelligence_fixtures.py")

    def test_building_twice_gives_the_same_result(self):
        self.assertEqual(build_fixtures(), build_fixtures())

    def test_no_paths_or_credentials(self):
        for path in FIXTURES.glob("*.json"):
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(fixture=path.name):
                for marker in ("/users/", "/music", "password", "token", "cookie", "http://", "https://"):
                    self.assertNotIn(marker, text)

    def test_empty_store_is_not_populated(self):
        caps = json.loads((FIXTURES / "capabilities_empty.json").read_text())["response"]
        for feature in caps["features"].values():
            self.assertFalse(feature["available"])
            self.assertEqual(feature["reason"], "not_populated")

    def test_reset_lists_everything(self):
        reset = json.loads((FIXTURES / "changes_reset.json").read_text())["response"]
        caught_up = json.loads((FIXTURES / "changes_caught_up.json").read_text())["response"]
        self.assertTrue(reset["reset"])
        self.assertEqual(len(reset["changes"]), 2)
        self.assertEqual(caught_up["changes"], [])

    def test_knowledge_fixtures_have_the_public_shape(self):
        internal = {"id", "created_generation", "navidrome_id", "discogs_id", "wikidata_id"}

        def walk(value):
            if isinstance(value, dict):
                for k, v in value.items():
                    yield k, v
                    yield from walk(v)
            elif isinstance(value, list):
                for v in value:
                    yield from walk(v)

        names = sorted(p.name for p in FIXTURES.glob("knowledge_*.json"))
        self.assertEqual(len(names), 11)
        for name in names:
            with self.subTest(fixture=name):
                pairs = list(walk(json.loads((FIXTURES / name).read_text())["response"]))
                self.assertFalse({k for k, _ in pairs} & internal)
                self.assertTrue(all(isinstance(v, bool) for k, v in pairs if k == "owned"))

    def test_connections_fixtures_page_and_stay_bounded(self):
        full, one, two = (json.loads((FIXTURES / f"knowledge_connections{n}.json").read_text())["response"]
                          for n in ("", "_page1", "_page2"))
        self.assertIsNone(full["next_cursor"])
        self.assertIsNotNone(one["next_cursor"])
        self.assertEqual(len(one["hops"]), 2)
        paged = [h["entity"]["mbid"] for h in one["hops"] + two["hops"]]
        self.assertEqual(len(paged), len(set(paged)), "an entity appears once across pages")
        self.assertEqual(paged, [h["entity"]["mbid"] for h in full["hops"]][:len(paged)])
        for hop in full["hops"]:
            self.assertTrue(1 <= hop["depth"] <= 2)
            self.assertIn("via_mbid", hop)

    def test_slice_pending_fixture_says_so(self):
        body = json.loads((FIXTURES / "knowledge_person_slice_pending.json").read_text())["response"]
        self.assertEqual(body["sources"]["musicbrainz_dump"]["coverage"], "pending")


class UnresolvedBodyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "intelligence.sqlite3")
        self.addCleanup(self.db.close)
        for n in range(5):
            unresolved.queue_unresolved(self.db, "album", f"al-{n}", [], "none", now=1.0)

    def test_paging_walks_the_whole_queue_once(self):
        seen, after = [], 0
        while True:
            body = build_unresolved_body(self.db, limit=2, after_id=after)
            seen += [item["navidrome_ref"] for item in body["items"]]
            if body["next_after_id"] is None:
                break
            after = body["next_after_id"]
        self.assertEqual(seen, [f"al-{n}" for n in range(5)])

    def test_limit_is_clamped(self):
        self.assertEqual(len(build_unresolved_body(self.db, limit=0)["items"]), 1)
        self.assertEqual(len(build_unresolved_body(self.db, limit=10_000)["items"]), 5)

    def test_answered_items_leave_the_open_list(self):
        unresolved.reject_all(self.db, 1)
        body = build_unresolved_body(self.db)
        self.assertEqual(body["open_count"], 4)
        self.assertEqual(len(body["items"]), 4)
        self.assertEqual(len(build_unresolved_body(self.db, status=None)["items"]), 5)


if __name__ == "__main__":
    unittest.main()
