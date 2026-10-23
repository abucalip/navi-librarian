"""Small, directly testable service-settings policy functions.

Persistence, runtime path ownership, MCP registration, and network checks remain
in the legacy server. Callers inject storage and path callbacks so this module
does not initialize the application or require MCP at import time.
"""
import json
import re
from pathlib import Path
from urllib.parse import urlparse


RECOMMENDATION_DIVERSITY_KEY = "recommendation_diversity"
DEFAULT_RECOMMENDATION_DIVERSITY = 0


def validate_recommendation_diversity(value):
    """Return a validated 0–100 integer preference; booleans are not integers here."""
    if type(value) is not int or not 0 <= value <= 100:
        return None
    return value


def recommendation_diversity_value(settings_read):
    """Read a persisted preference safely, falling back for absent/corrupt values."""
    value = settings_read().get(RECOMMENDATION_DIVERSITY_KEY, DEFAULT_RECOMMENDATION_DIVERSITY)
    validated = validate_recommendation_diversity(value)
    return DEFAULT_RECOMMENDATION_DIVERSITY if validated is None else validated


def get_recommendation_diversity_settings(settings_read):
    """Return the stable public settings payload, with a safe default for bad stored data."""
    return json.dumps({
        RECOMMENDATION_DIVERSITY_KEY: recommendation_diversity_value(settings_read),
    })


def set_recommendation_diversity_settings(settings_write, value):
    """Persist a bounded integer preference, refusing invalid input without writing."""
    validated = validate_recommendation_diversity(value)
    if validated is None:
        return json.dumps({
            "ok": False,
            "error": "recommendation_diversity must be an integer from 0 to 100.",
        })
    settings_write({RECOMMENDATION_DIVERSITY_KEY: validated})
    return json.dumps({
        "ok": True,
        RECOMMENDATION_DIVERSITY_KEY: validated,
        "message": "Recommendation diversity preference saved.",
    })


SELECTION_POLICY_KEY = "recommendation_selection_policy"
SELECTION_POLICIES = ("quota", "family_coverage")
DEFAULT_SELECTION_POLICY = "quota"


def recommendation_selection_policy_value(settings_read):
    """Read the final-list policy; absent or unknown values mean the 4/3/3 quota policy."""
    value = settings_read().get(SELECTION_POLICY_KEY, DEFAULT_SELECTION_POLICY)
    return value if value in SELECTION_POLICIES else DEFAULT_SELECTION_POLICY


AUTOMATIC_REFILL_KEY = "automatic_refill_enabled"
DEFAULT_AUTOMATIC_REFILL_ENABLED = True


def automatic_refill_enabled_value(settings_read):
    """Read the background refill switch; absent or non-boolean values mean on."""
    value = settings_read().get(AUTOMATIC_REFILL_KEY, DEFAULT_AUTOMATIC_REFILL_ENABLED)
    return value if type(value) is bool else DEFAULT_AUTOMATIC_REFILL_ENABLED


def get_automatic_refill_settings(settings_read):
    """Return the stable public refill payload."""
    return json.dumps({AUTOMATIC_REFILL_KEY: automatic_refill_enabled_value(settings_read)})


def set_automatic_refill_settings(settings_write, value):
    """Persist the refill switch, refusing non-boolean input without writing."""
    if type(value) is not bool:
        return json.dumps({"ok": False, "error": "automatic_refill_enabled must be a boolean."})
    settings_write({AUTOMATIC_REFILL_KEY: value})
    return json.dumps({
        "ok": True,
        AUTOMATIC_REFILL_KEY: value,
        "message": "Automatic refill preference saved.",
    })


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


def set_lastfm_settings(settings_read, settings_write, api_key=""):
    """Save a Last.fm API key; blank input preserves the stored key."""
    current = settings_read()
    key = str(api_key or "").strip() or str(current.get("lastfm_api_key") or "")
    settings_write({"lastfm_api_key": key})
    return json.dumps({
        "ok": True,
        "api_key_configured": bool(key),
        "message": "Last.fm settings saved; the API key is never returned.",
    })


def get_listenbrainz_settings(settings_read, username):
    """Return the username and whether a token is saved, never the token itself."""
    return json.dumps({
        "username": username,
        "token_configured": bool(str(settings_read().get("listenbrainz_token") or "").strip()),
    })


def set_listenbrainz_settings(settings_write, username, token=""):
    """Validate and save a ListenBrainz username; a blank token preserves the saved one."""
    value = str(username or "").strip()
    if not value or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value):
        return json.dumps({"ok": False, "error": "Enter a valid ListenBrainz username (letters, numbers, dot, underscore or hyphen)."})
    values = {"listenbrainz_username": value}
    token_value = str(token or "").strip()
    if token_value:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,200}", token_value):
            return json.dumps({"ok": False, "error": "The ListenBrainz token may only contain letters, numbers, hyphens and underscores."})
        values["listenbrainz_token"] = token_value
    settings_write(values)
    return json.dumps({
        "ok": True, "username": value,
        "message": "ListenBrainz settings saved; the token is never returned.",
    })


SLSKD_QUALITY_TIERS = {
    "mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"
}


