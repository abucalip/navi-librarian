"""Fallback genre tags for artists whose MusicBrainz genre tags are missing or too few.

The ListenBrainz artist batch returns only MusicBrainz genre tags, so many artists (about a
sixth of one measured history, including niche genres such as desert blues) have none, and the
Deep cuts gates reject their albums. Discogs master-release styles cover many of them and are
kept only when they name a MusicBrainz genre.

Pure functions over injected HTTP and cache callables, so tests use stubs and never touch the
network. Everything is best-effort and bounded: a failed call leaves an artist without extra
tags and never raises.
"""
from concurrent.futures import ThreadPoolExecutor
import re
from typing import Any, Callable, Iterable, Mapping, Sequence

from discovery.search.normalize import normalize_key
from integrations.provider_gate import musicbrainz_lane

DISCOGS_SEARCH_URL = "https://api.discogs.com/database/search"
MUSICBRAINZ_GENRE_URL = "https://musicbrainz.org/ws/2/genre/all"
GENRE_LIST_CACHE_KEY = "mb:genre-list"
GENRE_LIST_TTL_SECONDS = 90 * 24 * 60 * 60
DISCOGS_TAGS_CACHE_PREFIX = "discogs:artist-tags:"
DISCOGS_TAGS_TTL_SECONDS = 90 * 24 * 60 * 60
GENRE_PAGE_SIZE = 100
MAX_GENRE_PAGES = 40
# A page is tried this many times, waiting between tries; a page that never answers discards the list.
GENRE_PAGE_ATTEMPTS = 3
GENRE_RETRY_SECONDS = 5.0
# Discogs allows 60 authenticated requests per minute; keep at least 1 s between calls.
DISCOGS_SPACING_SECONDS = 1.0
DISCOGS_PER_PAGE = 25
DEFAULT_TAG_LIMIT = 5
DEFAULT_MAX_CALLS = 40


def fetch_musicbrainz_genres(
    get: Callable[..., Any], headers: Mapping[str, str], *,
    lane: Any = None, timeout: float = 25,
) -> set[str]:
    """All MusicBrainz genre names, lower-cased. Returns an empty set on any failure: a
    partial list would silently drop real genres, so a failed page discards the result."""
    genres: set[str] = set()
    lane = lane or musicbrainz_lane()
    for page in range(MAX_GENRE_PAGES):
        body = None
        for attempt in range(GENRE_PAGE_ATTEMPTS):
            if not lane.acquire():
                return set()
            try:
                response = get(MUSICBRAINZ_GENRE_URL, params={
                    "fmt": "json", "limit": GENRE_PAGE_SIZE, "offset": page * GENRE_PAGE_SIZE,
                }, headers=dict(headers), timeout=timeout)
                if response.status_code == 200:
                    body = response.json()
            except Exception:
                body = None
            if body is None:
                lane.penalize(GENRE_RETRY_SECONDS)  # the retry pause, held for every caller
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
    lane: Any = None,
) -> set[str]:
    """The MusicBrainz genre names, from the cache when fresh (about 25 requests otherwise)."""
    try:
        cached = cache_get(GENRE_LIST_CACHE_KEY, ttl_seconds=GENRE_LIST_TTL_SECONDS)
    except Exception:
        cached = None
    if isinstance(cached, list) and cached:
        return {str(name) for name in cached}
    genres = fetch_musicbrainz_genres(get, headers, lane=lane)
    if genres:
        try:
            cache_set(GENRE_LIST_CACHE_KEY, sorted(genres))
        except Exception:
            pass
    return genres


def _discogs_name(name: str) -> str:
    """An artist name without Discogs' disambiguation suffix, so 'Ash (2)' reads 'Ash'."""
    return re.sub(r"\s+\(\d+\)$", "", name.strip())


