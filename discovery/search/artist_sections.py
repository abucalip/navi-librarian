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
from collections.abc import Callable, Iterator, Mapping
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Any

from discovery.search.cache import SIMILAR_TTL_SECONDS, provider_cache_key, read_cached, write_cached
from discovery.search.index import OwnedData
from discovery.search.merge import OwnedKeys, same_entity
from discovery.search.normalize import album_match_key, normalize_key
from discovery.search.providers import DISCOGS_ATTRIBUTION, DiscogsSearch, LastFmSearch, ListenBrainzRadio, MusicBrainzSearch, ProviderError
from discovery.search.runner import SEARCH_DEADLINE_SECONDS
from discovery.search.similar import LASTFM, LISTENBRAINZ, SIMILAR_LIMIT, fuse_similar
from discovery.search.top_songs import top_songs

MISSING_ALBUMS_LIMIT = 50
CATALOG_LIMIT = 20
BIO_SOURCE = "wikidata"
NAVIDROME_BIO_SOURCE = "navidrome"
# Tag lookups per artist page: the seed plus this many top unowned candidates (MusicBrainz is 1 req/s).
TAG_LOOKUP_LIMIT = 4
TAG_DISPLAY_LIMIT = 8
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
    # Navidrome's own biography for an artist ID (``getArtistInfo2``). Owned artists use it before
    # the Wikidata service, so the page shows the text Navidrome shows.
    navidrome_bio: Callable[[str], str | None] | None = None
    # Deezer's tracklist for ``(artist, album)``, supplied by the route adapter (it owns the HTTP client).
    deezer_tracks: Callable[[str, str], list[dict[str, Any]]] | None = None
    # The release year of ``(artist, album)`` from the catalogue lookups, supplied by the route adapter.
    album_year: Callable[[str, str], int | None] | None = None
    # Apple Music's editorial notes for ``(artist, album)``, supplied by the route adapter.
    album_description: Callable[[str, str], dict[str, Any]] | None = None
    # Last.fm, when a key is saved. ``lastfm_generation`` keys its cache entries (section 5.2).
    lastfm: LastFmSearch | None = None
    lastfm_generation: int = 0
    # ListenBrainz radio, which needs the artist's MBID. None when the source is not wired.
    listenbrainz: ListenBrainzRadio | None = None
    # Discogs styles join the shared tags when a token is saved. ``discogs_generation`` keys their cache entries.
    discogs: DiscogsSearch | None = None
    discogs_generation: int = 0
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
            provider_cache_key("lastfm", network.lastfm_generation, f"artist-top:{normalize_key(name)}", "albums-plays"),
            lambda remaining, cancelled: network.lastfm.top_albums(name, remaining=remaining, cancelled=cancelled),
            remaining,
            cancelled,
        )
    except Exception:
        return []


