"""Global search and artist routes (contract sections 3.1 and 3.3).

HTTP adapters only. Matching, ranking and index lifecycle live in ``discovery/search``.
"""

from __future__ import annotations

import threading
import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import get_librarian
from discovery import store as discovery_store
from discovery.identity import IdentityJob, load_identities
from discovery.library_snapshot import build_library_snapshot
from discovery.search.artist_page import artist_page, json_sections, section_events
from discovery.search.events import search_events, sse
from discovery.search.index import OwnedIndex, fetch_song_inventory
from discovery.search.network import artist_network, external_search
from discovery.search.normalize import normalize_key, normalize_query
from discovery.search.query import SEARCH_TYPES
from settings.service import lastfm_generation, navidrome_generation

router = APIRouter()

_owned_index: OwnedIndex | None = None
_owned_index_lock = threading.Lock()


def _snapshot_lists(librarian, generation):
    """Artists and albums from the library snapshot, keyed by Navidrome generation (section 5.2)."""
    suffix = f":navidrome{generation}"

    def read(name):
        return librarian._discovery_read_list(name + suffix)

    def write(name, payload):
        librarian._discovery_write_list(name + suffix, payload)

    snapshot = build_library_snapshot(librarian.api_call, librarian.items, read, write)
    return snapshot["artists"], snapshot["albums"]


_identity_job = IdentityJob()


def _identity_pass(librarian, data):
    """One background pass that stores MBIDs for artists and albums that do not have one yet.

    A pass for a generation that is no longer current does nothing, so it cannot delete the
    records of the current generation or store records under an old one.
    """
    import httpx

    from discovery.identity import purge_stale_identities, resolve_identities
    from discovery.search.network import LIMITER
    from discovery.search.providers import MusicBrainzSearch

    if data.generation != navidrome_generation(librarian._discovery_settings_read):
        return {"artists": 0, "albums": 0, "unresolved": 0}
    purge_stale_identities(
        lambda prefix, keep: discovery_store.delete_prefix_except(librarian.DISCOVERY_DB, prefix, keep),
        data.generation,
    )
    # A background pass can wait longer than a search request, and a timed-out batch is simply retried.
    musicbrainz = MusicBrainzSearch(get=httpx.get, limiter=LIMITER, pause=time.sleep, request_timeout=30.0)

    def navidrome_mbid(artist_id):
        artist = librarian.api_call("getArtist", id=artist_id).get("artist", {})
        return artist.get("musicBrainzId") or None

    return resolve_identities(
        data,
        navidrome_mbid=navidrome_mbid,
        musicbrainz=musicbrainz,
        read_prefix=lambda prefix: discovery_store.read_prefix(librarian.DISCOVERY_DB, prefix),
        write_many=lambda lists: discovery_store.write_many(librarian.DISCOVERY_DB, lists),
        remaining=lambda: 3600.0,
        cancelled=threading.Event(),
    )


class IdentityCorrection(BaseModel):
    """An MBID chosen by the owner. ``null`` marks the item as having no MBID."""

    mbid: str | None = None


def _refresh_identities(generation) -> None:
    """Rebuild the owned index for this generation so a correction reaches results."""
    if _owned_index is not None:
        _owned_index.refresh(generation)


