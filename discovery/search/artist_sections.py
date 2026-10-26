"""Network sections of the artist page: ``bio`` and ``missing_albums`` (contract sections 3.3 and 3.8).

Identity: the owned artist's MusicBrainz MBID comes from Navidrome when the library tags it
(``getArtist``), and otherwise from an exact name match. Albums come from MusicBrainz and
Last.fm, deduplicated; the list is ordered by ListenBrainz listen counts.

Each network section runs on its own thread under one artist-page deadline. A section that has
not finished by then is reported ``deadline``; a failed one ``source_failed``.

``similar`` fuses Last.fm and ListenBrainz radio (contract section 7). Its raw records are cached
for seven days; owned filtering runs on every read.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Any

from discovery.search.cache import SIMILAR_TTL_SECONDS, provider_cache_key, read_cached, write_cached
from discovery.search.index import OwnedData
from discovery.search.merge import OwnedKeys, same_entity
from discovery.search.normalize import normalize_key
from discovery.search.providers import LastFmSearch, ListenBrainzRadio, MusicBrainzSearch, ProviderError
from discovery.search.runner import SEARCH_DEADLINE_SECONDS
from discovery.search.similar import LASTFM, LISTENBRAINZ, SIMILAR_LIMIT, fuse_similar

MISSING_ALBUMS_LIMIT = 50
BIO_SOURCE = "wikidata"
# Tag lookups per artist page: the seed plus this many top unowned candidates (MusicBrainz is 1 req/s).
TAG_LOOKUP_LIMIT = 10
TAG_TTL_SECONDS = 30 * 24 * 60 * 60


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
    # Navidrome's MBID for an artist ID, or None when the library does not tag it.
    navidrome_mbid: Callable[[str], str | None] | None = None
    # Last.fm, when a key is saved. ``lastfm_generation`` keys its cache entries (section 5.2).
    lastfm: LastFmSearch | None = None
    lastfm_generation: int = 0
    # ListenBrainz radio, which needs the artist's MBID. None when the source is not wired.
    listenbrainz: ListenBrainzRadio | None = None
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


def resolve_identity(
    network: ArtistNetwork,
    name: str,
    artist_id: str | None,
    *,
    remaining,
    cancelled,
    known_mbid: str | None = None,
) -> str | None:
    """The artist's MBID: the stored identity when known, else Navidrome's tag, else the first
    exact-name MusicBrainz match.

    The name lookup shares the search cache entry for the same name.
    """
    if known_mbid:
        return known_mbid
    if network.navidrome_mbid is not None and artist_id:
        try:
            tagged = network.navidrome_mbid(artist_id)
        except Exception:
            tagged = None  # A failed tag read falls back to the name lookup.
        if tagged:
            return tagged

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


def _lastfm_albums(network: ArtistNetwork, name: str, *, remaining, cancelled) -> list[dict[str, Any]]:
    """Last.fm's top albums for the artist. Best effort: a failure contributes no albums."""
    if network.lastfm is None:
        return []
    try:
        return _cached_records(
            network,
            provider_cache_key("lastfm", network.lastfm_generation, f"artist-top:{normalize_key(name)}", "albums"),
            lambda remaining, cancelled: network.lastfm.top_albums(name, remaining=remaining, cancelled=cancelled),
            remaining,
            cancelled,
        )
    except Exception:
        return []


def missing_albums(
    network: ArtistNetwork,
    name: str,
    artist_id: str | None,
    owned: OwnedKeys,
    *,
    remaining,
    cancelled,
    progress: dict | None = None,
    known_mbid: str | None = None,
) -> list[dict[str, Any]]:
    """Albums MusicBrainz or Last.fm lists for this artist that the library does not own.

    Most listened first. ``progress`` receives ``items`` as soon as the album list is known,
    before popularity is looked up, so a caller that runs out of time can still return a
    partial list.
    """
    mbid = resolve_identity(
        network, name, artist_id, remaining=remaining, cancelled=cancelled, known_mbid=known_mbid,
    )
    mb_albums: list[dict[str, Any]] = []
    if mbid is not None:
        mb_albums = _cached_records(
            network,
            provider_cache_key("musicbrainz", 0, f"artist-mbid:{mbid}", "albums"),
            lambda remaining, cancelled: network.musicbrainz.albums_by_artist(
                mbid, remaining=remaining, cancelled=cancelled
            ),
            remaining,
            cancelled,
        )
    lastfm_albums = _lastfm_albums(network, name, remaining=remaining, cancelled=cancelled)

    unique: list[dict[str, Any]] = []
    for album in [*mb_albums, *lastfm_albums]:
        if owned.owns(album):
            continue
        match = next((seen for seen in unique if same_entity(album, seen)), None)
        if match is None:
            unique.append({**album, "sources": [album["source"]]})
        elif album["source"] not in match["sources"]:
            match["sources"].append(album["source"])

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
        sources = list(album["sources"]) + (["listenbrainz"] if listens is not None else [])
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


