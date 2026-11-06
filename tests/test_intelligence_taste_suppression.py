import copy
import math
import unittest

import recommendation_feedback
from intelligence.taste import Rejection, SuppressionEntry, build_suppression, validate_events
from intelligence.taste.suppression import (
    CLIENTS, EXPIRY_SECONDS, KINDS, MAX_BATCH, MAX_WEIGHT, NEGATIVE_HALF_LIFE_SECONDS, SUBJECT_KINDS,
    SuppressionEvent,
)

NOW = 1_800_000_000.0
DAY = 86400
MBID = "ABCDEF01-2345-6789-ABCD-EF0123456789"


def raw(**overrides):
    base = {
        "event_id": "e1",
        "client": "macos",
        "kind": "dismiss",
        "subject_kind": "album",
        "subject_id": "al-1",
        "occurred_at": NOW - 10,
    }
    base.update(overrides)
    return base


def ev(**overrides):
    base = dict(
        event_id="e1", client="macos", kind="dismiss", subject_kind="album", subject_id="al-1",
        mbid=None, occurred_at=NOW, played_seconds=None, duration_seconds=None,
    )
    base.update(overrides)
    return SuppressionEvent(**base)


def reasons(batch):
    accepted, rejections = validate_events(batch, NOW)
    return [r.reason for r in rejections], accepted


class ConstantsTests(unittest.TestCase):
    def test_decay_constants_match_negative_feedback_policy(self):
        self.assertEqual(NEGATIVE_HALF_LIFE_SECONDS, recommendation_feedback.NEGATIVE_HALF_LIFE_SECONDS)
        self.assertEqual(EXPIRY_SECONDS, recommendation_feedback.NEGATIVE_EXPIRY_SECONDS)

    def test_allowed_values(self):
        self.assertEqual(CLIENTS, ("macos", "android"))
        self.assertEqual(KINDS, ("skip", "dismiss"))
        self.assertEqual(SUBJECT_KINDS, ("track", "album", "artist", "card"))
        self.assertEqual((MAX_BATCH, MAX_WEIGHT), (100, 1.0))


