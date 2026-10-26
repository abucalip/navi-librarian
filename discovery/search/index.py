"""In-process owned index for global search and library browsing (contract section 4.1).

The index holds normalized artists, albums and songs from the Navidrome library.
Builds run in background threads and are never started or awaited by a request
handler beyond a non-blocking trigger. A completed build replaces the current
index atomically; a failed or suspicious build keeps the last known-good index.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from discovery.recommendations import is_various_artists
from discovery.search.normalize import normalize_key

SONG_PAGE_SIZE = 500
MAX_SONGS = 200_000
SANITY_DROP_LIMIT = 0.10
INDEX_TTL_SECONDS = 10 * 60
RETRY_BACKOFF_SECONDS = 30

STATE_BUILDING = "building"
STATE_FRESH = "fresh"
STATE_STALE = "stale"
STATE_UNAVAILABLE = "unavailable"


class SongInventoryError(RuntimeError):
    """Raised when the paged song inventory cannot be proven complete."""


@dataclass(frozen=True)
class OwnedData:
    """One completed index build. Immutable once published."""

    generation: Any
    built_at: float
    artists: tuple[dict[str, Any], ...]
    albums: tuple[dict[str, Any], ...]
    songs: tuple[dict[str, Any], ...]
    by_artist_id: Mapping[str, tuple[dict[str, Any], ...]] = field(default_factory=dict)

    @property
    def song_count(self) -> int:
        return len(self.songs)


def fetch_song_inventory(
    api_call: Callable[..., dict[str, Any]],
    items: Callable[[Any], list[Any]],
    *,
    page_size: int = SONG_PAGE_SIZE,
    max_songs: int = MAX_SONGS,
) -> list[dict[str, Any]]:
    """Return every song in the library using paged ``search3`` with an empty query.

    The inventory is complete only when a short page ends the walk. Hitting the
    safety cap raises instead of returning a partial list.
    """
    songs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    offset = 0
    while offset < max_songs:
        root = api_call(
            "search3",
            query="",
            artistCount=0,
            albumCount=0,
            songCount=page_size,
            songOffset=offset,
        )
        page = items(root.get("searchResult3", {}).get("song"))
        for song in page:
            song_id = song.get("id")
            if song_id and song_id in seen_ids:
                continue
            if song_id:
                seen_ids.add(song_id)
            songs.append(song)
        if len(page) < page_size:
            return songs
        offset += page_size
    raise SongInventoryError("Navidrome song inventory exceeded the safety limit.")


def _artist_entry(artist: Mapping[str, Any]) -> dict[str, Any]:
    name = str(artist.get("name") or "").strip()
    return {
        "id": str(artist.get("id") or ""),
        "name": name,
        "key": normalize_key(name),
        "album_count": int(artist.get("album_count") or 0),
        "mbid": None,
    }


def _year(value: Any) -> int | None:
    """A four-digit year, or None when the library does not give one."""
    try:
        year = int(str(value).strip())
    except ValueError:
        return None
    return year if 1000 <= year <= 9999 else None


def _artist_genre(albums: Iterable[Mapping[str, Any]]) -> str | None:
    """The genre most albums of an artist carry, or None when no album has one.

    Counts ignore case, and the first spelling seen is shown. Ties go to the alphabetically first genre.
    """
    counts: dict[str, int] = {}
    spelling: dict[str, str] = {}
    for album in albums:
        genre = str(album.get("genre") or "").strip()
        if not genre:
            continue
        folded = genre.casefold()
        counts[folded] = counts.get(folded, 0) + 1
        spelling.setdefault(folded, genre)
    if not counts:
        return None
    best = sorted(counts, key=lambda genre: (-counts[genre], genre))[0]
    return spelling[best]


def _album_entry(album: Mapping[str, Any], artist_keys: Mapping[str, str]) -> dict[str, Any]:
    artist_name = str(album.get("artist") or "").strip()
    artist_id = str(album.get("artist_id") or "")
    artist_key = normalize_key(artist_name)
    name = str(album.get("album") or "").strip()
    year = album.get("year")
    return {
        "id": str(album.get("id") or ""),
        "artist_id": artist_id,
        "artist": artist_name,
        "artist_key": artist_keys.get(artist_id, artist_key),
        "name": name,
        "name_key": normalize_key(name),
        "key": f"{artist_key}/{normalize_key(name)}",
        "year": _year(year),
        "genre": str(album.get("genre") or "").strip() or None,
        "song_count": int(album.get("song_count") or 0),
        "release_mbid": str(album.get("release_mbid") or "").strip() or None,
        "release_group_mbid": None,
    }


def _song_entry(song: Mapping[str, Any]) -> dict[str, Any]:
    artist_name = str(song.get("artist") or "").strip()
    title = str(song.get("title") or "").strip()
    duration = song.get("duration")
    track = song.get("track")
    return {
        "id": str(song.get("id") or ""),
        "artist_id": str(song.get("artistId") or ""),
        "artist": artist_name,
        "artist_key": normalize_key(artist_name),
        "name": title,
        "name_key": normalize_key(title),
        "album": str(song.get("album") or "").strip(),
        "album_id": str(song.get("albumId") or ""),
        "key": f"{normalize_key(artist_name)}/{normalize_key(title)}",
        "duration": int(duration) if isinstance(duration, (int, float)) else None,
        "track_number": int(track) if isinstance(track, int) and track >= 1 else None,
        # Navidrome's play count for the song (Subsonic ``playCount``); zero when absent.
        "plays": _count(song.get("playCount")),
    }


def _count(value: Any) -> int:
    return int(value) if isinstance(value, int) and value > 0 else 0


def build_owned_data(
    *,
    generation: Any,
    built_at: float,
    artists: Iterable[Mapping[str, Any]],
    albums: Iterable[Mapping[str, Any]],
    songs: Iterable[Mapping[str, Any]],
    identities: Mapping[str, Mapping[str, Any]] | None = None,
) -> OwnedData:
    """Assemble a normalized index from raw snapshot and song records. Pure.

    ``identities`` maps ``artist:{id}`` to ``{"mbid": ...}`` and ``album:{id}`` to
    ``{"release_group_mbid": ...}``, as stored by the identity job. Unknown IDs keep null MBIDs.
    """
    identities = identities or {}
    # "Various Artists" is a compilation credit, not an artist, so it never becomes an artist result
    # (SEARCH_CONTRACT section 4.2).
    artist_entries = tuple(
        entry for entry in (_artist_entry(a) for a in artists)
        if entry["id"] and entry["name"] and not is_various_artists(entry["name"])
    )
    artist_keys = {entry["id"]: entry["key"] for entry in artist_entries}
    album_entries = tuple(
        _album_entry(a, artist_keys) for a in albums if a.get("id") and a.get("album")
    )
    song_entries = tuple(_song_entry(s) for s in songs if s.get("id") and s.get("title"))

    by_artist: dict[str, list[dict[str, Any]]] = {}
    for album in album_entries:
        by_artist.setdefault(album["artist_id"], []).append(album)
    plays_by_artist: dict[str, int] = {}
    for song in song_entries:
        plays_by_artist[song["artist_id"]] = plays_by_artist.get(song["artist_id"], 0) + song["plays"]
    for artist in artist_entries:
        artist["genre"] = _artist_genre(by_artist.get(artist["id"], ()))
        artist["mbid"] = (identities.get(f"artist:{artist['id']}") or {}).get("mbid") or None
        # Owner play count across the artist's songs (contract 4.1 owned data; used by the similar boost).
        artist["plays"] = plays_by_artist.get(artist["id"], 0)
    for album in album_entries:
        album["release_group_mbid"] = (
            (identities.get(f"album:{album['id']}") or {}).get("release_group_mbid") or None
        )
    return OwnedData(
        generation=generation,
        built_at=built_at,
        artists=artist_entries,
        albums=album_entries,
        songs=song_entries,
        by_artist_id={key: tuple(value) for key, value in by_artist.items()},
    )


@dataclass(frozen=True)
class IndexView:
    """A consistent read of the index for one request."""

    state: str
    data: OwnedData | None
    reason: str | None


_UNAVAILABLE_REASON = {
    STATE_BUILDING: "index_building",
    STATE_UNAVAILABLE: "index_unavailable",
}


class OwnedIndex:
    """Single-flight, last-known-good owned index.

    ``load_library`` returns ``(artists, albums)`` from the library snapshot and
    ``load_songs`` returns raw song records. Both are injected so the lifecycle is
    testable without Navidrome. With ``background=False`` a build runs inline,
    which is used by tests only.
    """

    def __init__(
        self,
        *,
        load_library: Callable[[], tuple[list[dict[str, Any]], list[dict[str, Any]]]],
        load_songs: Callable[[], list[dict[str, Any]]],
        load_identities: Callable[[Any], Mapping[str, Mapping[str, Any]]] | None = None,
        after_build: Callable[[OwnedData], None] | None = None,
        now: Callable[[], float] = time.time,
        ttl_seconds: float = INDEX_TTL_SECONDS,
        background: bool = True,
    ):
        self._load_library = load_library
        self._load_songs = load_songs
        self._load_identities = load_identities
        self._after_build = after_build
        self._now = now
        self._ttl = ttl_seconds
        self._background = background
        self._lock = threading.Lock()
        self._generation: Any = _NO_GENERATION
        self._data: OwnedData | None = None
        self._state = STATE_BUILDING
        self._building = False
        self._refresh_requested = False
        self._retry_at = 0.0

    def view(self) -> IndexView:
        """Return the current state without triggering or waiting for a build."""
        with self._lock:
            reason = None
            if self._state in _UNAVAILABLE_REASON:
                reason = _UNAVAILABLE_REASON[self._state]
            return IndexView(self._state, self._data, reason)

    def ensure(self, generation: Any, *, force: bool = False) -> None:
        """Start a build when needed. Never waits for the build to finish.

        A changed Navidrome generation drops the current index at once, so no data
        from the previous server is served (contract section 4.1).
        """
        generation_to_build = None
        with self._lock:
            if generation != self._generation:
                self._generation = generation
                self._refresh_requested = False
                self._data = None
                self._state = STATE_BUILDING
                self._retry_at = 0.0
            now = self._now()
            due = self._data is None or self._data.built_at + self._ttl <= now
            if (force or (due and now >= self._retry_at)) and not self._building:
                self._building = True
                generation_to_build = self._generation
        if generation_to_build is not None:
            self._spawn(generation_to_build)

    def refresh(self, generation: Any) -> None:
        """Rebuild now, but only if ``generation`` is still the current one.

        A caller that holds an older generation does nothing, so a late callback can never move
        the index back to a server that is no longer configured.
        """
        with self._lock:
            if generation != self._generation:
                return
            if self._building:
                # A build is already running and may have read the data before this request's
                # writes. Build once more when it finishes (see _run_build).
                self._refresh_requested = True
                return
            self._building = True
            generation_to_build = self._generation
        self._spawn(generation_to_build)

    def _spawn(self, generation: Any) -> None:
        """Start one build. Called without the lock held."""
        if self._background:
            threading.Thread(
                target=self._run_build, args=(generation,), daemon=True
            ).start()
        else:
            self._run_build(generation)

    def _run_build(self, generation: Any) -> None:
        try:
            data = self._build(generation)
        except Exception:
            data = None
        next_generation = None
        with self._lock:
            self._building = False
            if generation != self._generation:
                # The generation changed while this build ran. Its result belongs to a
                # server that is no longer configured, so discard it and build again.
                self._building = True
                next_generation = self._generation
            elif data is None:
                self._state = STATE_STALE if self._data is not None else STATE_UNAVAILABLE
                self._retry_at = self._now() + RETRY_BACKOFF_SECONDS
            else:
                self._data = data
                self._state = STATE_FRESH
            if next_generation is None and self._refresh_requested and generation == self._generation:
                self._refresh_requested = False
                self._building = True
                next_generation = self._generation
        if next_generation is not None:
            self._spawn(next_generation)
        elif data is not None and self._after_build is not None:
            try:
                self._after_build(data)
            except Exception:
                # Identity resolution is an enrichment. A failure there never affects the index.
                pass

    def _build(self, generation: Any) -> OwnedData:
        """Build one index. Raises when the sanity check rejects it."""
        artists, albums = self._load_library()
        songs = self._load_songs()
        identities = self._load_identities(generation) if self._load_identities else None
        built = build_owned_data(
            generation=generation,
            built_at=self._now(),
            artists=artists,
            albums=albums,
            songs=songs,
            identities=identities,
        )
        with self._lock:
            previous = self._data
        if previous is not None and previous.song_count:
            floor = previous.song_count * (1 - SANITY_DROP_LIMIT)
            if built.song_count < floor:
                # A fall of more than 10% is treated as a bad read, not as library change.
                raise SongInventoryError("Owned index song count fell suspiciously.")
        return built


_NO_GENERATION = object()
