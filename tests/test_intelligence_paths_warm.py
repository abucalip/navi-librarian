import tempfile
import unittest
from pathlib import Path

from intelligence.graph.paths import PATH_KINDS
from intelligence.graph.paths_warm import JOB, run_paths_warm
from intelligence.jobs import runner
from intelligence.store import open_store
from intelligence.store import repositories as repo


class PathsWarmTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = open_store(Path(self._tmp.name) / "w.sqlite3")
        for n in range(1, 4):
            repo.upsert_entity(self.db, "artist", f"A{n}", mbid=f"e0000000-0000-0000-0000-{n:012d}", owned=True)
        repo.upsert_entity(self.db, "artist", "Other", mbid="e0000000-0000-0000-0000-0000000000ff", owned=False)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def cached(self):
        return self.db.execute("SELECT COUNT(*) FROM insights WHERE kind LIKE 'path:%'").fetchone()[0]

    def test_builds_every_owned_artist_and_kind_once(self):
        result = run_paths_warm(self.db)
        self.assertEqual(result.state, "succeeded")
        self.assertEqual(self.cached(), 3 * len(PATH_KINDS))
        self.assertEqual(result.progress["built"] + result.progress["empty"], 3 * len(PATH_KINDS))
        self.assertEqual(result.progress["pending"], 0)

    def test_second_run_rebuilds_nothing(self):
        run_paths_warm(self.db)
        again = run_paths_warm(self.db)
        self.assertEqual(again.progress["skipped"], 3 * len(PATH_KINDS))
        self.assertEqual(again.progress["built"] + again.progress["empty"], 0)

    def test_kinds_are_limited_and_validated(self):
        run_paths_warm(self.db, kinds=("label_path",))
        self.assertEqual(self.cached(), 3)
        with self.assertRaises(ValueError):
            run_paths_warm(self.db, kinds=("nonsense",))

    def test_time_budget_stops_early_and_resumes(self):
        ticks = iter(range(0, 10_000))
        # each clock() call advances 1 s; a 4 s budget cannot finish 15 builds
        early = run_paths_warm(self.db, max_seconds=4, clock=lambda: float(next(ticks)))
        self.assertEqual(early.state, "queued")
        self.assertGreater(early.progress["pending"], 0)
        done = run_paths_warm(self.db, max_seconds=300)
        self.assertEqual(done.state, "succeeded")
        self.assertEqual(self.cached(), 3 * len(PATH_KINDS))
        self.assertEqual(runner.status(self.db, JOB)["state"], "succeeded")


if __name__ == "__main__":
    unittest.main()
