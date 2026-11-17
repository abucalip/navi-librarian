"""The Deezer, Apple Music, Wikipedia and MusicBrainz-year loaders behind the album and artist pages (efficiency K3 part 2).

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

Efficiency K5 (owner approval 2026-11-17): a definitive no-match from Deezer's album search (the query the
album details and the album links share) or from Apple's album search is remembered for an hour under its own
key (``no_match_store_key``), through the same ``read``/``write`` callables, so the route and the worker skip
the provider for that album. Only a provider answer writes the mark; a failure, a refusal or a Deezer error
body does not.

Efficiency K6: a found Deezer album page is kept on its own (``deezer_url_store_key``, the links' 7 days, like the
Apple page address) so an incomplete links set does not ask Deezer again, and a Wikipedia search that answered
with no matching article is remembered for an hour (``no_match_store_key("wikipedia", ...)``); a failed request
writes neither.
"""
import threading
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
from urllib.parse import quote, urlencode

from app.services import album_links, album_reviews, album_wikipedia, negative_marks, persistent_metadata
from app.services.apple_description import parse_editorial_notes
from app.services.deezer_album_details import shape_album_match
from app.services.deezer_album_matching import exact_album_matches, exact_album_release_year
from app.services.deezer_artwork import pick_artist, select_artist_artwork
from app.services.deezer_tracklist import shape_tracklist
from app.services.layered_cache import Loaded
from integrations.musicbrainz import album_year as mb_year

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

ARTWORK_CACHE_TTL = 6 * 60 * 60
DETAILS_MEMORY_TTL = ARTWORK_CACHE_TTL
YEAR_STORE_TTL = 365 * 24 * 60 * 60
LINKS_MEMORY_TTL = 24 * 60 * 60
LINKS_INCOMPLETE_TTL = 10 * 60
DETAILS_MISS_TTL = 60 * 60
DESCRIPTION_TTL = 7 * 24 * 60 * 60
DESCRIPTION_MISS_TTL = 24 * 60 * 60
EMPTY_DESCRIPTION = {"paragraphs": [], "source": "Apple Music", "url": None}
NO_MATCH_TTL = 60 * 60
NO_MATCH_MESSAGE = "No exact catalog match was found, so the tracklist is unavailable."


def clean(value) -> str:
    """The route's normalisation of an artist or album name (the store keys are built from it)."""
    return str(value or "").strip()[:180]


def details_store_key(artist: str, album: str) -> str:
    return "album-details:v1:" + artist.casefold() + ":" + album.casefold()


def description_store_key(artist: str, album: str) -> str:
    return "album-description:v1:" + artist.casefold() + ":" + album.casefold()


def apple_url_store_key(artist: str, album: str) -> str:
    return "apple-album-url:v1:" + artist.casefold() + ":" + album.casefold()


def deezer_url_store_key(artist: str, album: str) -> str:
    return "album-deezer-url:v1:" + artist.casefold() + ":" + album.casefold()


def no_match_store_key(provider: str, artist: str, album: str) -> str:
    """The K5 mark's key: ``provider`` is ``deezer`` (album search) or ``apple`` (album search)."""
    return "album-no-match:v1:" + provider + ":" + artist.casefold() + ":" + album.casefold()


def no_match_is_live(read, provider, artist, album) -> bool:
    return negative_marks.is_live(read, no_match_store_key(provider, artist, album), NO_MATCH_TTL)


def mark_no_match(write, provider, artist, album) -> None:
    negative_marks.mark(write, no_match_store_key(provider, artist, album))


def deezer_albums(response) -> list:
    """The albums of a Deezer search answer. Deezer reports quota and other errors as a 200 with an
    ``error`` object; that raises here, so it is a failure, never a no-match."""
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("error"):
        raise ValueError("Deezer answered with an error")
    return payload.get("data") or []


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
        albums = deezer_albums(response)
        exact = exact_album_matches(albums, artist, album)
        if not exact:
            result["message"] = NO_MATCH_MESSAGE
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


def fetch_album_details_remembered(read, write, get, artist, album):
    """`fetch_album_details`, skipped while a Deezer no-match mark lives; a new definitive no-match writes one."""
    if no_match_is_live(read, "deezer", artist, album):
        return {"artist": artist, "album": album, "year": None, "artwork_url": None, "tracks": [],
                "message": NO_MATCH_MESSAGE}, True
    result, definitive_miss = fetch_album_details(get, artist, album)
    if definitive_miss:
        mark_no_match(write, "deezer", artist, album)
    return result, definitive_miss


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
    loaded = details_loaded(*fetch_album_details_remembered(read, write, get, artist, album))
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


def apple_search_url_remembered(read, write, artist, album, search):
    """``search()`` (``(page address or None, answered)``, as `apple_search_url`), skipped while an Apple no-match
    mark lives; an answered search with no exact match writes one."""
    if no_match_is_live(read, "apple", artist, album):
        return None, True
    url, answered = search()
    if answered and not url:
        mark_no_match(write, "apple", artist, album)
    return url, answered


