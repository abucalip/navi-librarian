import copy
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import server_v2_phase3_checks as checks  # noqa: E402
import server_v2_phase3_live_lenses as live  # noqa: E402
from intelligence.insights import (  # noqa: E402
    AnniversaryConfig, BlindSpotsConfig, CanonConfig, DatedAlbum, SeriesConfig, WorldAlbum, anniversary_card,
    blind_spot_card, canon_card, find_anniversaries, find_blind_spots, find_hidden_canon, find_series_progress,
    series_card,
)
from intelligence.insights import set_builders  # noqa: E402

ARTIST = "11111111-1111-1111-1111-111111111111"
GROUPS = [f"aaaaaaaa-0000-0000-0000-00000000000{i}" for i in range(1, 9)]
OWNED = {GROUPS[0], GROUPS[1], GROUPS[2]}
TODAY = date(2026, 11, 6)
GENRES = ["rock", "pop"]


def studio_doc():
    return {"release-groups": [
        {"id": g, "title": f"Album {i}", "primary-type": "Album", "secondary-types": [], "first-release-date": f"{1990 + i}-11-10"}
        for i, g in enumerate(GROUPS[:6])
    ]}


def series_doc():
    return {"id": "5e5e5e5e-0000-0000-0000-000000000001", "name": "Test series", "relations": [
        {"type": "part of", "target-type": "release_group", "attribute-values": {"number": str(i + 1)},
         "release_group": {"id": g, "title": f"Chapter {i}"}} for i, g in enumerate(GROUPS[:6])
    ]}


class CheckFixtures(unittest.TestCase):
    def setUp(self):
        self.studio = set_builders.studio_discography_set(ARTIST, "Artist", studio_doc())
        self.series = set_builders.series_set(series_doc())
        self.assertIsNotNone(self.studio)
        self.assertIsNotNone(self.series)
        spots = find_blind_spots([self.studio], OWNED, BlindSpotsConfig())
        self.spot_cards = [blind_spot_card(s) for s in spots.spots]
        prog = find_series_progress([self.series], OWNED, SeriesConfig())
        self.series_cards = [series_card(p) for p in prog.progress]
        self.world = [WorldAlbum(GROUPS[6], "Unowned", "Artist", genres=("rock",), listens=5000),
                      WorldAlbum(GROUPS[7], "Other", "Artist", genres=("rock",), listens=4000)]
        canon = find_hidden_canon(self.world, OWNED, GENRES, CanonConfig())
        self.canon_cards = [canon_card(p) for p in canon.picks]
        self.dated = [DatedAlbum(g, f"Album {i}", "Artist", f"{1990 + i}-11-10") for i, g in enumerate(GROUPS[:3])]
        ann = find_anniversaries(self.dated, [], TODAY, AnniversaryConfig(window_days=30))
        self.ann_cards = [anniversary_card(a) for a in ann.items]
        self.assertTrue(self.spot_cards and self.series_cards and self.canon_cards and self.ann_cards)


class RealCardsPassTests(CheckFixtures):
    def test_every_lens_passes_on_correct_cards(self):
        self.assertEqual(checks.common_failures(self.spot_cards + self.series_cards + self.canon_cards + self.ann_cards), [])
        self.assertEqual(checks.blind_spot_failures(self.spot_cards, [self.studio], OWNED), [])
        self.assertEqual(checks.series_failures(self.series_cards, [self.series], OWNED), [])
        self.assertEqual(checks.canon_failures(self.canon_cards, OWNED, self.world, GENRES), [])
        dates = {d.group_mbid: d.release_date for d in self.dated}
        self.assertEqual(checks.anniversary_failures(self.ann_cards, OWNED, TODAY, 30, dates), [])


