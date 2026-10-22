"""Direct-import regression tests for exact MusicBrainz album-year matching."""
import json
import unittest
from unittest.mock import patch

from integrations.musicbrainz import album_year as service


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class MusicBrainzAlbumYearTests(unittest.TestCase):
    def setUp(self):
        service.year_cache.clear()
        service._last_request = 0.0

    def test_exact_title_and_artist_credit_returns_earliest_valid_year(self):
        payload = {"release-groups": [
            {"title": "Album", "artist-credit": [{"artist": {"name": "Other"}}], "first-release-date": "1980"},
            {"title": "Album", "artist-credit": [{"artist": {"name": "Artist"}}], "first-release-date": "1998-05"},
            {"title": "Album", "artist-credit": [{"artist": {"name": "Artist"}}], "first-release-date": "1997"},
            {"title": "Album Deluxe", "artist-credit": [{"artist": {"name": "Artist"}}], "first-release-date": "1990"},
        ]}
        with patch.object(service, "urlopen", return_value=_Response(payload)), patch.object(service, "monotonic", return_value=100.0), patch.object(service, "sleep"):
            self.assertEqual(service.lookup_album_year("Artist", "Album"), 1997)

    def test_missing_inputs_do_not_request(self):
        with patch.object(service, "urlopen") as request:
            self.assertIsNone(service.lookup_album_year("", "Album"))
            self.assertIsNone(service.lookup_album_year("Artist", ""))
            request.assert_not_called()

    def test_negative_result_is_cached_for_short_ttl(self):
        payload = {"release-groups": []}
        with patch.object(service, "urlopen", return_value=_Response(payload)), patch.object(service, "monotonic", return_value=100.0), patch.object(service, "sleep"), patch.object(service, "_year_lock"):
            self.assertIsNone(service.lookup_album_year("Unknown", "Album"))
            with patch.object(service, "urlopen") as request:
                self.assertIsNone(service.lookup_album_year("Unknown", "Album"))
                request.assert_not_called()


class BatchAlbumYearTests(unittest.TestCase):
    def setUp(self):
        from integrations.musicbrainz import album_year
        self.module = album_year
        album_year.year_cache.clear()
        album_year._last_request = -1e9
        patcher = patch.object(album_year, "sleep", lambda seconds: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _group(self, title, artist, date):
        return {"title": title, "first-release-date": date,
                "artist-credit": [{"artist": {"name": artist}}]}

    def test_one_request_resolves_many_albums_with_the_exact_match_rule(self):
        calls = []

        def fetch(query, limit):
            calls.append((query, limit))
            return [self._group("One", "A", "1999-05-01"), self._group("One", "Someone Else", "1950"),
                    self._group("Two", "B", "2004")]

        result = self.module.lookup_album_years([("A", "One"), ("B", "Two"), ("C", "Three")], fetch=fetch)
        self.assertEqual(len(calls), 1)
        self.assertIn('(artist:"A" AND releasegroup:"One")', calls[0][0])
        self.assertEqual(result, {("A", "One"): 1999, ("B", "Two"): 2004, ("C", "Three"): None})

    def test_cached_pairs_cost_no_request_and_large_batches_are_chunked(self):
        pairs = [(f"Artist {i}", f"Album {i}") for i in range(20)]
        calls = []
        self.module.lookup_album_years(pairs, fetch=lambda q, n: calls.append(q) or [])
        self.assertEqual(len(calls), 2)
        self.module.lookup_album_years(pairs, fetch=lambda q, n: calls.append(q) or [])
        self.assertEqual(len(calls), 2)

    def test_a_failed_request_is_neither_returned_nor_cached(self):
        def broken(query, limit):
            raise RuntimeError("down")

        self.assertEqual(self.module.lookup_album_years([("A", "One")], fetch=broken), {})
        self.assertEqual(self.module.year_cache, {})

    def test_one_retry_recovers_from_a_rate_limited_request(self):
        attempts = []

        def flaky(query, limit):
            attempts.append(query)
            if len(attempts) == 1:
                raise RuntimeError("503")
            return [self._group("One", "A", "1999")]

        self.assertEqual(self.module.lookup_album_years([("A", "One")], fetch=flaky), {("A", "One"): 1999})
        self.assertEqual(len(attempts), 2)

    def test_a_capped_response_never_caches_a_missing_pair_as_no_year(self):
        pairs = [(f"Artist {i}", f"Album {i}") for i in range(4)]
        calls = []

        def fetch(query, limit):
            calls.append(query)
            if all(f'"Album {i}"' in query for i in range(4)):
                return [self._group(f"Filler {n}", "Nobody", "2000") for n in range(limit)]
            return [self._group(f"Album {i}", f"Artist {i}", str(2000 + i)) for i in range(4)
                    if f'"Album {i}"' in query]

        result = self.module.lookup_album_years(pairs, fetch=fetch)
        self.assertEqual(result, {pair: 2000 + i for i, pair in enumerate(pairs)})
        self.assertEqual(len(calls), 3)

    def test_quotes_in_names_are_escaped(self):
        seen = []
        self.module.lookup_album_years([('A "B"', "C")], fetch=lambda q, n: seen.append(q) or [])
        self.assertIn('artist:"A \\"B\\""', seen[0])


if __name__ == "__main__":
    unittest.main()
