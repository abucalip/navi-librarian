import os
import unittest
from unittest import mock

from discovery.search.artist_sections import network_sections
from discovery.search.providers import album_candidate, artist_candidate
from intelligence.editions.ownership import (
    FLAG_ENV, NOT_OWNED, OTHER_EDITION, SAME_EDITION, base_key, edition_awareness_enabled, edition_match,
)
from tests.test_discovery_search_artist_sections import FakeMusicBrainz, network, radiohead_owned

OWNED = [
    {"id": "al2", "name": "Rumours (Deluxe Edition)", "year": 2013},
    {"id": "al1", "name": "Rumours", "year": 1977},
    {"id": "al3", "name": "Tusk", "year": 1979},
    {"id": "al4", "name": "Tango in the Night (Live)", "year": 1987},
]


class FlagTests(unittest.TestCase):
    def test_off_unless_explicitly_on(self):
        self.assertFalse(edition_awareness_enabled({}))
        self.assertFalse(edition_awareness_enabled({FLAG_ENV: ""}))
        self.assertFalse(edition_awareness_enabled({FLAG_ENV: "0"}))
        self.assertTrue(edition_awareness_enabled({FLAG_ENV: " TRUE "}))
        with mock.patch.dict(os.environ, {FLAG_ENV: "1"}):
            self.assertTrue(edition_awareness_enabled())


class MatchTests(unittest.TestCase):
    def test_base_key_drops_only_edition_brackets(self):
        self.assertEqual(base_key("Rumours (Deluxe Edition)"), base_key("Rumours"))
        self.assertEqual(base_key("Rumours [2011 Remaster]"), base_key("Rumours"))
        self.assertNotEqual(base_key("Rumours (Part 2)"), base_key("Rumours"))

    def test_same_name_is_same_edition_like_the_old_matcher(self):
        match = edition_match({"name": "Rumours", "year": 1977}, OWNED)
        self.assertEqual((match.status, match.owned_id), (SAME_EDITION, "al1"))

    def test_other_edition_when_the_library_holds_a_different_edition(self):
        match = edition_match({"name": "Tusk (Remastered)", "year": 2015}, OWNED)
        self.assertEqual((match.status, match.owned_id), (OTHER_EDITION, "al3"))
        self.assertEqual(match.candidate_markers, ("remaster", "remastered"))
        match = edition_match({"name": "Rumours (Super Deluxe)", "year": 2013}, OWNED)
        self.assertEqual(match.status, OTHER_EDITION)

    def test_plain_title_with_owned_deluxe_only(self):
        match = edition_match({"name": "Rumours", "year": 1977}, [OWNED[0]])
        self.assertEqual((match.status, match.owned_id, match.owned_markers), (OTHER_EDITION, "al2", ("deluxe",)))

    def test_live_is_never_another_edition(self):
        self.assertEqual(edition_match({"name": "Tango in the Night", "year": 1987}, OWNED).status, NOT_OWNED)
        self.assertEqual(edition_match({"name": "Tusk (Live)", "year": 1980}, OWNED).status, NOT_OWNED)

    def test_same_title_without_edition_words_and_other_year_is_not_owned(self):
        self.assertEqual(edition_match({"name": "Tusk", "year": 2004}, OWNED).status, NOT_OWNED)

    def test_different_albums_and_empty_names_never_match(self):
        self.assertEqual(edition_match({"name": "Mirage (Deluxe)", "year": 1982}, OWNED).status, NOT_OWNED)
        self.assertEqual(edition_match({"name": "(Deluxe)", "year": None}, [{"id": "x", "name": "(Deluxe)"}]).status,
                         SAME_EDITION)
        self.assertEqual(edition_match({"name": "(Deluxe)", "year": None}, OWNED).status, NOT_OWNED)

    def test_result_is_stable_whatever_the_owned_order(self):
        both = [{"id": "b", "name": "X (Deluxe)", "year": 2000}, {"id": "a", "name": "X (Expanded)", "year": 2001}]
        for entries in (both, both[::-1]):
            self.assertEqual(edition_match({"name": "X (Remaster)", "year": 2010}, entries).owned_id, "a")


class CatalogWiringTests(unittest.TestCase):
    ALBUMS = [
        album_candidate("musicbrainz", "OK Computer", "Radiohead", 1997, "rg-1"),
        album_candidate("musicbrainz", "OK Computer (Deluxe Edition)", "Radiohead", 1997, "rg-1b"),
        album_candidate("musicbrainz", "The Bends", "Radiohead", 1995, "rg-3"),
    ]
    OWNED_ITEMS = [{"name": "OK Computer", "year": 1997, "song_count": 12, "key": "radiohead/ok computer",
                    "id": "al1", "artwork_url": "/art/al1"}]

    def items(self):
        net = network(FakeMusicBrainz(artists=[artist_candidate("musicbrainz", "Radiohead", "mb-rh")],
                                      albums=self.ALBUMS))
        return network_sections(net, "Radiohead", "ar1", radiohead_owned(),
                                owned_album_items=self.OWNED_ITEMS)["albums"]["items"]

    def test_flag_off_adds_nothing_and_flag_on_changes_no_owned_flag(self):
        with mock.patch.dict(os.environ, {FLAG_ENV: ""}):
            off = self.items()
        with mock.patch.dict(os.environ, {FLAG_ENV: "1"}):
            on = self.items()
        self.assertTrue(all("owned_edition" not in item for item in off))
        self.assertEqual([{k: v for k, v in i.items() if k != "owned_edition"} for i in on], off)
        self.assertEqual({i["name"]: i["owned"] for i in on},
                         {"OK Computer": True, "OK Computer (Deluxe Edition)": False, "The Bends": False})

    def test_flag_on_reports_the_owned_edition_for_an_unowned_edition(self):
        with mock.patch.dict(os.environ, {FLAG_ENV: "1"}):
            by_name = {i["name"]: i for i in self.items()}
        self.assertEqual(by_name["OK Computer (Deluxe Edition)"]["owned_edition"]["status"], OTHER_EDITION)
        self.assertEqual(by_name["OK Computer (Deluxe Edition)"]["owned_edition"]["owned_id"], "al1")
        self.assertEqual(by_name["OK Computer"]["owned_edition"]["status"], SAME_EDITION)
        self.assertEqual(by_name["The Bends"]["owned_edition"]["status"], NOT_OWNED)


if __name__ == "__main__":
    unittest.main()
