"""MBID-keyed popularity (Last.fm listeners) for a candidate pool.

Name matching mislabels albums (brackets, curly quotes, edition suffixes), so every
lookup here is keyed by MusicBrainz identifiers:

* Last.fm ``artist.getInfo`` by artist MBID (measured: 203 of 203 candidates).
* Last.fm ``album.getInfo`` by *release* MBID. Last.fm answers "not found" to a
  release-group MBID (0 of 203), so releases are resolved first: one MusicBrainz
  release search per ``RELEASE_SEARCH_GROUPS`` release groups (``rgid:(a OR b ...)``),
  then the ListenBrainz release-group batch (``caa_release_mbid``) for groups the
  search did not cover. Measured: 166 of 203 albums found.

Pure functions over injected HTTP callables and cache callables, so tests use stubs
and never touch the network. Everything is best-effort and bounded: a failed call
leaves a candidate without a value and never raises. See docs/engine2.md.
"""
from typing import Any, Callable, Mapping

from discovery.batch_metadata import LISTENBRAINZ_RELEASE_GROUP_URL, RELEASE_GROUP_CHUNK

MUSICBRAINZ_RELEASE_SEARCH_URL = "https://musicbrainz.org/ws/2/release"
LASTFM_API_URL = "https://ws.audioscrobbler.com/2.0/"
ARTIST_CACHE_PREFIX = "popularity:lfm-artist:"
ALBUM_CACHE_PREFIX = "popularity:lfm-album:"
# Listener counts drift slowly; a miss is cached for less time so it can be retried.
POPULARITY_TTL_SECONDS = 30 * 24 * 60 * 60
MISS_TTL_SECONDS = 7 * 24 * 60 * 60
# Release groups per MusicBrainz search. Measured with 25: 100 releases per page, so
# a chunk costs one to three pages.
RELEASE_SEARCH_GROUPS = 25
RELEASE_SEARCH_PAGE = 100
MAX_RELEASE_SEARCH_PAGES = 6
# A release-search page that is rate-limited, failed with a 5xx or dropped is tried again after a
# pause, up to this many tries (measured 2026-10-24: a search right after a long run of paced calls
# returned nothing, and the third try succeeded after about 16 s).
RELEASE_SEARCH_ATTEMPTS = 3
RELEASE_SEARCH_RETRY_SECONDS = 8.0
RELEASE_SEARCH_RETRY_STATUSES = (429, 500, 502, 503, 504)
# Release MBIDs tried on Last.fm per release group (measured: 23 of 25 on the first
# try, 24 of 25 within five, 1.1 tries on average).
MAX_RELEASE_TRIES = 5
MUSICBRAINZ_SPACING_SECONDS = 1.1
LASTFM_SPACING_SECONDS = 0.27
DEFAULT_MAX_LASTFM_CALLS = 450


