import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import server_v2_phase6_exit as exit_check  # noqa: E402
from intelligence.store import open_store  # noqa: E402
from intelligence.store import repositories as repo  # noqa: E402


class Phase6ExitTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.db = open_store(Path(self.dir.name) / "intelligence.sqlite3")
        self.addCleanup(self.db.close)

    def test_item_checks_pass_on_an_empty_store(self):
        self.assertTrue(exit_check.check_sparse(self.db)["pass"])
        self.assertTrue(exit_check.check_suppression(self.db)["pass"])
        self.assertTrue(exit_check.check_smart_playlists(self.db)["pass"])

    def test_no_taste_reader_outside_the_allowed_packages(self):
        self.assertTrue(exit_check.check_no_weight_effect()["pass"])

    def test_reproducible_check_fails_loudly_without_owned_recordings(self):
        self.assertFalse(exit_check.check_reproducible(self.db)["pass"])

    def test_reproducible_with_owned_recordings(self):
        for n in range(5):
            repo.upsert_entity(self.db, "recording", f"R{n}", mbid=f"f0000000-0000-0000-0000-{n:012d}", owned=True)
        self.db.commit()
        self.assertTrue(exit_check.check_reproducible(self.db)["pass"])


if __name__ == "__main__":
    unittest.main()
