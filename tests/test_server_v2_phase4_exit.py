import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from server_v2_phase4_exit import (  # noqa: E402
    check_ambiguity, check_budgets, check_credits_synthetic, check_provenance, check_traversal_synthetic,
)
from intelligence.store import open_store  # noqa: E402
from intelligence.store import repositories as repo  # noqa: E402


class Phase4ExitTests(unittest.TestCase):
    def test_synthetic_credit_check_passes(self):
        self.assertTrue(check_credits_synthetic()["pass"])

    def test_synthetic_traversal_check_passes(self):
        self.assertTrue(check_traversal_synthetic()["pass"])

    def test_provenance_flags_an_edge_without_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = open_store(Path(tmp) / "p.sqlite3")
            a = repo.upsert_entity(db, "artist", "A", mbid="a0000000-0000-0000-0000-000000000001")[0]
            b = repo.upsert_entity(db, "recording", "R", mbid="b0000000-0000-0000-0000-000000000001")[0]
            repo.add_edge(db, a, b, "performance", source="musicbrainz_dump",
                          evidence_class="source_explicit", match_quality="exact_mbid")
            result = check_provenance(db)
            db.close()
        self.assertFalse(result["pass"])
        self.assertEqual(result["without_observation"], 1)

    def test_ambiguity_check_keeps_homonyms_apart(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = open_store(Path(tmp) / "h.sqlite3")
            for i in (1, 2):
                repo.upsert_entity(db, "artist", "Same Name", mbid=f"a0000000-0000-0000-0000-00000000000{i}")
            result = check_ambiguity(db)
            db.close()
        self.assertTrue(result["pass"])
        self.assertEqual(result["homonym_groups_in_slice"], 1)

    def test_budget_check_reads_the_import_report(self):
        report = {"progress": {"outcome": "loaded", "archive_bytes": 1, "scratch_bytes": 1, "slice_bytes": 1,
                               "import_seconds": 1.0, "load": {"by_type": {"artist": 1}}}}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            path.write_text(json.dumps(report))
            self.assertTrue(check_budgets(path)["pass"])
            report["progress"]["slice_bytes"] = 10**12
            path.write_text(json.dumps(report))
            self.assertEqual(check_budgets(path)["breaches"], ["slice_bytes"])
        self.assertIsNone(check_budgets(None)["pass"])


if __name__ == "__main__":
    unittest.main()
