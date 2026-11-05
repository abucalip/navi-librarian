import tempfile
import unittest
from pathlib import Path

from intelligence.insights import (
    GemsConfig, PlayRecord, dismiss_gem, dismissed_keys, find_forgotten_gems, list_gem_cards,
    restore_gem, save_gems,
)
from intelligence.store import generations, open_store

NOW = 1_800_000_000.0
DAY = 86400.0


def rec(key, plays=10, days=800):
    return PlayRecord(key, "album", key.upper(), "Artist", plays, NOW - days * DAY)


def run(db, keys):
    result = find_forgotten_gems(
        [rec(k, plays=10 + i) for i, k in enumerate(keys)],
        GemsConfig(now=NOW, min_records_with_history=1), dismissed_keys(db),
    )
    return save_gems(db, result, now=NOW)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)

    def keys(self):
        return [c["subject"]["key"] for c in list_gem_cards(self.db)]

    def test_saved_cards_come_back_best_first(self):
        self.assertEqual(run(self.db, ["a", "b", "c"]), 3)
        self.assertEqual(self.keys(), ["c", "b", "a"])

    def test_refresh_replaces_live_cards(self):
        run(self.db, ["a", "b"])
        run(self.db, ["c"])
        self.assertEqual(self.keys(), ["c"])

    def test_empty_result_clears_stale_cards(self):
        run(self.db, ["a"])
        save_gems(self.db, find_forgotten_gems([], GemsConfig(now=NOW)), now=NOW)
        self.assertEqual(self.keys(), [])

    def test_dismissal_hides_card_and_survives_refresh(self):
        run(self.db, ["a", "b"])
        self.assertTrue(dismiss_gem(self.db, "b", now=NOW))
        self.assertEqual(self.keys(), ["a"])
        run(self.db, ["a", "b"])
        self.assertEqual(self.keys(), ["a"])
        self.assertEqual(dismissed_keys(self.db), {"b"})

    def test_dismissing_twice_reports_false(self):
        run(self.db, ["a"])
        self.assertTrue(dismiss_gem(self.db, "a"))
        self.assertFalse(dismiss_gem(self.db, "a"))

    def test_dismissing_a_card_that_is_gone_still_suppresses_it(self):
        self.assertTrue(dismiss_gem(self.db, "x", now=NOW))
        run(self.db, ["x", "y"])
        self.assertEqual(self.keys(), ["y"])

    def test_restore_brings_the_gem_back_on_next_refresh(self):
        run(self.db, ["a"])
        dismiss_gem(self.db, "a")
        self.assertTrue(restore_gem(self.db, "a"))
        self.assertFalse(restore_gem(self.db, "a"))
        run(self.db, ["a"])
        self.assertEqual(self.keys(), ["a"])

    def test_cards_keep_reasons_and_generation(self):
        run(self.db, ["a"])
        row = self.db.execute("SELECT reasons_json, generation, subject_id FROM insights").fetchone()
        self.assertIn("dormant", row["reasons_json"])
        self.assertEqual((row["generation"], row["subject_id"]), (generations.current_generation(self.db), None))

    def test_writes_bump_the_insights_data_version(self):
        before = generations.data_version(self.db, "insights")
        run(self.db, ["a"])
        dismiss_gem(self.db, "a")
        self.assertEqual(generations.data_version(self.db, "insights"), before + 2)

    def test_other_insight_kinds_are_untouched(self):
        self.db.execute(
            "INSERT INTO insights (kind, payload, generation, computed_at) VALUES ('other', '{}', 1, 0)"
        )
        self.db.commit()
        run(self.db, ["a"])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM insights WHERE kind = 'other'").fetchone()[0], 1)
