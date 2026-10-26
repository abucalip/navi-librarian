"""Genre pages (contract section 3.4): owned and unowned artists and albums for one tag.

Owned items come from the owned index: an album matches when its genre equals the tag, and an
artist matches through such an album. Unowned items come from MusicBrainz tag search and, when a
Discogs token is saved, Discogs style search. Each source's records are cached for seven days under
the source's own generation (section 5.2); owned matching runs on every read. A Discogs-sourced
item carries the attribution text.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import Any

from discovery.search.cache import SIMILAR_TTL_SECONDS, genre_cache_key, read_cached, write_cached
from discovery.search.events import availability, owned_index_capability, owned_type_available
from discovery.search.index import IndexView
from discovery.search.merge import OwnedKeys, same_entity
from discovery.search.providers import (
    DISCOGS_ATTRIBUTION,
    artist_candidate,
    DiscogsSearch,
    MusicBrainzSearch,
)
from discovery.search.runner import SEARCH_DEADLINE_SECONDS

SECTION_ORDER = ("artists", "albums")
UNOWNED_LIMIT = 30


@dataclass
class GenreNetwork:
    """The network side of one genre page. Built per request; the limiter is shared."""

    musicbrainz: MusicBrainzSearch
    discogs: DiscogsSearch | None
    discogs_generation: int
    cache_read: Callable[[str], Any]
    cache_write: Callable[[str, Any], None]
    clock: Callable[[], float] = time.monotonic
    deadline_seconds: float = SEARCH_DEADLINE_SECONDS


def normalize_tag(raw: str) -> str:
    """Tags compare case-insensitively with single spaces; the result is also the cache key part."""
    return " ".join(raw.casefold().split())


def genre_capabilities(view: IndexView, network: GenreNetwork | None) -> dict[str, Any]:
    owned_ok = owned_type_available(view)
    discogs = (
        availability(True) if network is not None and network.discogs is not None
        else availability(False, "source_disabled")
    )
    network_ok = network is not None
    # A section can be served from the library or from the network, so it is unavailable only when neither works.
    section = availability(owned_ok or network_ok, view.reason)
    return {
        "sections": {name: section for name in SECTION_ORDER},
        "sources": {
            "navidrome": availability(owned_ok, view.reason),
            "musicbrainz": availability(network_ok, "not_in_this_build"),
            "discogs": discogs if network_ok else availability(False, "not_in_this_build"),
        },
        "owned_index": owned_index_capability(view),
    }


def owned_items(view: IndexView, tag: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Owned artists and albums whose albums carry ``tag`` as their genre."""
    if not owned_type_available(view) or view.data is None:
        return [], []
    albums = [a for a in view.data.albums if (a.get("genre") or "").casefold() == tag]
    artist_ids = {a["artist_id"] for a in albums}
    artists = [a for a in view.data.artists if a["id"] in artist_ids]
    artist_items = [
        {"owned": True, "id": a["id"], "key": a["key"], "name": a["name"], "mbid": a.get("mbid"),
         "sources": ["navidrome"]}
        for a in sorted(artists, key=lambda a: a["name"].casefold())
    ]
    album_items = [
        {"owned": True, "id": a["id"], "key": a["key"], "name": a["name"], "artist": a["artist"],
         "artist_key": a["artist_key"], "year": a["year"], "release_group_mbid": a.get("release_group_mbid"),
         "sources": ["navidrome"]}
        for a in sorted(albums, key=lambda a: (a["artist"].casefold(), a["name"].casefold()))
    ]
    return artist_items, album_items


def _cached(network: GenreNetwork, key: str, fetch, remaining, cancelled):
    hit = read_cached(network.cache_read, key, time.time(), positive_ttl=SIMILAR_TTL_SECONDS)
    if hit is not None:
        return hit
    records = fetch()
    if remaining() > 0 and not cancelled.is_set():
        write_cached(network.cache_write, key, records, time.time())
    return records


def _unowned(candidates_by_source: list[list[dict[str, Any]]], owned: OwnedKeys) -> list[dict[str, Any]]:
    """Interleave the sources' lists, drop owned and duplicate entities, and list each entity's sources."""
    merged: list[dict[str, Any]] = []
    longest = max((len(c) for c in candidates_by_source), default=0)
    for position in range(longest):
        for candidates in candidates_by_source:
            if position >= len(candidates):
                continue
            candidate = candidates[position]
            if owned.owns(candidate):
                continue
            match = next((m for m in merged if same_entity(m["candidate"], candidate)), None)
            if match is None:
                merged.append({"candidate": candidate, "sources": [candidate["source"]]})
            elif candidate["source"] not in match["sources"]:
                match["sources"].append(candidate["source"])
    return [_shape(m["candidate"], m["sources"]) for m in merged[:UNOWNED_LIMIT]]


