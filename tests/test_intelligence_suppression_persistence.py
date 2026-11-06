import json
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path

from intelligence.store import open_store
from intelligence.store.state import STATE_LATEST, STATE_MIGRATIONS, StateError, default_state_path
from intelligence.taste.suppression import SuppressionEvent
from intelligence.taste.suppression_persistence import (
    CONFLICT, DUPLICATE, INSERTED, RETENTION_SECONDS, SWEEP_LIMIT_MAX, InsertOutcome, get_event,
    insert_events, retention_cutoff, sweep_expired,
)

NOW = 1_800_000_000.0
DAY = 86400
MBID = "abcdef01-2345-6789-abcd-ef0123456789"


def U(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, str(name)))


def ev(name="e1", **overrides):
    base = dict(
        event_id=U(name), client="macos", kind="dismiss", subject_kind="album", subject_id="al-1",
        mbid=None, occurred_at=NOW, played_seconds=None, duration_seconds=None,
    )
    base.update(overrides)
    return SuppressionEvent(**base)


# Migration 1 as a bare connection sees it: the owner-state file's own schema, without the ATTACH prefix.
V1_TABLE_SQL = STATE_MIGRATIONS[0][2][0].replace("state.card_decisions", "card_decisions")


def count(db):
    return db.execute("SELECT COUNT(*) FROM state.suppression_events").fetchone()[0]


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = Path(self.dir.name) / "intelligence.sqlite3"
        self.db = open_store(self.path)
        self.addCleanup(self.db.close)


