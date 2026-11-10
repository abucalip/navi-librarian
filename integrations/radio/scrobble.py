"""Radio scrobbling and love, sent straight to Last.fm by the server (off by default).

Radio songs never reach Navidrome, so Navidrome's own scrobbling never sees them and cannot count
them twice. A song is scrobbled once its play is logged (30 seconds heard), and only when the owner
has switched scrobbling on. Every call here is outside the audio path: the relay hands the play id
to a background thread.

Credentials come from the environment (the owner's config.env): LASTFM_API_KEY, LASTFM_SHARED_SECRET
and LASTFM_SESSION_KEY. The session key is the one signed-in Last.fm user's key; nothing here asks for
a password. Secrets are never returned to clients or written to logs.
"""
from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from integrations.radio.store import RadioStore

LASTFM_URL = "https://ws.audioscrobbler.com/2.0/"
SETTING_KEY = "scrobble_enabled"
_TIMEOUT = httpx.Timeout(10.0)
_log = logging.getLogger(__name__)


class ScrobbleError(ValueError):
    """The request cannot be done as asked (shown to the owner as the reason)."""


class ScrobbleFailed(RuntimeError):
    """Last.fm did not accept the request, or could not be reached."""


@dataclass(frozen=True)
class Credentials:
    api_key: str
    shared_secret: str
    session_key: str

    @property
    def ready(self) -> bool:
        return bool(self.api_key and self.shared_secret and self.session_key)


def credentials_from_env(env: Mapping[str, str] | None = None) -> Credentials:
    env = os.environ if env is None else env
    return Credentials(
        api_key=str(env.get("LASTFM_API_KEY") or "").strip(),
        shared_secret=str(env.get("LASTFM_SHARED_SECRET") or "").strip(),
        session_key=str(env.get("LASTFM_SESSION_KEY") or "").strip(),
    )


def sign(params: Mapping[str, Any], shared_secret: str) -> str:
    """Last.fm's api_sig: parameters sorted by name, name and value joined, the secret appended, MD5.
    ``format`` and ``callback`` are not signed."""
    joined = "".join(f"{key}{params[key]}" for key in sorted(params) if key not in ("format", "callback"))
    return hashlib.md5((joined + shared_secret).encode("utf-8")).hexdigest()


def enabled(store: RadioStore) -> bool:
    return store.get_setting(SETTING_KEY) == "1"


def set_enabled(store: RadioStore, creds: Credentials, on: bool) -> None:
    if on and not creds.ready:
        raise ScrobbleError(
            "Last.fm is not set up for scrobbling. Add LASTFM_API_KEY, LASTFM_SHARED_SECRET and "
            "LASTFM_SESSION_KEY to the configuration first.")
    store.set_setting(SETTING_KEY, "1" if on else "")


def _post(post: Callable[..., Any] | None, creds: Credentials, method: str, fields: dict[str, Any]) -> dict:
    send = post or httpx.post  # looked up at call time so tests can replace httpx.post
    params = {"method": method, "api_key": creds.api_key, "sk": creds.session_key, **fields}
    params["api_sig"] = sign(params, creds.shared_secret)
    params["format"] = "json"
    try:
        response = send(LASTFM_URL, data=params, headers={"User-Agent": "Discair/1.0"}, timeout=_TIMEOUT)
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        raise ScrobbleFailed("Could not reach Last.fm.")
    if not isinstance(payload, dict):
        raise ScrobbleFailed("Last.fm sent an unexpected answer.")
    if payload.get("error"):
        raise ScrobbleFailed(f"Last.fm refused the request (error {payload.get('error')}).")
    return payload


def _accepted(payload: dict) -> int:
    attr = (payload.get("scrobbles") or {}).get("@attr") or {}
    try:
        return int(attr.get("accepted") or 0)
    except (TypeError, ValueError):
        return 0


def submit(store: RadioStore, play_id: int, *, creds: Credentials, post: Callable[..., Any] | None = None) -> str:
    """Scrobble one logged play. Returns what happened: 'sent', 'ignored' (Last.fm did not count it),
    'off', 'not_configured', 'done' (already scrobbled), 'no_artist' or 'missing'.

    The play is claimed before the call and never retried: a request whose answer was lost may
    have been accepted, so a second send could count the song twice.
    """
    if not enabled(store):
        return "off"
    if not creds.ready:
        return "not_configured"
    play = store.get_play(play_id)
    if play is None:
        return "missing"
    if not play["artist"]:
        return "no_artist"
    if not store.claim_scrobble(play_id):
        return "done"
    payload = _post(post, creds, "track.scrobble", {
        "artist": play["artist"], "track": play["title"], "timestamp": int(play["heard_at"]),
    })
    if _accepted(payload) < 1:
        _log.info("Last.fm ignored the scrobble of radio play %s", play_id)
        return "ignored"
    return "sent"


def submit_quietly(store: RadioStore, play_id: int) -> None:
    """For the background thread: a failure is logged without the song or any secret."""
    try:
        submit(store, play_id, creds=credentials_from_env())
    except Exception as exc:  # never raised into the relay
        _log.warning("Radio scrobble for play %s failed: %s", play_id, type(exc).__name__)


def love(store: RadioStore, play_id: int, *, creds: Credentials, post: Callable[..., Any] | None = None) -> None:
    """Love a logged song on Last.fm. Independent of the scrobbling switch: it is an explicit request."""
    play = store.get_play(play_id)
    if play is None:
        raise LookupError("No such song in the radio log.")
    if not play["artist"]:
        raise ScrobbleError("The station did not name an artist for this song.")
    if not creds.ready:
        raise ScrobbleError("Last.fm is not set up for love. Add the Last.fm keys to the configuration first.")
    _post(post, creds, "track.love", {"artist": play["artist"], "track": play["title"]})
    store.set_loved(play_id)