def _tags_for(network: ArtistNetwork, mbid: str, *, remaining, cancelled) -> tuple[set[str] | None, bool]:
    """MusicBrainz tags for one MBID, as ``(tags, hit_deadline)``.

    ``tags`` is None when the lookup failed; a failure contributes no tags and is not cached.
    ``hit_deadline`` is True when the call was rate-limited, so the section is incomplete.
    """
    key = provider_cache_key("musicbrainz", 0, f"artist-tags:{mbid}", "tags")
    hit = read_cached(network.cache_read, key, time.time(), positive_ttl=TAG_TTL_SECONDS)
    if hit is not None:
        return {record["name"] for record in hit}, False
    try:
        records = network.musicbrainz.artist_tags(mbid, remaining=remaining, cancelled=cancelled)
    except ProviderError as exc:
        return None, exc.state == "rate_limited"
    except Exception:
        return None, False
    if remaining() > 0 and not cancelled.is_set():
        write_cached(network.cache_write, key, records, time.time())
    return {record["name"] for record in records}, False


def similar_items(
    network: ArtistNetwork,
    name: str,
    artist_id: str | None,
    owned: OwnedKeys,
    *,
    remaining,
    cancelled,
    known_mbid: str | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """The ``similar`` section object. Raises when no source produced an answer.

    A source that fails while another answers gives a partial section (``source_failed``, with
    the other source's items). Only a complete fetch is cached, so a failure is never a hit.
    Shared tags (MusicBrainz) add to the ranking; a tag lookup rate-limited or out of time makes
    the section incomplete with reason ``deadline``. ``refresh`` skips the cached records (used
    by the daily precompute).
    """
    mbid = resolve_identity(
        network, name, artist_id, remaining=remaining, cancelled=cancelled, known_mbid=known_mbid,
    )
    key = f"similar:{mbid or 'none'}:{normalize_key(name)}:lastfm{network.lastfm_generation}:listenbrainz0"
    records = None if refresh else read_cached(
        network.cache_read, key, time.time(), positive_ttl=SIMILAR_TTL_SECONDS,
    )
    if records is None:
        records, failed, attempted = [], 0, 0
        if network.lastfm is not None:
            attempted += 1
            try:
                records += [
                    {"source": LASTFM, **record}
                    for record in network.lastfm.similar(name, remaining=remaining, cancelled=cancelled)
                ]
            except Exception:
                failed += 1
        if network.listenbrainz is not None and mbid:
            attempted += 1
            try:
                records += [
                    {"source": LISTENBRAINZ, **record}
                    for record in network.listenbrainz.similar(mbid, remaining=remaining, cancelled=cancelled)
                ]
            except Exception:
                failed += 1
        if attempted == 0:
            # No source can answer for this artist (no Last.fm key, and no MBID for radio).
            return {"section": "similar", "available": False, "complete": False,
                    "reason": "source_disabled", "items": []}
        if failed == attempted:
            raise ProviderError("failed")
        if failed == 0 and remaining() > 0 and not cancelled.is_set():
            write_cached(network.cache_write, key, records, time.time())
        complete = failed == 0
    else:
        complete = True

    seed_tags: set[str] = set()
    tags_hit_deadline = False
    if mbid:
        seed_tags, tags_hit_deadline = _tags_for(network, mbid, remaining=remaining, cancelled=cancelled)
        seed_tags = seed_tags or set()
    candidate_tags: dict[str, set[str]] = {}
    if seed_tags:
        # Only the top unowned candidates with an MBID are looked up; the rest have no shared-tag score.
        ranked = fuse_similar(records, name, mbid, owned, limit=SIMILAR_LIMIT)
        looked_up = [
            item["mbid"] for item in ranked if not item["owned"] and item["mbid"]
        ][:TAG_LOOKUP_LIMIT]
        for candidate_mbid in looked_up:
            tags, hit = _tags_for(network, candidate_mbid, remaining=remaining, cancelled=cancelled)
            tags_hit_deadline = tags_hit_deadline or hit
            if tags:
                candidate_tags[candidate_mbid] = tags

    items = fuse_similar(
        records, name, mbid, owned, seed_tags=seed_tags, candidate_tags=candidate_tags,
    )
    if complete and not tags_hit_deadline:
        return _available("similar", "items", items)
    return {
        "section": "similar", "available": True, "complete": False,
        "reason": "source_failed" if not complete else "deadline", "items": items,
    }


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
    artist_id: str | None,
    owned_data: OwnedData | None,
    known_mbid: str | None = None,
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
        items = missing_albums(
            network, name, artist_id, owned,
            remaining=remaining, cancelled=cancelled, progress=progress, known_mbid=known_mbid,
        )
        return _available("missing_albums", "items", items)

    def similar_job() -> dict[str, Any]:
        return similar_items(
            network, name, artist_id, owned,
            remaining=remaining, cancelled=cancelled, known_mbid=known_mbid,
        )

    jobs = {
        "bio": ("bio", bio_job),
        "missing_albums": ("items", missing_job),
        "similar": ("items", similar_job),
    }
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
