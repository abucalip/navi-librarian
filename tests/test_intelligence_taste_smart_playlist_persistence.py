import json
import math
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from intelligence.store import open_store
from intelligence.store.state import STATE_LATEST, STATE_MIGRATIONS, default_state_path
from intelligence.taste.smart_playlist_persistence import (
    CREATED, REJECTED, REPLACED, UNCHANGED, delete, get, list_playlists, put, valid_rule_id,
)

NOW = 1_800_000_000.0


def rid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, str(name)))


def raw_set(name="Late 80s", **overrides):
    base = {
        "name": name,
        "match": "all",
        "rules": [{"field": "year", "op": "at_least", "value": "1985"}],
        "order": "newest_added",
        "limit": 50,
    }
    base.update(overrides)
    return base


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "intelligence.sqlite3"
        self.db = open_store(self.path)
        self.addCleanup(self.db.close)

    def row_count(self):
        return self.db.execute("SELECT COUNT(*) FROM state.smart_playlists").fetchone()[0]


class MigrationThreeTests(StoreTestCase):
    def test_fresh_store_gets_table_in_owner_state_file_at_version_three(self):
        self.assertGreaterEqual(STATE_LATEST, 3)
        self.assertEqual(self.db.execute("PRAGMA state.user_version").fetchone()[0], STATE_LATEST)
        state_tables = {r[0] for r in self.db.execute("SELECT name FROM state.sqlite_master WHERE type = 'table'")}
        self.assertIn("smart_playlists", state_tables)
        main_tables = {r[0] for r in self.db.execute("SELECT name FROM main.sqlite_master WHERE type = 'table'")}
        self.assertNotIn("smart_playlists", main_tables)

    def test_shape_checks_refuse_bad_rows_at_the_database(self):
        bad_rows = [
            ("uppercase id", dict(rule_id=rid("x").upper())),
            ("bad match", dict(match="some")),
            ("bad order", dict(order="shuffle")),
            ("limit below 25", dict(limit=10)),
            ("empty name", dict(name="")),
            ("rules not an array", dict(rules='{"a":1}')),
        ]
        for label, overrides in bad_rows:
            values = dict(rule_id=rid("row"), name="n", match="all", rules="[]", order="title",
                          limit=None, created_at=1.0, updated_at=1.0)
            values.update(overrides)
            with self.subTest(label=label), self.assertRaises(sqlite3.IntegrityError):
                self.db.execute(
                    "INSERT INTO state.smart_playlists (rule_id, name, \"match\", rules, \"order\", \"limit\", "
                    "created_at, updated_at) VALUES (:rule_id, :name, :match, :rules, :order, :limit, "
                    ":created_at, :updated_at)", values)
            self.db.rollback()

    def test_already_migrated_file_reopens_without_remigrating(self):
        self.assertEqual(put(self.db, rid("keep"), raw_set(), NOW).status, CREATED)
        self.db.close()
        reopened = open_store(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.execute("PRAGMA state.user_version").fetchone()[0], STATE_LATEST)
        self.assertEqual(get(reopened, rid("keep")).name, "Late 80s")

    def test_version_two_state_file_migrates_to_three_and_keeps_its_rows(self):
        dir_path = Path(self.dir.name) / "v2"
        dir_path.mkdir()
        knowledge = dir_path / "intelligence.sqlite3"
        raw = sqlite3.connect(default_state_path(knowledge))
        for _number, _name, statements in STATE_MIGRATIONS[:2]:
            for statement in statements:
                raw.execute(statement.replace("state.", ""))
        raw.execute("PRAGMA user_version = 2")
        raw.commit()
        raw.close()

        db = open_store(knowledge)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("PRAGMA state.user_version").fetchone()[0], STATE_LATEST)
        self.assertEqual(put(db, rid("after"), raw_set(), NOW).status, CREATED)


class PutTests(StoreTestCase):
    def test_create_stores_canonical_content_with_both_stamps_set_to_now(self):
        outcome = put(self.db, rid("a"), raw_set("  Late 80s  "), NOW)
        self.assertEqual(outcome.status, CREATED)
        stored = get(self.db, rid("a"))
        self.assertEqual(stored.name, "Late 80s")
        self.assertEqual(stored.match, "all")
        self.assertEqual(stored.rules[0].field, "year")
        self.assertEqual((stored.order, stored.limit), ("newest_added", 50))
        self.assertEqual((stored.created_at, stored.updated_at), (NOW, NOW))

    def test_replaying_the_same_put_changes_nothing(self):
        put(self.db, rid("a"), raw_set(), NOW)
        before = self.db.execute("SELECT * FROM state.smart_playlists").fetchall()
        outcome = put(self.db, rid("a"), raw_set(), NOW + 500)
        self.assertEqual(outcome.status, UNCHANGED)
        self.assertEqual(self.db.execute("SELECT * FROM state.smart_playlists").fetchall(), before)
        self.assertEqual(self.row_count(), 1)

    def test_replace_keeps_created_at_and_moves_updated_at(self):
        put(self.db, rid("a"), raw_set(), NOW)
        outcome = put(self.db, rid("a"), raw_set(name="Renamed", limit=None), NOW + 60)
        self.assertEqual(outcome.status, REPLACED)
        stored = get(self.db, rid("a"))
        self.assertEqual((stored.name, stored.limit), ("Renamed", None))
        self.assertEqual(stored.created_at, NOW)
        self.assertEqual(stored.updated_at, NOW + 60)
        self.assertEqual(self.row_count(), 1)

    def test_rules_are_stored_as_json_array_and_round_trip(self):
        rules = [{"field": "artist", "op": "contains", "value": "Björk"},
                 {"field": "obscurity_band", "op": "not_equals", "value": "mainstream"}]
        put(self.db, rid("j"), raw_set(rules=rules), NOW)
        raw_text = self.db.execute("SELECT rules FROM state.smart_playlists").fetchone()[0]
        self.assertEqual(json.loads(raw_text), rules)
        self.assertEqual([r.field for r in get(self.db, rid("j")).rules], ["artist", "obscurity_band"])


