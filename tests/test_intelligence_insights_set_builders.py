import unittest

from intelligence.insights import blind_spots as bs
from intelligence.insights import set_builders as sb

A = "11111111-1111-1111-1111-111111111111"
G = [f"aaaaaaaa-0000-0000-0000-00000000000{i}" for i in range(1, 8)]


def rg(i, title, primary="Album", secondary=(), date="1960-01-01"):
    return {"id": G[i].upper() if i == 0 else G[i], "title": title, "primary-type": primary,
            "secondary-types": list(secondary), "first-release-date": date}


class StudioTests(unittest.TestCase):
    def test_keeps_only_plain_albums_oldest_first(self):
        doc = {"release-groups": [
            rg(2, "Late", date="1975-05"), rg(0, "Early", date="1959"),
            rg(1, "Live!", secondary=["Live"]), rg(3, "Single", primary="Single"),
            {"id": "bad", "title": "x", "primary-type": "Album", "secondary-types": []},
            {"id": G[4], "title": "No types", "primary-type": "Album"},
            rg(0, "Early again", date="1959"), "junk",
        ]}
        s = sb.studio_discography_set(A, "Miles", doc)
        self.assertEqual([i.title for i in s.items], ["Early", "Late"])
        self.assertEqual(s.items[0].group_mbid, G[0])
        self.assertEqual((s.key, s.kind, s.items[1].year), (f"artist:{A}:studio", "studio_discography", 1975))

    def test_malformed_is_none(self):
        for doc in (None, {}, {"release-groups": "x"}):
            self.assertIsNone(sb.studio_discography_set(A, "M", doc))
        self.assertIsNone(sb.studio_discography_set("nope", "M", {"release-groups": []}))


class ListenBrainzTests(unittest.TestCase):
    def test_provider_order_and_skips_unmapped(self):
        doc = {"payload": {"release_groups": [
            {"release_group_mbid": G[2], "release_group_name": "B"},
            {"release_group_mbid": None, "release_group_name": "unmapped"},
            {"release_group_mbid": G[1], "release_group_name": "A"}]}}
        s = sb.listenbrainz_top_set(A, "X", doc)
        self.assertEqual([i.title for i in s.items], ["B", "A"])
        self.assertEqual(s.source, "listenbrainz")
        self.assertIsNone(sb.listenbrainz_top_set(A, "X", {"payload": {}}))


class SeriesTests(unittest.TestCase):
    def rel(self, i, key=None, number=None):
        r = {"target-type": "release_group", "release_group": {"id": G[i], "title": f"T{i}"}}
        if key is not None:
            r["ordering-key"] = key
        if number is not None:
            r["attribute-values"] = {"number": number}
        return r

    def test_series_order(self):
        doc = {"id": A, "name": "Blue Note 4000", "relations": [
            self.rel(3), self.rel(1, number="2"), self.rel(0, key=1),
            {"target-type": "artist"}, self.rel(1, key=9)]}
        s = sb.series_set(doc)
        self.assertEqual([i.title for i in s.items], ["T0", "T1", "T3"])
        self.assertEqual((s.key, s.kind, s.label), (f"series:{A}", "series", "Blue Note 4000"))
        self.assertIsNone(sb.series_set({"id": A}))


class EndToEndTests(unittest.TestCase):
    def test_feeds_blind_spots(self):
        doc = {"release-groups": [rg(i, f"T{i}", date=f"19{60 + i}") for i in range(6)]}
        s = sb.studio_discography_set(A, "Miles", doc)
        result = bs.find_blind_spots([s], [G[0], G[1]], bs.BlindSpotsConfig())
        self.assertEqual((result.spots[0].owned, result.spots[0].total), (2, 6))


if __name__ == "__main__":
    unittest.main()
