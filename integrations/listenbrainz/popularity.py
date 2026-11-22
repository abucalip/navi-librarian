"""Batched ListenBrainz release-group popularity for the recommendation ranking pass.

Replaces the per-album Last.fm ``album.getInfo`` calls: one POST per chunk of release
groups returns listen and user counts. Best-effort and never raises; a release group
that is missing, null or fails to load simply gets no popularity bonus, like a Last.fm
miss did. Counts are stored under the existing ``listeners`` (user count) and
``playcount`` (listen count) names so the bounded bonus formula is unchanged.

A 200 answer that has no counts for a release group is cached as a short negative entry
(``{"negative": True, "at": <time>}``), so the group is not sent again for an hour. Failed
requests and malformed bodies write nothing.
"""
import time
from typing import Any, Callable, Iterable, Mapping

LISTENBRAINZ_POPULARITY_URL = "https://api.listenbrainz.org/1/popularity/release-group"
LISTENBRAINZ_ARTIST_POPULARITY_URL = "https://api.listenbrainz.org/1/popularity/artist"
LISTENBRAINZ_TOP_RELEASE_GROUPS_URL = (
    "https://api.listenbrainz.org/1/popularity/top-release-groups-for-artist/{mbid}"
)
POPULARITY_CACHE_PREFIX = "lb:popularity:release-group:"
ARTIST_POPULARITY_CACHE_PREFIX = "lb:popularity:artist:"
TOP_RELEASE_GROUPS_CACHE_PREFIX = "lb:popularity:top-release-groups:"
POPULARITY_TTL_SECONDS = 30 * 24 * 60 * 60
# Same negative TTL as discovery/search/cache.py. Enforced from the entry's own "at" time,
# because the metadata cache only applies the 30-day positive TTL to its rows.
NEGATIVE_TTL_SECONDS = 60 * 60
# The documented cap (MAX_ITEMS_PER_GET) is not published; 50 matches the measured
# safe size of the sibling release-group metadata endpoint.
POPULARITY_CHUNK = 50

_FRESH_NEGATIVE = object()


