import tempfile
import unittest
from datetime import date
from pathlib import Path

from intelligence.insights import (
    AnniversaryConfig, CanonConfig, ComparisonSet, DatedAlbum, SeriesConfig, SetItem, WorldAlbum,
    dismiss_anniversary, dismiss_canon, dismiss_series, dismissed_anniversary_keys, dismissed_canon_keys,
    dismissed_series_keys, find_anniversaries, find_hidden_canon, find_series_progress, list_anniversary_cards,
    list_canon_cards, list_series_cards, restore_anniversary, restore_canon, restore_series, save_anniversaries,
    save_canon, save_series,
)
from intelligence.insights import anniversaries as ann, hidden_canon as hc, series_completion as sc
from intelligence.store import generations, open_store

TODAY = date(2026, 6, 1)


def series(key, n=4):
    return ComparisonSet(key, "series", key.upper(), tuple(SetItem(f"{key}-{i}", f"T{i}", 2000 + i) for i in range(n)))


def run_series(db, keys, owned=1):
    sets = [series(k) for k in keys]
    own = [f"{k}-{i}" for k in keys for i in range(owned)]
    return save_series(db, find_series_progress(sets, own, SeriesConfig(), dismissed_series_keys(db)), now=1.0)


def world(mbid, artist="A", listens=5000):
    return WorldAlbum(mbid, f"T-{mbid}", artist, 1999, ("shoegaze", "dream pop"), listens)


def run_canon(db, mbids):
    res = find_hidden_canon([world(m, artist=m) for m in mbids], [], ["shoegaze", "dream pop"],
                            CanonConfig(), dismissed_canon_keys(db))
    return save_canon(db, res, now=1.0)


def run_ann(db, mbids):
    albums = [DatedAlbum(m, f"T-{m}", "A", "2016-06-01") for m in mbids]
    res = find_anniversaries(albums, [], TODAY, AnniversaryConfig(), dismissed_anniversary_keys(db))
    return save_anniversaries(db, res, now=1.0)


class CardPersistenceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)

    def keys(self, listing):
        return [c["subject"]["key"] for c in listing(self.db)]

    # series
    def test_series_refresh_replaces_and_empty_clears(self):
        run_series(self.db, ["a", "b"])
        run_series(self.db, ["c"])
        self.assertEqual(self.keys(list_series_cards), [sc.dismiss_key("c")])
        save_series(self.db, find_series_progress([], []), now=1.0)
        self.assertEqual(self.keys(list_series_cards), [])

    def test_series_closest_to_finished_first(self):
        save_series(self.db, find_series_progress([series("a"), series("b")], ["a-0", "b-0", "b-1", "b-2"],
                                                  SeriesConfig()), now=1.0)
        self.assertEqual(self.keys(list_series_cards), [sc.dismiss_key("b"), sc.dismiss_key("a")])

    def test_series_dismiss_survives_refresh_and_restores(self):
        run_series(self.db, ["a", "b"])
        self.assertTrue(dismiss_series(self.db, sc.dismiss_key("b")))
        self.assertFalse(dismiss_series(self.db, sc.dismiss_key("b")))
        run_series(self.db, ["a", "b"])
        self.assertEqual(self.keys(list_series_cards), [sc.dismiss_key("a")])
        self.assertTrue(restore_series(self.db, sc.dismiss_key("b")))
        self.assertFalse(restore_series(self.db, sc.dismiss_key("b")))
        run_series(self.db, ["a", "b"])
        self.assertEqual(len(list_series_cards(self.db)), 2)

    def test_series_tombstone_suppresses_unseen_series(self):
        self.assertTrue(dismiss_series(self.db, sc.dismiss_key("x")))
        run_series(self.db, ["x", "y"])
        self.assertEqual(self.keys(list_series_cards), [sc.dismiss_key("y")])

    # hidden canon
    def test_canon_save_list_dismiss_restore(self):
        self.assertEqual(run_canon(self.db, ["m1", "m2"]), 2)
        self.assertEqual(len(list_canon_cards(self.db)), 2)
        self.assertTrue(dismiss_canon(self.db, hc.dismiss_key("m1")))
        run_canon(self.db, ["m1", "m2"])
        self.assertEqual(self.keys(list_canon_cards), [hc.dismiss_key("m2")])
        self.assertTrue(restore_canon(self.db, hc.dismiss_key("m1")))
        run_canon(self.db, ["m1", "m2"])
        self.assertEqual(len(list_canon_cards(self.db)), 2)

    def test_canon_empty_result_clears(self):
        run_canon(self.db, ["m1"])
        save_canon(self.db, find_hidden_canon([], [], []), now=1.0)
        self.assertEqual(list_canon_cards(self.db), [])

    # anniversaries
    def test_anniversary_save_and_dismiss_is_per_year(self):
        self.assertEqual(run_ann(self.db, ["r1", "r2"]), 2)
        key = ann.dismiss_key("album_release", "r1", 2026)
        self.assertTrue(dismiss_anniversary(self.db, key))
        run_ann(self.db, ["r1", "r2"])
        self.assertEqual(self.keys(list_anniversary_cards), [ann.dismiss_key("album_release", "r2", 2026)])
        # next year's anniversary of r1 has another key, so it is not suppressed
        self.assertNotIn(ann.dismiss_key("album_release", "r1", 2027), dismissed_anniversary_keys(self.db))
        self.assertTrue(restore_anniversary(self.db, key))
        self.assertFalse(restore_anniversary(self.db, key))

    def test_anniversary_empty_day_clears_stale_cards(self):
        run_ann(self.db, ["r1"])
        res = find_anniversaries([DatedAlbum("r1", "T", "A", "2016-06-01")], [], date(2026, 6, 2))
        save_anniversaries(self.db, res, now=1.0)
        self.assertEqual(list_anniversary_cards(self.db), [])

    # shared guarantees
    def test_kinds_are_isolated_from_each_other(self):
        run_series(self.db, ["a"])
        run_canon(self.db, ["m1"])
        run_ann(self.db, ["r1"])
        dismiss_canon(self.db, hc.dismiss_key("m1"))
        run_series(self.db, ["b"])
        self.assertEqual(len(list_anniversary_cards(self.db)), 1)
        self.assertEqual(self.keys(list_series_cards), [sc.dismiss_key("b")])
        self.assertEqual(dismissed_series_keys(self.db), set())
        self.assertEqual(dismissed_canon_keys(self.db), {hc.dismiss_key("m1")})

    def test_other_kinds_untouched(self):
        for kind in ("other", "forgotten_gem", "blind_spot"):
            self.db.execute(
                "INSERT INTO insights (kind, payload, generation, computed_at) VALUES (?, '{}', 1, 0)", (kind,))
        self.db.commit()
        run_series(self.db, ["a"])
        run_canon(self.db, ["m1"])
        run_ann(self.db, ["r1"])
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM insights WHERE kind IN ('other','forgotten_gem','blind_spot')").fetchone()[0], 3)

    def test_cards_keep_reasons_generation_and_null_subject_id(self):
        run_series(self.db, ["a"])
        row = self.db.execute("SELECT reasons_json, generation, subject_id FROM insights").fetchone()
        self.assertIn("series_progress", row["reasons_json"])
        self.assertEqual((row["generation"], row["subject_id"]), (generations.current_generation(self.db), None))

    def test_writes_bump_the_insights_data_version(self):
        before = generations.data_version(self.db, "insights")
        run_series(self.db, ["a"])
        dismiss_series(self.db, sc.dismiss_key("a"))
        restore_series(self.db, sc.dismiss_key("a"))
        self.assertEqual(generations.data_version(self.db, "insights"), before + 3)

    def test_save_drops_a_card_whose_key_was_dismissed_after_the_run(self):
        res = find_series_progress([series("a")], ["a-0"], SeriesConfig())
        dismiss_series(self.db, sc.dismiss_key("a"))
        self.assertEqual(save_series(self.db, res, now=1.0), 0)


if __name__ == "__main__":
    unittest.main()
