import tempfile
import unittest
from pathlib import Path

from intelligence.editions import advise, edition_track_ids, find_duplicate_albums, link_release_group
from intelligence.health.audio import AudioMeasurement
from intelligence.store import open_store
from intelligence.store import repositories as repo

REL1 = "11111111-1111-1111-1111-111111111111"
REL2 = "22222222-2222-2222-2222-222222222222"
RG1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
BANNED = ("better", "worse", "best", "worst", "should", "recommend", "delete", "remove", "keep")


def doc(release, title, date):
    return {"id": release, "title": title, "date": date,
            "release-group": {"id": RG1, "title": "Rumours", "primary-type": "Album", "first-release-date": "1977-02-04"}}


def m(track_id, lufs=-12.0, lra=6.0, tp=-0.5, peak=-1.0, count=1):
    return AudioMeasurement(track_id, peak_dbfs=peak, peak_count=count, integrated_lufs=lufs,
                            loudness_range_lu=lra, true_peak_dbfs=tp)


class AdvisorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = open_store(Path(self._tmp.name) / "v2.sqlite3")
        self.addCleanup(self.db.close)

    def release(self, mbid, title, date, prefix, names=("Dreams", "Gold Dust Woman")):
        rid = repo.upsert_entity(self.db, "release", title, mbid=mbid, navidrome_id=f"al-{prefix}", owned=True)[0]
        link_release_group(self.db, rid, fetch=lambda _m: doc(mbid, title, date), now=1.0)
        for number, name in enumerate(names, 1):
            rec = repo.upsert_entity(self.db, "recording", name, navidrome_id=f"{prefix}{number}")[0]
            repo.add_edge(self.db, rec, rid, "appears_on", evidence_class="library_tag",
                          match_quality="fuzzy_unconfirmed", source="navidrome", role=f"1/{number}")

    def albums(self):
        self.release(REL1, "Rumours", "1977-02-04", "a")
        self.release(REL2, "Rumours (Remaster)", "2013-01-29", "b")
        return find_duplicate_albums(self.db)

    def counts(self):
        return self.db.execute("SELECT (SELECT COUNT(*) FROM edges) + (SELECT COUNT(*) FROM entities)").fetchone()[0]

    def test_track_ids_cover_every_edition(self):
        self.assertEqual(edition_track_ids(self.db, self.albums()), ["a1", "a2", "b1", "b2"])

    def test_compares_fully_measured_editions_with_deltas(self):
        albums = self.albums()
        meas = {"a1": m("a1", -9.0, 4.0, -0.2), "a2": m("a2", -9.0, 4.0, -0.2),
                "b1": m("b1", -14.0, 8.0, -1.5), "b2": m("b2", -14.0, 8.0, -1.5)}
        before = self.counts()
        [advice] = advise(self.db, albums, meas).advice
        self.assertEqual(self.counts(), before)
        self.assertTrue(advice.suggestion_only)
        [cmp] = advice.comparisons
        self.assertTrue(cmp.comparable)
        deltas = {d.metric: d for d in cmp.deltas}
        self.assertEqual(deltas["integrated_lufs"].value, -5.0)
        self.assertEqual(deltas["loudness_range_lu"].value, 4.0)
        self.assertTrue(deltas["peak_to_loudness_db"].meaningful)
        self.assertTrue(all(s.startswith("measured ") for s in cmp.statements))
        text = " ".join(cmp.statements).casefold()
        self.assertFalse([w for w in BANNED if w in text])

    def test_small_difference_is_about_the_same(self):
        meas = {i: m(i) for i in ("a1", "a2", "b1", "b2")}
        [advice] = advise(self.db, self.albums(), meas).advice
        [cmp] = advice.comparisons
        self.assertTrue(all(not d.meaningful for d in cmp.deltas))
        self.assertTrue(all("about the same" in s for s in cmp.statements))

    def test_partial_measurement_is_not_compared(self):
        meas = {"a1": m("a1"), "a2": m("a2"), "b1": m("b1")}
        [advice] = advise(self.db, self.albums(), meas).advice
        [cmp] = advice.comparisons
        self.assertFalse(cmp.comparable)
        self.assertEqual(cmp.deltas, ())
        self.assertEqual([r.code for r in cmp.reasons], ["not_fully_measured"])
        self.assertEqual(advice.editions[1].tracks_measured, 1)

    def test_different_tracklists_are_not_compared(self):
        self.release(REL1, "Rumours", "1977-02-04", "a")
        self.release(REL2, "Rumours (Deluxe)", "2013", "b", names=("Dreams", "Gold Dust Woman", "Silver Springs"))
        meas = {i: m(i) for i in ("a1", "a2", "b1", "b2", "b3")}
        [advice] = advise(self.db, find_duplicate_albums(self.db), meas).advice
        [cmp] = advice.comparisons
        self.assertFalse(cmp.comparable)
        self.assertEqual([r.code for r in cmp.reasons], ["tracklists_differ"])

    def test_nothing_measured_is_counted(self):
        report = advise(self.db, self.albums(), {})
        self.assertEqual(report.not_measured, 1)
        self.assertFalse(report.advice[0].comparisons[0].comparable)
        self.assertIsNone(report.advice[0].editions[0].integrated_lufs)

    def test_clipping_counted_and_infinite_values_ignored(self):
        meas = {"a1": m("a1", peak=0.0, count=200), "a2": AudioMeasurement("a2", integrated_lufs=float("-inf"), true_peak_dbfs=-1.0),
                "b1": m("b1"), "b2": m("b2")}
        [advice] = advise(self.db, self.albums(), meas).advice
        first = advice.editions[0]
        self.assertEqual((first.clipped_tracks, first.integrated_lufs), (1, -12.0))
        self.assertIn("clipped tracks", " ".join(advice.comparisons[0].statements))

    def test_accepts_saved_job_dicts(self):
        meas = {i: m(i).as_dict() for i in ("a1", "a2", "b1", "b2")}
        [advice] = advise(self.db, self.albums(), meas).advice
        self.assertTrue(advice.comparisons[0].comparable)


if __name__ == "__main__":
    unittest.main()
