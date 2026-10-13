"""Coordination for refreshing cached discovery lists.

Provider calls, list construction, persistence, and locking remain injected so
this module can be tested without importing the MCP server or contacting APIs.
"""
from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from threading import Lock
from typing import Any


def refresh_personal(
    lock: Lock,
    recommend: Callable[..., Any],
    write_list: Callable[[str, Any], None],
    *,
    count: int = 20,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Refresh the personal list, retaining the existing non-blocking lock contract."""
    if not lock.acquire(blocking=False):
        return {"ok": False, "status": "already_running", "list": "personal"}
    try:
        raw = recommend(count=count)
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            payload = {"error": "Recommendation engine returned invalid JSON."}
        if not isinstance(payload, dict) or payload.get("error"):
            return {"ok": False, "status": "error", "details": payload}
        write_list("personal", payload)
        return {
            "ok": True,
            "list": "personal",
            "generated_at": clock(),
            "recommendations": len(payload.get("recommendations", [])),
        }
    finally:
        lock.release()


def refresh_other(
    list_name: str,
    locks: Mapping[str, Lock],
    builders: Mapping[str, Callable[[], dict[str, Any]]],
    write_list: Callable[[str, Any], None],
    *,
    clock: Callable[[], float] = time.time,
) -> dict[str, Any]:
    """Refresh one named list, preserving lock, error, and response semantics."""
    lock = locks.get(list_name)
    builder = builders.get(list_name)
    if lock is None or builder is None:
        return {"ok": False, "error": "Unknown discovery list"}
    if not lock.acquire(blocking=False):
        return {"ok": False, "status": "already_running", "list": list_name}
    try:
        payload = builder()
        write_list(list_name, payload)
        return {
            "ok": True,
            "list": list_name,
            "generated_at": clock(),
            "items": len(payload.get("items", [])),
        }
    except Exception as exc:
        return {"ok": False, "list": list_name, "error": str(exc)}
    finally:
        lock.release()
