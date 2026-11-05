"""The ``/changes?since=`` feed: which resources changed after a cursor.

Cursors are the global change sequence kept in the store. A client stores the
``cursor`` it was given and sends it back as ``since``. A cursor ahead of the server
(for example after the store was rebuilt) cannot be trusted, so the response sets
``reset`` and lists every resource, telling the client to refresh everything.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ..store import generations


class ChangesError(ValueError):
    """The ``since`` value is not a usable cursor."""


def parse_since(raw: str | int | None) -> int:
    """Turn a query value into a cursor; a missing value means "from the beginning"."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return 0
    if isinstance(raw, bool):
        raise ChangesError("since must be a whole number")
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ChangesError("since must be a whole number") from None
    if value < 0:
        raise ChangesError("since must not be negative")
    return value


def build_changes(db: sqlite3.Connection, since: int = 0) -> dict[str, Any]:
    """Resources changed after ``since``, oldest change first, plus the new cursor."""
    cursor = generations.change_seq(db)
    reset = since > cursor
    changed = generations.changed_since(db, 0 if reset else since)
    versions = generations.data_versions(db)
    return {
        "cursor": cursor,
        "reset": reset,
        "generation": generations.current_generation(db),
        "changes": [
            {"resource": name, "data_version": versions.get(name, 0), "changed_at": seq}
            for name, seq in sorted(changed.items(), key=lambda item: (item[1], item[0]))
        ],
    }
