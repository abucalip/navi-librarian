"""Synthetic tests: candidate-pool genre prefetch runs before the supplementary tag lane."""
import time
import unittest
from unittest import mock

import discovery_candidate_gathering as gathering
from discovery_candidate_gathering import RecommendationProviders, gather_recommendation_candidates

PROFILE_MBID = "p-jazz"
PROFILE_GENRES = ["jazz", "modal jazz"]
CANDIDATE_GENRES = {"c-1": ["dub"], "c-2": ["folk"], "c-3": ["dub"]}


def _music_key(value):
    return "".join(str(value).casefold().split())


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("synthetic status")

    def json(self):
        return self._payload


class _MusicBrainzClient:
    def __init__(self, log, failing_artists=()):
        self._log = log
        self._failing_artists = set(failing_artists)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        if "/artist/" in url:
            artist_id = url.rsplit("/", 1)[1]
            self._log["artist"].append(artist_id)
            if artist_id in self._failing_artists:
                return _Response({}, status_code=503)
            genres = PROFILE_GENRES if artist_id == PROFILE_MBID else CANDIDATE_GENRES[artist_id]
            return _Response({"genres": [{"name": name} for name in genres]})
        if "/release-group/" in url:
            self._log["queries"].append(params["query"])
            return _Response({"release-groups": []})
        return _Response({}, status_code=404)


def _listens():
    now = int(time.time())
    return [
        {
            "listened_at": now - index * 3600,
            "track_metadata": {
                "artist_name": "Profile Jazz",
                "additional_info": {"artist_mbid": PROFILE_MBID},
            },
        }
        for index in range(12)
    ]


def _run(*, warm, failing_artists=(), prefetch_limit=5):
    cache = {}
    for index, artist_id in enumerate(CANDIDATE_GENRES, start=1):
        cache[f"mb:recording:rec-{index}"] = {
            "title": f"Track {index}",
            "artist-credit": [{"name": f"Cand {index}", "artist": {"id": artist_id}}],
            "releases": [{"release-group": {
                "id": f"rg-{index}", "title": f"Cand Album {index}",
                "primary-type": "Album", "secondary-types": [],
            }}],
        }
    if warm:
        cache[f"mb:artist-genres:{PROFILE_MBID}"] = list(PROFILE_GENRES)
        for artist_id, genres in CANDIDATE_GENRES.items():
            cache[f"mb:artist-genres:{artist_id}"] = list(genres)
    recordings = [
        {"recording_mbid": f"rec-{index}", "score": 300 - (index - 1) * 100}
        for index in range(1, len(CANDIDATE_GENRES) + 1)
    ]
    log = {"queries": [], "artist": []}
    providers = RecommendationProviders(
        listenbrainz_recent=lambda days: _listens(),
        listenbrainz_username=lambda: "fixture-user",
        music_key=_music_key,
        metadata_cache_get=lambda key, **kwargs: cache.get(key),
        metadata_cache_set=lambda key, value, *args, **kwargs: cache.__setitem__(key, value),
        is_album_candidate=lambda candidate: True,
        api_call=lambda *args, **kwargs: {"albumList2": {"album": []}},
        items=lambda root: list(root or []),
        http_get=lambda url, params=None, **kwargs: _Response({"payload": {
            "mbids": recordings if params["offset"] == 0 else [],
        }}),
        http_client=lambda *args, **kwargs: _MusicBrainzClient(log, failing_artists),
        sleep=lambda _seconds: None,
    )
    with mock.patch.object(gathering, "CANDIDATE_PREFETCH_LIMIT", prefetch_limit):
        result = gather_recommendation_candidates(providers, shortlist_target=10)
    return result, log


class CandidateGenrePrefetchTests(unittest.TestCase):
    def test_cold_cache_plans_exploration_queries_from_prefetched_candidate_genres(self):
        result, log = _run(warm=False)

        self.assertNotIsInstance(result, str)
        self.assertIn('primarytype:album AND tag:dub', log["queries"])
        self.assertIn('primarytype:album AND tag:folk', log["queries"])

    def test_cold_and_warm_cache_plan_the_same_queries(self):
        _cold, cold_log = _run(warm=False)
        _warm, warm_log = _run(warm=True)

        self.assertEqual(cold_log["queries"], warm_log["queries"])

    def test_each_artist_is_looked_up_once_per_run(self):
        _result, log = _run(warm=False)

        self.assertEqual(sorted(log["artist"]), sorted(set(log["artist"])))
        self.assertEqual(set(log["artist"]), {PROFILE_MBID, *CANDIDATE_GENRES})

    def test_prefetch_limit_zero_keeps_the_previous_cold_plan(self):
        _result, log = _run(warm=False, prefetch_limit=0)

        self.assertNotIn('primarytype:album AND tag:dub', log["queries"])
        self.assertNotIn('primarytype:album AND tag:folk', log["queries"])

    def test_exhausted_retry_stops_the_candidate_prefetch(self):
        result, log = _run(warm=False, failing_artists=("c-1",))

        self.assertNotIsInstance(result, str)
        # The prefetch retries c-1 three times, then stops before c-2 and c-3.
        # Only the later genre stage looks up c-2 and c-3, once each.
        self.assertEqual(log["artist"][:4], [PROFILE_MBID, "c-1", "c-1", "c-1"])
        self.assertEqual(log["artist"].count("c-2"), 1)
        self.assertEqual(log["artist"].count("c-3"), 1)


if __name__ == "__main__":
    unittest.main()
