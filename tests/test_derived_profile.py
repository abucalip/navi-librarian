import unittest

from discovery import derived_profile as dp
from discovery.recommendations import (
    apply_familiarity_exploration_bonus,
    classify_recommendation_category,
    genre_families,
)


def listens(tag_lists, weight=1.0):
    return [(tags, weight) for tags in tag_lists]


class FallbackFamilyTests(unittest.TestCase):
    def test_head_noun_groups_subgenres(self):
        for tag in ("Heavy Metal", "thrash metal", "metal"):
            self.assertEqual(dp.fallback_family(tag), "metal")
        self.assertEqual(dp.fallback_family("classical music"), "classical")
        self.assertEqual(dp.fallback_family("k-pop"), "pop")
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
            {"artist": "x"}, ["classical", "chamber music"], core, exploration)
        self.assertEqual(category, "adjacent")
        self.assertIn("classical", families)

    def test_sparse_history_uses_the_candidate_pool(self):
        core, exploration, source = dp.derive_profile(listens([["metal"]]), ["folk", "folk", "metal"])
        self.assertEqual(source, "candidate_pool_sparse_history")
        self.assertEqual(core, {"folk", "metal"})
        self.assertEqual(exploration, set())
        self.assertEqual(core.cluster_of, {"folk": "folk", "metal": "metal"})

    def test_no_history_and_no_pool_gives_an_empty_profile(self):
        core, exploration, source = dp.derive_profile([], [])
        self.assertEqual((set(core), exploration, source), (set(), set(), "no_profile"))

    def test_core_covers_about_eighty_percent(self):
        weights = {"a": 50, "b": 30, "c": 15, "d": 5}
        self.assertEqual(dp.derive_core_families(weights), {"a", "b"})
        self.assertEqual(dp.derive_core_families({}), set())

    def test_mixed_profile_keeps_both_worlds(self):
        history = listens([["jazz"], ["hip hop"], ["metal"]] * 4)
        core, _, _ = dp.derive_profile(history, [])
        self.assertEqual(core, {"jazz", "hip-hop", "metal"})


class ClassificationBehaviorTests(unittest.TestCase):
    def test_every_tag_gets_a_family(self):
        self.assertEqual(genre_families(["metal"]), {"metal"})
        self.assertEqual(genre_families(["jazz"]), {"jazz"})

    def test_artist_names_and_the_adventurous_list_do_not_matter(self):
        category, _ = classify_recommendation_category(
            {"primary_artist": "Tinariwen"}, [], {"metal"}, set())
        self.assertEqual(category, "unclassified")
        category, _ = classify_recommendation_category(
            {"artist": "x"}, ["drone metal", "noise"], {"metal"}, set())
        self.assertEqual(category, "adjacent")
        category, _ = classify_recommendation_category(
            {"artist": "x"}, ["free jazz"], {"metal"}, set())
        self.assertEqual(category, "adventurous")

    def test_exploration_bonus_uses_the_derived_set(self):
        base = {"score": 1.0}
        plain = apply_familiarity_exploration_bonus(dict(base), 1.5, ["folk"], {"folk"})
        none = apply_familiarity_exploration_bonus(dict(base), 1.5, ["african"], {"folk"})
        self.assertAlmostEqual(plain / none, 1.10)


class GatheringProfileTests(unittest.TestCase):
    def _gather(self):
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
        return gather_recommendation_candidates(providers)

    def test_empty_history_derives_the_profile_from_the_candidate_pool(self):
        result = self._gather()
        self.assertEqual(result["profile_source"], "candidate_pool_sparse_history")
        self.assertEqual(result["core_families"], {"metal"})
        self.assertEqual(result["exploration_families"], set())
        self.assertNotIn("profile_mode", result)


class AncestryGroupingTests(unittest.TestCase):
    def test_trailing_root_word_wins(self):
        for tag in ("doom metal", "alternative metal", "dream pop", "hard rock"):
            self.assertEqual(dp.fallback_family(tag), tag.split()[-1], tag)

    def test_ancestry_table_groups_names_without_a_root_word(self):
        self.assertEqual(dp.fallback_family("boom bap"), "hip-hop")
        self.assertEqual(dp.fallback_family("britpop"), "rock")
        self.assertEqual(dp.fallback_family("new wave"), "rock")

    def test_unknown_tag_still_uses_head_noun(self):
        self.assertEqual(dp.fallback_family("gypsy zouk"), "zouk")

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
        self.assertGreater(len(dp._ANCESTRY), 300)
        self.assertLessEqual(families, {
            "jazz", "hip-hop", "electronic", "metal", "punk", "rock", "pop",
            "classical", "folk", "blues", "country", "reggae", "rnb-soul", "funk",
            "gospel", "latin", "african", "brazilian"})


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
        same, _ = classify_recommendation_category({"artist": "x"}, ["pop", "rock"], core, set())
        across, _ = classify_recommendation_category({"artist": "x"}, ["rock", "jazz"], core, set())
        self.assertEqual((same, across), ("adjacent", "cross_genre"))

    def test_plain_sets_keep_the_original_cross_genre_rule(self):
        category, _ = classify_recommendation_category(
            {"artist": "x"}, ["pop", "rock"], {"pop", "rock"}, set())
        self.assertEqual(category, "cross_genre")

    def test_separate_families_stay_separate(self):
        rows = listens([["jazz"]] * 6 + [["metal"]] * 6)
        core, _, _ = dp.derive_profile(rows, [])
        self.assertEqual(len(set(core.cluster_of.values())), 2)


class AncestryTableCorrectionTests(unittest.TestCase):
    def test_curated_corrections_apply(self):
        for tag, family in {"thrash metal": "metal", "punk rock": "punk", "stoner rock": "rock",
                            "hip hop soul": "rnb-soul", "alternative dance": "electronic",
                            "dub": "reggae", "baroque": "classical",
                            "metalcore": "metal", "djent": "metal", "post-metal": "metal",
                            "amapiano": "african", "choro": "brazilian", "ska": "reggae",
                            "salsa": "latin", "gospel": "gospel", "lovers rock": "reggae",
                            "rhythm and blues": "rnb-soul", "chillwave": "electronic",
                            "nu jazz": "jazz", "g-funk": "funk"}.items():
            self.assertEqual(dp._ANCESTRY[tag], family, tag)

    def test_table_agrees_with_trailing_root_word_unless_overridden(self):
        import importlib.util, sys, types
        sys.modules.setdefault("httpx", types.ModuleType("httpx"))
        spec = importlib.util.spec_from_file_location("b", "scripts/build_genre_ancestry.py")
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        for tag, family in dp._ANCESTRY.items():
            last = tag.split()[-1]
            if last in dp.ROOT_WORDS and tag not in build.OVERRIDES:
                self.assertEqual(family, last, tag)
