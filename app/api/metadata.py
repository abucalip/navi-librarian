"""External metadata API routes and provider/cache helpers.

These endpoints enrich the UI with optional artist biographies, artwork, album
details, and release years. Provider failures remain non-fatal except for
invalid request parameters; discovery itself does not depend on metadata.
"""
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, wait
from time import monotonic
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_librarian
from app.services.artist_bio import resolve_artist_bio
from app.services.deezer_tracklist import shape_tracklist
from app.services.deezer_artwork import select_album_artwork, select_artist_artwork
from app.services.deezer_album_details import shape_album_match
from app.services import album_links, album_reviews, album_wikipedia, persistent_metadata
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

def _navidrome_artist_bio(librarian, name):
    """The library's own biography for an artist, or "" when Navidrome has none.

    Read-only and local: the artist id comes from the cached library snapshot and Navidrome
    answers from its own agent cache, so no public-web request is made. Any failure is a miss.
    """
    try:
        from app.api.search import clean_navidrome_bio

        wanted = librarian._music_key(name)
        match = next((a for a in librarian._discovery_library_snapshot()["artists"]
                      if a.get("id") and librarian._music_key(a.get("name", "")) == wanted), None)
        if match is None:
            return ""
        info = librarian.api_call("getArtistInfo2", id=match["id"]).get("artistInfo2", {})
        return clean_navidrome_bio(info.get("biography")) or ""
    except Exception:
        return ""


@router.get("/api/artist-bio")
def artist_bio_route(artist: str, librarian=Depends(get_librarian)):
    """Cache first, then Navidrome's biography for a library artist, then Wikipedia."""
    name = str(artist or "").strip()
    if name and len(name) <= 180:
        key = name.casefold()
        cached = _artist_bio_cache.get(key)
        if not (cached and monotonic() - cached["time"] < _ARTIST_BIO_CACHE_TTL):
            bio = _navidrome_artist_bio(librarian, name)
            if bio:
                _artist_bio_cache[key] = {"time": monotonic(), "bio": bio}
    return artist_bio(artist)


def artist_bio(artist: str):
    name = str(artist or "").strip()
    if not name or len(name) > 180:
        raise HTTPException(status_code=400, detail="A valid artist name is required.")
    key = name.casefold()
    now = monotonic()
    cached = _artist_bio_cache.get(key)
    if cached and now - cached["time"] < _ARTIST_BIO_CACHE_TTL:
        return {"artist": name, "bio": cached["bio"]}
    stored = persistent_metadata.read("artist-bio:v1:" + key)
    if stored:
        _artist_bio_cache[key] = {"time": monotonic(), "bio": stored}
        return {"artist": name, "bio": stored}

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
        if bio:
            persistent_metadata.write("artist-bio:v1:" + key, bio)
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


# A found release year does not change, so it is kept in the app's persistent metadata cache and
# survives restarts (the in-memory catalog cache does not). Only found years are stored: an album
# with no match may be matched later. `librarian` is the route dependency; called without it
# (direct calls, tests) the store is simply skipped.
_YEAR_STORE_TTL = 365 * 24 * 60 * 60


def _year_store_key(artist, album):
    from integrations.musicbrainz.album_year import _norm

    return "album-year:v1:" + _norm(artist) + ":" + _norm(album)


def _stored_year(librarian, artist, album):
    # The artist page calls without a librarian; the attached store serves that case.
    reader = getattr(librarian, "_metadata_cache_get", None) or persistent_metadata.read
    try:
        value = reader(_year_store_key(artist, album), _YEAR_STORE_TTL)
        return int(value) if value else None
    except Exception:
        return None


def _store_year(librarian, artist, album, year):
    writer = getattr(librarian, "_metadata_cache_set", None) or persistent_metadata.write
    if not year:
        return
    try:
        writer(_year_store_key(artist, album), int(year))
    except Exception:
        pass


