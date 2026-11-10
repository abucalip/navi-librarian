"""Grab the radio routes. HTTP adapter only: relay, logging and matching live in integrations/radio."""
from __future__ import annotations

import threading

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse

from acquisition import track_service
from app.api.dependencies import get_librarian
from discovery.search.query import artwork_url
from integrations.musicbrainz.recording_album import lookup_recording_album
from integrations.radio import library_match, logos, relay, scrobble, stations
from integrations.radio import now as radio_now
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


LOGO_CACHE_CONTROL = "private, max-age=300"


@router.put("/api/radio/stations/{station_id}/favourite")
def radio_favourite(station_id: str, payload: dict, librarian=Depends(get_librarian), store=Depends(get_store)):
    return _station_call(lambda: stations.set_favourite(
        librarian.api_call, store, station_id, payload.get("favourite")))


@router.put("/api/radio/stations/{station_id}/tags")
def radio_tags(station_id: str, payload: dict, librarian=Depends(get_librarian), store=Depends(get_store)):
    return _station_call(lambda: stations.set_tags(librarian.api_call, store, station_id, payload.get("tags")))


@router.get("/api/radio/stations/{station_id}/logo")
def radio_logo(station_id: str, size: int = 128, librarian=Depends(get_librarian), store=Depends(get_store)):
    """A station's logo: the cached image, or a generated PNG tile. Resolved on first request."""
    if size not in logos.LOGO_SIZES:
        raise HTTPException(status_code=400, detail="size must be 128 or 512")
    try:
        cached = logos.cached_logo(store, librarian.DATA_DIR, station_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid station id")
    if cached is not None:
        return Response(cached.path.read_bytes(), media_type=cached.media_type,
                        headers={"Cache-Control": LOGO_CACHE_CONTROL})
    subject = _station_call(lambda: stations.logo_subject(librarian.api_call, store, station_id))
    body, media_type = logos.image_bytes(subject, store, librarian.DATA_DIR, size)
    return Response(body, media_type=media_type, headers={"Cache-Control": LOGO_CACHE_CONTROL})


def _save_logo(station_id: str, body: bytes, librarian, store) -> dict:
    _station_call(lambda: stations.logo_subject(librarian.api_call, store, station_id))
    try:
        logos.set_override(store, librarian.DATA_DIR, station_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": station_id, "logo_url": stations.logo_path(station_id), "source": logos.OVERRIDE}


@router.put("/api/radio/stations/{station_id}/logo")
async def radio_put_logo(station_id: str, request: Request, librarian=Depends(get_librarian),
                         store=Depends(get_store)):
    """The owner's own image for a station (PNG, JPEG, GIF, WebP or ICO, up to 2 MB)."""
    body = await request.body()
    if len(body) > logos.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The image is too large.")
    return await run_in_threadpool(_save_logo, station_id, body, librarian, store)


@router.delete("/api/radio/stations/{station_id}/logo")
def radio_delete_logo(station_id: str, librarian=Depends(get_librarian), store=Depends(get_store)):
    """Clear the stored logo; the next request resolves it again from the sources."""
    _station_call(lambda: stations.logo_subject(librarian.api_call, store, station_id))
    try:
        logos.clear(store, librarian.DATA_DIR, station_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid station id")
    return {"ok": True, "logo_url": stations.logo_path(station_id)}


def _library_lookup(librarian, station_id: str):
    """Looks a parsed song up in the library once per song; a failed lookup is not kept, so it is retried."""
    def lookup(raw: str, artist: str, title: str):
        cached = radio_now.NOW.library(station_id, raw)
        if cached is not None:
            return cached
        try:
            song = library_match.find_song(librarian.api_call, artist, title)
        except Exception:
            return None
        result = {"in_library": song is not None,
                  "cover_url": artwork_url(song.get("coverArt")) if song else None}
        radio_now.NOW.remember_library(station_id, raw, result)
        return result
    return lookup


def _now_for(librarian, store, station_id: str) -> dict:
    local = store.get_station(station_id)
    return radio_now.view(
        radio_now.NOW.live(station_id), _library_lookup(librarian, station_id),
        proxied=bool(local and local["enabled"]), unreachable=radio_now.NOW.unreachable(station_id))


@router.get("/api/radio/stations/{station_id}/now")
def radio_station_now(station_id: str, librarian=Depends(get_librarian), store=Depends(get_store)):
    """The song a station is playing right now, from the relay's in-memory holder (no upstream call)."""
    return _now_for(librarian, store, station_id)


@router.get("/api/radio/now")
def radio_now_all(librarian=Depends(get_librarian), store=Depends(get_store)):
    """The live song of every relayed station; a station nobody is listening to is 'idle'."""
    return {"items": [{"id": local["station_id"], **_now_for(librarian, store, local["station_id"])}
                      for local in store.enabled_stations()]}


@router.get("/api/radio/plays")
def radio_plays(limit: int = 100, librarian=Depends(get_librarian), store=Depends(get_store)):
    """The Heard list: each logged play plus ``in_library`` (cached per song, one search the first time)."""
    if not 1 <= limit <= 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    return {"items": [{**play, "in_library": library_match.OWNED.owned(librarian.api_call, play.get("artist"),
                                                                    play.get("title"))}
                      for play in store.list_plays(limit)]}


@router.delete("/api/radio/plays")
def radio_clear_plays(store=Depends(get_store)):
    return {"ok": True, "removed": store.clear_plays()}


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


def _scrobble_in_background(store, play_id: int) -> None:
    """Scrobbling is a network call, so it runs on its own thread and never on the audio path."""
    threading.Thread(target=scrobble.submit_quietly, args=(store, play_id), daemon=True).start()


@router.get("/api/radio/scrobbling")
def radio_scrobbling(store=Depends(get_store)):
    """Whether radio songs are scrobbled to Last.fm (default off), and whether Last.fm is set up."""
    return {"enabled": scrobble.enabled(store), "configured": scrobble.credentials_from_env().ready}


@router.put("/api/radio/scrobbling")
def radio_set_scrobbling(payload: dict, store=Depends(get_store)):
    on = payload.get("enabled")
    if not isinstance(on, bool):
        raise HTTPException(status_code=400, detail="enabled must be true or false")
    creds = scrobble.credentials_from_env()
    try:
        scrobble.set_enabled(store, creds, on)
    except scrobble.ScrobbleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"enabled": on, "configured": creds.ready}


@router.post("/api/radio/plays/{play_id}/love")
def radio_love(play_id: int, store=Depends(get_store)):
    """Love a logged song on Last.fm. An explicit request, so it works whether or not scrobbling is on."""
    try:
        scrobble.love(store, play_id, creds=scrobble.credentials_from_env())
    except LookupError:
        raise HTTPException(status_code=404, detail="No such song in the radio log.")
    except scrobble.ScrobbleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except scrobble.ScrobbleFailed as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {"ok": True, "loved": True}


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
        radio_now.NOW.mark_unreachable(station["station_id"])
        raise HTTPException(status_code=502, detail="The station is unreachable.")
    content_type = upstream.headers.get("content-type", "")
    if upstream.status_code != 200 or not relay.stream_is_audio(content_type):
        await upstream.aclose()
        await client.aclose()
        radio_now.NOW.mark_unreachable(station["station_id"])
        raise HTTPException(status_code=502, detail="The station did not return an audio stream.")

    metaint = relay.metaint_of(upstream.headers)
    headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    if upstream.headers.get("icy-name"):
        headers["icy-name"] = upstream.headers["icy-name"]
    if wants_metadata and metaint:
        headers["icy-metaint"] = str(metaint)
    tracker = ListenTracker(store, station["station_id"], station["name"],
                            holder=radio_now.NOW, has_metadata=bool(metaint),
                            on_logged=lambda play_id: _scrobble_in_background(store, play_id))

    async def body():
        try:
            async for chunk in relay.relay_body(upstream, metaint, wants_metadata, tracker):
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(body(), media_type=content_type, headers=headers)
