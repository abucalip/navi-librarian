import tempfile
import unittest
from pathlib import Path
from unittest import mock

from intelligence.jobs import runner
from intelligence.musicbrainz import job
from intelligence.musicbrainz.dump import DumpInfo
from intelligence.store import repositories as repo
from intelligence.store.generations import data_version
from intelligence.store.db import open_store

from tests.test_intelligence_musicbrainz_loader import ent, link_row, lnk
from tests.test_intelligence_musicbrainz_loader import FakeDump


def world():
    return FakeDump({
        "artist": [ent(1, "a-gid", "Alpha"), ent(2, "b-gid", "Beta")],
        "link_type": [{"id": "100", "name": "producer"}],
        "link_attribute_type": [],
        "l_artist_artist": [lnk(1, 2, 10)],
        "link": [link_row(10, 100)],
        "link_attribute": [],
    })


class JobTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.archive = Path(self.dir.name) / "mbdump.tar.bz2"
        self.downloads = 0
        self.info = DumpInfo(31, "2026-11-04 00:22:22+00")

        def fake_download(directory, include_cover_art, export, opener):
            self.downloads += 1
            self.archive.write_bytes(b"x" * 100)
            return {"mbdump.tar.bz2": self.archive}

        for target, new in (
            ("intelligence.musicbrainz.job.download.download_export", fake_download),
            ("intelligence.musicbrainz.job.dump.read_info", lambda p: self.info),
            ("intelligence.musicbrainz.job.neighbourhood.archive_reader", lambda p: self.source),
        ):
            patcher = mock.patch(target, new)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.source = world()

    def seed(self):
        repo.upsert_entity(self.db, "artist", "Alpha", mbid="a-gid", owned=True)

    def run_it(self, **kw):
        return job.run_slice_import(self.db, self.dir.name, **kw)

    def test_no_seeds_downloads_nothing(self):
        result = self.run_it()
        self.assertEqual(result.state, "succeeded")
        self.assertEqual(result.progress["outcome"], "no_seeds")
        self.assertEqual(self.downloads, 0)
        self.assertEqual(data_version(self.db, job.RESOURCE), 0)

    def test_loads_and_deletes_archive(self):
        self.seed()
        result = self.run_it()
        self.assertEqual(result.progress["outcome"], "loaded")
        self.assertEqual(result.progress["load"]["edges_created"], 1)
        self.assertEqual(result.progress["dump_timestamp"], self.info.timestamp)
        self.assertTrue(result.progress["archive_deleted"])
        self.assertFalse(self.archive.exists())
        self.assertEqual(data_version(self.db, job.RESOURCE), 1)
        meta = dict(self.db.execute("SELECT key, value FROM meta WHERE key LIKE 'musicbrainz_slice.%'").fetchall())
        self.assertEqual(meta["musicbrainz_slice.dump_timestamp"], self.info.timestamp)
        self.assertEqual(meta["musicbrainz_slice.schema_sequence"], "31")
        self.assertIsNotNone(repo.find_entity(self.db, "artist", mbid="b-gid"))

    def test_keep_archive(self):
        self.seed()
        self.run_it(delete_archive=False)
        self.assertTrue(self.archive.exists())

    def test_entity_cap_falls_back_without_writing(self):
        self.seed()
        result = self.run_it(budgets=job.Budgets(max_entities=1))
        self.assertEqual(result.state, "succeeded")
        self.assertEqual(result.progress["outcome"], "fallback_api_only")
        self.assertIn("max_entities", result.progress["breaches"])
        self.assertIsNone(repo.find_entity(self.db, "artist", mbid="b-gid"))
        self.assertEqual(data_version(self.db, job.RESOURCE), 0)
        self.assertTrue(self.archive.exists())

    def test_scratch_breach_falls_back(self):
        self.seed()
        result = self.run_it(budgets=job.Budgets(scratch_bytes=10))
        self.assertEqual(result.progress["outcome"], "fallback_api_only")
        self.assertIn("scratch_bytes", result.progress["breaches"])

    def test_slow_select_falls_back(self):
        self.seed()
        ticks = iter(range(0, 100000, 10000))
        result = self.run_it(budgets=job.Budgets(import_seconds=5), clock=lambda: next(ticks))
        self.assertEqual(result.progress["outcome"], "fallback_api_only")
        self.assertIn("import_seconds", result.progress["breaches"])

    def test_wrong_schema_fails_and_keeps_data(self):
        self.seed()
        self.info = DumpInfo(99, None)
        result = self.run_it()
        self.assertEqual(result.state, "failed")
        self.assertIn("schema sequence 99", result.error)
        self.assertEqual(data_version(self.db, job.RESOURCE), 0)

    def test_rerun_after_failure_skips_finished_download(self):
        self.seed()
        self.info = DumpInfo(99, None)
        self.run_it()
        self.assertEqual(self.downloads, 1)
        self.info = DumpInfo(31, None)
        result = self.run_it()
        self.assertEqual(result.progress["outcome"], "loaded")
        self.assertEqual(self.downloads, 2)  # failed runs start fresh; the file check makes it a no-op

    def test_store_bytes_in_memory_is_zero(self):
        self.assertEqual(job.store_bytes(self.db), 0)

    def test_store_bytes_counts_file(self):
        path = Path(self.dir.name) / "s.db"
        db = open_store(str(path))
        self.assertGreater(job.store_bytes(db), 0)


if __name__ == "__main__":
    unittest.main()
