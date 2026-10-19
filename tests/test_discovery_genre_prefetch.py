"""Synthetic tests: profile genre prefetch runs before the supplementary tag lane."""
import time
import unittest

from discovery_candidate_gathering import RecommendationProviders, gather_recommendation_candidates

PROFILE_MBID = "p-jazz"
PROFILE_GENRES = ["jazz", "modal jazz"]


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
    """Serves artist genre lookups and release-group searches; records each request."""

    def __init__(self, log, artist_status=200):
        self._log = log
        self._artist_status = artist_status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        if "/artist/" in url:
            self._log["artist_lookups"].append(url.rsplit("/", 1)[1])
            if self._artist_status != 200:
                return _Response({}, status_code=self._artist_status)
            return _Response({"genres": [{"name": name} for name in PROFILE_GENRES]})
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


def _run(*, warm, artist_status=200):
    cache = {
        "mb:recording:rec-1": {
            "title": "Track 1",
            "artist-credit": [{"name": "Cand Artist", "artist": {"id": "c-1"}}],
            "releases": [{"release-group": {
                "id": "rg-1", "title": "Cand Album",
                "primary-type": "Album", "secondary-types": [],
            }}],
        },
    }
    if warm:
        cache[f"mb:artist-genres:{PROFILE_MBID}"] = list(PROFILE_GENRES)
    log = {"queries": [], "artist_lookups": []}
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
            "mbids": [{"recording_mbid": "rec-1", "score": 100}] if params["offset"] == 0 else [],
        }}),
        http_client=lambda *args, **kwargs: _MusicBrainzClient(log, artist_status),
        sleep=lambda _seconds: None,
    )
    result = gather_recommendation_candidates(providers, shortlist_target=10)
    return result, log, cache


class GenrePrefetchTests(unittest.TestCase):
    def test_cold_cache_plans_profile_queries_from_prefetched_genres(self):
        result, log, cache = _run(warm=False)

        self.assertNotIsInstance(result, str)
        self.assertEqual(
            log["queries"][:2],
            ['primarytype:album AND tag:jazz', 'primarytype:album AND tag:"modal jazz"'],
        )
        self.assertEqual(
            cache[f"mb:artist-genres:{PROFILE_MBID}"], sorted(PROFILE_GENRES),
        )
        # The profile artist is looked up once: the prefetch warms it, and the
        # later genre stage reads the cache instead of calling MusicBrainz again.
        self.assertEqual(log["artist_lookups"].count(PROFILE_MBID), 1)

    def test_cold_and_warm_cache_plan_the_same_profile_queries(self):
        cold, cold_log, _ = _run(warm=False)
        warm, warm_log, _ = _run(warm=True)

        self.assertEqual(cold_log["queries"], warm_log["queries"])
        self.assertEqual(
            cold["candidate_supply"]["tag_lane"]["profile_tag_count"],
            warm["candidate_supply"]["tag_lane"]["profile_tag_count"],
        )
        self.assertNotIn(PROFILE_MBID, warm_log["artist_lookups"])

    def test_prefetch_failure_does_not_fail_gathering(self):
        result, log, _cache = _run(warm=False, artist_status=503)

        self.assertNotIsInstance(result, str)
        self.assertEqual(log["queries"], [])
        self.assertIn(PROFILE_MBID, log["artist_lookups"])


if __name__ == "__main__":
    unittest.main()
