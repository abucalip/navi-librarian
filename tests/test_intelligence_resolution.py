import tempfile
import unittest
from pathlib import Path

from intelligence.resolution import LibraryRef, add_isrc, resolve
from intelligence.resolution import normalize as n
from intelligence.resolution import unresolved as q
from intelligence.store import generations, open_store
from intelligence.store import repositories as repo

MB1 = "11111111-1111-1111-1111-111111111111"
MB2 = "22222222-2222-2222-2222-222222222222"
MB3 = "33333333-3333-3333-3333-333333333333"


class NormalizeTests(unittest.TestCase):
    def test_text_ignores_case_accents_punctuation_and_spacing(self):
        self.assertEqual(n.normalize_text("  Beyoncé — Lemonade! "), "beyonce lemonade")
        self.assertEqual(n.normalize_text("Guns N' Roses"), "guns n roses")
        self.assertEqual(n.normalize_text("Simon & Garfunkel"), n.normalize_text("Simon and Garfunkel"))
        self.assertEqual(n.normalize_text("AC/DC"), "acdc")
        self.assertEqual(n.normalize_text(None), "")
        self.assertEqual(n.normalize_text("Sigur Rós"), "sigur ros")

    def test_non_latin_letters_are_kept(self):
        self.assertEqual(n.normalize_text("久石譲"), "久石譲")

    def test_artist_key_drops_leading_the_only(self):
        self.assertEqual(n.artist_key("The Beatles"), n.artist_key("Beatles"))
        self.assertEqual(n.artist_key("The"), "the")
        self.assertEqual(n.artist_key("Theo"), "theo")

    def test_title_key_keeps_edition_words(self):
        self.assertNotEqual(n.title_key("Rumours"), n.title_key("Rumours (Deluxe Edition)"))

    def test_edition_markers(self):
        self.assertEqual(n.edition_markers("Rumours (Deluxe Edition) [2011 Remaster]"), ["deluxe", "remaster"])
        self.assertEqual(n.edition_markers("Rumours"), [])
        self.assertEqual(n.edition_markers(None), [])

    def test_mbid_and_isrc(self):
        self.assertEqual(n.normalize_mbid(" " + MB1.upper() + " "), MB1)
        self.assertIsNone(n.normalize_mbid("not-a-uuid"))
        self.assertIsNone(n.normalize_mbid(None))
        self.assertEqual(n.normalize_isrc("us-abc-12-34567"), "USABC1234567")
        self.assertIsNone(n.normalize_isrc("USABC123"))
        self.assertIsNone(n.normalize_isrc(None))

    def test_durations_match(self):
        self.assertTrue(n.durations_match(200000, 202999))
        self.assertFalse(n.durations_match(200000, 203001))
        self.assertFalse(n.durations_match(None, 1))


class ResolutionTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db = open_store(Path(self.temp_dir.name) / "intelligence.sqlite3")
        self.addCleanup(self.db.close)

    def album(self, **kw):
        base = {"kind": "release", "navidrome_ref": "alb-1", "artist": "Fleetwood Mac", "title": "Rumours",
                "track_count": 2, "durations_ms": (200000, 250000)}
        base.update(kw)
        return LibraryRef(**base)

    @staticmethod
    def cand(mbid, **kw):
        base = {"mbid": mbid, "artist": "Fleetwood Mac", "title": "Rumours", "track_count": 2,
                "durations_ms": [201000, 249000]}
        base.update(kw)
        return base


