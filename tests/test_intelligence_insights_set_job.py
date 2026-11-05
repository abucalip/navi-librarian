import tempfile
import unittest
from pathlib import Path

from intelligence.insights import (
    BlindSpotsConfig, SetFetchers, dismiss_blind_spot, list_blind_spot_cards, owned_group_mbids,
    refresh_blind_spots,
)
from intelligence.store import open_store
from intelligence.store import repositories as repo

CFG = BlindSpotsConfig(min_set_size=3, min_owned=1)
ARTIST = "11111111-1111-4111-8111-111111111111"


def gid(n):
    return f"00000000-0000-4000-8000-{n:012d}"


def studio_doc(n=4):
    return {"release-groups": [
        {"id": gid(i), "title": f"A{i}", "primary-type": "Album", "secondary-types": [],
         "first-release-date": f"{2000 + i}"} for i in range(1, n + 1)]}


class SetJobTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)
        repo.upsert_entity(self.db, "artist", "Band", mbid=ARTIST, owned=True)
        self.own(1)

    def own(self, n, owned=True):
        rel, _ = repo.upsert_entity(self.db, "release", f"R{n}", mbid=gid(100 + n), owned=owned)
        grp, _ = repo.upsert_entity(self.db, "release_group", f"G{n}", mbid=gid(n))
        repo.add_edge(self.db, rel, grp, "member_of", evidence_class="source_explicit",
                      match_quality="exact_mbid", source="musicbrainz")

    def test_owned_groups_only_from_owned_releases(self):
        self.own(2, owned=False)
        self.assertEqual(owned_group_mbids(self.db), {gid(1)})

    def test_refresh_saves_card(self):
        calls = []
        def studio(m):
            calls.append(m)
            return studio_doc()
        r = refresh_blind_spots(self.db, SetFetchers(studio=studio), config=CFG, now=1.0)
        self.assertEqual((r.looked_up, r.sets, r.saved), (1, 1, 1))
        self.assertEqual(calls, [ARTIST])
        card = list_blind_spot_cards(self.db)[0]
        self.assertEqual(card["missing_total"], 3)

    def test_no_fetchers_makes_no_lookups(self):
        r = refresh_blind_spots(self.db, SetFetchers(), config=CFG)
        self.assertEqual(r.looked_up, 0)
        self.assertEqual(list_blind_spot_cards(self.db), [])

    def test_failure_keeps_last_good_cards(self):
        refresh_blind_spots(self.db, SetFetchers(studio=lambda m: studio_doc()), config=CFG, now=1.0)
        def boom(m):
            raise RuntimeError("down")
        r = refresh_blind_spots(self.db, SetFetchers(studio=boom), config=CFG, now=2.0)
        self.assertEqual((r.failed, r.saved), (1, None))
        self.assertEqual(len(list_blind_spot_cards(self.db)), 1)

    def test_budget_stops_without_saving(self):
        repo.upsert_entity(self.db, "artist", "Two", mbid="22222222-2222-4222-8222-222222222222", owned=True)
        r = refresh_blind_spots(self.db, SetFetchers(studio=lambda m: studio_doc()), config=CFG, max_lookups=1)
        self.assertEqual((r.looked_up, r.remaining, r.saved), (1, 1, None))

    def test_not_found_and_invalid_counted(self):
        r = refresh_blind_spots(self.db, SetFetchers(studio=lambda m: None, listenbrainz=lambda m: {"x": 1}),
                                config=CFG)
        self.assertEqual((r.not_found, r.invalid, r.saved), (1, 1, 0))

    def test_series_use_explicit_mbids_and_dismissals_hold(self):
        doc = {"id": gid(900), "name": "Series", "relations": [
            {"target-type": "release_group", "release_group": {"id": gid(i), "title": f"S{i}"}}
            for i in range(1, 5)]}
        seen = []
        def series(m):
            seen.append(m)
            return doc
        refresh_blind_spots(self.db, SetFetchers(series=series), config=CFG, series_mbids=[gid(900)], now=1.0)
        self.assertEqual(seen, [gid(900)])
        key = list_blind_spot_cards(self.db)[0]["subject"]["key"].split(":", 1)[1]
        dismiss_blind_spot(self.db, key)
        refresh_blind_spots(self.db, SetFetchers(series=series), config=CFG, series_mbids=[gid(900)], now=2.0)
        self.assertEqual(list_blind_spot_cards(self.db), [])

    def test_bad_budget_rejected(self):
        with self.assertRaises(ValueError):
            refresh_blind_spots(self.db, SetFetchers(), max_lookups=0)


if __name__ == "__main__":
    unittest.main()