def _chunks(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _classify_cached(value: Any, now: float) -> Any:
    """Return the stored stats, ``_FRESH_NEGATIVE`` for a fresh "no data" entry, or None."""
    if isinstance(value, dict) and value.get("negative"):
        at = value.get("at")
        if isinstance(at, (int, float)) and 0 <= now - at < NEGATIVE_TTL_SECONDS:
            return _FRESH_NEGATIVE
        return None
    return value


def _parse_counts(
    body: list,
    chunk: list[str],
    mbid_field: str = "release_group_mbid",
) -> dict[str, dict[str, Any]]:
    """Map the items in one 200 answer that carry both counts. Raises on malformed counts."""
    counts: dict[str, dict[str, Any]] = {}
    for entry in body:
        if not isinstance(entry, dict):
            continue
        mbid = str(entry.get(mbid_field) or "")
        listens = entry.get("total_listen_count")
        users = entry.get("total_user_count")
        if mbid not in chunk or listens is None or users is None:
            continue
        counts[mbid] = {"listeners": int(users), "playcount": int(listens), "tags": []}
    return counts


def _store(cache_set: Callable[[str, Any], None], key: str, value: Any) -> None:
    try:
        cache_set(key, value)
    except Exception:
        pass


def _split_cached(
    mbids: Iterable[str],
    cache_get: Callable[..., Any],
    clock: Callable[[], float],
    prefix: str = POPULARITY_CACHE_PREFIX,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Return (known stats, items that still need a request)."""
    found: dict[str, dict[str, Any]] = {}
    uncached: list[str] = []
    for mbid in dict.fromkeys(str(m) for m in mbids if m):
        try:
            cached = cache_get(f"{prefix}{mbid}", ttl_seconds=POPULARITY_TTL_SECONDS)
        except Exception:
            cached = None
        state = _classify_cached(cached, clock())
        if state is _FRESH_NEGATIVE:
            continue
        if state is not None:
            found[mbid] = state
        else:
            uncached.append(mbid)
    return found, uncached


def _fetch_batched_popularity(
    post: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    mbids: Iterable[str],
    *,
    url: str,
    payload_key: str,
    response_key: str,
    prefix: str,
    metric_label: str,
    headers: Mapping[str, str] | None,
    timeout: float,
    clock: Callable[[], float],
) -> dict[str, dict[str, Any]]:
    """Shared batched ListenBrainz popularity fetcher with 30-day cache and 1-hour negative mark."""
    from recommendation_run_metrics import record_provider_call

    found, uncached = _split_cached(mbids, cache_get, clock, prefix=prefix)
    for chunk in _chunks(uncached, POPULARITY_CHUNK):
        try:
            record_provider_call("listenbrainz", metric_label)
            response = post(
                url,
                json={payload_key: chunk},
                headers=dict(headers or {}),
                timeout=timeout,
            )
            if response.status_code != 200:
                continue
            body = response.json()
            if not isinstance(body, list):
                continue
            # Parse the whole body before any write: a malformed body writes nothing.
            counts = _parse_counts(body, chunk, mbid_field=response_key)
        except Exception:
            continue
        found.update(counts)
        for mbid in chunk:
            if mbid in counts:
                _store(cache_set, f"{prefix}{mbid}", counts[mbid])
            else:
                _store(cache_set, f"{prefix}{mbid}", {"negative": True, "at": clock()})
    return found


def fetch_release_group_popularity(
    post: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    mbids: Iterable[str],
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 15,
    clock: Callable[[], float] = time.time,
) -> dict[str, dict[str, Any]]:
    """Return {release_group_mbid: {"listeners", "playcount", "tags"}} for known groups."""
    return _fetch_batched_popularity(
        post,
        cache_get,
        cache_set,
        mbids,
        url=LISTENBRAINZ_POPULARITY_URL,
        payload_key="release_group_mbids",
        response_key="release_group_mbid",
        prefix=POPULARITY_CACHE_PREFIX,
        metric_label="popularity_batch",
        headers=headers,
        timeout=timeout,
        clock=clock,
    )


def fetch_artist_popularity(
    post: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    mbids: Iterable[str],
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 15,
    clock: Callable[[], float] = time.time,
) -> dict[str, dict[str, Any]]:
    """Return {artist_mbid: {"listeners", "playcount", "tags"}} for known artists."""
    return _fetch_batched_popularity(
        post,
        cache_get,
        cache_set,
        mbids,
        url=LISTENBRAINZ_ARTIST_POPULARITY_URL,
        payload_key="artist_mbids",
        response_key="artist_mbid",
        prefix=ARTIST_POPULARITY_CACHE_PREFIX,
        metric_label="artist_popularity_batch",
        headers=headers,
        timeout=timeout,
        clock=clock,
    )


def _parse_top_release_groups(body: list) -> list[dict[str, Any]]:
    """Parse ListenBrainz top-release-groups-for-artist response into normalized dicts."""
    items: list[dict[str, Any]] = []
    for entry in body:
        if not isinstance(entry, dict):
            continue
        mbid = str(entry.get("release_group_mbid") or "")
        if not mbid:
            continue
        listens = entry.get("total_listen_count")
        users = entry.get("total_user_count")
        items.append({
            "release_group_mbid": mbid,
            "name": str(entry.get("release_group_name") or ""),
            "listeners": int(users) if users is not None else 0,
            "playcount": int(listens) if listens is not None else 0,
        })
    return items


def fetch_artist_top_release_groups(
    get: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    artist_mbid: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout: float = 15,
    clock: Callable[[], float] = time.time,
) -> list[dict[str, Any]]:
    """Return top release groups for ``artist_mbid`` from ListenBrainz, cached 30 days."""
    from recommendation_run_metrics import record_provider_call

    mbid = str(artist_mbid or "").strip()
    if not mbid:
        return []
    cache_key = f"{TOP_RELEASE_GROUPS_CACHE_PREFIX}{mbid}"
    try:
        cached = cache_get(cache_key, ttl_seconds=POPULARITY_TTL_SECONDS)
    except Exception:
        cached = None
    state = _classify_cached(cached, clock())
    if state is _FRESH_NEGATIVE:
        return []
    if isinstance(state, list):
        return state

    try:
        record_provider_call("listenbrainz", "artist_top_release_groups")
        response = get(
            LISTENBRAINZ_TOP_RELEASE_GROUPS_URL.format(mbid=mbid),
            headers=dict(headers or {}),
            timeout=timeout,
        )
        if response.status_code != 200:
            return []
        body = response.json()
        if not isinstance(body, list):
            return []
        items = _parse_top_release_groups(body)
    except Exception:
        return []

    if items:
        _store(cache_set, cache_key, items)
    else:
        _store(cache_set, cache_key, {"negative": True, "at": clock()})
    return items


def build_popularity_lookup(
    candidates: Iterable[Mapping[str, Any]],
    limit: int,
    fetch: Callable[[list[str]], Mapping[str, Mapping[str, Any]]],
    music_key: Callable[[Any], str],
) -> Callable[[str, str], Mapping[str, Any] | None]:
    """Fetch popularity for the top ``limit`` candidates once; return an (artist, album) lookup."""
    top = sorted(candidates, key=lambda c: c["discovery_score"], reverse=True)[:limit]
    mbids = [c["release_group_mbid"] for c in top if c.get("release_group_mbid")]
    stats = fetch(mbids) if mbids else {}
    by_identity = {
        (music_key(c.get("primary_artist") or c.get("artist", "")), music_key(c.get("album", ""))):
            stats.get(c.get("release_group_mbid"))
        for c in top if c.get("release_group_mbid")
    }

    def lookup(artist: str, album: str):
        return by_identity.get((music_key(artist), music_key(album)))

    return lookup
