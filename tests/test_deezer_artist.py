import unittest

from integrations.deezer.artist import (
    ARTIST_NO_MATCH_PREFIX,
    ARTIST_SEARCH_CACHE_PREFIX,
    DEEZER_SPACING_SECONDS,
    NEGATIVE_TTL_SECONDS,
    POSITIVE_TTL_SECONDS,
    RELATED_ARTISTS_CACHE_PREFIX,
    RELATED_ARTISTS_NO_MATCH_PREFIX,
    TOP_TRACKS_CACHE_PREFIX,
    TOP_TRACKS_NO_MATCH_PREFIX,
    DeezerPacer,
    related_artists,
    search_artist_id,
    top_tracks,
)


class _FakeResponse:
    def __init__(self, status_code=200, body=None, raise_json=False):
        self.status_code = status_code
        self._body = body
        self._raise_json = raise_json

    def json(self):
        if self._raise_json:
            raise ValueError("bad json")
        return self._body


class DeezerArtistTests(unittest.TestCase):
    def setUp(self):
        self.cache = {}
        self.ttls_seen = []
        self.calls = []
        self.now = 1_000_000.0
        self.sleeps = []
        self.mono = 10.0
        self.pacer = DeezerPacer(
            spacing=DEEZER_SPACING_SECONDS,
            monotonic=lambda: self.mono,
            sleep=self._fake_sleep,
        )

    def _fake_sleep(self, seconds):
        self.sleeps.append(seconds)
        self.mono += seconds

    def _cache_get(self, key, ttl_seconds=0):
        self.ttls_seen.append((key, ttl_seconds))
        return self.cache.get(key)

    def _cache_set(self, key, value):
        self.cache[key] = value

    def test_search_artist_id_picks_highest_fans_exact_match_and_caches(self):
        def get(url, timeout=10.0):
            self.calls.append(url)
            return _FakeResponse(
                200,
                {
                    "data": [
                        {"id": 10, "name": "Broadcast Tribute", "nb_fan": 99999},
                        {"id": 11, "name": "Broadcast", "nb_fan": 50},
                        {"id": 42, "name": "broadcast", "nb_fan": 120000},
                    ]
                },
            )

        aid = search_artist_id(
            get, self._cache_get, self._cache_set, "  Broadcast  ",
            clock=lambda: self.now, pacer=self.pacer,
        )
        self.assertEqual(aid, 42)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("search/artist", self.calls[0])
        self.assertEqual(self.cache[f"{ARTIST_SEARCH_CACHE_PREFIX}broadcast"]["id"], 42)
        self.assertEqual(self.ttls_seen[0][1], POSITIVE_TTL_SECONDS)

        # Second call hits cache without HTTP or pacer sleep.
        aid2 = search_artist_id(
            get, self._cache_get, self._cache_set, "Broadcast",
            clock=lambda: self.now, pacer=self.pacer,
        )
        self.assertEqual(aid2, 42)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.sleeps, [])

    def test_search_artist_id_negative_mark_and_expiry(self):
        def get_empty(url, timeout=10.0):
            self.calls.append(url)
            return _FakeResponse(200, {"data": [{"id": 99, "name": "Other Artist", "nb_fan": 500}]})

        self.assertIsNone(
            search_artist_id(
                get_empty, self._cache_get, self._cache_set, "Unknown Band",
                clock=lambda: self.now, pacer=self.pacer,
            )
        )
        self.assertIn(f"{ARTIST_NO_MATCH_PREFIX}unknown band", self.cache)
        self.assertEqual(len(self.calls), 1)

        # Fresh negative mark skips HTTP.
        self.now += NEGATIVE_TTL_SECONDS - 1
        self.assertIsNone(
            search_artist_id(
                get_empty, self._cache_get, self._cache_set, "Unknown Band",
                clock=lambda: self.now, pacer=self.pacer,
            )
        )
        self.assertEqual(len(self.calls), 1)

        # After 1 hour, retries and succeeds.
        self.now += 1
        def get_found(url, timeout=10.0):
            self.calls.append(url)
            return _FakeResponse(200, {"data": [{"id": 77, "name": "Unknown Band", "nb_fan": 10}]})

        self.assertEqual(
            search_artist_id(
                get_found, self._cache_get, self._cache_set, "Unknown Band",
                clock=lambda: self.now, pacer=self.pacer,
            ),
            77,
        )
        self.assertEqual(len(self.calls), 2)

    def test_search_artist_id_errors_write_nothing(self):
        def get_500(url, timeout=10.0):
            return _FakeResponse(500, None)

        def get_api_err(url, timeout=10.0):
            return _FakeResponse(200, {"error": {"type": "QuotaException", "code": 4}})

        def get_raises(url, timeout=10.0):
            raise RuntimeError("network down")

        for fn in (get_500, get_api_err, get_raises):
            self.assertIsNone(
                search_artist_id(
                    fn, self._cache_get, self._cache_set, "Broadcast",
                    clock=lambda: self.now, pacer=self.pacer,
                )
            )
        self.assertEqual(self.cache, {})
        self.assertIsNone(
            search_artist_id(
                get_500, self._cache_get, self._cache_set, "   ",
                clock=lambda: self.now, pacer=self.pacer,
            )
        )

    def test_related_artists_caches_and_slices_limit(self):
        def get(url, timeout=10.0):
            self.calls.append(url)
            return _FakeResponse(
                200,
                {
                    "data": [
                        {"id": 1, "name": "Stereolab", "nb_fan": 50000},
                        {"id": 2, "name": "Pram", "nb_fan": 8000},
                        {"id": 3, "name": "", "nb_fan": 100},
                    ]
                },
            )

        res = related_artists(
            get, self._cache_get, self._cache_set, 42, limit=2,
            clock=lambda: self.now, pacer=self.pacer,
        )
        self.assertEqual(
            res,
            [
                {"id": 1, "name": "Stereolab", "nb_fan": 50000},
                {"id": 2, "name": "Pram", "nb_fan": 8000},
            ],
        )
        self.assertIn(f"{RELATED_ARTISTS_CACHE_PREFIX}42", self.cache)

        # Smaller limit reads from cache without HTTP.
        res_one = related_artists(
            get, self._cache_get, self._cache_set, 42, limit=1,
            clock=lambda: self.now, pacer=self.pacer,
        )
        self.assertEqual(res_one, [{"id": 1, "name": "Stereolab", "nb_fan": 50000}])
        self.assertEqual(len(self.calls), 1)

    def test_related_artists_empty_negative_mark_and_errors(self):
        def get_empty(url, timeout=10.0):
            self.calls.append(url)
            return _FakeResponse(200, {"data": []})

        self.assertEqual(
            related_artists(
                get_empty, self._cache_get, self._cache_set, 55,
                clock=lambda: self.now, pacer=self.pacer,
            ),
            [],
        )
        self.assertIn(f"{RELATED_ARTISTS_NO_MATCH_PREFIX}55", self.cache)
        self.assertEqual(
            related_artists(
                get_empty, self._cache_get, self._cache_set, 55,
                clock=lambda: self.now, pacer=self.pacer,
            ),
            [],
        )
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(
            related_artists(
                get_empty, self._cache_get, self._cache_set, 0,
                clock=lambda: self.now, pacer=self.pacer,
            ),
            [],
        )

    def test_top_tracks_parses_caches_and_negative_marks(self):
        def get(url, timeout=10.0):
            self.calls.append(url)
            return _FakeResponse(
                200,
                {
                    "data": [
                        {
                            "id": 101,
                            "title": "Come On Let's Go",
                            "rank": 54321,
                            "duration": 197,
                            "album": {"id": 9, "title": "The Noise Made by People"},
                        },
                        {"id": 102, "title": "Papercuts", "rank": 40000, "duration": 272},
                    ]
                },
            )

        tracks = top_tracks(
            get, self._cache_get, self._cache_set, 42, limit=1,
            clock=lambda: self.now, pacer=self.pacer,
        )
        self.assertEqual(
            tracks,
            [
                {
                    "id": 101,
                    "name": "Come On Let's Go",
                    "rank": 54321,
                    "duration": 197,
                    "album": "The Noise Made by People",
                }
            ],
        )
        self.assertIn(f"{TOP_TRACKS_CACHE_PREFIX}42", self.cache)

        # Second call with limit=2 hits cache.
        tracks2 = top_tracks(
            get, self._cache_get, self._cache_set, 42, limit=2,
            clock=lambda: self.now, pacer=self.pacer,
        )
        self.assertEqual(len(tracks2), 2)
        self.assertIsNone(tracks2[1]["album"])
        self.assertEqual(len(self.calls), 1)

        # Empty response writes negative mark.
        def get_empty(url, timeout=10.0):
            self.calls.append(url)
            return _FakeResponse(200, {"data": []})

        self.assertEqual(
            top_tracks(
                get_empty, self._cache_get, self._cache_set, 88,
                clock=lambda: self.now, pacer=self.pacer,
            ),
            [],
        )
        self.assertIn(f"{TOP_TRACKS_NO_MATCH_PREFIX}88", self.cache)

    def test_pacer_enforces_spacing_across_requests(self):
        def get(url, timeout=10.0):
            self.calls.append(url)
            return _FakeResponse(200, {"data": []})

        search_artist_id(
            get, self._cache_get, self._cache_set, "Artist One",
            clock=lambda: self.now, pacer=self.pacer,
        )
        related_artists(
            get, self._cache_get, self._cache_set, 1,
            clock=lambda: self.now, pacer=self.pacer,
        )
        top_tracks(
            get, self._cache_get, self._cache_set, 1,
            clock=lambda: self.now, pacer=self.pacer,
        )
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(len(self.sleeps), 2)
        for gap in self.sleeps:
            self.assertAlmostEqual(gap, DEEZER_SPACING_SECONDS)


if __name__ == "__main__":
    unittest.main()
