"""Network sections of the artist page: ``bio`` and ``missing_albums`` (contract sections 3.3 and 3.8).

The owned artist has no MBID (section 11.2), so its MusicBrainz identity is found by exact
name match. Each network section runs on its own thread under one artist-page deadline. A
section that has not finished by then is reported ``deadline``; a failed one ``source_failed``.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any

from discovery.search.cache import provider_cache_key, read_cached, write_cached
from discovery.search.index import OwnedData
from discovery.search.merge import OwnedKeys, same_entity
from discovery.search.normalize import normalize_key
from discovery.search.providers import MusicBrainzSearch
from discovery.search.runner import SEARCH_DEADLINE_SECONDS

MISSING_ALBUMS_LIMIT = 50
BIO_SOURCE = "wikidata"


@dataclass
class ArtistNetwork:
    """The network side of the artist page. Built per request; the limiter is shared."""

    musicbrainz: MusicBrainzSearch
    # Called with the release-group MBIDs and a ``can_cache`` check. The callable must not write
    # its results to a cache unless ``can_cache()`` is true at the moment of writing.
    popularity: Callable[[list[str], Callable[[], bool]], Mapping[str, Mapping[str, Any]]]
    bio: Callable[[str], str | None]
    cache_read: Callable[[str], Any]
    cache_write: Callable[[str, Any], None]
    sources: Mapping[str, dict[str, Any]] = field(default_factory=dict)
    clock: Callable[[], float] = time.monotonic
    deadline_seconds: float = SEARCH_DEADLINE_SECONDS


def _cached_records(network: ArtistNetwork, key: str, fetch, remaining, cancelled):
    """Return cached records for ``key`` or fetch and cache them. Late answers are not cached."""
    hit = read_cached(network.cache_read, key, time.time())
    if hit is not None:
        return hit
    records = fetch(remaining=remaining, cancelled=cancelled)
    if remaining() > 0 and not cancelled.is_set():
        write_cached(network.cache_write, key, records, time.time())
    return records


def resolve_identity(network: ArtistNetwork, name: str, *, remaining, cancelled) -> str | None:
    """MusicBrainz MBID of the artist with this exact normalized name, or None.

    The first exact match in MusicBrainz's own ranking is taken. The lookup shares the search
    cache entry for the same name.
    """
    key = normalize_key(name)
    records = _cached_records(
        network,
        provider_cache_key("musicbrainz", 0, key, "artist"),
        lambda remaining, cancelled: network.musicbrainz.artists(name, remaining=remaining, cancelled=cancelled),
        remaining,
        cancelled,
    )
    for record in records:
        if record["key"] == key and record["mbid"]:
            return record["mbid"]
    return None


def missing_albums(
    network: ArtistNetwork,
    name: str,
    owned: OwnedKeys,
    *,
    remaining,
    cancelled,
    progress: dict | None = None,
) -> list[dict[str, Any]]:
    """Albums MusicBrainz lists for this artist that the library does not own, most listened first.

    ``progress`` receives ``items`` as soon as the album list is known, before popularity is
    looked up, so a caller that runs out of time can still return a partial list.
    """
    mbid = resolve_identity(network, name, remaining=remaining, cancelled=cancelled)
    if mbid is None:
        return []
    albums = _cached_records(
        network,
        provider_cache_key("musicbrainz", 0, f"artist-mbid:{mbid}", "albums"),
        lambda remaining, cancelled: network.musicbrainz.albums_by_artist(
            mbid, remaining=remaining, cancelled=cancelled
        ),
        remaining,
        cancelled,
    )
    unique: list[dict[str, Any]] = []
    for album in albums:
        if owned.owns(album) or any(same_entity(album, seen) for seen in unique):
            continue
        unique.append(album)

    if progress is not None:
        progress["items"] = _shape_items(unique, {})

    def can_cache() -> bool:
        return remaining() > 0 and not cancelled.is_set()

    try:
        stats = network.popularity(
            [a["release_group_mbid"] for a in unique if a["release_group_mbid"]],
            can_cache,
        )
    except Exception:
        # Popularity only orders the list and labels its source; without it the list is still valid.
        stats = {}

    return _shape_items(unique, stats)


def _shape_items(albums: list[dict[str, Any]], stats: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Section items with ListenBrainz listen counts where known, most listened first."""
    items = []
    for album in albums:
        mbid_album = album["release_group_mbid"]
        # "playcount" is the total listen count; "listeners" is the number of users.
        listens = (stats.get(mbid_album) or {}).get("playcount") if mbid_album else None
        sources = [album["source"]] + (["listenbrainz"] if listens is not None else [])
        items.append({
            "name": album["name"],
            "year": album["year"],
            "release_group_mbid": mbid_album,
            "popularity": listens,
            "sources": sources,
        })
    items.sort(key=lambda i: (
        -(i["popularity"] if i["popularity"] is not None else -1),
        i["year"] is None,
        i["year"] or 0,
        i["name"].casefold(),
    ))
    return items[:MISSING_ALBUMS_LIMIT]


def _available(name: str, payload_key: str, payload: Any) -> dict[str, Any]:
    return {"section": name, "available": True, "complete": True, "reason": None, payload_key: payload}


def _incomplete(name: str, reason: str, payload_key: str) -> dict[str, Any]:
    empty = None if payload_key == "bio" else []
    return {
        "section": name, "available": False, "complete": False,
        "reason": reason, payload_key: empty,
    }


def network_sections(
    network: ArtistNetwork,
    name: str,
    owned_data: OwnedData | None,
) -> dict[str, dict[str, Any]]:
    """Run ``bio`` and ``missing_albums`` under one deadline. Returns the two section objects."""
    owned = OwnedKeys(owned_data)
    cancelled = threading.Event()
    deadline_at = network.clock() + network.deadline_seconds

    def remaining() -> float:
        return deadline_at - network.clock()

    def bio_job() -> dict[str, Any]:
        text = network.bio(name)
        if not text:
            return _available("bio", "bio", None)
        return _available("bio", "bio", {"text": text, "source": BIO_SOURCE})

    progress: dict[str, Any] = {}

    def missing_job() -> dict[str, Any]:
        items = missing_albums(network, name, owned, remaining=remaining, cancelled=cancelled, progress=progress)
        return _available("missing_albums", "items", items)

    jobs = {"bio": ("bio", bio_job), "missing_albums": ("items", missing_job)}
    pool = ThreadPoolExecutor(max_workers=len(jobs))
    try:
        futures = {section: pool.submit(job) for section, (_, job) in jobs.items()}
        results = {}
        for section, future in futures.items():
            payload_key = jobs[section][0]
            try:
                results[section] = future.result(timeout=max(0.0, remaining()))
            except FutureTimeout:
                if section == "missing_albums" and "items" in progress:
                    # The album list was known in time; only popularity was still pending.
                    results[section] = {
                        "section": section, "available": True, "complete": False,
                        "reason": "deadline", "items": progress["items"],
                    }
                else:
                    results[section] = _incomplete(section, "deadline", payload_key)
            except Exception:
                results[section] = _incomplete(section, "source_failed", payload_key)
    finally:
        cancelled.set()
        pool.shutdown(wait=False, cancel_futures=True)
    return results
