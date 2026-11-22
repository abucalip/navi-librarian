"""Direct-import tests for the week of Current tastes lists behind Today's picks."""
import unittest

from discovery import lens_week


def stored(day, *albums):
    return {"payload": {"day": day, "albums": [{"artist": a, "album": b} for a, b in albums]}, "generated_at": 1.0}


KEY = lambda text: text.strip().casefold()


class ArchiveTests(unittest.TestCase):
    def test_keeps_a_day_once_and_never_overwrites_it(self):
        db = {}
        read = lambda name: ({"payload": db[name]} if name in db else None)
        write = db.__setitem__
        self.assertEqual(lens_week.archive_current(stored("2026-11-10", ("A", "1")), read, write), "2026-11-10")
        self.assertIsNone(lens_week.archive_current(stored("2026-11-10", ("A", "1"), ("B", "2")), read, write))
        self.assertEqual(len(db["lens_week:current_tastes:2026-11-10"]["albums"]), 1)

    def test_skips_empty_malformed_and_undated_lists(self):
        write = lambda *_: self.fail("nothing should be written")
        for bad in (None, {}, {"payload": {"day": "2026-11-10", "albums": []}}, {"payload": {"day": "soon", "albums": [{}]}}):
            self.assertIsNone(lens_week.archive_current(bad, lambda _n: None, write))


class PoolTests(unittest.TestCase):
    def test_window_is_seven_days_newest_first(self):
        days = lens_week.week_days("2026-11-13")
        self.assertEqual((days[0], days[-1], len(days)), ("2026-11-13", "2026-11-07", 7))

    def test_pool_covers_the_week_dedupes_and_drops_owned_and_dismissed(self):
        db = {
            lens_week.archive_name("2026-11-12"): stored("2026-11-12", ("A", "1"), ("B", "2"))["payload"],
            lens_week.archive_name("2026-11-06"): stored("2026-11-06", ("Old", "Out of the week"))["payload"],
        }
        read = lambda name: ({"payload": db[name]} if name in db else None)
        live = stored("2026-11-13", (" a ", "1"), ("C", "3"), ("D", "4"), ("E", "5"))
        pool = lens_week.week_pool(
            "2026-11-13", live, read, KEY,
            is_owned=lambda a: a["artist"] == "D", is_dismissed=lambda a: a["artist"] == "E",
        )
        self.assertEqual([a["artist"] for a in pool], [" a ", "C", "B"])

    def test_picks_use_the_pick_shape_and_a_fresh_shuffle(self):
        pool = [{"artist": "A", "album": "1", "tags": ["x", "y"], "seed_tag": "x"}, {"artist": "B", "album": "2"}]
        out = lens_week.build_week_picks(pool, 1, lambda v: v.reverse())
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["pool_size"], 2)
        self.assertEqual(out["items"][0]["artist"], "B")
        self.assertEqual(out["items"][0]["dashboard_category"], "Current tastes")
        self.assertEqual(pool[0]["artist"], "A")  # the pool itself is not reordered

    def test_a_bridged_album_keeps_its_discover_more_label(self):
        out = lens_week.build_week_picks(
            [{"artist": "A", "album": "1", "seed_tag": "x", "bridge_label": "Discover more A"}], 1, lambda v: None)
        self.assertEqual(out["items"][0]["reason"], "Discover more A")
        self.assertEqual(out["items"][0]["why"], {
            "kind": "bridge", "sentence": "Discover more A", "chips": [],
        })

    def test_pick_includes_lens_why(self):
        out = lens_week.build_week_picks(
            [{"artist": "A", "album": "1", "lens": "current_tastes", "seed_tag": "ambient", "album_listeners": 5400}],
            1, lambda v: None,
        )
        self.assertEqual(out["items"][0]["listeners"], 5400)
        self.assertEqual(out["items"][0]["lastfm_listeners"], 5400)
        self.assertEqual(out["items"][0]["why"]["kind"], "lens")
        self.assertEqual(out["items"][0]["why"]["sentence"], "Close to the ambient you play lately")

    def test_pick_falls_back_to_listeners_and_lastfm_listeners(self):
        out = lens_week.build_week_picks(
            [
                {"artist": "A", "album": "1", "listeners": 1200},
                {"artist": "B", "album": "2", "lastfm_listeners": 800},
            ],
            2, lambda v: None,
        )
        self.assertEqual((out["items"][0]["listeners"], out["items"][0]["lastfm_listeners"]), (1200, 1200))
        self.assertEqual((out["items"][1]["listeners"], out["items"][1]["lastfm_listeners"]), (800, 800))


class WeekPicksServiceTests(unittest.TestCase):
    """The picks pool is the week's Current tastes albums plus the bridged Deep Dives albums."""

    def librarian(self, deep_items):
        from types import SimpleNamespace
        from datetime import datetime
        from discovery.lens_storage import lens_day, lens_storage_name

        live = {"payload": {"day": lens_day(datetime.now()), "seed_tags": ["shoegaze"],
                            "albums": [{"artist": "A", "album": "1", "tags": ["shoegaze"]}]}}
        db = {lens_storage_name(lens_week.LENS): live, "artist_deep_dive": {"payload": {"items": deep_items}}}
        return SimpleNamespace(
            _discovery_read_list=lambda name: db.get(name),
            _discovery_write_list=db.__setitem__,
            _music_key=KEY,
            _is_owned=None,
        )

    def test_picks_include_deep_dives_albums_of_the_same_genres(self):
        from app.services import lens_week_picks

        deep = [{"artist": "Slowdive", "album": "Souvlaki", "genres": ["shoegaze"]},
                {"artist": "Miles", "album": "Kind of Blue", "genres": ["jazz"]}]
        out = lens_week_picks.picks(self.librarian(deep), 10, shuffle=lambda v: None)
        names = [(i["artist"], i["album"]) for i in out["items"]]
        self.assertIn(("A", "1"), names)
        self.assertIn(("Slowdive", "Souvlaki"), names)
        self.assertNotIn(("Miles", "Kind of Blue"), names)

    def test_a_failing_bridge_leaves_the_week_albums(self):
        from app.services import lens_week_picks

        lib = self.librarian([])
        real = lib._discovery_read_list
        lib._discovery_read_list = lambda n: (_ for _ in ()).throw(RuntimeError) if n == "artist_deep_dive" else real(n)
        out = lens_week_picks.picks(lib, 10, shuffle=lambda v: None)
        self.assertEqual([i["artist"] for i in out["items"]], ["A"])


if __name__ == "__main__":
    unittest.main()
