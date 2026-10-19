import json
import unittest
from unittest import mock

from discovery_candidate_gathering import (
    RecommendationProviders,
    _TAG_SEARCH_ATTEMPTS,
    _get_with_bounded_retry,
    gather_recommendation_candidates,
)


class GenreLookupRetryTests(unittest.TestCase):
    def _run(self, statuses):
        client = _ScriptedClient(statuses)
        sleeps = []
        response = _get_with_bounded_retry(
            client,
            "https://musicbrainz.org/ws/2/artist/synthetic",
            params={"fmt": "json", "inc": "genres"},
            headers={},
            sleep=sleeps.append,
        )
        return response, client.calls, sleeps

    def test_success_on_first_attempt_does_not_retry_or_sleep(self):
        response, calls, sleeps = self._run([200])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [])

    def test_transient_503_then_success_returns_success(self):
        response, calls, sleeps = self._run([503, 503, 200])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, 3)
        self.assertEqual(sleeps, [2, 4])

    def test_retry_exhaustion_returns_last_retryable_status_after_bounded_attempts(self):
        response, calls, sleeps = self._run([503, 429, 502, 200])
        self.assertEqual(response.status_code, 502)
        self.assertEqual(calls, 3)
        self.assertEqual(sleeps, [2, 4])

    def test_non_retryable_status_is_returned_without_retry(self):
        response, calls, sleeps = self._run([404, 200])
        self.assertEqual(response.status_code, 404)
        self.assertEqual(calls, 1)
        self.assertEqual(sleeps, [])


class TagSearchRetryTests(unittest.TestCase):
    def _run(self, statuses):
        client = _ScriptedClient(statuses)
        sleeps = []
        response = _get_with_bounded_retry(
            client,
            "https://musicbrainz.org/ws/2/release-group/",
            params={"query": "tag:synthetic", "fmt": "json", "limit": 10},
            headers={},
            sleep=sleeps.append,
            attempts=_TAG_SEARCH_ATTEMPTS,
        )
        return response, client.calls, sleeps

    def test_tag_search_transient_503_recovers_with_one_retry(self):
        response, calls, sleeps = self._run([503, 200])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [2])

    def test_tag_search_retry_budget_is_one_retry_then_returns_last_status(self):
        response, calls, sleeps = self._run([503, 503, 200])
        self.assertEqual(response.status_code, 503)
        self.assertEqual(calls, 2)
        self.assertEqual(sleeps, [2])


class SupplementaryLaneStopTests(unittest.TestCase):
    def _run(self, *, release_group_statuses):
        mb_client = _TagSearchClient(release_group_statuses)
        cache = {}
        for index in range(3):
            cache[f"mb:recording:rec-{index}"] = _recording("Dominant", index)
        cache["mb:artist-genres:artist-Dominant"] = ["synthetic jazz", "synthetic soul"]
        pages = {0: [_cf_item(i) for i in range(3)]}
        providers = RecommendationProviders(
            listenbrainz_recent=lambda days: [],
            listenbrainz_username=lambda: "fixture-user",
            music_key=lambda value: "".join(str(value).casefold().split()),
            metadata_cache_get=lambda key, **kwargs: cache.get(key),
            metadata_cache_set=lambda *args, **kwargs: None,
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {},
            items=lambda response: [],
            http_get=lambda url, params=None, **kwargs: _Response(
                {"payload": {"mbids": pages.get(params["offset"], [])}}
            ),
            http_client=lambda *args, **kwargs: mb_client,
            sleep=lambda _seconds: None,
        )
        result = gather_recommendation_candidates(providers)
        return result, mb_client

    def test_persistent_503_stops_lane_after_one_bounded_retry(self):
        result, mb_client = self._run(release_group_statuses=[503] * 20)

        self.assertGreaterEqual(len(mb_client.release_group_queries), 1)
        # Each query exhausts its two attempts, then the lane stops: no further queries.
        self.assertEqual(mb_client.release_group_calls, _TAG_SEARCH_ATTEMPTS)
        supplementary = result["candidate_supply"]["supplementary"]
        self.assertEqual(supplementary["supplementary_queries_failed"], 1)
        self.assertEqual(supplementary["supplementary_candidates_added"], 0)

    def test_transient_503_then_success_still_adds_candidates(self):
        result, mb_client = self._run(release_group_statuses=[503, 200] + [200] * 20)

        supplementary = result["candidate_supply"]["supplementary"]
        self.assertEqual(supplementary["supplementary_queries_failed"], 0)
        self.assertGreater(supplementary["supplementary_candidates_added"], 0)