def slskd_config(settings_read):
    """Return validated slskd connection settings without exposing credentials."""
    settings = settings_read()
    api_key = settings.get("slskd_api_key", "")
    base_url = str(settings.get("slskd_url") or "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("slskd URL must be a valid HTTP or HTTPS URL.")
    if not api_key:
        raise ValueError("Add the slskd API key in Discovery Settings first.")
    return base_url, api_key, settings


def get_slskd_settings(settings_read, music_dir, defaults):
    """Serialize acquisition settings without returning the stored API key."""
    settings = settings_read()
    return json.dumps({
        "music_library_path": settings.get("music_library_path", str(music_dir)),
        "slskd_url": settings.get("slskd_url", defaults["slskd_url"]),
        "api_key_configured": bool(settings.get("slskd_api_key")),
        "slskd_downloads_path": settings.get(
            "slskd_downloads_path", defaults["slskd_downloads_path"]
        ),
        "quality_priority": settings.get("quality_priority", defaults["quality_priority"]),
        "quality_labels": {
            "mp3_320": "MP3 320 kbps",
            "mp3_193_319": "MP3 193–319 kbps",
            "mp3_192": "MP3 192 kbps",
            "flac_cd": "FLAC (CD quality preferred; metadata may not verify this)",
            "flac_16_44": "FLAC 16-bit / 44.1 kHz",
            "flac_hires": "FLAC Hi-Res (24-bit or above 44.1 kHz)",
        },
    }, ensure_ascii=False, indent=2)


def set_slskd_settings(
    settings_read, settings_write, get_music_dir, set_music_dir, defaults,
    slskd_url="", api_key="",
    quality_priority_json='["mp3_320","mp3_193_319","mp3_192","flac_cd","flac_16_44","flac_hires"]',
    slskd_downloads_path=None, music_library_path=None,
):
    """Validate and persist slskd settings; blank API keys preserve saved secrets."""
    url = (slskd_url or "").strip().rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return json.dumps({"ok": False, "error": "Enter a valid HTTP or HTTPS slskd URL."})
    try:
        quality = json.loads(quality_priority_json)
    except (ValueError, TypeError):
        return json.dumps({"ok": False, "error": "Quality priority must be valid JSON."})
    if (
        not isinstance(quality, list)
        or any(not isinstance(tier, str) for tier in quality)
        or len(quality) != len(SLSKD_QUALITY_TIERS)
        or set(quality) != SLSKD_QUALITY_TIERS
    ):
        return json.dumps({
            "ok": False,
            "error": "Quality priority must contain each supported tier exactly once.",
        })
    values = {"slskd_url": url, "quality_priority": quality}
    if music_library_path is not None:
        music_path = str(Path(music_library_path).expanduser())
        if not Path(music_path).is_absolute():
            return json.dumps({
                "ok": False,
                "error": "The music library path must be an absolute path visible to this app.",
            })
        if not Path(music_path).is_dir():
            return json.dumps({
                "ok": False,
                "error": "The music library path must exist and be a directory visible to this app.",
            })
        values["music_library_path"] = music_path
    if slskd_downloads_path is not None:
        download_path = str(Path(slskd_downloads_path).expanduser())
        if not Path(download_path).is_absolute():
            return json.dumps({
                "ok": False,
                "error": "The slskd downloads path must be an absolute path visible to this app.",
            })
        values["slskd_downloads_path"] = download_path
    if (api_key or "").strip():
        values["slskd_api_key"] = api_key.strip()
    settings_write(values)
    next_music_dir = get_music_dir()
    if music_library_path is not None:
        next_music_dir = Path(values["music_library_path"])
        set_music_dir(next_music_dir)
    return json.dumps({
        "ok": True,
        "music_library_path": str(next_music_dir),
        "slskd_url": url,
        "api_key_configured": bool(settings_read().get("slskd_api_key")),
        "quality_priority": quality,
        "message": "Settings saved. The API key is never returned by this tool.",
    }, ensure_ascii=False)


def test_navidrome_connection(api_call, json_dumps):
    """Translate the configured Navidrome ping into the stable settings result."""
    try:
        api_call("ping")
        return json_dumps({"ok": True, "status": "connected", "message": "Navidrome connection succeeded."})
    except Exception as exc:
        return json_dumps({
            "ok": False, "status": "connection_failed",
            "message": str(exc) if isinstance(exc, ValueError) else "Navidrome is unavailable or authentication failed.",
        })


def test_lastfm_connection(settings_read, http_get, json_dumps):
    """Validate the configured Last.fm key without exposing it in the result."""
    key = str(settings_read().get("lastfm_api_key") or "").strip()
    if not key:
        return json_dumps({"ok": False, "status": "not_configured", "message": "Add a Last.fm API key first."})
    try:
        response = http_get(
            "https://ws.audioscrobbler.com/2.0/",
            params={"method": "chart.getTopArtists", "api_key": key, "format": "json", "limit": 1},
            headers={"User-Agent": "NavidromeLibrarian/0.1"}, timeout=10,
        )
        response.raise_for_status()
        if response.json().get("error"):
            return json_dumps({"ok": False, "status": "authentication_failed", "message": "Last.fm rejected the API key. Check the key in Settings."})
        return json_dumps({"ok": True, "status": "connected", "message": "Last.fm API connection succeeded."})
    except Exception:
        return json_dumps({"ok": False, "status": "connection_failed", "message": "Could not reach Last.fm or validate the API key."})


def test_listenbrainz_connection(username_get, http_get, json_dumps):
    """Check whether the configured public ListenBrainz profile can be read."""
    try:
        username = username_get()
        response = http_get(
            f"https://api.listenbrainz.org/1/user/{username}/listens",
            params={"count": 1}, headers={"User-Agent": "NavidromeLibrarian/0.1"}, timeout=10,
        )
        if response.status_code == 404:
            return json_dumps({"ok": False, "status": "not_found", "message": "ListenBrainz user was not found."})
        response.raise_for_status()
        return json_dumps({"ok": True, "status": "connected", "message": "ListenBrainz profile is reachable."})
    except Exception:
        return json_dumps({"ok": False, "status": "connection_failed", "message": "Could not reach ListenBrainz or validate the username."})
