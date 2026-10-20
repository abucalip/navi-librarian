"""Save is a bookmark: it writes the for_me row and starts no search or thread."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import navidrome_server as server


class SaveBookmarkTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        patcher = patch.object(server, "DISCOVERY_DB", Path(temp.name) / "d.sqlite3")
        patcher.start()
        self.addCleanup(patcher.stop)
        server._discovery_init()

    def feedback(self, action, metadata=None):
        return json.loads(server.discovery_set_feedback(
            "Some Artist", "Some Album", action, json.dumps(metadata or {}),
        ))

    def for_me_rows(self):
        return [r for r in server._discovery_feedback_rows() if r["status"] == "for_me"]

    def test_save_writes_row_without_thread_or_acquisition(self):
        meta = {"genres": ["jazz"], "source": "test"}
        with patch.object(server, "discovery_acquire_album") as acquire, \
                patch.object(threading, "Thread") as thread:
            result = self.feedback("save", meta)
        acquire.assert_not_called()
        thread.assert_not_called()
        self.assertEqual(result, {
            "ok": True, "action": "save", "artist": "Some Artist", "album": "Some Album",
        })
        rows = self.for_me_rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["metadata"], meta)

    def test_remove_for_me_deletes_row(self):
        self.feedback("save")
        self.assertTrue(self.feedback("remove_for_me")["ok"])
        self.assertEqual(self.for_me_rows(), [])

    def test_dismiss_actions_unchanged(self):
        self.assertTrue(self.feedback("dismiss")["ok"])
        self.assertTrue(self.feedback("dismiss_artist")["ok"])
        statuses = {(r["scope"], r["status"]) for r in server._discovery_feedback_rows()}
        self.assertIn(("album", "not_for_me"), statuses)
        self.assertIn(("artist", "not_for_me_artist"), statuses)

    def test_legacy_auto_acquire_helper_is_gone(self):
        self.assertFalse(hasattr(server, "_discovery_auto_acquire_for_me"))


if __name__ == "__main__":
    unittest.main()
