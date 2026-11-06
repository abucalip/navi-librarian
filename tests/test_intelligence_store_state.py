import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from intelligence.insights import (
    accept_card, accepted_keys, dismiss_gem, dismissed_keys, list_gem_cards, restore_gem,
)
from intelligence.insights.forgotten_gems import CARD_KIND
from intelligence.store import open_store
from intelligence.store.db import connect
from intelligence.store.migrations import migrate
from intelligence.store.state import STATE_LATEST, StateError, default_state_path


def live_card(db, key, score=1.0):
    payload = json.dumps({"subject": {"key": key}, "score": score, "reasons": []})
    db.execute("INSERT INTO insights (kind, payload, generation, computed_at) VALUES (?, ?, 1, 0)", (CARD_KIND, payload))
    db.commit()


class StateFileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "intelligence.sqlite3"

    def test_default_state_path_sits_beside_the_knowledge_file(self):
        self.assertEqual(default_state_path(self.path), str(Path(self.dir.name) / "intelligence.state.sqlite3"))
        self.assertEqual(default_state_path(":memory:"), ":memory:")

    def test_state_has_own_version_and_file(self):
        db = open_store(self.path)
        self.assertEqual(db.execute("PRAGMA state.user_version").fetchone()[0], STATE_LATEST)
        self.assertTrue(Path(default_state_path(self.path)).exists())

    def test_decisions_survive_wiping_the_knowledge_file(self):
        db = open_store(self.path)
        live_card(db, "gem:a")
        dismiss_gem(db, "gem:a")
        accept_card(db, CARD_KIND, "gem:b")
        db.close()
        for suffix in ("", "-wal", "-shm"):
            Path(str(self.path) + suffix).unlink(missing_ok=True)
        db = open_store(self.path)
        self.assertEqual(dismissed_keys(db), {"gem:a"})
        self.assertEqual(accepted_keys(db, CARD_KIND), {"gem:b"})

    def test_dismissal_removes_live_card_from_knowledge_file(self):
        db = open_store(self.path)
        live_card(db, "gem:a")
        dismiss_gem(db, "gem:a")
        self.assertEqual(db.execute("SELECT COUNT(*) FROM main.insights").fetchone()[0], 0)
        snapshot = db.execute("SELECT payload FROM state.card_decisions").fetchone()[0]
        self.assertEqual(json.loads(snapshot)["score"], 1.0)

    def test_listing_hides_a_dismissed_key_even_if_a_live_row_remains(self):
        db = open_store(self.path)
        live_card(db, "gem:a")
        live_card(db, "gem:b", 0.5)
        dismiss_gem(db, "gem:a")
        live_card(db, "gem:a")  # as if a crash left the live row behind
        self.assertEqual([c["subject"]["key"] for c in list_gem_cards(db)], ["gem:b"])
        restore_gem(db, "gem:a")
        self.assertEqual(len(list_gem_cards(db)), 2)

    def test_legacy_decisions_move_once(self):
        db = connect(self.path)
        migrate(db)
        db.execute("INSERT INTO insights (kind, payload, generation, computed_at, dismissed_state) "
                   "VALUES (?, ?, 1, 5, 'dismissed')", (CARD_KIND, json.dumps({"subject": {"key": "gem:old"}})))
        db.execute("INSERT INTO insights (kind, payload, generation, computed_at, dismissed_state) "
                   "VALUES (?, ?, 1, 6, 'accepted')", (CARD_KIND, json.dumps({"subject": {"key": "gem:ok"}})))
        db.commit()
        db.close()
        db = open_store(self.path)
        self.assertEqual(dismissed_keys(db), {"gem:old"})
        self.assertEqual(accepted_keys(db, CARD_KIND), {"gem:ok"})
        self.assertEqual(db.execute("SELECT COUNT(*) FROM main.insights").fetchone()[0], 0)
        db.close()
        db = open_store(self.path)  # second open changes nothing
        self.assertEqual(db.execute("SELECT COUNT(*) FROM state.card_decisions").fetchone()[0], 2)

    def test_newer_state_file_is_refused(self):
        raw = sqlite3.connect(default_state_path(self.path))
        raw.execute(f"PRAGMA user_version = {STATE_LATEST + 1}")
        raw.close()
        with self.assertRaises(StateError):
            open_store(self.path)


if __name__ == "__main__":
    unittest.main()
