import unittest
from dataclasses import replace
from unittest import mock

from discovery.allocation_contract import AllocationCandidate, OwnershipStatus
import recommendation_feedback as feedback_module
from discovery.cooldown import prepare_ranking_inputs
from recommendation_feedback import apply_feedback_signal, feedback_penalty, save_boost

DAY = 24 * 60 * 60


class RecommendationFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.now = 2_000_000.0

    def album_row(self, *, artist_key="artist", album_key="album", status="not_for_me", age=0.0):
        return {
            "scope": "album", "artist_key": artist_key, "album_key": album_key,
            "artist": artist_key, "album": album_key, "status": status,
            "metadata": {}, "created_at": self.now - age, "updated_at": self.now - age,
        }

    def artist_row(self, *, artist_key="artist", age=0.0):
        return {
            "scope": "artist", "artist_key": artist_key, "album_key": "",
            "artist": artist_key, "album": "", "status": "not_for_me_artist",
            "metadata": {}, "created_at": self.now - age, "updated_at": self.now - age,
        }

    def save_row(self, *, artist_key="artist", album_key="album", age=0.0):
        return {
            "scope": "album", "artist_key": artist_key, "album_key": album_key,
            "artist": artist_key, "album": album_key, "status": "for_me",
            "metadata": {}, "created_at": self.now - age, "updated_at": self.now,
        }

    def candidate(self, candidate_id, artist, *, album="album", tags=(), ownership=OwnershipStatus.CLEAR, score=1.0):
        return AllocationCandidate(
            candidate_id=candidate_id, artist_key=f"name:{artist}", album_key=album,
            category="adjacent", score=score, tags=tuple(tags), ownership=ownership,
        ), {"primary_artist": artist, "album": album}

    def build(self, specs):
        candidates, sources = [], {}
        for spec in specs:
            candidate, source = self.candidate(*spec[:2], **(spec[2] if len(spec) > 2 else {}))
            candidates.append(candidate)
            sources[candidate.candidate_id] = source
        return candidates, sources

    def test_album_dismissal_penalises_only_that_album(self):
        candidates, sources = self.build([("a1", "artist"), ("a2", "artist")])
        candidates[0] = replace(candidates[0], album_key="album")
        candidates[1] = replace(candidates[1], album_key="sibling")
        adjusted = apply_feedback_signal(
            candidates, sources, [self.album_row(album_key="album")], now=self.now,
        )
        self.assertLess(adjusted[0].score, 1.0)
        self.assertEqual(adjusted[1].score, 1.0)

    def test_artist_dismissal_penalises_all_artist_albums_and_fresh_penalty_is_bounded(self):
        candidates, sources = self.build([("a1", "artist"), ("a2", "artist")])
        adjusted = apply_feedback_signal(candidates, sources, [self.artist_row()], now=self.now)
        for item in adjusted:
            self.assertAlmostEqual(item.score, 1.0 - feedback_module.ARTIST_DISMISS_PENALTY)
            self.assertGreater(item.score, 0.0)

    def test_dismiss_artist_album_and_artist_rows_do_not_double_count(self):
        candidates, sources = self.build([("a1", "artist")])
        candidates[0] = replace(candidates[0], album_key="album")
        rows = [self.album_row(album_key="album"), self.artist_row()]
        adjusted = apply_feedback_signal(candidates, sources, rows, now=self.now)
        # The larger single penalty applies; summing would give 0.8 and double-count.
        self.assertAlmostEqual(adjusted[0].score, 1.0 - feedback_module.ALBUM_DISMISS_PENALTY)

    def test_dismissal_expires_after_negative_window(self):
        candidates, sources = self.build([("a1", "artist")])
        candidates[0] = replace(candidates[0], album_key="album")
        expired = [self.album_row(album_key="album", age=61 * DAY)]
        adjusted = apply_feedback_signal(candidates, sources, expired, now=self.now)
        self.assertEqual(adjusted[0].score, 1.0)

    def test_dismissal_decays_with_fourteen_day_half_life(self):
        penalty_fresh = feedback_penalty("artist", "album", (), frozenset(), [self.album_row()], now=self.now)
        penalty_old = feedback_penalty(
            "artist", "album", (), frozenset(), [self.album_row(age=14 * DAY)], now=self.now,
        )
        self.assertAlmostEqual(penalty_old, penalty_fresh / 2)

    def test_shared_tags_with_dismissed_artist_penalise_other_artists_weaker(self):
        candidates, sources = self.build([
            ("dismissed", "artist", {"tags": ("rock",)}),
            ("other", "other", {"tags": ("rock",)}),
        ])
        adjusted = apply_feedback_signal(candidates, sources, [self.artist_row()], now=self.now)
        self.assertLess(adjusted[1].score, 1.0)
        self.assertGreater(adjusted[1].score, adjusted[0].score)

    def test_save_boost_is_positive_bounded_and_uses_created_at(self):
        boost = save_boost("artist", [self.save_row()], now=self.now)
        self.assertAlmostEqual(boost, feedback_module.SAVE_ARTIST_BOOST)
        decayed = save_boost("artist", [self.save_row(age=30 * DAY)], now=self.now)
        self.assertAlmostEqual(decayed, feedback_module.SAVE_ARTIST_BOOST / 2)
        self.assertEqual(save_boost("artist", [self.save_row(age=91 * DAY)], now=self.now), 0.0)

    def test_negative_and_positive_windows_are_independent(self):
        candidates, sources = self.build([("a1", "artist")])
        candidates[0] = replace(candidates[0], album_key="album")
        # A save older than the 60-day dismissal window still boosts; the dismissal has expired.
        rows = [self.album_row(album_key="album", age=61 * DAY), self.save_row(age=20 * DAY)]
        adjusted = apply_feedback_signal(candidates, sources, rows, now=self.now)
        self.assertGreater(adjusted[0].score, 1.0)

    def test_remove_for_me_leaves_no_positive_signal(self):
        self.assertEqual(save_boost("artist", [], now=self.now), 0.0)

    def test_non_clear_ownership_candidates_are_untouched(self):
        candidates, sources = self.build([
            ("owned", "artist", {"ownership": OwnershipStatus.EXACT_OWNED}),
        ])
        adjusted = apply_feedback_signal(candidates, sources, [self.artist_row()], now=self.now)
        self.assertEqual(adjusted[0].score, 1.0)

    def test_malformed_and_future_rows_are_ignored(self):
        candidates, sources = self.build([("a1", "artist")])
        malformed = [
            {"scope": "album", "status": "not_for_me", "artist_key": "artist", "album_key": "album"},
            {**self.album_row(album_key="album"), "updated_at": "not-a-time"},
            {**self.album_row(album_key="album"), "updated_at": self.now + DAY},
        ]
        candidates[0] = replace(candidates[0], album_key="album")
        adjusted = apply_feedback_signal(candidates, sources, malformed, now=self.now)
        self.assertEqual(adjusted[0].score, 1.0)

    def test_no_feedback_returns_candidates_unchanged(self):
        candidates, sources = self.build([("a1", "artist")])
        self.assertEqual(apply_feedback_signal(candidates, sources, [], now=self.now), candidates)

    def test_disabled_signal_adds_no_context_key(self):
        candidates, sources = self.build([("a1", "artist")])
        with mock.patch.object(feedback_module, "FEEDBACK_SIGNAL_ENABLED", False):
            adjusted, context = prepare_ranking_inputs(
                candidates, sources, ":memory:", None,
                now_fn=lambda: self.now, diversity_setting_fn=lambda: 0,
                feedback_fn=lambda: [self.artist_row()],
            )
        self.assertNotIn("feedback", context)
        self.assertEqual(adjusted[0].score, 1.0)

    def test_enabled_signal_freezes_feedback_into_context_and_replays(self):
        candidates, sources = self.build([("a1", "artist")])
        rows = [self.artist_row()]
        with mock.patch.object(feedback_module, "FEEDBACK_SIGNAL_ENABLED", True):
            live, context = prepare_ranking_inputs(
                candidates, sources, ":memory:", None,
                now_fn=lambda: self.now, diversity_setting_fn=lambda: 0,
                feedback_fn=lambda: rows,
            )
        self.assertEqual(context["feedback"], rows)
        replayed, _ = prepare_ranking_inputs(
            candidates, sources, ":memory:", context,
            now_fn=lambda: 0.0, diversity_setting_fn=lambda: 0,
        )
        self.assertEqual([c.score for c in live], [c.score for c in replayed])
        self.assertLess(replayed[0].score, 1.0)


if __name__ == "__main__":
    unittest.main()
