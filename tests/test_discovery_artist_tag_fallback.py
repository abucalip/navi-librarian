import unittest

from discovery.artist_tag_fallback import (
    fallback_artist_tags, fetch_musicbrainz_genres, load_genre_vocabulary,
)


class Resp:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body


def top_tags(*pairs):
    return Resp({"toptags": {"tag": [{"name": n, "count": str(c)} for n, c in pairs]}})


class FakeLastfm:
    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, url, params=None, **_):
        self.calls.append(params["mbid"])
        answer = self.answers[params["mbid"]]
        if isinstance(answer, Exception):
            raise answer
        return answer


class Cache:
    def __init__(self):
        self.data = {}

    def get(self, key, ttl_seconds=None):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value


GENRES = {"desert blues", "blues", "jazz fusion", "rock"}


class FallbackTagTests(unittest.TestCase):
    def run_fallback(self, answers, existing=None, mbids=None, **kwargs):
        self.lastfm, self.cache = FakeLastfm(answers), Cache()
        return fallback_artist_tags(
            mbids if mbids is not None else list(answers), existing or {}, get=self.lastfm, api_key="k",
            vocabulary=GENRES, cache_get=self.cache.get, cache_set=self.cache.set, **kwargs)

    def test_keeps_only_genre_tags_above_the_count_threshold(self):
        result = self.run_fallback({"a": top_tags(("desert blues", 100), ("tuareg", 90), ("blues", 5),
                                                  ("female vocalists", 80), ("Rock", 20))})
        self.assertEqual(result, {"a": ["desert blues", "rock"]})

    def test_existing_tags_come_first_and_are_not_duplicated(self):
        result = self.run_fallback({"a": top_tags(("blues", 100), ("rock", 50))}, existing={"a": ["rock"]})
        self.assertEqual(result, {"a": ["rock", "blues"]})

    def test_artists_with_enough_tags_cost_no_call(self):
        result = self.run_fallback({"a": top_tags(("blues", 100))}, existing={"a": ["rock", "blues"]})
        self.assertEqual((result, self.lastfm.calls), ({}, []))

    def test_unchanged_artists_are_left_out(self):
        self.assertEqual(self.run_fallback({"a": top_tags(("tuareg", 100))}), {})

    def test_limit_caps_the_merged_list(self):
        result = self.run_fallback({"a": top_tags(("blues", 100), ("rock", 90), ("jazz fusion", 80))}, limit=2)
        self.assertEqual(result, {"a": ["blues", "rock"]})

    def test_results_are_cached_including_not_found(self):
        answers = {"a": top_tags(("blues", 100)), "b": Resp({"error": 6, "message": "not found"})}
        self.assertEqual(self.run_fallback(answers), {"a": ["blues"]})
        self.assertEqual(self.cache.data["lfm:artist-tags:b"], [])
        calls = len(self.lastfm.calls)
        again = fallback_artist_tags(["a", "b"], {}, get=self.lastfm, api_key="k", vocabulary=GENRES,
                                     cache_get=self.cache.get, cache_set=self.cache.set)
        self.assertEqual((again, len(self.lastfm.calls)), ({"a": ["blues"]}, calls))

    def test_transient_failure_is_not_cached_and_does_not_stop_others(self):
        answers = {"a": RuntimeError("boom"), "b": Resp({"error": 11}), "c": top_tags(("blues", 100))}
        self.assertEqual(self.run_fallback(answers), {"c": ["blues"]})
        self.assertEqual(set(self.cache.data), {"lfm:artist-tags:c"})

    def test_call_budget_is_respected_in_the_order_given(self):
        answers = {m: top_tags(("blues", 100)) for m in "abc"}
        result = self.run_fallback(answers, max_calls=2, workers=1)
        self.assertEqual((sorted(result), sorted(self.lastfm.calls)), (["a", "b"], ["a", "b"]))

    def test_empty_vocabulary_or_input_makes_no_calls(self):
        fake = FakeLastfm({})
        cache = Cache()
        self.assertEqual(fallback_artist_tags(["a"], {}, get=fake, api_key="k", vocabulary=[],
                                              cache_get=cache.get, cache_set=cache.set), {})
        self.assertEqual(fallback_artist_tags([], {}, get=fake, api_key="k", vocabulary=GENRES,
                                              cache_get=cache.get, cache_set=cache.set), {})
        self.assertEqual(fake.calls, [])

    def test_invalid_arguments_are_rejected(self):
        for kwargs in ({"min_count": -1}, {"limit": True}, {"max_calls": 1.5}, {"workers": 0}):
            with self.assertRaises(ValueError):
                self.run_fallback({"a": top_tags(("blues", 100))}, **kwargs)


class GenreListTests(unittest.TestCase):
    def pages(self, total, per_page=100):
        def get(url, params=None, **_):
            start = params["offset"]
            names = [{"name": f"Genre {i}"} for i in range(start, min(start + per_page, total))]
            return Resp({"genres": names, "genre-count": total})
        return get

    def test_reads_every_page_and_lowercases(self):
        genres = fetch_musicbrainz_genres(self.pages(230), {})
        self.assertEqual((len(genres), "genre 229" in genres), (230, True))

    def test_a_failed_page_discards_the_partial_list(self):
        def get(url, params=None, **_):
            return Resp({}, 503) if params["offset"] else Resp(
                {"genres": [{"name": "Rock"}], "genre-count": 250})
        self.assertEqual(fetch_musicbrainz_genres(get, {}), set())
        self.assertEqual(fetch_musicbrainz_genres(lambda *a, **k: 1 / 0, {}), set())

    def test_a_page_that_never_answers_gives_up_after_the_attempts(self):
        calls = []
        self.assertEqual(fetch_musicbrainz_genres(lambda *a, **k: calls.append(1) or Resp({}, 503), {}), set())
        self.assertEqual(len(calls), 3)

    def test_a_page_that_fails_once_is_retried(self):
        calls = []

        def get(url, params=None, **_):
            calls.append(params["offset"])
            if len(calls) == 1:
                raise ConnectionError("dropped")
            return Resp({"genres": [{"name": "Rock"}], "genre-count": 1})
        self.assertEqual(fetch_musicbrainz_genres(get, {}), {"rock"})
        self.assertEqual(calls, [0, 0])

    def test_vocabulary_is_cached_and_reused(self):
        cache, fetches = Cache(), []

        def get(url, params=None, **_):
            fetches.append(params["offset"])
            return Resp({"genres": [{"name": "Rock"}], "genre-count": 1})
        first = load_genre_vocabulary(get, {}, cache.get, cache.set)
        second = load_genre_vocabulary(get, {}, cache.get, cache.set)
        self.assertEqual((first, second, fetches), ({"rock"}, {"rock"}, [0]))

    def test_failed_load_is_not_cached(self):
        cache = Cache()
        self.assertEqual(load_genre_vocabulary(lambda *a, **k: Resp({}, 500), {}, cache.get, cache.set), set())
        self.assertEqual(cache.data, {})


if __name__ == "__main__":
    unittest.main()
