"""The daily precompute step: a day is done only when the run was usable or raised (app/api/search.py)."""

import unittest
from unittest import mock

from app.api import search


class PrecomputeStepTests(unittest.TestCase):
    def test_an_unusable_index_leaves_the_day_undone_so_it_is_retried(self):
        with mock.patch.object(search, "_precompute_once", return_value=None):
            self.assertIsNone(search._precompute_step(object(), None))

    def test_a_finished_run_marks_the_day_done(self):
        with mock.patch.object(search, "_precompute_once", return_value={"complete": 1}):
            day = search._precompute_step(object(), None)
        self.assertIsNotNone(day)
        with mock.patch.object(search, "_precompute_once") as once:
            self.assertEqual(search._precompute_step(object(), day), day)
            once.assert_not_called()

    def test_a_raising_run_counts_as_done_and_is_not_retried_that_day(self):
        with mock.patch.object(search, "_precompute_once", side_effect=RuntimeError("boom")):
            day = search._precompute_step(object(), None)
        self.assertIsNotNone(day)


if __name__ == "__main__":
    unittest.main()
