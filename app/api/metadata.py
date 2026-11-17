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
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_librarian
from app.services.artist_bio import resolve_artist_bio
from app.services.fallback_artwork import (
    parse_qobuz_albums, select_apple_artwork, select_qobuz_artwork,
)
from app.services.deezer_artwork import select_album_artwork, select_artist_artwork
from app.services import runtime_metrics
from app.services import album_links, album_page_sources, album_reviews, persistent_metadata, stale_refresh
from app.services.layered_cache import LayeredCache, Loaded
from app.services.deezer_album_matching import release_year
from integrations.musicbrainz.album_year import (
    lookup_album_year as _lookup_musicbrainz_album_year,
    lookup_album_years as _lookup_musicbrainz_album_years,
    year_cache as _musicbrainz_year_cache,
)

router = APIRouter()

_EXTERNAL_HTTP = runtime_metrics.MeteredClient(
    timeout=httpx.Timeout(3.0, connect=1.5),
    # httpx closes idle connections after 5 s, so a burst of lookups after a short pause paid a
    # fresh TCP and TLS handshake each. Keep them open for a minute.
    limits=httpx.Limits(keepalive_expiry=60.0),
    # The User-Agent and JSON Accept header (Wikimedia answers 403 without them) are shared with the worker's prefetch.
    headers=album_page_sources.EXTERNAL_HEADERS,
)

# Artist biographies are cached for a day. Wikidata identifies the intended
# musical entity first; Wikipedia is only used when its page points back to
# that exact Wikidata item. This prevents name collisions (e.g. Rainbow the band
# versus the optical phenomenon) from producing unrelated summaries.
_ARTIST_BIO_CACHE_TTL = 24 * 60 * 60
_artist_bio_cache = LayeredCache("artist-bio")

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
        if key not in _artist_bio_cache:
            bio = _navidrome_artist_bio(librarian, name)
            if bio:
                # Memory only: the library's own bio is not written to the persistent store.
                _artist_bio_cache.put(key, bio, _ARTIST_BIO_CACHE_TTL)
    return artist_bio(artist)


def artist_bio(artist: str):
    name = str(artist or "").strip()
    if not name or len(name) > 180:
        raise HTTPException(status_code=400, detail="A valid artist name is required.")
    key = name.casefold()
    bio = _artist_bio_cache.get_or_load(
        key, lambda: _load_artist_bio(name), store_key="artist-bio:v1:" + key,
        stored_ttl=_ARTIST_BIO_CACHE_TTL)
    return {"artist": name, "bio": bio}


def _load_artist_bio(name):
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
    if not search_ok:
        return Loaded(bio)
    return Loaded(bio, memory_ttl=_ARTIST_BIO_CACHE_TTL, persist=bool(bio))


# Artwork is optional presentation metadata; discovery works without it.
_ARTWORK_CACHE_TTL = 6 * 60 * 60
_ARTWORK_NEGATIVE_CACHE_TTL = 5 * 60
_artwork_cache = LayeredCache("album-artwork")


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
_YEAR_STORE_TTL = album_page_sources.YEAR_STORE_TTL
_year_store_key = album_page_sources.year_store_key


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
        year = album_page_sources.deezer_year(_EXTERNAL_HTTP.get, artist, album)
        if year is not None:
            source = "Deezer"

    _store_year(librarian, artist, album, year)
    return {"artist": artist, "album": album, "year": year, "source": source}


_album_details_cache = LayeredCache("album-details")


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

    def load():
        return album_page_sources.details_loaded(*_fetch_album_details(artist, album))

    return _album_details_cache.get_or_load(
        key, load, store_key=album_page_sources.details_store_key(artist, album), stored_ttl=_ARTWORK_CACHE_TTL)


def _fetch_album_details(artist, album):
    """The Deezer answer and whether an empty one is final (no exact catalog match)."""
    return album_page_sources.fetch_album_details(_EXTERNAL_HTTP.get, artist, album)