@router.post("/api/album-years")
def album_years(body: AlbumYearsRequest, librarian=Depends(get_librarian)):
    """Years for many albums with few catalog requests (MusicBrainz exact matches only).

    Each result is {"artist", "album", "year"}; an album with no exact match has year null, and an
    album whose catalog request failed is left out so the page can ask again later.
    """
    pairs = [(item.artist.strip(), item.album.strip()) for item in body.items]
    stored = {pair: _stored_year(librarian, *pair) for pair in pairs}
    years = {pair: year for pair, year in stored.items() if year}
    missing = [pair for pair in pairs if pair not in years]
    if missing:
        found = _lookup_musicbrainz_album_years(missing)
        for pair, year in found.items():
            _store_year(librarian, pair[0], pair[1], year)
        years.update(found)
    return {"years": [
        {"artist": artist, "album": album, "year": year}
        for (artist, album), year in years.items()
    ]}


@router.get("/api/album-year")
def album_year(artist: str = "", album: str = "", librarian=Depends(get_librarian)):
    """Return a year only when an authoritative catalog has an exact album match."""
    artist = str(artist or "").strip()[:180]
    album = str(album or "").strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")

    stored = _stored_year(librarian, artist, album)
    if stored:
        return {"artist": artist, "album": album, "year": stored, "source": "cache"}

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

    _store_year(librarian, artist, album, year)
    return {"artist": artist, "album": album, "year": year, "source": source}


_album_details_cache = {}
_DETAILS_MISS_TTL = 60 * 60


@router.get("/api/album-details")
def album_details(artist: str = "", album: str = ""):
    """Return a carefully matched Deezer album and its tracklist for the card popup.

    A complete answer (with a tracklist) is kept for a month, in memory and on disk; an album the
    catalog definitely does not have is remembered for an hour. A provider failure is not cached.
    """
    artist = str(artist or "").strip()[:180]
    album = str(album or "").strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")

    key = (artist.casefold(), album.casefold())
    cached = _album_details_cache.get(key)
    if cached and monotonic() < cached[0]:
        return cached[1]
    store_key = "album-details:v1:" + key[0] + ":" + key[1]
    stored = persistent_metadata.read(store_key)
    if stored:
        _album_details_cache[key] = (monotonic() + _ARTWORK_CACHE_TTL, stored)
        return stored

    result, definitive_miss = _fetch_album_details(artist, album)
    if result["tracks"]:
        _album_details_cache[key] = (monotonic() + _ARTWORK_CACHE_TTL, result)
        persistent_metadata.write(store_key, result)
    elif definitive_miss:
        _album_details_cache[key] = (monotonic() + _DETAILS_MISS_TTL, result)
    return result


def _fetch_album_details(artist, album):
    """The Deezer answer and whether an empty one is final (no exact catalog match)."""
    result = {"artist": artist, "album": album, "year": None, "artwork_url": None, "tracks": []}
    try:
        query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 12})
        response = _EXTERNAL_HTTP.get("https://api.deezer.com/search/album?" + query)
        response.raise_for_status()
        albums = response.json().get("data") or []
        exact = exact_album_matches(albums, artist, album)
        if not exact:
            result["message"] = "No exact catalog match was found, so the tracklist is unavailable."
            return result, True

        match = exact[0]
        result.update(shape_album_match(match))
        album_id = match.get("id")
        if not album_id:
            result["message"] = "Album artwork found, but the catalog did not provide a tracklist ID."
            return result, False

        detail_response = _EXTERNAL_HTTP.get(f"https://api.deezer.com/album/{album_id}")
        detail_response.raise_for_status()
        details = detail_response.json()
        result["tracks"] = shape_tracklist(
            details.get("tracks", {}).get("data") or []
        )
        if not result["tracks"]:
            result["message"] = "The album was found, but its tracklist is unavailable."
        return result, False
    except Exception:
        result["message"] = "The album catalog is temporarily unavailable."
        return result, False


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
    store_key = "apple-album-url:v1:" + key[0] + ":" + key[1]
    stored = persistent_metadata.read(store_key, persistent_metadata.LINKS_TTL)
    if stored:
        _apple_url_cache[key] = (monotonic(), stored)
        return stored
    data = _json_or_none("https://itunes.apple.com/search", params={
        "term": f"{artist} {album}", "entity": "album", "limit": 10})
    url = album_links.apple_music_url((data or {}).get("results") or [], artist, album)
    if url:
        _apple_url_cache[key] = (monotonic(), url)
        persistent_metadata.write(store_key, url)
    return url


