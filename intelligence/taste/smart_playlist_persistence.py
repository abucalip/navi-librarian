"""Persist smart playlist rule sets in the owner-state file (Phase 6 item 6, slice 13).

Rule sets live in ``state.smart_playlists`` (migration 3, see :mod:`intelligence.store.state`). This is a
normal mutable table: rule sets are owner configuration, not rebuildable knowledge. There is no retention
and no stored result and no refresh flag. Rows leave only through :func:`delete`.

Every write goes through :func:`~intelligence.taste.smart_playlist.validate_rule_set` first. Bad input never
raises: it comes back as a rejected outcome (or ``False`` / ``None``) with a reason, and the table is not
touched. Only programming errors (a wrong connection type) raise.

Put rules
---------
* ``rule_id`` must be a canonical lowercase UUID string, supplied by the caller (so retries are idempotent);
* the caller supplies ``now`` (epoch seconds). The clock is never read here;
* a new id is created with ``created_at == updated_at == now``;
* the same id with the same canonical content is ``unchanged``: nothing is written, ``updated_at`` stays;
* the same id with different content is ``replaced``: ``created_at`` is kept, ``updated_at`` becomes ``now``.

Nothing here calls a provider or Navidrome, defines a route, runs a job, or evaluates a rule set.
"""
from __future__ import annotations

import json
import math
import re
import sqlite3
import uuid
from dataclasses import dataclass

from .smart_playlist import RuleSet, SmartRule, ValidationError, validate_rule_set

CREATED = "created"
REPLACED = "replaced"
UNCHANGED = "unchanged"
REJECTED = "rejected"

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_COLUMNS = ('rule_id', 'name', '"match"', 'rules', '"order"', '"limit"', 'created_at', 'updated_at')
_SELECT = f"SELECT {', '.join(_COLUMNS)} FROM state.smart_playlists"


@dataclass(frozen=True)
class PutOutcome:
    rule_id: object  # echoed as supplied; may be malformed
    status: str  # CREATED, REPLACED, UNCHANGED or REJECTED
    errors: tuple[ValidationError, ...] = ()


@dataclass(frozen=True)
class SmartPlaylist:
    rule_id: str
    name: str
    match: str
    rules: tuple[SmartRule, ...]
    order: str
    limit: int | None
    created_at: float
    updated_at: float


def valid_rule_id(rule_id: object) -> bool:
    """True for a canonical lowercase hyphenated UUID string. Never raises."""
    if not isinstance(rule_id, str) or not _UUID_RE.match(rule_id):
        return False
    try:
        return str(uuid.UUID(rule_id)) == rule_id
    except ValueError:
        return False


def _valid_clock(now: object) -> bool:
    return (
        not isinstance(now, bool) and isinstance(now, (int, float))
        and math.isfinite(now) and now > 0
    )


def _content(rule_set: RuleSet) -> tuple:
    return (rule_set.name, rule_set.match, rule_set.rules, rule_set.order, rule_set.limit)


def _encode_rules(rules: tuple[SmartRule, ...]) -> str:
    return json.dumps(
        [{"field": r.field, "op": r.op, "value": r.value} for r in rules],
        separators=(",", ":"), sort_keys=True,
    )


def _decode_rules(text: str) -> tuple[SmartRule, ...]:
    return tuple(SmartRule(item["field"], item["op"], item["value"]) for item in json.loads(text))


def _row_to_playlist(row: sqlite3.Row | tuple) -> SmartPlaylist:
    rule_id, name, match, rules, order, limit, created_at, updated_at = row
    return SmartPlaylist(
        rule_id=rule_id, name=name, match=match, rules=_decode_rules(rules), order=order,
        limit=limit, created_at=created_at, updated_at=updated_at,
    )


def put(db: sqlite3.Connection, rule_id: object, raw: object, now: object) -> PutOutcome:
    """Create or replace a rule set under ``rule_id``. Never raises on bad input.

    Returns ``created``, ``replaced`` or ``unchanged`` on success, or ``rejected`` with the reasons. A
    rejected call writes nothing.
    """
    if not valid_rule_id(rule_id):
        return PutOutcome(rule_id, REJECTED, (ValidationError("rule_id", "bad_rule_id"),))
    if not _valid_clock(now):
        return PutOutcome(rule_id, REJECTED, (ValidationError("now", "bad_clock"),))

    rule_set, errors = validate_rule_set(raw)
    if rule_set is None:
        return PutOutcome(rule_id, REJECTED, tuple(errors))

    stamp = float(now)
    try:
        with db:
            row = db.execute(f"{_SELECT} WHERE rule_id = ?", (rule_id,)).fetchone()
            if row is None:
                db.execute(
                    "INSERT INTO state.smart_playlists "
                    "(rule_id, name, \"match\", rules, \"order\", \"limit\", created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (rule_id, rule_set.name, rule_set.match, _encode_rules(rule_set.rules),
                     rule_set.order, rule_set.limit, stamp, stamp),
                )
                return PutOutcome(rule_id, CREATED)
            stored = _row_to_playlist(row)
            if _content(stored) == _content(rule_set):
                return PutOutcome(rule_id, UNCHANGED)
            db.execute(
                "UPDATE state.smart_playlists SET name = ?, \"match\" = ?, rules = ?, \"order\" = ?, "
                "\"limit\" = ?, updated_at = ? WHERE rule_id = ?",
                (rule_set.name, rule_set.match, _encode_rules(rule_set.rules), rule_set.order,
                 rule_set.limit, stamp, rule_id),
            )
            return PutOutcome(rule_id, REPLACED)
    except sqlite3.IntegrityError:
        # The table's CHECKs are the storage contract; validation should already have caught this.
        return PutOutcome(rule_id, REJECTED, (ValidationError("", "rejected_by_store"),))


def get(db: sqlite3.Connection, rule_id: object) -> SmartPlaylist | None:
    """The stored rule set with this id, or None (also None for a malformed id)."""
    if not valid_rule_id(rule_id):
        return None
    row = db.execute(f"{_SELECT} WHERE rule_id = ?", (rule_id,)).fetchone()
    return None if row is None else _row_to_playlist(row)


def list_playlists(db: sqlite3.Connection) -> tuple[SmartPlaylist, ...]:
    """All stored rule sets, oldest first, with ``rule_id`` as the tie-break (a stable order)."""
    rows = db.execute(f"{_SELECT} ORDER BY created_at, rule_id").fetchall()
    return tuple(_row_to_playlist(row) for row in rows)


def delete(db: sqlite3.Connection, rule_id: object) -> bool:
    """Explicitly delete one rule set. True if a row existed; False if not or if the id is malformed."""
    if not valid_rule_id(rule_id):
        return False
    with db:
        cursor = db.execute("DELETE FROM state.smart_playlists WHERE rule_id = ?", (rule_id,))
    return cursor.rowcount == 1
