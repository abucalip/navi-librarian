"""Offline tests for the batched ListenBrainz artist-genre lookup (no network)."""
import unittest
from unittest import mock

import discovery_candidate_gathering as gathering
from discovery_batch_metadata import (
    ARTIST_GENRE_CHUNK,
    LISTENBRAINZ_ARTIST_URL,
    prefetch_artist_genres,
)
from discovery_candidate_gathering import RecommendationProviders, gather_recommendation_candidates


class _Response:
    def __init__(self, payload, status_code=200, bad_json=False):
        self.payload = payload
        self.status_code = status_code
        self.bad_json = bad_json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("status")

    def json(self):
        if self.bad_json:
            raise ValueError("not json")
        return self.payload


def _entry(*tags, mbid=None):
    return {"artist_mbid": mbid, "tag": {"artist": [
        {"tag": name, "count": 1, **({"genre_mbid": f"g-{name}"} if is_genre else {})}
        for name, is_genre in tags
    ]}}


class _Cache:
    def __init__(self, seeded=()):
        self.store = {key: ["seeded"] for key in seeded}
        self.writes = {}

    def get(self, key, **kwargs):
        return self.store.get(key)

    def set(self, key, value, **kwargs):
        self.store[key] = value
        self.writes[key] = value


def _call(get, ids, cache):
    return prefetch_artist_genres(
        get, ids, headers={}, cache_get=cache.get, cache_set=cache.set,
    )


class PrefetchArtistGenresTests(unittest.TestCase):
    def test_chunks_at_the_constant_and_comma_joins(self):
        ids = [f"a{i}" for i in range(ARTIST_GENRE_CHUNK * 2 + 1)]
        calls = []

        def get(url, params=None, **kwargs):
            calls.append((url, params))
            return _Response([])

        _call(get, ids, _Cache())

        self.assertEqual([len(p["artist_mbids"].split(",")) for _u, p in calls],
                         [ARTIST_GENRE_CHUNK, ARTIST_GENRE_CHUNK, 1])
        self.assertTrue(all(u == LISTENBRAINZ_ARTIST_URL and p["inc"] == "tag" for u, p in calls))

    def test_keeps_only_genre_mbid_tags_lowercased_sorted_deduplicated(self):
        body = [_entry((" Rock ", True), ("rock", True), ("Alt Pop", True), ("favourite", False), mbid="a1")]
        cache = _Cache()

        written = _call(lambda *a, **k: _Response(body), ["a1"], cache)

        self.assertEqual(cache.writes, {"mb:artist-genres:a1": ["alt pop", "rock"]})
        self.assertEqual(written, {"a1": ["alt pop", "rock"]})

    def test_artist_with_tag_object_but_no_genres_caches_empty_list(self):
        cache = _Cache()
        _call(lambda *a, **k: _Response([_entry(("x", False), mbid="a1")]), ["a1"], cache)
        self.assertEqual(cache.writes, {"mb:artist-genres:a1": []})

    def test_missing_artist_or_missing_tag_object_stays_uncached(self):
        cache = _Cache()
        _call(lambda *a, **k: _Response([{"artist_mbid": "a2", "artist": {}}]), ["a1", "a2"], cache)
        self.assertEqual(cache.writes, {})

    def test_failures_never_raise_and_leave_artists_uncached(self):
        def boom(*a, **k):
            raise RuntimeError("down")

        for get in (
            boom,
            lambda *a, **k: _Response({}, status_code=502),
            lambda *a, **k: _Response(None, bad_json=True),
            lambda *a, **k: _Response({"a1": 1}),
            lambda *a, **k: _Response([1, 2]),
        ):
            cache = _Cache()
            self.assertEqual(_call(get, ["a1"], cache), {})
            self.assertEqual(cache.writes, {})

    def test_failed_chunk_does_not_block_later_chunks(self):
        ids = [f"a{i}" for i in range(ARTIST_GENRE_CHUNK + 1)]
        responses = iter([_Response({}, status_code=502),
                          _Response([_entry(("jazz", True), mbid=ids[-1])])])
        cache = _Cache()

        _call(lambda *a, **k: next(responses), ids, cache)

        self.assertEqual(cache.writes, {f"mb:artist-genres:{ids[-1]}": ["jazz"]})

    def test_cached_artists_are_not_requested(self):
        cache = _Cache(seeded=["mb:artist-genres:a1"])
        calls = []

        def get(url, params=None, **kwargs):
            calls.append(params["artist_mbids"])
            return _Response([])

        _call(get, ["a1", "a2", "a2"], cache)
        self.assertEqual(calls, ["a2"])
        _call(get, ["a1"], cache)
        self.assertEqual(calls, ["a2"])


class GenreStageIntegrationTests(unittest.TestCase):
    def _providers(self, cache, sleeps, mb_requests, lb_gets):
        class Client:
            def __enter__(self_inner):
                return self_inner

            def __exit__(self_inner, *args):
                return False

            def get(self_inner, url, params=None, headers=None):
                mbid = url.rsplit("/", 1)[-1]
                if mbid == "rec-0":
                    return _Response({
                        "title": "Track",
                        "artist-credit": [{"name": "Cand", "artist": {"id": "cand"}}],
                        "releases": [{"release-group": {
                            "id": "rg", "title": "Album",
                            "primary-type": "Album", "secondary-types": []}}],
                    })
                mb_requests.append(mbid)
                return _Response({"genres": [{"name": "Fallback"}]})

        def http_get(url, params=None, **kwargs):
            if url == LISTENBRAINZ_ARTIST_URL:
                lb_gets.append(params["artist_mbids"].split(","))
                return _Response([_entry(("shoegaze", True), mbid="batched")])
            return _Response({"payload": {"mbids": [{"recording_mbid": "rec-0", "score": 9}]}})

        return RecommendationProviders(
            listenbrainz_recent=lambda days: [],
            listenbrainz_username=lambda: "fixture-user",
            music_key=lambda value: "".join(str(value).casefold().split()),
            metadata_cache_get=cache.get,
            metadata_cache_set=cache.set,
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {},
            items=lambda response: [],
            http_get=http_get,
            http_client=lambda *args, **kwargs: Client(),
            sleep=sleeps.append,
        )

    def test_batch_hit_skips_musicbrainz_and_spacing_and_missing_artist_falls_back(self):
        cache, sleeps, mb, lb = _Cache(), [], [], []
        providers = self._providers(cache, sleeps, mb, lb)
        listens = [
            {"track_metadata": {"artist_name": name, "additional_info": {"artist_mbid": name}}}
            for name in ("batched", "missing")
        ]
        providers = RecommendationProviders(**{**providers.__dict__,
                                               "listenbrainz_recent": lambda days: listens})

        gather_recommendation_candidates(providers)

        self.assertEqual(cache.store.get("mb:artist-genres:batched"), ["shoegaze"])
        self.assertNotIn("batched", mb)
        self.assertIn("missing", mb)
        self.assertEqual(cache.store.get("mb:artist-genres:missing"), ["fallback"])
        self.assertTrue(lb and all("batched" in group for group in lb))


if __name__ == "__main__":
    unittest.main()