_album_description_cache = {}
_DESCRIPTION_TTL = 7 * 24 * 60 * 60
_DESCRIPTION_MISS_TTL = 24 * 60 * 60
_APPLE_PAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html",
}


def _apple_description(artist: str, album: str):
    """Apple Music's notes as ``({"paragraphs", "source", "url"}, answered)``.

    Only an exactly matching Apple Music page is read, and only albums Apple has written notes for
    have any. ``answered`` is False when a fetch failed, so the caller does not remember the miss.
    """
    empty = {"paragraphs": [], "source": "Apple Music", "url": None}
    url = _apple_album_url(artist, album)
    if not url:
        return empty, True
    try:
        response = _EXTERNAL_HTTP.get(url, headers=_APPLE_PAGE_HEADERS, follow_redirects=True, timeout=6.0)
        response.raise_for_status()
    except Exception:
        return empty, False
    return {"paragraphs": parse_editorial_notes(response.text) or [], "source": "Apple Music", "url": url}, True


def _wikipedia_description(artist: str, album: str):
    """The album's Wikipedia lead as ``(description or None, answered)``."""
    try:
        search = _EXTERNAL_HTTP.get("https://en.wikipedia.org/w/rest.php/v1/search/page", params={
            "q": f"{album_reviews.search_text(artist, album)} album", "limit": 5})
        search.raise_for_status()
        key = album_wikipedia.pick_album_article(search.json().get("pages"), artist, album)
        if not key:
            return None, True
        summary = _EXTERNAL_HTTP.get("https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(key, safe=""))
        summary.raise_for_status()
        return album_wikipedia.description_from_summary(summary.json()), True
    except Exception:
        return None, False


def album_description(artist: str, album: str) -> dict:
    """The album's description: Apple Music's editorial notes, else its Wikipedia lead, else empty.

    The answer is ``{"paragraphs", "source", "url"}`` (Wikipedia adds ``license``). A failed fetch is
    not cached, so the next visit retries.
    """
    key = (artist.casefold(), album.casefold())
    cached = _album_description_cache.get(key)
    if cached:
        ttl = _DESCRIPTION_TTL if cached["value"]["paragraphs"] else _DESCRIPTION_MISS_TTL
        if monotonic() - cached["time"] < ttl:
            return cached["value"]
    store_key = "album-description:v1:" + key[0] + ":" + key[1]
    stored = persistent_metadata.read(store_key)
    if stored and stored.get("paragraphs"):
        _album_description_cache[key] = {"time": monotonic(), "value": stored}
        return stored
    value, apple_answered = _apple_description(artist, album)
    wikipedia_answered = True
    if not value["paragraphs"]:
        wikipedia, wikipedia_answered = _wikipedia_description(artist, album)
        if wikipedia:
            value = wikipedia
    if value["paragraphs"]:
        persistent_metadata.write(store_key, value)
    if value["paragraphs"] or (apple_answered and wikipedia_answered):
        _album_description_cache[key] = {"time": monotonic(), "value": value}
    return value


@router.get("/api/album-description")
def album_description_route(artist: str = "", album: str = ""):
    artist, album = artist.strip()[:180], album.strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    return album_description(artist, album)


# Reviews: up to three outlets' own summary lines, each with a link to the full review. Every outlet
# is asked at once and the page waits only for a short deadline. A full set, or one where every
# outlet replied, is kept for a week; a partial one (an outlet failed or was slow) only for ten
# minutes, so a flaky outlet neither hides its review for long nor is asked again on every visit.
_REVIEWS_TTL = 7 * 24 * 60 * 60
_REVIEWS_PARTIAL_TTL = 10 * 60
_REVIEWS_DEADLINE = 6.0
_review_cache = {}
_REVIEW_PAGE_TIMEOUT = httpx.Timeout(4.0, connect=1.5)
_WORDPRESS_REVIEW_SITES = (
    ("PopMatters", "https://www.popmatters.com"),
    ("Consequence", "https://consequence.net"),
    ("The Quietus", "https://thequietus.com"),
    ("Treble", "https://www.treblezine.com"),
    ("Angry Metal Guy", "https://www.angrymetalguy.com"),
)
_review_pool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="album-reviews")


