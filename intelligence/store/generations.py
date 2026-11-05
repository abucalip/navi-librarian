"""Derivation generation and per-resource ``data_version`` counters (docs/ServerV2.md 6.4).

The generation stamps every derived row. Changing matching logic bumps it, and derived
tables rebuild from observations without refetching. A ``data_version`` per
client-visible resource changes whenever that resource changes, which is what ETags and
a ``/changes?since=`` feed are built from. Both live in the ``meta`` table.
"""
from __future__ import annotations

import sqlite3

GENERATION_KEY = "generation"
DATA_VERSION_PREFIX = "data_version:"


def _read(db: sqlite3.Connection, key: str) -> int:
    row = db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return int(row["value"]) if row else 0


def _increment(db: sqlite3.Connection, key: str, floor: int = 0) -> int:
    """Atomically add one to a counter and return the new value."""
    with db:
        db.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT (key) DO UPDATE SET value = CAST(value AS INTEGER) + 1",
            (key, str(floor + 1)),
        )
        return _read(db, key)


def current_generation(db: sqlite3.Connection) -> int:
    """The generation new derived rows are stamped with (at least 1)."""
    return max(_read(db, GENERATION_KEY), 1)


def bump_generation(db: sqlite3.Connection) -> int:
    """Start a new generation, for example after a matching-logic change."""
    return _increment(db, GENERATION_KEY, floor=1)


def data_version(db: sqlite3.Connection, resource: str) -> int:
    """The change counter for one client-visible resource (0 if it never changed)."""
    _check_resource(resource)
    return _read(db, DATA_VERSION_PREFIX + resource)


def bump_data_version(db: sqlite3.Connection, resource: str) -> int:
    """Record that a resource changed; returns its new counter."""
    _check_resource(resource)
    return _increment(db, DATA_VERSION_PREFIX + resource)


def data_versions(db: sqlite3.Connection) -> dict[str, int]:
    """Every resource counter, for the capabilities and changes responses."""
    rows = db.execute("SELECT key, value FROM meta WHERE key LIKE ?", (DATA_VERSION_PREFIX + "%",)).fetchall()
    return {r["key"][len(DATA_VERSION_PREFIX):]: int(r["value"]) for r in rows}


def _check_resource(resource: str) -> None:
    if not resource or resource != resource.strip() or ":" in resource:
        raise ValueError(f"invalid resource name: {resource!r}")
