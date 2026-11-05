import unittest
from datetime import date

from intelligence.insights import (
    AnniversaryConfig, DatedAlbum, DatedArtist, anniversary_card, find_anniversaries,
)

TODAY = date(2026, 11, 5)


def alb(i, d, **kw):
    return DatedAlbum(f"G{i}", f"T{i}", f"A{i}", d, **kw)


class AnniversaryTests(unittest.TestCase):
    def test_nothing_supplied(self):
        self.assertEqual(find_anniversaries([], [], TODAY).empty_reason, "nothing_supplied")

    def test_exact_day_and_milestone(self):
        r = find_anniversaries([alb(1, "1976-11-05"), alb(2, "1977-11-05"), alb(3, "1976-11-06")], [], TODAY)
        self.assertEqual([(i.mbid, i.years) for i in r.items], [("g1", 50)])
        r = find_anniversaries([alb(2, "1977-11-05")], [], TODAY, AnniversaryConfig(milestone_every=1))
        self.assertEqual(r.items[0].years, 49)

    def test_none_today(self):
        self.assertEqual(find_anniversaries([alb(1, "1976-03-01")], [], TODAY).empty_reason, "none_today")

    def test_partial_and_future_dates_are_dropped_and_counted(self):
        r = find_anniversaries([alb(1, "1976"), alb(2, "1976-11"), alb(3, "2030-11-05"), alb(4, None)], [], TODAY)
        self.assertEqual((r.partial_dates, r.future_dates, r.items), (2, 1, ()))

    def test_same_year_is_not_an_anniversary(self):
        r = find_anniversaries([alb(1, "2026-11-05")], [], TODAY, AnniversaryConfig(milestone_every=1))
        self.assertEqual(r.items, ())

    def test_window_reports_offset(self):
        r = find_anniversaries([alb(1, "1976-11-03"), alb(2, "1976-11-08")], [], TODAY, AnniversaryConfig(window_days=2))
        self.assertEqual([(i.mbid, i.days_from_today) for i in r.items], [("g1", -2)])
        self.assertIn("2 days ago", anniversary_card(r.items[0])["body"])

    def test_window_crosses_year_end(self):
        r = find_anniversaries([alb(1, "1977-01-01")], [], date(2026, 12, 31), AnniversaryConfig(window_days=1))
        self.assertEqual((r.items[0].years, r.items[0].days_from_today), (50, 1))

    def test_leap_day_observed_feb_28(self):
        r = find_anniversaries([alb(1, "1976-02-29")], [], date(2026, 2, 28))
        self.assertEqual(r.items[0].years, 50)
        self.assertEqual(find_anniversaries([alb(1, "1976-02-29")], [], date(2036, 2, 29)).items[0].years, 60)
        self.assertEqual(find_anniversaries([alb(1, "1976-02-29")], [], date(2036, 2, 28)).items, ())

    def test_artist_kinds_and_wording_are_separate(self):
        artists = [DatedArtist("P1", "Ann", "Person", "1966-11-05", "2016-11-05"),
                   DatedArtist("B1", "Band", "group", "1976-11-05", "1996-11-05"),
                   DatedArtist("O1", "Orch", "orchestra", "1976-11-05")]
        r = find_anniversaries([], artists, TODAY)
        kinds = {(i.kind, i.years) for i in r.items}
        self.assertEqual(kinds, {("artist_born", 60), ("artist_died", 10), ("artist_formed", 50), ("artist_disbanded", 30)})
        self.assertEqual(r.unknown_type, 1)
        body = {i.kind: anniversary_card(i)["body"] for i in r.items}
        self.assertTrue(body["artist_died"].startswith("Died 10 years ago today"))
        self.assertTrue(body["artist_born"].startswith("Born 60 years ago today"))

    def test_dismiss_is_per_anniversary_year(self):
        (item,) = find_anniversaries([alb(1, "1976-11-05")], [], TODAY).items
        self.assertEqual(item.key, "anniversary:album_release:g1:2026")
        r = find_anniversaries([alb(1, "1976-11-05")], [], TODAY, dismissed=[item.key])
        self.assertEqual((r.items, r.suppressed, r.empty_reason), ((), 1, "none_today"))
        r = find_anniversaries([alb(1, "1976-11-05")], [], date(2031, 11, 5), dismissed=[item.key])
        self.assertEqual(r.items[0].years, 55)

    def test_missing_mbid_and_duplicates_skipped(self):
        r = find_anniversaries([DatedAlbum(None, "x", "a", "1976-11-05"), alb(1, "1976-11-05"), alb(1, "1976-11-05")], [], TODAY)
        self.assertEqual(len(r.items), 1)

    def test_order_and_limit(self):
        r = find_anniversaries([alb(1, "1996-11-05"), alb(2, "1966-11-05"), alb(3, "1976-11-05")], [], TODAY,
                               AnniversaryConfig(limit=2))
        self.assertEqual([i.mbid for i in r.items], ["g2", "g3"])

    def test_card_shape(self):
        (item,) = find_anniversaries([alb(1, "1976-11-05")], [], TODAY).items
        c = anniversary_card(item)
        self.assertEqual((c["kind"], c["actions"], c["dismissible"]), ("anniversary", [{"kind": "dismiss"}], True))
        self.assertEqual(c["body"], "Released 50 years ago today (1976-11-05).")
        self.assertEqual(c["subject"]["type"], "release_group")
        self.assertEqual(c["reasons"][0]["evidence"], {"event": "album_release", "date": "1976-11-05", "years": 50})


if __name__ == "__main__":
    unittest.main()
