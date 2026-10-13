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
