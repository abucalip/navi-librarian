"""Bodies for the smart playlist routes (Phase 6 item 6, slice 14).

Pure builders over the owner-state rule sets (slice 13) and the evaluator (slice 12). Each takes the
clock as an argument. Nothing here calls Navidrome or a provider, runs a job, or writes to Navidrome:
a result is evaluated on request and not stored, and the server never exports a playlist (owner
decision, 2026-11-07).
"""
from __future__ import annotations

import sqlite3
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from ..taste import smart_playlist as engine
from ..taste import smart_playlist_persistence as store

CREATED, REPLACED, UNCHANGED = store.CREATED, store.REPLACED, store.UNCHANGED
REJECTED = store.REJECTED
BAD_ID_REASON = "bad_rule_id"


def playlist_body(p: store.SmartPlaylist) -> dict[str, Any]:
    return {
        "rule_id": p.rule_id,
        "name": p.name,
        "match": p.match,
        "rules": [{"field": r.field, "op": r.op, "value": r.value} for r in p.rules],
        "order": p.order,
        "limit": p.limit,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def build_list_body(db: sqlite3.Connection) -> dict[str, Any]:
    """All stored rule sets, oldest first. No rule sets is an empty list."""
    playlists = [playlist_body(p) for p in store.list_playlists(db)]
    return {"playlists": playlists, "total": len(playlists), "config": build_config()}


def build_config() -> dict[str, Any]:
    return {
        "fields": list(engine.FIELDS),
        "text_ops": list(engine.TEXT_OPS),
        "numeric_ops": list(engine.NUMERIC_OPS),
        "insight_ops": list(engine.INSIGHT_OPS),
        "orders": list(engine.ORDERS),
        "matches": list(engine.MATCHES),
        "min_limit": engine.MIN_LIMIT,
        "max_limit": engine.MAX_LIMIT,
        "max_rules": engine.MAX_RULES,
        "max_name_length": engine.MAX_NAME_LENGTH,
        "max_value_length": engine.MAX_VALUE_LENGTH,
    }


def build_put_body(db: sqlite3.Connection, rule_id: str, raw: Any, now: float) -> tuple[bool, dict[str, Any]]:
    """Create or replace one rule set. Returns ``(ok, body)``; a rejected call stores nothing."""
    outcome = store.put(db, rule_id, raw, now)
    if outcome.status == REJECTED:
        return False, {"status": REJECTED, "errors": [{"path": e.path, "reason": e.reason} for e in outcome.errors]}
    stored = store.get(db, rule_id)
    return True, {"status": outcome.status, "playlist": playlist_body(stored)}


def build_get_body(db: sqlite3.Connection, rule_id: str) -> dict[str, Any] | None:
    stored = store.get(db, rule_id)
    return None if stored is None else playlist_body(stored)


def delete_playlist(db: sqlite3.Connection, rule_id: str) -> bool:
    return store.delete(db, rule_id)


def build_result_body(
    db: sqlite3.Connection, rule_id: str, songs: Sequence[Mapping[str, Any]], now: float, seed: int = 0,
) -> dict[str, Any] | None:
    """Evaluate one stored rule set now over ``songs``. ``None`` when the id is not stored.

    No insight lookups are wired yet, so ``obscurity_band`` and ``in_lens`` rules come back unfinished
    and listed in ``missing_data``. That is a report, never an error.
    """
    stored = store.get(db, rule_id)
    if stored is None:
        return None
    rule_set = engine.RuleSet(stored.name, stored.match, stored.rules, stored.order, stored.limit)
    result = engine.evaluate(rule_set, songs, now=now, insights=None, seed=seed)
    return {
        "rule_id": rule_id,
        "song_ids": list(result.song_ids),
        "matched": result.matched,
        "returned": len(result.song_ids),
        "unfinished": list(result.unfinished),
        "missing_data": list(result.missing_data),
        "evaluated_at": now,
        "songs_considered": len(songs),
        "stored": False,
    }


def songs_from_subsonic(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Map Subsonic song entries to evaluator rows. Missing values stay absent (unknown, not zero)."""
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str) or not item["id"]:
            continue
        row: dict[str, Any] = {"id": item["id"]}
        for src, dst in (("artist", "artist"), ("title", "title"), ("genre", "genre"), ("suffix", "format"),
                         ("year", "year"), ("playCount", "plays"), ("userRating", "rating"), ("bitRate", "bitrate")):
            if item.get(src) is not None:
                row[dst] = item[src]
        for src, dst in (("created", "added_at"), ("played", "played_at")):
            stamp = _epoch(item.get(src))
            if stamp is not None:
                row[dst] = stamp
        rows.append(row)
    return rows


def _epoch(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    stamp = parsed.timestamp()
    return stamp if stamp > 0 else None
