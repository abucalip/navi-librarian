"""Album page sections: ``album``, ``year``, ``genre``, ``description``, ``tracks``, ``similar_artists`` and ``similar_albums``.

The tracklist comes from a race between the providers that can supply one (Deezer, Last.fm,
MusicBrainz): the first non-empty answer wins, so the page waits for the fastest source rather
than the best one. Each track is marked ``owned`` against the library's songs for that album
(by title, or by track number and length), and library songs the provider does not list are
appended as owned. When no provider answers, an owned album falls back to the library's own
tracklist. Sections are yielded as they finish, so the album header never waits for the network.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Iterator
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from typing import Any

from discovery.search.artist_sections import (
    ArtistNetwork,
    _available,
    _cached_records,
    _incomplete,
    _lastfm_albums,
    resolve_identity,
    similar_items,
    tag_items,
)
from discovery.search.cache import provider_cache_key
from discovery.search.index import OwnedData
from discovery.search.merge import OwnedKeys
from discovery.search.normalize import normalize_key
from discovery.search.quality_label import quality_label
from discovery.search.query import artwork_url

ALBUM_SECTION_ORDER = ("album", "year", "genre", "description", "tracks", "similar_artists", "similar_albums")
# A provider track and a library song with the same number and a length within this many seconds are one track.
TRACK_LENGTH_TOLERANCE_SECONDS = 3
SIMILAR_ALBUM_ARTISTS = 6
SIMILAR_ALBUM_LIMIT = 12


def _payload_key(section: str) -> str:
    return section if section in ("year", "genre", "description") else "items"


def find_album(data: OwnedData, artist_key: str, album_key: str, album_id: str | None) -> dict[str, Any] | None:
    """The owned album for a route key; a Navidrome ID breaks ties between albums sharing one."""
    if album_id:
        # A Navidrome ID names the album exactly, even when the song's artist differs from the album's.
        by_id = next((a for a in data.albums if a["id"] == album_id), None)
        if by_id is not None:
            return by_id
    matches = [a for a in data.albums if a["key"] == f"{artist_key}/{album_key}"]
    return matches[0] if matches else None


def _with_quality(track: dict[str, Any], song: dict[str, Any]) -> dict[str, Any]:
    """The track with the song file's quality tag when it has one; the key is absent otherwise."""
    label = quality_label(song.get("suffix"), song.get("bit_rate"), song.get("bit_depth"), song.get("sampling_rate"))
    return {**track, "quality": label} if label else track


def owned_tracks(data: OwnedData, album_id: str) -> list[dict[str, Any]]:
    songs = sorted(
        (s for s in data.songs if s["album_id"] == album_id),
        key=lambda s: (s["track_number"] is None, s["track_number"] or 0, s["name"].casefold()),
    )
    return [
        _with_quality({"track_number": s["track_number"] or index + 1, "title": s["name"],
                       "duration_seconds": s["duration"] or 0, "owned": True}, s)
        for index, s in enumerate(songs)
    ]