_artist_image_cache = LayeredCache("artist-image")
_album_links_cache = LayeredCache("album-links")
_ALBUM_LINKS_TTL = 24 * 60 * 60


def _json_or_none(url, **kwargs):
    """A JSON answer from a music service, or None when it fails. Links are best effort."""
    try:
        response = _EXTERNAL_HTTP.get(url, **kwargs)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


_apple_url_cache = LayeredCache("apple-album-url")
# Efficiency K2: a stored page or link set past its 7-day TTL is served while one background refresh
# runs, for at most ten times that TTL.
_LINKS_MAX_STALE = 10 * persistent_metadata.LINKS_TTL


def _apple_album_url(artist: str, album: str, allow_stale=False):
    """The exactly matching Apple Music album page for an artist and album, or None.

    The album page asks twice (for its links and for its description), so a found page is kept for an hour.
    """
    return _apple_album_url_state(artist, album, allow_stale)[0]


def _apple_album_url_state(artist: str, album: str, allow_stale=False):
    """``(url, stale)``; with `allow_stale` a stored page past its TTL is returned and refreshed in the background."""
    key = (artist.casefold(), album.casefold())

    def load():
        data = _json_or_none("https://itunes.apple.com/search", params={
            "term": f"{artist} {album}", "entity": "album", "limit": 10})
        url = album_links.apple_music_url((data or {}).get("results") or [], artist, album)
        # No page is not remembered: it may be a failed request as well as a real miss.
        return Loaded(url, memory_ttl=3600, persist=True) if url else Loaded(url)

    return _apple_url_cache.get_or_load_state(
        key, load, store_key="apple-album-url:v1:" + key[0] + ":" + key[1],
        store_ttl=persistent_metadata.LINKS_TTL, stored_ttl=3600,
        max_stale=_LINKS_MAX_STALE if allow_stale else None)


_album_description_cache = LayeredCache("album-description")
_APPLE_PAGE_HEADERS = album_page_sources.APPLE_PAGE_HEADERS


def _apple_description(artist: str, album: str):
    """Apple Music's notes as ``({"paragraphs", "source", "url"}, answered)``.

    Only an exactly matching Apple Music page is read, and only albums Apple has written notes for
    have any. ``answered`` is False when a fetch failed, so the caller does not remember the miss.
    """
    # A stale page address is fine here: the page itself is fetched now, and a failed fetch is not cached.
    url = _apple_album_url(artist, album, allow_stale=True)
    if not url:
        return dict(album_page_sources.EMPTY_DESCRIPTION), True
    return album_page_sources.apple_notes(_EXTERNAL_HTTP.get, artist, album, url)


def _wikipedia_description(artist: str, album: str):
    """The album's Wikipedia lead as ``(description or None, answered)``."""
    return album_page_sources.wikipedia_description(_EXTERNAL_HTTP.get, artist, album)


def album_description(artist: str, album: str) -> dict:
    """The album's description: Apple Music's editorial notes, else its Wikipedia lead, else empty.

    The answer is ``{"paragraphs", "source", "url"}`` (Wikipedia adds ``license``). A failed fetch is
    not cached, so the next visit retries.
    """
    key = (artist.casefold(), album.casefold())

    def load():
        return album_page_sources.load_description(
            lambda: _apple_description(artist, album), lambda: _wikipedia_description(artist, album))

    return _album_description_cache.get_or_load(
        key, load, store_key=album_page_sources.description_store_key(artist, album),
        accept_stored=lambda stored: bool(stored and stored.get("paragraphs")),
        stored_ttl=album_page_sources.DESCRIPTION_TTL)


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
# Efficiency K2 (owner decision 2026-11-17): a stored review list or outlet answer past its TTL is
# served for up to 70 days while one background refresh asks again.
_REVIEWS_MAX_STALE = 70 * 24 * 60 * 60
_REVIEWS_DEADLINE = 6.0
_review_cache = LayeredCache("album-reviews")
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


