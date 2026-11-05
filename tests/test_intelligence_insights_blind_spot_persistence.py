import tempfile
import unittest
from pathlib import Path

from intelligence.insights import (
    BlindSpotsConfig, ComparisonSet, SetItem, dismiss_blind_spot, dismissed_set_keys, find_blind_spots,
    list_blind_spot_cards, restore_blind_spot, save_blind_spots,
)
from intelligence.insights.blind_spots import dismiss_key
from intelligence.store import generations, open_store

CFG = BlindSpotsConfig(min_set_size=3, min_owned=1)


def mk(key, n=4):
    items = tuple(SetItem(f"{key}-{i}", f"T{i}", 2000 + i) for i in range(n))
    return ComparisonSet(key, "series", key.upper(), items)


def run(db, keys, owned_each=1):
    sets = [mk(k) for k in keys]
    owned = [f"{k}-{i}" for k in keys for i in range(owned_each)]
    return save_blind_spots(db, find_blind_spots(sets, owned, CFG, dismissed_set_keys(db)), now=1.0)


class BlindSpotPersistenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)

    def keys(self):
        return [c["subject"]["key"] for c in list_blind_spot_cards(self.db)]

    def test_saved_cards_come_back_fullest_first(self):
        sets = [mk("a"), mk("b")]
        owned = ["a-0", "b-0", "b-1", "b-2"]
        save_blind_spots(self.db, find_blind_spots(sets, owned, CFG), now=1.0)
        self.assertEqual(self.keys(), [dismiss_key("b"), dismiss_key("a")])

    def test_refresh_replaces_live_cards(self):
        run(self.db, ["a", "b"])
        run(self.db, ["c"])
        self.assertEqual(self.keys(), [dismiss_key("c")])

    def test_empty_result_clears_stale_cards(self):
        run(self.db, ["a"])
        save_blind_spots(self.db, find_blind_spots([], [], CFG), now=1.0)
        self.assertEqual(self.keys(), [])

    def test_dismissal_hides_card_and_survives_refresh(self):
        run(self.db, ["a", "b"])
        self.assertTrue(dismiss_blind_spot(self.db, "b"))
        self.assertEqual(self.keys(), [dismiss_key("a")])
        run(self.db, ["a", "b"])
        self.assertEqual(self.keys(), [dismiss_key("a")])
        self.assertEqual(dismissed_set_keys(self.db), {dismiss_key("b")})

    def test_dismissing_twice_reports_false(self):
        run(self.db, ["a"])
        self.assertTrue(dismiss_blind_spot(self.db, "a"))
        self.assertFalse(dismiss_blind_spot(self.db, "a"))

    def test_dismissing_a_set_with_no_live_card_still_suppresses_it(self):
        self.assertTrue(dismiss_blind_spot(self.db, "x"))
        run(self.db, ["x", "y"])
        self.assertEqual(self.keys(), [dismiss_key("y")])

    def test_restore_brings_the_set_back_on_next_refresh(self):
        run(self.db, ["a"])
        dismiss_blind_spot(self.db, "a")
        self.assertTrue(restore_blind_spot(self.db, "a"))
        self.assertFalse(restore_blind_spot(self.db, "a"))
        run(self.db, ["a"])
        self.assertEqual(self.keys(), [dismiss_key("a")])

    def test_cards_keep_reasons_and_generation(self):
        run(self.db, ["a"])
        row = self.db.execute("SELECT reasons_json, generation, subject_id FROM insights").fetchone()
        self.assertIn("comparison_set", row["reasons_json"])
        self.assertEqual((row["generation"], row["subject_id"]), (generations.current_generation(self.db), None))

    def test_writes_bump_the_insights_data_version(self):
        before = generations.data_version(self.db, "insights")
        run(self.db, ["a"])
        dismiss_blind_spot(self.db, "a")
        self.assertEqual(generations.data_version(self.db, "insights"), before + 2)

    def test_other_kinds_including_gems_are_untouched(self):
        for kind in ("other", "forgotten_gem"):
            self.db.execute(
                "INSERT INTO insights (kind, payload, generation, computed_at) VALUES (?, '{}', 1, 0)", (kind,))
        self.db.commit()
        run(self.db, ["a"])
        dismiss_blind_spot(self.db, "a")
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM insights WHERE kind IN ('other','forgotten_gem')").fetchone()[0], 2)
