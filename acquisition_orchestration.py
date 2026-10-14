"""Acquisition lifecycle transitions with injected persistence/runtime dependencies.

This module owns small acquisition state transitions and coordination guards. It deliberately does not import
SQLite, MCP, application configuration, or filesystem code; callers inject those
boundaries so transitions can be tested directly and reused by MCP/web adapters.
"""
from __future__ import annotations

from typing import Any, Callable, ContextManager


def request_skip_acquisition_source(
    artist: str,
    album: str,
    *,
    initialize: Callable[[], Any],
    transition_lock: Any,
    connect: Callable[[], ContextManager[Any]],
    music_key: Callable[[str], str],
    lifecycle: Any,
    now: Callable[[], float],
    json_module: Any,
) -> dict[str, Any]:
    """Atomically request fallback only for a downloading job with eligible peers."""
    initialize()
    identity = (music_key(artist), music_key(album))
    # Serialize with dismiss/import/source-switch transitions in this process.
    with transition_lock:
        with connect() as db:
            row = db.execute(
                "SELECT status, details_json, candidate_json FROM discovery_acquisitions "
                "WHERE artist_key=? AND album_key=?", identity,
            ).fetchone()
            if not row:
                return {"ok": False, "error": lifecycle.skip_request_error(None, {})}
            try:
                candidate = json_module.loads(row[2] or "{}")
                details = json_module.loads(row[1] or "{}")
            except (ValueError, TypeError):
                candidate, details = {}, {}
            error = lifecycle.skip_request_error(row[0], candidate)
            if error:
                return {"ok": False, "error": error}
            details["skip_requested"] = True
            details["skip_requested_at"] = now()
            cursor = db.execute(
                "UPDATE discovery_acquisitions SET details_json=?, updated_at=? "
                "WHERE artist_key=? AND album_key=? AND status='downloading'",
                (json_module.dumps(details, ensure_ascii=False), now(), *identity),
            )
            if cursor.rowcount != 1:
                return {
                    "ok": False,
                    "error": "Acquisition state changed; please refresh and try again.",
                }
            db.commit()
    return {
        "ok": True,
        "status": "skip_requested",
        "message": "Switch requested; cancelling the current source before starting the next one.",
    }


def switch_source_unless_dismissed(
    artist: str,
    album: str,
    *,
    transition_lock: Any,
    is_dismissed: Callable[[str, str], bool],
    switch_source: Callable[[], Any],
) -> Any:
    """Serialize a source switch with dismissal and refuse to queue after dismissal.

    The lock intentionally covers both the dismissal check and the switch callback,
    matching the server's existing in-process transition ordering.
    """
    with transition_lock:
        if is_dismissed(artist, album):
            return None
        return switch_source()