class MbidTagTests(ResolutionTestCase):
    def test_tag_is_trusted_and_creates_owned_entity(self):
        res = resolve(self.db, self.album(mbid=MB1.upper()), now=1.0)
        self.assertEqual((res.outcome, res.rung, res.match_quality, res.evidence_class),
                         ("resolved", "mbid_tag", "exact_mbid", "library_tag"))
        entity = repo.get_entity(self.db, res.entity_id)
        self.assertEqual((entity["type"], entity["mbid"], entity["navidrome_id"], entity["owned"]),
                         ("release", MB1, "alb-1", 1))

    def test_tag_never_calls_search(self):
        def boom(_):
            raise AssertionError("search must not run")
        self.assertEqual(resolve(self.db, self.album(mbid=MB1), now=1.0, search=boom).outcome, "resolved")

    def test_repeat_is_idempotent(self):
        first = resolve(self.db, self.album(mbid=MB1), now=1.0)
        second = resolve(self.db, self.album(mbid=MB1), now=2.0)
        self.assertEqual(first.entity_id, second.entity_id)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 1)

    def test_malformed_tag_falls_through_to_the_queue(self):
        res = resolve(self.db, self.album(mbid="garbage"), now=1.0)
        self.assertEqual(res.outcome, "unresolved")

    def test_release_and_release_group_with_same_mbid_stay_separate(self):
        a = resolve(self.db, self.album(mbid=MB1), now=1.0)
        b = resolve(self.db, self.album(kind="release_group", navidrome_ref="alb-1", mbid=MB1), now=1.0)
        self.assertNotEqual(a.entity_id, b.entity_id)

    def test_item_already_linked_to_another_mbid_is_a_conflict(self):
        resolve(self.db, self.album(mbid=MB1), now=1.0)
        res = resolve(self.db, self.album(mbid=MB2), now=2.0)
        self.assertEqual(res.outcome, "unresolved")
        self.assertIn("different MBID", res.reason)
        self.assertEqual(repo.find_entity(self.db, "release", navidrome_id="alb-1")["mbid"], MB1)

    def test_mbid_linked_to_another_item_is_not_overwritten(self):
        first = resolve(self.db, self.album(mbid=MB1), now=1.0)
        second = resolve(self.db, self.album(navidrome_ref="alb-2", mbid=MB1), now=2.0)
        self.assertEqual(second.entity_id, first.entity_id)
        self.assertEqual(repo.get_entity(self.db, first.entity_id)["navidrome_id"], "alb-1")


class IsrcTests(ResolutionTestCase):
    def track(self, **kw):
        base = {"kind": "recording", "navidrome_ref": "trk-1", "isrc": "USABC1234567",
                "artist": "A", "title": "T"}
        base.update(kw)
        return LibraryRef(**base)

    def test_unique_isrc_resolves(self):
        eid, _ = repo.upsert_entity(self.db, "recording", "T", mbid=MB1)
        add_isrc(self.db, eid, "us-abc-12-34567")
        res = resolve(self.db, self.track(), now=1.0)
        self.assertEqual((res.outcome, res.rung, res.match_quality, res.entity_id), ("resolved", "isrc", "isrc", eid))
        self.assertEqual(repo.get_entity(self.db, eid)["navidrome_id"], "trk-1")

    def test_two_recordings_with_same_isrc_are_queued(self):
        for mbid in (MB1, MB2):
            eid, _ = repo.upsert_entity(self.db, "recording", "T", mbid=mbid)
            add_isrc(self.db, eid, "USABC1234567")
        res = resolve(self.db, self.track(), now=1.0)
        self.assertEqual(res.outcome, "unresolved")
        self.assertEqual({c["mbid"] for c in res.candidates}, {MB1, MB2})

    def test_isrc_naming_a_recording_owned_by_another_item_is_queued(self):
        eid, _ = repo.upsert_entity(self.db, "recording", "T", mbid=MB1, navidrome_id="other")
        add_isrc(self.db, eid, "USABC1234567")
        self.assertEqual(resolve(self.db, self.track(), now=1.0).outcome, "unresolved")
        self.assertEqual(repo.get_entity(self.db, eid)["navidrome_id"], "other")

    def test_isrc_is_ignored_for_albums(self):
        eid, _ = repo.upsert_entity(self.db, "recording", "T", mbid=MB1)
        add_isrc(self.db, eid, "USABC1234567")
        self.assertEqual(resolve(self.db, self.album(isrc="USABC1234567"), now=1.0).outcome, "unresolved")

    def test_add_isrc_rejects_garbage(self):
        eid, _ = repo.upsert_entity(self.db, "recording", "T", mbid=MB1)
        with self.assertRaises(ValueError):
            add_isrc(self.db, eid, "nope")


