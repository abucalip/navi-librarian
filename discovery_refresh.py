"""Coordination for refreshing cached discovery lists.

Provider calls, list construction, persistence, and locking remain injected so
this module can be tested without importing the web service or contacting APIs.
"""
from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from threading import Lock
from typing import Any

import discovery_snapshot


def cache_staleness_reason(
    cached: Mapping[str, Any] | None,
    *,
    now: float,
    max_age_seconds: float,
) -> str | None:
    """Return why a cached list needs refreshing, or None while it is fresh.

    Missing and malformed timestamps are stale rather than aborting the whole
    scheduler cycle. Future timestamps retain the legacy behavior and count as
    fresh until their age reaches the configured threshold.
    """
    if cached is None:
        return "missing"
    try:
        generated_at = float(cached["generated_at"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return "invalid_timestamp"
    if not math.isfinite(generated_at):
        return "invalid_timestamp"
    if now - generated_at >= max_age_seconds:
        return "expired"
    return None


def refresh_stale_lists(
    list_names: Sequence[str],
    read_cached: Callable[[str], Mapping[str, Any] | None],
    refresh_one: Callable[[str], Any],
    *,
    now: float,
    max_age_seconds: float,
) -> list[dict[str, Any]]:
    """Check each cache and refresh stale lists without one failure blocking others.

    The returned per-list diagnostics intentionally contain only bounded status,
    stage, and exception-type fields; provider exception messages may contain
    private URLs or request details and are not copied into scheduler diagnostics.
    """
    outcomes: list[dict[str, Any]] = []
    for list_name in list_names:
        try:
            cached = read_cached(list_name)
        except Exception as exc:
            outcomes.append({
                "list": list_name,
                "status": "read_failed",
                "stage": "read",
                "error_type": type(exc).__name__,
            })
            continue

        reason = cache_staleness_reason(
            cached, now=now, max_age_seconds=max_age_seconds
        )
        if reason is None:
            outcomes.append({"list": list_name, "status": "fresh"})
            continue

        try:
            result = refresh_one(list_name)
        except Exception as exc:
            outcomes.append({
                "list": list_name,
                "status": "refresh_failed",
                "stage": "refresh",
                "reason": reason,
                "error_type": type(exc).__name__,
            })
            continue

        if isinstance(result, dict) and result.get("ok") is False:
            status = result.get("status")
            outcomes.append({
                "list": list_name,
                "status": status if status == "already_running" else "refresh_failed",
                "stage": "refresh",
                "reason": reason,
            })
        else:
            outcomes.append({
                "list": list_name,
                "status": "refreshed",
                "reason": reason,
            })
    return outcomes


def _record_refresh_outcome(
    callback: Callable[[dict[str, Any]], None] | None,
    *,
    origin: str,
    status: str,
    generated_at: float | None = None,
    item_count: int | None = None,
    error_type: str | None = None,
) -> None:
    """Persist bounded refresh telemetry without affecting refresh behavior."""
    if callback is None:
        return
    outcome: dict[str, Any] = {
        "list_name": "personal",
        "origin": origin,
        "status": status,
        "generated_at": generated_at,
        "item_count": item_count,
        "error_type": error_type,
    }
    try:
        callback(outcome)
    except Exception:
        # Diagnostics must never turn a successful refresh into a failure.
        pass


def refresh_personal(
    lock: Lock,
    recommend: Callable[..., Any],
    write_list: Callable[[str, Any], None],
    *,
    count: int = 20,
    clock: Callable[[], float] = time.time,
    origin: str = "manual",
    record_outcome: Callable[[dict[str, Any]], None] | None = None,
    read_previous: Callable[[str], Mapping[str, Any] | None] | None = None,
    is_excluded: Callable[[Mapping[str, Any]], bool] | None = None,
) -> dict[str, Any]:
    """Refresh the personal list and record a bounded manual/scheduler outcome.

    When ``read_previous`` is given, a build that the snapshot policy rejects
    (see ``discovery_snapshot.replacement_decision``) leaves the stored list in
    place. Without it, behavior is unchanged.
    """
    if not lock.acquire(blocking=False):
        _record_refresh_outcome(
            record_outcome, origin=origin, status="already_running",
            generated_at=clock() if record_outcome is not None else None,
        )
        return {"ok": False, "status": "already_running", "list": "personal"}
    try:
        try:
            raw = recommend(count=count)
        except Exception as exc:
            _record_refresh_outcome(
                record_outcome, origin=origin, status="error",
                generated_at=clock() if record_outcome is not None else None, error_type=type(exc).__name__,
            )
            raise
        try:
            payload = json.loads(raw) if isinstance(raw, str) else raw
        except (ValueError, TypeError):
            payload = {"error": "Recommendation engine returned invalid JSON."}
        if not isinstance(payload, dict) or payload.get("error"):
            _record_refresh_outcome(
                record_outcome, origin=origin, status="error",
                generated_at=clock() if record_outcome is not None else None,
            )
            return {"ok": False, "status": "error", "details": payload}
        if read_previous is not None:
            try:
                stored = read_previous("personal")
            except Exception:
                stored = None
                replace, reason = False, "previous_read_failed"
            else:
                replace, reason = discovery_snapshot.replacement_decision(
                    stored.get("payload") if isinstance(stored, Mapping) else None,
                    payload,
                    is_excluded=is_excluded,
                )
            if not replace:
                _record_refresh_outcome(
                    record_outcome, origin=origin, status="rejected",
                    generated_at=clock() if record_outcome is not None else None,
                )
                return {"ok": False, "status": "rejected", "reason": reason, "list": "personal"}
        try:
            write_list("personal", payload)
        except Exception as exc:
            _record_refresh_outcome(
                record_outcome, origin=origin, status="error",
                generated_at=clock() if record_outcome is not None else None, error_type=type(exc).__name__,
            )
            raise
        generated_at = clock()
        item_count = len(payload.get("recommendations", []))
        _record_refresh_outcome(
            record_outcome, origin=origin, status="success",
            generated_at=generated_at, item_count=item_count,
        )
        return {
            "ok": True,
            "list": "personal",
            "generated_at": generated_at,
            "recommendations": item_count,
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


def refresh_all(
    refresh_personal_callback: Callable[[int], Any],
    refresh_other_callback: Callable[[str], Any],
) -> list[Any]:
    """Refresh all discovery lists in the legacy, deterministic order.

    Callbacks keep provider access, list locks, and persistence in their existing
    owners while this orchestration remains directly testable.
    """
    return [
        refresh_personal_callback(20),
        refresh_other_callback("classics"),
        refresh_other_callback("artist_deep_dive"),
        refresh_other_callback("new_releases"),
    ]
