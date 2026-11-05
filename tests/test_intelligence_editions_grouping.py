import tempfile
import unittest
from pathlib import Path

from intelligence.editions import (
    TrackEntry, compare_tracklists, edition_labels, group_editions, link_release_group,
    parse_release, release_relation,
)
from intelligence.editions.grouping import LATER, ORIGINAL, UNKNOWN
from intelligence.store import open_store
from intelligence.store import repositories as repo

REL1 = "11111111-1111-1111-1111-111111111111"
REL2 = "22222222-2222-2222-2222-222222222222"
RG1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


def doc(release, title, date, disambiguation=None, first="1977-02-04", secondary=()):
    return {
        "id": release, "title": title, "date": date, "disambiguation": disambiguation,
        "release-group": {"id": RG1, "title": "Rumours", "primary-type": "Album",
                          "secondary-types": list(secondary), "first-release-date": first},
    }


def te(title, pos=None, mbid=None, rid=1):
    return TrackEntry(pos, title, rid, mbid)


class LabelTests(unittest.TestCase):
    def test_labels_from_title_disambiguation_and_type(self):
        info = parse_release(doc(REL1, "Rumours (Deluxe)", "2013", "2013 remastered", secondary=["Live"]), REL1)
        self.assertEqual(edition_labels(info), ("deluxe", "remaster", "live"))

    def test_plain_release_has_no_labels(self):
        self.assertEqual(edition_labels(parse_release(doc(REL1, "Rumours", "1977-02-04"), REL1)), ())
        self.assertEqual(edition_labels(None), ())

    def test_words_inside_other_words_do_not_match(self):
        info = parse_release(doc(REL1, "Rumours", "1977", "alive and well"), REL1)
        self.assertEqual(edition_labels(info), ())


class RelationTests(unittest.TestCase):
    def rel(self, date, first="1977-02-04"):
        return release_relation(parse_release(doc(REL1, "R", date, first=first), REL1))

    def test_original_later_unknown(self):
        self.assertEqual(self.rel("1977-02-04"), ORIGINAL)
        self.assertEqual(self.rel("1977"), ORIGINAL)  # coarser date: same year
        self.assertEqual(self.rel("2013-01-29"), LATER)
        self.assertEqual(self.rel("1970-01-01"), UNKNOWN)  # earlier than "first" is inconsistent
        self.assertEqual(self.rel(None), UNKNOWN)
        self.assertEqual(self.rel("2013", first=None), UNKNOWN)
        self.assertEqual(self.rel("garbage"), UNKNOWN)
        self.assertEqual(release_relation(None), UNKNOWN)


class GroupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = open_store(Path(self._tmp.name) / "v2.sqlite3")
        self.addCleanup(self.db.close)

    def add_release(self, mbid, title, date, owned=True, tracks=(), disambiguation=None):
        rid = repo.upsert_entity(self.db, "release", title, mbid=mbid, navidrome_id=f"al-{mbid[:2]}", owned=owned)[0]
        link_release_group(self.db, rid, fetch=lambda m: doc(mbid, title, date, disambiguation), now=1.0)
        for n, name in enumerate(tracks, 1):
            rec = repo.upsert_entity(self.db, "recording", name, navidrome_id=f"{mbid[:2]}-{n}")[0]
            repo.add_edge(self.db, rec, rid, "appears_on", evidence_class="library_tag",
                          match_quality="fuzzy_unconfirmed", source="navidrome", role=f"1/{n}")
        return rid

    def group_id(self):
        return repo.find_entity(self.db, "release_group", mbid=RG1)["id"]

    def test_groups_owned_editions_in_date_order(self):
        self.add_release(REL2, "Rumours (Deluxe)", "2013-01-29", tracks=["Dreams", "Gold Dust Woman", "Silver Springs"])
        self.add_release(REL1, "Rumours", "1977-02-04", tracks=["Dreams", "Gold Dust Woman"])
        editions = group_editions(self.db, self.group_id())
        self.assertEqual([e.mbid for e in editions], [REL1, REL2])
        self.assertEqual([e.relation for e in editions], [ORIGINAL, LATER])
        self.assertEqual(editions[1].labels, ("deluxe",))
        self.assertEqual([t.title for t in editions[1].tracks], ["Dreams", "Gold Dust Woman", "Silver Springs"])

    def test_unowned_members_hidden_unless_asked(self):
        self.add_release(REL1, "Rumours", "1977-02-04")
        self.add_release(REL2, "Rumours (Deluxe)", "2013", owned=False)
        self.assertEqual(len(group_editions(self.db, self.group_id())), 1)
        self.assertEqual(len(group_editions(self.db, self.group_id(), owned_only=False)), 2)

    def test_release_without_stored_document_is_unknown(self):
        rid = repo.upsert_entity(self.db, "release", "Lone", mbid=REL2, owned=True)[0]
        gid = repo.upsert_entity(self.db, "release_group", "Lone", mbid=RG1)[0]
        repo.add_edge(self.db, rid, gid, "member_of", evidence_class="source_explicit",
                      match_quality="exact_mbid", source="musicbrainz")
        [edition] = group_editions(self.db, gid)
        self.assertEqual((edition.relation, edition.labels, edition.info), (UNKNOWN, (), None))

    def test_wrong_entity_type_is_rejected(self):
        rid = self.add_release(REL1, "Rumours", "1977")
        with self.assertRaises(ValueError):
            group_editions(self.db, rid)

    def test_group_is_read_only(self):
        self.add_release(REL1, "Rumours", "1977")
        before = self.db.execute("SELECT (SELECT COUNT(*) FROM edges) + (SELECT COUNT(*) FROM entities)").fetchone()[0]
        group_editions(self.db, self.group_id())
        after = self.db.execute("SELECT (SELECT COUNT(*) FROM edges) + (SELECT COUNT(*) FROM entities)").fetchone()[0]
        self.assertEqual(before, after)


class CompareTests(unittest.TestCase):
    def test_identical(self):
        d = compare_tracklists([te("A"), te("B")], [te("a"), te("B")])
        self.assertTrue(d.same)
        self.assertEqual(d.shared, 2)

    def test_bonus_tracks_and_missing(self):
        d = compare_tracklists([te("A"), te("B")], [te("A"), te("B"), te("Bonus")])
        self.assertEqual((d.shared, d.only_in_a, d.only_in_b), (2, (), ("Bonus",)))
        self.assertFalse(d.same)

    def test_reorder(self):
        d = compare_tracklists([te("A"), te("B"), te("C")], [te("A"), te("C"), te("B")])
        self.assertTrue(d.order_changed)
        self.assertEqual(d.shared, 3)

    def test_matches_by_mbid_when_titles_differ(self):
        m = "99999999-9999-9999-9999-999999999999"
        d = compare_tracklists([te("Go Your Own Way", mbid=m)], [te("Go Your Own Way (Remastered)", mbid=m)])
        self.assertEqual((d.shared, d.only_in_a, d.only_in_b), (1, (), ()))

    def test_repeated_titles_are_ambiguous_not_paired(self):
        d = compare_tracklists([te("Intro"), te("Intro"), te("A")], [te("Intro"), te("A")])
        self.assertEqual(d.ambiguous, ("Intro",))
        self.assertEqual(d.shared, 1)
        self.assertFalse(d.same)

    def test_empty(self):
        self.assertTrue(compare_tracklists([], []).same)


if __name__ == "__main__":
    unittest.main()
