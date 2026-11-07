import tempfile
import unittest
from pathlib import Path

from intelligence.api import (
    CONTRACT_VERSION, ChangesError, ServerFacts, build_capabilities, build_changes,
    etag_for, not_modified, parse_since,
)
from intelligence.store import LATEST_VERSION, generations, open_store


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db = open_store(Path(self.temp_dir.name) / "intelligence.sqlite3")
        self.addCleanup(self.db.close)


class ChangeSequenceTests(ApiTestCase):
    def test_sequence_starts_at_zero_and_advances_per_bump(self):
        self.assertEqual(generations.change_seq(self.db), 0)
        generations.bump_data_version(self.db, "health")
        generations.bump_data_version(self.db, "health")
        generations.bump_data_version(self.db, "unresolved")
        self.assertEqual(generations.change_seq(self.db), 3)
        self.assertEqual(generations.data_versions(self.db), {"health": 2, "unresolved": 1})

    def test_changed_since_reports_latest_stamp_per_resource(self):
        generations.bump_data_version(self.db, "health")      # seq 1
        generations.bump_data_version(self.db, "unresolved")  # seq 2
        generations.bump_data_version(self.db, "health")      # seq 3
        self.assertEqual(generations.changed_since(self.db, 0), {"health": 3, "unresolved": 2})
        self.assertEqual(generations.changed_since(self.db, 2), {"health": 3})
        self.assertEqual(generations.changed_since(self.db, 3), {})

    def test_failed_bump_leaves_sequence_untouched(self):
        with self.assertRaises(ValueError):
            generations.bump_data_version(self.db, "bad:name")
        self.assertEqual(generations.change_seq(self.db), 0)


class EtagTests(unittest.TestCase):
    def test_tag_changes_with_version_and_generation(self):
        self.assertEqual(etag_for("health", 2, 1), 'W/"health-1-2"')
        self.assertNotEqual(etag_for("health", 2, 1), etag_for("health", 3, 1))
        self.assertNotEqual(etag_for("health", 2, 1), etag_for("health", 2, 2))

    def test_matching_header_forms(self):
        tag = etag_for("health", 2, 1)
        self.assertTrue(not_modified(tag, tag))
        self.assertTrue(not_modified('"health-1-2"', tag))  # weak comparison
        self.assertTrue(not_modified('W/"other", ' + tag, tag))
        self.assertTrue(not_modified("*", tag))

    def test_non_matching_or_missing_header_sends_body(self):
        tag = etag_for("health", 2, 1)
        self.assertFalse(not_modified(None, tag))
        self.assertFalse(not_modified("  ", tag))
        self.assertFalse(not_modified(etag_for("health", 1, 1), tag))


class ChangesTests(ApiTestCase):
    def test_empty_store(self):
        self.assertEqual(
            build_changes(self.db),
            {"cursor": 0, "reset": False, "generation": 1, "changes": []},
        )

    def test_lists_changes_oldest_first_and_new_cursor(self):
        generations.bump_data_version(self.db, "unresolved")
        generations.bump_data_version(self.db, "health")
        body = build_changes(self.db, 0)
        self.assertEqual(body["cursor"], 2)
        self.assertEqual([c["resource"] for c in body["changes"]], ["unresolved", "health"])
        self.assertEqual(body["changes"][1], {"resource": "health", "data_version": 1, "changed_at": 2})

    def test_only_changes_after_cursor(self):
        generations.bump_data_version(self.db, "unresolved")
        cursor = build_changes(self.db)["cursor"]
        generations.bump_data_version(self.db, "health")
        body = build_changes(self.db, cursor)
        self.assertEqual([c["resource"] for c in body["changes"]], ["health"])
        self.assertEqual(build_changes(self.db, body["cursor"])["changes"], [])

    def test_cursor_ahead_of_server_resets(self):
        generations.bump_data_version(self.db, "health")
        body = build_changes(self.db, 99)
        self.assertTrue(body["reset"])
        self.assertEqual([c["resource"] for c in body["changes"]], ["health"])
        self.assertEqual(body["cursor"], 1)

    def test_parse_since(self):
        self.assertEqual(parse_since(None), 0)
        self.assertEqual(parse_since(""), 0)
        self.assertEqual(parse_since("7"), 7)
        self.assertEqual(parse_since(7), 7)
        for bad in ("abc", "-1", "1.5", True):
            with self.assertRaises(ChangesError):
                parse_since(bad)


class CapabilitiesTests(ApiTestCase):
    def test_fresh_store_reports_nothing_populated(self):
        body = build_capabilities(self.db)
        self.assertEqual(body["contract_version"], CONTRACT_VERSION)
        self.assertEqual(body["schema_version"], LATEST_VERSION)
        self.assertEqual(body["generation"], 1)
        self.assertEqual(body["cursor"], 0)
        self.assertEqual(body["graph_coverage"], "none")
        self.assertFalse(body["sonic_available"])
        self.assertFalse(body["listenbrainz_connected"])
        self.assertEqual(body["data_versions"], {})
        for feature in body["features"].values():
            self.assertFalse(feature["available"])
            self.assertEqual(feature["reason"], "not_populated")

    def test_feature_becomes_available_when_its_resource_changes(self):
        generations.bump_data_version(self.db, "health")
        body = build_capabilities(self.db)
        self.assertEqual(
            body["features"]["library_health"],
            {"available": True, "resource": "health", "data_version": 1},
        )
        self.assertFalse(body["features"]["unresolved_queue"]["available"])
        self.assertEqual(body["data_versions"], {"health": 1})
        self.assertEqual(body["cursor"], 1)

    def test_paths_feature_follows_the_musicbrainz_slice(self):
        self.assertEqual(
            build_capabilities(self.db)["features"]["paths"],
            {"available": False, "resource": "musicbrainz_slice", "data_version": 0, "reason": "not_populated"},
        )
        generations.bump_data_version(self.db, "musicbrainz_slice")
        self.assertEqual(
            build_capabilities(self.db)["features"]["paths"],
            {"available": True, "resource": "musicbrainz_slice", "data_version": 1},
        )

    def test_server_facts_are_passed_through_and_coverage_is_validated(self):
        body = build_capabilities(
            self.db, ServerFacts(sonic_available=True, listenbrainz_connected=True, graph_coverage="partial")
        )
        self.assertTrue(body["sonic_available"])
        self.assertTrue(body["listenbrainz_connected"])
        self.assertEqual(body["graph_coverage"], "partial")
        self.assertEqual(build_capabilities(self.db, ServerFacts(graph_coverage="huge"))["graph_coverage"], "none")

    def test_body_exposes_no_file_paths_or_secrets(self):
        # The feature name "paths" is a route concept, not a file path: only separators are refused.
        text = str(build_capabilities(self.db)).lower()
        for word in ("/", "\\", "token", "password", "sqlite"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()