class RejectionTests(StoreTestCase):
    def setUp(self):
        super().setUp()
        put(self.db, rid("existing"), raw_set(), NOW)

    def assertRejected(self, outcome, reason_path=None):
        self.assertEqual(outcome.status, REJECTED)
        self.assertTrue(outcome.errors)
        if reason_path is not None:
            self.assertIn(reason_path, [(e.path, e.reason) for e in outcome.errors])

    def test_malformed_ids_are_rejected_without_writing(self):
        bad_ids = [rid("x").upper(), "not-a-uuid", "", 42, None, rid("x")[:-1], rid("x") + " "]
        for bad in bad_ids:
            with self.subTest(bad=bad):
                self.assertRejected(put(self.db, bad, raw_set(), NOW), ("rule_id", "bad_rule_id"))
        self.assertEqual(self.row_count(), 1)

    def test_bad_clock_is_rejected_without_writing(self):
        for bad in (0, -5, math.nan, math.inf, True, "1800000000", None):
            with self.subTest(clock=bad):
                self.assertRejected(put(self.db, rid("new"), raw_set(), bad), ("now", "bad_clock"))
        self.assertIsNone(get(self.db, rid("new")))

    def test_invalid_rule_sets_are_rejected_with_reasons_and_write_nothing(self):
        cases = [
            (raw_set(name="   "), ("name", "bad_name")),
            (raw_set(match="some"), ("match", "bad_match")),
            (raw_set(order="shuffle"), ("order", "bad_order")),
            (raw_set(limit=10), ("limit", "bad_limit")),
            (raw_set(rules=[{"field": "mood", "op": "equals", "value": "x"}]), ("rules[0].field", "bad_field")),
            (raw_set(rules=[{"field": "year", "op": "contains", "value": "19"}]), ("rules[0].op", "bad_op")),
            (raw_set(rules=[{"field": "year", "op": "at_least", "value": 1985}]), ("rules[0].value", "bad_value")),
            (raw_set(rules=[{"field": "year", "op": "at_least", "value": "1"}] * 21), ("rules", "too_many_rules")),
            ("just a string", ("", "not_an_object")),
            (None, ("", "not_an_object")),
        ]
        for raw, expected in cases:
            with self.subTest(expected=expected):
                self.assertRejected(put(self.db, rid("bad"), raw, NOW), expected)
        self.assertIsNone(get(self.db, rid("bad")))

    def test_rejected_replace_leaves_the_stored_set_untouched(self):
        before = get(self.db, rid("existing"))
        self.assertRejected(put(self.db, rid("existing"), raw_set(order="shuffle"), NOW + 9))
        self.assertEqual(get(self.db, rid("existing")), before)


class ReadAndDeleteTests(StoreTestCase):
    def test_list_is_oldest_first_with_rule_id_as_tie_break(self):
        put(self.db, rid("c"), raw_set("C"), NOW + 20)
        put(self.db, rid("b"), raw_set("B"), NOW + 10)
        put(self.db, rid("a"), raw_set("A"), NOW + 10)
        put(self.db, rid("d"), raw_set("D"), NOW)
        order = [p.name for p in list_playlists(self.db)]
        expected_ties = sorted([(rid("a"), "A"), (rid("b"), "B")])
        self.assertEqual(order, ["D", expected_ties[0][1], expected_ties[1][1], "C"])
        self.assertEqual([p.name for p in list_playlists(self.db)], order)

    def test_list_keeps_created_at_order_after_a_replace(self):
        put(self.db, rid("old"), raw_set("Old"), NOW)
        put(self.db, rid("new"), raw_set("New"), NOW + 5)
        put(self.db, rid("old"), raw_set("Old renamed"), NOW + 99)
        self.assertEqual([p.name for p in list_playlists(self.db)], ["Old renamed", "New"])

    def test_get_returns_none_for_unknown_or_malformed_ids(self):
        self.assertIsNone(get(self.db, rid("nobody")))
        self.assertIsNone(get(self.db, "NOT A UUID"))
        self.assertIsNone(get(self.db, None))

    def test_delete_reports_whether_a_row_existed(self):
        put(self.db, rid("gone"), raw_set(), NOW)
        self.assertTrue(delete(self.db, rid("gone")))
        self.assertFalse(delete(self.db, rid("gone")))
        self.assertIsNone(get(self.db, rid("gone")))

    def test_delete_of_malformed_id_is_false_and_removes_nothing(self):
        put(self.db, rid("keep"), raw_set(), NOW)
        self.assertFalse(delete(self.db, "BAD"))
        self.assertFalse(delete(self.db, 7))
        self.assertEqual(self.row_count(), 1)

    def test_valid_rule_id_accepts_only_canonical_lowercase_uuids(self):
        self.assertTrue(valid_rule_id(rid("ok")))
        self.assertFalse(valid_rule_id(rid("ok").replace("-", "")))
        self.assertFalse(valid_rule_id(b"x"))


if __name__ == "__main__":
    unittest.main()
