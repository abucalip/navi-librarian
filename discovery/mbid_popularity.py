"""MBID-keyed popularity (ListenBrainz listeners) for a candidate pool.

Every lookup here is keyed directly by MusicBrainz identifiers via ListenBrainz's
batched popularity endpoints:

* ``POST /1/popularity/release-group`` (``fetch_release_group_popularity``) for album
  listeners, keyed by release-group MBID directly (no MusicBrainz release-search
  indirection needed).
* ``POST /1/popularity/artist`` (``fetch_artist_popularity``) for artist listeners,
  used as a fallback when ``with_artist_listeners=True``.

Pure functions over injected HTTP and cache callables, so tests use stubs and never
touch the network. Everything is best-effort and bounded: a failed call leaves a
candidate without a value and never raises.
"""
import time
from typing import Any, Callable, Mapping

from integrations.listenbrainz.popularity import (
    fetch_artist_popularity,
    fetch_release_group_popularity,
)


def resolve_popularity(
    post: Callable[..., Any],
    candidates: list[Mapping[str, Any]],
    *,
    headers: Mapping[str, str] | None = None,
    cache_get: Callable[..., Any],
    cache_set: Callable[..., Any],
    timeout: float = 15,
    with_artist_listeners: bool = True,
    clock: Callable[[], float] = time.time,
) -> dict[str, dict[str, Any]]:
    """Return {release_group_mbid: popularity} for candidates with MBIDs.

    ``candidates`` carry ``release_group_mbid`` and ``artist_mbid``. Each value has
    ``album_listeners`` and ``artist_listeners`` (None when unknown), ``release_year``
    (None), and ``basis``: "album", "artist" (album unresolved, artist listeners usable
    as a fallback) or "none". Never raises. A candidate without a release-group MBID is
    omitted. ``with_artist_listeners=False`` skips the artist popularity batch.
    """
    groups = list(dict.fromkeys(
        str(c["release_group_mbid"]) for c in candidates if c.get("release_group_mbid")
    ))
    if not groups:
        return {}
    artist_of = {
        str(c["release_group_mbid"]): str(c["artist_mbid"])
        for c in candidates
        if c.get("release_group_mbid") and c.get("artist_mbid")
    }

    album_stats = fetch_release_group_popularity(
        post, cache_get, cache_set, groups, headers=headers, timeout=timeout, clock=clock,
    )
    artists = list(dict.fromkeys(artist_of.values())) if with_artist_listeners else []
    artist_stats = (
        fetch_artist_popularity(
            post, cache_get, cache_set, artists, headers=headers, timeout=timeout, clock=clock,
        )
        if artists else {}
    )

    result: dict[str, dict[str, Any]] = {}
    for group in groups:
        album_entry = album_stats.get(group)
        listeners = album_entry["listeners"] if isinstance(album_entry, Mapping) else None
        artist_entry = artist_stats.get(artist_of.get(group, ""))
        fallback = artist_entry["listeners"] if isinstance(artist_entry, Mapping) else None
        result[group] = {
            "album_listeners": listeners,
            "release_year": None,
            "artist_listeners": fallback,
            "basis": "album" if listeners is not None else ("artist" if fallback is not None else "none"),
        }
    return result