def _ask_outlet(store_key, ask):
    found = ask()
    persistent_metadata.write(store_key, {"review": found, "checked": time.time()})
    return found


def _outlet_answer_is_fresh(stored, age):
    if stored["review"]:
        return age <= _SOURCE_FOUND_TTL
    return time.time() - float(stored.get("checked") or 0) < _SOURCE_MISS_TTL


def _outlet_review(name: str, artist: str, album: str, ask, allow_stale=False, stale=None):
    """The outlet's review (or None) from its own stored answer, else ``ask()``; an exception is not stored.

    With `allow_stale` (efficiency K2), a stored answer past its TTL but under 70 days old is returned at
    once, `name` is added to `stale`, and one background ``ask()`` replaces it; a failed ask leaves it.
    """
    store_key = f"album-review-source:v1:{name}:{artist.casefold()}:{album.casefold()}"
    if allow_stale and persistent_metadata.can_read_age():
        stored, age = persistent_metadata.read_with_age(store_key, _REVIEWS_MAX_STALE) or (None, None)
        if isinstance(stored, dict) and "review" in stored:
            if _outlet_answer_is_fresh(stored, age):
                return stored["review"]
            stale_refresh.REFRESHER.submit(("album-review-source", store_key), lambda: _ask_outlet(store_key, ask))
            if stale is not None:
                stale.append(name)
            return stored["review"]
        return _ask_outlet(store_key, ask)
    stored = persistent_metadata.read(store_key, _SOURCE_FOUND_TTL)
    if isinstance(stored, dict) and "review" in stored and (
            stored["review"] or time.time() - float(stored.get("checked") or 0) < _SOURCE_MISS_TTL):
        return stored["review"]
    return _ask_outlet(store_key, ask)


def _review_sources(artist: str, album: str, allow_stale=False, stale=None):
    """The source lookups in display order, each a no-argument callable returning a review or None.

    The Guardian is left out without a key, so a missing key is never stored as "no review". With
    `allow_stale`, an outlet's stale answer may be used; the outlet's name is then added to `stale`.
    """
    asks = [("Pitchfork", lambda: _pitchfork_review(artist, album))]
    if os.environ.get("GUARDIAN_API_KEY", "").strip():
        asks.append(("The Guardian", lambda: _guardian_review(artist, album)))
    asks += [(name, lambda n=name, site=site: _wordpress_review(n, site, artist, album))
             for name, site in _WORDPRESS_REVIEW_SITES]
    return [lambda n=name, ask=ask: _outlet_review(n, artist, album, ask, allow_stale, stale) for name, ask in asks]


def album_reviews_for(artist: str, album: str) -> dict:
    """``{"reviews": [{"source", "quote", "url"}, ...]}`` with at most three entries.

    ``retryable`` is added when an outlet failed or was too slow and fewer than three were found;
    the browser does not keep such an answer. A stored list past its 7-day TTL is answered at once and
    refreshed in the background, for up to 70 days (efficiency K2).
    """
    key = (artist.casefold(), album.casefold())
    return _review_cache.get_or_load(
        key, lambda: _load_album_reviews(artist, album, allow_stale=True),
        store_key="album-reviews:v1:" + key[0] + ":" + key[1],
        store_ttl=_REVIEWS_TTL, accept_stored=lambda stored: bool(stored and stored.get("reviews")),
        stored_ttl=3600, max_stale=_REVIEWS_MAX_STALE, refresh=lambda: _load_album_reviews(artist, album))