@router.put("/api/identities/{kind}/{item_id}")
def correct_identity(kind: str, item_id: str, body: IdentityCorrection, librarian=Depends(get_librarian)):
    """Store the owner's MBID for one artist (``kind=artist``) or album (``kind=album``).

    For an album the MBID is the release-group MBID. A stored correction is never replaced by the
    identity pass; delete the record to let the pass resolve the item again.
    """
    from discovery.identity import MBID_PATTERN, KINDS, identity_name, record_for

    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="Unknown kind. Use artist or album.")
    if body.mbid is not None and not MBID_PATTERN.fullmatch(body.mbid):
        raise HTTPException(status_code=400, detail="mbid must be a lowercase MusicBrainz UUID or null.")
    view = owned_view(librarian)
    generation = navidrome_generation(librarian._discovery_settings_read)
    if view.data is None:
        # Corrections need the library to be indexed, so the ID can be checked against it.
        return JSONResponse(
            status_code=409,
            content={"code": "index_not_ready", "message": "The library index is not ready. Try again shortly."},
        )
    items = view.data.artists if kind == "artist" else view.data.albums
    if not any(item["id"] == item_id for item in items):
        raise HTTPException(status_code=404, detail="No library item has this ID.")
    discovery_store.write_many(librarian.DISCOVERY_DB, {
        identity_name(generation, kind, item_id): record_for(kind, body.mbid, "manual"),
    })
    _refresh_identities(generation)
    return {"kind": kind, "id": item_id, "mbid": body.mbid, "source": "manual"}


@router.delete("/api/identities/{kind}/{item_id}")
def reset_identity(kind: str, item_id: str, librarian=Depends(get_librarian)):
    """Delete the stored identity for one item, so the next identity pass resolves it again."""
    from discovery.identity import KINDS, identity_name

    if kind not in KINDS:
        raise HTTPException(status_code=404, detail="Unknown kind. Use artist or album.")
    generation = navidrome_generation(librarian._discovery_settings_read)
    removed = discovery_store.delete_list(librarian.DISCOVERY_DB, identity_name(generation, kind, item_id))
    _refresh_identities(generation)
    return {"kind": kind, "id": item_id, "removed": bool(removed)}


def owned_index_for(librarian) -> OwnedIndex:
    """Return the process-wide owned index, creating it on first use with the given service."""
    global _owned_index
    with _owned_index_lock:
        if _owned_index is None:
            def after_build(data):
                # New identities change owned results, so rebuild once when a pass stored any.
                _identity_job.start(
                    lambda: _identity_pass(librarian, data),
                    # refresh() does nothing when this pass's generation is no longer current.
                    on_changed=lambda: _owned_index and _owned_index.refresh(data.generation),
                )

            _owned_index = OwnedIndex(
                load_library=lambda: _snapshot_lists(
                    librarian, navidrome_generation(librarian._discovery_settings_read)
                ),
                load_songs=lambda: fetch_song_inventory(librarian.api_call, librarian.items),
                load_identities=lambda generation: load_identities(
                    lambda prefix: discovery_store.read_prefix(librarian.DISCOVERY_DB, prefix),
                    generation,
                ),
                after_build=after_build,
            )
        return _owned_index


def owned_view(librarian):
    """Trigger a background refresh if needed, then read the last known-good state."""
    index = owned_index_for(librarian)
    index.ensure(navidrome_generation(librarian._discovery_settings_read))
    return index.view()


def _wants_stream(request: Request) -> bool:
    return "text/event-stream" in request.headers.get("accept", "")


def _elapsed_ms(started: float) -> int:
    return int((time.monotonic() - started) * 1000)


def _parse_types(raw: str | None) -> list[str]:
    if raw is None:
        return list(SEARCH_TYPES)
    requested = [part.strip() for part in raw.split(",")]
    if not requested or any(part not in SEARCH_TYPES for part in requested):
        raise HTTPException(
            status_code=400,
            detail="types must be a comma list of artist, album, song or genre.",
        )
    return list(dict.fromkeys(requested))


def _parse_limit(raw: str | None) -> int:
    if raw is None:
        return 10
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if not 1 <= value <= 50:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 50.")
    return value


