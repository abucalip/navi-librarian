"""Tests for the dynamic lens history fetch (Engine 2, Phase 4): windows, sources, paging.

No network: the window readers and the HTTP getter are fakes.
"""
import functools
import unittest

from discovery import history_fetch

DAY = 86400
NOW = 1_800_000_000  # a fixed "now" in 2027; the windows below are relative to it


def _listen(ts, artist="A", track="T"):
    return {"listened_at": ts, "track_metadata": {"artist_name": artist, "track_name": track}}


def _reader(name, listens_by_window, calls, fail=False):
    """A window reader that returns the listens stamped inside the requested window."""
    def read(start, end):
        calls.append((name, start, end))
        if fail:
            raise RuntimeError("provider down")
        return [item for item in listens_by_window if start < item["listened_at"] <= end]
    return name, read


class FetchWalkTests(unittest.TestCase):
    def test_stops_after_the_first_window_when_it_has_enough_listens(self):
        recent = [_listen(NOW - i) for i in range(10)]
        calls = []
        result = history_fetch.fetch_lens_history(
            [_reader("listenbrainz", recent, calls)], now=NOW, min_usable=5, step_days=365, max_days=3650,
        )
        self.assertEqual(result["stopped"], "enough_listens")
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(result["listens"]), 10)

    def test_walks_back_window_by_window_until_enough_listens_are_found(self):
        old = [_listen(NOW - 3 * 365 * DAY - i) for i in range(12)]  # three windows back
        calls = []
        result = history_fetch.fetch_lens_history(
            [_reader("listenbrainz", old, calls)], now=NOW, min_usable=10, step_days=365, max_days=5 * 365,
        )
        self.assertEqual(result["stopped"], "enough_listens")
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(result["listens"]), 12)

    def test_windows_alternate_between_the_two_sources(self):
        listens = [_listen(NOW - i * 400 * DAY) for i in range(1, 6)]
        calls = []
        result = history_fetch.fetch_lens_history(
            [_reader("listenbrainz", listens, calls), _reader("lastfm", listens, calls)],
            now=NOW, min_usable=100, step_days=365, max_days=5 * 365,
        )
        sources = [name for name, _start, _end in calls]
        self.assertEqual(sources[:4], ["listenbrainz", "lastfm", "listenbrainz", "lastfm"])
        self.assertEqual(result["stopped"], "floor_reached")

    def test_a_failing_source_is_answered_by_the_other_for_that_window(self):
        listens = [_listen(NOW - 10)]
        calls = []
        result = history_fetch.fetch_lens_history(
            [_reader("listenbrainz", listens, calls, fail=True), _reader("lastfm", listens, calls)],
            now=NOW, min_usable=1, step_days=365, max_days=365,
        )
        self.assertEqual([call[0] for call in calls], ["listenbrainz", "lastfm"])
        self.assertEqual(result["windows"][0], {"source": "lastfm", "count": 1, "truncated": False})
        self.assertEqual(result["unanswered"], 0)

    def test_a_window_no_source_answers_is_counted_and_the_walk_goes_on(self):
        calls = []
        result = history_fetch.fetch_lens_history(
            [_reader("listenbrainz", [], calls, fail=True), _reader("lastfm", [], calls, fail=True)],
            now=NOW, min_usable=1, step_days=365, max_days=2 * 365,
        )
        self.assertEqual(result["unanswered"], 2)
        self.assertEqual(result["listens"], [])
        self.assertEqual(result["stopped"], "floor_reached")

    def test_the_walk_never_goes_past_the_floor(self):
        calls = []
        history_fetch.fetch_lens_history(
            [_reader("listenbrainz", [], calls)], now=NOW, min_usable=1, step_days=365, max_days=400,
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual(min(start for _name, start, _end in calls), NOW - 400 * DAY)

    def test_the_same_listen_from_both_sources_is_counted_once(self):
        listen = _listen(NOW - 5, artist="Same", track="Song")
        calls = []
        result = history_fetch.fetch_lens_history(
            [_reader("listenbrainz", [listen], calls), _reader("lastfm", [dict(listen)], calls)],
            now=NOW, min_usable=100, step_days=365, max_days=2 * 365,
        )
        self.assertEqual(len(result["listens"]), 1)

    def test_a_window_at_the_page_cap_is_flagged_as_possibly_truncated(self):
        full = [_listen(NOW - 10 - i) for i in range(history_fetch.WINDOW_LISTEN_CAP)]
        calls = []
        result = history_fetch.fetch_lens_history(
            [_reader("listenbrainz", full, calls)], now=NOW, min_usable=10**9, step_days=365, max_days=365,
        )
        self.assertTrue(result["windows"][0]["truncated"])

    def test_the_default_threshold_reaches_past_the_most_recent_year(self):
        self.assertGreater(history_fetch.LENS_MIN_USABLE_LISTENS, 571)

    def test_no_sources_means_no_listens(self):
        result = history_fetch.fetch_lens_history([], now=NOW)
        self.assertEqual(result["listens"], [])
        self.assertEqual(result["stopped"], "no_sources")


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class ListenBrainzWindowTests(unittest.TestCase):
    def test_pages_backwards_with_max_ts_and_keeps_only_the_window(self):
        page_one = [{"listened_at": 1000 - i} for i in range(100)]  # 1000 .. 901
        page_two = [{"listened_at": 900 - i} for i in range(5)] + [{"listened_at": 400}]
        seen_params = []

        def get(url, params, **_kwargs):
            seen_params.append(dict(params))
            return _Response({"payload": {"listens": page_one if "max_ts" not in params or params["max_ts"] == 1000 else page_two}})

        listens = history_fetch.listenbrainz_window(
            "user", 300, 1000, get=get, headers={}, pause=lambda _s: None,
        )
        self.assertNotIn("min_ts", seen_params[0])
        self.assertEqual(seen_params[0]["max_ts"], 1000)
        self.assertEqual(seen_params[1]["max_ts"], 900)  # oldest of page one minus one
        self.assertTrue(all(300 < item["listened_at"] <= 1000 for item in listens))
        self.assertIn(400, [item["listened_at"] for item in listens])

    def test_stops_when_a_page_reaches_the_window_start(self):
        calls = []

        def get(url, params, **_kwargs):
            calls.append(params)
            return _Response({"payload": {"listens": [{"listened_at": 500 - i} for i in range(100)]}})

        history_fetch.listenbrainz_window("user", 450, 1000, get=get, headers={}, pause=lambda _s: None)
        self.assertEqual(len(calls), 1)


class LastFmErrorTests(unittest.TestCase):
    def test_an_api_error_in_a_200_reply_raises_instead_of_reading_as_empty(self):
        def get(url, params, **_kwargs):
            return _Response({"error": 6, "message": "User not found"})

        with self.assertRaises(history_fetch.LastFmResponseError):
            history_fetch.lastfm_window("nobody", "key", 0, 10, get=get, pause=lambda _s: None)

    def test_a_reply_without_a_recenttracks_object_raises(self):
        def get(url, params, **_kwargs):
            return _Response({"unexpected": True})

        with self.assertRaises(history_fetch.LastFmResponseError):
            history_fetch.lastfm_window("user", "key", 0, 10, get=get, pause=lambda _s: None)

    def test_a_single_track_returned_as_an_object_is_read(self):
        def get(url, params, **_kwargs):
            return _Response({"recenttracks": {"@attr": {"totalPages": "1"}, "track": {
                "name": "Only", "artist": {"#text": "Band"}, "date": {"uts": "5"}}}})

        listens = history_fetch.lastfm_window("user", "key", 0, 10, get=get, pause=lambda _s: None)
        self.assertEqual([item["listened_at"] for item in listens], [5])

    def test_a_valid_empty_window_is_not_an_error(self):
        def get(url, params, **_kwargs):
            return _Response({"recenttracks": {"@attr": {"totalPages": "1"}, "track": []}})

        self.assertEqual(history_fetch.lastfm_window("user", "key", 0, 10, get=get, pause=lambda _s: None), [])

    def test_a_last_fm_error_window_is_answered_by_listenbrainz(self):
        def lastfm_get(url, params, **_kwargs):
            return _Response({"error": 10, "message": "Invalid API key"})

        listens = [_listen(NOW - 10)]
        calls = []
        result = history_fetch.fetch_lens_history(
            [
                ("lastfm", functools.partial(history_fetch.lastfm_window, "user", "bad-key",
                                             get=lastfm_get, pause=lambda _s: None)),
                _reader("listenbrainz", listens, calls),
            ],
            now=NOW, min_usable=1, step_days=365, max_days=365,
        )
        self.assertEqual(result["windows"][0], {"source": "listenbrainz", "count": 1, "truncated": False})
        self.assertEqual(len(result["listens"]), 1)
        self.assertEqual(result["unanswered"], 0)


class LastFmWindowTests(unittest.TestCase):
    def test_converts_scrobbles_to_the_listenbrainz_shape_and_skips_now_playing(self):
        payload = {"recenttracks": {
            "@attr": {"totalPages": "1"},
            "track": [
                {"name": "Song", "artist": {"#text": "Band", "mbid": "mbid-1"}, "album": {"#text": "Record"},
                 "date": {"uts": "1200"}},
                {"name": "Now", "artist": {"#text": "Band"}, "album": {"#text": ""}},  # no date: now playing
            ],
        }}
        seen = []

        def get(url, params, **_kwargs):
            seen.append(dict(params))
            return _Response(payload)

        listens = history_fetch.lastfm_window("user", "key", 1000, 1500, get=get, pause=lambda _s: None)
        self.assertEqual(seen[0]["from"], 1001)
        self.assertEqual(seen[0]["to"], 1500)
        self.assertEqual(len(listens), 1)
        self.assertEqual(listens[0]["listened_at"], 1200)
        self.assertEqual(listens[0]["track_metadata"]["artist_name"], "Band")
        self.assertEqual(listens[0]["track_metadata"]["additional_info"]["artist_mbids"], ["mbid-1"])

    def test_follows_every_page_the_api_reports(self):
        pages = {
            1: {"recenttracks": {"@attr": {"totalPages": "2"}, "track": [{"name": "a", "artist": {"#text": "x"}, "date": {"uts": "2"}}]}},
            2: {"recenttracks": {"@attr": {"totalPages": "2"}, "track": [{"name": "b", "artist": {"#text": "x"}, "date": {"uts": "1"}}]}},
        }

        def get(url, params, **_kwargs):
            return _Response(pages[params["page"]])

        listens = history_fetch.lastfm_window("user", "key", 0, 10, get=get, pause=lambda _s: None)
        self.assertEqual([item["track_metadata"]["track_name"] for item in listens], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
