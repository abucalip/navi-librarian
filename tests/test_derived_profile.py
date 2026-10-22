import unittest

from discovery import derived_profile as dp
from discovery.recommendations import (
    apply_familiarity_exploration_bonus,
    classify_recommendation_category,
    genre_families,
)
from settings.service import taste_profile_mode_value


def listens(tag_lists, weight=1.0):
    return [(tags, weight) for tags in tag_lists]


class FallbackFamilyTests(unittest.TestCase):
    def test_head_noun_groups_subgenres(self):
        for tag in ("Heavy Metal", "thrash metal", "metal"):
            self.assertEqual(dp.fallback_family(tag), "metal")
        self.assertEqual(dp.fallback_family("classical music"), "classical")
        self.assertEqual(dp.fallback_family("k-pop"), "k-pop")
        self.assertEqual(dp.fallback_family(""), "")

    def test_shipped_rules_win_over_fallback(self):
        self.assertEqual(dp.derived_genre_families(["hard bop"]), {"jazz"})
        self.assertEqual(dp.derived_genre_families(["black metal", "jazz"]), {"metal", "jazz"})


class DeriveProfileTests(unittest.TestCase):
    def test_metal_listener_gets_metal_core_and_no_african_bonus(self):
        history = listens([["heavy metal"], ["thrash metal"], ["death metal"]] * 4
                          + [["doom metal", "folk"]])
        pool = ["black metal"] * 2 + ["folk"] * 3 + ["jazz"]
        core, exploration, source = dp.derive_profile(history, pool)
        self.assertEqual(source, "derived")
        self.assertIn("metal", core)
        self.assertNotIn("african", core | exploration)
        self.assertEqual(exploration, {"folk", "jazz"} - core)

    def test_classical_listener_is_not_classed_adventurous(self):
        history = listens([["baroque", "classical"], ["romantic classical"]] * 5)
        core, exploration, _ = dp.derive_profile(history, ["opera"])
        category, families = classify_recommendation_category(
            {"artist": "x"}, ["classical", "chamber music"], core, exploration, derived=True)
        self.assertEqual(category, "adjacent")
        self.assertIn("classical", families)
        # The fixed vocabulary would call the same candidate adventurous.
        fixed, _ = classify_recommendation_category(
            {"artist": "x"}, ["classical", "chamber music"], core, exploration)
        self.assertEqual(fixed, "adventurous")

    def test_sparse_history_falls_back_to_defaults(self):
        from discovery import taste_families
        core, exploration, source = dp.derive_profile(listens([["metal"]]), ["folk"])
        self.assertEqual(source, "defaults_sparse_history")
        self.assertEqual(core, set(taste_families.CORE_FAMILIES))
        self.assertEqual(exploration, set(taste_families.EXPLORATION_FAMILIES))

    def test_core_covers_about_eighty_percent(self):
        weights = {"a": 50, "b": 30, "c": 15, "d": 5}
        self.assertEqual(dp.derive_core_families(weights), {"a", "b"})
        self.assertEqual(dp.derive_core_families({}), set())

    def test_mixed_profile_keeps_both_worlds(self):
        history = listens([["jazz"], ["hip hop"], ["metal"]] * 4)
        core, _, _ = dp.derive_profile(history, [])
        self.assertEqual(core, {"jazz", "hip-hop", "metal"})


class DerivedModeBehaviorTests(unittest.TestCase):
    def test_fixed_mode_is_unchanged(self):
        self.assertEqual(genre_families(["metal"]), set())
        self.assertEqual(genre_families(["metal"], derived=True), {"metal"})

    def test_derived_ignores_artist_names_and_adventurous_list(self):
        category, _ = classify_recommendation_category(
            {"primary_artist": "Tinariwen"}, [], {"metal"}, set(), derived=True)
        self.assertEqual(category, "unclassified")
        category, _ = classify_recommendation_category(
            {"artist": "x"}, ["drone metal", "noise"], {"metal"}, set(), derived=True)
        self.assertEqual(category, "adjacent")

    def test_exploration_bonus_uses_derived_set(self):
        base = {"score": 1.0}
        plain = apply_familiarity_exploration_bonus(dict(base), 1.5, ["folk"], {"folk"}, True)
        none = apply_familiarity_exploration_bonus(dict(base), 1.5, ["african"], {"folk"}, True)
        self.assertAlmostEqual(plain / none, 1.10)


class ModeSettingTests(unittest.TestCase):
    def test_defaults_to_derived_and_fixed_stays_selectable(self):
        self.assertEqual(taste_profile_mode_value(lambda: {}), "derived")
        self.assertEqual(taste_profile_mode_value(lambda: {"taste_profile_mode": "bogus"}), "derived")
        self.assertEqual(taste_profile_mode_value(lambda: {"taste_profile_mode": "fixed"}), "fixed")
        self.assertEqual(taste_profile_mode_value(lambda: {"taste_profile_mode": "derived"}), "derived")


if __name__ == "__main__":
    unittest.main()


