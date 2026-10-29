"""Get a single song: search, queue, watch, import and dismiss (D-016: outside the server).

Each function takes the librarian object that ``app.api.dependencies.get_librarian`` returns and
reads its helpers by attribute at call time, the adapter pattern ``discovery/lens_service.py``
uses. A song is one row of the acquisition table whose "album" is a synthetic name
(``track_job_album``) so every album job keeps its own identity; the row's details carry
``kind: "track"`` and the real album and title. Its candidate stores the file under
``track_file``, never ``files``, so the album watcher's restart recovery never claims it.

The policy is the owner's: the best file is chosen automatically, the song goes to the folder
the library already uses for its album (a new ``<artist>/<album>`` only when there is none),
and dismissing a song removes only its own download. See docs/ALBUM_PAGE_REDESIGN_PROPOSAL.md.
"""
from __future__ import annotations

import threading
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from acquisition import track_search
from acquisition.progress_accounting import observe_progress
from acquisition.track_destination import DestinationError, plan_destination
from acquisition.track_import import destination_filename, import_track_file
from integrations.slskd import transfers
from integrations.slskd.search_polling import collect_search_responses

KIND = "track"
FAILED_TOKENS = {"failed", "errored", "cancelled", "canceled", "timedout"}
DONE_TOKENS = {"succeeded", "completed"}
RETRY_LIMIT = 3
RETRY_INTERVAL_SECONDS = 30
FAILED_GRACE_SECONDS = 15 * 60
STALL_SECONDS = 5 * 60
WATCH_SECONDS = 48 * 60 * 60
MAX_FALLBACKS = 4
RESUMABLE = frozenset({"downloading", "download_complete_waiting_for_folder", "monitor_error"})
# Nothing was downloaded in these states, so dismissing has no file to remove.
FILELESS = frozenset({"no_matches", "queue_failed", "settings_required", "slskd_error", "imported"})

_ACTIVE_LOCK = threading.Lock()
_ACTIVE: set[tuple[str, str]] = set()


def track_job_album(album: str, title: str) -> str:
    """The acquisition row's album name for one song of an album."""
    return f"{title} (song on {album})"


def _tokens(state: Any) -> set[str]:
    text = str(state or "").replace("_", "").casefold()
    return {part for part in text.replace(",", " ").split() if part}


def _basename(value: Any) -> str:
    return str(value or "").replace("\\", "/").rsplit("/", 1)[-1]


def _context(job: dict[str, Any]) -> dict[str, Any]:
    details = job.get("details") or {}
    return {
        "artist": job["artist"], "job_album": job["album"],
        "album": details.get("album_name") or "", "title": details.get("track_title") or "",
        "track_number": details.get("track_number"), "year": details.get("year"),
    }


def _is_track(job: dict[str, Any]) -> bool:
    return (job.get("details") or {}).get("kind") == KIND


def _find_job(librarian: Any, artist: str, job_album: str) -> dict[str, Any] | None:
    identity = (librarian._music_key(artist), librarian._music_key(job_album))
    return next((job for job in librarian._discovery_list_acquisition_jobs()
                 if (job["artist_key"], job["album_key"]) == identity), None)


def _details(ctx: dict[str, Any], candidate: dict[str, Any] | None = None, **extra: Any) -> dict[str, Any]:
    """Every status write carries the song's identity, because a write replaces the details."""
    details: dict[str, Any] = {
        "kind": KIND, "album_name": ctx["album"], "track_title": ctx["title"],
        "track_number": ctx.get("track_number"), "year": ctx.get("year"),
    }
    if candidate:
        file = candidate.get("track_file") or {}
        details.update({
            "source_username": candidate.get("username"), "folder": candidate.get("folder"),
            "file_name": _basename(file.get("filename")), "file_size": file.get("size"),
            "file_count": 1, "quality_summary": list(candidate.get("quality_summary") or []),
            "fallback_count": len(candidate.get("fallback_candidates") or []),
        })
    details.update(extra)
    return details


