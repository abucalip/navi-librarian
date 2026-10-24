"""Fallback genre tags for artists whose MusicBrainz genre tags are missing or too few.

The ListenBrainz artist batch returns only MusicBrainz genre tags, so many artists (about a
sixth of one measured history, including niche genres such as desert blues) have none, and the
Deep cuts gates reject their albums. Last.fm top tags cover most of them but are noisy
("female vocalists", "seen live"), so they are kept only when they name a MusicBrainz genre.

Pure functions over injected HTTP and cache callables, so tests use stubs and never touch the
network. Everything is best-effort and bounded: a failed call leaves an artist without extra
tags and never raises. Unwired; see docs/engine2.md.
"""
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Iterable, Mapping, Sequence

LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
MUSICBRAINZ_GENRE_URL = "https://musicbrainz.org/ws/2/genre/all"
GENRE_LIST_CACHE_KEY = "mb:genre-list"
GENRE_LIST_TTL_SECONDS = 90 * 24 * 60 * 60
LASTFM_TAGS_CACHE_PREFIX = "lfm:artist-tags:"
LASTFM_TAGS_TTL_SECONDS = 90 * 24 * 60 * 60
GENRE_PAGE_SIZE = 100
MAX_GENRE_PAGES = 40
MUSICBRAINZ_SPACING_SECONDS = 1.1
# A page is tried this many times, waiting between tries; a page that never answers discards the list.
GENRE_PAGE_ATTEMPTS = 3
GENRE_RETRY_SECONDS = 5.0
# Last.fm allows about four calls a second; each worker waits this long after a call.
LASTFM_WORKER_SPACING_SECONDS = 0.9
# Last.fm error 6: the artist is definitively unknown (not a transient failure).
LASTFM_NOT_FOUND = 6
DEFAULT_MIN_COUNT = 10
DEFAULT_TAG_LIMIT = 5
DEFAULT_MAX_CALLS = 40


def fetch_musicbrainz_genres(
    get: Callable[..., Any], headers: Mapping[str, str], *,
    sleep: Callable[[float], Any] | None = None, timeout: float = 25,
) -> set[str]:
    """All MusicBrainz genre names, lower-cased. Returns an empty set on any failure: a
    partial list would silently drop real genres, so a failed page discards the result."""
    genres: set[str] = set()
    for page in range(MAX_GENRE_PAGES):
        body = None
        for attempt in range(GENRE_PAGE_ATTEMPTS):
            try:
                response = get(MUSICBRAINZ_GENRE_URL, params={
                    "fmt": "json", "limit": GENRE_PAGE_SIZE, "offset": page * GENRE_PAGE_SIZE,
                }, headers=dict(headers), timeout=timeout)
                if response.status_code == 200:
                    body = response.json()
            except Exception:
                body = None
            if sleep is not None:
                sleep(MUSICBRAINZ_SPACING_SECONDS if body is not None else GENRE_RETRY_SECONDS)
            if body is not None:
                break
        names = body.get("genres") if isinstance(body, dict) else None
        if not isinstance(names, list):
            return set()
        genres.update(str(g["name"]).strip().casefold() for g in names
                      if isinstance(g, dict) and g.get("name"))
        if (page + 1) * GENRE_PAGE_SIZE >= int(body.get("genre-count") or 0):
            return genres
    return set()


def load_genre_vocabulary(
    get: Callable[..., Any], headers: Mapping[str, str],
    cache_get: Callable[..., Any], cache_set: Callable[..., Any], *,
    sleep: Callable[[float], Any] | None = None,
) -> set[str]:
    """The MusicBrainz genre names, from the cache when fresh (about 25 requests otherwise)."""
    try:
        cached = cache_get(GENRE_LIST_CACHE_KEY, ttl_seconds=GENRE_LIST_TTL_SECONDS)
    except Exception:
        cached = None
    if isinstance(cached, list) and cached:
        return {str(name) for name in cached}
    genres = fetch_musicbrainz_genres(get, headers, sleep=sleep)
    if genres:
        try:
            cache_set(GENRE_LIST_CACHE_KEY, sorted(genres))
        except Exception:
            pass
    return genres


