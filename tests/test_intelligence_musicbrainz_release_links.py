import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from intelligence.musicbrainz import archive_filter, dump, release_links as rl
from intelligence.store import repositories as repo
from intelligence.store.db import open_store

MB = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="musicbrainz_dump")


class FakeDump:
    def __init__(self, tables):
        self.tables = tables

    def __call__(self, wanted):
        for name in wanted:
            if name in self.tables:
                yield name, iter(self.tables[name])


class FakeStream:
    """Stands in for the archive filter: the same filtering over lists of integer rows."""

    def __init__(self, track, credit):
        self.tables = {"track": track, "artist_credit_name": credit}
        self.calls = []

    def __call__(self, table, key, keep, take):
        self.calls.append(table)
        return [tuple(row[i] for i in take) for row in self.tables[table] if row[key] in keep]


def tables():
    """Recording 20 (credited as an instrumentalist) is on a release group twice, on a bootleg and on a compilation."""
    return {
        "recording": [{"id": "20", "gid": "r-1"}, {"id": "21", "gid": "r-2"}],
        "medium": [{"id": "100", "release": "30"}, {"id": "101", "release": "31"}, {"id": "102", "release": "32"},
                   {"id": "103", "release": "33"}],
        "release_status": [{"id": "1", "name": "Official"}, {"id": "2", "name": "Bootleg"}],
        "release": [
            {"id": "30", "gid": "rel-30", "name": "Early", "artist_credit": "900", "release_group": "500", "status": "1"},
            {"id": "31", "gid": "rel-31", "name": "Reissue", "artist_credit": "900", "release_group": "500", "status": "1"},
            {"id": "32", "gid": "rel-32", "name": "Bootleg", "artist_credit": "900", "release_group": "501", "status": "2"},
            {"id": "33", "gid": "rel-33", "name": "Hits", "artist_credit": "901", "release_group": "502", "status": "1"},
        ],
        "artist": [{"id": "5", "gid": "l-1", "name": "Leader One", "sort_name": "One, Leader"},
                   {"id": "6", "gid": rl.VARIOUS_ARTISTS, "name": "Various Artists", "sort_name": "Various Artists"}],
        "iso_3166_1": [{"area": "222", "code": "US"}],
        "release_country": [
            {"release": "30", "country": "222", "date_year": "1959", "date_month": "8", "date_day": "17"},
            {"release": "31", "country": "222", "date_year": "1962", "date_month": None, "date_day": None}],
        "release_unknown_country": [],
    }


def stream():
    # (id, gid, recording, medium) ... only the columns the filter reads: recording at 2, medium at 3
    track = [(1, 0, 20, 100), (2, 0, 20, 101), (3, 0, 20, 102), (4, 0, 20, 103), (5, 0, 21, 100), (6, 0, 99, 100)]
    credit = [(900, 0, 5), (901, 0, 6), (902, 0, 5)]
    return FakeStream(track, credit)


def new_store(*, recording_roles=(("r-1", "instrument"), ("r-2", "composer"))):
    db = open_store(":memory:")
    anchor, _ = repo.upsert_entity(db, "artist", "Anchor", mbid="a-gid", owned=True)
    for gid, relation in recording_roles:
        rec, _ = repo.upsert_entity(db, "recording", gid, mbid=gid)
        repo.add_edge(db, anchor, rec, relation, **MB)
    return db, anchor


def run(db, tbl=None, fake=None, **kw):
    return rl.build_release_links(db, FakeDump(tbl or tables()), fake or stream(),
                                  dump_timestamp="2026-11-04", schema_sequence=31, **kw)


def edges(db, relation):
    return db.execute("SELECT * FROM edges WHERE relation = ?", (relation,)).fetchall()


class CreditedRecordingTests(unittest.TestCase):
    def test_only_performer_and_producer_credits_count(self):
        db, _ = new_store(recording_roles=(("r-1", "instrument"), ("r-2", "composer"), ("r-3", "producer"),
                                           ("r-4", "recording engineer")))
        self.assertEqual(set(rl.credited_recordings(db)), {"r-1", "r-3"})

    def test_a_credit_from_an_unowned_artist_does_not_count(self):
        db, _ = new_store(recording_roles=())
        other, _ = repo.upsert_entity(db, "artist", "Other", mbid="o-gid")
        rec, _ = repo.upsert_entity(db, "recording", "r-9", mbid="r-9")
        repo.add_edge(db, other, rec, "instrument", **MB)
        self.assertEqual(rl.credited_recordings(db), {})

    def test_inferred_and_unresolved_credits_do_not_count(self):
        db, anchor = new_store(recording_roles=())
        rec, _ = repo.upsert_entity(db, "recording", "r-8", mbid="r-8")
        repo.add_edge(db, anchor, rec, "instrument", evidence_class="inferred", match_quality="exact_mbid", source="x")
        self.assertEqual(rl.credited_recordings(db), {})


