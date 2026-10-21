"""Pure progress accounting for the acquisition download watcher."""


def observe_progress(current_bytes, last_progress_bytes, last_progress_at,
                     stall_detected_at, now_monotonic):
    """Update progress markers and return elapsed time without side effects.

    Progress is recorded only when the observed aggregate byte count increases,
    matching the watcher's historical behavior. A positive increase clears any
    previous stall marker; equal or lower counts do not reset the timer.
    """
    if current_bytes > last_progress_bytes:
        last_progress_bytes = current_bytes
        last_progress_at = now_monotonic
        stall_detected_at = None
    return {
        "last_progress_bytes": last_progress_bytes,
        "last_progress_at": last_progress_at,
        "stall_detected_at": stall_detected_at,
        "stalled_for": now_monotonic - last_progress_at,
    }
