"""External metadata API routes and provider/cache helpers.

These endpoints enrich the UI with optional artist biographies, artwork, album
details, and release years. Provider failures remain non-fatal except for
invalid request parameters; discovery itself does not depend on metadata.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.artist_bio import resolve_artist_bio
from app.services.deezer_tracklist import shape_tracklist
from app.services.deezer_artwork import select_album_artwork, select_artist_artwork
from app.services.deezer_album_details import shape_album_match
from app.services import album_links
from app.services.apple_description import parse_editorial_notes
from app.services.deezer_album_matching import exact_album_matches, exact_album_release_year, release_year
from integrations.musicbrainz.album_year import (
    lookup_album_year as _lookup_musicbrainz_album_year,
    lookup_album_years as _lookup_musicbrainz_album_years,
    year_cache as _musicbrainz_year_cache,
)

router = APIRouter()

_EXTERNAL_HTTP = httpx.Client(
    timeout=httpx.Timeout(3.0, connect=1.5),
    # httpx closes idle connections after 5 s, so a burst of lookups after a short pause paid a
    # fresh TCP and TLS handshake each. Keep them open for a minute.
    limits=httpx.Limits(keepalive_expiry=60.0),
    # Wikimedia answers 403 ("robot policy") to this User-Agent when the request carries httpx's
    # default `Accept: */*`, so every artist bio came back empty. A JSON Accept header fixes it.
    headers={
        "User-Agent": "NavidromeLibrarian/1.0 (personal music discovery; contact: local app)",
        "Accept": "application/json",
    },
)

# Artist biographies are cached for a day. Wikidata identifies the intended
# musical entity first; Wikipedia is only used when its page points back to
# that exact Wikidata item. This prevents name collisions (e.g. Rainbow the band
# versus the optical phenomenon) from producing unrelated summaries.
_ARTIST_BIO_CACHE_TTL = 24 * 60 * 60
_artist_bio_cache = {}

@router.get("/api/artist-bio")
def artist_bio(artist: str):
    name = str(artist or "").strip()
    if not name or len(name) > 180:
        raise HTTPException(status_code=400, detail="A valid artist name is required.")
    key = name.casefold()
    now = monotonic()
    cached = _artist_bio_cache.get(key)
    if cached and now - cached["time"] < _ARTIST_BIO_CACHE_TTL:
        return {"artist": name, "bio": cached["bio"]}

    bio = ""
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "uselang": "en",
        "format": "json",
        "limit": 10,
    }
    summary_url = (
        "https://en.wikipedia.org/api/rest_v1/page/summary/"
        + __import__("urllib.parse", fromlist=["quote"]).quote(name.replace(" ", "_"), safe="")
    )

    # Start both network requests together. The summary is used only after its
    # Wikidata identity is checked, so the faster path doesn't reintroduce
    # wrong-name biographies such as Rainbow the optical phenomenon.
    with ThreadPoolExecutor(max_workers=2) as pool:
        search_future = pool.submit(
            _EXTERNAL_HTTP.get, "https://www.wikidata.org/w/api.php", params=params
        )
        summary_future = pool.submit(_EXTERNAL_HTTP.get, summary_url)
        entities = []
        page = {}
        search_ok = False
        try:
            search_response = search_future.result()
            search_response.raise_for_status()
            entities = search_response.json().get("search", [])
            search_ok = True
        except Exception:
            pass
        try:
            summary_response = summary_future.result()
            if summary_response.status_code == 200:
                page = summary_response.json()
        except Exception:
            pass

    bio = resolve_artist_bio(name, entities, page)

    # A failed Wikidata lookup is not "this artist has no bio": do not cache it for a day.
    if search_ok:
        _artist_bio_cache[key] = {"time": monotonic(), "bio": bio}
    return {"artist": name, "bio": bio}


# Artwork is optional presentation metadata; discovery works without it.
_ARTWORK_CACHE_TTL = 6 * 60 * 60
_ARTWORK_NEGATIVE_CACHE_TTL = 5 * 60
_artwork_cache = {}


def _musicbrainz_album_year(artist: str, album: str):
    """Compatibility adapter for the directly testable MusicBrainz lookup."""
    return _lookup_musicbrainz_album_year(artist, album)


class AlbumYearItem(BaseModel):
    artist: str = Field(max_length=180)
    album: str = Field(max_length=180)


class AlbumYearsRequest(BaseModel):
    items: list[AlbumYearItem] = Field(max_length=60)


@router.post("/api/album-years")
def album_years(body: AlbumYearsRequest):
    """Years for many albums with few catalog requests (MusicBrainz exact matches only).

    Each result is {"artist", "album", "year"}; an album with no exact match has year null, and an
    album whose catalog request failed is left out so the page can ask again later.
    """
    pairs = [(item.artist.strip(), item.album.strip()) for item in body.items]
    years = _lookup_musicbrainz_album_years(pairs)
    return {"years": [
        {"artist": artist, "album": album, "year": year}
        for (artist, album), year in years.items()
    ]}


@router.get("/api/album-year")
def album_year(artist: str = "", album: str = ""):
    """Return a year only when an authoritative catalog has an exact album match."""
    artist = str(artist or "").strip()[:180]
    album = str(album or "").strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")

    year = _musicbrainz_album_year(artist, album)
    source = "MusicBrainz" if year else None

    # MusicBrainz is primary. Deezer is a fallback only for an exact normalized
    # artist AND album match; fuzzy or artist-only results are never trusted.
    if not year:
        try:
            query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 20})
            response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/album?" + query)
            response.raise_for_status()
            matched_year = exact_album_release_year(
                response.json().get("data") or [], artist, album
            )
            if matched_year is not None:
                year = matched_year
                source = "Deezer"
        except Exception:
            pass

    return {"artist": artist, "album": album, "year": year, "source": source}


@router.get("/api/album-details")
def album_details(artist: str = "", album: str = ""):
    """Return a carefully matched Deezer album and its tracklist for the card popup."""
    artist = str(artist or "").strip()[:180]
    album = str(album or "").strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")

    result = {"artist": artist, "album": album, "year": None, "artwork_url": None, "tracks": []}
    try:
        query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 12})
        response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/album?" + query)
        response.raise_for_status()
        albums = response.json().get("data") or []
        exact = exact_album_matches(albums, artist, album)
        if not exact:
            result["message"] = "No exact catalog match was found, so the tracklist is unavailable."
            return result

        match = exact[0]
        result.update(shape_album_match(match))
        album_id = match.get("id")
        if not album_id:
            result["message"] = "Album artwork found, but the catalog did not provide a tracklist ID."
            return result

        detail_response = _EXTERNAL_HTTP.get(f"https://api.deezer.com/album/{album_id}")
        detail_response.raise_for_status()
        details = detail_response.json()
        result["tracks"] = shape_tracklist(
            details.get("tracks", {}).get("data") or []
        )
        if not result["tracks"]:
            result["message"] = "The album was found, but its tracklist is unavailable."
        return result
    except Exception:
        result["message"] = "The album catalog is temporarily unavailable."
        return result


_artist_image_cache = {}
_album_links_cache = {}
_ALBUM_LINKS_TTL = 24 * 60 * 60


def _json_or_none(url, **kwargs):
    """A JSON answer from a music service, or None when it fails. Links are best effort."""
    try:
        response = _EXTERNAL_HTTP.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


_apple_url_cache = {}


def _apple_album_url(artist: str, album: str):
    """The exactly matching Apple Music album page for an artist and album, or None.

    The album page asks twice (for its links and for its description), so a found page is kept for an hour.
    """
    key = (artist.casefold(), album.casefold())
    cached = _apple_url_cache.get(key)
    if cached and monotonic() - cached[0] < 3600:
        return cached[1]
    data = _json_or_none("https://itunes.apple.com/search", params={
        "term": f"{artist} {album}", "entity": "album", "limit": 10})
    url = album_links.apple_music_url((data or {}).get("results") or [], artist, album)
    if url:
        _apple_url_cache[key] = (monotonic(), url)
    return url


_album_description_cache = {}
_DESCRIPTION_TTL = 7 * 24 * 60 * 60
_DESCRIPTION_MISS_TTL = 24 * 60 * 60
_APPLE_PAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html",
}


def album_description(artist: str, album: str) -> dict:
    """Apple Music's editorial notes for an album: ``{"paragraphs", "source", "url"}`` or an empty result.

    Only an exactly matching Apple Music page is read, and only albums Apple has written notes for
    have any. A failed fetch is not cached, so the next visit retries.
    """
    key = (artist.casefold(), album.casefold())
    cached = _album_description_cache.get(key)
    if cached:
        ttl = _DESCRIPTION_TTL if cached["value"]["paragraphs"] else _DESCRIPTION_MISS_TTL
        if monotonic() - cached["time"] < ttl:
            return cached["value"]
    empty = {"paragraphs": [], "source": "Apple Music", "url": None}
    url = _apple_album_url(artist, album)
    if not url:
        return empty
    try:
        response = _EXTERNAL_HTTP.get(url, headers=_APPLE_PAGE_HEADERS, follow_redirects=True, timeout=6.0)
        response.raise_for_status()
    except Exception:
        return empty
    paragraphs = parse_editorial_notes(response.text) or []
    value = {"paragraphs": paragraphs, "source": "Apple Music", "url": url}
    _album_description_cache[key] = {"time": monotonic(), "value": value}
    return value


@router.get("/api/album-description")
def album_description_route(artist: str = "", album: str = ""):
    artist, album = artist.strip()[:180], album.strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    return album_description(artist, album)


@router.get("/api/album-links")
def album_page_links(artist: str = "", album: str = "", mbid: str = ""):
    """The album's own page on each music service that could be matched exactly.

    A service that is missing from the answer had no exact match (or did not answer); the page keeps
    its search link for that service.
    """
    artist, album, mbid = artist.strip()[:180], album.strip()[:180], mbid.strip()[:40]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    key = (artist.casefold(), album.casefold(), mbid)
    cached = _album_links_cache.get(key)
    if cached and monotonic() - cached["time"] < _ALBUM_LINKS_TTL:
        return cached["links"]

    def apple():
        return _apple_album_url(artist, album)

    def deezer():
        data = _json_or_none("https://api.deezer.com/search/album?" + urlencode(
            {"q": f'artist:"{artist}" album:"{album}"', "limit": 12}))
        return album_links.deezer_url((data or {}).get("data") or [], artist, album)

    def musicbrainz():
        if mbid:
            return mbid
        import threading

        from discovery.search.network import LIMITER
        from discovery.search.providers import MusicBrainzSearch

        deadline = monotonic() + 4.0
        try:
            groups = MusicBrainzSearch(get=_EXTERNAL_HTTP.get, limiter=LIMITER).release_groups_named(
                artist, album, remaining=lambda: deadline - monotonic(), cancelled=threading.Event())
        except Exception:
            return None
        return album_links.musicbrainz_group_id(groups, artist, album)

    with ThreadPoolExecutor(max_workers=3) as pool:
        apple_future, deezer_future, mb_future = pool.submit(apple), pool.submit(deezer), pool.submit(musicbrainz)
        apple_url, deezer_page, group_id = apple_future.result(), deezer_future.result(), mb_future.result()

    links = {}
    if apple_url:
        links["apple_music"] = apple_url
    if deezer_page:
        links["deezer"] = deezer_page
    if group_id:
        links["musicbrainz"] = f"https://musicbrainz.org/release-group/{group_id}"
        links["listenbrainz"] = f"https://listenbrainz.org/album/{group_id}"
    # A missing service may only have been slow or busy, so an incomplete answer is kept for minutes, not a day.
    complete = "musicbrainz" in links and "apple_music" in links and "deezer" in links
    _album_links_cache[key] = {"time": monotonic() - (0 if complete else _ALBUM_LINKS_TTL - 10 * 60), "links": links}
    return links


@router.get("/api/artist-image")
def artist_image(name: str = ""):
    """A larger photo for an artist page hero, from Deezer. Empty ``artwork_url`` when none matches."""
    name = name.strip()[:180]
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    cached = _artist_image_cache.get(name.casefold())
    if cached and monotonic() - cached["time"] < _ARTWORK_CACHE_TTL:
        return cached["data"]
    result = {"artwork_url": None, "image_kind": "artist", "source": "Deezer"}
    try:
        response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/artist?" + urlencode({"q": name, "limit": 8}))
        response.raise_for_status()
        match = select_artist_artwork(response.json().get("data") or [], name)
        if match is not None:
            photo = next(
                (item.get("picture_xl") for item in response.json().get("data") or []
                 if str(item.get("name") or "").casefold() == name.casefold() and item.get("picture_xl")),
                None,
            )
            result = {**match, "artwork_url": (photo or match["artwork_url"]).replace("http://", "https://", 1)}
    except Exception:
        # A provider outage is not cached, so the next visit retries.
        return {**result, "retryable": True}
    _artist_image_cache[name.casefold()] = {"time": monotonic(), "data": result}
    return result


@router.get("/api/artwork")
def album_artwork(artist: str = "", album: str = ""):
    artist = artist.strip()[:180]
    album = album.strip()[:180]
    if not artist and not album:
        raise HTTPException(status_code=400, detail="artist or album is required")

    key = (artist.casefold(), album.casefold())
    now = monotonic()
    cached = _artwork_cache.get(key)
    if cached:
        ttl = _ARTWORK_CACHE_TTL if cached["data"].get("artwork_url") else _ARTWORK_NEGATIVE_CACHE_TTL
        if now - cached["time"] < ttl:
            return cached["data"]

    result = {"artwork_url": None, "image_kind": "album", "source": "Deezer"}
    lookup_failed = False
    try:
        if artist and album:
            query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 8})
        else:
            query = urlencode({"q": artist or album, "limit": 8})
        endpoint = "https://api.deezer.com/search/album?" + query
        response = _EXTERNAL_HTTP.get(endpoint)
        response.raise_for_status()
        payload = response.json()
        albums = payload.get("data") or []

        if albums:
            selected_artwork = select_album_artwork(albums, artist, album)
            if selected_artwork is not None:
                result = selected_artwork

        # Do not perform a serialized MusicBrainz lookup here: it rate-limits
        # requests and can delay artwork by several seconds. Deezer release dates
        # are shown when available; missing years must never delay the cover.
        # If the album is not in the catalog, use a matching artist photo instead.
        if not result["artwork_url"] and artist:
            artist_query = urlencode({"q": artist, "limit": 8})
            response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/artist?" + artist_query)
            response.raise_for_status()
            artist_payload = response.json()
            artists = artist_payload.get("data") or []
            selected_artist_artwork = select_artist_artwork(
                artists, artist, year=result.get("year")
            )
            if selected_artist_artwork is not None:
                result = selected_artist_artwork
    except Exception:
        # A provider outage must not poison the negative cache for five minutes.
        # Tell the browser this result is transient so it can retry with backoff.
        lookup_failed = True
        result["retryable"] = True

    if not lookup_failed:
        _artwork_cache[key] = {"time": monotonic(), "data": result}
    return result