def _status(librarian: Any, ctx: dict[str, Any], status: str, candidate=None, **extra: Any) -> bool:
    return librarian._discovery_update_acquisition_status(
        ctx["artist"], ctx["job_album"], status, _details(ctx, candidate, **extra),
    )


def _as_album_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """The one-file shape the shared slskd start, cleanup and folder-inspection helpers read."""
    return {
        "username": candidate["username"], "folder": candidate.get("folder") or "",
        "files": [dict(candidate["track_file"])],
        "quality_summary": list(candidate.get("quality_summary") or []),
    }


def _candidate_record(found: dict[str, Any]) -> dict[str, Any]:
    return {
        "username": found["username"], "folder": found["folder"],
        "track_file": {"filename": found["filename"], "size": found["size"]},
        "quality_summary": [found["quality_tier"]], "upload_speed": found["upload_speed"],
    }


# ---- request -------------------------------------------------------------------------------

def request_track(
    librarian: Any, artist: str, album: str, title: str,
    track_number: int | None = None, year: Any = None, metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Search slskd for one song and start downloading the best clear match."""
    artist, album, title = artist.strip(), album.strip(), title.strip()
    if not artist or not album or not title:
        return {"ok": False, "error": "Artist, album and title are required."}
    ctx = {"artist": artist, "job_album": track_job_album(album, title), "album": album,
           "title": title, "track_number": track_number, "year": year}
    metadata = dict(metadata or {})
    identity = (librarian._music_key(artist), librarian._music_key(ctx["job_album"]))
    lock = librarian._DISCOVERY_IMPORT_TRANSITION_LOCK
    reply = {"artist": artist, "album": ctx["job_album"]}

    with lock:
        if librarian._discovery_is_dismissed(artist, ctx["job_album"]) and not \
                librarian._discovery_reactivate_dismissed_acquisition(artist, ctx["job_album"], metadata):
            return {**reply, "ok": False, "status": "dismissed", "message": (
                "This song is still dismissed and could not be safely reopened. Refresh Acquisitions.")}
        job = _find_job(librarian, artist, ctx["job_album"])
        status = (job or {}).get("status")
        if status in {"importing", "imported"}:
            return {**reply, "ok": False, "status": status,
                    "message": "This song is already being imported or is in the library."}
        with _ACTIVE_LOCK:
            watching = identity in _ACTIVE
        if watching or status == "downloading" or identity in librarian._DISCOVERY_ACQUIRE_ACTIVE:
            if status == "downloading" and not watching and (job["candidate"] or {}).get("track_file"):
                _spawn(librarian, _context(job), job["candidate"], job["settings"])
                return {**reply, "ok": True, "status": "recovery_started",
                        "message": "Resumed monitoring the saved download."}
            return {**reply, "ok": False, "status": "already_in_progress",
                    "message": "A request or download is already active for this song."}
        librarian._DISCOVERY_ACQUIRE_ACTIVE.add(identity)
    try:
        return _search_and_queue(librarian, ctx, metadata, reply)
    finally:
        with lock:
            librarian._DISCOVERY_ACQUIRE_ACTIVE.discard(identity)


def _search_and_queue(librarian: Any, ctx: dict[str, Any], metadata: dict[str, Any], reply: dict[str, Any]) -> dict[str, Any]:
    artist, album, title, job_album = ctx["artist"], ctx["album"], ctx["title"], ctx["job_album"]
    try:
        base_url, api_key, settings = librarian._slskd_config()
    except ValueError as exc:
        _status(librarian, ctx, "settings_required", message=str(exc), metadata=metadata)
        return {**reply, "ok": False, "status": "settings_required", "message": str(exc)}
    headers = {"X-API-KEY": api_key}
    priority = settings.get("quality_priority", librarian._DISCOVERY_SETTINGS_DEFAULTS["quality_priority"])
    try:
        from integrations.slskd.search import response_items

        search = collect_search_responses(
            track_search.track_search_queries(artist, title), base_url, headers,
            http_client=httpx, monotonic=time.monotonic, sleep=time.sleep,
            new_search_id=lambda: str(uuid.uuid4()), response_items=response_items,
        )
        found = track_search.extract_track_candidates(
            list(search["payload_by_peer"].values()), artist, album, title, priority,
            music_key=librarian._music_key, album_path_match=librarian._slskd_album_path_match,
            quality_tier=librarian._slskd_quality_tier,
        )
        if not found:
            message = ("No single file clearly matching this song was found. "
                       "You can try again later.")
            _status(librarian, ctx, "no_matches", message=message, metadata=metadata,
                    search_queries_attempted=search["search_attempts"],
                    peer_responses_seen=len(search["payload_by_peer"]))
            return {**reply, "ok": True, "status": "no_matches", "message": message}

        records = [_candidate_record(item) for item in found]
        failures: list[dict[str, Any]] = []
        for index, record in enumerate(records[:10]):
            record["fallback_candidates"] = records[index + 1:index + 1 + MAX_FALLBACKS]
            file = [dict(record["track_file"])]
            try:
                queued = librarian._discovery_queue_candidate_unless_dismissed(
                    artist, job_album, base_url, headers, record["username"], file)
                if queued is None:
                    return {**reply, "ok": False, "status": "dismissed",
                            "message": "This song was dismissed before a source could be queued."}
            except httpx.HTTPError as exc:
                action = librarian._slskd_queue_failure_action(exc)
                code = getattr(getattr(exc, "response", None), "status_code", None)
                if action == "retry_source":
                    failures.append({"username": record["username"], "http_status": code})
                    continue
                if action == "fatal":
                    message = (f"slskd rejected the queue request with HTTP {code}; "
                               "check the API key and its permissions.")
                    _status(librarian, ctx, "slskd_error", message=message, metadata=metadata)
                    return {**reply, "ok": False, "status": "slskd_error", "message": message}
                _start(librarian, ctx, record, settings, metadata)
                return {**reply, "ok": True, "status": "queued_unconfirmed", "message": (
                    "The queue request returned an HTTP error, so its outcome is uncertain. "
                    "Monitoring this source before trying another.")}
            except (ValueError, TypeError):
                failures.append({"username": record["username"], "error": "invalid"})
                continue

            started = librarian._slskd_candidate_start_state(
                base_url, headers, _as_album_candidate(record), timeout=8)
            if started is False:
                download_root = Path(str(settings.get("slskd_downloads_path")
                                         or librarian._DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"])).expanduser()
                if not librarian._discovery_cancel_and_clean_source(
                        download_root, _as_album_candidate(record), base_url, headers):
                    message = ("The first source did not start, and cleanup could not be confirmed. "
                               "Check the acquisition status before retrying.")
                    _status(librarian, ctx, "source_switch_failed", message=message)
                    return {**reply, "ok": False, "status": "source_switch_failed", "message": message}
                failures.append({"username": record["username"], "error": "download_did_not_start"})
                continue
            _start(librarian, ctx, record, settings, metadata)
            return {**reply, "ok": True, "status": "queued" if started else "queued_unconfirmed",
                    "source_username": record["username"],
                    "message": "Download started. The song will be moved into the music library when it finishes."}

        message = "None of the matching sources started a download. Check slskd and try again."
        _status(librarian, ctx, "queue_failed", message=message, attempts=failures, metadata=metadata)
        return {**reply, "ok": False, "status": "queue_failed", "message": message}
    except (httpx.HTTPError, ValueError, TypeError) as exc:
        message = f"slskd request failed: {type(exc).__name__}"
        _status(librarian, ctx, "slskd_error", message=message, detail=str(exc)[:300], metadata=metadata)
        return {**reply, "ok": False, "status": "slskd_error", "message": message}


# ---- watcher -------------------------------------------------------------------------------

def _safe_settings(settings: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in (settings or {}).items() if key not in {"slskd_api_key", "api_key"}}


def _start(librarian: Any, ctx: dict[str, Any], candidate: dict[str, Any], settings: dict[str, Any], metadata=None) -> bool:
    """Persist the queued download, then watch it. False when dismissed or already watched."""
    identity = (librarian._music_key(ctx["artist"]), librarian._music_key(ctx["job_album"]))
    with librarian._DISCOVERY_IMPORT_TRANSITION_LOCK:
        if librarian._discovery_is_dismissed(ctx["artist"], ctx["job_album"]):
            return False
        with _ACTIVE_LOCK:
            if identity in _ACTIVE:
                return False
        extra = {"metadata": dict(metadata)} if isinstance(metadata, dict) else {}
        librarian._discovery_save_acquisition_job(
            ctx["artist"], ctx["job_album"], "downloading", _details(ctx, candidate, **extra),
            candidate=candidate, settings=_safe_settings(settings))
    return _spawn(librarian, ctx, candidate, settings)


def _spawn(librarian: Any, ctx: dict[str, Any], candidate: dict[str, Any], settings: dict[str, Any]) -> bool:
    identity = (librarian._music_key(ctx["artist"]), librarian._music_key(ctx["job_album"]))
    with _ACTIVE_LOCK:
        if identity in _ACTIVE:
            return False
        _ACTIVE.add(identity)

    def run() -> None:
        try:
            watch_track(librarian, ctx, candidate, settings)
        except Exception as exc:
            _status(librarian, ctx, "monitor_error", candidate, error=type(exc).__name__,
                    message="Song watcher stopped unexpectedly.")
        finally:
            with _ACTIVE_LOCK:
                _ACTIVE.discard(identity)

    try:
        threading.Thread(target=run, name="navidrome-track-" + uuid.uuid4().hex[:8], daemon=True).start()
    except Exception as exc:
        with _ACTIVE_LOCK:
            _ACTIVE.discard(identity)
        _status(librarian, ctx, "monitor_error", candidate, error=type(exc).__name__,
                message="Could not start the song watcher.")
        return False
    return True


def _best_record(tracked: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    best = None
    for item in tracked:
        if _basename(item.get("filename")).casefold() != name:
            continue
        rank = 3 if _tokens(item.get("state")) & DONE_TOKENS and not _tokens(item.get("state")) & FAILED_TOKENS \
            else 0 if _tokens(item.get("state")) & FAILED_TOKENS else 2
        if best is None or rank >= best[0]:
            best = (rank, item)
    return best[1] if best else None


def _transferred(record: dict[str, Any] | None) -> int:
    for key in ("bytesTransferred", "bytesDownloaded", "downloadedBytes", "transferredBytes"):
        try:
            if record and record.get(key) is not None:
                return max(0, int(record[key]))
        except (TypeError, ValueError):
            pass
    return 0


def watch_track(librarian: Any, ctx: dict[str, Any], candidate: dict[str, Any], settings: dict[str, Any], *,
                clock: Any = time, poll_seconds: float = 2) -> None:
    """Poll one queued song; import it when it is complete and verified on disk."""
    base_url, api_key, _ = librarian._slskd_config()
    headers = {"X-API-KEY": api_key}
    artist, job_album = ctx["artist"], ctx["job_album"]
    download_root = Path(str(settings.get("slskd_downloads_path")
                             or librarian._DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"])).expanduser()
    file = candidate["track_file"]
    name, size = _basename(file["filename"]).casefold(), int(file["size"])
    deadline = clock.monotonic() + WATCH_SECONDS
    last_bytes, last_progress_at = 0, clock.monotonic()
    retries, last_retry_at, failed_since = 0, None, None

    while clock.monotonic() < deadline:
        try:
            if librarian._discovery_is_dismissed(artist, job_album):
                return
            tracked = librarian._slskd_download_transfer_files(base_url, headers, candidate["username"])
            record = _best_record(tracked, name)
            state = _tokens((record or {}).get("state"))
            current = _transferred(record)
            now = clock.monotonic()
            progress = observe_progress(current, last_bytes, last_progress_at, None, now)
            last_bytes, last_progress_at = progress["last_progress_bytes"], progress["last_progress_at"]
            done = bool(record) and (bool(state & DONE_TOKENS and not state & FAILED_TOKENS) or current >= size)

            if record and state & FAILED_TOKENS and not done:
                failed_since = failed_since or now
                if retries < RETRY_LIMIT:
                    if last_retry_at is None or now - last_retry_at >= RETRY_INTERVAL_SECONDS:
                        retries += 1
                        last_retry_at = now
                        try:
                            transfers.queue_download_files(base_url, headers, candidate["username"],
                                                           [dict(file)], http_client=httpx)
                        except Exception:
                            pass  # counted as an attempt; the next poll re-evaluates
                        _status(librarian, ctx, "downloading", candidate, track_retries=retries,
                                message="Retrying the failed song from the same source.")
                elif candidate.get("fallback_candidates"):
                    candidate = _switch_source(librarian, ctx, candidate, settings, download_root, base_url, headers)
                    if candidate is None:
                        return
                    file = candidate["track_file"]
                    name, size = _basename(file["filename"]).casefold(), int(file["size"])
                    last_bytes, last_progress_at = 0, clock.monotonic()
                    retries, last_retry_at, failed_since = 0, None, None
                elif now - failed_since >= FAILED_GRACE_SECONDS:
                    _status(librarian, ctx, "download_failed", candidate, states=sorted(state))
                    return
            elif not done and progress["stalled_for"] >= STALL_SECONDS and candidate.get("fallback_candidates"):
                candidate = _switch_source(librarian, ctx, candidate, settings, download_root, base_url, headers)
                if candidate is None:
                    return
                file = candidate["track_file"]
                name, size = _basename(file["filename"]).casefold(), int(file["size"])
                last_bytes, last_progress_at = 0, clock.monotonic()
                retries, last_retry_at, failed_since = 0, None, None
            else:
                failed_since = None

            if done:
                inspection = librarian._discovery_inspect_completed_album(download_root, _as_album_candidate(candidate))
                if inspection["path"] is None:
                    _status(librarian, ctx, "download_complete_waiting_for_folder", candidate,
                            downloads_path=str(download_root), **inspection["diagnostics"])
                else:
                    result = import_completed_track(librarian, ctx, candidate, inspection["path"])
                    if result in {"dismissed", "failed", "imported"}:
                        return
        except Exception as exc:
            _status(librarian, ctx, "monitor_error", candidate, error=type(exc).__name__,
                    error_message=str(exc)[:500])
        clock.sleep(poll_seconds)
    _status(librarian, ctx, "monitor_timeout", candidate)


def _switch_source(librarian, ctx, candidate, settings, download_root, base_url, headers):
    """Clean the failed source and queue the next one; None when the watcher should stop."""
    with librarian._DISCOVERY_IMPORT_TRANSITION_LOCK:
        if librarian._discovery_is_dismissed(ctx["artist"], ctx["job_album"]):
            return None
        if not librarian._discovery_cancel_and_clean_source(
                download_root, _as_album_candidate(candidate), base_url, headers):
            _status(librarian, ctx, "source_switch_failed", candidate, error=(
                "The current source could not be safely cancelled and cleaned. No other source was queued."))
            return None
        fallbacks = list(candidate.get("fallback_candidates") or [])
        while fallbacks:
            nxt = fallbacks.pop(0)
            nxt = {**nxt, "fallback_candidates": fallbacks}
            try:
                transfers.queue_download_files(base_url, headers, nxt["username"],
                                               [dict(nxt["track_file"])], http_client=httpx)
            except Exception:
                continue
            librarian._discovery_save_acquisition_job(
                ctx["artist"], ctx["job_album"], "downloading",
                _details(ctx, nxt, message="Switched to the next source."),
                candidate=nxt, settings=_safe_settings(settings))
            return nxt
        _status(librarian, ctx, "queue_failed", candidate,
                message="No other source could be queued for this song.")
        return None


def import_completed_track(librarian: Any, ctx: dict[str, Any], candidate: dict[str, Any], source_folder: Path) -> str:
    """Import the verified file unless dismissal wins; returns dismissed, failed or imported."""
    artist, job_album = ctx["artist"], ctx["job_album"]
    file = candidate["track_file"]
    with librarian._DISCOVERY_IMPORT_TRANSITION_LOCK:
        if librarian._discovery_is_dismissed(artist, job_album):
            return "dismissed"
        try:
            root = Path(librarian.MUSIC_DIR).expanduser().resolve(strict=True)
            if not root.is_dir():
                raise OSError("not a directory")
        except (OSError, RuntimeError, TypeError, ValueError):
            _status(librarian, ctx, "library_mount_unavailable", candidate, source_folder=str(source_folder))
            return "failed"
        matched = librarian._discovery_match_completed_album_files(source_folder, _as_album_candidate(candidate))
        if not matched or len(matched) != 1:
            _status(librarian, ctx, "download_complete_move_failed", candidate,
                    source_folder=str(source_folder), error="The downloaded file could not be verified by name and size.")
            return "failed"
        local = next(iter(matched.values()))
        try:
            album_dir = plan_destination(root, artist, ctx["album"],
                                         safe_folder_name=librarian._discovery_safe_folder_name,
                                         music_key=librarian._music_key)
            destination_filename(file["filename"])
        except OSError as exc:
            _status(librarian, ctx, "download_complete_move_failed", candidate,
                    source_folder=str(source_folder), error=str(exc))
            return "failed"
        if not _status(librarian, ctx, "importing", candidate, source_folder=str(source_folder),
                       destination=str(album_dir)):
            return "failed"
        try:
            destination = import_track_file(local, album_dir, root, file["filename"], int(file["size"]))
        except FileExistsError:
            _status(librarian, ctx, "destination_exists", candidate, source_folder=str(source_folder),
                    destination=str(album_dir), error="A file with this name is already in the album folder.")
            return "failed"
        except OSError as exc:
            _status(librarian, ctx, "download_complete_move_failed", candidate,
                    source_folder=str(source_folder), destination=str(album_dir), error=str(exc))
            return "failed"
        except Exception as exc:
            _status(librarian, ctx, "download_complete_move_failed", candidate,
                    source_folder=str(source_folder), destination=str(album_dir),
                    error=f"Unexpected import error ({type(exc).__name__}): {exc}")
            return "failed"
        _status(librarian, ctx, "imported", candidate, source_folder=str(source_folder),
                destination=str(destination), imported_at=time.time())
        return "imported"


# ---- dismiss, status ------------------------------------------------------------------------

def dismiss_track(librarian: Any, artist: str, job_album: str) -> dict[str, Any] | None:
    """Dismiss a song and remove only its own download; None when the row is not a song."""
    try:
        lock = librarian._DISCOVERY_IMPORT_TRANSITION_LOCK
        if not (probe := _find_job(librarian, artist, job_album)) or not _is_track(probe):
            return None
    except Exception:
        return None  # not a song, or the rows cannot be read: the album path decides
    with lock:
        job = _find_job(librarian, artist, job_album)
        if job is None or not _is_track(job):
            return None
        if job["status"] == "dismissed":
            return {"ok": True, "status": "dismissed", "message": "Acquisition is already dismissed."}
        ctx, candidate = _context(job), job["candidate"] or {}
        if job["status"] not in FILELESS:
            if not candidate.get("track_file") or not candidate.get("username"):
                return {"ok": False, "error": (
                    "The song may have a download file, but its source inventory is missing. "
                    "For safety, the card was not dismissed and no files were deleted.")}
            try:
                base_url, api_key, current = librarian._slskd_config()
                root = (current.get("slskd_downloads_path") or job["settings"].get("slskd_downloads_path")
                        or librarian._DISCOVERY_SETTINGS_DEFAULTS["slskd_downloads_path"])
                cleaned = librarian._discovery_cancel_and_clean_source(
                    root, _as_album_candidate(candidate), base_url, {"X-API-KEY": api_key})
            except Exception:
                cleaned = False
            if not cleaned:
                return {"ok": False, "error": (
                    "Could not safely cancel this song and remove its download file. Nothing was "
                    "dismissed; check the download folder and acquisition settings.")}
        librarian._discovery_update_acquisition_status(
            artist, job_album, "dismissed",
            _details(ctx, candidate or None, dismissed_at=time.time(), cleanup_confirmed=True))
    return {"ok": True, "status": "dismissed",
            "message": "Song dismissed and its safely identified download file was removed."}


def _live_progress(librarian: Any, job: dict[str, Any]) -> dict[str, Any] | None:
    candidate = job.get("candidate") or {}
    file = candidate.get("track_file")
    if not file or not candidate.get("username"):
        return None
    unavailable = {"available": False, "total_tracks": 1, "remaining_tracks": 1, "completed_tracks": 0,
                   "percent": None, "speed_bytes_per_second": None}
    try:
        base_url, api_key, _ = librarian._slskd_config()
        tracked = librarian._slskd_download_transfer_files(base_url, {"X-API-KEY": api_key}, candidate["username"])
    except Exception:
        return unavailable
    expected, matched = transfers.match_expected_transfer_records([dict(file)], tracked)
    summary = transfers.summarize_transfer_progress(expected, matched)
    total, moved = summary["total_size_bytes"], summary["transferred_size_bytes"]
    key = (job["artist_key"], job["album_key"])
    speed = None
    try:
        speed = librarian._DISCOVERY_PROGRESS_SNAPSHOTS.estimate(
            key, summary["file_byte_snapshot"], time.monotonic(), transfers.estimate_transfer_speed)
    except Exception:
        pass
    done = min(summary["completed_tracks"], 1)
    return {
        "available": True, "total_tracks": 1, "completed_tracks": done, "remaining_tracks": 1 - done,
        "percent": round(min(100.0, max(0.0, moved / total * 100.0)), 1) if total else None,
        "total_size_bytes": total or None,
        "remaining_size_bytes": max(0, total - moved) if total else None,
        "speed_bytes_per_second": speed,
    }


def augment_status(librarian: Any, payload: Any) -> Any:
    """Resume watchers for songs interrupted by a restart and add live progress to song cards.

    Never raises: the status payload is returned unchanged when nothing applies or on any error.
    """
    try:
        songs = [job for job in librarian._discovery_list_acquisition_jobs()
                 if _is_track(job) and job["status"] in RESUMABLE]
        if not songs or not isinstance(payload, dict):
            return payload
        entries = {(item.get("artist"), item.get("album")): item
                   for item in payload.get("acquisitions") or [] if isinstance(item, dict)}
        for job in songs:
            candidate = job["candidate"] or {}
            if candidate.get("track_file") and candidate.get("username"):
                _spawn(librarian, _context(job), candidate, job["settings"])
            entry = entries.get((job["artist"], job["album"]))
            progress = _live_progress(librarian, job) if entry is not None and job["status"] != "monitor_error" else None
            if entry is not None and progress is not None:
                entry["details"] = {**(entry.get("details") or {}), "live_progress": progress}
    except Exception:
        pass
    return payload
