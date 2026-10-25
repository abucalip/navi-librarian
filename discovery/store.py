"""SQLite persistence for cached discovery-list payloads.

This module deliberately knows nothing about Navidrome, recommendation logic, or
server initialization, so its storage behavior can be tested through normal imports.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
from os import PathLike
from typing import Any


def _ensure_schema(db: sqlite3.Connection) -> None:
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS discovery_lists (
            name TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            generated_at REAL NOT NULL
        )
        """
    )


def read_list(database_path: str | PathLike[str], name: str) -> dict[str, Any] | None:
    """Read one cached list, returning None when absent or malformed."""
    with sqlite3.connect(database_path, timeout=10) as db:
        _ensure_schema(db)
        row = db.execute(
            "SELECT payload_json, generated_at FROM discovery_lists WHERE name = ?",
            (name,),
        ).fetchone()

    if row is None:
        return None
    try:
        payload = json.loads(row[0])
    except (ValueError, TypeError):
        return None
    return {"payload": payload, "generated_at": row[1]}



def delete_prefix_except(
    database_path: str | PathLike[str],
    prefix: str,
    keep_prefix: str,
) -> int:
    """Delete cached lists whose name starts with ``prefix`` but not with ``keep_prefix``.

    Prefixes are compared as plain text, not LIKE patterns, so names with ``%`` or ``_`` are
    matched exactly. ``keep_prefix`` must start with ``prefix``. Returns the number of rows removed.
    """
    if not keep_prefix.startswith(prefix):
        raise ValueError("keep_prefix must start with prefix")
    with sqlite3.connect(database_path, timeout=10) as db:
        _ensure_schema(db)
        cursor = db.execute(
            "DELETE FROM discovery_lists "
            "WHERE substr(name, 1, ?) = ? AND substr(name, 1, ?) <> ?",
            (len(prefix), prefix, len(keep_prefix), keep_prefix),
        )
        return cursor.rowcount


_RECOMMENDATION_HISTORY_RETENTION_SECONDS = 30 * 24 * 60 * 60
_RECOMMENDATION_HISTORY_MAX_ROWS = 2000


def recommendation_identity_hash(recommendation: dict[str, Any]) -> str | None:
    """Return a SHA-256 hash of normalized artist/album identity."""
    import hashlib
    import unicodedata

    artist = " ".join(
        unicodedata.normalize("NFKC", str(recommendation.get("artist") or ""))
        .casefold().split()
    )
    album = " ".join(
        unicodedata.normalize("NFKC", str(recommendation.get("album") or ""))
        .casefold().split()
    )
    if not artist or not album:
        return None
    return hashlib.sha256(f"{artist}\0{album}".encode("utf-8")).hexdigest()


def _recommendation_identity_hash(recommendation: dict[str, Any]) -> str | None:
    """Compatibility alias for the persisted-history identity contract."""
    return recommendation_identity_hash(recommendation)


def _ensure_recommendation_history_schema(db: sqlite3.Connection) -> None:
    db.execute(
        """CREATE TABLE IF NOT EXISTS recommendation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            generated_at REAL NOT NULL,
            identity_hash TEXT NOT NULL,
            rank INTEGER NOT NULL CHECK (rank >= 1)
        )"""
    )
    db.execute(
        "CREATE INDEX IF NOT EXISTS idx_recommendation_history_identity_time "
        "ON recommendation_history(identity_hash, generated_at DESC)"
    )


def _record_recommendation_batch_db(
    db: sqlite3.Connection,
    recommendations: list[Any],
    *,
    generated_at: float,
) -> int:
    """Append a bounded, identity-hashed snapshot of a successfully stored list."""
    _ensure_recommendation_history_schema(db)
    rows = []
    for rank, recommendation in enumerate(recommendations[:20], start=1):
        if not isinstance(recommendation, dict):
            continue
        identity_hash = _recommendation_identity_hash(recommendation)
        if identity_hash:
            rows.append((generated_at, identity_hash, rank))
    if rows:
        db.executemany(
            "INSERT INTO recommendation_history(generated_at, identity_hash, rank) VALUES (?, ?, ?)",
            rows,
        )
    db.execute(
        "DELETE FROM recommendation_history WHERE generated_at < ?",
        (generated_at - _RECOMMENDATION_HISTORY_RETENTION_SECONDS,),
    )
    db.execute(
        "DELETE FROM recommendation_history WHERE id NOT IN "
        "(SELECT id FROM recommendation_history ORDER BY generated_at DESC, id DESC LIMIT ?)",
        (_RECOMMENDATION_HISTORY_MAX_ROWS,),
    )
    return len(rows)