def _discogs_artist_styles(
    get: Callable[..., Any],
    artist_name: str,
    token: str,
    headers: Mapping[str, str] | None,
    timeout: float,
) -> list[str]:
    """Lower-cased Discogs styles for one artist, most frequent first; [] on no match.

    Raises on any transient or auth failure so the caller leaves the value uncached.
    """
    from recommendation_run_metrics import record_provider_call

    record_provider_call("discogs", "database.search")
    req_headers = dict(headers) if headers else {}
    req_headers["Authorization"] = f"Discogs token={token}"
    response = get(
        DISCOGS_SEARCH_URL,
        params={"type": "master", "artist": artist_name, "per_page": DISCOGS_PER_PAGE},
        headers=req_headers,
        timeout=timeout,
    )
    if response.status_code == 404:
        return []
    if response.status_code != 200:
        raise RuntimeError(f"Discogs returned {response.status_code}")
    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("Discogs returned a non-object body")
    results = body.get("results")
    if not isinstance(results, list):
        raise RuntimeError("Discogs body has no results")
    key = normalize_key(artist_name)
    if not key:
        return []
    counts: dict[str, int] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        artist, separator, _ = str(item.get("title") or "").partition(" - ")
        if not separator or normalize_key(_discogs_name(artist)) != key:
            continue
        styles = item.get("style")
        if not isinstance(styles, list):
            continue
        for style in styles:
            folded = str(style).strip().casefold()
            if folded:
                counts[folded] = counts.get(folded, 0) + 1
    return sorted(counts, key=lambda s: (-counts[s], s))


def fallback_artist_tags(
    artist_mbids: Iterable[str],
    existing_tags: Mapping[str, Sequence[str]],
    *,
    get: Callable[..., Any],
    discogs_token: str,
    artist_names: Mapping[str, str],
    vocabulary: Iterable[str],
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    headers: Mapping[str, str] | None = None,
    sleep: Callable[[float], Any] | None = None,
    min_existing: int = 2,
    limit: int = DEFAULT_TAG_LIMIT,
    max_calls: int = DEFAULT_MAX_CALLS,
    workers: int = 1,
    timeout: float = 15,
) -> dict[str, list[str]]:
    """Extend the tags of artists that have fewer than ``min_existing``.

    Returns {artist MBID: tags} only for artists whose tag list grew: the existing tags first,
    then Discogs styles that name a genre in ``vocabulary``, up to ``limit`` in all. Cached
    artists cost no call; at most ``max_calls`` uncached artists with a known name are fetched,
    in the order given. Never raises."""
    for name, value in (("min_existing", min_existing),
                        ("limit", limit), ("max_calls", max_calls), ("workers", workers)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0 or (name == "workers" and value < 1):
            raise ValueError(f"{name} must be a non-negative integer (workers at least 1)")
    genres = {str(name).casefold() for name in vocabulary}
    if not genres:
        return {}
    token = str(discogs_token or "").strip()
    wanted = [
        mbid for mbid in dict.fromkeys(str(m) for m in artist_mbids if m)
        if len(existing_tags.get(mbid, ())) < min_existing
    ]
    cached: dict[str, list[str]] = {}
    pending: list[str] = []
    for mbid in wanted:
        try:
            value = cache_get(f"{DISCOGS_TAGS_CACHE_PREFIX}{mbid}", ttl_seconds=DISCOGS_TAGS_TTL_SECONDS)
        except Exception:
            value = None
        if isinstance(value, list):
            cached[mbid] = [str(tag) for tag in value if tag]
        elif token and str(artist_names.get(mbid) or "").strip():
            pending.append(mbid)
    pending = pending[:max_calls]

    def fetch(mbid: str):
        try:
            styles = _discogs_artist_styles(get, str(artist_names[mbid]).strip(), token, headers, timeout)
        except Exception:
            return mbid, None
        if sleep is not None:
            sleep(DISCOGS_SPACING_SECONDS)
        return mbid, styles

    if pending:
        with ThreadPoolExecutor(max_workers=min(workers, len(pending))) as pool:
            for mbid, styles in pool.map(fetch, pending):
                if styles is None:
                    continue
                cached[mbid] = styles
                try:
                    cache_set(f"{DISCOGS_TAGS_CACHE_PREFIX}{mbid}", styles)
                except Exception:
                    pass

    result: dict[str, list[str]] = {}
    for mbid in wanted:
        merged = list(existing_tags.get(mbid, ()))
        for name in cached.get(mbid, ()):
            if len(merged) >= limit:
                break
            if name in genres and name not in merged:
                merged.append(name)
        if len(merged) > len(existing_tags.get(mbid, ())):
            result[mbid] = merged
    return result