class _TagSearchClient:
    """Serves recording and release-group responses; release-group statuses are scripted."""

    def __init__(self, release_group_statuses):
        self._statuses = list(release_group_statuses)
        self.release_group_calls = 0
        self.release_group_queries = set()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        if "/release-group/" not in url:
            return _Response({}, status_code=200)
        self.release_group_calls += 1
        self.release_group_queries.add((params or {}).get("query"))
        status = self._statuses.pop(0) if self._statuses else 200
        if status != 200:
            return _StatusRaisingResponse(status)
        return _Response({"release-groups": [{
            "title": f"Synthetic Album {self.release_group_calls}",
            "primary-type": "Album",
            "secondary-types": [],
            "artist-credit": [{"name": "Synthetic Artist", "artist": {"id": "artist-syn"}}],
        }]}, status_code=200)


class HTTPStatusError(Exception):
    """Named like the httpx error so the bounded error-class label matches production."""


class _StatusRaisingResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        raise HTTPStatusError(f"{self.status_code} synthetic")


class _ScriptedClient:
    def __init__(self, statuses):
        self._statuses = list(statuses)
        self.calls = 0

    def get(self, url, *, params=None, headers=None):
        self.calls += 1
        return _StatusResponse(self._statuses.pop(0))


class _StatusResponse:
    def __init__(self, status_code):
        self.status_code = status_code


class RecommendationCandidateGatheringTests(unittest.TestCase):
    def _providers(self, *, listens=None, username="fixture-user", http_get=None):
        return RecommendationProviders(
            listenbrainz_recent=listens or (lambda days: []),
            listenbrainz_username=lambda: username,
            music_key=lambda value: "".join(str(value).casefold().split()),
            metadata_cache_get=lambda *args, **kwargs: None,
            metadata_cache_set=lambda *args, **kwargs: None,
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {},
            items=lambda response: [],
            http_get=http_get or (lambda *args, **kwargs: _Response({"payload": {"mbids": []}})),
            http_client=lambda *args, **kwargs: _Client(),
            sleep=lambda _seconds: None,
        )

    def test_listen_history_failure_returns_legacy_error_before_recommendation_request(self):
        requested = []
        providers = self._providers(
            listens=lambda days: (_ for _ in ()).throw(RuntimeError("provider down")),
            http_get=lambda *args, **kwargs: requested.append(args),
        )

        result = json.loads(gather_recommendation_candidates(providers))

        self.assertEqual(
            result["error"],
            "Could not retrieve recent listening history: provider down",
        )
        self.assertEqual(requested, [])

    def test_empty_recording_recommendations_keep_legacy_message(self):
        providers = self._providers()

        result = json.loads(gather_recommendation_candidates(providers))

        self.assertEqual(result["recommendations"], [])
        self.assertEqual(
            result["message"],
            "ListenBrainz returned no recording recommendations.",
        )


def _cf_item(index):
    return {"recording_mbid": f"rec-{index}", "score": 1000 - index}


def _recording(artist, album_index):
    return {
        "title": f"Track {album_index}",
        "artist-credit": [{"name": artist, "artist": {"id": f"artist-{artist}"}}],
        "releases": [{"release-group": {
            "id": f"rg-{artist}-{album_index}",
            "title": f"{artist} Album {album_index}",
            "primary-type": "Album",
            "secondary-types": [],
        }}],
    }