class MigrationTests(StoreTestCase):
    def test_migration_creates_event_table_in_owner_state_file(self):
        self.assertEqual(STATE_LATEST, 2)
        self.assertEqual(self.db.execute("PRAGMA state.user_version").fetchone()[0], 2)
        tables = {r[0] for r in self.db.execute("SELECT name FROM state.sqlite_master WHERE type = 'table'")}
        self.assertIn("suppression_events", tables)
        main_tables = {r[0] for r in self.db.execute("SELECT name FROM main.sqlite_master WHERE type = 'table'")}
        self.assertNotIn("suppression_events", main_tables)

    def test_existing_v1_state_file_migrates_and_keeps_its_decisions(self):
        dir_path = Path(self.dir.name) / "old"
        dir_path.mkdir()
        knowledge = dir_path / "intelligence.sqlite3"
        state = default_state_path(knowledge)
        raw = sqlite3.connect(state)
        raw.execute(V1_TABLE_SQL)
        raw.execute("INSERT INTO card_decisions (kind, key, state, payload, decided_at) "
                    "VALUES ('gem', 'gem:old', 'dismissed', ?, 5)", (json.dumps({"subject": {"key": "gem:old"}}),))
        raw.execute("PRAGMA user_version = 1")
        raw.commit()
        raw.close()

        db = open_store(knowledge)
        self.addCleanup(db.close)
        self.assertEqual(db.execute("PRAGMA state.user_version").fetchone()[0], 2)
        self.assertEqual(db.execute("SELECT key FROM state.card_decisions").fetchone()[0], "gem:old")
        insert_events(db, [ev("after-migration")])
        self.assertEqual(count(db), 1)

    def test_failed_state_migration_rolls_back_completely(self):
        dir_path = Path(self.dir.name) / "blocked"
        dir_path.mkdir()
        knowledge = dir_path / "intelligence.sqlite3"
        state = default_state_path(knowledge)
        raw = sqlite3.connect(state)
        raw.execute(V1_TABLE_SQL)
        raw.execute("PRAGMA user_version = 1")
        # A name clash on the second statement of migration 2 forces a failure after the table is created.
        raw.execute("CREATE TABLE other (x INTEGER)")
        raw.execute("CREATE INDEX suppression_events_time ON other (x)")
        raw.commit()
        raw.close()

        with self.assertRaises(StateError):
            open_store(knowledge)
        raw = sqlite3.connect(state)
        self.addCleanup(raw.close)
        self.assertEqual(raw.execute("PRAGMA user_version").fetchone()[0], 1)
        tables = {r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertNotIn("suppression_events", tables)


class RoundTripAndInsertTests(StoreTestCase):
    def test_all_fields_round_trip_for_a_track_with_nullable_values_present(self):
        event = ev("track", kind="skip", subject_kind="track", subject_id="nav-track-9", mbid=MBID,
                   occurred_at=NOW - 60.5, played_seconds=12.25, duration_seconds=240.0)
        self.assertEqual(insert_events(self.db, [event])[0].status, INSERTED)
        self.assertEqual(get_event(self.db, event.event_id), event)

    def test_nullable_fields_round_trip_as_null(self):
        event = ev("bare")
        insert_events(self.db, [event])
        stored = get_event(self.db, event.event_id)
        self.assertEqual(stored, event)
        self.assertIsNone(stored.mbid)
        self.assertIsNone(stored.played_seconds)
        self.assertIsNone(stored.duration_seconds)

    def test_valid_event_is_inserted(self):
        outcome = insert_events(self.db, [ev("one")])
        self.assertEqual(outcome, (InsertOutcome(U("one"), INSERTED),))
        self.assertEqual(count(self.db), 1)

    def test_reinserting_the_same_event_id_creates_no_duplicate(self):
        event = ev("replay")
        insert_events(self.db, [event])
        outcome = insert_events(self.db, [event])
        self.assertEqual([o.status for o in outcome], [DUPLICATE])
        self.assertEqual(count(self.db), 1)

    def test_same_id_with_different_payload_keeps_the_original_row(self):
        original = ev("conflict")
        insert_events(self.db, [original])
        changed = ev("conflict", subject_id="al-2", client="android")
        outcome = insert_events(self.db, [changed])
        self.assertEqual([o.status for o in outcome], [CONFLICT])
        self.assertEqual(count(self.db), 1)
        self.assertEqual(get_event(self.db, original.event_id), original)

    def test_batch_with_duplicates_is_deterministic_and_keeps_first_copy(self):
        a = ev("a")
        a_changed = ev("a", subject_id="other")
        b = ev("b")
        batch = [a, a, a_changed, b]
        first = insert_events(self.db, batch)
        self.assertEqual([o.status for o in first], [INSERTED, DUPLICATE, CONFLICT, INSERTED])
        self.assertEqual(get_event(self.db, a.event_id), a)
        self.assertEqual(count(self.db), 2)
        second = insert_events(self.db, batch)
        self.assertEqual([o.status for o in second], [DUPLICATE, DUPLICATE, CONFLICT, DUPLICATE])
        self.assertEqual(count(self.db), 2)

    def test_failed_batch_rolls_back_every_event(self):
        good_first = ev("good-1")
        # Passes validation's shape but breaks the table contract: a skip must be a track.
        broken = ev("broken", kind="skip", subject_kind="album")
        good_last = ev("good-2")
        with self.assertRaises(sqlite3.IntegrityError):
            insert_events(self.db, [good_first, broken, good_last])
        self.assertEqual(count(self.db), 0)

    def test_inputs_of_the_wrong_type_are_refused_before_any_write(self):
        with self.assertRaises(TypeError):
            insert_events(self.db, [ev("x"), {"event_id": U("x")}])
        with self.assertRaises(TypeError):
            insert_events(self.db, ev("y"))
        with self.assertRaises(ValueError):
            insert_events(self.db, [ev(f"n{i}") for i in range(101)])
        self.assertEqual(count(self.db), 0)

    def test_database_constraints_reinforce_the_contract(self):
        bad_rows = [
            dict(event_id=U("c1").upper()),
            dict(client="ios"),
            dict(kind="like"),
            dict(subject_kind="playlist"),
            dict(subject_id=""),
            dict(subject_id="x" * 201),
            dict(mbid="NOT-A-UUID"),
            dict(occurred_at=0.0),
            dict(kind="skip", subject_kind="album"),
            dict(subject_kind="album", played_seconds=3.0),
            dict(subject_kind="artist", duration_seconds=3.0),
            dict(subject_kind="track", played_seconds=-1.0),
        ]
        for overrides in bad_rows:
            with self.subTest(overrides=overrides):
                event = ev("check", **overrides)
                with self.assertRaises(sqlite3.IntegrityError):
                    insert_events(self.db, [event])
        self.assertEqual(count(self.db), 0)

    def test_stored_rows_cannot_be_updated(self):
        event = ev("frozen")
        insert_events(self.db, [event])
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE state.suppression_events SET subject_id = 'changed'")
        self.assertEqual(get_event(self.db, event.event_id), event)


class RetentionTests(StoreTestCase):
    def seed(self, ages_in_seconds, prefix="age"):
        events = [ev(f"{prefix}-{i}", occurred_at=NOW - age) for i, age in enumerate(ages_in_seconds)]
        insert_events(self.db, events)
        return events

    def test_cutoff_is_now_minus_180_days(self):
        self.assertEqual(RETENTION_SECONDS, 180 * DAY)
        self.assertEqual(retention_cutoff(NOW), NOW - 180 * DAY)

    def test_rows_older_than_the_cutoff_are_deleted(self):
        self.seed([181 * DAY, 400 * DAY])
        self.assertEqual(sweep_expired(self.db, NOW, limit=100), 2)
        self.assertEqual(count(self.db), 0)

    def test_boundary_row_on_the_cutoff_and_newer_rows_are_kept(self):
        self.seed([180 * DAY, 180 * DAY - 1, 179 * DAY, 0, -300])
        just_older = ev("just-older", occurred_at=NOW - 180 * DAY - 1)
        insert_events(self.db, [just_older])
        self.assertEqual(sweep_expired(self.db, NOW, limit=100), 1)
        self.assertIsNotNone(get_event(self.db, U("age-0")))  # exactly on the cutoff: kept
        self.assertIsNone(get_event(self.db, just_older.event_id))  # one second older: deleted
        self.assertEqual(count(self.db), 5)  # the four newer seeded rows plus the cutoff row

    def test_bounded_sweep_never_exceeds_its_limit_and_completes_when_repeated(self):
        self.seed([200 * DAY + i for i in range(5)])
        self.seed([10 * DAY], prefix="newer")  # a newer row that must survive every pass
        self.assertEqual(sweep_expired(self.db, NOW, limit=2), 2)
        self.assertEqual(count(self.db), 4)
        self.assertEqual(sweep_expired(self.db, NOW, limit=2), 2)
        self.assertEqual(sweep_expired(self.db, NOW, limit=2), 1)
        self.assertEqual(sweep_expired(self.db, NOW, limit=2), 0)  # repeat is safe
        self.assertEqual(count(self.db), 1)

    def test_sweep_deletes_the_oldest_rows_first(self):
        self.seed([300 * DAY, 500 * DAY, 400 * DAY])
        sweep_expired(self.db, NOW, limit=1)
        self.assertIsNone(get_event(self.db, U("age-1")))  # 500 days old
        self.assertIsNotNone(get_event(self.db, U("age-0")))

    def test_sweep_leaves_other_owner_state_and_knowledge_untouched(self):
        self.seed([400 * DAY])
        self.db.execute("INSERT INTO state.card_decisions (kind, key, state, payload, decided_at) "
                        "VALUES ('gem', 'gem:keep', 'dismissed', '{}', 1)")
        self.db.execute("INSERT INTO main.insights (kind, payload, generation, computed_at) "
                        "VALUES ('gem', '{}', 1, 1)")
        self.db.commit()
        sweep_expired(self.db, NOW, limit=100)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM state.card_decisions").fetchone()[0], 1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM main.insights").fetchone()[0], 1)

    def test_invalid_sweep_arguments_are_refused(self):
        for limit in (0, -1, True, 1.5, SWEEP_LIMIT_MAX + 1):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                sweep_expired(self.db, NOW, limit=limit)
        for now in (float("nan"), float("inf"), True, "now"):
            with self.subTest(now=now), self.assertRaises(ValueError):
                sweep_expired(self.db, now, limit=1)


class UnsafeStateTests(unittest.TestCase):
    def test_missing_event_table_fails_without_deleting_anything(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = sqlite3.connect(Path(directory) / "state.sqlite3")
            raw.execute("CREATE TABLE card_decisions (kind TEXT, key TEXT, state TEXT, payload TEXT, decided_at REAL)")
            raw.execute("INSERT INTO card_decisions VALUES ('gem', 'k', 'dismissed', '{}', 1)")
            raw.commit()
            db = sqlite3.connect(":memory:")
            db.execute("ATTACH DATABASE ? AS state", (str(Path(directory) / "state.sqlite3"),))
            with self.assertRaises(sqlite3.OperationalError):
                insert_events(db, [ev("x")])
            with self.assertRaises(sqlite3.OperationalError):
                sweep_expired(db, NOW, limit=10)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM state.card_decisions").fetchone()[0], 1)
            db.close()
            raw.close()


if __name__ == "__main__":
    unittest.main()
