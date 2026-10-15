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


def queue_candidate_unless_dismissed(
    artist: str,
    album: str,
    *,
    transition_lock: Any,
    is_dismissed: Callable[[str, str], bool],
    queue_source: Callable[[], Any],
) -> Any:
    """Queue a candidate only while the shared dismissal transition is held."""
    with transition_lock:
        if is_dismissed(artist, album):
            return None
        return queue_source()


def import_source_unless_dismissed(
    artist: str,
    album: str,
    *,
    transition_lock: Any,
    is_dismissed: Callable[[str, str], bool],
    import_source: Callable[[], Any],
) -> Any:
    """Run verified-source import only while serialized against dismissal.

    The transition lock deliberately spans both the dismissal check and the
    entire import callback so dismissal cannot win between those operations.
    """
    with transition_lock:
        if is_dismissed(artist, album):
            return "dismissed"
        return import_source()


def existing_acquisition_response(
    artist: str,
    album: str,
    identity: tuple[str, str],
    existing_job: dict[str, Any] | None,
    existing_status: str | None,
    watcher_active: bool,
    *,
    start_watcher: Callable[..., Any],
    watcher_lock: Any,
    active_watchers: set[tuple[str, str]],
    lifecycle: Any,
    json_module: Any,
) -> str | None:
    """Return a response for an existing acquisition, or None when a new search may proceed.

    The caller holds the shared acquisition-transition lock across this decision.
    The watcher lock is acquired only to read the watcher reservation after startup,
    preserving the server's existing lock order and avoiding duplicate queue attempts.
    """
    if existing_status in {"importing", "imported"}:
        return json_module.dumps({
            "ok": False, "status": existing_status, "artist": artist, "album": album,
            "message": "This album is already being imported or is in the library.",
        }, ensure_ascii=False)

    if existing_status == "downloading" and not watcher_active:
        candidate = (existing_job or {}).get("candidate") or {}
        settings = (existing_job or {}).get("settings") or {}
        if lifecycle.should_resume_monitor(existing_status, candidate, watcher_active):
            try:
                start_watcher(
                    existing_job["artist"], existing_job["album"], candidate, settings,
                )
            except Exception as exc:
                return json_module.dumps({
                    "ok": False, "status": "monitor_recovery_failed",
                    "artist": artist, "album": album,
                    "message": (
                        "The saved download could not be resumed safely. "
                        "Inspect slskd and acquisition status before retrying."
                    ),
                    "error": type(exc).__name__,
                }, ensure_ascii=False)
            with watcher_lock:
                recovery_started = identity in active_watchers
            return json_module.dumps({
                "ok": True, "status": (
                    "recovery_started" if recovery_started else "already_in_progress"
                ),
                "artist": artist, "album": album,
                "message": (
                    "Resumed monitoring the saved download without queueing "
                    "another source."
                ),
            }, ensure_ascii=False)
        return json_module.dumps({
            "ok": False, "status": "recovery_unavailable",
            "artist": artist, "album": album,
            "message": (
                "The saved download has no usable source details. Inspect "
                "slskd and acquisition status before retrying."
            ),
        }, ensure_ascii=False)

    if (
        watcher_active
        or existing_status == "downloading"
    ):
        return json_module.dumps({
            "ok": False, "status": "already_in_progress", "artist": artist, "album": album,
            "message": "An acquisition request or download is already active for this album.",
        }, ensure_ascii=False)

    return None


def run_reserved_acquisition(
    identity: tuple[str, str],
    *,
    transition_lock: Any,
    active_requests: set[tuple[str, str]],
    acquire: Callable[[], Any],
) -> Any:
    """Run an already-reserved acquisition and always release its reservation.

    The caller must atomically add `identity` to `active_requests` while holding
    `transition_lock` before calling this helper. The callback runs outside the
    lock; cleanup reacquires it so a concurrent request cannot observe a stale
    reservation after the callback completes or raises.
    """
    try:
        return acquire()
    finally:
        with transition_lock:
            active_requests.discard(identity)


def reserve_acquisition_request(
    identity: tuple[str, str],
    *,
    active_requests: set[tuple[str, str]],
) -> bool:
    """Atomically reserve a new acquisition identity while the caller holds the transition lock.

    Returns False without mutation when another request already owns the identity.
    Lock ownership remains with the coordinator so its existing-job checks and this
    reservation can be one indivisible transition.
    """
    if identity in active_requests:
        return False
    active_requests.add(identity)
    return True
