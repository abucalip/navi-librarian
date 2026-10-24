"""Per-lens feedback comparison (Engine 2, Phase 5): counts, rates and scope filtering."""
import unittest

from discovery.lens_feedback import lens_acquisition_summary, lens_feedback_summary

LENSES = ("repeated_tracks", "deep_cuts", "obsessions")


def row(status, lens=None, scope="album", metadata=None):
    meta = {"lens": lens} if lens is not None else {}
    if metadata is not None:
        meta = metadata
    return {"scope": scope, "status": status, "metadata": meta}


class LensFeedbackSummaryTests(unittest.TestCase):
    def test_counts_saves_and_dismissals_per_lens(self):
        rows = [
            row("for_me", "repeated_tracks"),
            row("not_for_me", "repeated_tracks"),
            row("not_for_me", "repeated_tracks"),
            row("for_me", "obsessions"),
        ]
        summary = lens_feedback_summary(rows, LENSES)
        self.assertEqual(summary["repeated_tracks"],
                         {"saved": 1, "dismissed": 2, "actions": 3, "save_rate": 0.333})
        self.assertEqual(summary["obsessions"],
                         {"saved": 1, "dismissed": 0, "actions": 1, "save_rate": 1.0})
        self.assertEqual(summary["deep_cuts"],
                         {"saved": 0, "dismissed": 0, "actions": 0, "save_rate": None})

    def test_ignores_rows_without_a_known_lens(self):
        rows = [
            row("for_me"),                       # personal list save: no lens in metadata
            row("for_me", "not_a_lens"),         # unknown lens name
            row("for_me", metadata={"lens": 3}), # non-string lens
            row("for_me", metadata="lens"),      # metadata that is not a mapping
        ]
        summary = lens_feedback_summary(rows, LENSES)
        self.assertTrue(all(entry["actions"] == 0 for entry in summary.values()))

    def test_ignores_artist_scope_and_other_statuses(self):
        rows = [
            row("not_for_me_artist", "deep_cuts", scope="artist"),
            row("for_me_other", "deep_cuts"),
            "not a row",
        ]
        summary = lens_feedback_summary(rows, LENSES)
        self.assertEqual(summary["deep_cuts"]["actions"], 0)

    def test_empty_feedback_gives_zero_counts_for_every_lens(self):
        summary = lens_feedback_summary([], LENSES)
        self.assertEqual(list(summary), list(LENSES))
        self.assertTrue(all(entry["save_rate"] is None for entry in summary.values()))


class LensAcquisitionSummaryTests(unittest.TestCase):
    def test_counts_only_jobs_whose_request_metadata_names_a_lens(self):
        jobs = [
            {"status": "downloading", "details": {"metadata": {"lens": "obsessions"}}},
            {"status": "imported", "details": {"metadata": {"lens": "obsessions"}}},
            {"status": "imported", "details": {"metadata": {}}},
            {"status": "imported", "details": {"metadata": {"lens": "not_a_lens"}}},
            {"status": "imported", "details": {"metadata": "lens"}},
            {"status": "imported", "details": "not a mapping"},
            "not a job",
        ]
        summary = lens_acquisition_summary(jobs, LENSES)
        self.assertEqual(summary["obsessions"],
                         {"requests": 2, "by_status": {"downloading": 1, "imported": 1}})
        self.assertEqual(summary["deep_cuts"], {"requests": 0, "by_status": {}})


if __name__ == "__main__":
    unittest.main()