def recent_recommendation_history(
    database_path: str | PathLike[str],
    *,
    now: float | None = None,
    within_seconds: float = _RECOMMENDATION_HISTORY_RETENTION_SECONDS,
) -> list[dict[str, Any]]:
    """Return recent hashed identities and rank/timestamp, newest occurrence first."""
    timestamp = time.time() if now is None else float(now)
    if within_seconds < 0 or not math.isfinite(float(within_seconds)):
        raise ValueError("within_seconds must be finite and non-negative")
    with sqlite3.connect(database_path, timeout=10) as db:
        _ensure_recommendation_history_schema(db)
        rows = db.execute(
            "SELECT identity_hash, generated_at, rank FROM recommendation_history "
            "WHERE generated_at >= ? AND generated_at <= ? "
            "ORDER BY generated_at DESC, id DESC LIMIT ?",
            (timestamp - float(within_seconds), timestamp, _RECOMMENDATION_HISTORY_MAX_ROWS),
        ).fetchall()
    return [
        {"identity_hash": row[0], "generated_at": row[1], "rank": row[2]}
        for row in rows
    ]


def write_list(
    database_path: str | PathLike[str],
    name: str,
    payload: Any,
    *,
    generated_at: float | None = None,
) -> None:
    """Atomically replace a cached list payload and its generation timestamp."""
    timestamp = time.time() if generated_at is None else float(generated_at)
    encoded = json.dumps(payload, ensure_ascii=False)
    with sqlite3.connect(database_path, timeout=10) as db:
        _ensure_schema(db)
        db.execute(
            "INSERT OR REPLACE INTO discovery_lists "
            "(name, payload_json, generated_at) VALUES (?, ?, ?)",
            (name, encoded, timestamp),
        )
        if name == "personal" and isinstance(payload, dict):
            recommendations = payload.get("recommendations")
            if isinstance(recommendations, list):
                _record_recommendation_batch_db(db, recommendations, generated_at=timestamp)
        db.commit()


