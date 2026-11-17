"""The Deezer, Apple Music and Wikipedia loaders behind the album page (efficiency K3 part 2).

The metadata routes (``app/api/metadata.py``) and the worker's owned-entity prefetch
(``app/services/owned_prefetch.py``) must fill the same stored rows, so what each namespace asks, how an answer
is shaped, its store key and whether it may be stored are defined once, here. Every function takes the HTTP
``get`` it should use: the route passes its metered client, the worker passes a counting, capped one, so a
request past a cap is refused before it is sent.

Nothing here imports ``app.api`` or a route module. The route wraps these in ``LayeredCache`` (memory,
single-flight, stale serving). The worker has no such cache and does not attach ``persistent_metadata``, so
``prefetch_*`` read and write the metadata store through the ``read``/``write`` callables it is given, under the
same keys.

A refused or failed request is never turned into a stored answer: the worker's description path stores only a
description that was found, and writes nothing when Apple's answer is missing because a request failed.
"""
from urllib.parse import quote, urlencode

from app.services import album_links, album_reviews, album_wikipedia, persistent_metadata
from app.services.apple_description import parse_editorial_notes
from app.services.deezer_album_details import shape_album_match
from app.services.deezer_album_matching import exact_album_matches
from app.services.deezer_tracklist import shape_tracklist
from app.services.layered_cache import Loaded

EXTERNAL_HEADERS = {
    # Wikimedia answers 403 ("robot policy") to this User-Agent when the request carries httpx's
    # default `Accept: */*`, so every artist bio came back empty. A JSON Accept header fixes it.
    "User-Agent": "Discair/1.0 (personal music discovery; contact: local app)",
    "Accept": "application/json",
}
EXTERNAL_TIMEOUT = 3.0
APPLE_PAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Accept": "text/html",
}

DETAILS_MEMORY_TTL = 6 * 60 * 60
DETAILS_MISS_TTL = 60 * 60
DESCRIPTION_TTL = 7 * 24 * 60 * 60
DESCRIPTION_MISS_TTL = 24 * 60 * 60
EMPTY_DESCRIPTION = {"paragraphs": [], "source": "Apple Music", "url": None}


def clean(value) -> str:
    """The route's normalisation of an artist or album name (the store keys are built from it)."""
    return str(value or "").strip()[:180]


def details_store_key(artist: str, album: str) -> str:
    return "album-details:v1:" + artist.casefold() + ":" + album.casefold()


def description_store_key(artist: str, album: str) -> str:
    return "album-description:v1:" + artist.casefold() + ":" + album.casefold()


def apple_url_store_key(artist: str, album: str) -> str:
    return "apple-album-url:v1:" + artist.casefold() + ":" + album.casefold()


def counting_get(get):
    """``get`` with the route client's User-Agent, Accept header and timeout, for a bare ``httpx.get``-style callable."""
    def send(url, **kwargs):
        headers = {**EXTERNAL_HEADERS, **(kwargs.pop("headers", None) or {})}
        timeout = kwargs.pop("timeout", EXTERNAL_TIMEOUT)
        return get(url, headers=headers, timeout=timeout, **kwargs)
    return send


# --- Deezer album details and tracklist -------------------------------------------------------------

def fetch_album_details(get, artist, album):
    """The Deezer answer and whether an empty one is final (no exact catalog match)."""
    result = {"artist": artist, "album": album, "year": None, "artwork_url": None, "tracks": []}
    try:
        query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 12})
        response = get("https://api.deezer.com/search/album?" + query)
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

        detail_response = get(f"https://api.deezer.com/album/{album_id}")
        detail_response.raise_for_status()
        details = detail_response.json()
        result["tracks"] = shape_tracklist(details.get("tracks", {}).get("data") or [])
        if not result["tracks"]:
            result["message"] = "The album was found, but its tracklist is unavailable."
        return result, False
    except Exception:
        result["message"] = "The album catalog is temporarily unavailable."
        return result, False


def details_loaded(result, definitive_miss) -> Loaded:
    """A complete answer is kept (memory and store); a definite no-match for an hour; a failure not at all."""
    if result["tracks"]:
        return Loaded(result, memory_ttl=DETAILS_MEMORY_TTL, persist=True)
    return Loaded(result, memory_ttl=DETAILS_MISS_TTL if definitive_miss else None)


