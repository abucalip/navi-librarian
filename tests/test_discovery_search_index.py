import threading
import unittest

from discovery.search.index import (
    MAX_SONGS,
    RETRY_BACKOFF_SECONDS,
    STATE_BUILDING,
    STATE_FRESH,
    STATE_STALE,
    STATE_UNAVAILABLE,
    OwnedIndex,
    SongInventoryError,
    fetch_song_inventory,
)


def items(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def library(song_titles=("One", "Two")):
    artists = [{"id": "ar1", "name": "Radiohead", "album_count": 2}]
    albums = [
        {"id": "al1", "artist": "Radiohead", "artist_id": "ar1", "album": "OK Computer",
         "year": 1997, "song_count": 12},
    ]
    songs = [{"id": f"s{i}", "title": title, "artist": "Radiohead", "artistId": "ar1",
              "album": "OK Computer", "albumId": "al1"} for i, title in enumerate(song_titles)]
    return artists, albums, songs


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


class FakeLoaders:
    """Returns the library and songs it is given, and records how often it was asked."""

    def __init__(self, songs=None):
        self.songs = songs if songs is not None else library()[2]
        self.library_calls = 0
        self.song_calls = 0
        self.fail_next = False

    def load_library(self):
        self.library_calls += 1
        artists, albums, _ = library()
        return artists, albums

    def load_songs(self):
        self.song_calls += 1
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("Navidrome is down")
        return list(self.songs)


def make_index(loaders, clock, **kwargs):
    return OwnedIndex(
        load_library=loaders.load_library,
        load_songs=loaders.load_songs,
        now=clock,
        background=False,
        **kwargs,
    )


class FetchSongInventoryTests(unittest.TestCase):
    def test_pages_until_a_short_page_and_deduplicates_ids(self):
        pages = [
            [{"id": f"s{i}"} for i in range(3)],
            [{"id": "s2"}, {"id": "s3"}],
        ]
        calls = []

        def api_call(method, **params):
            calls.append((method, params))
            page = pages[len(calls) - 1] if len(calls) <= len(pages) else []
            return {"searchResult3": {"song": page}}

        songs = fetch_song_inventory(api_call, items, page_size=3)
        self.assertEqual([s["id"] for s in songs], ["s0", "s1", "s2", "s3"])
        self.assertEqual([p["songOffset"] for _, p in calls], [0, 3])
        self.assertEqual(calls[0][1]["query"], "")

    def test_empty_library_is_complete(self):
        songs = fetch_song_inventory(
            lambda method, **params: {"searchResult3": {}}, items, page_size=3,
        )
        self.assertEqual(songs, [])

    def test_full_pages_past_the_safety_cap_raise_instead_of_returning_a_partial_list(self):
        def api_call(method, **params):
            return {"searchResult3": {"song": [{"id": f"s{params['songOffset']}-{i}"} for i in range(2)]}}

        with self.assertRaises(SongInventoryError):
            fetch_song_inventory(api_call, items, page_size=2, max_songs=4)

    def test_year_is_a_four_digit_value_or_null(self):
        from discovery.search.index import _year

        self.assertEqual(_year(1999), 1999)
        self.assertEqual(_year("2001"), 2001)
        self.assertIsNone(_year(0))
        self.assertIsNone(_year(None))
        self.assertIsNone(_year("n/a"))

    def test_safety_cap_default_is_large_enough_for_the_current_library(self):
        self.assertGreater(MAX_SONGS, 12_097)


class OwnedIndexLifecycleTests(unittest.TestCase):
    def test_first_build_is_building_then_fresh(self):
        loaders = FakeLoaders()
        index = make_index(loaders, FakeClock())
        self.assertEqual(index.view().state, STATE_BUILDING)
        self.assertEqual(index.view().reason, "index_building")

        index.ensure("gen-1")
        view = index.view()
        self.assertEqual(view.state, STATE_FRESH)
        self.assertIsNone(view.reason)
        self.assertEqual(len(view.data.songs), 2)
        self.assertEqual(view.data.artists[0]["key"], "radiohead")

    def test_fresh_index_is_not_rebuilt_before_ttl(self):
        clock = FakeClock()
        loaders = FakeLoaders()
        index = make_index(loaders, clock, ttl_seconds=600)
        index.ensure("gen-1")
        clock.now += 599
        index.ensure("gen-1")
        self.assertEqual(loaders.song_calls, 1)
        clock.now += 2
        index.ensure("gen-1")
        self.assertEqual(loaders.song_calls, 2)

    def test_failed_first_build_is_unavailable_and_the_next_trigger_retries(self):
        clock = FakeClock()
        loaders = FakeLoaders()
        loaders.fail_next = True
        index = make_index(loaders, clock)
        index.ensure("gen-1")
        view = index.view()
        self.assertEqual(view.state, STATE_UNAVAILABLE)
        self.assertEqual(view.reason, "index_unavailable")
        self.assertIsNone(view.data)

        clock.now += RETRY_BACKOFF_SECONDS
        index.ensure("gen-1")
        self.assertEqual(index.view().state, STATE_FRESH)

    def test_failed_refresh_keeps_last_known_good_index_and_reports_stale(self):
        clock = FakeClock()
        loaders = FakeLoaders()
        index = make_index(loaders, clock, ttl_seconds=10)
        index.ensure("gen-1")
        good = index.view().data

        clock.now += 11
        loaders.fail_next = True
        index.ensure("gen-1")
        view = index.view()
        self.assertEqual(view.state, STATE_STALE)
        self.assertIs(view.data, good)
        self.assertIsNone(view.reason)

    def test_suspicious_song_drop_is_rejected_and_reported_stale(self):
        clock = FakeClock()
        loaders = FakeLoaders(songs=[{"id": f"s{i}", "title": f"t{i}"} for i in range(100)])
        index = make_index(loaders, clock, ttl_seconds=10)
        index.ensure("gen-1")
        good = index.view().data

        clock.now += 11
        loaders.songs = [{"id": f"s{i}", "title": f"t{i}"} for i in range(89)]
        index.ensure("gen-1")
        self.assertEqual(index.view().state, STATE_STALE)
        self.assertIs(index.view().data, good)

    def test_small_song_drop_inside_the_limit_is_accepted(self):
        clock = FakeClock()
        loaders = FakeLoaders(songs=[{"id": f"s{i}", "title": f"t{i}"} for i in range(100)])
        index = make_index(loaders, clock, ttl_seconds=10)
        index.ensure("gen-1")
        clock.now += 11
        loaders.songs = [{"id": f"s{i}", "title": f"t{i}"} for i in range(91)]
        index.ensure("gen-1")
        self.assertEqual(index.view().data.song_count, 91)

    def test_failed_build_waits_for_the_retry_backoff_before_trying_again(self):
        clock = FakeClock()
        loaders = FakeLoaders()
        loaders.fail_next = True
        index = make_index(loaders, clock)
        index.ensure("gen-1")
        self.assertEqual(loaders.song_calls, 1)

        clock.now += 10
        index.ensure("gen-1")
        self.assertEqual(loaders.song_calls, 1)
        self.assertEqual(index.view().state, STATE_UNAVAILABLE)

        clock.now += RETRY_BACKOFF_SECONDS
        index.ensure("gen-1")
        self.assertEqual(loaders.song_calls, 2)
        self.assertEqual(index.view().state, STATE_FRESH)

    def test_generation_change_builds_at_once_even_during_the_old_backoff(self):
        clock = FakeClock()
        loaders = FakeLoaders()
        loaders.fail_next = True
        index = make_index(loaders, clock)
        index.ensure("gen-1")
        clock.now += 1
        index.ensure("gen-2")
        self.assertEqual(loaders.song_calls, 2)
        self.assertEqual(index.view().state, STATE_FRESH)

    def test_forced_refresh_bypasses_fresh_index_ttl_but_not_a_failed_build_backoff(self):
        clock = FakeClock()
        loaders = FakeLoaders()
        index = make_index(loaders, clock, ttl_seconds=600)
        index.ensure("gen-1")
        index.ensure("gen-1", force=True)
        self.assertEqual(loaders.song_calls, 2)

    def test_generation_change_drops_the_previous_index_at_once(self):
        loaders = FakeLoaders()
        index = make_index(loaders, FakeClock())
        index.ensure("gen-1")
        self.assertEqual(index.view().state, STATE_FRESH)

        # The new server's build fails: the previous server's data must not be served.
        loaders.fail_next = True
        index.ensure("gen-2")
        view = index.view()
        self.assertIsNone(view.data)
        self.assertEqual(view.state, STATE_UNAVAILABLE)

    def test_generation_change_skips_the_sanity_check_on_the_first_rebuild(self):
        clock = FakeClock()
        loaders = FakeLoaders(songs=[{"id": f"s{i}", "title": f"t{i}"} for i in range(100)])
        index = make_index(loaders, clock)
        index.ensure("gen-1")
        loaders.songs = [{"id": "only", "title": "one"}]
        index.ensure("gen-2")
        self.assertEqual(index.view().state, STATE_FRESH)
        self.assertEqual(index.view().data.song_count, 1)

    def test_single_flight_joins_a_running_build(self):
        release = threading.Event()
        started = threading.Event()
        loaders = FakeLoaders()

        def slow_songs():
            started.set()
            release.wait(5)
            return list(loaders.songs)

        index = OwnedIndex(
            load_library=loaders.load_library,
            load_songs=slow_songs,
            now=FakeClock(),
            background=True,
        )
        index.ensure("gen-1")
        self.assertTrue(started.wait(5))
        index.ensure("gen-1")
        index.ensure("gen-1")
        release.set()
        for _ in range(500):
            if index.view().state == STATE_FRESH:
                break
            threading.Event().wait(0.01)
        self.assertEqual(index.view().state, STATE_FRESH)
        self.assertEqual(loaders.library_calls, 1)


if __name__ == "__main__":
    unittest.main()
