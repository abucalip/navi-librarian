"""Bodies for the client feedback routes (Phase 6 item 5, slice 10, D-027).

``build_intake_body`` validates a batch of raw client events and stores the accepted ones in the
owner-state file; ``build_suppression_body`` reads the decaying suppression view back. Both take the
clock as an argument. Nothing here calls a provider, logs event content, or feeds a ranking: the
memory is record-only, and the body says so (``record_only``).
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ..taste.suppression import (
    CLIENTS, EXPIRY_SECONDS, KINDS, MAX_BATCH, MAX_WEIGHT, NEGATIVE_HALF_LIFE_SECONDS, SUBJECT_KINDS,
    build_suppression, validate_events,
)
from ..taste.suppression_persistence import CONFLICT, DUPLICATE, INSERTED, insert_events, list_active_events

DEFAULT_LIMIT = 50
MAX_LIMIT = 200

ACCEPTED = "accepted"
REJECTED = "rejected"
CONFLICT_REASON = "event_id_conflict"


class BatchTooLarge(ValueError):
    """The batch has more than ``MAX_BATCH`` events; nothing was stored."""


def build_intake_body(db: sqlite3.Connection, raw_events: list[Any], now: float) -> dict[str, Any]:
    """Validate and store one batch. ``results`` has one entry per input item, in input order.

    A malformed item is ``rejected`` with a reason and never stops the rest. A replay of a stored event,
    or a repeat of an id inside the batch, is ``accepted`` with ``duplicate: true`` and changes nothing.
    The same ``event_id`` with a different payload is ``rejected`` as ``event_id_conflict`` and the
    stored row is kept.
    """
    accepted, rejections = validate_events(raw_events, now)
    if rejections and rejections[0].index == -1:
        raise BatchTooLarge(f"a batch holds at most {MAX_BATCH} events")
    outcomes = {o.event_id: o.status for o in insert_events(db, list(accepted))}
    rejected_at = {r.index: r.reason for r in rejections}

    results: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_events):
        if index in rejected_at:
            results.append({"index": index, "status": REJECTED, "reason": rejected_at[index]})
            continue
        status = outcomes[raw["event_id"].lower()]
        if status == CONFLICT:
            results.append({"index": index, "status": REJECTED, "reason": CONFLICT_REASON})
        else:
            results.append({"index": index, "status": ACCEPTED, "duplicate": status == DUPLICATE or _repeat(raw_events, index)})
    return {
        "received": len(raw_events),
        "inserted": sum(1 for s in outcomes.values() if s == INSERTED),
        "accepted": sum(1 for r in results if r["status"] == ACCEPTED),
        "rejected": sum(1 for r in results if r["status"] == REJECTED),
        "results": results,
    }


def _repeat(raw_events: list[Any], index: int) -> bool:
    """True when an earlier, valid item of this batch carries the same (case-insensitive) event id."""
    wanted = raw_events[index]["event_id"].lower()
    return any(
        isinstance(earlier, dict) and isinstance(earlier.get("event_id"), str) and earlier["event_id"].lower() == wanted
        for earlier in raw_events[:index]
    )


def build_suppression_body(db: sqlite3.Connection, now: float, limit: int = DEFAULT_LIMIT, offset: int = 0) -> dict[str, Any]:
    """One page of active suppression entries, newest first. Empty memory is an empty list."""
    limit = min(max(int(limit), 1), MAX_LIMIT)
    offset = max(int(offset), 0)
    entries = build_suppression(list_active_events(db, now), now)
    page = entries[offset:offset + limit]
    return {
        "entries": [
            {
                "subject_kind": e.subject_kind,
                "subject_id": e.subject_id,
                "weight": e.weight,
                "events": e.events,
                "skips": e.skips,
                "last_event_at": e.last_event_at,
            }
            for e in page
        ],
        "total": len(entries),
        "next_offset": offset + limit if offset + limit < len(entries) else None,
        "as_of": now,
        "record_only": True,
        "config": {
            "half_life_days": NEGATIVE_HALF_LIFE_SECONDS // 86400,
            "expiry_days": EXPIRY_SECONDS // 86400,
            "max_weight": MAX_WEIGHT,
            "max_batch": MAX_BATCH,
            "clients": list(CLIENTS),
            "kinds": list(KINDS),
            "subject_kinds": list(SUBJECT_KINDS),
        },
    }
