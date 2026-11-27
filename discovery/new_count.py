"""Count newly generated discovery-list items since a client timestamp (Bento B0).

Pure logic kept outside ``navidrome_server.py`` (D-016) and HTTP adapters: parses an
ISO-8601 ``since`` timestamp and counts how many visible items in a discovery-list
response were produced after it.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any


def parse_since(raw: str) -> datetime:
    """Parse an ISO-8601 timestamp string into a UTC-aware ``datetime``.

    Raises ``ValueError`` when ``raw`` is empty or not a valid ISO-8601 date/time.
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError("since must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("since must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _optional_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return parse_since(value)
    except ValueError:
        return None


def _item_timestamp(item: Mapping[str, Any]) -> datetime | None:
    for field in ("added_at", "generated_at", "created_at"):
        ts = _optional_timestamp(item.get(field))
        if ts is not None:
            return ts
    return None


def count_new_items(payload: Mapping[str, Any], since: datetime) -> int:
    """Return how many visible items in ``payload`` are newer than ``since``.

    When an item carries its own timestamp (``added_at``, ``generated_at``, or
    ``created_at``), that timestamp decides; otherwise the list's ``generated_at``
    applies to the whole ``items`` list. Disabled or ungenerated lists return ``0``.
    """
    if payload.get("disabled"):
        return 0
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return 0
    list_ts = _optional_timestamp(payload.get("generated_at"))
    total = 0
    for item in items:
        ts = _item_timestamp(item) if isinstance(item, Mapping) else None
        effective = ts if ts is not None else list_ts
        if effective is not None and effective > since:
            total += 1
    return total