def _pitchfork_review(artist: str, album: str):
    response = _EXTERNAL_HTTP.get(
        "https://pitchfork.com/search/", params={"q": album_reviews.search_text(artist, album)},
        headers=_APPLE_PAGE_HEADERS, follow_redirects=True, timeout=_REVIEW_PAGE_TIMEOUT)
    response.raise_for_status()
    return album_reviews.pick_pitchfork(album_reviews.parse_pitchfork_search(response.text), artist, album)


def _guardian_get(api_key: str, path: str, **params):
    response = _EXTERNAL_HTTP.get(
        "https://content.guardianapis.com/" + path, params={**params, "api-key": api_key}, timeout=_REVIEW_PAGE_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _guardian_text(text: str) -> str:
    """Query text the Guardian accepts: it answers 400 to colons, brackets and similar inside a phrase."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w'\u2019 -]+", " ", text)).strip()


def _guardian_artist_tag(api_key: str, artist: str):
    """The Guardian's tag for an artist, remembered for a month once found.

    A collaboration ("Tony Allen & Hugh Masekela") has no tag of its own, so the first name is tried next.
    """
    store_key = "guardian-artist-tag:v1:" + artist.casefold()
    stored = persistent_metadata.read(store_key)
    if stored:
        return stored
    names = [artist] + [part for part in re.split(r"\s+(?:&|and|with|feat\.?|featuring|/)\s+|,\s*", artist)[:1] if part != artist]
    for name in names:
        query = _guardian_text(album_reviews.search_text(name, ""))
        tag = album_reviews.pick_guardian_tag(
            _guardian_get(api_key, "tags", q=query, type="keyword", **{"page-size": 5}), name) if query else None
        if tag:
            persistent_metadata.write(store_key, tag)
            return tag
    return None


def _guardian_review(artist: str, album: str):
    """The Guardian's album review: through the artist's tag when it has one, else by text search."""
    api_key = os.environ.get("GUARDIAN_API_KEY", "").strip()
    if not api_key:
        return None
    album_text = _guardian_text(album_reviews.search_text("", album))
    if not album_text:
        return None
    tag = _guardian_artist_tag(api_key, artist)
    if tag:
        query = {"tag": f"{tag},tone/albumreview", "q": f'"{album_text}"'}
    else:
        query = {"tag": "tone/albumreview", "q": f'"{_guardian_text(album_reviews.search_text(artist, ""))}" "{album_text}"'}
    payload = _guardian_get(api_key, "search", **query, **{"order-by": "relevance", "show-fields": "trailText", "page-size": 10})
    return album_reviews.pick_guardian(payload, artist, album)


def _wordpress_review(name: str, site: str, artist: str, album: str):
    search = _EXTERNAL_HTTP.get(
        site + "/wp-json/wp/v2/search", params={
            "search": album_reviews.search_text(artist, album), "subtype": "post", "per_page": 8},
        headers={**_APPLE_PAGE_HEADERS, "Accept": "application/json"}, follow_redirects=True,
        timeout=_REVIEW_PAGE_TIMEOUT)
    search.raise_for_status()
    url = album_reviews.pick_wordpress_post(search.json(), artist, album)
    if not url:
        return None
    page = _EXTERNAL_HTTP.get(url, headers=_APPLE_PAGE_HEADERS, follow_redirects=True, timeout=_REVIEW_PAGE_TIMEOUT)
    page.raise_for_status()
    return album_reviews.review(name, album_reviews.page_dek(page.text), url)


# Each outlet's answer is kept on its own: a review for a month, "nothing there" for three days, a failure
# not at all. A retry after a partial answer then asks only the outlets that failed, and an album the
# outlets never reviewed is not asked about again after a restart.
_SOURCE_FOUND_TTL = 30 * 24 * 60 * 60
_SOURCE_MISS_TTL = 3 * 24 * 60 * 60


def _outlet_review(name: str, artist: str, album: str, ask):
    """The outlet's review (or None) from its own stored answer, else ``ask()``; an exception is not stored."""
    store_key = f"album-review-source:v1:{name}:{artist.casefold()}:{album.casefold()}"
    stored = persistent_metadata.read(store_key, _SOURCE_FOUND_TTL)
    if isinstance(stored, dict) and "review" in stored and (
            stored["review"] or time.time() - float(stored.get("checked") or 0) < _SOURCE_MISS_TTL):
        return stored["review"]
    found = ask()
    persistent_metadata.write(store_key, {"review": found, "checked": time.time()})
    return found


def _review_sources(artist: str, album: str):
    """The source lookups in display order, each a no-argument callable returning a review or None.

    The Guardian is left out without a key, so a missing key is never stored as "no review".
    """
    asks = [("Pitchfork", lambda: _pitchfork_review(artist, album))]
    if os.environ.get("GUARDIAN_API_KEY", "").strip():
        asks.append(("The Guardian", lambda: _guardian_review(artist, album)))
    asks += [(name, lambda n=name, site=site: _wordpress_review(n, site, artist, album))
             for name, site in _WORDPRESS_REVIEW_SITES]
    return [lambda n=name, ask=ask: _outlet_review(n, artist, album, ask) for name, ask in asks]


def album_reviews_for(artist: str, album: str) -> dict:
    """``{"reviews": [{"source", "quote", "url"}, ...]}`` with at most three entries.

    ``retryable`` is added when an outlet failed or was too slow and fewer than three were found;
    the browser does not keep such an answer.
    """
    key = (artist.casefold(), album.casefold())
    cached = _review_cache.get(key)
    if cached and monotonic() - cached["time"] < cached["ttl"]:
        return cached["value"]
    store_key = "album-reviews:v1:" + key[0] + ":" + key[1]
    stored = persistent_metadata.read(store_key, _REVIEWS_TTL)
    if stored and stored.get("reviews"):
        _review_cache[key] = {"time": monotonic(), "ttl": 3600, "value": stored}
        return stored
    futures = [_review_pool.submit(source) for source in _review_sources(artist, album)]
    done, pending = wait(futures, timeout=_REVIEWS_DEADLINE)
    found, failed = [], bool(pending)
    for future in futures:
        if future not in done:
            future.cancel()
            found.append(None)
            continue
        try:
            found.append(future.result())
        except Exception:
            found.append(None)
            failed = True
    value = {"reviews": album_reviews.pick_reviews(found)}
    partial = failed and len(value["reviews"]) < album_reviews.MAX_REVIEWS
    if partial:
        value["retryable"] = True
    _review_cache[key] = {"time": monotonic(), "ttl": _REVIEWS_PARTIAL_TTL if partial else 3600, "value": value}
    if value["reviews"] and not partial:
        persistent_metadata.write(store_key, value)
    return value


@router.get("/api/album-reviews")
def album_reviews_route(artist: str = "", album: str = ""):
    artist, album = artist.strip()[:180], album.strip()[:180]
    if not artist or not album:
        raise HTTPException(status_code=400, detail="artist and album are required")
    return album_reviews_for(artist, album)


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
    store_key = "album-links:v1:" + "|".join(key)
    stored = persistent_metadata.read(store_key, persistent_metadata.LINKS_TTL)
    if stored:
        _album_links_cache[key] = {"time": monotonic(), "links": stored}
        return stored

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
    if complete:
        persistent_metadata.write(store_key, links)
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
    store_key = "artist-image:v1:" + name.casefold()
    stored = persistent_metadata.read(store_key)
    if stored and stored.get("artwork_url"):
        _artist_image_cache[name.casefold()] = {"time": monotonic(), "data": stored}
        return stored
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
    if result.get("artwork_url"):
        persistent_metadata.write(store_key, result)
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
    store_key = "album-artwork:v1:" + key[0] + ":" + key[1]
    stored = persistent_metadata.read(store_key)
    if stored and stored.get("artwork_url"):
        _artwork_cache[key] = {"time": monotonic(), "data": stored}
        return stored

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
        if result.get("artwork_url"):
            persistent_metadata.write(store_key, result)
    return result


