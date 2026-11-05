"""Response bodies for the Library Health and unresolved-queue endpoints.

Pure builders like the rest of ``intelligence.api``: they take data in and return plain
dictionaries. ``next_after_id`` is the cursor for the next page, ``None`` on the last page.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from ..health import HealthReport
from ..resolution import unresolved
from ..store import generations

MAX_PAGE = 200
DEFAULT_PAGE = 50


def build_health_body(db: sqlite3.Connection, report: HealthReport) -> dict[str, Any]:
    """The health report with the data version it was stored under (0 if never stored)."""
    body = report.as_dict()
    body["data_version"] = generations.data_versions(db).get("health", 0)
    body["generation"] = generations.current_generation(db)
    return body


def build_unresolved_body(
    db: sqlite3.Connection,
    *,
    status: str | None = "open",
    kind: str | None = None,
    limit: int = DEFAULT_PAGE,
    after_id: int = 0,
) -> dict[str, Any]:
    """One page of the unresolved queue, oldest first."""
    limit = min(max(int(limit), 1), MAX_PAGE)
    rows = unresolved.list_unresolved(db, status=status, kind=kind, limit=limit + 1, after_id=after_id)
    page = rows[:limit]
    return {
        "items": page,
        "open_count": unresolved.count_unresolved(db, "open"),
        "next_after_id": page[-1]["id"] if len(rows) > limit else None,
        "data_version": generations.data_versions(db).get("unresolved", 0),
        "generation": generations.current_generation(db),
    }
