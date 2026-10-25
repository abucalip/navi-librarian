"""Provider clients, pacing and the result cache for external search (contract sections 5 to 6, 9)."""

import threading
import unittest

from discovery.search.cache import NEGATIVE_TTL_SECONDS, POSITIVE_TTL_SECONDS, provider_cache_key, read_cached, write_cached
from discovery.search.limiter import SourceLimiter
from discovery.search.providers import LastFmSearch, MusicBrainzSearch, ProviderError, lucene_phrase


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class ScriptedGet:
    """Returns scripted responses in order and records every request."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.requests.append((url, params))
        return self.responses.pop(0)


def open_limiter():
    return SourceLimiter({"musicbrainz": 0.0, "lastfm": 0.0})


def never_cancelled():
    return threading.Event()


def plenty():
    return 10.0


class LimiterTests(unittest.TestCase):
    def test_second_call_waits_for_the_interval(self):
        clock = [0.0]
        slept = []
        limiter = SourceLimiter({"musicbrainz": 1.0}, clock=lambda: clock[0], sleep=slept.append)
        self.assertTrue(limiter.admit("musicbrainz", 3.0))
        self.assertTrue(limiter.admit("musicbrainz", 3.0))
        self.assertEqual(slept, [1.0])

    def test_call_that_would_wait_past_the_deadline_is_refused_not_queued(self):
        clock = [0.0]
        slept = []
        limiter = SourceLimiter({"musicbrainz": 1.0}, clock=lambda: clock[0], sleep=slept.append)
        self.assertTrue(limiter.admit("musicbrainz", 3.0))
        self.assertFalse(limiter.admit("musicbrainz", 0.5))
        self.assertEqual(slept, [])

    def test_sources_are_paced_independently(self):
        clock = [0.0]
        slept = []
        limiter = SourceLimiter({"musicbrainz": 1.0, "lastfm": 0.2}, clock=lambda: clock[0], sleep=slept.append)
        self.assertTrue(limiter.admit("musicbrainz", 3.0))
        self.assertTrue(limiter.admit("lastfm", 3.0))
        self.assertEqual(slept, [])


class MusicBrainzTests(unittest.TestCase):
    def client(self, get, pause=lambda _: None):
        return MusicBrainzSearch(get=get, limiter=open_limiter(), pause=pause)

    def test_503_is_retried_with_backoff_and_then_succeeds(self):
        pauses = []
        get = ScriptedGet(
            FakeResponse(503),
            FakeResponse(200, {"artists": [{"id": "mb-1", "name": "Ash"}]}),
        )
        result = self.client(get, pauses.append).artists("ash", remaining=plenty, cancelled=never_cancelled())
        self.assertEqual([c["name"] for c in result], ["Ash"])
        self.assertEqual(pauses, [1.0])
        self.assertEqual(len(get.requests), 2)

    def test_persistent_503_is_a_failure_after_the_last_retry(self):
        get = ScriptedGet(FakeResponse(503), FakeResponse(503), FakeResponse(503))
        with self.assertRaises(ProviderError) as raised:
            self.client(get).artists("ash", remaining=plenty, cancelled=never_cancelled())
        self.assertEqual(raised.exception.state, "failed")
        self.assertEqual(len(get.requests), 3)

    def test_refused_pacing_reports_rate_limited_without_a_request(self):
        limiter = SourceLimiter({"musicbrainz": 5.0})
        limiter.admit("musicbrainz", 10.0)
        get = ScriptedGet()
        client = MusicBrainzSearch(get=get, limiter=limiter, pause=lambda _: None)
        with self.assertRaises(ProviderError) as raised:
            client.artists("ash", remaining=lambda: 0.1, cancelled=never_cancelled())
        self.assertEqual(raised.exception.state, "rate_limited")
        self.assertEqual(get.requests, [])

    def test_artist_query_is_one_quoted_phrase_with_depth_fifty(self):
        get = ScriptedGet(FakeResponse(200, {"artists": []}))
        self.client(get).artists('a "b"', remaining=plenty, cancelled=never_cancelled())
        _, params = get.requests[0]
        self.assertEqual(params["query"], 'artist:"a \\"b\\""')
        self.assertEqual(params["limit"], 50)

    def test_album_candidates_join_the_artist_credit_and_keep_the_year(self):
        get = ScriptedGet(FakeResponse(200, {"release-groups": [{
            "id": "rg-1",
            "title": "Kid A",
            "first-release-date": "2000-10-02",
            "artist-credit": [
                {"name": "Radiohead", "joinphrase": " & "},
                {"name": "Thom Yorke", "joinphrase": ""},
            ],
        }]}))
        [album] = self.client(get).albums("kid a", remaining=plenty, cancelled=never_cancelled())
        self.assertEqual(album["artist"], "Radiohead & Thom Yorke")
        self.assertEqual(album["year"], 2000)
        self.assertEqual(album["release_group_mbid"], "rg-1")
        self.assertEqual(album["key"], "radiohead thom yorke/kid a")

    def test_cancelled_work_makes_no_request(self):
        cancelled = threading.Event()
        cancelled.set()
        get = ScriptedGet()
        with self.assertRaises(ProviderError):
            self.client(get).artists("ash", remaining=plenty, cancelled=cancelled)
        self.assertEqual(get.requests, [])

    def test_lucene_phrase_escapes_only_quote_and_backslash(self):
        self.assertEqual(lucene_phrase('a\\b"c'), '"a\\\\b\\"c"')


class LastFmTests(unittest.TestCase):
    def test_error_inside_an_http_200_body_is_a_failure_not_an_empty_answer(self):
        get = ScriptedGet(FakeResponse(200, {"error": 10, "message": "Invalid API key"}))
        client = LastFmSearch(get=get, limiter=open_limiter(), api_key="k")
        with self.assertRaises(ProviderError) as raised:
            client.artists("ash", remaining=plenty, cancelled=never_cancelled())
        self.assertEqual(raised.exception.state, "failed")

    def test_single_match_object_and_list_are_both_read(self):
        single = {"results": {"artistmatches": {"artist": {"name": "Ash", "mbid": ""}}}}
        client = LastFmSearch(get=ScriptedGet(FakeResponse(200, single)), limiter=open_limiter(), api_key="k")
        [artist] = client.artists("ash", remaining=plenty, cancelled=never_cancelled())
        self.assertEqual((artist["name"], artist["mbid"], artist["source"]), ("Ash", None, "lastfm"))

    def test_api_key_is_sent_as_a_parameter_only(self):
        get = ScriptedGet(FakeResponse(200, {"results": {"albummatches": {"album": []}}}))
        client = LastFmSearch(get=get, limiter=open_limiter(), api_key="secret")
        client.albums("kid a", remaining=plenty, cancelled=never_cancelled())
        _, params = get.requests[0]
        self.assertEqual(params["api_key"], "secret")
        self.assertEqual(params["method"], "album.search")


class CacheTests(unittest.TestCase):
    def test_non_empty_entries_live_a_day_and_empty_answers_an_hour(self):
        store = {}
        write_cached(store.__setitem__, "k1", [{"name": "Ash"}], now=1000.0)
        write_cached(store.__setitem__, "k2", [], now=1000.0)
        self.assertIsNotNone(read_cached(store.get, "k1", now=1000.0 + POSITIVE_TTL_SECONDS))
        self.assertIsNone(read_cached(store.get, "k1", now=1001.0 + POSITIVE_TTL_SECONDS))
        self.assertIsNotNone(read_cached(store.get, "k2", now=1000.0 + NEGATIVE_TTL_SECONDS))
        self.assertIsNone(read_cached(store.get, "k2", now=1001.0 + NEGATIVE_TTL_SECONDS))

    def test_malformed_entries_are_misses(self):
        self.assertIsNone(read_cached(lambda _: "junk", "k", now=0.0))
        self.assertIsNone(read_cached(lambda _: {"at": "x", "results": []}, "k", now=0.0))

    def test_key_carries_source_generation_and_depth_but_no_credential(self):
        self.assertEqual(
            provider_cache_key("lastfm", 3, "ash", "artist"),
            "search:lastfm:3:ash:artist:depth50",
        )


if __name__ == "__main__":
    unittest.main()
