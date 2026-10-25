"""Wiring for external search: which sources are configured and how each part is fetched.

The registry and limiter are process-wide, so concurrent searches share provider calls and
one pacing policy per source. Everything per request (settings, cache access, the parts a
query needs) is built fresh by ``external_search``.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx

from discovery.search.cache import provider_cache_key
from discovery.search.events import NOT_IN_BUILD, availability
from discovery.search.limiter import SourceLimiter
from discovery.search.providers import LastFmSearch, MusicBrainzSearch
from discovery.search.runner import ExternalSearch, FetchRegistry, Part
from settings.service import lastfm_generation

MUSICBRAINZ_GENERATION = 0  # MusicBrainz has no credential (section 5.2).
LASTFM_API_KEY = "lastfm_api_key"

REGISTRY = FetchRegistry()
# MusicBrainz asks for an average of one request per second per IP; Last.fm allows about five per second.
LIMITER = SourceLimiter({"musicbrainz": 1.0, "lastfm": 0.2})

_KINDS = ("artist", "album")


def _source_capabilities(api_key: str) -> dict[str, dict[str, Any]]:
    lastfm = availability(True) if api_key else availability(False, "source_disabled")
    return {
        "navidrome": availability(True),
        "musicbrainz": availability(True),
        "lastfm": lastfm,
        "listenbrainz": availability(False, NOT_IN_BUILD),
        "discogs": availability(False, NOT_IN_BUILD),
    }


def external_search(
    *,
    settings_read: Callable[[], Mapping[str, Any]],
    cache_read: Callable[[str], Any],
    cache_write: Callable[[str, Any], None],
    http_get: Callable[..., Any] | None = None,
    registry: FetchRegistry | None = None,
    limiter: SourceLimiter | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> ExternalSearch:
    """Build the network side of one search from the saved settings."""
    settings = settings_read()
    api_key = str(settings.get(LASTFM_API_KEY) or "").strip()
    lastfm_gen = lastfm_generation(settings_read)
    get = http_get or httpx.get
    rate_limiter = limiter or LIMITER
    musicbrainz = MusicBrainzSearch(get=get, limiter=rate_limiter, pause=time.sleep)
    lastfm = LastFmSearch(get=get, limiter=rate_limiter, api_key=api_key) if api_key else None

    def parts_for(query: str, types: Sequence[str]) -> list[Part]:
        parts: list[Part] = []
        for kind in _KINDS:
            if kind not in types:
                continue
            method = "artists" if kind == "artist" else "albums"
            parts.append(Part(
                source="musicbrainz",
                kind=kind,
                key=provider_cache_key("musicbrainz", MUSICBRAINZ_GENERATION, query, kind),
                fetch=lambda remaining, cancelled, q=query, m=method: getattr(musicbrainz, m)(
                    q, remaining=remaining, cancelled=cancelled
                ),
            ))
            if lastfm is not None:
                parts.append(Part(
                    source="lastfm",
                    kind=kind,
                    key=provider_cache_key("lastfm", lastfm_gen, query, kind),
                    fetch=lambda remaining, cancelled, q=query, m=method: getattr(lastfm, m)(
                        q, remaining=remaining, cancelled=cancelled
                    ),
                ))
        return parts

    return ExternalSearch(
        parts_for=parts_for,
        sources=_source_capabilities(api_key),
        registry=registry or REGISTRY,
        cache_read=cache_read,
        cache_write=cache_write,
        clock=clock,
    )
