import unittest

from discovery.artist_tag_fallback import (
    fallback_artist_tags, fetch_musicbrainz_genres, load_genre_vocabulary,
)


class Resp:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body


def discogs_results(*releases):
    """Build a Discogs /database/search response from (title, styles) pairs."""
    return Resp({"results": [{"title": title, "style": list(styles)} for title, styles in releases]})


class FakeDiscogs:
    def __init__(self, answers):
        self.answers, self.calls, self.headers_seen = answers, [], []

    def __call__(self, url, params=None, headers=None, **_):
        artist = (params or {}).get("artist")
        self.calls.append(artist)
        self.headers_seen.append(dict(headers or {}))
        answer = self.answers[artist]
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
    def run_fallback(self, answers, existing=None, mbids=None, names=None, token="tok", **kwargs):
        self.discogs, self.cache = FakeDiscogs(answers), Cache()
        mbid_list = mbids if mbids is not None else list(answers)
        artist_names = names if names is not None else {m: f"Artist {m}" for m in mbid_list}
        return fallback_artist_tags(
            mbid_list, existing or {}, get=self.discogs, discogs_token=token,
            artist_names=artist_names, vocabulary=GENRES,
            cache_get=self.cache.get, cache_set=self.cache.set, **kwargs)

    def test_keeps_only_vocabulary_styles_ordered_by_frequency_and_ignores_other_artists(self):
        result = self.run_fallback(
            {"Artist a": discogs_results(
                ("Artist a - One", ["Desert Blues", "Tuareg"]),
                ("Artist a (2) - Two", ["Desert Blues", "Rock"]),
                ("Other Artist - Three", ["Jazz Fusion"]),
            )},
            mbids=["a"],
        )
        self.assertEqual(result, {"a": ["desert blues", "rock"]})
        self.assertEqual(self.discogs.headers_seen[0]["Authorization"], "Discogs token=tok")

    def test_existing_tags_come_first_and_are_not_duplicated(self):
        result = self.run_fallback(
            {"Artist a": discogs_results(("Artist a - Album", ["Blues", "Rock"]))},
            existing={"a": ["rock"]}, mbids=["a"],
        )
        self.assertEqual(result, {"a": ["rock", "blues"]})

    def test_artists_with_enough_tags_cost_no_call(self):
        result = self.run_fallback(
            {"Artist a": discogs_results(("Artist a - Album", ["Blues"]))},
            existing={"a": ["rock", "blues"]}, mbids=["a"],
        )
        self.assertEqual((result, self.discogs.calls), ({}, []))

    def test_unchanged_artists_are_left_out(self):
        result = self.run_fallback(
            {"Artist a": discogs_results(("Artist a - Album", ["Tuareg"]))},
            mbids=["a"],
        )
        self.assertEqual(result, {})

    def test_limit_caps_the_merged_list(self):
        result = self.run_fallback(
            {"Artist a": discogs_results(
                ("Artist a - 1", ["Blues", "Rock", "Jazz Fusion"]),
                ("Artist a - 2", ["Blues", "Rock"]),
                ("Artist a - 3", ["Blues"]),
            )},
            mbids=["a"], limit=2,
        )
        self.assertEqual(result, {"a": ["blues", "rock"]})

    def test_results_are_cached_including_not_found(self):
        answers = {
            "Artist a": discogs_results(("Artist a - Album", ["Blues"])),
            "Artist b": discogs_results(),
        }
        self.assertEqual(self.run_fallback(answers, mbids=["a", "b"]), {"a": ["blues"]})
        self.assertEqual(self.cache.data["discogs:artist-tags:b"], [])
        calls = len(self.discogs.calls)
        again = fallback_artist_tags(
            ["a", "b"], {}, get=self.discogs, discogs_token="tok",
            artist_names={"a": "Artist a", "b": "Artist b"}, vocabulary=GENRES,
            cache_get=self.cache.get, cache_set=self.cache.set,
        )
        self.assertEqual((again, len(self.discogs.calls)), ({"a": ["blues"]}, calls))

    def test_transient_failure_is_not_cached_and_does_not_stop_others(self):
        answers = {
            "Artist a": RuntimeError("boom"),
            "Artist b": Resp({}, 429),
            "Artist c": discogs_results(("Artist c - Album", ["Blues"])),
        }
        self.assertEqual(self.run_fallback(answers, mbids=["a", "b", "c"]), {"c": ["blues"]})
        self.assertEqual(set(self.cache.data), {"discogs:artist-tags:c"})

    def test_call_budget_is_respected_in_the_order_given(self):
        answers = {f"Artist {m}": discogs_results((f"Artist {m} - Album", ["Blues"])) for m in "abc"}
        result = self.run_fallback(answers, mbids=["a", "b", "c"], max_calls=2, workers=1)
        self.assertEqual((sorted(result), self.discogs.calls), (["a", "b"], ["Artist a", "Artist b"]))

    def test_empty_vocabulary_input_token_or_name_makes_no_calls(self):
        fake = FakeDiscogs({})
        cache = Cache()
        self.assertEqual(fallback_artist_tags(
            ["a"], {}, get=fake, discogs_token="tok", artist_names={"a": "Artist a"},
            vocabulary=[], cache_get=cache.get, cache_set=cache.set), {})
        self.assertEqual(fallback_artist_tags(
            [], {}, get=fake, discogs_token="tok", artist_names={},
            vocabulary=GENRES, cache_get=cache.get, cache_set=cache.set), {})
        self.assertEqual(fallback_artist_tags(
            ["a"], {}, get=fake, discogs_token="", artist_names={"a": "Artist a"},
            vocabulary=GENRES, cache_get=cache.get, cache_set=cache.set), {})
        self.assertEqual(fallback_artist_tags(
            ["a"], {}, get=fake, discogs_token="tok", artist_names={},
            vocabulary=GENRES, cache_get=cache.get, cache_set=cache.set), {})
        self.assertEqual(fake.calls, [])

    def test_invalid_arguments_are_rejected(self):
        for kwargs in ({"min_existing": -1}, {"limit": True}, {"max_calls": 1.5}, {"workers": 0}):
            with self.assertRaises(ValueError):
                self.run_fallback({"Artist a": discogs_results(("Artist a - Album", ["Blues"]))}, mbids=["a"], **kwargs)


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
