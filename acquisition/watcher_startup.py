"""Dependency-injected acquisition watcher startup and persisted reservation."""
from __future__ import annotations
import hashlib
import threading

def start_import_watcher(artist, album, candidate, settings, *, services):
    """Reserve, persist, and start one watcher without importing app/MCP runtime."""
    music_key = services["music_key"]
    identity = (music_key(artist), music_key(album))
    settings = settings or {}
    details = {
        "source_username": candidate.get("username"),
        "folder": candidate.get("folder"),
        "file_count": len(candidate.get("files") or []),
        "quality_summary": list(candidate.get("quality_summary") or []),
        "downloads_path": settings.get("slskd_downloads_path"),
    }
    safe_settings = {key: value for key, value in settings.items()
                     if key not in {"slskd_api_key", "api_key"}}
    transition_lock, import_lock = services["transition_lock"], services["import_lock"]
    active, is_dismissed = services["active"], services["is_dismissed"]
    with transition_lock:
        if is_dismissed(artist, album):
            return False
        with import_lock:
            if identity in active:
                return False
            active.add(identity)
        try:
            services["save_job"](artist, album, "downloading", details,
                                 candidate=candidate, settings=safe_settings)
            services["update_status"](artist, album, "downloading", details)
        except Exception:
            with import_lock:
                active.discard(identity)
            raise
    thread_factory = services.get("thread_factory", threading.Thread)
    watcher = thread_factory(
        target=services["watcher_entry"],
        args=(artist, album, dict(candidate), dict(settings), identity),
        name="navidrome-import-" + hashlib.sha1(
            (music_key(artist) + "|" + music_key(album)).encode("utf-8")
        ).hexdigest()[:10], daemon=True,
    )
    try:
        watcher.start()
    except Exception as exc:
        with import_lock:
            active.discard(identity)
        services["update_status"](artist, album, "monitor_error", {
            "error": type(exc).__name__,
            "message": "Could not start the acquisition watcher.",
        })
        return False
    return True
