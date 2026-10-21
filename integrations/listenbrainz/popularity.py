"""Batched ListenBrainz release-group popularity for the recommendation ranking pass.

Replaces the per-album Last.fm ``album.getInfo`` calls: one POST per chunk of release
groups returns listen and user counts. Best-effort and never raises; a release group
that is missing, null or fails to load simply gets no popularity bonus, like a Last.fm
miss did. Counts are stored under the existing ``listeners`` (user count) and
``playcount`` (listen count) names so the bounded bonus formula is unchanged.
"""
from typing import Any, Callable, Iterable, Mapping

LISTENBRAINZ_POPULARITY_URL = "https://api.listenbrainz.org/1/popularity/release-group"
POPULARITY_CACHE_PREFIX = "lb:popularity:release-group:"
POPULARITY_TTL_SECONDS = 30 * 24 * 60 * 60
# The documented cap (MAX_ITEMS_PER_GET) is not published; 50 matches the measured
# safe size of the sibling release-group metadata endpoint.
POPULARITY_CHUNK = 50


def _chunks(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def fetch_release_group_popularity(
    post: Callable[..., Any],
    cache_get: Callable[..., Any],
    cache_set: Callable[[str, Any], None],
    mbids: Iterable[str],
    *,
    headers: Mapping[str, str],
    timeout: float = 15,
) -> dict[str, dict[str, Any]]:
    """Return {release_group_mbid: {"listeners", "playcount", "tags"}} for known groups."""
    from recommendation_run_metrics import record_provider_call

    found: dict[str, dict[str, Any]] = {}
    uncached: list[str] = []
    for mbid in dict.fromkeys(str(m) for m in mbids if m):
        try:
            known = cache_get(f"{POPULARITY_CACHE_PREFIX}{mbid}", ttl_seconds=POPULARITY_TTL_SECONDS)
        except Exception:
            known = None
        if known is not None:
            found[mbid] = known
        else:
            uncached.append(mbid)

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
            for entry in body:
                if not isinstance(entry, dict):
                    continue
                mbid = str(entry.get("release_group_mbid") or "")
                listens = entry.get("total_listen_count")
                users = entry.get("total_user_count")
                if mbid not in chunk or listens is None or users is None:
                    continue
                stats = {"listeners": int(users), "playcount": int(listens), "tags": []}
                found[mbid] = stats
                try:
                    cache_set(f"{POPULARITY_CACHE_PREFIX}{mbid}", stats)
                except Exception:
                    pass
        except Exception:
            continue
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