class PlanAndStoreTests(unittest.TestCase):
    def setUp(self):
        self.db, self.anchor = new_store()
        self.result = run(self.db)

    def entity(self, kind, gid):
        return repo.find_entity(self.db, kind, mbid=gid)

    def test_one_official_release_per_group_the_earliest(self):
        rec = self.entity("recording", "r-1")
        targets = [self.db.execute("SELECT mbid FROM entities WHERE id = ?", (e["to_id"],)).fetchone()[0]
                   for e in repo.edges_from(self.db, rec["id"], rl.REL_TRACK_ON)]
        self.assertEqual(targets, ["rel-30"])  # not the 1962 reissue, the bootleg or the compilation

    def test_a_recording_without_a_performer_credit_gets_no_release(self):
        self.assertEqual(repo.edges_from(self.db, self.entity("recording", "r-2")["id"], rl.REL_TRACK_ON), [])

    def test_leader_edge_and_names(self):
        release = self.entity("release", "rel-30")
        leaders = repo.edges_from(self.db, release["id"], rl.REL_RELEASE_ARTIST)
        self.assertEqual(len(leaders), 1)
        leader = repo.get_entity(self.db, leaders[0]["to_id"])
        self.assertEqual((leader["mbid"], leader["canonical_name"], leader["sort_name"], leader["owned"]),
                         ("l-1", "Leader One", "One, Leader", 0))

    def test_compilations_and_other_editions_are_not_stored(self):
        for gid in ("rel-31", "rel-32", "rel-33"):
            self.assertIsNone(self.entity("release", gid))
        self.assertIsNone(self.entity("artist", rl.VARIOUS_ARTISTS))

    def test_release_facts_come_from_the_dump(self):
        row = self.db.execute("SELECT * FROM release_facts WHERE entity_id = ?",
                              (self.entity("release", "rel-30")["id"],)).fetchone()
        self.assertEqual((row["date"], row["country"], row["status"]), ("1959-08-17", "US", "official"))

    def test_edges_are_dump_grade_with_their_own_source(self):
        for row in self.db.execute("SELECT * FROM edges WHERE relation IN (?, ?)", (rl.REL_TRACK_ON, rl.REL_RELEASE_ARTIST)):
            self.assertEqual((row["evidence_class"], row["match_quality"], row["source"]),
                             ("source_explicit", "exact_mbid", rl.SOURCE))
            self.assertTrue(row["source_url"].startswith("https://musicbrainz.org/release/"))
            self.assertIsNotNone(row["observation_id"])

    def test_library_relations_are_never_written(self):
        self.assertEqual(edges(self.db, "appears_on"), [])
        self.assertEqual(edges(self.db, "credited_to"), [])

    def test_counts(self):
        self.assertEqual(self.result.edges_created, 2)
        self.assertEqual(self.result.entities_created, {"release": 1, "artist": 1})
        self.assertEqual(self.result.plan["compilation_only_releases_skipped"], 1)
        self.assertEqual(self.result.plan["credited_recordings"], 1)

    def test_rerun_changes_nothing(self):
        again = run(self.db)
        self.assertEqual((again.edges_created, again.edges_existing, again.edges_removed), (0, 2, 0))
        self.assertEqual(again.entities_created, {})


class ExistingEntityTests(unittest.TestCase):
    def test_an_owned_release_is_matched_by_mbid_not_duplicated_or_unowned(self):
        db, _ = new_store()
        owned, _ = repo.upsert_entity(db, "release", "My copy", mbid="rel-30", owned=True)
        db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, '1960')", (owned,))
        result = run(db)
        rows = db.execute("SELECT id, owned, canonical_name FROM entities WHERE type = 'release'").fetchall()
        self.assertEqual([(r["id"], r["owned"], r["canonical_name"]) for r in rows], [(owned, 1, "My copy")])
        self.assertEqual(db.execute("SELECT date FROM release_facts WHERE entity_id = ?", (owned,)).fetchone()[0], "1960")
        self.assertNotIn("release", result.entities_created)

    def test_an_existing_leader_artist_is_reused(self):
        db, _ = new_store()
        leader, _ = repo.upsert_entity(db, "artist", "Known", mbid="l-1")
        run(db)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM entities WHERE mbid = 'l-1'").fetchone()[0], 1)
        self.assertEqual(repo.get_entity(db, leader)["canonical_name"], "Known")


