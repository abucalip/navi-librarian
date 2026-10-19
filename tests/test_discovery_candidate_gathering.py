import json
import unittest

from discovery_candidate_gathering import (
    RecommendationProviders,
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


class _Response:
    def __init__(self, payload):
        self.payload = payload

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
