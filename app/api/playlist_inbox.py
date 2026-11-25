"""Authenticated Playlist Inbox HTTP routes."""

from contextlib import closing
from itertools import islice
import os
import sqlite3
from time import time

from fastapi import APIRouter, Depends, HTTPException, Path, Response

from acquisition.state import read_track_statuses
from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from app.api.search import owned_view
from discovery.playlist_download import InboxDownloadError, download_track
from discovery.playlist_inbox import edition_detail, edition_tracks, list_items
from integrations.navidrome.playlists import PlaylistClient
from intelligence.store import open_readonly
from intelligence.store.playlist_editions import edition_copy_states, get_edition, list_current_editions
from settings.service import listenbrainz_username

router = APIRouter(prefix="/api/playlists/inbox")


def _configured(librarian):
    settings = librarian._discovery_settings_read()
    try:
        listenbrainz_username(lambda: settings)
    except ValueError:
        return False
    return bool(str(settings.get("listenbrainz_token") or "").strip()
                or os.environ.get("LISTENBRAINZ_TOKEN", "").strip())


def _copy_states(db, librarian):
    try:
        navidrome = PlaylistClient(librarian._navidrome_config())
    except ValueError:
        return None
    return edition_copy_states(db, navidrome.target_key)


def _with_copy_state(item, states):
    state = "unconfigured" if states is None else states.get(item["edition_id"], "not_linked")
    return {**item, "navidrome_sync_state": state}


@router.get("")
def inbox_list(response: Response, librarian=Depends(get_librarian)):
    try:
        with closing(open_readonly(librarian.DATA_DIR / STORE_FILE)) as db:
            editions = list_current_editions(db)
            states = _copy_states(db, librarian) if editions else None
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Playlist Inbox store unavailable.") from error

    response.headers["Cache-Control"] = "no-store"
    configured = _configured(librarian)
    if not editions:
        return {
            "state": "empty" if configured else "unconfigured",
            "listenbrainz_configured": configured,
            "index_state": None,
            "items": [],
        }

    view = owned_view(librarian)
    return {
        "state": "ready",
        "listenbrainz_configured": configured,
        "index_state": view.state,
        "items": [_with_copy_state(item, states) for item in list_items(editions, view.data, time())],
    }


@router.get("/{edition_id}")
def inbox_detail(response: Response, edition_id: int = Path(gt=0, le=2**63 - 1), librarian=Depends(get_librarian)):
    try:
        with closing(open_readonly(librarian.DATA_DIR / STORE_FILE)) as db:
            edition = get_edition(db, edition_id)
            if edition is None:
                raise HTTPException(status_code=404, detail="Playlist Inbox edition not found.")
            states = _copy_states(db, librarian)

        view = owned_view(librarian)
        jobs = read_track_statuses(librarian.DISCOVERY_DB) if view.data is not None and edition.snapshot.tracks else {}
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Playlist Inbox store unavailable.") from error

    response.headers["Cache-Control"] = "no-store"
    return {
        "listenbrainz_configured": _configured(librarian),
        "index_state": view.state,
        **_with_copy_state(edition_detail(edition, view.data, jobs, librarian._music_key, time()), states),
    }


@router.post("/{edition_id}/tracks/{position}/download")
def inbox_download(
    response: Response,
    edition_id: int = Path(gt=0, le=2**63 - 1),
    position: int = Path(ge=0, le=2**63 - 2),
    librarian=Depends(get_librarian),
):
    try:
        with closing(open_readonly(librarian.DATA_DIR / STORE_FILE)) as db:
            edition = get_edition(db, edition_id)
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Playlist Inbox store unavailable.") from error
    if edition is None:
        raise HTTPException(status_code=404, detail="Playlist Inbox edition not found.")
    if position >= len(edition.snapshot.tracks):
        raise HTTPException(status_code=404, detail="Playlist Inbox track not found.")
    track = next(islice(edition_tracks(edition), position, None))
    try:
        result = download_track(librarian, edition_id, track)
    except InboxDownloadError as error:
        raise HTTPException(status_code=error.status, detail={"code": error.code, "message": str(error)}) from error
    response.headers["Cache-Control"] = "no-store"
    return {"edition_id": edition_id, "position": position, **result}
