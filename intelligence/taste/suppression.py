"""Pure skip and dismissal suppression memory (Phase 6 item 5, D-027).

Clients report skips and dismissals as events. This module validates a batch of raw event mappings
and builds a per-subject suppression view from the accepted events. Inputs are plain values supplied
by the caller. Nothing here reads or writes a store, calls a provider, defines a route, runs a job,
talks to a client, or feeds a recommendation. The memory is record-only: no ranking, lens, radio,
card or playlist reads it, and a skipped track does not spread to its album or artist.

Honesty rules
-------------
* a skip is what the client reports; nothing is inferred from scrobbles or re-derived here;
* a subject is judged only by its own events: a track skip never creates an album or artist entry;
* a malformed event is rejected with a reason and never stops the rest of its batch, except a batch
  larger than ``MAX_BATCH``, which is rejected as a whole;
* duplicate ``event_id`` values are idempotent: the first accepted copy is kept, so replaying a batch
  changes nothing;
* decay and thresholds (14-day half-life, 60-day expiry, 1.0 cap, 100-event batch, 300 s future
  tolerance) are starting values reused from ``recommendation_feedback.py``, not measured.

Decay
-----
An event is active when ``0 <= now - occurred_at <= EXPIRY_SECONDS``. Its weight is
``2 ** (-age / NEGATIVE_HALF_LIFE_SECONDS)``. A subject's weight is the sum of its active event
weights, capped at ``MAX_WEIGHT`` and rounded to six places. Future events are ignored until their
time arrives.

Determinism
-----------
Events are ordered by a total key before deduplication and summation, so float sums and output order
never depend on the caller's input order.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

NEGATIVE_HALF_LIFE_SECONDS = 14 * 86400
EXPIRY_SECONDS = 60 * 86400
MAX_WEIGHT = 1.0
MAX_BATCH = 100
CLIENTS = ("macos", "android")
KINDS = ("skip", "dismiss")
SUBJECT_KINDS = ("track", "album", "artist", "card")

MAX_EVENT_ID_LENGTH = 64
MAX_SUBJECT_ID_LENGTH = 200
FUTURE_TOLERANCE_SECONDS = 300
WEIGHT_PLACES = 6

_SKIP = "skip"
_TRACK = "track"
_MBID_RE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")


@dataclass(frozen=True)
class SuppressionEvent:
    event_id: str
    client: str
    kind: str
    subject_kind: str
    subject_id: str
    mbid: str | None
    occurred_at: float                  # epoch seconds
    played_seconds: float | None        # tracks only
    duration_seconds: float | None      # tracks only


@dataclass(frozen=True)
class Rejection:
    index: int          # position in the batch; -1 means the whole batch
    reason: str         # lowercase snake_case code


@dataclass(frozen=True)
class SuppressionEntry:
    subject_kind: str
    subject_id: str
    weight: float           # 0 < weight <= MAX_WEIGHT, rounded to WEIGHT_PLACES
    events: int             # active events counted into the weight
    skips: int              # active events of kind "skip"
    last_event_at: float    # newest active event time


def _finite(value: Any) -> float | None:
    """Return ``value`` as a finite float, or None. Booleans and non-numbers are never numbers here."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except OverflowError:
        return None
    return number if math.isfinite(number) else None


def _seconds(raw: Mapping[str, Any], field: str, subject_kind: str) -> tuple[float | None, bool]:
    """Return ``(value, ok)`` for an optional duration. Only tracks may carry one; absent is fine."""
    value = raw.get(field)
    if value is None:
        return None, True
    if subject_kind != _TRACK:
        return None, False
    number = _finite(value)
    if number is None or number < 0:
        return None, False
    return number, True


def _parse(index: int, raw: Any, now: float) -> SuppressionEvent | Rejection:
    def reject(reason: str) -> Rejection:
        return Rejection(index, reason)

    if not isinstance(raw, Mapping):
        return reject("not_a_mapping")

    event_id = raw.get("event_id")
    if not isinstance(event_id, str) or not 0 < len(event_id) <= MAX_EVENT_ID_LENGTH:
        return reject("bad_event_id")

    client = raw.get("client")
    if client not in CLIENTS:
        return reject("bad_client")

    kind = raw.get("kind")
    if kind not in KINDS:
        return reject("bad_kind")

    subject_kind = raw.get("subject_kind")
    if subject_kind not in SUBJECT_KINDS:
        return reject("bad_subject_kind")

    subject_id = raw.get("subject_id")
    if not isinstance(subject_id, str) or not 0 < len(subject_id) <= MAX_SUBJECT_ID_LENGTH:
        return reject("bad_subject_id")

    if kind == _SKIP and subject_kind != _TRACK:
        return reject("skip_needs_track")

    mbid_raw = raw.get("mbid")
    if mbid_raw is None:
        mbid = None
    elif isinstance(mbid_raw, str) and _MBID_RE.fullmatch(mbid_raw):
        mbid = mbid_raw.lower()
    else:
        return reject("bad_mbid")

    occurred_at = _finite(raw.get("occurred_at"))
    if occurred_at is None or occurred_at <= 0:
        return reject("bad_occurred_at")
    if occurred_at > now + FUTURE_TOLERANCE_SECONDS:
        return reject("future")

    played, played_ok = _seconds(raw, "played_seconds", subject_kind)
    if not played_ok:
        return reject("bad_played_seconds")
    duration, duration_ok = _seconds(raw, "duration_seconds", subject_kind)
    if not duration_ok:
        return reject("bad_duration_seconds")

    return SuppressionEvent(
        event_id=event_id,
        client=client,
        kind=kind,
        subject_kind=subject_kind,
        subject_id=subject_id,
        mbid=mbid,
        occurred_at=occurred_at,
        played_seconds=played,
        duration_seconds=duration,
    )


