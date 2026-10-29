import tempfile
import unittest
from pathlib import Path

from integrations.radio.listening import ListenTracker
from integrations.radio.store import MERGE_WINDOW_SECONDS, RadioStore


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class ListenTrackerTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = RadioStore(Path(self.dir.name) / "radio.sqlite3")
        self.clock = Clock()
        self.tracker = ListenTracker(self.store, "s1", "Rock FM", clock=self.clock)

    def tearDown(self):
        self.dir.cleanup()

    def listen(self, title, seconds):
        self.tracker.set_title(title)
        self.clock.now += seconds

    def test_only_songs_heard_long_enough_are_logged(self):
        self.listen("A - Skipped", 10)
        self.listen("B - Heard", 200)
        self.tracker.close()
        plays = self.store.list_plays()
        self.assertEqual([(p["artist"], p["title"], p["listened_seconds"]) for p in plays],
                         [("B", "Heard", 200)])

    def test_untitled_gaps_station_name_and_unparsed_titles(self):
        self.listen("", 100)
        self.listen("rock fm", 100)
        self.listen("Station jingle", 100)
        self.tracker.close()
        plays = self.store.list_plays()
        self.assertEqual(len(plays), 1)
        self.assertIsNone(plays[0]["artist"])
        self.assertEqual(plays[0]["title"], "Station jingle")

    def test_nothing_logged_when_the_client_leaves_early(self):
        self.listen("A - Song", 29)
        self.tracker.close()
        self.assertEqual(self.store.list_plays(), [])

    def test_same_title_repeated_updates_do_not_split_a_listen(self):
        self.tracker.set_title("A - Song")
        self.clock.now += 40
        self.tracker.set_title("A - Song")
        self.clock.now += 40
        self.tracker.close()
        self.assertEqual(self.store.list_plays()[0]["listened_seconds"], 80)

    def test_reconnect_extends_the_same_play(self):
        self.listen("A - Song", 60)
        self.tracker.close()
        self.clock.now += 20
        second = ListenTracker(self.store, "s1", "Rock FM", clock=self.clock)
        second.set_title("A - Song")
        self.clock.now += 50
        second.close()
        plays = self.store.list_plays()
        self.assertEqual(len(plays), 1)
        self.assertEqual(plays[0]["listened_seconds"], 110)

    def test_same_title_much_later_is_a_new_play(self):
        self.listen("A - Song", 60)
        self.tracker.close()
        self.clock.now += MERGE_WINDOW_SECONDS + 1
        self.listen("A - Song", 60)
        self.tracker.close()
        self.assertEqual(len(self.store.list_plays()), 2)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = RadioStore(Path(self.dir.name) / "radio.sqlite3")

    def tearDown(self):
        self.dir.cleanup()

    def test_token_lookup_requires_an_enabled_station(self):
        self.store.save_station("1", "tok", "Rock FM", "http://x/stream")
        self.assertEqual(self.store.station_by_token("tok")["original_url"], "http://x/stream")
        self.store.disable_station("1")
        self.assertIsNone(self.store.station_by_token("tok"))
        self.assertIsNone(self.store.station_by_token("other"))

    def test_resaving_a_station_issues_a_new_token_and_enables_it(self):
        self.store.save_station("1", "old", "Rock FM", "http://x/stream")
        self.store.disable_station("1")
        self.store.save_station("1", "new", "Rock FM", "http://x/stream")
        self.assertIsNone(self.store.station_by_token("old"))
        self.assertIsNotNone(self.store.station_by_token("new"))

    def test_album_grabbed_and_delete(self):
        play = self.store.record_play("1", "Rock FM", "A - S", "A", "S", 60, now=5000.0)
        self.store.set_album(play, "Album", 1999)
        self.store.mark_grabbed(play)
        row = self.store.get_play(play)
        self.assertEqual((row["album"], row["year"], row["grabbed"]), ("Album", 1999, 1))
        self.assertTrue(self.store.delete_play(play))
        self.assertFalse(self.store.delete_play(play))


if __name__ == "__main__":
    unittest.main()