def _chunks(values: list, size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def order_releases(releases: list[tuple[str, str | None, str]]) -> list[str]:
    """Release MBIDs, official first, then earliest date (undated last)."""
    ranked = sorted(releases, key=lambda item: (item[1] != "Official", item[2] or "9999"))
    return [mbid for mbid, _status, _date in ranked]


def _release_search_body(
    get: Callable[..., Any], query: str, offset: int, *,
    headers: Mapping[str, str], timeout: float, sleep: Callable[[float], Any] | None,
) -> dict | None:
    """One release-search page as a body dict, or None when it failed for good.

    A rate limit, a server error or a dropped connection is tried again after a pause
    (``RELEASE_SEARCH_RETRY_SECONDS``), up to ``RELEASE_SEARCH_ATTEMPTS`` tries. Without
    ``sleep`` the retries are immediate. Never raises."""
    from recommendation_run_metrics import record_provider_call

    for attempt in range(RELEASE_SEARCH_ATTEMPTS):
        try:
            record_provider_call("musicbrainz", "release_search_batch")
            response = get(
                MUSICBRAINZ_RELEASE_SEARCH_URL,
                params={"query": query, "limit": RELEASE_SEARCH_PAGE, "offset": offset, "fmt": "json"},
                headers=dict(headers),
                timeout=timeout,
            )
        except Exception:
            response = None
        if sleep is not None:
            sleep(MUSICBRAINZ_SPACING_SECONDS)
        if response is not None:
            if response.status_code == 200:
                try:
                    body = response.json()
                except Exception:
                    return None
                return body if isinstance(body, dict) else None
            if response.status_code not in RELEASE_SEARCH_RETRY_STATUSES:
                return None
        if attempt < RELEASE_SEARCH_ATTEMPTS - 1 and sleep is not None:
            sleep(RELEASE_SEARCH_RETRY_SECONDS)
    return None


def fetch_release_mbids(
    get: Callable[..., Any],
    release_group_mbids: list[str],
    *,
    headers: Mapping[str, str],
    sleep: Callable[[float], Any] | None = None,
    timeout: float = 30,
    years: dict[str, int] | None = None,
) -> dict[str, list[str]]:
    """Return {release_group_mbid: ordered release MBIDs} from batched MusicBrainz searches.

    A page that fails for good is skipped, so the group may be missing or partial; callers fall
    back to ``fetch_representative_releases``. Rate-limited, 5xx and dropped pages are retried
    with a pause first (see ``_release_search_body``). When ``years`` is given it is filled with
    {release_group_mbid: earliest release year} from the same search, at no extra call. Never raises.
    """
    found: dict[str, list[tuple[str, str | None, str]]] = {}
    for chunk in _chunks(list(dict.fromkeys(m for m in release_group_mbids if m)), RELEASE_SEARCH_GROUPS):
        wanted = set(chunk)
        query = "rgid:(" + " OR ".join(chunk) + ")"
        for page in range(MAX_RELEASE_SEARCH_PAGES):
            body = _release_search_body(
                get, query, page * RELEASE_SEARCH_PAGE,
                headers=headers, timeout=timeout, sleep=sleep,
            )
            if body is None:
                break
            try:
                releases = body.get("releases")
                if not isinstance(releases, list):
                    break
                for release in releases:
                    group = (release.get("release-group") or {}).get("id") if isinstance(release, dict) else None
                    if group in wanted and release.get("id"):
                        found.setdefault(group, []).append(
                            (release["id"], release.get("status"), str(release.get("date") or ""))
                        )
                if (page + 1) * RELEASE_SEARCH_PAGE >= int(body.get("count") or 0):
                    break
            except Exception:
                break
    if years is not None:
        for group, items in found.items():
            dated = [int(date[:4]) for _mbid, _status, date in items if date[:4].isdigit()]
            if dated:
                years[group] = min(dated)
    return {group: order_releases(items) for group, items in found.items()}


def fetch_representative_releases(
    get: Callable[..., Any],
    release_group_mbids: list[str],
    *,
    headers: Mapping[str, str],
    timeout: float = 30,
) -> dict[str, str]:
    """Return {release_group_mbid: release MBID} from the ListenBrainz release-group batch.

    One representative release per group (the cover-art release). Cheaper than the
    MusicBrainz search but resolved on Last.fm less often (19 of 25 against 23 of 25),
    so it is the fallback. Never raises.
    """
    from recommendation_run_metrics import record_provider_call

    out: dict[str, str] = {}
    for chunk in _chunks(list(dict.fromkeys(m for m in release_group_mbids if m)), RELEASE_GROUP_CHUNK):
        try:
            record_provider_call("listenbrainz", "release_group_batch")
            response = get(
                LISTENBRAINZ_RELEASE_GROUP_URL,
                params={"release_group_mbids": ",".join(chunk), "inc": "release"},
                headers=dict(headers),
                timeout=timeout,
            )
            body = response.json() if response.status_code == 200 else None
            if not isinstance(body, dict):
                continue
            for mbid in chunk:
                entry = body.get(mbid)
                group = entry.get("release_group") if isinstance(entry, dict) else None
                release = group.get("caa_release_mbid") if isinstance(group, dict) else None
                if release:
                    out[mbid] = str(release)
        except Exception:
            continue
    return out


class _Budget:
    def __init__(self, calls: int):
        self.left = max(0, int(calls))

    def take(self) -> bool:
        if self.left <= 0:
            return False
        self.left -= 1
        return True


# Last.fm error 6 is the definitive "not found" for an MBID. Every other error
# (service offline, rate limit, temporary failure, ...) and any non-200 status
# without that error is transient and must not be cached as a miss.
LASTFM_NOT_FOUND = 6


def _lastfm_stats(get, method: str, mbid: str, api_key: str, section: str, timeout: float):
    """Return {"listeners", "playcount"}, or None for a definitive not-found.

    Raises on any transient failure so the caller leaves the value uncached.
    """
    from recommendation_run_metrics import record_provider_call

    record_provider_call("lastfm", method)
    response = get(
        LASTFM_API_URL,
        params={"method": method, "mbid": mbid, "api_key": api_key, "format": "json"},
        timeout=timeout,
    )
    body = response.json()
    if not isinstance(body, dict):
        raise RuntimeError("Last.fm returned a non-object body")
    if "error" in body:
        if body["error"] == LASTFM_NOT_FOUND:
            return None
        raise RuntimeError(f"Last.fm error {body['error']}")
    if response.status_code != 200:
        raise RuntimeError(f"Last.fm returned {response.status_code}")
    block = body.get(section)
    if not isinstance(block, dict):
        raise RuntimeError("Last.fm body has no " + section)
    stats = block.get("stats") if section == "artist" else block
    try:
        return {"listeners": int(stats["listeners"]), "playcount": int(stats.get("playcount") or 0)}
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Last.fm body has no listeners")


def _cached(cache_get, key: str):
    """Return (hit, value). A cached not-found is {"listeners": None}.

    ``MetadataCache.get`` applies one TTL per read, so a miss is read with the
    short TTL first and a found value with the long one.
    """
    value = cache_get(key, ttl_seconds=MISS_TTL_SECONDS)
    if isinstance(value, dict) and "listeners" in value:
        return True, value
    value = cache_get(key, ttl_seconds=POPULARITY_TTL_SECONDS)
    if isinstance(value, dict) and value.get("listeners") is not None:
        return True, value
    return False, None


def _store(cache_set, key: str, stats):
    cache_set(key, stats if stats else {"listeners": None})


def resolve_popularity(
    get: Callable[..., Any],
    candidates: list[Mapping[str, Any]],
    *,
    api_key: str,
    headers: Mapping[str, str],
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    sleep: Callable[[float], Any] | None = None,
    max_lastfm_calls: int = DEFAULT_MAX_LASTFM_CALLS,
    timeout: float = 30,
    with_artist_listeners: bool = True,
) -> dict[str, dict[str, Any]]:
    """Return {release_group_mbid: popularity} for candidates with MBIDs.

    ``candidates`` carry ``release_group_mbid`` and ``artist_mbid``. Each value has
    ``album_listeners`` and ``artist_listeners`` (None when unknown) and
    ``basis``: "album", "artist" (album unresolved, artist listeners usable as a
    fallback) or "none". Last.fm requests stop at ``max_lastfm_calls``; cached values
    cost nothing. Never raises. A candidate without a release-group MBID is omitted.
    ``with_artist_listeners=False`` skips the artist.getInfo calls (album listeners only).
    """
    budget = _Budget(max_lastfm_calls)
    result: dict[str, dict[str, Any]] = {}
    release_years: dict[str, int] = {}
    groups = list(dict.fromkeys(str(c["release_group_mbid"]) for c in candidates if c.get("release_group_mbid")))
    artist_of = {str(c["release_group_mbid"]): str(c["artist_mbid"]) for c in candidates
                 if c.get("release_group_mbid") and c.get("artist_mbid")}

    def lastfm(method, mbid, section):
        if not budget.take():
            return None, False
        try:
            stats = _lastfm_stats(get, method, mbid, api_key, section, timeout)
        except Exception:
            return None, False
        if sleep is not None:
            sleep(LASTFM_SPACING_SECONDS)
        return stats, True

    # Artist level (one call per distinct artist).
    artist_listeners: dict[str, int | None] = {}
    artists = dict.fromkeys(artist_of.values()) if with_artist_listeners else {}
    for artist in artists:
        hit, value = _cached(cache_get, f"{ARTIST_CACHE_PREFIX}{artist}")
        if not hit:
            stats, answered = lastfm("artist.getInfo", artist, "artist")
            if not answered:
                continue
            _store(cache_set, f"{ARTIST_CACHE_PREFIX}{artist}", stats)
            value = stats
        artist_listeners[artist] = value["listeners"] if value else None

    # Album level: cache first, then resolve releases for the groups still unknown.
    album: dict[str, int | None] = {}
    cached_years: dict[str, int | None] = {}
    pending = []
    for group in groups:
        hit, value = _cached(cache_get, f"{ALBUM_CACHE_PREFIX}{group}")
        if hit:
            album[group] = value["listeners"]
            cached_years[group] = value.get("release_year")
        else:
            pending.append(group)
    if pending and budget.left > 0:
        releases = fetch_release_mbids(
            get, pending, headers=headers, sleep=sleep, timeout=timeout, years=release_years)
        missing = [g for g in pending if g not in releases]
        if missing:
            for group, release in fetch_representative_releases(
                get, missing, headers=headers, timeout=timeout
            ).items():
                releases[group] = [release]
        for group in pending:
            stats = None
            tried = 0
            for release in releases.get(group, [])[:MAX_RELEASE_TRIES]:
                stats, answered = lastfm("album.getInfo", release, "album")
                if not answered:
                    tried = -1
                    break
                tried += 1
                if stats:
                    break
            if tried >= 0 and (stats or tried):
                # The release year rides in the album cache entry, so a cached group keeps it.
                entry = {**(stats or {"listeners": None}), "release_year": release_years.get(group)}
                _store(cache_set, f"{ALBUM_CACHE_PREFIX}{group}", entry)
                album[group] = stats["listeners"] if stats else None
                cached_years[group] = release_years.get(group)

    for group in groups:
        listeners = album.get(group)
        fallback = artist_listeners.get(artist_of.get(group, ""))
        result[group] = {
            "album_listeners": listeners,
            "release_year": cached_years.get(group) or release_years.get(group),
            "artist_listeners": fallback,
            "basis": "album" if listeners is not None else ("artist" if fallback is not None else "none"),
        }
    return result
