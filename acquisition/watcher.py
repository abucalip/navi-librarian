"""Injected acquisition watcher lifecycle; no app/MCP initialization on import."""
from pathlib import Path

from acquisition.progress_accounting import observe_progress
import shutil
import time


FAILED_TOKENS = {"failed", "errored", "cancelled", "canceled", "timedout"}
FAILED_TRACK_MAX_RETRIES = 3
FAILED_TRACK_RETRY_INTERVAL = 30
# After retries are spent, keep watching so a manual retry in the slskd UI can
# still rescue the album before the source is declared failed.
FAILED_TRACK_GRACE_SECONDS = 15 * 60


def _state_tokens(value):
    text = str(value or "").replace("_", "").casefold()
    return {part for part in text.replace(",", " ").split() if part}


def _state_rank(value):
    tokens = _state_tokens(value)
    if tokens & {"succeeded", "completed"} and not tokens & FAILED_TOKENS:
        return 3
    if tokens & FAILED_TOKENS:
        return 0
    return 2


def watch_and_import_album(artist, album, candidate, settings, *, services):
    """Poll one queued acquisition and import only a strictly verified completed folder.

    Application I/O and state transitions are injected by the legacy adapter so
    the loop can be tested without starting MCP or FastAPI.
    """
    MUSIC_DIR = services["music_dir"]
    _discovery_reconcile_interrupted_import = services["reconcile_interrupted_import"]
    _slskd_config = services["slskd_config"]
    _DISCOVERY_SETTINGS_DEFAULTS = services["settings_defaults"]
    _discovery_is_dismissed = services["is_dismissed"]
    _discovery_skip_requested = services["skip_requested"]
    _discovery_switch_to_next_source = services["switch_to_next_source"]
    _discovery_locate_completed_album = services["locate_completed_album"]
    _discovery_import_completed_source = services["import_completed_source"]
    _slskd_download_transfer_files = services["download_transfer_files"]
    _discovery_update_acquisition_status = services["update_status"]
    _discovery_inspect_completed_album = services["inspect_completed_album"]
    clock = services.get("clock", time)
    queue_files = services.get("queue_files")
    import shutil
    music_root = MUSIC_DIR.expanduser()
    if _discovery_reconcile_interrupted_import(artist, album, candidate):
        return
    base_url, api_key, _ = _slskd_config()
    headers = {"X-API-KEY": api_key}
    download_root = Path(str(
        settings.get("slskd_downloads_path")
        or _DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"]
    )).expanduser()
    expected = {
        str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
        for item in candidate.get("files", [])
    }
    expected_sizes = {
        str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold():
            max(0, int(item.get("size") or 0))
        for item in candidate.get("files", [])
        if str(item.get("filename") or "").strip()
    }
    deadline = clock.monotonic() + 48 * 60 * 60
    completed_at = None
    last_progress_at = clock.monotonic()
    last_progress_bytes = 0
    stall_detected_at = None
    source_switches = 0
    retry_attempts = {}
    last_retry_at = None
    while clock.monotonic() < deadline:
        try:
            if _discovery_is_dismissed(artist, album):
                return
            if _discovery_skip_requested(artist, album):
                next_candidate = _discovery_switch_to_next_source(
                    artist, album, candidate, settings, download_root, headers, "manual_skip"
                )
                if next_candidate is None:
                    return
                candidate = next_candidate
                expected = {
                    str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
                    for item in candidate.get("files", [])
                }
                expected_sizes = {
                    str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold():
                        max(0, int(item.get("size") or 0))
                    for item in candidate.get("files", [])
                    if str(item.get("filename") or "").strip()
                }
                last_progress_at = clock.monotonic()
                last_progress_bytes = 0
                stall_detected_at = None
                completed_at = None
                source_switches += 1
                retry_attempts, last_retry_at = {}, None
                continue
            # Filesystem completion is authoritative: slskd may prune successful
            # transfer records before this watcher polls them again.
            source = _discovery_locate_completed_album(download_root, candidate)
            if source is not None:
                result = _discovery_import_completed_source(
                    artist, album, source, music_root, candidate
                )
                if result in {"dismissed", "failed", "imported"}:
                    return

            tracked = _slskd_download_transfer_files(
                base_url, headers, candidate["username"]
            )
            matching_by_name = {}
            for item in tracked:
                name = str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
                if name not in expected:
                    continue
                previous = matching_by_name.get(name)
                # Prefer completed, then live, then failed records so a retried
                # track is not masked by its stale errored predecessor.
                if previous is None or (
                    _state_rank(item.get("state")) >= _state_rank(previous.get("state"))
                ):
                    matching_by_name[name] = item

            states = {
                str(item.get("state") or "").replace("_", "").casefold()
                for item in matching_by_name.values()
            }
            current_bytes = 0
            for item in matching_by_name.values():
                for key in ("bytesTransferred", "bytesDownloaded", "downloadedBytes", "transferredBytes"):
                    try:
                        if item.get(key) is not None:
                            current_bytes += max(0, int(item[key]))
                            break
                    except (TypeError, ValueError):
                        pass
            now_mono = clock.monotonic()
            progress = observe_progress(
                current_bytes, last_progress_bytes, last_progress_at,
                stall_detected_at, now_mono,
            )
            last_progress_bytes = progress["last_progress_bytes"]
            last_progress_at = progress["last_progress_at"]
            stall_detected_at = progress["stall_detected_at"]
            stalled_for = progress["stalled_for"]
            failed_names = sorted(
                name for name, item in matching_by_name.items()
                if _state_tokens(item.get("state")) & FAILED_TOKENS
            )
            if failed_names:
                now = clock.monotonic()
                retryable = [n for n in failed_names
                             if retry_attempts.get(n, 0) < FAILED_TRACK_MAX_RETRIES]
                if (retryable and queue_files is not None and (
                        last_retry_at is None
                        or now - last_retry_at >= FAILED_TRACK_RETRY_INTERVAL)):
                    files = [item for item in candidate.get("files", [])
                             if str(item.get("filename") or "").replace("\\", "/")
                             .rsplit("/", 1)[-1].casefold() in retryable]
                    last_retry_at = now
                    for name in retryable:
                        retry_attempts[name] = retry_attempts.get(name, 0) + 1
                    try:
                        queue_files(base_url, headers, candidate["username"], files)
                    except Exception:
                        pass  # counted as an attempt; the next poll re-evaluates
                    _discovery_update_acquisition_status(artist, album, "downloading", {
                        "source_username": candidate.get("username"),
                        "folder": candidate.get("folder"),
                        "quality_summary": list(candidate.get("quality_summary") or []),
                        "failed_tracks": failed_names,
                        "track_retries": dict(retry_attempts),
                        "message": f"Retrying {len(files)} failed track(s) from the same source.",
                    })
                elif (not retryable or queue_files is None) and (
                        last_retry_at is None
                        or now - last_retry_at >= FAILED_TRACK_GRACE_SECONDS):
                    _discovery_update_acquisition_status(artist, album, "download_failed", {
                        "source_username": candidate["username"],
                        "states": sorted(states),
                        "failed_tracks": failed_names,
                    })
                    return
                # Another source would redo the whole album; hold off the stall switch.
                stalled_for = 0
            if (stalled_for >= 120 and candidate.get("fallback_candidates")
                    and not (states and states.issubset({"succeeded", "completed"}))):
                if stall_detected_at is None:
                    stall_detected_at = clock.time()
                    _discovery_update_acquisition_status(artist, album, "downloading", {
                        "source_username": candidate.get("username"),
                        "folder": candidate.get("folder"),
                        "quality_summary": list(candidate.get("quality_summary") or []),
                        "zero_progress_seconds": int(stalled_for),
                        "stall_detected_at": stall_detected_at,
                        "skip_countdown_seconds": 15,
                        "fallback_count": len(candidate.get("fallback_candidates") or []),
                        "source_switches": source_switches,
                        "message": "No download progress for 2 minutes. Switching automatically in 15 seconds unless skipped manually.",
                    })
                skip_requested = _discovery_skip_requested(artist, album)
                if skip_requested or clock.time() - stall_detected_at >= 15:
                    next_candidate = _discovery_switch_to_next_source(
                        artist, album, candidate, settings, download_root, headers,
                        "manual_skip" if skip_requested else "zero_progress_timeout",
                    )
                    if next_candidate is None:
                        return
                    candidate = next_candidate
                    expected = {
                        str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
                        for item in candidate.get("files", [])
                    }
                    expected_sizes = {
                        str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold():
                            max(0, int(item.get("size") or 0))
                        for item in candidate.get("files", [])
                        if str(item.get("filename") or "").strip()
                    }
                    last_progress_at = clock.monotonic()
                    last_progress_bytes = 0
                    stall_detected_at = None
                    completed_at = None
                    source_switches += 1
                    retry_attempts, last_retry_at = {}, None
                    continue
            # Byte counters can reach the advertised file sizes before slskd
            # switches transfers to succeeded/completed. Use them as completion
            # evidence too, while still requiring the files on disk before import.
            all_transfers_complete = bool(expected) and all(
                name in matching_by_name and (
                    str(matching_by_name[name].get("state") or "").replace("_", "").casefold()
                    in {"succeeded", "completed"}
                    or (
                        expected_sizes.get(name, 0) > 0
                        and any(
                            matching_by_name[name].get(key) is not None
                            and str(matching_by_name[name][key]).isdigit()
                            and int(matching_by_name[name][key]) >= expected_sizes[name]
                            for key in ("bytesTransferred", "bytesDownloaded", "downloadedBytes", "transferredBytes")
                        )
                    )
                )
                for name in expected
            )
            if all_transfers_complete:
                completed_at = completed_at or clock.monotonic()
                folder_inspection = _discovery_inspect_completed_album(download_root, candidate)
                source = folder_inspection["path"]
                if source is None:
                    _discovery_update_acquisition_status(artist, album, "download_complete_waiting_for_folder", {
                        "source_username": candidate["username"],
                        "downloads_path": str(download_root),
                        "downloads_path_available": download_root.is_dir(),
                        "expected_folder": candidate.get("folder"),
                        "expected_files": len(expected),
                        "matched_transfer_records": len(matching_by_name),
                        "transfer_states": sorted(states),
                        "completion_evidence": "transfer byte counters or terminal states",
                        **folder_inspection["diagnostics"],
                    })
                else:
                    result = _discovery_import_completed_source(
                        artist, album, source, music_root, candidate
                    )
                    if result in {"dismissed", "failed", "imported"}:
                        return
                # Keep looking for the local SMB/NFS-visible folder for up to six hours.
                if clock.monotonic() - completed_at > 6 * 60 * 60:
                    _discovery_update_acquisition_status(artist, album, "download_complete_move_failed", {
                        "downloads_path": str(download_root),
                        "folder": candidate.get("folder"),
                    })
                    return
        except Exception as exc:
            # Preserve the actual failure reason so recurring monitor errors can
            # be diagnosed from acquisition status without attaching a debugger.
            _discovery_update_acquisition_status(artist, album, "monitor_error", {
                "error": type(exc).__name__,
                "error_message": str(exc)[:500],
            })
        clock.sleep(2)
    _discovery_update_acquisition_status(artist, album, "monitor_timeout", {
        "source_username": candidate["username"]
    })
