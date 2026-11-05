import tempfile
import unittest
from pathlib import Path

from intelligence.editions import find_duplicate_albums, find_duplicate_recordings, find_duplicates, link_release_group
from intelligence.store import open_store
from intelligence.store import repositories as repo

REL1 = "11111111-1111-1111-1111-111111111111"
REL2 = "22222222-2222-2222-2222-222222222222"
REL3 = "33333333-3333-3333-3333-333333333333"
RG1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
RG2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
REC = "99999999-9999-9999-9999-999999999999"


def doc(release, title, date, group=RG1, group_title="Rumours"):
    return {"id": release, "title": title, "date": date,
            "release-group": {"id": group, "title": group_title, "primary-type": "Album",
                              "first-release-date": "1977-02-04"}}


class DuplicateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = open_store(Path(self._tmp.name) / "v2.sqlite3")
        self.addCleanup(self.db.close)
        self.n = 0

    def release(self, mbid, title, date, tracks=(), owned=True, group=RG1, group_title="Rumours"):
        rid = repo.upsert_entity(self.db, "release", title, mbid=mbid, navidrome_id=f"al-{mbid[:2]}", owned=owned)[0]
        link_release_group(self.db, rid, fetch=lambda m: doc(mbid, title, date, group, group_title), now=1.0)
        for number, (name, rec_mbid) in enumerate(tracks, 1):
            self.n += 1
            rec = repo.upsert_entity(self.db, "recording", name, mbid=rec_mbid, navidrome_id=f"t{self.n}")[0]
            repo.add_edge(self.db, rec, rid, "appears_on", evidence_class="library_tag",
                          match_quality="fuzzy_unconfirmed", source="navidrome", role=f"1/{number}")
        return rid

    def counts(self):
        return self.db.execute("SELECT (SELECT COUNT(*) FROM edges) + (SELECT COUNT(*) FROM entities)").fetchone()[0]

    def test_two_owned_editions_are_a_duplicate_album(self):
        self.release(REL1, "Rumours", "1977-02-04", [("Dreams", None), ("Gold Dust Woman", None)])
        self.release(REL2, "Rumours (Deluxe)", "2013-01-29", [("Dreams", None), ("Gold Dust Woman", None), ("Silver Springs", None)])
        [album] = find_duplicate_albums(self.db)
        self.assertTrue(album.suggestion_only)
        self.assertEqual([e.mbid for e in album.editions], [REL1, REL2])
        [difference] = album.differences
        self.assertEqual(difference.diff.only_in_b, ("Silver Springs",))
        self.assertEqual([r.code for r in album.reasons], ["same_release_group", "edition_labels"])

    def test_single_owned_edition_or_unowned_second_is_not_a_duplicate(self):
        self.release(REL1, "Rumours", "1977-02-04")
        self.release(REL2, "Rumours (Deluxe)", "2013", owned=False)
        self.assertEqual(find_duplicate_albums(self.db), [])

    def test_missing_tracklist_is_said(self):
        self.release(REL1, "Rumours", "1977-02-04")
        self.release(REL2, "Rumours", "1977-02-04")
        [album] = find_duplicate_albums(self.db)
        self.assertIn("tracklist_unknown", [r.code for r in album.reasons])

    def test_recording_on_two_albums_is_a_duplicate_recording(self):
        self.release(REL1, "Rumours", "1977-02-04", [("Dreams", REC)])
        self.release(REL3, "Greatest Hits", "1988", [("Dreams", REC)], group=RG2, group_title="Greatest Hits")
        recordings, skipped = find_duplicate_recordings(self.db)
        [rec] = recordings
        self.assertEqual((skipped, rec.same_album, rec.recording_mbid), (0, False, REC))
        self.assertEqual(len(rec.appearances), 2)
        self.assertIn("different_albums", [r.code for r in rec.reasons])

    def test_recording_across_editions_is_marked_expected(self):
        self.release(REL1, "Rumours", "1977-02-04", [("Dreams", REC)])
        self.release(REL2, "Rumours (Deluxe)", "2013", [("Dreams", REC)])
        [rec], _ = find_duplicate_recordings(self.db)
        self.assertTrue(rec.same_album)
        self.assertIn("edition_overlap", [r.code for r in rec.reasons])

    def test_recording_without_mbid_is_counted_not_compared(self):
        self.release(REL1, "Rumours", "1977-02-04", [("Dreams", None)])
        rid = repo.find_entity(self.db, "recording", navidrome_id="t1")["id"]
        other = self.release(REL3, "Greatest Hits", "1988", group=RG2, group_title="Greatest Hits")
        repo.add_edge(self.db, rid, other, "appears_on", evidence_class="library_tag",
                      match_quality="fuzzy_unconfirmed", source="navidrome", role="1/1")
        recordings, skipped = find_duplicate_recordings(self.db)
        self.assertEqual((recordings, skipped), ([], 1))

    def test_unowned_release_does_not_count(self):
        self.release(REL1, "Rumours", "1977-02-04", [("Dreams", REC)])
        self.release(REL3, "Greatest Hits", "1988", [("Dreams", REC)], owned=False, group=RG2, group_title="GH")
        self.assertEqual(find_duplicate_recordings(self.db), ([], 0))

    def test_report_limit_and_read_only(self):
        for mbid, title in ((REL1, "Rumours"), (REL2, "Rumours (Deluxe)")):
            self.release(mbid, title, "1977", [("Dreams", REC)])
        self.release(REL3, "Greatest Hits", "1988", [("Dreams", REC)], group=RG2, group_title="GH")
        before = self.counts()
        report = find_duplicates(self.db, limit=1)
        self.assertEqual((len(report.albums), len(report.recordings), report.truncated), (1, 1, False))
        self.assertEqual(self.counts(), before)

    def test_empty_store(self):
        report = find_duplicates(self.db)
        self.assertEqual((report.albums, report.recordings, report.skipped_recordings, report.truncated), ([], [], 0, False))


if __name__ == "__main__":
    unittest.main()
