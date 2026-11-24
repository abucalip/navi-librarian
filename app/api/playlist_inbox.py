"""Authenticated, read-only Playlist Inbox HTTP routes."""

from contextlib import closing
import os
import sqlite3
from time import time

from fastapi import APIRouter, Depends, HTTPException, Path, Response

from acquisition.state import read_track_statuses
from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from app.api.search import owned_view
from discovery.playlist_inbox import edition_detail, list_items
from intelligence.store import open_readonly
from intelligence.store.playlist_editions import get_edition, list_current_editions
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


@router.get("")
def inbox_list(response: Response, librarian=Depends(get_librarian)):
    try:
        with closing(open_readonly(librarian.DATA_DIR / STORE_FILE)) as db:
            editions = list_current_editions(db)
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
        "items": list_items(editions, view.data, time()),
    }


@router.get("/{edition_id}")
def inbox_detail(response: Response, edition_id: int = Path(gt=0, le=2**63 - 1), librarian=Depends(get_librarian)):
    try:
        with closing(open_readonly(librarian.DATA_DIR / STORE_FILE)) as db:
            edition = get_edition(db, edition_id)
        if edition is None:
            raise HTTPException(status_code=404, detail="Playlist Inbox edition not found.")

        view = owned_view(librarian)
        jobs = read_track_statuses(librarian.DISCOVERY_DB) if view.data is not None and edition.snapshot.tracks else {}
    except sqlite3.Error as error:
        raise HTTPException(status_code=503, detail="Playlist Inbox store unavailable.") from error

    response.headers["Cache-Control"] = "no-store"
    return {
        "listenbrainz_configured": _configured(librarian),
        "index_state": view.state,
        **edition_detail(edition, view.data, jobs, librarian._music_key, time()),
    }