class SparseHistoryFallbackTests(unittest.TestCase):
    """Sparse history must use the complete fixed behavior, not a hybrid."""

    def _gather(self, mode):
        from discovery.candidate_gathering import RecommendationProviders, gather_recommendation_candidates
        from tests.test_discovery_candidate_gathering import _Response, _TagSearchClient, _cf_item, _recording

        cache = {f"mb:recording:rec-{i}": _recording("Dominant", i) for i in range(3)}
        cache["mb:artist-genres:artist-Dominant"] = ["synthetic metal"]
        providers = RecommendationProviders(
            listenbrainz_recent=lambda days: [],
            listenbrainz_username=lambda: "fixture-user",
            music_key=lambda value: "".join(str(value).casefold().split()),
            metadata_cache_get=lambda key, **kwargs: cache.get(key),
            metadata_cache_set=lambda *args, **kwargs: None,
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {},
            items=lambda response: [],
            http_get=lambda url, params=None, **kwargs: _Response(
                {"payload": {"mbids": {0: [_cf_item(i) for i in range(3)]}.get(params["offset"], [])}}
            ),
            http_client=lambda *args, **kwargs: _TagSearchClient([200] * 20),
            sleep=lambda _seconds: None,
        )
        return gather_recommendation_candidates(providers, profile_mode=mode)

    def test_sparse_derived_run_reports_effective_fixed_mode(self):
        from discovery import taste_families
        result = self._gather("derived")
        self.assertEqual(result["profile_mode"], "fixed")
        self.assertEqual(result["profile_source"], "defaults_sparse_history")
        self.assertEqual(result["core_families"], set(taste_families.CORE_FAMILIES))

    def test_fixed_run_is_unchanged(self):
        result = self._gather("fixed")
        self.assertEqual((result["profile_mode"], result["profile_source"]), ("fixed", "fixed"))

    def test_sparse_classification_and_bonus_match_fixed_behavior(self):
        # With the effective mode "fixed", the server passes derived=False.
        derived = self._gather("derived")["profile_mode"] == "derived"
        self.assertFalse(derived)
        candidate = {"primary_artist": "Tinariwen"}
        category, families = classify_recommendation_category(
            candidate, [], {"jazz"}, {"african"}, derived=derived)
        self.assertEqual((category, families), ("adjacent", {"african"}))
        category, _ = classify_recommendation_category(
            {"artist": "x"}, ["noise"], {"jazz"}, {"african"}, derived=derived)
        self.assertEqual(category, "adventurous")
        boosted = apply_familiarity_exploration_bonus({"score": 1.0}, 1.5, ["afrobeat"], {"african"}, derived)
        plain = apply_familiarity_exploration_bonus({"score": 1.0}, 1.5, ["metal"], {"african"}, derived)
        self.assertAlmostEqual(boosted / plain, 1.10)


class AncestryGroupingTests(unittest.TestCase):
    def test_trailing_root_word_wins(self):
        for tag in ("doom metal", "alternative metal", "dream pop", "hard rock"):
            self.assertEqual(dp.fallback_family(tag), tag.split()[-1], tag)

    def test_ancestry_table_groups_names_without_a_root_word(self):
        self.assertEqual(dp.fallback_family("boom bap"), "hip-hop")
        self.assertEqual(dp.fallback_family("britpop"), "rock")
        self.assertEqual(dp.fallback_family("new wave"), "rock")

    def test_unknown_tag_still_uses_head_noun(self):
        self.assertEqual(dp.fallback_family("k-pop"), "k-pop")

    def test_table_loader_tolerates_missing_or_bad_files(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(dp._load_ancestry(Path(tmp) / "none.json"), {})
            bad = Path(tmp) / "bad.json"
            bad.write_text("[1]", encoding="utf-8")
            self.assertEqual(dp._load_ancestry(bad), {})

    def test_shipped_table_is_well_formed(self):
        families = set(dp._ANCESTRY.values())
        self.assertGreater(len(dp._ANCESTRY), 100)
        self.assertLessEqual(families, {
            "jazz", "hip-hop", "electronic", "metal", "punk", "rock", "pop",
            "classical", "folk", "blues", "country", "reggae", "rnb-soul", "funk"})


class CoreClusterTests(unittest.TestCase):
    def _rows(self):
        # pop and rock always co-occur; jazz is separate.
        return listens([["pop", "rock"]] * 6 + [["jazz"]] * 6)

    def test_cooccurring_core_families_share_a_cluster(self):
        core, _, source = dp.derive_profile(self._rows(), [])
        self.assertEqual(source, "derived")
        self.assertEqual(core, {"pop", "rock", "jazz"})
        self.assertEqual(core.cluster_of["pop"], core.cluster_of["rock"])
        self.assertNotEqual(core.cluster_of["pop"], core.cluster_of["jazz"])

    def test_cross_genre_needs_two_distinct_clusters(self):
        core, _, _ = dp.derive_profile(self._rows(), [])
        same, _ = classify_recommendation_category({"artist": "x"}, ["pop", "rock"], core, set(), derived=True)
        across, _ = classify_recommendation_category({"artist": "x"}, ["rock", "jazz"], core, set(), derived=True)
        self.assertEqual((same, across), ("adjacent", "cross_genre"))

    def test_plain_sets_keep_the_original_cross_genre_rule(self):
        category, _ = classify_recommendation_category(
            {"artist": "x"}, ["pop", "rock"], {"pop", "rock"}, set(), derived=True)
        self.assertEqual(category, "cross_genre")

    def test_separate_families_stay_separate(self):
        rows = listens([["jazz"]] * 6 + [["metal"]] * 6)
        core, _, _ = dp.derive_profile(rows, [])
        self.assertEqual(len(set(core.cluster_of.values())), 2)