def _lastfm_top_tags(
    get: Callable[..., Any], artist_mbid: str, api_key: str, timeout: float,
) -> list[list]:
    """[[tag, count], ...] for one artist; [] when Last.fm does not know it. Raises on any
    transient failure so the caller leaves the value uncached."""
    from recommendation_run_metrics import record_provider_call

    record_provider_call("lastfm", "artist.getTopTags")
    response = get(LASTFM_API_URL, params={
        "method": "artist.gettoptags", "mbid": artist_mbid, "api_key": api_key, "format": "json",
    }, timeout=timeout)
    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("Last.fm returned a non-object body")
    if "error" in body:
        if body["error"] == LASTFM_NOT_FOUND:
            return []
        raise RuntimeError(f"Last.fm error {body['error']}")
    if response.status_code != 200:
        raise RuntimeError(f"Last.fm returned {response.status_code}")
    tags = (body.get("toptags") or {}).get("tag")
    if isinstance(tags, dict):
        tags = [tags]
    if not isinstance(tags, list):
        raise RuntimeError("Last.fm body has no tags")
    out = []
    for item in tags:
        try:
            out.append([str(item["name"]).strip().casefold(), int(item["count"])])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def fallback_artist_tags(
    artist_mbids: Iterable[str],
    existing_tags: Mapping[str, Sequence[str]],
    *,
    get: Callable[..., Any],
    api_key: str,
    vocabulary: Iterable[str],
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    sleep: Callable[[float], Any] | None = None,
    min_existing: int = 2,
    min_count: int = DEFAULT_MIN_COUNT,
    limit: int = DEFAULT_TAG_LIMIT,
    max_calls: int = DEFAULT_MAX_CALLS,
    workers: int = 4,
    timeout: float = 15,
) -> dict[str, list[str]]:
    """Extend the tags of artists that have fewer than ``min_existing``.

    Returns {artist MBID: tags} only for artists whose tag list grew: the existing tags first,
    then Last.fm top tags with a count of at least ``min_count`` that name a genre in
    ``vocabulary``, up to ``limit`` in all. Cached artists cost no call; at most ``max_calls``
    uncached artists are fetched, in the order given. Never raises."""
    for name, value in (("min_existing", min_existing), ("min_count", min_count),
                        ("limit", limit), ("max_calls", max_calls), ("workers", workers)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (name == "workers" and value < 1):
            raise ValueError(f"{name} must be a non-negative integer (workers at least 1)")
    genres = {str(name).casefold() for name in vocabulary}
    if not genres:
        return {}
    wanted = [
        mbid for mbid in dict.fromkeys(str(m) for m in artist_mbids if m)
        if len(existing_tags.get(mbid, ())) < min_existing
    ]
    cached: dict[str, list[list]] = {}
    pending: list[str] = []
    for mbid in wanted:
        try:
            value = cache_get(f"{LASTFM_TAGS_CACHE_PREFIX}{mbid}", ttl_seconds=LASTFM_TAGS_TTL_SECONDS)
        except Exception:
            value = None
        if isinstance(value, list):
            cached[mbid] = value
        else:
            pending.append(mbid)
    pending = pending[:max_calls]

    def fetch(mbid: str):
        try:
            tags = _lastfm_top_tags(get, mbid, api_key, timeout)
        except Exception:
            return mbid, None
        if sleep is not None:
            sleep(LASTFM_WORKER_SPACING_SECONDS)
        return mbid, tags

    if pending:
        with ThreadPoolExecutor(max_workers=min(workers, len(pending))) as pool:
            for mbid, tags in pool.map(fetch, pending):
                if tags is None:
                    continue
                cached[mbid] = tags
                try:
                    cache_set(f"{LASTFM_TAGS_CACHE_PREFIX}{mbid}", tags)
                except Exception:
                    pass

    result: dict[str, list[str]] = {}
    for mbid in wanted:
        merged = list(existing_tags.get(mbid, ()))
        for name, count in cached.get(mbid, ()):
            if len(merged) >= limit:
                break
            if count >= min_count and name in genres and name not in merged:
                merged.append(name)
        if len(merged) > len(existing_tags.get(mbid, ())):
            result[mbid] = merged
    return result