class ReplacementTests(unittest.TestCase):
    def test_edges_that_left_the_dump_are_removed_with_their_orphans(self):
        db, _ = new_store(recording_roles=(("r-1", "instrument"), ("r-2", "instrument")))
        tbl = tables()
        tbl["medium"].append({"id": "104", "release": "34"})
        tbl["release"].append({"id": "34", "gid": "rel-34", "name": "Other", "artist_credit": "902",
                               "release_group": "503", "status": "1"})
        tbl["recording"].append({"id": "22", "gid": "r-3"})
        fake = stream()
        fake.tables["track"].append((7, 0, 21, 104))
        run(db, tbl, fake)
        self.assertEqual(len(edges(db, rl.REL_TRACK_ON)), 3)
        # the next dump no longer lists the track on release 34
        fake2 = stream()
        run(db, tbl, fake2, min_retained=0.1)
        self.assertEqual(len(edges(db, rl.REL_TRACK_ON)), 2)
        self.assertIsNone(repo.find_entity(db, "release", mbid="rel-34"))
        self.assertIsNotNone(repo.find_entity(db, "release", mbid="rel-30"))

    def test_a_run_that_keeps_too_little_is_refused_and_rolled_back(self):
        db, _ = new_store()
        run(db)
        empty = tables()
        empty["release"] = []
        with self.assertRaises(rl.SliceValidationError):
            run(db, empty)
        self.assertEqual(len(edges(db, rl.REL_TRACK_ON)), 1)

    def test_no_credited_recordings_is_an_empty_plan(self):
        db, _ = new_store(recording_roles=())
        fake = stream()
        result = run(db, fake=fake)
        self.assertEqual((result.edges_created, fake.calls), (0, []))


def _archive(directory, members):
    path = Path(directory) / "mbdump.tar.bz2"
    with tarfile.open(path, "w:bz2") as tar:
        for name, text in [("TIMESTAMP", "2026-11-04\n"), ("SCHEMA_SEQUENCE", "31\n"), *members]:
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


class ArchiveFilterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        track = "".join(f"{i}\tg{i}\t{rec}\t{medium}\t1\t1\tname\t5\t\\N\t0\t\\N\tf\n"
                        for i, (rec, medium) in enumerate([(20, 100), (21, 101), (20, 102), (22, 103)], 1))
        track += "broken line\nx\ty\tnot-a-number\t4\n"
        self.path = _archive(self.tmp.name, [("mbdump/area", "1\n"), ("mbdump/track", track)])

    def run_filter(self, keep, **kw):
        return archive_filter.filter_table(self.path, "track", archive_filter.TRACK_RECORDING, keep,
                                           (archive_filter.TRACK_RECORDING, archive_filter.TRACK_MEDIUM),
                                           workers=2, parallel=False, **kw)

    def test_keeps_matching_rows_in_archive_order_and_only_the_asked_columns(self):
        self.assertEqual(self.run_filter({20, 22}), [(20, 100), (20, 102), (22, 103)])

    def test_malformed_rows_are_skipped_not_guessed_at(self):
        self.assertEqual(self.run_filter({20, 21, 22}), [(20, 100), (21, 101), (20, 102), (22, 103)])

    def test_nothing_wanted_gives_nothing(self):
        self.assertEqual(self.run_filter(set()), [])

    def test_progress_ends_at_one(self):
        seen = []
        self.run_filter({20}, on_progress=seen.append)
        self.assertEqual(seen[-1], 1.0)

    def test_a_missing_table_is_an_error(self):
        with self.assertRaises(dump.DumpError):
            archive_filter.filter_table(self.path, "artist_credit_name", 0, {1}, (0,), workers=2, parallel=False)

    def test_blocks_split_mid_line_still_give_whole_rows(self):
        old = archive_filter.BLOCK_BYTES
        archive_filter.BLOCK_BYTES = 16
        self.addCleanup(setattr, archive_filter, "BLOCK_BYTES", old)
        self.assertEqual(self.run_filter({20, 21, 22}), [(20, 100), (21, 101), (20, 102), (22, 103)])


if __name__ == "__main__":
    unittest.main()
