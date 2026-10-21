"""Controlled end-to-end fixture: feedback through ranking and the real allocator.

Synthetic pool only. A dominant artist has the highest raw scores, so without
feedback it fills most of the slate. The test runs the real
prepare_ranking_inputs and allocate_personal_recommendations path with injected
feedback rows, and checks that repeats drop while relevance and eligibility hold.
"""
import unittest

from discovery.allocation_contract import AllocationCandidate, AllocationRequest, OwnershipStatus
from discovery.personal_allocator import allocate_personal_recommendations
from recommendation_cooldown import prepare_ranking_inputs

NOW = 2_000_000.0
DAY = 24 * 60 * 60
COUNT = 6
TARGETS = {"adjacent": 3, "cross_genre": 2, "adventurous": 1}
# (artist, album, score): "Dominant" has the strongest scores.
POOL = [
    ("Dominant", "One", 1.30), ("Dominant", "Two", 1.28), ("Dominant", "Three", 1.26),
    ("Dominant", "Four", 1.24), ("Dominant", "Five", 1.22),
    ("Alpha", "Solo", 1.10), ("Bravo", "Solo", 1.08), ("Charlie", "Solo", 1.06),
    ("Delta", "Solo", 1.04), ("Echo", "Solo", 1.02), ("Foxtrot", "Solo", 1.00),
]
CATEGORIES = ("adjacent", "cross_genre", "adventurous", "adjacent", "cross_genre", "adjacent")


def _key(value):
    return "".join(c.casefold() for c in value if c.isalnum())


def _pool():
    candidates, sources = [], {}
    for index, (artist, album, score) in enumerate(POOL):
        candidate_id = str(index)
        category = CATEGORIES[index % len(CATEGORIES)]
        candidates.append(AllocationCandidate(
            candidate_id=candidate_id,
            artist_key=f"name:{_key(artist)}",
            album_key=_key(album),
            category=category,
            score=score,
            source_order=index,
            tags=("rock",),
            ownership=OwnershipStatus.CLEAR,
        ))
        sources[candidate_id] = {"primary_artist": artist, "album": album}
    return candidates, sources


def _allocate(candidates):
    return allocate_personal_recommendations(AllocationRequest(
        candidates=tuple(candidates),
        count=COUNT,
        category_targets=TARGETS,
        diversity_style_targets={},
        diversity_penalty=0.0,
        family_cap=1,
        max_checks=60,
    ))


def _ranked(feedback):
    candidates, sources = _pool()
    adjusted, context = prepare_ranking_inputs(
        candidates, sources, ":memory:", None,
        now_fn=lambda: NOW, diversity_setting_fn=lambda: 0,
        feedback_fn=lambda: feedback,
    )
    return adjusted, sources, context, _allocate(adjusted)


def _artist_of(sources, allocation):
    return [sources[candidate_id]["primary_artist"] for candidate_id in allocation.selected_candidate_ids]


class FeedbackEndToEndFixtureTests(unittest.TestCase):
    def test_artist_dismissal_reduces_repeats_and_keeps_relevance_and_eligibility(self):
        dismissed = [{
            "scope": "artist", "artist_key": "dominant", "album_key": "",
            "artist": "Dominant", "album": "", "status": "not_for_me_artist",
            "metadata": {}, "created_at": NOW, "updated_at": NOW,
        }]
        _, _, _, baseline = _ranked([])
        adjusted, sources, context, after = _ranked(dismissed)

        baseline_artists = _artist_of(sources, baseline)
        after_artists = _artist_of(sources, after)
        self.assertGreater(baseline_artists.count("Dominant"), after_artists.count("Dominant"))
        self.assertEqual(len(after.selected_candidate_ids), COUNT)
        self.assertEqual(len(adjusted), len(POOL))
        self.assertIn("feedback", context)
        # Relevance: the strongest non-dominant candidate still makes the slate.
        self.assertIn("Alpha", after_artists)
        # Ownership and eligibility: no candidate is excluded by feedback.
        self.assertEqual(
            {c.candidate_id for c in adjusted},
            {str(index) for index in range(len(POOL))},
        )

    def test_dismissed_artist_penalty_is_bounded_and_not_permanent(self):
        dismissed = [{
            "scope": "artist", "artist_key": "dominant", "album_key": "",
            "artist": "Dominant", "album": "", "status": "not_for_me_artist",
            "metadata": {}, "created_at": NOW, "updated_at": NOW,
        }]
        adjusted, _, _, _ = _ranked(dismissed)
        penalised = [c for c in adjusted if c.artist_key == "name:dominant"]
        self.assertTrue(all(c.score > 0.0 for c in penalised))
        # After the negative window, the same dismissal no longer changes scores.
        expired = [dict(dismissed[0], updated_at=NOW - 61 * DAY)]
        candidates, sources = _pool()
        later, _ = prepare_ranking_inputs(
            candidates, sources, ":memory:", None,
            now_fn=lambda: NOW, diversity_setting_fn=lambda: 0,
            feedback_fn=lambda: expired,
        )
        self.assertEqual([c.score for c in later], [c.score for c in candidates])

    def test_saved_album_lifts_its_artist_without_removing_others(self):
        saved = [{
            "scope": "album", "artist_key": "alpha", "album_key": "solo",
            "artist": "Alpha", "album": "Solo", "status": "for_me",
            "metadata": {}, "created_at": NOW, "updated_at": NOW,
        }]
        _, _, _, baseline = _ranked([])
        adjusted, sources, _, after = _ranked(saved)
        self.assertEqual(len(after.selected_candidate_ids), len(baseline.selected_candidate_ids))
        self.assertGreaterEqual(
            _artist_of(sources, after).count("Alpha"),
            _artist_of(sources, baseline).count("Alpha"),
        )
        alpha = next(c for c in adjusted if c.artist_key == "name:alpha")
        self.assertGreater(alpha.score, 1.10)


if __name__ == "__main__":
    unittest.main()
