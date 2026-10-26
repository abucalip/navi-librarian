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


class PrecomputeCursorTests(unittest.TestCase):
    def librarian(self, stored):
        writes = []
        lib = mock.Mock()
        lib._discovery_read_list.return_value = stored
        lib._discovery_write_list.side_effect = lambda name, payload: writes.append((name, payload))
        return lib, writes

    def view(self):
        from discovery.search.index import STATE_FRESH
        data = mock.Mock(artists=[{"id": "a"}, {"id": "b"}, {"id": "c"}])
        return mock.Mock(data=data, state=STATE_FRESH)

    def run_once(self, stored):
        lib, writes = self.librarian(stored)
        captured = {}

        def fake_run(artists, network, owned, **kwargs):
            captured.update(kwargs)
            kwargs["on_progress"](2)
            return {"complete": 1}

        with mock.patch.object(search, "owned_view", return_value=self.view()), \
                mock.patch.object(search, "artist_network_for"), \
                mock.patch.object(search, "OwnedKeys"), \
                mock.patch.object(search, "run_precompute", side_effect=fake_run):
            search._precompute_once(lib)
        return captured, writes

    def test_the_run_starts_where_the_last_pass_stopped_and_stores_progress(self):
        captured, writes = self.run_once({"payload": {"next": 2}, "generated_at": "x"})
        self.assertEqual(captured["start"], 2)
        self.assertEqual(writes, [(search.PRECOMPUTE_CURSOR, {"next": 2})])

    def test_a_missing_or_malformed_cursor_starts_at_the_beginning(self):
        for stored in (None, "junk", {"payload": "junk"}, {"payload": {"next": "x"}}):
            captured, _ = self.run_once(stored)
            self.assertEqual(captured["start"], 0)


if __name__ == "__main__":
    unittest.main()
