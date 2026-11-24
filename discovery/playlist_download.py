"""Validate an Inbox occurrence before handing it to single-track acquisition."""

from concurrent.futures import Future
from dataclasses import replace
import sqlite3
from threading import Lock
from time import time
from unicodedata import normalize

import httpx

from acquisition import track_service
from discovery.recording_match import match_recordings
from discovery.search.index import SongInventoryError, build_owned_data, fetch_song_inventory
from discovery.search.normalize import normalize_mbid
from integrations.listenbrainz.client import lookup_recording
from integrations.musicbrainz.recording_album import lookup_inbox_album
from integrations.navidrome.client import items
from integrations.navidrome.playlists import PlaylistClient, PlaylistProviderError


_lock = Lock()
_requests = {}


class InboxDownloadError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code


def _label(value):
    return " ".join(normalize("NFC", value).casefold().split()) if isinstance(value, str) else ""


def _ownership(track, owned, *, allow_ambiguous=False):
    match, = match_recordings((track,), owned)
    if match.state == "ambiguous" and not allow_ambiguous:
        raise InboxDownloadError(409, "ambiguous_track", "This recording cannot be identified safely.")
    return match.song_id


def _resolve_album(librarian, track):
    token = str(librarian._discovery_settings_read().get("listenbrainz_token") or "").strip()
    try:
        row = lookup_recording(track.artist, track.title, token=token or None)
    except (httpx.HTTPError, ValueError):
        row = {}
    mbid = normalize_mbid(row.get("recording_mbid"))
    release = normalize_mbid(row.get("release_mbid"))
    album = row.get("release_name")
    mapped_release = None
    if mbid and release and _label(album) and (
        _label(row.get("artist_credit_name")), _label(row.get("recording_name"))
    ) == (_label(track.artist), _label(track.title)):
        mapped_release = (mbid, release, album)
        if mbid == track.recording_mbid and track.release_mbid in (None, release):
            return mbid, album, None

    try:
        result = lookup_inbox_album(
            track.artist, track.title, recording_mbid=track.recording_mbid,
            release_mbid=track.release_mbid, duration_ms=track.duration_ms, mapped_release=mapped_release,
        )
    except (OSError, ValueError, AttributeError, TypeError) as error:
        raise InboxDownloadError(502, "metadata_unavailable", "The recording lookup is unavailable.") from error
    if result is None:
        raise InboxDownloadError(409, "unresolved_album", "Could not confirm which album contains this recording.")
    return result


def _check_inventory(librarian, config, navidrome, marker):
    try:
        if marker is None or navidrome.scan_marker() != marker or librarian._navidrome_config() != config:
            raise PlaylistProviderError("The library scan or connection changed.")
    except (PlaylistProviderError, ValueError) as error:
        raise InboxDownloadError(503, "ownership_unavailable", "Could not verify current library ownership.") from error


def _download(librarian, track, config, source):
    navidrome = PlaylistClient(config)
    try:
        marker = navidrome.scan_marker()
        if marker is None:
            raise PlaylistProviderError("The library is being scanned.")
        songs = fetch_song_inventory(navidrome.search_songs, items)
        owned = build_owned_data(generation=navidrome.target_key, built_at=time(), artists=(), albums=(), songs=songs)
    except (PlaylistProviderError, SongInventoryError) as error:
        raise InboxDownloadError(503, "ownership_unavailable", "Could not verify current library ownership.") from error

    # Metadata may corroborate a tag-only owned match, so repeat matching after enrichment.
    has_album = bool(_label(track.album))
    song_id = _ownership(track, owned, allow_ambiguous=not has_album)
    year = None
    if not song_id and not has_album:
        try:
            existing = track_service.inbox_download_job(librarian, source)
        except sqlite3.Error as error:
            raise InboxDownloadError(503, "acquisition_unavailable", "Could not read acquisition state.") from error
        if existing and (_label(existing["artist"]), _label(existing["title"])) == (
            _label(track.artist), _label(track.title)
        ):
            mbid, album, year = existing["recording_mbid"], existing["album"], existing["year"]
        else:
            mbid, album, year = _resolve_album(librarian, track)
        track = replace(track, recording_mbid=mbid, album=album)
        song_id = _ownership(track, owned)
    _check_inventory(librarian, config, navidrome, marker)
    if song_id:
        return {"ok": True, "status": "owned", "song_id": song_id}

    try:
        result = track_service.request_track(
            librarian, track.artist, track.album, track.title, year=year,
            inbox_source=source, recording_mbid=track.recording_mbid,
        )
    except (httpx.HTTPError, OSError, sqlite3.Error, ValueError) as error:
        raise InboxDownloadError(502, "acquisition_unavailable", "Could not request this track.") from error
    # Expose the acquisition identity for polling and a separate display album.
    return {
        "ok": result["ok"], "status": result["status"], "message": result["message"],
        "artist": result["artist"], "job_album": result["album"], "album": track.album.strip(),
    }


def download_track(librarian, edition_id, track):
    """Share concurrent clicks, including clicks in repeated edition occurrences."""
    if track.conflicting_recording_mbids:
        raise InboxDownloadError(409, "ambiguous_track", "This track has conflicting recording identifiers.")
    if not _label(track.artist) or not _label(track.title):
        raise InboxDownloadError(409, "unresolved_track", "This track needs an artist and title to download.")
    track = replace(track, recording_mbid=normalize_mbid(track.recording_mbid),
                    release_mbid=normalize_mbid(track.release_mbid))
    source = (f"{track.recording_mbid}/{track.release_mbid or ''}" if track.recording_mbid
              else f"{edition_id}/{track.position}")
    try:
        config = librarian._navidrome_config()
    except ValueError as error:
        raise InboxDownloadError(503, "ownership_unavailable", "Could not verify current library ownership.") from error
    key = (config[:2], track.recording_mbid, track.release_mbid, _label(track.artist),
           _label(track.title), _label(track.album), track.duration_ms)
    with _lock:
        pending = _requests.get(key)
        if pending is None:
            pending = _requests[key] = Future()
            leader = True
        else:
            leader = False
    if not leader:
        return pending.result()
    try:
        result = _download(librarian, track, config, source)
        pending.set_result(result)
        return result
    except BaseException as error:
        pending.set_exception(error)
        raise
    finally:
        with _lock:
            del _requests[key]
