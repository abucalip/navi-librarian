import unittest

from dataclasses import replace

from discovery.current_tastes import (
    _seed_queries,
    _under_represented_tags,
    ERA_BOOST, MIN_WINDOW_LISTENS, SPINE_BOOST, current_tastes_context, current_tastes_plan, decade_shares,
    dominant_area, era_match, expand_artist_weights, ranking_boost, recent_window,
)
from discovery.allocation_contract import AllocationCandidate, OwnershipStatus
from discovery.lens_lists import lens_seed_queries
from discovery.tag_queries import tag_from_query
from discovery.lenses import CURRENT_TASTES, DEEP_CUTS, DEFAULT_LENS_ORDER, run_lens

DAY = 24 * 60 * 60
NOW = 1_800_000_000

ROCK = ["rock", "alternative rock", "indie rock", "garage rock", "hard rock"]


def listen(artist, days_ago):
    return {
        "listened_at": NOW - days_ago * DAY,
        "track_metadata": {"additional_info": {"artist_mbid": artist}},
    }


def tags_for_history():
    # Six rock artists dominate the all-time history; the month plays them lightly.
    artist_tags = {f"rock{i}": list(ROCK) for i in range(6)}
    artist_tags["ethio"] = ["ethio jazz", "jazz"]
    artist_tags["soul"] = ["soul"]
    return artist_tags


class UnderRepresentedTagTests(unittest.TestCase):
    def test_a_tag_the_month_plays_more_than_usual_is_kept_whatever_its_all_time_rank(self):
        # Rock carries 91% of all-time weight but only 10% of the month, so it is dropped; raï
        # carries 9% all-time and 90% this month, so it is kept.
        long_term = {"rock": 100.0, "rai": 10.0}
        window_played = {"rock": 1.0, "rai": 9.0}
        tags = {"rock": ["rock"], "rai": ["raï"]}
        self.assertEqual(_under_represented_tags(window_played, long_term, tags), {"rock"})

    def test_a_linked_artist_the_listener_did_not_play_is_never_dropped_by_this_rule(self):
        tags = {"played": ["folk"], "linked": ["folk-rock"]}
        self.assertEqual(_under_represented_tags({"played": 1.0}, {"played": 1.0, "linked": 0.0}, tags), set())


class SeedTests(unittest.TestCase):
    def test_each_heavy_artist_contributes_its_rarest_kept_tag(self):
        # The common tag outweighs the rare one, but the rare tag is seeded because its artist is heavy.
        kept_weights = {"common": 100.0, "rare": 10.0}
        kept_tags = {"common": ["jazz", "rare-style"], "rare": ["ethio-jazz", "jazz"]}
        played = {"common": 100.0, "rare": 10.0}
        history_shares = {"jazz": 0.5, "rare-style": 0.2, "ethio-jazz": 0.005}
        tags = [tag_from_query(q) for q, _f, _s in _seed_queries(kept_weights, kept_tags, played, history_shares, 2)]
        self.assertIn("ethio-jazz", tags)
        self.assertEqual(len(tags), len(set(tags)))

    def test_fills_with_heaviest_tags_when_there_are_fewer_heavy_artists_than_seeds(self):
        kept_weights = {"a": 5.0, "b": 1.0}
        kept_tags = {"a": ["x", "y"], "b": ["y"]}
        queries = _seed_queries(kept_weights, kept_tags, {"a": 5.0, "b": 1.0}, {"x": 0.1, "y": 0.1}, 3)
        self.assertEqual(len(queries), 2)


class RecentWindowTests(unittest.TestCase):
    def test_thirty_days_is_used_when_it_holds_enough_listens(self):
        listens = [listen("a", d) for d in range(MIN_WINDOW_LISTENS)]
        window, days = recent_window(listens)
        self.assertEqual((len(window), days), (MIN_WINDOW_LISTENS, 30))

    def test_thin_month_widens_to_ninety_days(self):
        listens = [listen("a", 1), listen("b", 45)] + [listen("c", 60 + i) for i in range(MIN_WINDOW_LISTENS)]
        window, days = recent_window(listens)
        self.assertEqual(days, 90)
        self.assertEqual(len(window), len(listens))

    def test_longest_window_is_the_fallback_and_undated_listens_are_ignored(self):
        listens = [listen("a", 1), {"track_metadata": {}}, {"listened_at": "bad"}]
        window, days = recent_window(listens)
        self.assertEqual((len(window), days), (1, 365))

    def test_empty_history_gives_an_empty_window(self):
        self.assertEqual(recent_window([]), ([], 30))