class ValidateTests(unittest.TestCase):
    def test_good_event_is_accepted(self):
        accepted, rejections = validate_events([raw()], NOW)
        self.assertEqual(rejections, ())
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0].subject_id, "al-1")

    def test_bad_event_id(self):
        for value in (None, "", "x" * 65, 7):
            with self.subTest(value=value):
                got, _ = reasons([raw(event_id=value)])
                self.assertEqual(got, ["bad_event_id"])
        self.assertEqual(reasons([{k: v for k, v in raw().items() if k != "event_id"}])[0], ["bad_event_id"])

    def test_bad_client(self):
        self.assertEqual(reasons([raw(client="ios")])[0], ["bad_client"])

    def test_bad_kind(self):
        self.assertEqual(reasons([raw(kind="like")])[0], ["bad_kind"])

    def test_bad_subject_kind(self):
        self.assertEqual(reasons([raw(subject_kind="song")])[0], ["bad_subject_kind"])

    def test_bad_subject_id(self):
        for value in ("", "y" * 201, None):
            with self.subTest(value=value):
                self.assertEqual(reasons([raw(subject_id=value)])[0], ["bad_subject_id"])

    def test_skip_needs_track(self):
        self.assertEqual(reasons([raw(kind="skip", subject_kind="album")])[0], ["skip_needs_track"])
        got, accepted = reasons([raw(kind="skip", subject_kind="track")])
        self.assertEqual((got, len(accepted)), ([], 1))

    def test_bad_mbid(self):
        for value in ("not-a-uuid", "", 12, MBID + "0"):
            with self.subTest(value=value):
                self.assertEqual(reasons([raw(mbid=value)])[0], ["bad_mbid"])

    def test_mbid_is_normalised_to_lowercase(self):
        accepted = validate_events([raw(mbid=MBID)], NOW)[0]
        self.assertEqual(accepted[0].mbid, MBID.lower())

    def test_mbid_absent_is_none(self):
        self.assertIsNone(validate_events([raw()], NOW)[0][0].mbid)

    def test_bad_occurred_at_rejects_bool_nan_inf_and_non_positive(self):
        for value in (True, False, math.nan, math.inf, -math.inf, 0, -5, "123", None):
            with self.subTest(value=value):
                self.assertEqual(reasons([raw(occurred_at=value)])[0], ["bad_occurred_at"])

    def test_future_events(self):
        self.assertEqual(reasons([raw(occurred_at=NOW + 301)])[0], ["future"])
        self.assertEqual(reasons([raw(occurred_at=NOW + 300)])[0], [])

    def test_bad_played_seconds(self):
        self.assertEqual(reasons([raw(kind="skip", subject_kind="track", played_seconds=-1)])[0], ["bad_played_seconds"])
        self.assertEqual(reasons([raw(kind="skip", subject_kind="track", played_seconds=True)])[0], ["bad_played_seconds"])
        self.assertEqual(reasons([raw(kind="skip", subject_kind="track", played_seconds=math.nan)])[0], ["bad_played_seconds"])
        self.assertEqual(reasons([raw(kind="skip", subject_kind="track", played_seconds=math.inf)])[0], ["bad_played_seconds"])
        self.assertEqual(reasons([raw(played_seconds=12)])[0], ["bad_played_seconds"])  # album: not allowed

    def test_bad_duration_seconds(self):
        self.assertEqual(reasons([raw(kind="skip", subject_kind="track", duration_seconds=-0.1)])[0], ["bad_duration_seconds"])
        self.assertEqual(reasons([raw(kind="skip", subject_kind="track", duration_seconds=False)])[0], ["bad_duration_seconds"])
        self.assertEqual(reasons([raw(duration_seconds=200)])[0], ["bad_duration_seconds"])  # artist: not allowed

    def test_track_durations_accepted_and_zero_is_valid(self):
        accepted = validate_events([raw(kind="skip", subject_kind="track", played_seconds=0, duration_seconds=180)], NOW)[0]
        self.assertEqual((accepted[0].played_seconds, accepted[0].duration_seconds), (0.0, 180.0))

    def test_not_a_mapping(self):
        self.assertEqual(reasons(["oops"])[0], ["not_a_mapping"])
        self.assertEqual(reasons([None])[0], ["not_a_mapping"])

    def test_batch_over_limit_is_rejected_whole(self):
        batch = [raw(event_id=f"e{i}") for i in range(MAX_BATCH + 1)]
        accepted, rejections = validate_events(batch, NOW)
        self.assertEqual(accepted, ())
        self.assertEqual(rejections, (Rejection(-1, "batch_too_large"),))

    def test_batch_at_limit_is_accepted(self):
        batch = [raw(event_id=f"e{i}") for i in range(MAX_BATCH)]
        accepted, rejections = validate_events(batch, NOW)
        self.assertEqual((len(accepted), rejections), (MAX_BATCH, ()))

    def test_bad_item_does_not_affect_good_ones(self):
        batch = [raw(event_id="a"), raw(event_id="b", client="ios"), raw(event_id="c")]
        accepted, rejections = validate_events(batch, NOW)
        self.assertEqual([e.event_id for e in accepted], ["a", "c"])
        self.assertEqual(rejections, (Rejection(1, "bad_client"),))

    def test_duplicate_event_id_in_batch_keeps_first_without_rejection(self):
        batch = [raw(event_id="dup", subject_id="first"), raw(event_id="dup", subject_id="second")]
        accepted, rejections = validate_events(batch, NOW)
        self.assertEqual(rejections, ())
        self.assertEqual([(e.event_id, e.subject_id) for e in accepted], [("dup", "first")])

    def test_extra_fields_are_ignored_and_not_stored(self):
        event = validate_events([raw(path="/music/x.flac", token="secret", device="Hamdi's Mac")], NOW)[0][0]
        self.assertNotIn("path", vars(event))
        self.assertNotIn("token", vars(event))
        self.assertEqual(set(vars(event)), {
            "event_id", "client", "kind", "subject_kind", "subject_id", "mbid",
            "occurred_at", "played_seconds", "duration_seconds",
        })

    def test_inputs_are_not_mutated(self):
        batch = [raw(), raw(event_id="x", client="ios")]
        before = copy.deepcopy(batch)
        validate_events(batch, NOW)
        self.assertEqual(batch, before)

    def test_empty_batch(self):
        self.assertEqual(validate_events([], NOW), ((), ()))


