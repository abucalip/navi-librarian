"""Star Operation S3b: Navidrome stars as a taste seed (weights, cache, setting, gatherer)."""
import json
import time
import unittest

import recommendation_run_metrics as run_metrics
from discovery.star_seeds import (
    STAR_EXPIRY_SECONDS, STAR_HALF_LIFE_SECONDS, STAR_SEED_WEIGHT, STARRED_CACHE_KEY,
    UNDATED_STAR_FACTOR, cached_starred, starred_seed_weights,
)
from integrations.navidrome import items
from recommendation_feedback import SAVE_SEED_WEIGHT
from settings.service import (
    get_star_seed_settings, set_star_seed_settings, star_seed_enabled_value,
)
from tests.test_discovery_save_tag_seed import _music_key, _run

NOW = 1_800_000_000.0


def _starred(artists=(), albums=()):
    return {"artists": list(artists), "albums": list(albums)}


class WeightTests(unittest.TestCase):
    def test_fresh_star_has_full_weight_and_is_below_a_save(self):
        weights = starred_seed_weights(
            _starred([{"id": "1", "name": "Band", "starred_at": NOW}]), _music_key, now=NOW)
        self.assertEqual(weights, {"band": STAR_SEED_WEIGHT})
        self.assertLess(STAR_SEED_WEIGHT, SAVE_SEED_WEIGHT)

    def test_weight_halves_at_the_half_life_and_ends_at_expiry(self):
        def weight(age):
            return starred_seed_weights(
                _starred([{"name": "Band", "starred_at": NOW - age}]), _music_key, now=NOW,
            ).get("band", 0.0)
        self.assertAlmostEqual(weight(STAR_HALF_LIFE_SECONDS), STAR_SEED_WEIGHT / 2)
        self.assertGreater(weight(STAR_EXPIRY_SECONDS), 0.0)
        self.assertEqual(weight(STAR_EXPIRY_SECONDS + 1), 0.0)

    def test_undated_star_counts_at_a_flat_fraction(self):
        weights = starred_seed_weights(_starred([{"name": "Band", "starred_at": None}]), _music_key, now=NOW)
        self.assertEqual(weights["band"], STAR_SEED_WEIGHT * UNDATED_STAR_FACTOR)

    def test_future_or_unreadable_dates_contribute_nothing(self):
        weights = starred_seed_weights(_starred([
            {"name": "Future", "starred_at": NOW + 100},
            {"name": "Bad", "starred_at": "soon"},
            {"name": "Nan", "starred_at": float("nan")},
        ]), _music_key, now=NOW)
        self.assertEqual(weights, {})

    def test_album_star_seeds_its_artist_and_the_larger_weight_wins(self):
        weights = starred_seed_weights(_starred(
            [{"name": "Band", "starred_at": NOW - STAR_HALF_LIFE_SECONDS}],
            [{"name": "Record", "artist": "Band", "starred_at": NOW},
             {"name": "Other", "artist": "  ", "starred_at": NOW},
             {"name": "NoArtist", "starred_at": NOW}],
        ), _music_key, now=NOW)
        self.assertEqual(weights, {"band": STAR_SEED_WEIGHT})

    def test_empty_starred_gives_no_seeds(self):
        self.assertEqual(starred_seed_weights(_starred(), _music_key, now=NOW), {})
        self.assertEqual(starred_seed_weights({}, _music_key, now=NOW), {})


class CacheTests(unittest.TestCase):
    def test_miss_reads_once_then_hits_the_cache(self):
        store, calls = {}, []

        def api_call(method, **kw):
            calls.append(method)
            return {"starred2": {"artist": [{"id": "1", "name": "Band"}]}}

        def get(key, ttl_seconds):
            return store.get(key)

        for _ in range(2):
            result = cached_starred(api_call, items, get, store.__setitem__)
        self.assertEqual(calls, ["getStarred2"])
        self.assertEqual(result["artists"][0]["name"], "Band")
        self.assertIn(STARRED_CACHE_KEY, store)

    def test_malformed_cache_entry_is_refetched(self):
        calls = []
        result = cached_starred(
            lambda m, **kw: calls.append(m) or {"starred2": {}}, items,
            lambda key, ttl_seconds: {"artists": "x"}, lambda k, v: None)
        self.assertEqual(calls, ["getStarred2"])
        self.assertEqual(result, {"artists": [], "albums": []})


class SettingTests(unittest.TestCase):
    def test_default_is_off_and_bad_values_mean_off(self):
        self.assertFalse(star_seed_enabled_value(lambda: {}))
        self.assertFalse(star_seed_enabled_value(lambda: {"star_seed_enabled": "yes"}))
        self.assertTrue(star_seed_enabled_value(lambda: {"star_seed_enabled": True}))
        self.assertEqual(json.loads(get_star_seed_settings(lambda: {})), {"star_seed_enabled": False})

    def test_set_persists_booleans_and_refuses_others_without_writing(self):
        written = []
        ok = json.loads(set_star_seed_settings(written.append, True))
        self.assertTrue(ok["ok"])
        self.assertEqual(written, [{"star_seed_enabled": True}])
        bad = json.loads(set_star_seed_settings(written.append, "true"))
        self.assertFalse(bad["ok"])
        self.assertEqual(len(written), 1)


