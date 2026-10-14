"""Source-switch orchestration with explicit runtime and persistence dependencies.

The caller owns synchronization and dismissal arbitration. This function preserves
the conservative rule that cleanup must succeed before a new source is queued and
uncertain queue outcomes must be monitored rather than retried blindly.
"""


def switch_to_next_source_locked(
    artist, album, candidate, settings, download_root, headers, reason, *,
    get_slskd_config, lifecycle, cleanup_source, update_status, http_client,
    candidate_start_state, save_job, list_jobs, music_key,
):
    """Switch only among prevalidated complete candidates, cleaning the previous album folder first."""
    base_url, _, _ = get_slskd_config()
    fallbacks = list(candidate.get("fallback_candidates") or [])
    if not fallbacks:
        update_status(artist, album, "download_stalled_no_fallback", {
            "source_username": candidate.get("username"),
            "reason": reason,
            "message": "No other complete eligible source is available.",
        })
        return None
    if not cleanup_source(download_root, candidate, base_url, headers):
        update_status(artist, album, "source_switch_failed", {
            "source_username": candidate.get("username"),
            "reason": reason,
            "error": "Could not safely cancel transfers or clean the previous album folder.",
        })
        return None
    for index, next_candidate in enumerate(fallbacks):
        files = lifecycle.normalized_candidate_files(next_candidate)
        if not lifecycle.fallback_candidate_is_usable(next_candidate):
            continue
        queue_error = None
        try:
            response = http_client.post(
                f"{base_url}/api/v0/transfers/downloads/{next_candidate['username']}",
                headers=headers, json=files, timeout=12,
            )
            response.raise_for_status()
        except http_client.HTTPError as exc:
            # The server may have accepted the request before the connection
            # failed. Inspect the source before considering another peer.
            queue_error = type(exc).__name__
        except (ValueError, TypeError):
            continue
        monitor_candidate = dict(next_candidate)
        monitor_candidate["files"] = files
        monitor_candidate["fallback_candidates"] = fallbacks[index + 1:]
        start_state = candidate_start_state(base_url, headers, monitor_candidate, timeout=8)
        if start_state is not True:
            if start_state is None:
                # The new source may be active. Persist it and keep monitoring rather
                # than queueing another peer or abandoning a possibly live transfer.
                details = {
                    "source_username": next_candidate.get("username"),
                    "folder": next_candidate.get("folder"),
                    "file_count": len(files),
                    "quality_summary": list(next_candidate.get("quality_summary") or []),
                    "downloads_path": str(download_root),
                    "previous_source_username": candidate.get("username"),
                    "source_switch_reason": reason,
                    "queue_error": queue_error,
                    "message": (
                        "The fallback queue outcome is uncertain; monitoring this "
                        "source to avoid duplicate downloads."
                        if queue_error else
                        "The next source was queued but its start could not be confirmed; monitoring it to avoid duplicate downloads."
                    ),
                }
                save_job(artist, album, "downloading", details,
                                                candidate=monitor_candidate, settings=settings)
                return monitor_candidate
            if not cleanup_source(
                download_root, monitor_candidate, base_url, headers
            ):
                update_status(artist, album, "source_switch_failed", {
                    "source_username": next_candidate.get("username"),
                    "reason": reason,
                    "error": (
                        "Fallback source did not start and its transfers/files "
                        "could not be safely cancelled and cleaned. No further "
                        "source will be queued."
                    ),
                })
                return None
            continue
        previous_details = next(
            (job.get("details") or {} for job in list_jobs()
             if job["artist_key"] == music_key(artist) and job["album_key"] == music_key(album)),
            {},
        )
        details = {
            "source_username": next_candidate.get("username"),
            "folder": next_candidate.get("folder"),
            "file_count": len(files),
            "unique_track_count": next_candidate.get("unique_track_count"),
            "expected_track_count": next_candidate.get("expected_track_count"),
            "quality_summary": list(next_candidate.get("quality_summary") or []),
            "downloads_path": str(download_root),
            "source_switches": int(previous_details.get("source_switches") or 0) + 1,
            "previous_source_username": candidate.get("username"),
            "source_switch_reason": reason,
            "message": "Previous source stalled; switched to the next complete eligible source.",
        }
        save_job(artist, album, "downloading", details,
                                        candidate=monitor_candidate, settings=settings)
        return monitor_candidate
    update_status(artist, album, "download_stalled_no_fallback", {
        "source_username": candidate.get("username"),
        "reason": reason,
        "message": "Every remaining eligible source failed to start.",
    })
    return None