def validate_events(
    raw_events: Sequence[Any], now: float,
) -> tuple[tuple[SuppressionEvent, ...], tuple[Rejection, ...]]:
    """Validate a batch of raw event mappings against ``now`` (epoch seconds).

    Returns ``(accepted, rejections)``. A batch over ``MAX_BATCH`` is rejected whole with
    ``Rejection(-1, "batch_too_large")`` and nothing is accepted. Otherwise each item is judged on its
    own; a duplicate ``event_id`` of an already accepted event is dropped without a rejection. Bad
    data never raises; a non-finite ``now`` or a non-sequence batch is a caller error and does.
    Inputs are not modified.
    """
    current = _finite(now)
    if current is None:
        raise ValueError("now must be a finite number of epoch seconds")
    if not isinstance(raw_events, (list, tuple)):
        raise TypeError("raw_events must be a list or tuple of mappings")
    if len(raw_events) > MAX_BATCH:
        return (), (Rejection(-1, "batch_too_large"),)

    accepted: list[SuppressionEvent] = []
    rejected: list[Rejection] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_events):
        parsed = _parse(index, raw, current)
        if isinstance(parsed, Rejection):
            rejected.append(parsed)
            continue
        if parsed.event_id in seen:
            continue
        seen.add(parsed.event_id)
        accepted.append(parsed)
    return tuple(accepted), tuple(rejected)


def _event_key(event: SuppressionEvent) -> tuple:
    """Total order over events: time first, then every field, so ties never depend on input order."""
    return (
        event.occurred_at,
        event.event_id,
        event.subject_kind,
        event.subject_id,
        event.kind,
        event.client,
        event.mbid or "",
        -1.0 if event.played_seconds is None else event.played_seconds,
        -1.0 if event.duration_seconds is None else event.duration_seconds,
    )


def build_suppression(events: Sequence[SuppressionEvent], now: float) -> tuple[SuppressionEntry, ...]:
    """Build the per-subject suppression view at ``now``, newest subject first.

    Events are deduplicated by ``event_id``, keeping the earliest ``occurred_at``. Only events with
    ``0 <= now - occurred_at <= EXPIRY_SECONDS`` count. Subjects with no active event are omitted.
    Ties on ``last_event_at`` sort by ``subject_kind`` then ``subject_id``. Inputs are not modified.
    """
    current = _finite(now)
    if current is None:
        raise ValueError("now must be a finite number of epoch seconds")

    seen: set[str] = set()
    unique: list[SuppressionEvent] = []
    for event in sorted(events, key=_event_key):
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        unique.append(event)

    # subject -> [weight sum, active events, active skips, newest active time]
    groups: dict[tuple[str, str], list[Any]] = {}
    for event in unique:
        age = current - event.occurred_at
        if age < 0 or age > EXPIRY_SECONDS:
            continue
        weight = 2.0 ** (-age / NEGATIVE_HALF_LIFE_SECONDS)
        acc = groups.setdefault((event.subject_kind, event.subject_id), [0.0, 0, 0, event.occurred_at])
        acc[0] += weight
        acc[1] += 1
        if event.kind == _SKIP:
            acc[2] += 1
        acc[3] = max(acc[3], event.occurred_at)

    entries = [
        SuppressionEntry(
            subject_kind=subject_kind,
            subject_id=subject_id,
            weight=round(min(total, MAX_WEIGHT), WEIGHT_PLACES),
            events=count,
            skips=skips,
            last_event_at=last,
        )
        for (subject_kind, subject_id), (total, count, skips, last) in groups.items()
    ]
    entries.sort(key=lambda entry: (-entry.last_event_at, entry.subject_kind, entry.subject_id))
    return tuple(entries)