@router.get("/api/search")
def search(
    q: str | None = None,
    types: str | None = None,
    scope: str = "all",
    limit: str | None = None,
    librarian=Depends(get_librarian),
):
    raw_query = (q or "").strip()
    if not 1 <= len(raw_query) <= 200:
        raise HTTPException(status_code=400, detail="q must be 1 to 200 characters.")
    query = normalize_query(raw_query)
    if not query:
        raise HTTPException(status_code=400, detail="q must contain a letter or digit.")
    if scope not in ("owned", "all"):
        raise HTTPException(status_code=400, detail="scope must be owned or all.")
    requested_types = _parse_types(types)
    max_per_type = _parse_limit(limit)

    view = owned_view(librarian)
    started = time.monotonic()
    # scope=owned never reads or writes the provider cache and makes no network call (section 8.1).
    external = None
    if scope == "all":
        external = external_search(
            settings_read=librarian._discovery_settings_read,
            cache_read=librarian._discovery_read_list,
            cache_write=librarian._discovery_write_list,
            delete_except=lambda prefix, keep: discovery_store.delete_prefix_except(
                librarian.DISCOVERY_DB, prefix, keep
            ),
        )

    def stream():
        for name, payload in search_events(
            view,
            query=query,
            types=requested_types,
            limit=max_per_type,
            elapsed_ms=lambda: _elapsed_ms(started),
            external=external,
            started=started,
        ):
            yield sse(name, payload)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-store"},
    )


def artist_network_for(librarian):
    """Route adapter: ListenBrainz popularity and the existing bio service feed the artist page."""
    import httpx

    from app.api.metadata import artist_bio
    from integrations.listenbrainz.client import request_headers
    from discovery.search.providers import REQUEST_TIMEOUT
    from integrations.listenbrainz.popularity import fetch_release_group_popularity

    def popularity(mbids, can_cache):
        def cache_set(key, value):
            # A response that arrives after the artist-page deadline is not cached.
            if can_cache():
                librarian._metadata_cache_set(key, value)

        return fetch_release_group_popularity(
            httpx.post,
            librarian._metadata_cache_get,
            cache_set,
            mbids,
            headers=request_headers(),
            timeout=REQUEST_TIMEOUT,
        )

    def bio(name):
        return artist_bio(artist=name)["bio"]

    def navidrome_mbid(artist_id):
        # One read-only Navidrome call per artist page; the library tags MBIDs on many artists.
        artist = librarian.api_call("getArtist", id=artist_id).get("artist", {})
        return artist.get("musicBrainzId") or None

    settings = librarian._discovery_settings_read()
    return artist_network(
        cache_read=librarian._discovery_read_list,
        cache_write=librarian._discovery_write_list,
        popularity=popularity,
        bio=bio,
        navidrome_mbid=navidrome_mbid,
        lastfm_api_key=str(settings.get("lastfm_api_key") or "").strip(),
        lastfm_gen=lastfm_generation(librarian._discovery_settings_read),
    )


@router.get("/api/artists/{key}")
def artist(
    key: str,
    request: Request,
    id: str | None = None,
    mbid: str | None = None,
    librarian=Depends(get_librarian),
):
    """Artist page. ``mbid`` is accepted for provider lookups; it never selects the owned artist."""
    started = time.monotonic()
    try:
        page = artist_page(
            owned_view(librarian),
            normalize_key(key),
            id,
            network=artist_network_for(librarian),
        )
    except Exception:
        return JSONResponse(
            status_code=502,
            content={"code": "artist_failed", "message": "Owned index read failed."},
        )

    if page.status == "unknown":
        return JSONResponse(
            status_code=404,
            content={"code": "unknown_artist", "message": "No artist matches this key."},
        )
    if page.status == "ambiguous":
        return JSONResponse(
            status_code=409,
            content={
                "code": "ambiguous_artist",
                "message": "More than one artist has this key. Pass the artist ID.",
                "candidates": page.candidates,
            },
        )

    done = {
        "elapsed_ms": _elapsed_ms(started),
        "deadline_hit": False,
        "partial": page.partial,
    }
    if _wants_stream(request):
        def stream():
            yield sse("capabilities", page.capabilities)
            for section in section_events(page):
                yield sse("section", section)
            yield sse("done", done)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store"},
        )
    return {
        "capabilities": page.capabilities,
        "sections": json_sections(page),
        "done": done,
    }