def _owned_match(album: dict[str, Any], owned_albums: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The owned album (an ``owned_albums`` item) a provider album describes: same name key, compatible year."""
    key = album_match_key(album["name"])
    for entry in owned_albums:
        if album_match_key(entry["name"]) == key and (
            album["year"] is None or entry["year"] is None or album["year"] == entry["year"]
        ):
            return entry
    return None


def album_catalog(
    network: ArtistNetwork,
    name: str,
    artist_id: str | None,
    owned: OwnedKeys,
    owned_albums: list[dict[str, Any]],
    *,
    remaining,
    cancelled,
    progress: dict | None = None,
    known_mbid: str | None = None,
) -> list[dict[str, Any]]:
    """Every album MusicBrainz or Last.fm lists for this artist, plus owned albums they do not list.

    Each item has ``owned``; owned items also carry the library ``id``, ``key`` and artwork. Most
    listened first (ListenBrainz). ``progress`` receives ``items`` as soon as the album list is
    known, before popularity is looked up, so a caller that runs out of time can still return a
    partial list.
    """
    mbid = resolve_identity(
        network, name, artist_id, remaining=remaining, cancelled=cancelled, known_mbid=known_mbid,
    )
    mb_albums: list[dict[str, Any]] = []
    if mbid is not None:
        mb_albums = _cached_records(
            network,
            provider_cache_key("musicbrainz", 0, f"artist-mbid:{mbid}", "studio-albums"),
            lambda remaining, cancelled: network.musicbrainz.albums_by_artist(
                mbid, remaining=remaining, cancelled=cancelled
            ),
            remaining,
            cancelled,
        )
    lastfm_albums = _lastfm_albums(network, name, remaining=remaining, cancelled=cancelled)

    unique: list[dict[str, Any]] = []
    # Last.fm lists an artist's albums most played first; that order ranks albums ListenBrainz cannot.
    lastfm_rank = {normalize_key(a["name"]): position for position, a in enumerate(lastfm_albums)}
    lastfm_plays = {normalize_key(a["name"]): a.get("playcount") for a in lastfm_albums}
    for album in [*mb_albums, *lastfm_albums]:
        match = next((seen for seen in unique if same_entity(album, seen)), None)
        if match is None:
            unique.append({**album, "sources": [album["source"]],
                           "rank": lastfm_rank.get(normalize_key(album["name"])),
                           "lastfm_plays": lastfm_plays.get(normalize_key(album["name"]))})
        elif album["source"] not in match["sources"]:
            match["sources"].append(album["source"])

    artist_key = normalize_key(name)
    seen_owned: set[str] = set()
    for album in unique:
        album["owned_flag"] = owned.owns(album)
        entry = _owned_match(album, owned_albums) if album["owned_flag"] else None
        album["owned_entry"] = entry
        if entry is not None:
            seen_owned.add(entry["key"])
    # Owned albums the providers do not list (live albums, compilations) still belong on the page.
    for entry in owned_albums:
        if entry["key"] not in seen_owned:
            unique.append({
                "name": entry["name"], "year": entry["year"], "release_group_mbid": None,
                "sources": ["navidrome"], "owned_entry": entry,
            })

    def shape(stats: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
        return _shape_items(unique, stats, artist=name, artist_key=artist_key)

    if progress is not None:
        progress["catalog"] = shape({})

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
    return shape(stats)


def unowned_only(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The ``missing_albums`` view of a catalog: albums the library does not own."""
    keep = ("name", "year", "key", "release_group_mbid", "popularity", "popularity_source", "sources")
    return [{k: item[k] for k in keep} for item in catalog if not item["owned"]][:MISSING_ALBUMS_LIMIT]


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
    """Albums MusicBrainz or Last.fm lists for this artist that the library does not own."""
    return unowned_only(album_catalog(
        network, name, artist_id, owned, [],
        remaining=remaining, cancelled=cancelled, progress=progress, known_mbid=known_mbid,
    ))


def _shape_items(
    albums: list[dict[str, Any]],
    stats: Mapping[str, Mapping[str, Any]],
    *,
    artist: str,
    artist_key: str,
) -> list[dict[str, Any]]:
    """Catalog items with ListenBrainz listen counts where known, most listened first."""
    items = []
    # Last.fm's play counts stand in only when ListenBrainz knows none of the albums: the two services
    # count on very different scales, so a list never mixes them.
    has_listenbrainz = any((stats.get(a["release_group_mbid"]) or {}).get("playcount") is not None
                           for a in albums if a["release_group_mbid"])
    for album in albums:
        mbid_album = album["release_group_mbid"]
        # "playcount" is the total listen count; "listeners" is the number of users.
        listens = (stats.get(mbid_album) or {}).get("playcount") if mbid_album else None
        listen_source = "listenbrainz" if listens is not None else None
        if listens is None and not has_listenbrainz and album.get("lastfm_plays"):
            listens, listen_source = album["lastfm_plays"], "lastfm"
        sources = list(album["sources"]) + (["listenbrainz"] if listen_source == "listenbrainz" else [])
        entry = album.get("owned_entry")
        items.append({
            "name": album["name"],
            "year": album["year"],
            "release_group_mbid": mbid_album,
            "popularity": listens,
            "popularity_source": listen_source,
            "sources": sources,
            "rank": album.get("rank"),
            "owned": bool(album.get("owned_flag")) or entry is not None,
            "artist": artist,
            "key": entry["key"] if entry else f"{artist_key}/{normalize_key(album['name'])}",
            "id": entry.get("id") if entry else None,
            "artwork_url": entry.get("artwork_url") if entry else None,
        })
    items.sort(key=lambda i: (
        -(i["popularity"] if i["popularity"] is not None else -1),
        i["rank"] is None,
        i["rank"] or 0,
        i["year"] is None,
        i["year"] or 0,
        i["name"].casefold(),
    ))
    return items


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


def _styles_for(network: ArtistNetwork, name: str, *, remaining, cancelled) -> tuple[set[str] | None, bool]:
    """Discogs styles of one artist, as ``(styles, hit_deadline)``; same failure rules as ``_tags_for``."""
    if network.discogs is None:
        return set(), False
    key = provider_cache_key("discogs", network.discogs_generation, f"artist-styles:{normalize_key(name)}", "styles")
    hit = read_cached(network.cache_read, key, time.time(), positive_ttl=TAG_TTL_SECONDS)
    if hit is not None:
        return {record["name"] for record in hit}, False
    try:
        records = network.discogs.artist_styles(name, remaining=remaining, cancelled=cancelled)
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
        complete = failed == 0
        fetched = True
    else:
        complete = True
        fetched = False

    seed_tags: set[str] = set()
    candidate_styles: dict[str, set[str]] = {}
    tags_hit_deadline = False
    if mbid:
        seed_tags, tags_hit_deadline = _tags_for(network, mbid, remaining=remaining, cancelled=cancelled)
        seed_tags = seed_tags or set()
    seed_styles, hit = _styles_for(network, name, remaining=remaining, cancelled=cancelled)
    tags_hit_deadline = tags_hit_deadline or hit
    seed_styles = seed_styles or set()
    seed_tags = seed_tags | seed_styles
    candidate_tags: dict[str, set[str]] = {}
    if seed_tags:
        # Only the top unowned candidates with an MBID are looked up; the rest have no shared-tag score.
        ranked = fuse_similar(records, name, mbid, owned, limit=SIMILAR_LIMIT)
        looked_up = [
            (item["mbid"], item["name"]) for item in ranked if not item["owned"] and item["mbid"]
        ][:TAG_LOOKUP_LIMIT]
        for candidate_mbid, candidate_name in looked_up:
            tags, hit = _tags_for(network, candidate_mbid, remaining=remaining, cancelled=cancelled)
            tags_hit_deadline = tags_hit_deadline or hit
            styles, hit = _styles_for(network, candidate_name, remaining=remaining, cancelled=cancelled)
            tags_hit_deadline = tags_hit_deadline or hit
            if styles:
                candidate_styles[candidate_mbid] = styles
            combined = (tags or set()) | (styles or set())
            if combined:
                candidate_tags[candidate_mbid] = combined

    items = fuse_similar(
        records, name, mbid, owned, seed_tags=seed_tags, candidate_tags=candidate_tags,
        seed_styles=seed_styles, candidate_styles=candidate_styles,
    )
    # Commit the fetched records only once the whole section is complete, so an incomplete
    # refresh (a rate-limited tag lookup, say) leaves the previous entry in place (contract 5.2).
    if fetched and complete and not tags_hit_deadline and remaining() > 0 and not cancelled.is_set():
        write_cached(network.cache_write, key, records, time.time())
    if complete and not tags_hit_deadline:
        return _available("similar", "items", items)
    return {
        "section": "similar", "available": True, "complete": False,
        "reason": "source_failed" if not complete else "deadline", "items": items,
    }


def _available(name: str, payload_key: str, payload: Any) -> dict[str, Any]:
    return {"section": name, "available": True, "complete": True, "reason": None, payload_key: payload}


def _incomplete(name: str, reason: str, payload_key: str) -> dict[str, Any]:
    empty = None if payload_key in ("bio", "year", "description") else []
    return {
        "section": name, "available": False, "complete": False,
        "reason": reason, payload_key: empty,
    }


def tag_items(
    network: ArtistNetwork,
    name: str,
    artist_id: str | None,
    *,
    remaining,
    cancelled,
    known_mbid: str | None = None,
    library_genre: str | None = None,
) -> dict[str, Any]:
    """The ``tags`` section: the artist's MusicBrainz tags and Discogs styles, library genre first."""
    mbid = resolve_identity(
        network, name, artist_id, remaining=remaining, cancelled=cancelled, known_mbid=known_mbid,
    )
    names: list[str] = [library_genre.casefold()] if library_genre else []
    incomplete = False
    if mbid:
        tags, hit = _tags_for(network, mbid, remaining=remaining, cancelled=cancelled)
        incomplete = incomplete or hit
        names += sorted(tags or ())
    styles, hit = _styles_for(network, name, remaining=remaining, cancelled=cancelled)
    incomplete = incomplete or hit
    names += sorted(styles or ())
    unique = list(dict.fromkeys(names))[:TAG_DISPLAY_LIMIT]
    items = [{"name": tag} for tag in unique]
    if incomplete:
        return {"section": "tags", "available": True, "complete": False, "reason": "deadline", "items": items}
    return _available("tags", "items", items)


def iter_network_sections(
    network: ArtistNetwork,
    name: str,
    artist_id: str | None,
    owned_data: OwnedData | None,
    known_mbid: str | None = None,
    owned_album_items: list[dict[str, Any]] | None = None,
    library_genre: str | None = None,
) -> dict[str, dict[str, Any]]:
    """Run ``bio``, ``tags``, ``top_songs``, ``albums``, ``missing_albums`` and ``similar`` under one deadline.

    ``albums`` and ``missing_albums`` come from one catalog fetch. Sections are yielded as they finish.
    """
    owned = OwnedKeys(owned_data)
    cancelled = threading.Event()
    deadline_at = network.clock() + network.deadline_seconds

    def remaining() -> float:
        return deadline_at - network.clock()

    def bio_job() -> dict[str, Any]:
        if artist_id and network.navidrome_bio is not None:
            try:
                owned_text = network.navidrome_bio(artist_id)
            except Exception:
                owned_text = None  # A failed Navidrome read falls back to the public bio service.
            if owned_text:
                return _available("bio", "bio", {"text": owned_text, "source": NAVIDROME_BIO_SOURCE})
        if network.lastfm is not None:
            try:
                lastfm_text = network.lastfm.artist_bio(name, remaining=remaining, cancelled=cancelled)
            except Exception:
                lastfm_text = None  # Last.fm is best effort; the public bio service is next.
            if lastfm_text:
                return _available("bio", "bio", {"text": lastfm_text, "source": LASTFM})
        text = network.bio(name)
        if not text:
            return _available("bio", "bio", None)
        return _available("bio", "bio", {"text": text, "source": BIO_SOURCE})

    progress: dict[str, Any] = {}
    identity_lock = threading.Lock()
    identity: dict[str, str | None] = {}

    def mbid_once() -> str | None:
        """The artist's MBID, looked up once for every job (three jobs asking at once would queue behind MusicBrainz's limiter)."""
        with identity_lock:
            if "mbid" not in identity:
                identity["mbid"] = resolve_identity(
                    network, name, artist_id, remaining=remaining, cancelled=cancelled, known_mbid=known_mbid,
                )
            return identity["mbid"]

    def catalog_job() -> dict[str, Any]:
        catalog = album_catalog(
            network, name, artist_id, owned, owned_album_items or [],
            remaining=remaining, cancelled=cancelled, progress=progress, known_mbid=mbid_once(),
        )
        return {"albums": catalog}

    def similar_job() -> dict[str, Any]:
        return similar_items(
            network, name, artist_id, owned,
            remaining=remaining, cancelled=cancelled, known_mbid=mbid_once(),
        )

    def tags_job() -> dict[str, Any]:
        return tag_items(
            network, name, artist_id,
            remaining=remaining, cancelled=cancelled, known_mbid=mbid_once(), library_genre=library_genre,
        )

    def top_songs_job() -> dict[str, Any]:
        return top_songs(
            network, name, artist_id, owned_data,
            mbid=mbid_once(), remaining=remaining, cancelled=cancelled,
        )

    jobs = {
        "bio": ("bio", bio_job),
        "top_songs": ("items", top_songs_job),
        "tags": ("items", tags_job),
        "catalog": ("items", catalog_job),
        "similar": ("items", similar_job),
    }
    pool = ThreadPoolExecutor(max_workers=len(jobs))
    try:
        pending = {pool.submit(job): section for section, (_, job) in jobs.items()}
        while pending:
            done, _ = wait(set(pending), timeout=max(0.0, remaining()), return_when=FIRST_COMPLETED)
            if not done:
                # The deadline passed: every section still running is reported ``deadline``.
                for section in pending.values():
                    yield from _failed_sections(section, "deadline", jobs, progress)
                return
            for future in done:
                section = pending.pop(future)
                try:
                    result = future.result()
                except Exception:
                    yield from _failed_sections(section, "source_failed", jobs, progress)
                    continue
                if section == "catalog":
                    catalog = result["albums"]
                    yield _available("albums", "items", catalog[:CATALOG_LIMIT])
                    yield _available("missing_albums", "items", unowned_only(catalog))
                else:
                    yield result
    finally:
        cancelled.set()
        pool.shutdown(wait=False, cancel_futures=True)


def _failed_sections(section: str, reason: str, jobs, progress) -> Iterator[dict[str, Any]]:
    """Section objects for a job that failed or ran out of time."""
    if section != "catalog":
        yield _incomplete(section, reason, jobs[section][0])
        return
    partial = progress.get("catalog") if reason == "deadline" else None
    for target in ("albums", "missing_albums"):
        if partial is None:
            yield _incomplete(target, reason, "items")
        else:
            # The list was known in time; only popularity was still pending.
            items = partial[:CATALOG_LIMIT] if target == "albums" else unowned_only(partial)
            yield {"section": target, "available": True, "complete": False, "reason": "deadline", "items": items}


def network_sections(*args: Any, **kwargs: Any) -> dict[str, dict[str, Any]]:
    """Every network section, collected. See ``iter_network_sections`` for the streaming form."""
    return {section["section"]: section for section in iter_network_sections(*args, **kwargs)}