def mark_owned_tracks(provider: list[dict[str, Any]], songs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The provider's tracklist with ``owned`` on each track, plus library songs it does not list.

    ``songs`` are the library's songs for this album. A track is owned when a song has the same
    normalized title, or the same track number and a length within a few seconds (remasters
    rename tracks but keep their place). Songs matching no track are appended as owned.
    """
    unmatched = list(songs)
    matched: dict[int, dict[str, Any]] = {}
    for index, track in enumerate(provider):
        key = normalize_key(track["title"])
        song = next((s for s in unmatched if s["name_key"] == key), None)
        if song is not None:
            unmatched.remove(song)
            matched[index] = song
    for index, track in enumerate(provider):
        if index in matched or not track.get("duration_seconds"):
            continue
        song = next((
            s for s in unmatched
            if s["track_number"] == track["track_number"] and s["duration"]
            and abs(s["duration"] - track["duration_seconds"]) <= TRACK_LENGTH_TOLERANCE_SECONDS
        ), None)
        if song is not None:
            unmatched.remove(song)
            matched[index] = song
    items = [
        _with_quality({**track, "owned": True}, matched[index]) if index in matched else {**track, "owned": False}
        for index, track in enumerate(provider)
    ]
    extras = sorted(unmatched, key=lambda s: (s["track_number"] is None, s["track_number"] or 0, s["name"].casefold()))
    for song in extras:
        items.append(_with_quality({
            "track_number": song["track_number"] or len(items) + 1,
            "title": song["name"], "duration_seconds": song["duration"] or 0, "owned": True,
        }, song))
    return items


def race_tracks(
    network: ArtistNetwork, artist: str, album: str, release_group_mbid: str | None, *, remaining, cancelled,
) -> list[dict[str, Any]]:
    """The first non-empty tracklist from any source; cached for a week once found."""
    key = provider_cache_key("tracks", 0, f"{normalize_key(artist)}/{normalize_key(album)}", "tracks")
    hit = _read_tracks(network, key)
    if hit is not None:
        return hit

    attempts = []
    if network.deezer_tracks is not None:
        attempts.append(lambda: network.deezer_tracks(artist, album))
    if network.lastfm is not None:
        attempts.append(lambda: network.lastfm.album_tracks(artist, album, remaining=remaining, cancelled=cancelled))
    if release_group_mbid:
        attempts.append(lambda: network.musicbrainz.release_group_tracks(
            release_group_mbid, remaining=remaining, cancelled=cancelled))
    if not attempts:
        raise RuntimeError("no tracklist source")

    pool = ThreadPoolExecutor(max_workers=len(attempts))
    try:
        pending = {pool.submit(attempt) for attempt in attempts}
        failed = 0
        while pending:
            done, pending = wait(pending, timeout=max(0.0, remaining()), return_when=FIRST_COMPLETED)
            if not done:
                raise TimeoutError("deadline")
            for future in done:
                try:
                    tracks = future.result()
                except Exception:
                    failed += 1
                    continue
                if tracks:
                    if remaining() > 0:
                        network.cache_write(key, {"at": time.time(), "results": tracks})
                    return tracks
        if failed == len(attempts):
            raise RuntimeError("all tracklist sources failed")
        return []
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _read_tracks(network: ArtistNetwork, key: str) -> list[dict[str, Any]] | None:
    from discovery.search.cache import SIMILAR_TTL_SECONDS, read_cached

    return read_cached(network.cache_read, key, time.time(), positive_ttl=SIMILAR_TTL_SECONDS) or None


def similar_albums(
    network: ArtistNetwork, similar: list[dict[str, Any]], owned: OwnedKeys, *, remaining, cancelled,
) -> list[dict[str, Any]]:
    """One top album per similar artist that the library does not own, in the artists' order."""
    items: list[dict[str, Any]] = []
    for artist in similar[:SIMILAR_ALBUM_ARTISTS]:
        if remaining() <= 0 or cancelled.is_set():
            break
        try:
            albums = _lastfm_albums(network, artist["name"], remaining=remaining, cancelled=cancelled)
        except Exception:
            continue
        for album in albums:
            if owned.owns(album):
                continue
            items.append({
                "name": album["name"],
                "artist": artist["name"],
                "artist_key": artist["key"],
                "key": f"{artist['key']}/{normalize_key(album['name'])}",
                "year": album["year"],
                "owned": False,
                "release_group_mbid": album["release_group_mbid"],
                "sources": [album["source"]],
            })
            break
    return items[:SIMILAR_ALBUM_LIMIT]


def album_sections(
    network: ArtistNetwork,
    data: OwnedData | None,
    *,
    album: dict[str, Any] | None,
    artist: str,
    artist_key: str,
    name: str,
    year: int | None,
    release_group_mbid: str | None,
) -> Iterator[dict[str, Any]]:
    """Yield each section object as it completes. ``album`` is the owned index entry, if any."""
    owned = OwnedKeys(data)
    owned_artist = next((a for a in (data.artists if data else ()) if a["key"] == artist_key), None)
    artist_id = owned_artist["id"] if owned_artist else None
    cancelled = threading.Event()
    deadline_at = network.clock() + network.deadline_seconds

    def remaining() -> float:
        return deadline_at - network.clock()

    yield _available("album", "album", {
        "name": album["name"] if album else name,
        "artist": album["artist"] if album else artist,
        "artist_key": artist_key,
        "artist_id": album["artist_id"] if album else None,
        "key": album["key"] if album else f"{artist_key}/{normalize_key(name)}",
        "year": album["year"] if album else year,
        "owned": album is not None,
        "id": album["id"] if album else None,
        "artwork_url": artwork_url(album["id"]) if album else None,
        "release_group_mbid": (album or {}).get("release_group_mbid") or release_group_mbid,
        "song_count": album["song_count"] if album else None,
    })

    shown_artist = album["artist"] if album else artist
    shown_name = album["name"] if album else name
    rg_mbid = (album or {}).get("release_group_mbid") or release_group_mbid

    known_year = album["year"] if album else year

    def year_job() -> dict[str, Any]:
        found = network.album_year(shown_artist, shown_name) if network.album_year else None
        return _available("year", "year", found)

    def description_job() -> dict[str, Any]:
        found = network.album_description(shown_artist, shown_name) if network.album_description else None
        return {**_available("description", "description", found or {"paragraphs": [], "source": "Apple Music", "url": None})}

    def tracks_job() -> dict[str, Any]:
        library = owned_tracks(data, album["id"]) if album and data else []
        try:
            provider = race_tracks(network, shown_artist, shown_name, rg_mbid, remaining=remaining, cancelled=cancelled)
        except Exception:
            if not library:
                raise
            # No provider answered: an owned album still lists what the library has.
            return _available("tracks", "items", library)
        songs = sorted(
            (s for s in data.songs if s["album_id"] == album["id"]), key=lambda s: s["track_number"] or 0,
        ) if album and data else []
        return _available("tracks", "items", mark_owned_tracks(provider, songs) if provider else library)

    def genre_job() -> dict[str, Any]:
        tags = tag_items(
            network, shown_artist, artist_id, remaining=remaining, cancelled=cancelled,
            known_mbid=(owned_artist or {}).get("mbid"),
        )
        names = tags.get("items") or []
        return {**_available("genre", "genre", names[0]["name"] if names else None), "complete": tags["complete"]}

    def similar_job() -> dict[str, Any]:
        section = similar_items(
            network, shown_artist, artist_id, owned,
            remaining=remaining, cancelled=cancelled,
            known_mbid=(owned_artist or {}).get("mbid"),
        )
        section["section"] = "similar_artists"
        return section

    # The year is in the section at once when the library or the caller knows it; otherwise it is looked up.
    pool = ThreadPoolExecutor(max_workers=6)
    try:
        pending = {
            pool.submit(tracks_job): "tracks",
            pool.submit(similar_job): "similar_artists",
            pool.submit(description_job): "description",
        }
        library_genre = (album or {}).get("genre") or (owned_artist or {}).get("genre")
        if library_genre:
            yield _available("genre", "genre", library_genre.casefold())
        else:
            pending[pool.submit(genre_job)] = "genre"
        if known_year is not None:
            yield _available("year", "year", known_year)
        else:
            pending[pool.submit(year_job)] = "year"
        while pending:
            done, _ = wait(set(pending), timeout=max(0.0, remaining()), return_when=FIRST_COMPLETED)
            if not done:
                for future, section in pending.items():
                    yield _incomplete(section, "deadline", _payload_key(section))
                    if section == "similar_artists":
                        yield _incomplete("similar_albums", "deadline", "items")
                break
            for future in done:
                section = pending.pop(future)
                try:
                    result = future.result()
                except TimeoutError:
                    result = _incomplete(section, "deadline", _payload_key(section))
                except Exception:
                    result = _incomplete(section, "source_failed", _payload_key(section))
                yield result
                if section == "similar_artists":
                    if network.lastfm is None:
                        yield {"section": "similar_albums", "available": False, "complete": False,
                               "reason": "source_disabled", "items": []}
                    else:
                        items = result.get("items") or []
                        pending[pool.submit(lambda items=items: {
                            "section": "similar_albums", "available": True, "complete": result["complete"],
                            "reason": None if result["complete"] else result["reason"],
                            "items": similar_albums(network, items, owned, remaining=remaining, cancelled=cancelled),
                        })] = "similar_albums"
    finally:
        cancelled.set()
        pool.shutdown(wait=False, cancel_futures=True)
