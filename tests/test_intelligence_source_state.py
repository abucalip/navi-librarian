import tempfile
import unittest
from pathlib import Path

from intelligence.store import open_store, source_state as ss


class SourceStateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db = open_store(Path(self.temp_dir.name) / "intelligence.sqlite3")
        self.addCleanup(self.db.close)

    def test_never_attempted_is_pending(self):
        self.assertEqual(ss.status(self.db, "musicbrainz", "artist", "a"), "pending")
        self.assertIsNone(ss.get_state(self.db, "musicbrainz", "artist", "a"))

    def test_ok_schedules_refresh_and_resets_attempts(self):
        ss.record_outcome(self.db, "musicbrainz", "artist", "a", "error", now=100)
        row = ss.record_outcome(self.db, "musicbrainz", "artist", "a", "ok", now=200, ttl=50, etag="e1")
        self.assertEqual((row["outcome"], row["attempts"], row["next_refresh_at"], row["etag"]), ("ok", 0, 250, "e1"))

    def test_not_found_is_distinct_from_pending(self):
        ss.record_outcome(self.db, "musicbrainz", "artist", "a", "not_found", now=1, ttl=10)
        self.assertEqual(ss.status(self.db, "musicbrainz", "artist", "a"), "not_found")

    def test_no_ttl_means_no_refresh_scheduled(self):
        row = ss.record_outcome(self.db, "musicbrainz", "artist", "a", "ok", now=1)
        self.assertIsNone(row["next_refresh_at"])
        self.assertEqual(ss.due(self.db, "musicbrainz", "artist", now=10**9), [])

    def test_failures_back_off_and_cap(self):
        delays = []
        for i in range(12):
            row = ss.record_outcome(self.db, "musicbrainz", "artist", "a", "error", now=0)
            delays.append(row["next_refresh_at"])
        self.assertEqual(delays[:3], [300, 600, 1200])
        self.assertEqual(delays[-1], 86400)
        self.assertEqual(row["attempts"], 12)

    def test_blocked_backs_off_longer_than_error(self):
        blocked = ss.record_outcome(self.db, "musicbrainz", "artist", "b", "blocked", now=0)
        self.assertEqual(blocked["next_refresh_at"], 3600)

    def test_failure_keeps_last_good_observation_and_validators(self):
        from intelligence.store import repositories as repo
        obs_id, _ = repo.add_observation(self.db, "musicbrainz", {"x": 1}, fetched_at=1)
        ss.record_outcome(self.db, "musicbrainz", "artist", "a", "ok", now=1, observation_id=obs_id,
                          etag="e", last_modified="Mon")
        row = ss.record_outcome(self.db, "musicbrainz", "artist", "a", "error", now=2)
        self.assertEqual((row["observation_id"], row["etag"], row["last_modified"]), (obs_id, "e", "Mon"))

    def test_due_is_ordered_bounded_and_scoped(self):
        for key, t in (("late", 30), ("early", 10), ("future", 500)):
            ss.record_outcome(self.db, "musicbrainz", "artist", key, "ok", now=0, ttl=t)
        ss.record_outcome(self.db, "musicbrainz", "album", "other", "ok", now=0, ttl=1)
        self.assertEqual([r["key"] for r in ss.due(self.db, "musicbrainz", "artist", now=100)], ["early", "late"])
        self.assertEqual(len(ss.due(self.db, "musicbrainz", "artist", now=100, limit=1)), 1)

    def test_unknown_outcome_is_refused(self):
        with self.assertRaises(ValueError):
            ss.record_outcome(self.db, "musicbrainz", "artist", "a", "maybe", now=1)

    def test_deleting_an_observation_keeps_the_ledger_row(self):
        from intelligence.store import repositories as repo
        obs_id, _ = repo.add_observation(self.db, "musicbrainz", {"x": 1}, fetched_at=1)
        ss.record_outcome(self.db, "musicbrainz", "artist", "a", "ok", now=1, observation_id=obs_id)
        with self.db:
            self.db.execute("DELETE FROM observations WHERE id = ?", (obs_id,))
        self.assertIsNone(ss.get_state(self.db, "musicbrainz", "artist", "a")["observation_id"])
