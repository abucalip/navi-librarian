"""Global search and artist routes (contract sections 3.1 and 3.3).

HTTP adapters only. Matching, ranking and index lifecycle live in ``discovery/search``.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.api.dependencies import get_librarian
from discovery import store as discovery_store
from discovery.identity import IdentityJob, load_identities
from discovery.library_snapshot import build_library_snapshot
from discovery.search.album_page import ALBUM_SECTION_ORDER, album_sections, find_album
from discovery.search.artist_page import artist_page, drain_deferred, json_sections, section_events
from discovery.search.events import NOT_IN_BUILD, search_events, sse
from discovery.search.index import STATE_FRESH, STATE_STALE, OwnedIndex, fetch_song_inventory
from discovery.search.merge import OwnedKeys
from discovery.search.genre_page import (
    SECTION_ORDER as GENRE_SECTION_ORDER,
    genre_capabilities,
    genre_sections,
    json_sections as genre_json_sections,
    normalize_tag,
)
from discovery.search.network import artist_network, external_search, genre_network
from discovery.search.similar_precompute import run_precompute
from discovery.search.normalize import normalize_key, normalize_query
from discovery.search.query import SEARCH_TYPES
from settings.service import discogs_generation, discogs_token_and_source, lastfm_generation, navidrome_generation

router = APIRouter()


def clean_navidrome_bio(raw) -> str | None:
    """Plain text from Navidrome's biography: tags dropped, the "Read more" link removed."""
    import html
    import re

    text = re.sub(r"<a\b[^>]*>.*?</a>", "", str(raw or ""), flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return re.sub(r"\s+", " ", text).strip() or None

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


def _cache_reader(librarian):
    """Reader for provider cache entries. The store wraps each entry as ``{"payload": entry, ...}``."""

    def read(name):
        stored = librarian._discovery_read_list(name)
        return stored.get("payload") if isinstance(stored, dict) else None

    return read


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

    def current_generation():
        return navidrome_generation(librarian._discovery_settings_read)

    idle = {"artists": 0, "albums": 0, "unresolved": 0}
    if data.generation != current_generation():
        return idle
    purge_stale_identities(
        lambda namespace, generation: discovery_store.delete_numbered_below(
            librarian.DISCOVERY_DB, namespace, generation
        ),
        current_generation,
    )
    # The generation may have changed while the cleanup ran. Writes under this pass's generation would
    # be stale, so stop here.
    if data.generation != current_generation():
        return idle
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
            cache_read=_cache_reader(librarian),
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


PRECOMPUTE_CHECK_SECONDS = 1800
logger = logging.getLogger(__name__)


PRECOMPUTE_CURSOR = "similar-precompute-cursor"


def _precompute_cursor(librarian) -> dict:
    """Where the last precompute pass stopped: ``{"next": position}`` in the owned artist list."""
    stored = librarian._discovery_read_list(PRECOMPUTE_CURSOR)
    payload = stored.get("payload") if isinstance(stored, dict) else None
    return payload if isinstance(payload, dict) else {}


def _precompute_once(librarian):
    """One precompute pass over the library, or None when the owned index is not usable yet."""
    view = owned_view(librarian)
    if view.data is None or view.state not in (STATE_FRESH, STATE_STALE):
        return None
    artists = list(view.data.artists)
    cursor = _precompute_cursor(librarian)
    return run_precompute(
        artists, artist_network_for(librarian), OwnedKeys(view.data),
        start=cursor.get("next", 0) if isinstance(cursor.get("next", 0), int) else 0,
        on_progress=lambda position: librarian._discovery_write_list(PRECOMPUTE_CURSOR, {"next": position}),
    )


def _precompute_step(librarian, last_day: str | None) -> str | None:
    """Run the day's precompute if it has not run yet; return the day that is now done.

    A day that is not usable yet (the owned index is still building) stays undone and is retried
    on the next check. A run that raises counts as done, so a broken run is not retried in a loop.
    """
    today = date.today().isoformat()
    if today == last_day:
        return last_day
    try:
        counts = _precompute_once(librarian)
    except Exception as exc:
        # Bounded diagnostics: the error type only, never provider details.
        logger.error("Similar-artist precompute failed (%s)", type(exc).__name__)
        return today
    if counts is None:
        return last_day
    logger.info("Similar-artist precompute finished: %s", counts)
    return today


def _precompute_loop(librarian) -> None:
    last_day = None
    while True:
        last_day = _precompute_step(librarian, last_day)
        time.sleep(PRECOMPUTE_CHECK_SECONDS)


def start_similar_precompute(librarian) -> threading.Thread:
    """Start the background loop that precomputes similar artists once per local day."""
    thread = threading.Thread(
        target=_precompute_loop, args=(librarian,), name="navidrome-similar-artists", daemon=True,
    )
    thread.start()
    return thread


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

    def deezer_tracks(artist, album):
        from app.api.metadata import album_details

        return album_details(artist=artist, album=album).get("tracks") or []

    def album_year(artist, album):
        from app.api.metadata import album_year as lookup

        return lookup(artist=artist, album=album).get("year")

    def album_description(artist, album):
        from app.api.metadata import album_description as lookup

        return lookup(artist, album)

    def navidrome_bio(artist_id):
        # Navidrome's own biography text, read-only. Its agents (Last.fm and others) fill it in.
        info = librarian.api_call("getArtistInfo2", id=artist_id).get("artistInfo2", {})
        return clean_navidrome_bio(info.get("biography"))

    settings = librarian._discovery_settings_read()
    return artist_network(
        cache_read=_cache_reader(librarian),
        cache_write=librarian._discovery_write_list,
        popularity=popularity,
        bio=bio,
        navidrome_mbid=navidrome_mbid,
        navidrome_bio=navidrome_bio,
        deezer_tracks=deezer_tracks,
        album_year=album_year,
        album_description=album_description,
        lastfm_api_key=str(settings.get("lastfm_api_key") or "").strip(),
        lastfm_gen=lastfm_generation(librarian._discovery_settings_read),
        discogs_token=discogs_token_and_source(librarian._discovery_settings_read, os.environ)[0],
        discogs_gen=discogs_generation(librarian._discovery_settings_read),
    )


@router.get("/api/artists/{key}")
def artist(
    key: str,
    request: Request,
    id: str | None = None,
    mbid: str | None = None,
    name: str | None = None,
    librarian=Depends(get_librarian),
):
    """Artist page. ``mbid`` is accepted for provider lookups; it never selects the owned artist.

    ``name`` lets a key the library does not have be served as an unowned artist page.
    """
    started = time.monotonic()
    try:
        view = owned_view(librarian)
        page = artist_page(
            view,
            normalize_key(key),
            id,
            network=artist_network_for(librarian),
            name=(name or "").strip()[:200] or None,
            mbid=mbid,
            defer_network=_wants_stream(request),
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
            # Owned sections go out at once; each network section follows as it finishes.
            for section in [page.sections[n] for n in ("artist", "owned_albums") if n in page.sections]:
                yield sse("section", section)
            if page.deferred is not None:
                for section in drain_deferred(page, view):
                    yield sse("section", section)
                for section in section_events(page):
                    if section["section"] not in ("artist", "owned_albums") and section["reason"] == NOT_IN_BUILD:
                        yield sse("section", section)
            else:
                for section in section_events(page)[2:]:
                    yield sse("section", section)
            yield sse("done", {**done, "elapsed_ms": _elapsed_ms(started), "partial": page.partial})

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


@router.get("/api/albums/{artist_key}/{album_key}")
def album(
    artist_key: str,
    album_key: str,
    request: Request,
    id: str | None = None,
    artist: str | None = None,
    name: str | None = None,
    year: int | None = None,
    mbid: str | None = None,
    librarian=Depends(get_librarian),
):
    """Album page: header, tracklist, similar artists and similar unowned albums.

    An album the library has is found by its keys (and ``id``). Any other album needs ``artist`` and
    ``name`` (and ``year`` and the release-group ``mbid`` when known), as an unowned search result carries.
    """
    started = time.monotonic()
    artist_key, album_key = normalize_key(artist_key), normalize_key(album_key)
    view = owned_view(librarian)
    data = view.data if view.state in (STATE_FRESH, STATE_STALE) else None
    owned_entry = find_album(data, artist_key, album_key, id) if data else None
    shown_artist, shown_name = (artist or "").strip()[:200], (name or "").strip()[:200]
    if owned_entry is None and not (shown_artist and shown_name):
        return JSONResponse(
            status_code=404,
            content={"code": "unknown_album", "message": "No album matches this key."},
        )
    network = artist_network_for(librarian)
    capabilities = {
        "sections": {section: {"available": True, "reason": None} for section in ALBUM_SECTION_ORDER},
        "sources": dict(network.sources),
        "owned_index": {"available": data is not None, "reason": view.reason, "state": view.state},
    }
    sections_iter = album_sections(
        network, data, album=owned_entry, artist=shown_artist, artist_key=artist_key,
        name=shown_name, year=year, release_group_mbid=mbid,
    )

    def finish(partial: bool) -> dict:
        return {"elapsed_ms": _elapsed_ms(started), "deadline_hit": partial, "partial": partial}

    if _wants_stream(request):
        def stream():
            yield sse("capabilities", capabilities)
            partial = False
            for section in sections_iter:
                partial = partial or section["reason"] in ("deadline", "source_failed")
                yield sse("section", section)
            yield sse("done", finish(partial))

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})
    collected = {section["section"]: section for section in sections_iter}
    sections = {}
    for section_name in ALBUM_SECTION_ORDER:
        entry = collected.get(section_name) or {
            "available": False, "complete": False, "reason": "deadline", "items": []}
        sections[section_name] = {k: v for k, v in entry.items() if k != "section"}
    partial = any(s["reason"] in ("deadline", "source_failed") for s in sections.values())
    return {"capabilities": capabilities, "sections": sections, "done": finish(partial)}


