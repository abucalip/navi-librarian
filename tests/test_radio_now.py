"""Live "now" holder, the /now state rules, the library match and the eager 30-second log
(docs/RADIO_PLAYBACK_CONTRACT.md sections 3.2, 3.3 and 3.8)."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from integrations.radio import now as radio_now
from integrations.radio.library_match import find_song
from integrations.radio.listening import ListenTracker
from integrations.radio.now import NowHolder, view
from integrations.radio.store import RadioStore


class Clock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now


class HolderTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.holder = NowHolder(clock=self.clock, stale_seconds=20)

    def test_nobody_listening_is_none_and_the_newest_fresh_connection_wins(self):
        self.assertIsNone(self.holder.live("1"))
        self.holder.publish("1", "a", {"has_metadata": True, "raw": "A - Old", "play_id": None})
        self.clock.now += 5
        self.holder.publish("1", "b", {"has_metadata": True, "raw": "B - New", "play_id": 7})
        self.assertEqual(self.holder.live("1")["raw"], "B - New")
        self.holder.withdraw("1", "b")
        self.assertEqual(self.holder.live("1")["raw"], "A - Old")
        self.holder.withdraw("1", "a")
        self.assertIsNone(self.holder.live("1"))

    def test_a_connection_that_stops_reporting_goes_stale(self):
        self.holder.publish("1", "a", {"has_metadata": True, "raw": "A - Song", "play_id": None})
        self.clock.now += 21
        self.assertIsNone(self.holder.live("1"))

    def test_unreachable_mark_expires(self):
        self.holder.mark_unreachable("1")
        self.assertTrue(self.holder.unreachable("1"))
        self.clock.now += radio_now.UNREACHABLE_SECONDS + 1
        self.assertFalse(self.holder.unreachable("1"))

    def test_library_answer_is_kept_for_the_same_title_only(self):
        self.holder.remember_library("1", "A - Song", {"in_library": True, "cover_url": "/c"})
        self.assertEqual(self.holder.library("1", "A - Song"), {"in_library": True, "cover_url": "/c"})
        self.assertIsNone(self.holder.library("1", "B - Other"))


class ViewTests(unittest.TestCase):
    def snapshot(self, raw, has_metadata=True, play_id=None):
        return {"has_metadata": has_metadata, "raw": raw, "play_id": play_id}

    def test_not_proxied_station_is_not_proxied_whatever_the_holder_says(self):
        result = view(self.snapshot("A - Song", play_id=3), proxied=False)
        self.assertEqual(result["state"], "not_proxied")
        self.assertIsNone(result["raw_title"])
        self.assertIsNone(result["play_id"])

    def test_no_listener_is_idle_or_unavailable_when_the_station_was_unreachable(self):
        self.assertEqual(view(None)["state"], "idle")
        self.assertEqual(view(None, unreachable=True)["state"], "unavailable")

    def test_station_without_icy_titles_is_no_metadata(self):
        self.assertEqual(view(self.snapshot(None))["state"], "no_metadata")
        self.assertEqual(view(self.snapshot("A - Song", has_metadata=False))["state"], "no_metadata")

    def test_title_without_separator_is_unparsed_and_not_looked_up(self):
        lookup = mock.Mock()
        result = view(self.snapshot("Station jingle", play_id=4), lookup)
        self.assertEqual((result["state"], result["raw_title"], result["artist"], result["title"]),
                         ("unparsed", "Station jingle", None, None))
        self.assertEqual(result["play_id"], 4)
        lookup.assert_not_called()

    def test_parsed_song_carries_the_library_answer_and_play_id(self):
        lookup = mock.Mock(return_value={"in_library": True, "cover_url": "/api/owned/artwork/al-1"})
        result = view(self.snapshot("Pink Floyd - Time", play_id=9), lookup)
        lookup.assert_called_once_with("Pink Floyd - Time", "Pink Floyd", "Time")
        self.assertEqual(result, {"state": "ok", "raw_title": "Pink Floyd - Time", "artist": "Pink Floyd",
                                  "title": "Time", "play_id": 9, "in_library": True,
                                  "cover_url": "/api/owned/artwork/al-1"})

    def test_song_with_no_library_answer_is_not_in_library_and_has_no_cover(self):
        result = view(self.snapshot("Pink Floyd - Time"), lambda raw, a, t: None)
        self.assertEqual((result["state"], result["in_library"], result["cover_url"], result["play_id"]),
                         ("ok", False, None, None))


class FindSongTests(unittest.TestCase):
    def search(self, *songs):
        return mock.Mock(return_value={"searchResult3": {"song": list(songs)}})

    def test_exact_artist_and_title_ignoring_case_and_spacing(self):
        api = self.search({"id": "s1", "artist": "Pink  Floyd", "title": "time", "coverArt": "al-1"},
                          {"id": "s2", "artist": "Pink Floyd", "title": "Time (Live)"})
        self.assertEqual(find_song(api, "pink floyd", "Time")["id"], "s1")
        self.assertEqual(api.call_args.kwargs["query"], "pink floyd Time")

    def test_partial_or_missing_match_is_none(self):
        api = self.search({"id": "s2", "artist": "Pink Floyd", "title": "Time (Live)"})
        self.assertIsNone(find_song(api, "Pink Floyd", "Time"))
        self.assertIsNone(find_song(self.search(), "Pink Floyd", "Time"))


class EagerLogTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = RadioStore(Path(self.dir.name) / "radio.sqlite3")
        self.clock = Clock()
        self.holder = NowHolder(clock=Clock(0.0))
        self.tracker = ListenTracker(self.store, "s1", "Rock FM", clock=self.clock,
                                     holder=self.holder, has_metadata=True)

    def tearDown(self):
        self.dir.cleanup()

    def test_song_is_logged_at_thirty_seconds_while_still_playing(self):
        self.tracker.set_title("A - Song")
        self.clock.now += 29
        self.tracker.tick()
        self.assertEqual(self.store.list_plays(), [])
        self.assertIsNone(self.holder.live("s1")["play_id"])

        self.clock.now += 1
        self.tracker.tick()
        plays = self.store.list_plays()
        self.assertEqual([(p["artist"], p["title"], p["listened_seconds"]) for p in plays], [("A", "Song", 30)])
        self.assertEqual(self.holder.live("s1")["play_id"], plays[0]["id"])

    def test_closing_adds_only_what_was_heard_after_the_threshold(self):
        self.tracker.set_title("A - Song")
        self.clock.now += 30
        self.tracker.tick()
        self.clock.now += 50
        self.tracker.tick()
        self.tracker.close()
        plays = self.store.list_plays()
        self.assertEqual(len(plays), 1)
        self.assertEqual(plays[0]["listened_seconds"], 80)
        self.assertIsNone(self.holder.live("s1"))

    def test_skipping_before_thirty_seconds_logs_nothing_and_clears_the_song(self):
        self.tracker.set_title("A - Song")
        self.clock.now += 10
        self.tracker.tick()
        self.tracker.set_title("B - Next")
        self.assertEqual(self.holder.live("s1")["raw"], "B - Next")
        self.assertIsNone(self.holder.live("s1")["play_id"])
        self.tracker.close()
        self.assertEqual(self.store.list_plays(), [])

    def test_next_song_gets_its_own_play_id(self):
        self.tracker.set_title("A - Song")
        self.clock.now += 40
        self.tracker.tick()
        self.tracker.set_title("B - Next")
        self.clock.now += 35
        self.tracker.tick()
        self.tracker.close()
        plays = self.store.list_plays()
        self.assertEqual([(p["title"], p["listened_seconds"]) for p in plays], [("Next", 35), ("Song", 40)])

    def test_tracker_without_a_holder_still_logs_on_close(self):
        store = RadioStore(Path(self.dir.name) / "plain.sqlite3")
        plain = ListenTracker(store, "s1", "Rock FM", clock=self.clock)
        plain.set_title("A - Song")
        self.clock.now += 45
        plain.tick()
        plain.close()
        self.assertEqual(store.list_plays()[0]["listened_seconds"], 45)


if __name__ == "__main__":
    unittest.main()
