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
POPULARITY_CACHE_PREFIX = "lb:popularity:release-group:"
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


def _parse_counts(body: list, chunk: list[str]) -> dict[str, dict[str, Any]]:
    """Map the groups in one 200 answer that carry both counts. Raises on malformed counts."""
    counts: dict[str, dict[str, Any]] = {}
    for entry in body:
        if not isinstance(entry, dict):
            continue
        mbid = str(entry.get("release_group_mbid") or "")
        listens = entry.get("total_listen_count")
        users = entry.get("total_user_count")
        if mbid not in chunk or listens is None or users is None:
            continue
        counts[mbid] = {"listeners": int(users), "playcount": int(listens), "tags": []}
    return counts


def _store(cache_set: Callable[[str, Any], None], mbid: str, value: Any) -> None:
    try:
        cache_set(f"{POPULARITY_CACHE_PREFIX}{mbid}", value)
    except Exception:
        pass


def _split_cached(mbids, cache_get, clock) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Return (known stats, release groups that still need a request)."""
    found: dict[str, dict[str, Any]] = {}
    uncached: list[str] = []
    for mbid in dict.fromkeys(str(m) for m in mbids if m):
        try:
            cached = cache_get(f"{POPULARITY_CACHE_PREFIX}{mbid}", ttl_seconds=POPULARITY_TTL_SECONDS)
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


def fetch_release_group_popularity(
    post: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    mbids: Iterable[str],
    *,
    headers: Mapping[str, str],
    timeout: float = 15,
    clock: Callable[[], float] = time.time,
) -> dict[str, dict[str, Any]]:
    """Return {release_group_mbid: {"listeners", "playcount", "tags"}} for known groups."""
    from recommendation_run_metrics import record_provider_call

    found, uncached = _split_cached(mbids, cache_get, clock)
    for chunk in _chunks(uncached, POPULARITY_CHUNK):
        try:
            record_provider_call("listenbrainz", "popularity_batch")
            response = post(
                LISTENBRAINZ_POPULARITY_URL,
                json={"release_group_mbids": chunk},
                headers=dict(headers),
                timeout=timeout,
            )
            if response.status_code != 200:
                continue
            body = response.json()
            if not isinstance(body, list):
                continue
            # Parse the whole body before any write: a malformed body writes nothing.
            counts = _parse_counts(body, chunk)
        except Exception:
            continue
        found.update(counts)
        for mbid in chunk:
            if mbid in counts:
                _store(cache_set, mbid, counts[mbid])
            else:
                _store(cache_set, mbid, {"negative": True, "at": clock()})
    return found


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
