"""Synthetic tests: the genre circuit breaker also gates the profile genre prefetch.

With the flag off, the prefetch asks about every profile artist even after
failures. With the flag on, the prefetch stops after consecutive exhausted
lookups and sends nothing further for the remaining profile artists.
"""
import time
import unittest
from unittest import mock

import discovery_candidate_gathering as gathering
import test_discovery_candidate_genre_prefetch as prefetch_fixture
from test_discovery_candidate_genre_prefetch import CANDIDATE_GENRES, _run

PROFILE_ARTISTS = ["p-1", "p-2", "p-3", "p-4", "p-5"]


def _profile_listens():
    # Descending listen counts keep the top-15 profile order deterministic.
    now = int(time.time())
    listens = []
    step = 0
    for position, artist_id in enumerate(PROFILE_ARTISTS):
        for _ in range(len(PROFILE_ARTISTS) - position):
            listens.append({
                "listened_at": now - step * 3600,
                "track_metadata": {
                    "artist_name": f"Profile {artist_id}",
                    "additional_info": {"artist_mbid": artist_id},
                },
            })
            step += 1
    return listens


class ProfileGenreBreakerTests(unittest.TestCase):
    def _run_with_profile(self, *, failing_artists, enabled, threshold=2):
        patches = [
            mock.patch.object(prefetch_fixture, "_listens", _profile_listens),
            # The fixture client answers only the profile artist and candidates, so
            # the other profile artists need genre entries of their own.
            mock.patch.dict(CANDIDATE_GENRES, {artist_id: ["jazz"] for artist_id in PROFILE_ARTISTS}),
        ]
        patches.append(mock.patch.object(gathering, "GENRE_CIRCUIT_BREAKER_ENABLED", bool(enabled)))
        patches.append(mock.patch.object(gathering, "GENRE_CIRCUIT_BREAKER_THRESHOLD", threshold))
        for patch in patches:
            patch.start()
        try:
            return _run(warm=False, failing_artists=tuple(failing_artists), prefetch_limit=0)
        finally:
            for patch in reversed(patches):
                patch.stop()

    def test_flag_off_still_asks_about_every_profile_artist_after_failures(self):
        _result, log = self._run_with_profile(failing_artists=PROFILE_ARTISTS, enabled=False)

        for artist_id in PROFILE_ARTISTS:
            self.assertIn(artist_id, log["artist"])

    def test_flag_on_sends_no_profile_lookups_after_the_breaker_opens(self):
        result, log = self._run_with_profile(
            failing_artists=PROFILE_ARTISTS, enabled=True, threshold=2,
        )

        self.assertNotIsInstance(result, str)
        # p-1 and p-2 each exhaust three attempts, which opens a threshold of 2.
        # p-3 to p-5 are never requested by the prefetch or the genre stage, which
        # breaks on its own streak right after p-2.
        self.assertNotIn("p-3", log["artist"])
        self.assertNotIn("p-4", log["artist"])
        self.assertNotIn("p-5", log["artist"])

    def test_flag_on_records_the_skipped_profile_lookups_as_an_aggregate(self):
        result, _log = self._run_with_profile(
            failing_artists=PROFILE_ARTISTS, enabled=True, threshold=2,
        )

        self.assertNotIsInstance(result, str)
        skipped = [
            entry for entry in result["failures"]
            if entry.get("source") == "profile_genre_circuit_breaker"
        ]
        self.assertEqual(skipped, [{
            "source": "profile_genre_circuit_breaker",
            "skipped_artists": len(PROFILE_ARTISTS) - 2,
        }])

    def test_flag_on_without_failures_sends_every_profile_lookup_once(self):
        _result, log = self._run_with_profile(failing_artists=(), enabled=True)

        for artist_id in PROFILE_ARTISTS:
            self.assertEqual(log["artist"].count(artist_id), 1)


if __name__ == "__main__":
    unittest.main()