def prefetch_tracks(read, write, get, artist, album) -> list:
    """The worker's Deezer tracklist: the stored row if there is one, else one fetch, stored only when complete."""
    artist, album = clean(artist), clean(album)
    if not artist or not album:
        return []
    key = details_store_key(artist, album)
    stored = read(key, persistent_metadata.FOUND_TTL)
    if stored:
        return stored.get("tracks") or []
    loaded = details_loaded(*fetch_album_details(get, artist, album))
    if loaded.persist:
        write(key, loaded.value)
    return loaded.value.get("tracks") or []


# --- Apple Music notes and Wikipedia lead -----------------------------------------------------------

def apple_search_url(get, artist, album):
    """``(page address or None, answered)``; ``answered`` is False when the search request itself failed."""
    try:
        response = get("https://itunes.apple.com/search", params={
            "term": f"{artist} {album}", "entity": "album", "limit": 10})
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None, False
    return album_links.apple_music_url((data or {}).get("results") or [], artist, album), True


def apple_notes(get, artist, album, url):
    """Apple Music's notes as ``({"paragraphs", "source", "url"}, answered)`` for a matched page address."""
    try:
        response = get(url, headers=APPLE_PAGE_HEADERS, follow_redirects=True, timeout=6.0)
        response.raise_for_status()
    except Exception:
        return dict(EMPTY_DESCRIPTION), False
    return {"paragraphs": parse_editorial_notes(response.text) or [], "source": "Apple Music", "url": url}, True


def wikipedia_description(get, artist, album):
    """The album's Wikipedia lead as ``(description or None, answered)``."""
    try:
        search = get("https://en.wikipedia.org/w/rest.php/v1/search/page", params={
            "q": f"{album_reviews.search_text(artist, album)} album", "limit": 5})
        search.raise_for_status()
        key = album_wikipedia.pick_album_article(search.json().get("pages"), artist, album)
        if not key:
            return None, True
        summary = get("https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(key, safe=""))
        summary.raise_for_status()
        return album_wikipedia.description_from_summary(summary.json()), True
    except Exception:
        return None, False


def load_description(apple, wikipedia, *, require_apple_answer=False) -> Loaded:
    """Apple's notes, else Wikipedia's lead, else empty, as a `Loaded`.

    ``apple()`` and ``wikipedia()`` return ``(value, answered)``. Found text is kept for a week; an empty answer
    is remembered for a day only when both sources answered, and a failure is not remembered. With
    ``require_apple_answer`` (the worker) an Apple answer lost to a failed request ends the lookup with nothing
    to store, so a Wikipedia lead is never kept in place of notes Apple would have given.
    """
    value, apple_answered = apple()
    wikipedia_answered = True
    if not value["paragraphs"]:
        if require_apple_answer and not apple_answered:
            return Loaded(value, memory_ttl=None)
        found, wikipedia_answered = wikipedia()
        if found:
            value = found
    if value["paragraphs"]:
        return Loaded(value, memory_ttl=DESCRIPTION_TTL, persist=True)
    return Loaded(value, memory_ttl=DESCRIPTION_MISS_TTL if apple_answered and wikipedia_answered else None)


def prefetch_description(read, write, get, artist, album) -> dict:
    """The worker's album description: the stored row, else Apple then Wikipedia, storing only found text.

    The Apple page address is read from and stored under the route's own ``apple-album-url`` row.
    """
    artist, album = clean(artist), clean(album)
    if not artist or not album:
        return dict(EMPTY_DESCRIPTION)
    key = description_store_key(artist, album)
    stored = read(key, DESCRIPTION_TTL)
    if stored and stored.get("paragraphs"):
        return stored

    def apple():
        url_key = apple_url_store_key(artist, album)
        url, answered = read(url_key, persistent_metadata.LINKS_TTL), True
        if not url:
            url, answered = apple_search_url(get, artist, album)
            if url:
                write(url_key, url)
        if not url:
            return dict(EMPTY_DESCRIPTION), answered
        return apple_notes(get, artist, album, url)

    loaded = load_description(apple, lambda: wikipedia_description(get, artist, album), require_apple_answer=True)
    if loaded.persist:
        write(key, loaded.value)
    return loaded.value