def history():
    # Long-term rock, a thin recent window of Ethiopian jazz and some recent rock.
    old = [listen(f"rock{i}", 200 + i) for i in range(6) for _ in range(4)]
    recent_rock = [listen("rock0", 3), listen("rock1", 5)]
    ethio = [listen("ethio", d) for d in range(2, 2 + 25)]
    return old + recent_rock + ethio


class CurrentTastesPlanTests(unittest.TestCase):
    def history(self):
        return history()

    def test_long_term_dominant_tags_are_excluded_exactly(self):
        plan = current_tastes_plan(self.history(), tags_for_history())
        self.assertEqual(plan["window_days"], 30)
        for tag in ROCK:
            self.assertIn(tag, plan["excluded_tags"])
        self.assertNotIn("ethio jazz", plan["excluded_tags"])
        self.assertNotIn("jazz", plan["excluded_tags"])

    def test_seeds_come_from_the_remaining_window_tags(self):
        plan = current_tastes_plan(self.history(), tags_for_history())
        seed_tags = [seed["tag"] for seed in plan["seeds"]]
        self.assertIn("ethio jazz", seed_tags)
        self.assertIn("jazz", seed_tags)
        self.assertFalse(set(seed_tags) & set(ROCK))
        self.assertEqual(len(plan["queries"]), len(plan["seeds"]))

    def test_a_tag_is_not_excluded_because_a_root_word_is_dominant(self):
        # "jazz" is not dominant long term here, so "ethio jazz" stays even though its
        # root word could match a family the history covers elsewhere.
        plan = current_tastes_plan(self.history(), tags_for_history())
        self.assertNotIn("ethio jazz", plan["excluded_tags"])

    def test_similar_links_add_weight_at_a_discount_and_widen_the_seeds(self):
        plan = current_tastes_plan(
            self.history(), {**tags_for_history(), "soul2": ["neo soul"]},
            similar={"ethio": ["soul2"]},
        )
        self.assertIn("neo soul", [seed["tag"] for seed in plan["seeds"]])

    def test_linked_artists_contribute_their_own_tags_as_seeds(self):
        tags = {**tags_for_history(), "mulatu": ["funk", "afrobeat"]}
        plan = current_tastes_plan(self.history(), tags, similar={"ethio": ["mulatu"]})
        self.assertIn("afrobeat", [seed["tag"] for seed in plan["seeds"]])

    def test_limit_must_be_positive(self):
        with self.assertRaises(ValueError):
            current_tastes_plan(self.history(), tags_for_history(), limit=0)


class EnrichmentHelperTests(unittest.TestCase):
    def test_expand_adds_discounted_weight_and_ignores_self_links(self):
        weights = {"a": 4.0}
        expanded = expand_artist_weights(weights, {"a": ["b", "a"]}, 0.5)
        self.assertEqual(expanded["b"], 2.0)
        self.assertEqual(expanded["a"], 4.0)
        self.assertEqual(weights, {"a": 4.0})

    def test_dominant_area_needs_the_minimum_share(self):
        weights = {"a": 3.0, "b": 1.0, "c": 6.0}
        areas = {"a": "ET", "b": "ET", "c": "US"}
        # US holds 6 of 10 weight, so it is the dominant area.
        self.assertEqual(dominant_area(weights, areas), ("US", 0.6))
        self.assertEqual(dominant_area(weights, {"a": "ET", "b": "ET"}), ("ET", 0.4))
        self.assertIsNone(dominant_area(weights, {"c": "US"}, min_share=0.7))
        self.assertIsNone(dominant_area({}, areas))

    def test_decade_shares_and_era_match(self):
        shares = decade_shares({"a": 1.0, "b": 3.0}, {"a": 1974, "b": 1979})
        self.assertEqual(shares, {1970: 1.0})
        self.assertEqual(era_match(1972, shares), 1.0)
        self.assertEqual(era_match(1990, shares), 0.0)
        self.assertEqual(era_match(None, shares), 0.0)