def _shape(candidate: dict[str, Any], sources: list[str]) -> dict[str, Any]:
    identifier = candidate["mbid"] or candidate["release_group_mbid"] or f"{candidate['source']}:{candidate['key']}"
    item: dict[str, Any] = {
        "owned": False, "id": identifier, "key": candidate["key"], "name": candidate["name"],
        "mbid": candidate["mbid"], "sources": sources,
    }
    if candidate["type"] == "album":
        item.update({
            "artist": candidate["artist"], "artist_key": candidate["artist_key"],
            "year": candidate["year"], "release_group_mbid": candidate["release_group_mbid"],
        })
    if "discogs" in sources:
        item["attribution"] = DISCOGS_ATTRIBUTION
    return item


def _artists_from_albums(albums: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Discogs lists albums only; its artists are the album artists, most frequent first."""
    counts: dict[str, int] = {}
    names: dict[str, str] = {}
    for album in albums:
        counts[album["artist_key"]] = counts.get(album["artist_key"], 0) + 1
        names.setdefault(album["artist_key"], album["artist"])
    ordered = sorted(counts, key=lambda k: (-counts[k], k))
    return [artist_candidate("discogs", names[k], None) for k in ordered if k]


def genre_sections(
    view: IndexView, network: GenreNetwork | None, tag: str,
) -> tuple[dict[str, dict[str, Any]], bool, bool]:
    """Both section objects, ``partial`` and ``deadline_hit``. Owned items first, then the unowned ones from the network."""
    owned_artists, owned_albums = owned_items(view, tag)
    sections = {
        "artists": {"section": "artists", "available": True, "complete": True, "reason": None, "items": owned_artists},
        "albums": {"section": "albums", "available": True, "complete": True, "reason": None, "items": owned_albums},
    }
    partial = not owned_type_available(view)
    if network is None:
        return sections, partial, False

    owned = OwnedKeys(view.data if owned_type_available(view) else None)
    cancelled = threading.Event()
    deadline_at = network.clock() + network.deadline_seconds

    def remaining() -> float:
        return deadline_at - network.clock()

    def key(source: str, kind: str) -> str:
        generation = network.discogs_generation if source == "discogs" else 0
        return genre_cache_key(source, generation, tag, kind)

    def mb(kind: str, method: str):
        return _cached(
            network, key("musicbrainz", kind),
            lambda: getattr(network.musicbrainz, method)(tag, remaining=remaining, cancelled=cancelled),
            remaining, cancelled,
        )

    def discogs_albums():
        return _cached(
            network, key("discogs", "album"),
            lambda: network.discogs.style_albums(tag, remaining=remaining, cancelled=cancelled),
            remaining, cancelled,
        )

    jobs: dict[str, Callable[[], Any]] = {
        "mb_artists": lambda: mb("artist", "artists_by_tag"),
        "mb_albums": lambda: mb("album", "albums_by_tag"),
    }
    if network.discogs is not None:
        jobs["discogs_albums"] = discogs_albums
    pool = ThreadPoolExecutor(max_workers=len(jobs))
    results: dict[str, list[dict[str, Any]]] = {}
    failed: set[str] = set()
    timed_out: set[str] = set()
    try:
        futures = {name: pool.submit(job) for name, job in jobs.items()}
        for name, future in futures.items():
            try:
                results[name] = future.result(timeout=max(0.0, remaining()))
            except FutureTimeout:
                timed_out.add(name)
                results[name] = []
            except Exception:
                failed.add(name)
                results[name] = []
    finally:
        cancelled.set()
        pool.shutdown(wait=False, cancel_futures=True)

    discogs_artists = _artists_from_albums(results.get("discogs_albums", []))
    unowned = {
        "artists": _unowned([results["mb_artists"], discogs_artists], owned),
        "albums": _unowned([results["mb_albums"], results.get("discogs_albums", [])], owned),
    }
    section_jobs = {"artists": {"mb_artists", "discogs_albums"}, "albums": {"mb_albums", "discogs_albums"}}
    for name in SECTION_ORDER:
        section = sections[name]
        section["items"] = section["items"] + unowned[name]
        wanted = section_jobs[name] & set(jobs)
        if wanted & failed:
            section.update(complete=False, reason="source_failed")
        elif wanted & timed_out:
            section.update(complete=False, reason="deadline")
    partial = partial or any(s["reason"] is not None for s in sections.values())
    return sections, partial, any(s["reason"] == "deadline" for s in sections.values())


def json_sections(sections: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {n: {k: v for k, v in s.items() if k != "section"} for n, s in sections.items()}