class RecommendationCfPagingTests(unittest.TestCase):
    def _providers(self, *, pages, recordings=None, cache=None, fail_page=None):
        calls = []
        pages_by_offset = pages
        recordings = recordings or {}
        cache = cache if cache is not None else {}

        def http_get(url, params=None, **kwargs):
            calls.append(dict(params or {}))
            offset = params["offset"]
            if fail_page is not None and offset == fail_page:
                raise RuntimeError("provider detail must not leak")
            return _Response({"payload": {"mbids": pages_by_offset.get(offset, [])}})

        mb_client = _RecordingClient(recordings)
        providers = RecommendationProviders(
            listenbrainz_recent=lambda days: [],
            listenbrainz_username=lambda: "fixture-user",
            music_key=lambda value: "".join(str(value).casefold().split()),
            metadata_cache_get=lambda key, **kwargs: cache.get(key),
            metadata_cache_set=lambda *args, **kwargs: None,
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {},
            items=lambda response: [],
            http_get=http_get,
            http_client=lambda *args, **kwargs: mb_client,
            sleep=lambda _seconds: None,
        )
        return providers, calls, mb_client

    def test_second_page_is_requested_with_offset_and_budget_stops_at_two_pages(self):
        pages = {
            0: [_cf_item(i) for i in range(100)],
            100: [_cf_item(i) for i in range(100, 200)],
            200: [_cf_item(i) for i in range(200, 300)],
        }
        recordings = {f"rec-{i}": _recording(f"Artist {i}", i) for i in range(200)}
        providers, calls, _ = self._providers(pages=pages, recordings=recordings)

        result = gather_recommendation_candidates(providers)

        self.assertEqual([c["offset"] for c in calls], [0, 100])
        self.assertTrue(all(c["count"] == 100 for c in calls))
        self.assertEqual(result["candidate_supply"]["cf_recordings"]["cf_recordings_returned"], 200)
        paging = result["candidate_supply"]["cf_paging"]
        self.assertEqual(paging["pages_requested"], 2)
        self.assertEqual(paging["pages_fetched"], 2)
        self.assertIsNone(paging["page_failure_class"])

    def test_short_page_stops_paging(self):
        pages = {0: [_cf_item(i) for i in range(100)], 100: [_cf_item(i) for i in range(100, 130)]}
        providers, calls, _ = self._providers(pages=pages)

        gather_recommendation_candidates(providers)

        self.assertEqual([c["offset"] for c in calls], [0, 100])

    def test_overlapping_mbids_across_pages_are_deduplicated(self):
        pages = {0: [_cf_item(i) for i in range(100)], 100: [_cf_item(i) for i in range(50, 150)]}
        providers, _, mb_client = self._providers(pages=pages)

        result = gather_recommendation_candidates(providers)

        self.assertEqual(result["candidate_supply"]["cf_recordings"]["cf_recordings_returned"], 150)
        self.assertEqual(len(set(mb_client.requested)), len(mb_client.requested))

    def test_second_page_failure_keeps_first_page_and_reports_class_only(self):
        pages = {0: [_cf_item(i) for i in range(100)]}
        recordings = {f"rec-{i}": _recording(f"Artist {i}", i) for i in range(100)}
        providers, calls, _ = self._providers(pages=pages, recordings=recordings, fail_page=100)

        result = gather_recommendation_candidates(providers)

        self.assertNotIn("error", result)
        paging = result["candidate_supply"]["cf_paging"]
        self.assertEqual(paging["pages_requested"], 2)
        self.assertEqual(paging["pages_fetched"], 1)
        self.assertEqual(paging["page_failure_class"], "RuntimeError")
        self.assertNotIn("must not leak", repr(result))
        self.assertEqual(result["candidate_supply"]["cf_recordings"]["cf_recordings_resolved"], 100)

    def test_first_page_failure_keeps_legacy_error_contract(self):
        providers, _, _ = self._providers(pages={}, fail_page=0)

        result = json.loads(gather_recommendation_candidates(providers))

        self.assertEqual(
            result["error"],
            "Could not retrieve ListenBrainz recommendations: provider detail must not leak",
        )

    def test_artist_cap_skips_cache_known_recordings_before_any_resolution_call(self):
        pages = {0: [_cf_item(i) for i in range(25)]}
        recordings = {f"rec-{i}": _recording("Dominant", i) for i in range(25)}
        cache = {f"mb:recording:rec-{i}": recordings[f"rec-{i}"] for i in range(25)}
        providers, _, mb_client = self._providers(pages=pages, recordings=recordings, cache=cache)

        result = gather_recommendation_candidates(providers)

        self.assertEqual(mb_client.requested, [])
        paging = result["candidate_supply"]["cf_paging"]
        self.assertEqual(paging["artist_cap_skipped"], 15)
        self.assertEqual(result["candidate_supply"]["cf_recordings"]["cf_recordings_resolved"], 10)

    def test_uncached_resolution_budget_bounds_mb_calls(self):
        pages = {0: [_cf_item(i) for i in range(20)]}
        recordings = {f"rec-{i}": _recording(f"Artist {i}", i) for i in range(20)}
        providers, _, mb_client = self._providers(pages=pages, recordings=recordings)

        with mock.patch("discovery_candidate_gathering.CF_MAX_UNCACHED_RESOLUTIONS", 3):
            result = gather_recommendation_candidates(providers)

        self.assertEqual(len(mb_client.requested), 3)
        paging = result["candidate_supply"]["cf_paging"]
        self.assertEqual(paging["uncached_resolution_calls"], 3)
        self.assertEqual(paging["resolution_budget_skipped"], 17)
        self.assertEqual(result["candidate_supply"]["cf_recordings"]["cf_recordings_resolved"], 3)


class _RecordingClient:
    def __init__(self, recordings):
        self.recordings = recordings
        self.requested = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        mbid = url.rsplit("/", 1)[-1]
        if mbid.startswith("rec-"):
            self.requested.append(mbid)
        return _Response(self.recordings.get(mbid, {}), status_code=200)


class _Response:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class _Client:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


if __name__ == "__main__":
    unittest.main()
