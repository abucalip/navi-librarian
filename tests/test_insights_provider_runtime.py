"""Provider-backed lens refresh: budgeted ticks, resume, completeness gate, outage handling."""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from intelligence.ingest.navidrome import ingest_album
from intelligence.insights import (
    list_anniversary_cards, list_blind_spot_cards, list_canon_cards, list_series_cards, refresh_provider_lenses,
)
from intelligence.insights import provider_cache as cache
from intelligence.store import open_store

A1, A2 = "11111111-1111-4111-8111-111111111111", "22222222-2222-4222-8222-222222222222"
SERIES_ID = "55555555-5555-4555-8555-555555555555"
NOW = 1_800_000_000.0
TODAY = date(2026, 6, 1)


def g(n):
    return f"{n:08d}-0000-4000-8000-000000000000"


def album(i, artist_id, artist_mbid, rel_mbid):
    return {"id": f"al{i}", "name": f"Album {i}", "artist": f"Artist {artist_id}", "artistId": artist_id,
            "artists": [{"id": artist_id, "musicBrainzId": artist_mbid}], "musicBrainzId": rel_mbid,
            "genres": [{"name": "Shoegaze"}, {"name": "Dream Pop"}], "song": []}


class Resp:
    def __init__(self, status, body):
        self.status_code, self._b = status, body

    def json(self):
        return self._b


class FakeProviders:
    """Routes by URL; owned groups g(1), g(2) for artist 1 and g(11), g(12) for artist 2."""

    def __init__(self, fail_after=None):
        self.calls = []
        self.fail_after = fail_after

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append(url)
        if self.fail_after is not None and len(self.calls) > self.fail_after:
            return Resp(503, {})
        p = params or {}
        if "/release-group/" in url and p.get("inc") == "series-rels":
            group = url.rsplit("/", 1)[1]
            if group == g(404):
                return Resp(404, {})
            sid = SERIES_ID if group in (g(1), g(2), g(11)) else None
            rels = [{"target-type": "series", "series": {"id": sid.upper()}}] if sid else []
            return Resp(200, {"id": group, "relations": rels})
        if "/series/" in url:
            members = [g(1), g(2), g(3), g(4)]  # owns 1 and 2
            rels = [{"target-type": "release_group", "ordering-key": i + 1,
                     "release_group": {"id": m, "title": f"RG {m[:8]}", "first-release-date": "1991"}}
                    for i, m in enumerate(members)]
            return Resp(200, {"id": SERIES_ID, "name": "The Series", "relations": rels})
        if url.endswith("/release"):
            base = 0 if p["artist"] == A1 else 10
            rels = [{"id": f"aaaaaaa{base + k}-0000-4000-8000-000000000000"[-36:],
                     "release-group": {"id": g(base + k), "title": f"RG {base + k}"}} for k in (1, 2)]
            return Resp(200, {"releases": rels})
        if url.endswith("/release-group"):
            base = 0 if p["artist"] == A1 else 10
            groups = [{"id": g(base + k), "title": f"RG {base + k}", "primary-type": "Album", "secondary-types": [],
                       "first-release-date": f"{1990 + k}-06-01"} for k in range(1, 8)]
            return Resp(200, {"release-groups": groups, "release-group-count": 7})
        if "popularity" in url:
            base = 0 if url.endswith(A1) else 10
            return Resp(200, [{"release_group_mbid": g(base + k), "release_group_name": f"RG {base + k}",
                               "total_listen_count": 1000 * k} for k in range(1, 8)])
        return Resp(200, {"name": "X", "type": "Group", "life-span": {"begin": "1991-06-01"}})


def rel_mbid(base, k):
    return f"aaaaaaa{base + k}-0000-4000-8000-000000000000"[-36:]


