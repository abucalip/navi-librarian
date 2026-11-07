"""Smart playlist routes (Server V2 Phase 6 item 6, slice 14).

HTTP adapters only: list, create-or-replace, read, delete and evaluate saved rule sets kept in the
owner-state file. Bodies come from ``intelligence.api.smart_playlists``. A result is evaluated on
request over the Navidrome song list and is not stored. The server never writes a playlist to
Navidrome and makes no provider call. Rule content is never logged.
"""
import threading
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.api.dependencies import get_librarian
from intelligence.api.smart_playlists import (
    build_get_body, build_insights, build_list_body, build_put_body, build_result_body, delete_playlist, songs_from_subsonic,
)
from intelligence.store import open_store
from intelligence.taste.smart_playlist_persistence import valid_rule_id

router = APIRouter()

STORE_FILE = "intelligence.sqlite3"
SONG_PAGE = 500
MAX_SONGS = 50_000
_LOCK = threading.Lock()


def _now() -> float:
    return time.time()


def _store(librarian):
    return open_store(librarian.DATA_DIR / STORE_FILE)


def _check_id(rule_id: str) -> None:
    if not valid_rule_id(rule_id):
        raise HTTPException(status_code=400, detail="rule_id must be a lowercase UUID")


def _fetch_songs(librarian) -> list[dict[str, Any]]:
    """Page the whole Navidrome song list (an empty ``search3`` query lists everything)."""
    songs: list[dict[str, Any]] = []
    offset = 0
    while offset < MAX_SONGS:
        root = librarian.api_call("search3", query='""', artistCount=0, albumCount=0,
                                  songCount=SONG_PAGE, songOffset=offset)
        page = librarian.items(root.get("searchResult3", {}).get("song"))
        songs.extend(songs_from_subsonic(page))
        if len(page) < SONG_PAGE:
            break
        offset += SONG_PAGE
    return songs


@router.get("/api/playlists/smart")
def list_smart(librarian=Depends(get_librarian)):
    try:
        db = _store(librarian)
        try:
            return build_list_body(db)
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read smart playlists.")


@router.put("/api/playlists/smart/{rule_id}")
def put_smart(rule_id: str, body: dict[str, Any], librarian=Depends(get_librarian)):
    _check_id(rule_id)
    try:
        with _LOCK:
            db = _store(librarian)
            try:
                ok, payload = build_put_body(db, rule_id, body, _now())
            finally:
                db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not store the smart playlist.")
    if not ok:
        return JSONResponse(status_code=400, content=payload)
    return payload


@router.get("/api/playlists/smart/{rule_id}")
def get_smart(rule_id: str, librarian=Depends(get_librarian)):
    _check_id(rule_id)
    try:
        db = _store(librarian)
        try:
            body = build_get_body(db, rule_id)
        finally:
            db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read the smart playlist.")
    if body is None:
        raise HTTPException(status_code=404, detail="Smart playlist not found.")
    return body


@router.delete("/api/playlists/smart/{rule_id}")
def delete_smart(rule_id: str, librarian=Depends(get_librarian)):
    _check_id(rule_id)
    try:
        with _LOCK:
            db = _store(librarian)
            try:
                deleted = delete_playlist(db, rule_id)
            finally:
                db.close()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not delete the smart playlist.")
    if not deleted:
        raise HTTPException(status_code=404, detail="Smart playlist not found.")
    return {"deleted": True}


@router.get("/api/playlists/smart/{rule_id}/result")
def result_smart(rule_id: str, seed: int = 0, librarian=Depends(get_librarian)):
    _check_id(rule_id)
    try:
        db = _store(librarian)
        try:
            if build_get_body(db, rule_id) is None:
                raise HTTPException(status_code=404, detail="Smart playlist not found.")
            try:
                songs = _fetch_songs(librarian)
            except Exception:
                raise HTTPException(status_code=502, detail="Could not read the Navidrome song list.")
            return build_result_body(db, rule_id, songs, _now(), seed, insights=build_insights(db, songs))
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not evaluate the smart playlist.")
