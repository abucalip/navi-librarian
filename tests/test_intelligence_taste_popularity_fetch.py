import unittest
from unittest import mock

from intelligence.taste import fetch_artist_popularity
from intelligence.taste.popularity_fetch import (
    LISTENBRAINZ_SPACING_SECONDS, POPULARITY_ARTIST_URL, POPULARITY_CHUNK_SIZE,
)

HEADERS = {"User-Agent": "navi-test"}


def mbid(n):
    return f"00000000-0000-4000-8000-{n:012d}"


class Resp:
    def __init__(self, status=200, body=None, text=None):
        self.status_code = status
        self._body = body
        self.text = text if text is not None else ("" if body is None else "[...]")

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def echo(request_json):
    """Answer every requested MBID with a count of 1000 + its position in the request."""
    rows = [{"artist_mbid": m, "total_listen_count": 1000 + i}
            for i, m in enumerate(request_json["artist_mbids"])]
    return Resp(200, body=rows)


class FakePost:
    """Replays queued responses (a Resp, a callable taking the body, or an exception to raise)."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if not self.responses:
            return echo(json)
        item = self.responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item(json) if callable(item) else item


class PopularityFetchTests(unittest.TestCase):
    def setUp(self):
        self.recorded = []
        patcher = mock.patch(
            "recommendation_run_metrics.record_provider_call",
            side_effect=lambda provider, call: self.recorded.append((provider, call)),
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_fetch(self, mbids, *responses):
        self.post = FakePost(*responses)
        self.sleeps = []
        result = fetch_artist_popularity(
            mbids, post=self.post, headers=HEADERS, sleep=self.sleeps.append, timeout=12,
        )
        return result

    def test_chunking_250_mbids_makes_three_batch_requests(self):
        mbids = [mbid(i) for i in range(250)]
        result = self.run_fetch(mbids, echo, echo, echo)
        self.assertEqual(len(self.post.calls), 3)
        sizes = [len(c["json"]["artist_mbids"]) for c in self.post.calls]
        self.assertEqual(sizes, [POPULARITY_CHUNK_SIZE, POPULARITY_CHUNK_SIZE, 50])
        self.assertEqual(len(result), 250)
        self.assertEqual(list(result), mbids)

    def test_request_shape_is_one_post_with_exact_body(self):
        self.run_fetch([mbid(1), mbid(2)], echo)
        self.assertEqual(len(self.post.calls), 1)
        call = self.post.calls[0]
        self.assertEqual(call["url"], "https://api.listenbrainz.org/1/popularity/artist")
        self.assertEqual(call["url"], POPULARITY_ARTIST_URL)
        self.assertEqual(call["json"], {"artist_mbids": [mbid(1), mbid(2)]})
        self.assertEqual(call["headers"], HEADERS)
        self.assertEqual(call["timeout"], 12)

    def test_duplicates_are_removed_in_first_seen_order(self):
        a, b, c = mbid(1), mbid(2), mbid(3)
        result = self.run_fetch([a, b, a, c, b], echo)
        self.assertEqual(len(self.post.calls), 1)
        self.assertEqual(self.post.calls[0]["json"], {"artist_mbids": [a, b, c]})
        self.assertEqual(list(result), [a, b, c])

    def test_empty_list_makes_no_request_and_no_pause(self):
        result = self.run_fetch([])
        self.assertEqual(result, {})
        self.assertEqual(self.post.calls, [])
        self.assertEqual(self.sleeps, [])
        self.assertEqual(self.recorded, [])

    def test_empty_and_missing_mbids_are_skipped(self):
        result = self.run_fetch([None, "", mbid(7)], echo)
        self.assertEqual(self.post.calls[0]["json"], {"artist_mbids": [mbid(7)]})
        self.assertEqual(list(result), [mbid(7)])

    def test_404_gives_none_for_every_mbid_in_the_chunk(self):
        a, b = mbid(1), mbid(2)
        result = self.run_fetch([a, b], Resp(404, text="not found"))
        self.assertEqual(result, {a: None, b: None})
        self.assertEqual(self.sleeps, [LISTENBRAINZ_SPACING_SECONDS])

    def test_200_with_empty_body_gives_none(self):
        a = mbid(1)
        result = self.run_fetch([a], Resp(200, text="   "))
        self.assertEqual(result, {a: None})

    def test_500_raises_and_still_pauses(self):
        with self.assertRaises(RuntimeError):
            self.run_fetch([mbid(1)], Resp(500, body=[], text="boom"))
        self.assertEqual(self.sleeps, [LISTENBRAINZ_SPACING_SECONDS])

    def test_transport_error_raises(self):
        with self.assertRaises(ConnectionError):
            self.run_fetch([mbid(1)], ConnectionError("down"))
        self.assertEqual(self.sleeps, [LISTENBRAINZ_SPACING_SECONDS])

    def test_bad_json_raises(self):
        with self.assertRaises(ValueError):
            self.run_fetch([mbid(1)], Resp(200, body=ValueError("not json"), text="<html>"))

    def test_non_list_json_raises(self):
        with self.assertRaises(RuntimeError):
            self.run_fetch([mbid(1)], Resp(200, body={"error": "x"}))

    def test_failure_in_a_later_chunk_raises_instead_of_partial_result(self):
        mbids = [mbid(i) for i in range(150)]
        with self.assertRaises(RuntimeError):
            self.run_fetch(mbids, echo, Resp(503, text="busy"))

    def test_null_counts_become_none_and_absent_mbids_are_none(self):
        a, b, c = mbid(1), mbid(2), mbid(3)

        def answer(_):
            return Resp(200, body=[
                {"artist_mbid": a, "total_listen_count": 42},
                {"artist_mbid": b, "total_listen_count": None},
                {"artist_mbid": "ffffffff-0000-4000-8000-000000000000", "total_listen_count": 9},
            ])

        result = self.run_fetch([a, b, c], answer)
        self.assertEqual(result, {a: 42, b: None, c: None})

    def test_one_pause_and_one_count_per_request(self):
        mbids = [mbid(i) for i in range(250)]
        self.run_fetch(mbids, echo, echo, echo)
        self.assertEqual(self.sleeps, [LISTENBRAINZ_SPACING_SECONDS] * 3)
        self.assertEqual(self.recorded, [("listenbrainz", "popularity_artist")] * 3)


if __name__ == "__main__":
    unittest.main()
