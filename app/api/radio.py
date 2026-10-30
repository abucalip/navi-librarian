"""Grab the radio routes. HTTP adapter only: relay, logging and matching live in integrations/radio."""
from __future__ import annotations

import threading

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from acquisition import track_service
from app.api.dependencies import get_librarian
from integrations.musicbrainz.recording_album import lookup_recording_album
from integrations.radio import relay, stations
from integrations.radio.listening import ListenTracker
from integrations.radio.store import RadioStore

router = APIRouter()

_STORES: dict[str, RadioStore] = {}
_STORES_LOCK = threading.Lock()
_UPSTREAM_TIMEOUT = httpx.Timeout(10.0, read=30.0)
# Replaced in tests so the relay can be exercised without a network.
client_factory = httpx.AsyncClient


def get_store(librarian=Depends(get_librarian)) -> RadioStore:
    path = str(librarian.DATA_DIR / "radio.sqlite3")
    with _STORES_LOCK:
        if path not in _STORES:
            _STORES[path] = RadioStore(path)
        return _STORES[path]


def _station_call(action):
    try:
        return action()
    except stations.StationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach Navidrome's radio stations.")


@router.get("/api/radio/stations")
def radio_stations(librarian=Depends(get_librarian), store=Depends(get_store)):
    return {"items": _station_call(lambda: stations.list_stations(librarian.api_call, store))}


@router.get("/api/radio/settings")
def radio_settings(store=Depends(get_store)):
    return {"app_url": store.get_setting(stations.APP_URL_KEY)}


@router.put("/api/radio/settings")
def radio_save_settings(payload: dict, librarian=Depends(get_librarian), store=Depends(get_store)):
    """The address Navidrome clients (a phone on Tailscale, say) reach this app at."""
    return _station_call(lambda: stations.set_app_url(librarian.api_call, store, str(payload.get("app_url") or "")))


@router.post("/api/radio/stations/{station_id}/enable")
def radio_enable(station_id: str, payload: dict, librarian=Depends(get_librarian), store=Depends(get_store)):
    base_url = str(payload.get("base_url") or "")
    return _station_call(lambda: stations.enable(librarian.api_call, store, station_id, base_url))


@router.post("/api/radio/stations/{station_id}/disable")
def radio_disable(station_id: str, librarian=Depends(get_librarian), store=Depends(get_store)):
    return _station_call(lambda: stations.disable(librarian.api_call, store, station_id))


@router.get("/api/radio/plays")
def radio_plays(limit: int = 100, store=Depends(get_store)):
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return {"items": store.list_plays(limit)}


@router.delete("/api/radio/plays/{play_id}")
def radio_delete_play(play_id: int, store=Depends(get_store)):
    if not store.delete_play(play_id):
        raise HTTPException(status_code=404, detail="No such song in the radio log.")
    return {"ok": True}


@router.post("/api/radio/plays/{play_id}/get")
def radio_get_play(play_id: int, librarian=Depends(get_librarian), store=Depends(get_store)):
    """Download a logged song with the song-only Get, once its album is known."""
    play = store.get_play(play_id)
    if play is None:
        raise HTTPException(status_code=404, detail="No such song in the radio log.")
    if not play["artist"]:
        return {"ok": False, "message": "The station did not name an artist for this song."}
    album, year = play["album"], play["year"]
    if not album:
        try:
            found = lookup_recording_album(play["artist"], play["title"])
        except Exception:
            raise HTTPException(status_code=502, detail="Could not look up this song's album.")
        if not found:
            return {"ok": False, "message": "Could not find which album this song is on."}
        album, year = found["album"], found["year"]
        store.set_album(play_id, album, year)
    try:
        result = track_service.request_track(librarian, play["artist"], album, play["title"], None, year, None)
    except Exception:
        raise HTTPException(status_code=502, detail="Could not search slskd for this song.")
    if result.get("ok") and result.get("status") != "no_matches":
        store.mark_grabbed(play_id)
    return {**result, "album": album}


@router.get("/radio/stream/{token}")
async def radio_stream(token: str, request: Request, store=Depends(get_store)):
    """The relay a station's Navidrome address points at. The token is the credential: Subsonic
    clients cannot send the web session cookie, so this path is public to the login gate."""
    station = store.station_by_token(token)
    if station is None:
        raise HTTPException(status_code=404, detail="Unknown radio stream.")
    wants_metadata = request.headers.get("icy-metadata") == "1"
    client = client_factory(timeout=_UPSTREAM_TIMEOUT, follow_redirects=True, max_redirects=5)
    try:
        upstream = await client.send(
            client.build_request("GET", station["original_url"], headers=relay.UPSTREAM_REQUEST_HEADERS),
            stream=True)
    except Exception:
        await client.aclose()
        raise HTTPException(status_code=502, detail="The station is unreachable.")
    content_type = upstream.headers.get("content-type", "")
    if upstream.status_code != 200 or not relay.stream_is_audio(content_type):
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail="The station did not return an audio stream.")

    metaint = relay.metaint_of(upstream.headers)
    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if upstream.headers.get("icy-name"):
        headers["icy-name"] = upstream.headers["icy-name"]
    if wants_metadata and metaint:
        headers["icy-metaint"] = str(metaint)
    tracker = ListenTracker(store, station["station_id"], station["name"])

    async def body():
        try:
            async for chunk in relay.relay_body(upstream, metaint, wants_metadata, tracker):
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(body(), media_type=content_type, headers=headers)