def _load_album_reviews(artist: str, album: str, allow_stale=False):
    """The reviews as a `Loaded`. A list built from any stale outlet answer is kept in memory briefly and
    not stored, so it is never stamped as fresh; the outlets' own refreshes fill the store."""
    stale = []
    futures = [_review_pool.submit(source) for source in _review_sources(artist, album, allow_stale, stale)]
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
    short = partial or bool(stale)
    return Loaded(value, memory_ttl=_REVIEWS_PARTIAL_TTL if short else 3600,
                  persist=bool(value["reviews"]) and not short)


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
    return _album_links_cache.get_or_load(
        key, lambda: _load_album_links(artist, album, mbid, allow_stale=True),
        store_key="album-links:v1:" + "|".join(key),
        store_ttl=persistent_metadata.LINKS_TTL, stored_ttl=_ALBUM_LINKS_TTL,
        max_stale=_LINKS_MAX_STALE, refresh=lambda: _load_album_links(artist, album, mbid))


def _load_album_links(artist: str, album: str, mbid: str, allow_stale=False):
    """The links as a `Loaded`. A set that used a stale Apple page is kept for minutes and not stored."""
    return album_page_sources.load_album_links(
        artist, album, mbid, apple=lambda: _apple_album_url_state(artist, album, allow_stale),
        json_get=lambda *a, **k: _json_or_none(*a, **k), mb_get=lambda *a, **k: _EXTERNAL_HTTP.get(*a, **k))


@router.get("/api/artist-image")
def artist_image(name: str = ""):
    """A larger photo for an artist page hero, from Deezer. Empty ``artwork_url`` when none matches."""
    name = name.strip()[:180]
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    return _artist_image_cache.get_or_load(
        name.casefold(), lambda: _load_artist_image(name), store_key=album_page_sources.artist_image_store_key(name),
        accept_stored=_has_artwork, stored_ttl=_ARTWORK_CACHE_TTL)


_has_artwork = album_page_sources.has_artwork


def _load_artist_image(name: str):
    return album_page_sources.load_artist_image(_EXTERNAL_HTTP.get, name)


def _fallback_album_artwork(artist: str, album: str):
    """An exact-match cover from Apple Music, else Qobuz. Raises when a provider cannot be reached."""
    response = _EXTERNAL_HTTP.get("https://itunes.apple.com/search", params={
        "term": f"{artist} {album}", "entity": "album", "limit": 10})
    response.raise_for_status()
    found = select_apple_artwork(response.json().get("results") or [], artist, album)
    if found:
        return found
    response = _EXTERNAL_HTTP.get(
        "https://www.qobuz.com/us-en/search", params={"q": f"{artist} {album}"},
        headers=_APPLE_PAGE_HEADERS, follow_redirects=True)
    response.raise_for_status()
    return select_qobuz_artwork(parse_qobuz_albums(response.text), artist, album)


@router.get("/api/artwork")
def album_artwork(artist: str = "", album: str = ""):
    artist = artist.strip()[:180]
    album = album.strip()[:180]
    if not artist and not album:
        raise HTTPException(status_code=400, detail="artist or album is required")

    key = (artist.casefold(), album.casefold())
    return _artwork_cache.get_or_load(
        key, lambda: _load_album_artwork(artist, album), store_key="album-artwork:v2:" + key[0] + ":" + key[1],
        accept_stored=_has_artwork, stored_ttl=_ARTWORK_CACHE_TTL)


def _load_album_artwork(artist: str, album: str):
    result = {"artwork_url": None, "image_kind": "album", "source": "Deezer"}
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
        # Deezer does not have the album: ask Apple Music, then Qobuz, for an exactly matching cover.
        if not result["artwork_url"] and artist and album:
            result = _fallback_album_artwork(artist, album) or result

        # An artist photo is only a valid answer when no album was requested; using it
        # for a missing album made one picture appear on several albums of an artist.
        if not result["artwork_url"] and artist and not album:
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
        result["retryable"] = True
        return Loaded(result)

    found = bool(result.get("artwork_url"))
    return Loaded(result, memory_ttl=_ARTWORK_CACHE_TTL if found else _ARTWORK_NEGATIVE_CACHE_TTL, persist=found)


