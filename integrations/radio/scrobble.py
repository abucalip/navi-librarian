"""Radio scrobbling and love, sent straight to ListenBrainz by the server (off by default).

Radio songs never reach Navidrome, so Navidrome's own scrobbling never sees them and cannot count
them twice. A song is scrobbled once its play is logged (30 seconds heard), and only when the owner
has switched scrobbling on. Every call here is outside the audio path: the relay hands the play id
to a background thread.

Credentials come from the environment (the owner's config.env): LISTENBRAINZ_TOKEN.
Secrets are never returned to clients or written to logs.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx

from integrations.musicbrainz.recording_album import lookup_recording_mbid
from integrations.radio.store import RadioStore

LISTENBRAINZ_SUBMIT_URL = "https://api.listenbrainz.org/1/submit-listens"
LISTENBRAINZ_FEEDBACK_URL = "https://api.listenbrainz.org/1/feedback/recording-feedback"
SETTING_KEY = "scrobble_enabled"
_TIMEOUT = httpx.Timeout(10.0)
_USER_AGENT = "Discair/1.0 (+https://github.com/abucalip/navi-librarian)"
_log = logging.getLogger(__name__)


class ScrobbleError(ValueError):
    """The request cannot be done as asked (shown to the owner as the reason)."""


class ScrobbleFailed(RuntimeError):
    """ListenBrainz did not accept the request, or could not be reached."""


@dataclass(frozen=True)
class Credentials:
    """ListenBrainz user token for radio scrobbling and recording feedback."""

    token: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.token)


def credentials_from_env(env: Mapping[str, str] | None = None) -> Credentials:
    env = os.environ if env is None else env
    return Credentials(token=str(env.get("LISTENBRAINZ_TOKEN") or "").strip())


def enabled(store: RadioStore) -> bool:
    return store.get_setting(SETTING_KEY) == "1"


def set_enabled(store: RadioStore, creds: Credentials, on: bool) -> None:
    if on and not creds.ready:
        raise ScrobbleError(
            "ListenBrainz is not set up for scrobbling. Add LISTENBRAINZ_TOKEN to the configuration first.")
    store.set_setting(SETTING_KEY, "1" if on else "")


def _post(post: Callable[..., Any] | None, creds: Credentials, url: str, body: dict[str, Any]) -> dict[str, Any]:
    send = post or httpx.post  # looked up at call time so tests can replace httpx.post
    headers = {
        "Authorization": f"Token {creds.token}",
        "User-Agent": _USER_AGENT,
    }
    try:
        response = send(url, json=body, headers=headers, timeout=_TIMEOUT)
        status_code = getattr(response, "status_code", 200)
        if isinstance(status_code, int) and status_code >= 400:
            raise ScrobbleFailed(f"ListenBrainz refused the request (HTTP {status_code}).")
        payload = response.json()
    except ScrobbleFailed:
        raise
    except (httpx.HTTPError, ValueError):
        raise ScrobbleFailed("Could not reach ListenBrainz.")
    if not isinstance(payload, dict):
        raise ScrobbleFailed("ListenBrainz sent an unexpected answer.")
    if payload.get("error"):
        raise ScrobbleFailed(f"ListenBrainz refused the request ({payload.get('error')}).")
    return payload


def submit(store: RadioStore, play_id: int, *, creds: Credentials, post: Callable[..., Any] | None = None) -> str:
    """Scrobble one logged play to ListenBrainz. Returns what happened: 'sent', 'off',
    'not_configured', 'done' (already scrobbled), 'no_artist' or 'missing'.

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
    track_metadata: dict[str, Any] = {
        "artist_name": play["artist"],
        "track_name": play["title"],
    }
    if play.get("album"):
        track_metadata["release_name"] = play["album"]
    body = {
        "listen_type": "single",
        "payload": [{
            "listened_at": int(play["heard_at"]),
            "track_metadata": track_metadata,
        }],
    }
    _post(post, creds, LISTENBRAINZ_SUBMIT_URL, body)
    return "sent"


def submit_quietly(store: RadioStore, play_id: int) -> None:
    """For the background thread: a failure is logged without the song or any secret."""
    try:
        submit(store, play_id, creds=credentials_from_env())
    except Exception as exc:  # never raised into the relay
        _log.warning("Radio scrobble for play %s failed: %s", play_id, type(exc).__name__)


def love(
    store: RadioStore,
    play_id: int,
    *,
    creds: Credentials,
    post: Callable[..., Any] | None = None,
    lookup_mbid: Callable[[str, str], str | None] | None = None,
) -> bool:
    """Love a logged song on ListenBrainz (or locally if no recording MBID can be resolved).
    Independent of the scrobbling switch: it is an explicit request.

    Returns True if submitted to ListenBrainz, False if loved locally only.
    """
    play = store.get_play(play_id)
    if play is None:
        raise LookupError("No such song in the radio log.")
    if not play["artist"]:
        raise ScrobbleError("The station did not name an artist for this song.")
    if not creds.ready:
        raise ScrobbleError(
            "ListenBrainz is not set up for love. Add LISTENBRAINZ_TOKEN to the configuration first."
        )
    resolve = lookup_mbid or lookup_recording_mbid
    recording_mbid: str | None = None
    try:
        recording_mbid = resolve(play["artist"], play["title"])
    except OSError as exc:
        _log.info("Could not resolve recording MBID for radio play %s: %s", play_id, type(exc).__name__)
    if recording_mbid:
        _post(post, creds, LISTENBRAINZ_FEEDBACK_URL, {"recording_mbid": recording_mbid, "score": 1})
        store.set_loved(play_id)
        return True
    store.set_loved(play_id)
    return False
