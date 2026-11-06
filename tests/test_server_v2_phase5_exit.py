import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from server_v2_phase5_exit import audit_path, check_synthetic  # noqa: E402


def reason(**kw):
    base = {"code": "same_label", "text": "released on Domino", "via": {"canonical_name": "Domino"},
            "anchor": {"canonical_name": "Album?"},
            "evidence": [{"source": "musicbrainz_dump", "evidence_class": "source_explicit", "match_quality": "exact_mbid"}]}
    base.update(kw)
    return base


def path(*reasons, status="ok", start=1, stop=2):
    return {"status": status, "start": {"id": start}, "stops": [{"entity": {"id": stop}, "reasons": list(reasons)}]}


class Phase5ExitTests(unittest.TestCase):
    def test_synthetic_check_passes(self):
        self.assertTrue(check_synthetic()["pass"])

    def test_clean_path_has_no_problems_and_a_question_mark_in_a_title_is_fine(self):
        self.assertEqual(audit_path(path(reason())), [])

    def test_problems_are_named(self):
        self.assertIn("stop_without_reason", audit_path(path()))
        self.assertIn("reason_without_evidence", audit_path(path(reason(evidence=[]))))
        self.assertIn("uncertain_evidence_used", audit_path(path(reason(evidence=[{"source": "x", "evidence_class": "inferred"}]))))
        self.assertIn("uncertain_evidence_used", audit_path(path(reason(evidence=[{"source": "x", "match_quality": "unresolved"}]))))
        self.assertIn("reason_names_unresolved", audit_path(path(reason(via={"canonical_name": None}))))
        self.assertIn("start_is_a_stop", audit_path(path(reason(), stop=1)))
        self.assertIn("empty_with_stops", audit_path(path(reason(), status="empty")))


if __name__ == "__main__":
    unittest.main()
