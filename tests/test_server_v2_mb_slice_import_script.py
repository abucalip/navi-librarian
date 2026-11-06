import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import server_v2_mb_slice_import as script  # noqa: E402
from intelligence.jobs.runner import RunResult  # noqa: E402
from intelligence.store import open_store, repositories as repo  # noqa: E402


class SliceImportScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = Path(self.tmp.name) / "data"

    def test_plan_reports_seeds_and_budgets_without_running_the_job(self):
        self.data.mkdir()
        db = open_store(self.data / script.STORE_FILE)
        repo.upsert_entity(db, "artist", "Alpha", mbid="a-gid", owned=True)
        db.close()
        with mock.patch.object(script.job, "run_slice_import") as run_job:
            report = script.run(self.data, self.data / "s", plan_only=True, export=None, cover_art=False,
                                keep_archive=False, hops=2)
        run_job.assert_not_called()
        self.assertEqual(report["seeds"]["artist"], 1)
        self.assertEqual(report["budgets"]["download_bytes"], 7_900_000_000)
        self.assertFalse((self.data / "s").exists())

    def test_run_passes_options_to_the_job_and_reports_its_result(self):
        result = RunResult(1, "succeeded", {"outcome": "loaded"})
        with mock.patch.object(script.job, "run_slice_import", return_value=result) as run_job:
            report = script.run(self.data, self.data / "s", plan_only=False, export="2026-11-04", cover_art=True,
                                keep_archive=True, hops=1)
        kwargs = run_job.call_args.kwargs
        self.assertEqual((kwargs["export"], kwargs["include_cover_art"], kwargs["delete_archive"], kwargs["hops"]),
                         ("2026-11-04", True, False, 1))
        self.assertEqual(report, {"state": "succeeded", "error": None, "progress": {"outcome": "loaded"}})
        self.assertTrue((self.data / "s").is_dir())

    def test_ingest_library_records_owned_artists_with_mbid_only(self):
        calls = []

        def fake_nd(method, **params):
            calls.append(method)
            if method == "getArtists":
                return {"artists": {"index": [{"artist": [
                    {"id": "1", "name": "Alpha", "musicBrainzId": "11111111-1111-4111-8111-111111111111"},
                    {"id": "2", "name": "No Mbid"},
                    {"id": "3", "name": "Various Artists", "musicBrainzId": "22222222-2222-4222-8222-222222222222"}]}]}}
            if method == "getArtist":
                return {"artist": {"album": [{"id": "10"}]}}
            return {"album": {"id": "10", "name": "First", "artist": "Alpha", "artistId": "1",
                              "musicBrainzId": "33333333-3333-4333-8333-333333333333", "song": []}}

        db = open_store(":memory:")
        report = script.ingest_library(db, now=1.0, nd=fake_nd, log=lambda *a, **k: None)
        self.assertEqual(report, {"artists_with_mbid": 1, "albums_ingested": 1})
        self.assertEqual(calls.count("getArtist"), 1)
        self.assertTrue(script.neighbourhood.owned_seeds(db)["artist"])

    def test_api_fill_flag_runs_the_fill_not_the_import(self):
        done = RunResult(1, "succeeded", {"requests": 0})
        with mock.patch.object(script.api_fill, "run_api_fill", return_value=done) as fill, \
                mock.patch.object(script.job, "run_slice_import") as imp:
            code = script.main(["--data-dir", str(self.data), "--api-fill", "--max-requests", "7"])
        self.assertEqual(code, 0)
        fill.assert_called_once()
        self.assertEqual(fill.call_args.kwargs["max_requests"], 7)
        imp.assert_not_called()

    def test_main_exit_code_follows_job_state(self):
        failed = RunResult(1, "failed", {}, "boom")
        with mock.patch.object(script.job, "run_slice_import", return_value=failed):
            code = script.main(["--data-dir", str(self.data)])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
