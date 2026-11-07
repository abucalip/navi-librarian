"""Insight lookups for smart playlist results (Server V2 Phase 6 slice 16): bands and lens members."""
import tempfile
import unittest
from pathlib import Path

from intelligence.api import smart_playlists as api
from intelligence.insights import persistence as gems
from intelligence.insights.forgotten_gems import Gem, GemsResult, PlayRecord
from intelligence.store import open_store
from intelligence.taste.obscurity import BUCKETS, song_bands

NOW = 1_700_000_000.0
RID = "00000001-0000-4000-8000-00000005ba17"


def gem(key):
    return Gem(PlayRecord(key=key, kind=key.split(":")[0], title="t", play_count=9), 0.5, 0.5, 1.0, 400)


class Bands(unittest.TestCase):
    def test_thresholds_and_missing_figures(self):
        pop = {"a": 5_000_000, "b": 200_000, "c": 20_000, "d": 12, "e": None}
        got = song_bands({"1": "a", "2": "b", "3": "c", "4": "d", "5": "e", "6": None, "7": "zz"}, pop)
        self.assertEqual(got, {"1": "mainstream", "2": "known", "3": "niche", "4": "obscure"})
        self.assertEqual(set(got.values()) | {"x"}, set(BUCKETS) | {"x"})

    def test_config_lists_bands_and_lenses(self):
        cfg = api.build_config()
        self.assertEqual(cfg["obscurity_bands"], list(BUCKETS))
        self.assertEqual(cfg["lens_keys"], ["forgotten_gems"])


class Lookups(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)
        self.songs = [{"id": "s1", "album_id": "al1"}, {"id": "s2", "album_id": "al2"}, {"id": "s3"}]

    def test_no_cards_leaves_the_lens_out(self):
        self.assertEqual(api.build_insights(self.db, self.songs), {})

    def test_track_and_album_gems_become_members(self):
        gems.save_gems(self.db, GemsResult(gems=(gem("track:s3"), gem("album:al1"))), NOW)
        got = api.build_insights(self.db, self.songs)
        self.assertEqual(got["lens_members"], {"forgotten_gems": {"s1", "s3"}})
        self.assertNotIn("obscurity_band", got)

    def test_dismissed_gem_is_not_a_member(self):
        gems.save_gems(self.db, GemsResult(gems=(gem("track:s3"), gem("track:s2"))), NOW)
        gems.dismiss_gem(self.db, "track:s2", NOW)
        self.assertEqual(api.build_insights(self.db, self.songs)["lens_members"]["forgotten_gems"], {"s3"})

    def test_result_uses_both_lookups(self):
        api.build_put_body(self.db, RID, {"name": "x", "match": "all", "order": "title", "rules": [
            {"field": "in_lens", "op": "equals", "value": "forgotten_gems"},
            {"field": "obscurity_band", "op": "equals", "value": "obscure"}]}, NOW)
        gems.save_gems(self.db, GemsResult(gems=(gem("track:s3"), gem("track:s1"))), NOW)
        ins = api.build_insights(self.db, self.songs, {"s1": "a", "s3": "b"}, {"a": 10, "b": 5_000_000})
        body = api.build_result_body(self.db, RID, self.songs, NOW, insights=ins)
        self.assertEqual((body["song_ids"], body["unfinished"], body["missing_data"]), (["s1"], [], []))
        body = api.build_result_body(self.db, RID, self.songs, NOW, insights=api.build_insights(self.db, self.songs))
        self.assertEqual((body["unfinished"], body["missing_data"]), ([1], ["obscurity_band"]))

    def test_subsonic_rows_keep_album_id(self):
        rows = api.songs_from_subsonic([{"id": "a", "albumId": "al"}, {"id": "b"}])
        self.assertEqual([r.get("album_id") for r in rows], ["al", None])


if __name__ == "__main__":
    unittest.main()