class SearchTests(ResolutionTestCase):
    def test_single_clearing_candidate_is_accepted_as_fuzzy_confirmed(self):
        res = resolve(self.db, self.album(), now=1.0, search=lambda r: [self.cand(MB1)])
        self.assertEqual((res.outcome, res.rung, res.match_quality, res.evidence_class),
                         ("resolved", "search", "fuzzy_confirmed", "derived"))
        self.assertEqual(repo.get_entity(self.db, res.entity_id)["mbid"], MB1)

    def test_first_result_is_never_taken_when_two_clear(self):
        res = resolve(self.db, self.album(), now=1.0, search=lambda r: [self.cand(MB1), self.cand(MB2)])
        self.assertEqual(res.outcome, "unresolved")
        self.assertEqual([c["mbid"] for c in res.candidates], [MB1, MB2])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 0)

    def test_one_failing_check_leaves_one_passing_candidate(self):
        found = [self.cand(MB1), self.cand(MB2, track_count=3), self.cand(MB3, durations_ms=[100000, 250000])]
        res = resolve(self.db, self.album(), now=1.0, search=lambda r: found)
        self.assertEqual((res.outcome, res.entity_id is not None), ("resolved", True))
        self.assertEqual(res.mbid, MB1)

    def test_edition_differences_do_not_silently_merge(self):
        res = resolve(self.db, self.album(), now=1.0,
                      search=lambda r: [self.cand(MB1, title="Rumours (Deluxe Edition)")])
        self.assertEqual(res.outcome, "unresolved")

    def test_artist_spelling_variants_still_match(self):
        res = resolve(self.db, self.album(artist="The Fleetwood Mac"), now=1.0, search=lambda r: [self.cand(MB1)])
        self.assertEqual(res.outcome, "resolved")

    def test_missing_candidate_data_fails_the_check(self):
        res = resolve(self.db, self.album(), now=1.0, search=lambda r: [self.cand(MB1, durations_ms=None)])
        self.assertEqual(res.outcome, "unresolved")

    def test_names_alone_are_not_enough(self):
        res = resolve(self.db, self.album(track_count=None, durations_ms=()), now=1.0,
                      search=lambda r: [self.cand(MB1)])
        self.assertEqual(res.outcome, "unresolved")
        self.assertIn("names alone", res.reason)

    def test_missing_artist_or_title_is_unresolved(self):
        res = resolve(self.db, self.album(artist=None), now=1.0, search=lambda r: [self.cand(MB1)])
        self.assertEqual(res.outcome, "unresolved")

    def test_candidate_without_valid_mbid_is_ignored(self):
        res = resolve(self.db, self.album(), now=1.0, search=lambda r: [self.cand("bad")])
        self.assertEqual(res.outcome, "unresolved")

    def test_no_search_queues_the_item(self):
        res = resolve(self.db, self.album(), now=1.0)
        self.assertEqual(res.outcome, "unresolved")
        self.assertEqual(q.count_unresolved(self.db), 1)

    def test_provider_failure_defers_and_writes_nothing(self):
        def down(_):
            raise TimeoutError("musicbrainz down")
        before = generations.data_versions(self.db)
        res = resolve(self.db, self.album(), now=1.0, search=down)
        self.assertEqual((res.outcome, res.reason), ("deferred", "search failed: TimeoutError"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM unresolved").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 0)
        self.assertEqual(generations.data_versions(self.db), before)

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve(self.db, self.album(kind="work"), now=1.0)


class QueueTests(ResolutionTestCase):
    def ambiguous(self):
        return resolve(self.db, self.album(), now=1.0, search=lambda r: [self.cand(MB1), self.cand(MB2)])

    def test_queue_is_idempotent_and_refreshes_open_items(self):
        a = self.ambiguous()
        b = self.ambiguous()
        self.assertEqual(a.unresolved_id, b.unresolved_id)
        self.assertEqual(q.count_unresolved(self.db), 1)
        resolve(self.db, self.album(), now=9.0, search=lambda r: [self.cand(MB1), self.cand(MB3)])
        item = q.get_unresolved(self.db, a.unresolved_id)
        self.assertEqual([c["mbid"] for c in item["candidates"]], [MB1, MB3])
        self.assertEqual(item["first_seen"], 1.0)

    def test_data_version_bumps_only_on_change(self):
        self.ambiguous()
        v = generations.data_version(self.db, "unresolved")
        self.ambiguous()
        self.assertEqual(generations.data_version(self.db, "unresolved"), v)

    def test_confirm_resolves_item_as_user_confirmed(self):
        uid = self.ambiguous().unresolved_id
        item = q.confirm_candidate(self.db, uid, MB2.upper())
        self.assertEqual(item["status"], "user_confirmed")
        self.assertEqual(q.confirmed_mbid(item), MB2)
        self.assertEqual(len(item["candidates"]), 2)
        res = resolve(self.db, self.album(), now=5.0, search=lambda r: self.fail("must not search"))
        self.assertEqual((res.outcome, res.rung, res.evidence_class, res.mbid), ("resolved", "user_confirmed", "user_confirmed", MB2))
        self.assertEqual(repo.get_entity(self.db, res.entity_id)["navidrome_id"], "alb-1")

    def test_confirm_requires_an_offered_candidate(self):
        uid = self.ambiguous().unresolved_id
        with self.assertRaises(q.UnresolvedError):
            q.confirm_candidate(self.db, uid, MB3)
        with self.assertRaises(q.UnresolvedError):
            q.confirm_candidate(self.db, uid, "garbage")
        self.assertEqual(q.get_unresolved(self.db, uid)["status"], "open")

    def test_reject_is_final_and_not_requeued(self):
        uid = self.ambiguous().unresolved_id
        q.reject_all(self.db, uid)
        res = resolve(self.db, self.album(), now=5.0, search=lambda r: [self.cand(MB1)])
        self.assertEqual((res.outcome, res.rung), ("unresolved", "user_rejected"))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 0)
        self.assertEqual(q.count_unresolved(self.db, "user_rejected"), 1)

    def test_answered_items_cannot_be_answered_again_but_can_be_reopened(self):
        uid = self.ambiguous().unresolved_id
        q.reject_all(self.db, uid)
        with self.assertRaises(q.UnresolvedError):
            q.confirm_candidate(self.db, uid, MB1)
        item = q.reopen(self.db, uid)
        self.assertEqual(item["status"], "open")
        self.assertEqual(q.confirm_candidate(self.db, uid, MB1)["status"], "user_confirmed")

    def test_reopen_clears_confirmation_mark(self):
        uid = self.ambiguous().unresolved_id
        q.confirm_candidate(self.db, uid, MB1)
        item = q.reopen(self.db, uid)
        self.assertTrue(all("confirmed" not in c for c in item["candidates"]))
        self.assertIsNone(q.confirmed_mbid(item))

    def test_unknown_item(self):
        with self.assertRaises(q.UnresolvedError):
            q.reject_all(self.db, 999)
        self.assertIsNone(q.get_unresolved(self.db, 999))

    def test_listing_filters_and_pages(self):
        for i in range(3):
            resolve(self.db, self.album(navidrome_ref=f"a{i}"), now=float(i))
        resolve(self.db, self.album(kind="recording", navidrome_ref="t0", isrc=None), now=9.0)
        page = q.list_unresolved(self.db, limit=2)
        self.assertEqual(len(page), 2)
        rest = q.list_unresolved(self.db, after_id=page[-1]["id"])
        self.assertEqual(len(rest), 2)
        self.assertEqual(len(q.list_unresolved(self.db, kind="recording")), 1)
        q.reject_all(self.db, page[0]["id"])
        self.assertEqual(len(q.list_unresolved(self.db, status=None)), 4)
        self.assertEqual(len(q.list_unresolved(self.db)), 3)

    def test_rejected_item_keeps_its_reason_and_candidates_when_requeued(self):
        uid = self.ambiguous().unresolved_id
        q.reject_all(self.db, uid)
        before = q.get_unresolved(self.db, uid)
        q.queue_unresolved(self.db, "release", "alb-1", [], "other", now=3.0)
        self.assertEqual(q.get_unresolved(self.db, uid), before)


if __name__ == "__main__":
    unittest.main()