class LensWiringTests(unittest.TestCase):
    def candidate(self, cid, audience):
        return AllocationCandidate(
            candidate_id=cid, artist_key=cid, album_key=cid, category="adjacent", score=1.0,
            genre_family=None, audience=audience, seed=f"s-{cid}", tag_strength=0.5,
            tags=("a", "b"), ownership=OwnershipStatus.CLEAR, artist_known=False,
        )

    def test_current_tastes_keeps_albums_without_a_listener_count(self):
        pool = [self.candidate("unknown", None), self.candidate("known", 2000)]
        result = run_lens(CURRENT_TASTES, pool, 2)
        self.assertEqual(set(result.selected_candidate_ids), {"unknown", "known"})

    def test_current_tastes_keeps_a_known_artist_but_still_drops_owned_albums(self):
        known = self.candidate("known", 2000)
        known = replace(known, artist_known=True)
        owned = replace(self.candidate("owned", 2000), ownership=OwnershipStatus.EXACT_OWNED)
        result = run_lens(CURRENT_TASTES, [known, owned], 2)
        self.assertEqual(result.selected_candidate_ids, ("known",))
        self.assertEqual({d.candidate_id: d.status for d in result.decisions}["owned"], "already_owned")

    def test_deep_cuts_still_rejects_known_artists(self):
        known = replace(self.candidate("known", 2000), artist_known=True)
        self.assertEqual(run_lens(DEEP_CUTS, [known], 1).selected_candidate_ids, ())

    def test_ranking_boost_moves_a_spine_release_ahead_of_an_equal_one(self):
        plain = self.candidate("plain", 2000)
        spine = replace(self.candidate("spine", 2000), ranking_boost=0.5)
        result = run_lens(CURRENT_TASTES, [plain, spine], 2)
        self.assertEqual(result.selected_candidate_ids[0], "spine")

    def test_context_names_the_spine_and_decades_from_the_window(self):
        context = current_tastes_context(
            history(), {"ethio": "Ethiopia"}, {"ethio": 1972})
        self.assertEqual(context["spine_area"], "Ethiopia")
        # Only the ethio artist has a year; the rock artists add weight but no decade.
        self.assertEqual(set(context["decades"]), {1970})
        self.assertGreater(context["decades"][1970], 0.5)
        self.assertLess(context["decades"][1970], 1.0)

    def test_ranking_boost_applies_spine_and_era(self):
        decades = {1970: 0.8}
        self.assertEqual(ranking_boost(artist_area="Ethiopia", release_year=1972, spine_area="Ethiopia", decades=decades),
                         SPINE_BOOST + ERA_BOOST * 0.8)
        self.assertEqual(ranking_boost(artist_area="Ethiopia", release_year=None, spine_area="Ethiopia", decades=decades),
                         SPINE_BOOST)
        self.assertEqual(ranking_boost(artist_area="US", release_year=1990, spine_area="Ethiopia", decades=decades), 0.0)

    def test_deep_cuts_still_rejects_albums_without_a_listener_count(self):
        pool = [self.candidate("unknown", None)]
        result = run_lens(DEEP_CUTS, pool, 1)
        self.assertEqual(result.selected_candidate_ids, ())

    def test_current_tastes_replaces_now_in_the_default_order(self):
        self.assertIn(CURRENT_TASTES, DEFAULT_LENS_ORDER)
        self.assertEqual({lens.name for lens in DEFAULT_LENS_ORDER},
                         {"deep_cuts", "current_tastes", "genre_spread"})

    def test_lens_seed_queries_include_current_tastes(self):
        seeds = lens_seed_queries(self.listens(), tags_for_history())
        self.assertIn("current_tastes", seeds)
        self.assertTrue(seeds["current_tastes"])

    def listens(self):
        return history()


if __name__ == "__main__":
    unittest.main()
