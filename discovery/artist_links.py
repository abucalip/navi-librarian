"""Similar-artist and collaborator links for Current tastes (Engine 2).

Similar artists come from ListenBrainz ``lb-radio/artist`` by artist MBID. Collaborators come from
the MusicBrainz artist lookup with ``inc=artist-rels``, keeping relations that link two artists
through a band, a collaboration, a production or a performance role. Each answer is cached for 90
days (an empty answer too), at most ``LINK_MAX_CALLS`` provider calls run per kind per run, and a
failed call leaves its artist uncached so a later run asks again. Never raises. Injected callables
keep tests offline. See docs/plans/engine2.md.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any
from urllib.parse import quote

from integrations.provider_gate import musicbrainz_lane

LISTENBRAINZ_RADIO_URL = "https://api.listenbrainz.org/1/lb-radio/artist/"
LISTENBRAINZ_SPACING_SECONDS = 0.5
MUSICBRAINZ_ARTIST_URL = "https://musicbrainz.org/ws/2/artist/"
SIMILAR_CACHE_PREFIX = "lb:similar:"
COLLABORATOR_CACHE_PREFIX = "mb:artist-collaborators:"
LINK_TTL_SECONDS = 90 * 24 * 60 * 60
# Similar artists kept per artist (the window weights are discounted anyway).
SIMILAR_LIMIT = 10
LINK_MAX_CALLS = 30
# MusicBrainz relation types that tie two artists together as people who made music together.
COLLABORATOR_RELATIONS = frozenset({
    "member of band", "collaboration", "producer", "performer", "vocal", "instrument",
    "supporting musician", "conductor", "arranger", "orchestrator",
})


def _lb_similar(body: Any, seed_mbid: str) -> list[str] | None:
    """Similar-artist MBIDs from a ListenBrainz radio body; None when the body is not an answer at all."""
    if not isinstance(body, Mapping):
        return None
    found: list[str] = []
    for entries in body.values():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            mbid = str(entry.get("similar_artist_mbid") or "").strip()
            if not mbid or mbid == seed_mbid or mbid in found:
                continue
            found.append(mbid)
            if len(found) >= SIMILAR_LIMIT:
                return found
    return found


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
    sleep: Callable[[float], Any] | None = None,
    spacing: float = 0.0,
    lane: Any = None,
) -> dict[str, list[str]]:
    """Shared cache-then-ask loop. ``ask`` returns the links for one artist, or None on failure.

    Spacing is ``lane`` (a slot from the shared gate before each ask) or, for a provider with
    no gate, ``sleep(spacing)`` after each ask."""
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
        if lane is not None and not lane.acquire():
            break
        asked += 1
        try:
            answer = ask(mbid)
        except Exception:
            answer = None
        if lane is None and sleep is not None:
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
    headers: Mapping[str, str] | None = None,
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    sleep: Callable[[float], Any] | None = None,
    timeout: float = 30,
) -> dict[str, list[str]]:
    """Return {artist MBID: similar artist MBIDs} from ListenBrainz radio."""
    from recommendation_run_metrics import record_provider_call

    req_headers = dict(headers or {})

    def ask(mbid: str) -> list[str] | None:
        record_provider_call("listenbrainz", "lb_radio_artist")
        response = get(
            f"{LISTENBRAINZ_RADIO_URL}{quote(mbid, safe='')}",
            params={
                "mode": "easy",
                "max_similar_artists": SIMILAR_LIMIT,
                "max_recordings_per_artist": 1,
                "pop_begin": 0,
                "pop_end": 100,
            },
            headers=req_headers,
            timeout=timeout,
        )
        if response.status_code != 200:
            return None
        return _lb_similar(response.json(), mbid)

    return _fetch_links(artist_mbids, prefix=SIMILAR_CACHE_PREFIX, cache_get=cache_get,
                        cache_set=cache_set, ask=ask, sleep=sleep, spacing=LISTENBRAINZ_SPACING_SECONDS)


def fetch_collaborators(
    get: Callable[..., Any],
    artist_mbids: Iterable[str],
    *,
    headers: Mapping[str, str],
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    lane: Any = None,
    timeout: float = 30,
) -> dict[str, list[str]]:
    """Return {artist MBID: collaborator MBIDs} from MusicBrainz artist relations (one lookup each)."""
    from recommendation_run_metrics import record_provider_call

    lane = lane or musicbrainz_lane()

    def ask(mbid: str) -> list[str] | None:
        record_provider_call("musicbrainz", "artist_rels")
        response = get(
            f"{MUSICBRAINZ_ARTIST_URL}{mbid}",
            params={"inc": "artist-rels", "fmt": "json"},
            headers=dict(headers),
            timeout=timeout,
        )
        lane.penalize_response(response)
        if response.status_code != 200:
            return None
        return _collaborators(response.json())

    return _fetch_links(artist_mbids, prefix=COLLABORATOR_CACHE_PREFIX, cache_get=cache_get,
                        cache_set=cache_set, ask=ask, lane=lane)
