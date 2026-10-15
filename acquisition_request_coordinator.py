"""Top-level acquisition request coordination with injected server dependencies.

The coordinator preserves the legacy request response contract while keeping
locks, persisted state, watcher lifecycle, and the acquisition implementation
owned by the caller.
"""
from __future__ import annotations

from typing import Any, Callable

from acquisition_orchestration import (
    existing_acquisition_response,
    reactivate_dismissed_acquisition_if_needed,
    reserve_acquisition_request,
    run_reserved_acquisition,
)


def acquire_album_request(
    artist: str,
    album: str,
    metadata_json: str = "{}",
    auto_queue: bool = True,
    *,
    music_key: Callable[[str], str],
    transition_lock: Any,
    watcher_lock: Any,
    active_watchers: set[tuple[str, str]],
    active_requests: set[tuple[str, str]],
    list_jobs: Callable[[], list[dict[str, Any]]],
    is_dismissed: Callable[[str, str], bool],
    reactivate: Callable[[str, str, Any], Any],
    start_watcher: Callable[..., Any],
    lifecycle: Any,
    json_module: Any,
    acquire_impl: Callable[[str, str, str, bool], Any],
) -> str:
    """Coordinate a request without duplicating active searches or unsafe recovery."""
    if not artist.strip() or not album.strip():
        return json_module.dumps({
            "ok": False, "error": "Artist and album are required.",
        })

    identity = (music_key(artist), music_key(album))
    with transition_lock:
        if not reactivate_dismissed_acquisition_if_needed(
            artist, album, metadata_json,
            is_dismissed=is_dismissed,
            reactivate=reactivate,
            json_module=json_module,
        ):
            return json_module.dumps({
                "ok": False, "status": "dismissed", "artist": artist, "album": album,
                "message": (
                    "This acquisition is still dismissed and could not be safely "
                    "reopened. Refresh Acquisitions and check its status."
                ),
            }, ensure_ascii=False)

        with watcher_lock:
            watcher_active = identity in active_watchers
        existing_job = next((
            job for job in list_jobs()
            if job["artist_key"] == identity[0] and job["album_key"] == identity[1]
        ), None)
        existing_status = (existing_job or {}).get("status")
        existing_response = existing_acquisition_response(
            artist, album, identity, existing_job, existing_status, watcher_active,
            start_watcher=start_watcher,
            watcher_lock=watcher_lock,
            active_watchers=active_watchers,
            lifecycle=lifecycle,
            json_module=json_module,
        )
        if existing_response is not None:
            return existing_response
        if not reserve_acquisition_request(identity, active_requests=active_requests):
            return json_module.dumps({
                "ok": False, "status": "already_in_progress",
                "artist": artist, "album": album,
                "message": "An acquisition request or download is already active for this album.",
            }, ensure_ascii=False)

    return run_reserved_acquisition(
        identity,
        transition_lock=transition_lock,
        active_requests=active_requests,
        acquire=lambda: acquire_impl(artist, album, metadata_json, auto_queue),
    )
