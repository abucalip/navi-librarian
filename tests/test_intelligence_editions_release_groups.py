import tempfile
import unittest
from pathlib import Path

from intelligence.editions import link_release_group, parse_release, sweep_owned_releases
from intelligence.store import open_store
from intelligence.store import repositories as repo

REL1 = "11111111-1111-1111-1111-111111111111"
REL2 = "22222222-2222-2222-2222-222222222222"
REL3 = "33333333-3333-3333-3333-333333333333"
RG1 = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
RG2 = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def doc(release=REL1, group=RG1, title="Rumours", **over):
    base = {
        "id": release, "title": title, "date": "1977-02-04", "country": "GB", "status": "Official",
        "release-group": {"id": group, "title": title, "primary-type": "Album",
                          "secondary-types": ["Live"], "first-release-date": "1977-02-04"},
    }
    base.update(over)
    return base


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db = open_store(Path(self._tmp.name) / "v2.sqlite3")
        self.addCleanup(self.db.close)

    def release(self, mbid=REL1, owned=True, nav="al-1"):
        return repo.upsert_entity(self.db, "release", "Rumours", mbid=mbid, navidrome_id=nav, owned=owned)[0]


class ParseTests(unittest.TestCase):
    def test_reads_group_facts(self):
        info = parse_release(doc(), REL1)
        self.assertEqual((info.group_mbid, info.group_title, info.primary_type), (RG1, "Rumours", "Album"))
        self.assertEqual(info.secondary_types, ("Live",))
        self.assertEqual((info.date, info.country, info.status), ("1977-02-04", "GB", "Official"))

    def test_other_release_is_refused(self):
        self.assertIsNone(parse_release(doc(release=REL2), REL1))

    def test_missing_or_malformed_group_is_refused(self):
        self.assertIsNone(parse_release({"id": REL1}, REL1))
        self.assertIsNone(parse_release(doc(**{"release-group": {"id": "nope", "title": "x"}}), REL1))
        self.assertIsNone(parse_release(doc(**{"release-group": {"id": RG1, "title": " "}}), REL1))

    def test_uppercase_ids_are_normalized(self):
        self.assertEqual(parse_release(doc(group=RG1.upper()), REL1).group_mbid, RG1)


class LinkTests(Base):
    def test_links_and_records_evidence(self):
        rid = self.release()
        out = link_release_group(self.db, rid, fetch=lambda m: doc(), now=1.0)
        self.assertEqual(out.outcome, "linked")
        (edge,) = repo.edges_from(self.db, rid, "member_of")
        self.assertEqual((edge["evidence_class"], edge["match_quality"], edge["source"]),
                         ("source_explicit", "exact_mbid", "musicbrainz"))
        self.assertIsNotNone(edge["observation_id"])
        group = repo.get_entity(self.db, edge["to_id"])
        self.assertEqual((group["type"], group["mbid"], group["owned"]), ("release_group", RG1, 0))

    def test_repeat_is_idempotent(self):
        rid = self.release()
        link_release_group(self.db, rid, fetch=lambda m: doc(), now=1.0)
        again = link_release_group(self.db, rid, fetch=lambda m: doc(), now=2.0)
        self.assertEqual(again.outcome, "already_linked")
        self.assertEqual(len(repo.edges_from(self.db, rid, "member_of")), 1)

    def test_two_releases_share_one_group(self):
        a, b = self.release(REL1, nav="al-1"), self.release(REL2, nav="al-2")
        link_release_group(self.db, a, fetch=lambda m: doc(m), now=1.0)
        link_release_group(self.db, b, fetch=lambda m: doc(m), now=1.0)
        ga = repo.edges_from(self.db, a, "member_of")[0]["to_id"]
        gb = repo.edges_from(self.db, b, "member_of")[0]["to_id"]
        self.assertEqual(ga, gb)

    def test_conflict_keeps_existing_link(self):
        rid = self.release()
        link_release_group(self.db, rid, fetch=lambda m: doc(), now=1.0)
        out = link_release_group(self.db, rid, fetch=lambda m: doc(group=RG2), now=2.0)
        self.assertEqual(out.outcome, "conflict")
        (edge,) = repo.edges_from(self.db, rid, "member_of")
        self.assertEqual(repo.get_entity(self.db, edge["to_id"])["mbid"], RG1)
        self.assertIsNone(repo.find_entity(self.db, "release_group", mbid=RG2))

    def test_provider_failure_writes_nothing(self):
        rid = self.release()

        def boom(_):
            raise TimeoutError("slow")

        out = link_release_group(self.db, rid, fetch=boom, now=1.0)
        self.assertEqual(out.outcome, "deferred")
        self.assertEqual(repo.edges_from(self.db, rid), [])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 0)

    def test_not_found_and_invalid_write_nothing(self):
        rid = self.release()
        self.assertEqual(link_release_group(self.db, rid, fetch=lambda m: None, now=1.0).outcome, "not_found")
        self.assertEqual(link_release_group(self.db, rid, fetch=lambda m: doc(release=REL2), now=1.0).outcome, "invalid")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 0)

    def test_release_without_mbid_is_not_looked_up(self):
        rid = repo.upsert_entity(self.db, "release", "No tag", navidrome_id="al-9", owned=True)[0]
        calls = []
        out = link_release_group(self.db, rid, fetch=lambda m: calls.append(m), now=1.0)
        self.assertEqual((out.outcome, calls), ("invalid", []))

    def test_wrong_entity_type_is_rejected(self):
        artist = repo.upsert_entity(self.db, "artist", "A", mbid=REL3)[0]
        with self.assertRaises(ValueError):
            link_release_group(self.db, artist, fetch=lambda m: doc(), now=1.0)


class SweepTests(Base):
    def test_only_owned_unlinked_mbid_releases(self):
        owned = self.release(REL1, nav="a")
        self.release(REL2, owned=False, nav="b")
        repo.upsert_entity(self.db, "release", "No tag", navidrome_id="c", owned=True)
        seen = []
        res = sweep_owned_releases(self.db, fetch=lambda m: seen.append(m) or doc(m), now=1.0)
        self.assertEqual((seen, res.linked, res.looked_up, res.remaining), ([REL1], 1, 1, 0))
        self.assertEqual(len(repo.edges_from(self.db, owned, "member_of")), 1)
        again = sweep_owned_releases(self.db, fetch=lambda m: seen.append(m), now=2.0)
        self.assertEqual((again.looked_up, len(seen)), (0, 1))

    def test_limit_bounds_lookups(self):
        for i, m in enumerate((REL1, REL2, REL3)):
            self.release(m, nav=f"al-{i}")
        res = sweep_owned_releases(self.db, fetch=lambda m: doc(m), now=1.0, limit=2)
        self.assertEqual((res.looked_up, res.linked, res.remaining), (2, 2, 1))

    def test_outage_stops_early_and_keeps_remainder(self):
        for i, m in enumerate((REL1, REL2, REL3)):
            self.release(m, nav=f"al-{i}")
        calls = []

        def fetch(m):
            calls.append(m)
            raise ConnectionError("down")

        res = sweep_owned_releases(self.db, fetch=fetch, now=1.0)
        self.assertEqual((len(calls), res.deferred, res.remaining), (1, 1, 2))
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM edges").fetchone()[0], 0)

    def test_bad_limit(self):
        with self.assertRaises(ValueError):
            sweep_owned_releases(self.db, fetch=lambda m: None, now=1.0, limit=0)


if __name__ == "__main__":
    unittest.main()