class GathererTests(unittest.TestCase):
    @staticmethod
    def _api(starred_name="Never Heard", calls=None):
        def api_call(method, **kw):
            if calls is not None:
                calls.append(method)
            if method == "getStarred2":
                return {"starred2": {"artist": [{"id": "s1", "name": starred_name,
                                                 "starred": "2026-11-01T00:00:00Z"}]}}
            return {"albumList2": {"album": []}}
        return api_call

    def _counted(self, **kw):
        run_metrics.snapshot_and_reset()
        log = _run([], **kw)
        return log, run_metrics.snapshot_and_reset()["counts"]

    def test_setting_off_or_absent_reads_no_stars_and_changes_nothing(self):
        base = _run([])
        for reader in (None, lambda: {}, lambda: {"star_seed_enabled": False}):
            calls = []
            run_metrics.snapshot_and_reset()
            self.assertEqual(_run([], settings_read=reader, api_call=self._api(calls=calls)), base)
            self.assertNotIn("getStarred2", calls)
            self.assertNotIn("star_seed.starred_artists", run_metrics.snapshot_and_reset()["counts"])

    def test_enabled_star_with_cached_mbid_genres_seeds_tag_selection(self):
        # "Cand 2" has an MBID and cached genres this run, so a star on it is a usable seed.
        calls = []
        _log, counts = self._counted(
            settings_read=lambda: {"star_seed_enabled": True},
            api_call=self._api("Cand 2", calls))
        self.assertEqual(calls.count("getStarred2"), 1)
        self.assertEqual(counts["star_seed.starred_artists"], 1)
        self.assertEqual(counts["save_seed.saved_artists"], 0)
        self.assertEqual(counts["save_seed.from_cached_genres"], 1)

    def test_star_without_known_genres_is_skipped_and_adds_no_query(self):
        base = _run([])
        log, counts = self._counted(
            settings_read=lambda: {"star_seed_enabled": True}, api_call=self._api("Never Heard"))
        self.assertEqual(counts["save_seed.skipped_no_genres"], 1)
        self.assertLessEqual(len(log["queries"]), len(base["queries"]))

    def test_failing_star_read_leaves_the_run_unchanged(self):
        def api_call(method, **kw):
            if method == "getStarred2":
                raise RuntimeError("navidrome down")
            return {"albumList2": {"album": []}}

        run_metrics.snapshot_and_reset()
        base = _run([])
        base_counts = run_metrics.snapshot_and_reset()["counts"]
        self.assertEqual(_run([], settings_read=lambda: {"star_seed_enabled": True}, api_call=api_call), base)
        self.assertEqual(run_metrics.snapshot_and_reset()["counts"], base_counts)

    def test_failing_settings_read_leaves_the_run_unchanged(self):
        def boom():
            raise RuntimeError("settings down")

        base = _run([])
        self.assertEqual(_run([], settings_read=boom), base)

    def test_stars_do_not_disturb_save_seeding_when_both_present(self):
        row = {"metadata": {}, "scope": "album", "artist_key": "cand2", "album_key": "x",
               "status": "for_me", "created_at": time.time() - 86400, "updated_at": time.time()}
        run_metrics.snapshot_and_reset()
        _run([row], settings_read=lambda: {"star_seed_enabled": True}, api_call=self._api("Cand 2"))
        counts = run_metrics.snapshot_and_reset()["counts"]
        self.assertEqual(counts["save_seed.saved_artists"], 1)
        self.assertEqual(counts["star_seed.starred_artists"], 1)


if __name__ == "__main__":
    unittest.main()


class StarSeedRouteTests(unittest.TestCase):
    def setUp(self):
        from app.api import settings as routes
        self.routes = routes
        self.store = {}

        class Librarian:
            _discovery_settings_read = staticmethod(lambda: dict(self.store))
            _discovery_settings_write = staticmethod(lambda values: self.store.update(values))
        self.librarian = Librarian()

    def test_get_defaults_off_then_put_round_trips(self):
        self.assertEqual(self.routes.get_star_seed_settings(self.librarian), {"star_seed_enabled": False})
        result = self.routes.set_star_seed_settings({"star_seed_enabled": True}, self.librarian)
        self.assertTrue(result["ok"])
        self.assertEqual(self.routes.get_star_seed_settings(self.librarian), {"star_seed_enabled": True})

    def test_put_rejects_non_boolean_without_writing(self):
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as caught:
            self.routes.set_star_seed_settings({"star_seed_enabled": "on"}, self.librarian)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(self.store, {})