class BrokenCardsFailTests(CheckFixtures):
    def test_blind_spot_listing_an_owned_group_fails(self):
        bad = copy.deepcopy(self.spot_cards)
        bad[0]["missing"].append({"group_mbid": GROUPS[0], "title": "x", "year": 1990})
        self.assertTrue(any("owned group" in f for f in checks.blind_spot_failures(bad, [self.studio], OWNED)))

    def test_blind_spot_wrong_count_fails(self):
        bad = copy.deepcopy(self.spot_cards)
        bad[0]["body"] = "You own 5 of 6 in this set; 1 not in your library."
        self.assertTrue(any("recomputed" in f for f in checks.blind_spot_failures(bad, [self.studio], OWNED)))

    def test_blind_spot_without_a_backing_set_fails(self):
        self.assertTrue(any("no comparison set" in f for f in checks.blind_spot_failures(self.spot_cards, [], OWNED)))

    def test_series_wrong_total_and_owned_member_fail(self):
        bad = copy.deepcopy(self.series_cards)
        bad[0]["total"] = 7
        bad[0]["missing_runs"][0]["items"][0]["group_mbid"] = GROUPS[1]
        failures = checks.series_failures(bad, [self.series], OWNED)
        self.assertTrue(any("recomputed" in f for f in failures))
        self.assertTrue(any("owned group" in f for f in failures))

    def test_barely_started_series_must_be_left_out(self):
        few = {GROUPS[0]}
        card = series_card(find_series_progress([self.series], few, SeriesConfig(min_share_owned=0.0)).progress[0])
        self.assertTrue(any("barely started" in f for f in checks.series_failures([card], [self.series], few)))

    def test_canon_owned_or_off_pool_or_wrong_genre_fails(self):
        self.assertTrue(any("is owned" in f for f in checks.canon_failures(self.canon_cards, OWNED | {GROUPS[6]}, self.world, GENRES)))
        self.assertTrue(any("not in the fetched" in f for f in checks.canon_failures(self.canon_cards, OWNED, [], GENRES)))
        self.assertTrue(any("top genres" in f for f in checks.canon_failures(self.canon_cards, OWNED, self.world, ["jazz", "folk"])))

    def test_anniversary_outside_window_unowned_or_wrong_document_date_fails(self):
        dates = {d.group_mbid: d.release_date for d in self.dated}
        self.assertTrue(any("not within" in f for f in checks.anniversary_failures(self.ann_cards, OWNED, date(2026, 6, 1), 30, dates)))
        self.assertTrue(any("not owned" in f for f in checks.anniversary_failures(self.ann_cards, set(), TODAY, 30, dates)))
        self.assertTrue(any("differs from the document" in f for f in checks.anniversary_failures(
            self.ann_cards, OWNED, TODAY, 30, {k: "1999-01-01" for k in dates})))

    def test_common_checks_catch_missing_reasons_and_duplicates(self):
        card = copy.deepcopy(self.canon_cards[0])
        card["reasons"] = []
        failures = checks.common_failures([card, self.canon_cards[0], self.canon_cards[0]])
        self.assertTrue(any("no reasons" in f for f in failures))
        self.assertTrue(any("duplicate key" in f for f in failures))


class VerdictAndIntegrityTests(unittest.TestCase):
    def test_verdicts(self):
        self.assertEqual(checks.verdict([], []), "no_cards")
        self.assertEqual(checks.verdict([{}], []), "verified")
        self.assertEqual(checks.verdict([{}], ["x"]), "failed")
        self.assertEqual(checks.verdict([], ["x"]), "failed")

    def test_run_integrity(self):
        self.assertTrue(checks.run_integrity({"musicbrainz": 100, "listenbrainz": 20}, 250)["complete"])
        self.assertFalse(checks.run_integrity({"musicbrainz": 300}, 250)["complete"])
        self.assertFalse(checks.run_integrity({"musicbrainz": 5, "musicbrainz_gave_up": 1}, 250)["complete"])
        self.assertFalse(checks.run_integrity({"musicbrainz": 5, "status_500": 1}, 250)["complete"])
        self.assertFalse(checks.run_integrity({"musicbrainz": 5}, 250, job_failures=2)["complete"])
        self.assertTrue(checks.run_integrity({"musicbrainz": 5, "musicbrainz_retries": 3}, 250)["complete"])


class VerifyLensesEndToEndTests(CheckFixtures):
    def run_verify(self, cards):
        docs = {"studio": {ARTIST: studio_doc()}, "lb": {}}
        return live.verify_lenses(
            None, OWNED, docs, {ARTIST: "Artist"}, [self.series], self.world, GENRES, self.dated, TODAY, 30,
            cards={"blind_spots": cards[0], "series": cards[1], "hidden_canon": cards[2], "anniversaries": cards[3]},
            job_failed=0)

    def test_correct_cards_are_verified(self):
        out = self.run_verify((self.spot_cards, self.series_cards, self.canon_cards, self.ann_cards))
        self.assertEqual({k: v["verdict"] for k, v in out["lenses"].items()},
                         {"blind_spots": "verified", "series": "verified", "hidden_canon": "verified", "anniversaries": "verified"})

    def test_empty_lenses_are_no_cards_not_verified(self):
        out = self.run_verify(([], [], [], []))
        self.assertTrue(all(v["verdict"] in ("no_cards", "failed") for v in out["lenses"].values()))
        self.assertFalse(any(v["verdict"] == "verified" for v in out["lenses"].values()))

    def test_a_corrupted_card_fails_its_lens(self):
        bad = copy.deepcopy(self.canon_cards)
        bad[0]["subject"]["group_mbid"] = GROUPS[0]
        out = self.run_verify((self.spot_cards, self.series_cards, bad, self.ann_cards))
        self.assertEqual(out["lenses"]["hidden_canon"]["verdict"], "failed")
        self.assertEqual(out["lenses"]["series"]["verdict"], "verified")


if __name__ == "__main__":
    unittest.main()
