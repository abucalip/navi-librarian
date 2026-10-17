"""SQLite persistence for cached discovery-list payloads.

This module deliberately knows nothing about Navidrome, recommendation logic, or
server initialization, so its storage behavior can be tested through normal imports.
"""
from __future__ import annotations

import json
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
        db.commit()


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
    return diagnostic

def record_recommendation_diagnostics(
    database_path: str | PathLike[str],
    gathered: dict[str, Any],
    albums: Any,
    recommendations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist the bounded pool snapshot using the completed gathering result."""
    from collections import Counter

    albums = list(albums)
    return record_recommendation_pool_diagnostic(
        database_path,
        gathered.get("cf_recording_mbids", []),
        [
            f"{item.get('artist', '')}|{item.get('album', '')}"
            for item in recommendations
        ],
        {
            "cf_recordings_returned": gathered.get("cf_recordings_returned", 0),
            "cf_recordings_resolved": gathered.get("cf_recordings_resolved", 0),
            "resolved_album_count": len(albums),
            "supplementary_cache_hits": gathered.get("supplementary_cache_hits", 0),
            "supplementary_cache_misses": gathered.get("supplementary_cache_misses", 0),
            "candidate_counts_by_source": dict(Counter(
                item.get("discovery_source", "listenbrainz") for item in albums
            )),
        },
    )