class BuildTests(unittest.TestCase):
    def test_empty_input_is_empty_tuple(self):
        self.assertEqual(build_suppression([], NOW), ())

    def test_single_event_at_age_zero_has_weight_one(self):
        (entry,) = build_suppression([ev(occurred_at=NOW)], NOW)
        self.assertEqual(entry.weight, 1.0)
        self.assertEqual((entry.events, entry.skips, entry.last_event_at), (1, 0, NOW))

    def test_weight_halves_at_exactly_fourteen_days(self):
        (entry,) = build_suppression([ev(occurred_at=NOW - NEGATIVE_HALF_LIFE_SECONDS)], NOW)
        self.assertEqual(entry.weight, 0.5)

    def test_excluded_just_past_sixty_days_and_included_at_exactly_sixty(self):
        self.assertEqual(build_suppression([ev(occurred_at=NOW - EXPIRY_SECONDS - 1)], NOW), ())
        (entry,) = build_suppression([ev(occurred_at=NOW - EXPIRY_SECONDS)], NOW)
        self.assertEqual(entry.weight, round(2.0 ** -(EXPIRY_SECONDS / NEGATIVE_HALF_LIFE_SECONDS), 6))

    def test_future_events_are_ignored(self):
        self.assertEqual(build_suppression([ev(occurred_at=NOW + 1)], NOW), ())

    def test_weight_caps_at_one_with_many_events(self):
        events = [ev(event_id=f"e{i}", occurred_at=NOW - i) for i in range(10)]
        (entry,) = build_suppression(events, NOW)
        self.assertEqual(entry.weight, MAX_WEIGHT)
        self.assertEqual(entry.events, 10)

    def test_weight_is_rounded_to_six_places(self):
        (entry,) = build_suppression([ev(occurred_at=NOW - 3 * DAY)], NOW)
        self.assertEqual(entry.weight, round(entry.weight, 6))

    def test_duplicate_event_id_counted_once_with_earliest_time(self):
        events = [ev(event_id="same", occurred_at=NOW - 1), ev(event_id="same", occurred_at=NOW - 100)]
        (entry,) = build_suppression(events, NOW)
        self.assertEqual(entry.events, 1)
        self.assertEqual(entry.last_event_at, NOW - 100)

    def test_skipped_track_does_not_create_album_or_artist_entries(self):
        events = [ev(event_id="s", kind="skip", subject_kind="track", subject_id="t-1", mbid=MBID.lower(), occurred_at=NOW)]
        entries = build_suppression(events, NOW)
        self.assertEqual([(e.subject_kind, e.subject_id) for e in entries], [("track", "t-1")])
        self.assertEqual(entries[0].skips, 1)

    def test_separate_subjects_do_not_interact(self):
        events = [
            ev(event_id="a", subject_kind="album", subject_id="al-1", occurred_at=NOW),
            ev(event_id="b", subject_kind="album", subject_id="al-2", occurred_at=NOW - 14 * DAY),
        ]
        by_id = {e.subject_id: e for e in build_suppression(events, NOW)}
        self.assertEqual(by_id["al-1"].weight, 1.0)
        self.assertEqual(by_id["al-2"].weight, 0.5)

    def test_same_id_different_kind_are_separate_subjects(self):
        events = [ev(event_id="a", subject_kind="artist", subject_id="x"), ev(event_id="b", subject_kind="album", subject_id="x")]
        self.assertEqual(len(build_suppression(events, NOW)), 2)

    def test_tie_breaks_by_subject_kind_then_subject_id(self):
        events = [
            ev(event_id="a", subject_kind="track", subject_id="t-b", occurred_at=NOW),
            ev(event_id="b", subject_kind="track", subject_id="t-a", occurred_at=NOW),
        ]
        self.assertEqual([e.subject_id for e in build_suppression(events, NOW)], ["t-a", "t-b"])

    def test_output_is_newest_first(self):
        events = [
            ev(event_id="old", subject_id="old", occurred_at=NOW - 2 * DAY),
            ev(event_id="new", subject_id="new", occurred_at=NOW - 1),
        ]
        self.assertEqual([e.subject_id for e in build_suppression(events, NOW)], ["new", "old"])

    def test_input_order_does_not_change_output(self):
        events = [
            ev(event_id=f"e{i}", subject_id=f"s{i % 3}", occurred_at=NOW - (i * 7919) % (30 * DAY), kind="dismiss")
            for i in range(40)
        ]
        self.assertEqual(build_suppression(events, NOW), build_suppression(list(reversed(events)), NOW))

    def test_inputs_are_not_mutated(self):
        events = [ev(event_id="a"), ev(event_id="b", occurred_at=NOW - 5)]
        before = list(events)
        build_suppression(events, NOW)
        self.assertEqual(events, before)

    def test_entries_are_frozen_dataclasses(self):
        (entry,) = build_suppression([ev()], NOW)
        self.assertIsInstance(entry, SuppressionEntry)
        with self.assertRaises(Exception):
            entry.weight = 0.0  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