class Runtime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = open_store(Path(self.tmp.name) / "x.sqlite3")
        self.addCleanup(self.db.close)
        n = 0
        for base, aid, am in ((0, "ar1", A1), (10, "ar2", A2)):
            for k in (1, 2):
                n += 1
                ingest_album(self.db, album(n, aid, am, rel_mbid(base, k)), now=1.0)

    def tick(self, fake, budget, ttl=30 * 86400.0, now=NOW):
        return refresh_provider_lenses(self.db, get=fake, headers={"User-Agent": "t"}, sleep=None,
                                       budget=budget, ttl=ttl, now=now, today=TODAY)

    def series_tick(self, fake, budget, now=NOW, ttl=30 * 86400.0):
        return refresh_provider_lenses(self.db, get=fake, headers={"User-Agent": "t"}, sleep=None,
                                       budget=budget, ttl=ttl, now=now, today=TODAY, series=True)

    def cards(self):
        return (len(list_blind_spot_cards(self.db, 50)), len(list_canon_cards(self.db, 50)),
                len(list_anniversary_cards(self.db, 50)))

    def test_budget_is_respected_and_cards_wait_for_a_complete_pass(self):
        fake = FakeProviders()
        result = self.tick(fake, budget=3)
        self.assertEqual(result.state, "succeeded")
        self.assertLessEqual(len(fake.calls), 3)
        self.assertEqual(result.progress["stopped"], "budget")
        self.assertFalse(result.progress["complete"])
        self.assertEqual(self.cards(), (0, 0, 0))

    def test_resumes_until_complete_then_saves_cards_without_refetching(self):
        fake = FakeProviders()
        for _ in range(10):
            result = self.tick(fake, budget=4)
            if result.progress["complete"]:
                break
        self.assertTrue(result.progress["complete"])
        self.assertGreater(self.cards()[0], 0)       # blind spots: owns 2 of 7
        self.assertGreater(self.cards()[1], 0)       # hidden canon
        self.assertGreater(self.cards()[2], 0)       # anniversaries (1991-06-01 is 35 years before TODAY)
        before = len(fake.calls)
        done = self.tick(fake, budget=50)
        self.assertEqual(len(fake.calls), before)    # everything fresh: no provider traffic
        self.assertTrue(done.progress["complete"])

    def test_stale_documents_are_refetched_after_ttl(self):
        fake = FakeProviders()
        self.tick(fake, budget=200)
        before = len(fake.calls)
        self.tick(fake, budget=200, now=NOW + 31 * 86400.0)
        self.assertGreater(len(fake.calls), before)

    def test_outage_fails_the_run_keeps_cache_and_saved_cards(self):
        fake = FakeProviders()
        self.tick(fake, budget=200)
        saved = self.cards()
        broken = FakeProviders(fail_after=0)
        result = self.tick(broken, budget=200, now=NOW + 31 * 86400.0)
        self.assertEqual(result.state, "failed")
        self.assertEqual(self.cards(), saved)
        self.assertIsNotNone(cache.get(self.db, "studio", A1))

    def test_no_owned_artists_makes_no_requests(self):
        empty = open_store(Path(self.tmp.name) / "empty.sqlite3")
        self.addCleanup(empty.close)
        fake = FakeProviders()
        result = refresh_provider_lenses(empty, get=fake, headers={}, sleep=None, budget=10, now=NOW, today=TODAY)
        self.assertEqual(fake.calls, [])
        self.assertFalse(result.progress["complete"])

    def test_dismissed_blind_spot_stays_suppressed(self):
        from intelligence.insights import dismiss_blind_spot
        fake = FakeProviders()
        self.tick(fake, budget=200)
        key = list_blind_spot_cards(self.db, 50)[0]["subject"]["key"]
        dismiss_blind_spot(self.db, key.removeprefix("blind_spot:"))
        self.tick(fake, budget=200, now=NOW + 31 * 86400.0)
        self.assertNotIn(key, {c["subject"]["key"] for c in list_blind_spot_cards(self.db, 50)})

    def test_series_off_makes_no_series_requests(self):
        fake = FakeProviders()
        self.tick(fake, budget=200)
        self.assertFalse([u for u in fake.calls if "/series/" in u or "/release-group/" in u])
        self.assertEqual(list_series_cards(self.db, 50), [])

    def test_series_ids_are_discovered_then_cards_saved_once_complete(self):
        fake = FakeProviders()
        for _ in range(20):
            result = self.series_tick(fake, budget=5)
            if result.progress.get("series_complete"):
                break
        self.assertTrue(result.progress["series_complete"])
        self.assertEqual(result.progress["series_ids"], 1)
        cards = list_series_cards(self.db, 50)
        self.assertEqual(len(cards), 1)
        self.assertEqual((cards[0]["owned"], cards[0]["total"]), (2, 4))
        before = len(fake.calls)
        again = self.series_tick(fake, budget=50)
        self.assertEqual(len(fake.calls), before)    # all fresh: no provider traffic
        self.assertTrue(again.progress["series_complete"])

    def test_series_cards_wait_for_complete_discovery(self):
        fake = FakeProviders()
        result = self.series_tick(fake, budget=6)    # browse and artist documents use the budget first
        self.assertEqual(result.progress["stopped"], "budget")
        self.assertFalse(result.progress["series_complete"])
        self.assertEqual(list_series_cards(self.db, 50), [])

    def test_series_lookup_404_for_a_group_counts_as_no_series(self):
        from intelligence.insights.provider_runtime import _group_series
        self.assertEqual(_group_series(FakeProviders(), g(404), {}, None), {"series": []})
        self.assertEqual(_group_series(FakeProviders(), g(1), {}, None), {"series": [SERIES_ID]})

    def test_series_outage_fails_the_run_and_keeps_cards(self):
        fake = FakeProviders()
        self.series_tick(fake, budget=200)
        saved = list_series_cards(self.db, 50)
        result = self.series_tick(FakeProviders(fail_after=0), budget=200, now=NOW + 31 * 86400.0)
        self.assertEqual(result.state, "failed")
        self.assertEqual(list_series_cards(self.db, 50), saved)


if __name__ == "__main__":
    unittest.main()
