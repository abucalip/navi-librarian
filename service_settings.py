"""Small, directly testable service-settings policy functions.

Persistence, runtime path ownership, MCP registration, and network checks remain
in the legacy server. Callers inject storage and path callbacks so this module
does not initialize the application or require MCP at import time.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def navidrome_config(settings_read):
    """Return validated Navidrome connection settings without exposing secrets."""
    settings = settings_read()
    base_url = str(settings.get("navidrome_url") or "").strip().rstrip("/")
    username = str(settings.get("navidrome_user") or "").strip()
    password = str(settings.get("navidrome_password") or "")
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Enter a valid HTTP or HTTPS Navidrome URL in Settings.")
    if not username or not password:
        raise ValueError("Configure the Navidrome username and password in Settings.")
    return base_url, username, password


def listenbrainz_username(settings_read):
    """Return the configured public ListenBrainz username."""
    username = str(settings_read().get("listenbrainz_username") or "").strip()
    if not username or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", username):
        raise ValueError("Configure a valid ListenBrainz username in Settings.")
    return username


def get_navidrome_settings(settings_read, music_dir):
    """Serialize safe Navidrome settings without returning the saved password."""
    settings = settings_read()
    return json.dumps({
        "navidrome_url": settings.get("navidrome_url", ""),
        "username": settings.get("navidrome_user", ""),
        "password_configured": bool(settings.get("navidrome_password")),
        "music_library_path": settings.get("music_library_path", str(music_dir)),
    }, ensure_ascii=False)


def set_navidrome_settings(
    settings_read,
    settings_write,
    get_music_dir,
    set_music_dir,
    navidrome_url,
    username,
    password="",
    music_library_path=None,
):
    """Validate and persist Navidrome settings; blank passwords preserve secrets."""
    url = (navidrome_url or "").strip().rstrip("/")
    parsed = urlparse(url)
    user = (username or "").strip()
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return json.dumps({"ok": False, "error": "Enter a valid HTTP or HTTPS Navidrome URL."})
    if not user:
        return json.dumps({"ok": False, "error": "Enter a Navidrome username."})
    current = settings_read()
    saved_password = str(password or "") or str(current.get("navidrome_password") or "")
    if not saved_password:
        return json.dumps({"ok": False, "error": "Enter a Navidrome password."})
    values = {"navidrome_url": url, "navidrome_user": user, "navidrome_password": saved_password}
    next_music_dir = get_music_dir()
    if music_library_path is not None:
        music_path = str(Path(music_library_path).expanduser())
        if not Path(music_path).is_absolute() or not Path(music_path).is_dir():
            return json.dumps({"ok": False, "error": "The music library path must be an existing absolute directory visible to this app."})
        values["music_library_path"] = music_path
        next_music_dir = Path(music_path)
    settings_write(values)
    if music_library_path is not None:
        set_music_dir(next_music_dir)
    return json.dumps({
        "ok": True, "navidrome_url": url, "username": user,
        "password_configured": True, "music_library_path": str(next_music_dir),
        "message": "Navidrome settings saved. The password is never returned.",
    }, ensure_ascii=False)


def get_lastfm_settings(settings_read):
    """Return Last.fm configuration status without exposing its API key."""
    settings = settings_read()
    return json.dumps({"api_key_configured": bool(settings.get("lastfm_api_key"))})


def set_listenbrainz_settings(settings_write, username):
    """Validate and save a ListenBrainz username."""
    value = str(username or "").strip()
    if not value or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
        return json.dumps({"ok": False, "error": "Enter a valid ListenBrainz username (letters, numbers, dot, underscore or hyphen)."})
    settings_write({"listenbrainz_username": value})
    return json.dumps({"ok": True, "username": value, "message": "ListenBrainz settings saved."})
