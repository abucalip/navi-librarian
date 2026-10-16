import json
import unittest

from discovery_candidate_gathering import (
    RecommendationProviders,
    gather_recommendation_candidates,
)


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