def record_discovery_refresh_outcome(
    database_path: str | PathLike[str],
    *,
    list_name: str,
    origin: str,
    status: str,
    generated_at: float | None = None,
    item_count: int | None = None,
    error_type: str | None = None,
) -> dict[str, Any]:
    """Persist only the latest bounded refresh outcome per list and trigger."""
    import re

    if list_name != "personal":
        raise ValueError("unsupported discovery list for refresh diagnostics")
    if origin not in {"manual", "scheduler", "read"}:
        raise ValueError("unsupported discovery refresh origin")
    if status not in {"success", "error", "already_running", "rejected"}:
        raise ValueError("unsupported discovery refresh status")
    if item_count is not None and (type(item_count) is not int or item_count < 0):
        raise ValueError("item_count must be a non-negative integer")
    if error_type is not None and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", error_type):
        error_type = "OtherError"

    timestamp = time.time() if generated_at is None else float(generated_at)
    outcome = {
        "list_name": list_name,
        "origin": origin,
        "status": status,
        "generated_at": timestamp,
        "item_count": item_count,
        "error_type": error_type,
    }
    with sqlite3.connect(database_path, timeout=10) as db:
        db.execute(
            """CREATE TABLE IF NOT EXISTS discovery_refresh_outcomes (
                list_name TEXT NOT NULL,
                origin TEXT NOT NULL,
                status TEXT NOT NULL,
                generated_at REAL NOT NULL,
                item_count INTEGER,
                error_type TEXT,
                PRIMARY KEY (list_name, origin)
            )"""
        )
        db.execute(
            """INSERT OR REPLACE INTO discovery_refresh_outcomes
            (list_name, origin, status, generated_at, item_count, error_type)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (list_name, origin, status, timestamp, item_count, error_type),
        )
        db.commit()
    return outcome


def record_recommendation_pool_diagnostic(
    database_path: str | PathLike[str],
    recording_mbids: list[str],
    recommendation_keys: list[str],
    metrics: dict[str, Any],
    *,
    generated_at: float | None = None,
) -> dict[str, Any]:
    """Persist one bounded, privacy-conscious recommendation-pool snapshot.

    Raw recording MBIDs and album identities are never stored. SHA-256 hashes
    allow set-overlap comparisons with the preceding refresh; only the latest
    snapshot is retained.
    """
    import hashlib

    def digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    timestamp = time.time() if generated_at is None else float(generated_at)
    recording_hashes = sorted({digest(str(value)) for value in recording_mbids if value})[:100]
    recommendation_hashes = sorted({digest(str(value)) for value in recommendation_keys if value})[:20]
    pool_fingerprint = digest("\n".join(recording_hashes))
    recommendation_fingerprint = digest("\n".join(recommendation_hashes))

    with sqlite3.connect(database_path, timeout=10) as db:
        _ensure_schema(db)
        db.execute(
            """CREATE TABLE IF NOT EXISTS recommendation_pool_diagnostics (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                generated_at REAL NOT NULL,
                pool_fingerprint TEXT NOT NULL,
                recording_hashes_json TEXT NOT NULL,
                recommendation_fingerprint TEXT NOT NULL,
                recommendation_hashes_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL
            )"""
        )
        previous = db.execute(
            "SELECT recording_hashes_json, recommendation_hashes_json "
            "FROM recommendation_pool_diagnostics WHERE id = 1"
        ).fetchone()
        previous_recordings = set(json.loads(previous[0])) if previous else set()
        previous_recommendations = set(json.loads(previous[1])) if previous else set()
        current_recordings = set(recording_hashes)
        current_recommendations = set(recommendation_hashes)

        def jaccard(left: set[str], right: set[str]) -> float | None:
            if not left and not right:
                return None
            union = left | right
            return round(len(left & right) / len(union), 6) if union else None

        diagnostic = {
            "generated_at": timestamp,
            "refresh_origin": (
                metrics.get("refresh_origin")
                if metrics.get("refresh_origin") in {"direct_api", "manual", "scheduler", "read"}
                else "unspecified"
            ),
            "cf_pool_fingerprint": pool_fingerprint,
            "cf_recordings_returned": int(metrics.get("cf_recordings_returned", len(recording_mbids))),
            "cf_recordings_with_metadata": int(metrics.get("cf_recordings_resolved", 0)),
            "resolved_album_count": int(metrics.get("resolved_album_count", 0)),
            "cf_recording_jaccard_previous": jaccard(previous_recordings, current_recordings) if previous else None,
            "final_list_fingerprint": recommendation_fingerprint,
            "final_list_jaccard_previous": jaccard(previous_recommendations, current_recommendations) if previous else None,
            "supplementary_cache_hits": int(metrics.get("supplementary_cache_hits", 0)),
            "supplementary_cache_misses": int(metrics.get("supplementary_cache_misses", 0)),
            "candidate_counts_by_source": dict(metrics.get("candidate_counts_by_source", {})),
            "candidate_diagnostics": metrics.get("candidate_diagnostics", {}),
            "profile_list_generated_at": timestamp,
        }
        db.execute(
            """INSERT OR REPLACE INTO recommendation_pool_diagnostics
            (id, generated_at, pool_fingerprint, recording_hashes_json,
             recommendation_fingerprint, recommendation_hashes_json, metrics_json)
            VALUES (1, ?, ?, ?, ?, ?, ?)""",
            (timestamp, pool_fingerprint, json.dumps(recording_hashes),
             recommendation_fingerprint, json.dumps(recommendation_hashes),
             json.dumps(diagnostic, ensure_ascii=False, sort_keys=True)),
        )
        db.commit()
    # Keep the trigger in persisted metrics only; do not expand the API payload.
    public_diagnostic = dict(diagnostic)
    public_diagnostic.pop("refresh_origin", None)
    public_diagnostic.pop("candidate_diagnostics", None)
    return public_diagnostic

def record_recommendation_diagnostics(
    database_path: str | PathLike[str],
    gathered: dict[str, Any],
    albums: Any,
    recommendations: list[dict[str, Any]],
    *,
    refresh_origin: str = "direct_api",
    candidate_diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Persist the bounded pool snapshot using the completed gathering result."""
    from collections import Counter
    from discovery.candidate_supply import summarize_candidate_stages
    from recommendation.diagnostics import summarize_candidate_diagnostics

    from recommendation_run_metrics import snapshot_and_reset

    albums = list(albums)
    aggregate = summarize_candidate_diagnostics(gathered, candidate_diagnostics or [])
    aggregate["run_metrics"] = snapshot_and_reset()
    aggregate["candidate_supply"] = {
        **aggregate["candidate_supply"],
        "stages": summarize_candidate_stages(albums, candidate_diagnostics or []),
    }
    return record_recommendation_pool_diagnostic(
        database_path,
        gathered.get("cf_recording_mbids", []),
        [
            f"{item.get('artist', '')}|{item.get('album', '')}"
            for item in recommendations
        ],
        {
            "refresh_origin": refresh_origin,
            "cf_recordings_returned": gathered.get("cf_recordings_returned", 0),
            "cf_recordings_resolved": gathered.get("cf_recordings_resolved", 0),
            "resolved_album_count": len(albums),
            "supplementary_cache_hits": gathered.get("supplementary_cache_hits", 0),
            "supplementary_cache_misses": gathered.get("supplementary_cache_misses", 0),
            "candidate_counts_by_source": dict(Counter(
                item.get("discovery_source", "listenbrainz") for item in albums
            )),
            "candidate_diagnostics": aggregate,
        },
    )