def apple_page_url(read, write, get, artist, album):
    """``(Apple page address or None, answered)``: the stored ``apple-album-url`` row, else one search (found: stored)."""
    key = apple_url_store_key(artist, album)
    url = read(key, persistent_metadata.LINKS_TTL)
    if url:
        return url, True
    url, answered = apple_search_url_remembered(read, write, artist, album, lambda: apple_search_url(get, artist, album))
    if url:
        write(key, url)
    return url, answered


def apple_notes(get, artist, album, url):
    """Apple Music's notes as ``({"paragraphs", "source", "url"}, answered)`` for a matched page address."""
    try:
        response = get(url, headers=APPLE_PAGE_HEADERS, follow_redirects=True, timeout=6.0)
        response.raise_for_status()
    except Exception:
        return dict(EMPTY_DESCRIPTION), False
    return {"paragraphs": parse_editorial_notes(response.text) or [], "source": "Apple Music", "url": url}, True


def wikipedia_description(get, artist, album, on_no_article=None):
    """The album's Wikipedia lead as ``(description or None, answered)``.

    ``on_no_article()`` is called when the search answered and no article matched (never after a failure).
    """
    try:
        search = get("https://en.wikipedia.org/w/rest.php/v1/search/page", params={
            "q": f"{album_reviews.search_text(artist, album)} album", "limit": 5})
        search.raise_for_status()
        key = album_wikipedia.pick_album_article(search.json().get("pages"), artist, album)
        if not key:
            if on_no_article:
                on_no_article()
            return None, True
        summary = get("https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(key, safe=""))
        summary.raise_for_status()
        return album_wikipedia.description_from_summary(summary.json()), True
    except Exception:
        return None, False


def wikipedia_description_remembered(read, write, get, artist, album):
    """`wikipedia_description`, skipped while a Wikipedia no-article mark lives; a search with no match writes one (K6)."""
    if no_match_is_live(read, "wikipedia", artist, album):
        return None, True
    return wikipedia_description(get, artist, album, lambda: mark_no_match(write, "wikipedia", artist, album))


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
        url, answered = apple_page_url(read, write, get, artist, album)
        if not url:
            return dict(EMPTY_DESCRIPTION), answered
        return apple_notes(get, artist, album, url)

    loaded = load_description(apple, lambda: wikipedia_description_remembered(read, write, get, artist, album),
        require_apple_answer=True)
    if loaded.persist:
        write(key, loaded.value)
    return loaded.value


# --- Album year -------------------------------------------------------------------------------------

def year_store_key(artist: str, album: str) -> str:
    return "album-year:v1:" + mb_year.normalize(artist) + ":" + mb_year.normalize(album)


def deezer_year_answer(get, artist, album):
    """``(release year of an exact Deezer match or None, answered)``; ``answered`` is False when the request failed."""
    try:
        query = urlencode({"q": f'artist:"{artist}" album:"{album}"', "limit": 20})
        response = get("https://api.deezer.com/search/album?" + query)
        response.raise_for_status()
        return exact_album_release_year(deezer_albums(response), artist, album), True
    except Exception:
        return None, False


def deezer_year(get, artist, album):
    """The release year of an exact Deezer match, else None (a failure is also None; nothing is stored for it)."""
    return deezer_year_answer(get, artist, album)[0]


def deezer_year_remembered(read, write, get, artist, album):
    """`deezer_year`, skipped while a ``deezer-year`` no-match mark lives; an answer without a year writes one (K5).

    Its own mark: this search asks for 20 results, not the details' and links' 12, so it is a different question.
    """
    if no_match_is_live(read, "deezer-year", artist, album):
        return None
    year, answered = deezer_year_answer(get, artist, album)
    if answered and not year:
        mark_no_match(write, "deezer-year", artist, album)
    return year


def prefetch_year(read, write, mb_fetch, deezer_get, artist, album):
    """The worker's album year: the stored row, else one counted MusicBrainz lookup (then Deezer, when given).

    Only a found year is stored. A MusicBrainz lookup that failed or was refused ends with nothing stored and no
    Deezer fallback, so a refusal never changes which source a year comes from.
    """
    artist, album = clean(artist), clean(album)
    if not artist or not album:
        return None
    key = year_store_key(artist, album)
    try:
        stored = read(key, YEAR_STORE_TTL)
        if stored:
            return int(stored)
    except (TypeError, ValueError):
        pass
    year, answered = mb_year.lookup_album_year_counted(artist, album, mb_fetch)
    if not answered:
        return None
    if not year and deezer_get is not None:
        year = deezer_year_remembered(read, write, deezer_get, artist, album)
    if year:
        write(key, int(year))
    return year


# --- Album links ------------------------------------------------------------------------------------

def links_store_key(artist: str, album: str, mbid: str) -> str:
    return "album-links:v1:" + "|".join((artist.casefold(), album.casefold(), mbid))


def json_or_none(get):
    """``get`` turned into a function giving a JSON answer, or None when the request fails. Links are best effort."""
    def ask(url, **kwargs):
        try:
            response = get(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None
    return ask


def load_album_links(artist, album, mbid, *, apple, json_get, mb_get, read, write) -> Loaded:
    """The album's page on each service that matched exactly, as a `Loaded`.

    ``apple()`` returns ``(page address or None, stale)``; ``json_get(url, **kw)`` a JSON answer or None;
    ``mb_get`` is the raw HTTP get for MusicBrainz; ``read``/``write`` hold the Deezer no-match mark (K5) and the found Deezer page (K6). A set
    that is incomplete (a service slow, busy, refused or without a match) or used a stale Apple page is kept for
    minutes and not stored, so a no-match is remembered for its hour only, never for the links' week.
    """
    def deezer():
        page_key = deezer_url_store_key(artist, album)
        kept = read(page_key, persistent_metadata.LINKS_TTL)
        if kept:
            return kept
        if no_match_is_live(read, "deezer", artist, album):
            return None
        data = json_get("https://api.deezer.com/search/album?" + urlencode(
            {"q": f'artist:"{artist}" album:"{album}"', "limit": 12}))
        answered = isinstance(data, dict) and not data.get("error")  # None: a failed request
        albums = (data.get("data") or []) if answered else []
        if answered and not exact_album_matches(albums, artist, album):
            mark_no_match(write, "deezer", artist, album)
        page = album_links.deezer_url(albums, artist, album)
        if page:
            write(page_key, page)
        return page

    def musicbrainz():
        if mbid:
            return mbid
        from discovery.search.providers import MusicBrainzSearch

        deadline = monotonic() + 4.0
        try:
            groups = MusicBrainzSearch(get=mb_get).release_groups_named(
                artist, album, remaining=lambda: deadline - monotonic(), cancelled=threading.Event())
        except Exception:
            return None
        return album_links.musicbrainz_group_id(groups, artist, album)

    with ThreadPoolExecutor(max_workers=3) as pool:
        apple_future, deezer_future, mb_future = pool.submit(apple), pool.submit(deezer), pool.submit(musicbrainz)
        (apple_url, apple_stale), deezer_page, group_id = apple_future.result(), deezer_future.result(), mb_future.result()

    links = {}
    if apple_url:
        links["apple_music"] = apple_url
    if deezer_page:
        links["deezer"] = deezer_page
    if group_id:
        links["musicbrainz"] = f"https://musicbrainz.org/release-group/{group_id}"
        links["listenbrainz"] = f"https://listenbrainz.org/album/{group_id}"
    complete = "musicbrainz" in links and "apple_music" in links and "deezer" in links
    keep = complete and not apple_stale
    return Loaded(links, memory_ttl=LINKS_MEMORY_TTL if keep else LINKS_INCOMPLETE_TTL, persist=keep)


def prefetch_links(read, write, get, artist, album, mbid) -> dict:
    """The worker's album links: the stored row, else one lookup, stored only when complete.

    Keyed by the strings the clients send: the album page's artist and album, and its release-group id or "".
    """
    artist, album, mbid = clean(artist), clean(album), str(mbid or "").strip()[:40]
    if not artist or not album:
        return {}
    key = links_store_key(artist, album, mbid)
    stored = read(key, persistent_metadata.LINKS_TTL)
    if stored:
        return stored
    loaded = load_album_links(
        artist, album, mbid, apple=lambda: (apple_page_url(read, write, get, artist, album)[0], False),
        json_get=json_or_none(get), mb_get=get, read=read, write=write)
    if loaded.persist:
        write(key, loaded.value)
    return loaded.value


# --- Artist image -----------------------------------------------------------------------------------

def artist_image_store_key(name: str) -> str:
    return "artist-image:v2:" + name.casefold()


def has_artwork(stored) -> bool:
    return bool(stored and stored.get("artwork_url"))


def load_artist_image(get, name) -> Loaded:
    """A larger Deezer photo of the matched artist, as a `Loaded`; a provider failure is marked retryable, not kept."""
    result = {"artwork_url": None, "image_kind": "artist", "source": "Deezer"}
    try:
        response = get("https://api.deezer.com/search/artist?" + urlencode({"q": name, "limit": 8}))
        response.raise_for_status()
        artists = response.json().get("data") or []
        match = select_artist_artwork(artists, name)
        if match is not None:
            # The larger photo of the artist that was matched, not of another artist with the same name.
            photo = (pick_artist(artists, name) or {}).get("picture_xl")
            result = {**match, "artwork_url": (photo or match["artwork_url"]).replace("http://", "https://", 1)}
    except Exception:
        return Loaded({**result, "retryable": True})
    return Loaded(result, memory_ttl=ARTWORK_CACHE_TTL, persist=bool(result.get("artwork_url")))


def prefetch_artist_image(read, write, get, name) -> dict:
    """The worker's artist photo: the stored row, else one search, stored only when a photo was found."""
    name = clean(name)
    if not name:
        return {}
    key = artist_image_store_key(name)
    stored = read(key, persistent_metadata.FOUND_TTL)
    if has_artwork(stored):
        return stored
    loaded = load_artist_image(get, name)
    if loaded.persist:
        write(key, loaded.value)
    return loaded.value
