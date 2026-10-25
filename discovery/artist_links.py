"""Similar-artist and collaborator links for Current tastes (Engine 2).

Similar artists come from Last.fm ``artist.getSimilar`` by artist MBID. Collaborators come from the
MusicBrainz artist lookup with ``inc=artist-rels``, keeping relations that link two artists through
a band, a collaboration, a production or a performance role. Each answer is cached for 90 days (an
empty answer too), at most ``LINK_MAX_CALLS`` provider calls run per kind per run, and a failed
call leaves its artist uncached so a later run asks again. Never raises. Injected callables keep
tests offline. See docs/engine2.md.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from discovery.artist_tag_fallback import LASTFM_API_URL
from discovery.mbid_popularity import LASTFM_SPACING_SECONDS, MUSICBRAINZ_SPACING_SECONDS

MUSICBRAINZ_ARTIST_URL = "https://musicbrainz.org/ws/2/artist/"
SIMILAR_CACHE_PREFIX = "lastfm:similar:"
COLLABORATOR_CACHE_PREFIX = "mb:artist-collaborators:"
LINK_TTL_SECONDS = 90 * 24 * 60 * 60
# Similar artists kept per artist (Last.fm returns more; the window weights are discounted anyway).
SIMILAR_LIMIT = 10
LINK_MAX_CALLS = 30
# MusicBrainz relation types that tie two artists together as people who made music together.
COLLABORATOR_RELATIONS = frozenset({
    "member of band", "collaboration", "producer", "performer", "vocal", "instrument",
    "supporting musician", "conductor", "arranger", "orchestrator",
})


def _lastfm_similar(body: Any) -> list[str] | None:
    """Similar-artist MBIDs from a Last.fm body; None when the body is not an answer at all."""
    if not isinstance(body, Mapping) or "error" in body:
        return None
    block = body.get("similarartists")
    artists = block.get("artist") if isinstance(block, Mapping) else None
    if not isinstance(artists, list):
        return None
    return [str(item["mbid"]) for item in artists
            if isinstance(item, Mapping) and item.get("mbid")][:SIMILAR_LIMIT]


def _collaborators(body: Any) -> list[str] | None:
    """Collaborator artist MBIDs from a MusicBrainz artist body; None when it is not an answer."""
    if not isinstance(body, Mapping):
        return None
    relations = body.get("relations")
    if not isinstance(relations, list):
        return None
    found: list[str] = []
    for relation in relations:
        if not isinstance(relation, Mapping) or relation.get("target-type") != "artist":
            continue
        if relation.get("type") not in COLLABORATOR_RELATIONS:
            continue
        target = relation.get("artist")
        mbid = str(target.get("id") or "") if isinstance(target, Mapping) else ""
        if mbid and mbid not in found:
            found.append(mbid)
    return found


def _fetch_links(
    mbids: Iterable[str],
    *,
    prefix: str,
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    ask: Callable[[str], list[str] | None],
    sleep: Callable[[float], Any] | None,
    spacing: float,
) -> dict[str, list[str]]:
    """Shared cache-then-ask loop. ``ask`` returns the links for one artist, or None on failure."""
    links: dict[str, list[str]] = {}
    asked = 0
    for mbid in dict.fromkeys(str(m) for m in mbids if m):
        try:
            cached = cache_get(f"{prefix}{mbid}", ttl_seconds=LINK_TTL_SECONDS)
        except Exception:
            cached = None
        if isinstance(cached, list):
            links[mbid] = [str(item) for item in cached]
            continue
        if asked >= LINK_MAX_CALLS:
            continue
        asked += 1
        try:
            answer = ask(mbid)
        except Exception:
            answer = None
        if sleep is not None:
            sleep(spacing)
        if answer is None:
            continue
        links[mbid] = answer
        try:
            cache_set(f"{prefix}{mbid}", answer)
        except Exception:
            pass
    return links


def fetch_similar_artists(
    get: Callable[..., Any],
    artist_mbids: Iterable[str],
    *,
    api_key: str,
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    sleep: Callable[[float], Any] | None = None,
    timeout: float = 30,
) -> dict[str, list[str]]:
    """Return {artist MBID: similar artist MBIDs} from Last.fm. Without an API key nothing is asked."""
    from recommendation_run_metrics import record_provider_call

    if not api_key:
        return {}

    def ask(mbid: str) -> list[str] | None:
        record_provider_call("lastfm", "artist.getSimilar")
        response = get(
            LASTFM_API_URL,
            params={"method": "artist.getSimilar", "mbid": mbid, "limit": SIMILAR_LIMIT,
                    "api_key": api_key, "format": "json"},
            timeout=timeout,
        )
        if response.status_code != 200:
            return None
        return _lastfm_similar(response.json())

    return _fetch_links(artist_mbids, prefix=SIMILAR_CACHE_PREFIX, cache_get=cache_get,
                        cache_set=cache_set, ask=ask, sleep=sleep, spacing=LASTFM_SPACING_SECONDS)


def fetch_collaborators(
    get: Callable[..., Any],
    artist_mbids: Iterable[str],
    *,
    headers: Mapping[str, str],
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    sleep: Callable[[float], Any] | None = None,
    timeout: float = 30,
) -> dict[str, list[str]]:
    """Return {artist MBID: collaborator MBIDs} from MusicBrainz artist relations (one lookup each)."""
    from recommendation_run_metrics import record_provider_call

    def ask(mbid: str) -> list[str] | None:
        record_provider_call("musicbrainz", "artist_rels")
        response = get(
            f"{MUSICBRAINZ_ARTIST_URL}{mbid}",
            params={"inc": "artist-rels", "fmt": "json"},
            headers=dict(headers),
            timeout=timeout,
        )
        if response.status_code != 200:
            return None
        return _collaborators(response.json())

    return _fetch_links(artist_mbids, prefix=COLLABORATOR_CACHE_PREFIX, cache_get=cache_get,
                        cache_set=cache_set, ask=ask, sleep=sleep, spacing=MUSICBRAINZ_SPACING_SECONDS)