@router.get("/api/genres/{tag}")
def genre(tag: str, request: Request, librarian=Depends(get_librarian)):
    """Genre page (contract section 3.4): owned and unowned artists and albums for a tag."""
    normalized = normalize_tag(tag)
    if not normalized or len(normalized) > 100:
        raise HTTPException(status_code=400, detail="tag must be 1 to 100 characters.")
    started = time.monotonic()
    try:
        view = owned_view(librarian)
        network = genre_network(
            settings_read=librarian._discovery_settings_read,
            cache_read=_cache_reader(librarian),
            cache_write=librarian._discovery_write_list,
            delete_except=lambda prefix, keep: discovery_store.delete_prefix_except(
                librarian.DISCOVERY_DB, prefix, keep
            ),
        )
        sections, partial, deadline_hit = genre_sections(view, network, normalized)
        capabilities = genre_capabilities(view, network)
    except Exception:
        return JSONResponse(
            status_code=502,
            content={"code": "genre_failed", "message": "Genre page failed."},
        )
    done = {"elapsed_ms": _elapsed_ms(started), "deadline_hit": deadline_hit, "partial": partial}
    if _wants_stream(request):
        def stream():
            yield sse("capabilities", capabilities)
            for name in GENRE_SECTION_ORDER:
                yield sse("section", sections[name])
            yield sse("done", done)

        return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})
    return {"capabilities": capabilities, "sections": genre_json_sections(sections), "done": done}
