"""Synthetic tests: the genre-stage circuit breaker is off by default and stops only when enabled."""
import unittest
from unittest import mock

import discovery_candidate_gathering as gathering
from test_discovery_candidate_genre_prefetch import CANDIDATE_GENRES, PROFILE_MBID, _run


class GenreCircuitBreakerTests(unittest.TestCase):
    def test_flag_is_off_by_default(self):
        self.assertFalse(gathering.GENRE_CIRCUIT_BREAKER_ENABLED)

    def test_flag_off_keeps_asking_about_every_artist_after_failures(self):
        failing = tuple(CANDIDATE_GENRES)
        _result, log = _run(warm=False, failing_artists=failing, prefetch_limit=0)

        self.assertEqual(set(log["artist"]), {PROFILE_MBID, *CANDIDATE_GENRES})

    def test_flag_on_stops_the_genre_stage_after_consecutive_exhaustions(self):
        failing = (PROFILE_MBID, *CANDIDATE_GENRES)
        with mock.patch.object(gathering, "GENRE_CIRCUIT_BREAKER_ENABLED", True), \
                mock.patch.object(gathering, "GENRE_CIRCUIT_BREAKER_THRESHOLD", 2):
            result, log = _run(warm=False, failing_artists=failing, prefetch_limit=0)

        self.assertNotIsInstance(result, str)
        # The profile prefetch makes three attempts for the profile artist. The genre
        # stage then makes three attempts each for the two top candidates, and stops
        # before the third candidate is requested at all.
        self.assertEqual(len(log["artist"]), 3 + 3 + 3)
        self.assertNotIn("c-3", log["artist"])

    def test_flag_on_without_failures_changes_nothing(self):
        with mock.patch.object(gathering, "GENRE_CIRCUIT_BREAKER_ENABLED", True):
            _result, log = _run(warm=False, prefetch_limit=0)

        self.assertEqual(set(log["artist"]), {PROFILE_MBID, *CANDIDATE_GENRES})
