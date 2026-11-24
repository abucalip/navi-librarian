"""Match ordered track occurrences using recording MBIDs or corroborated tags."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
import re
from typing import Any, Literal
import unicodedata

from discovery.search.index import OwnedData
from discovery.search.normalize import normalize_mbid
from integrations.listenbrainz.jspf import PlaylistTrack


_DURATION_TOLERANCE_MS = 2_000
_VERSION_MARKER = re.compile(
    r"\b(?:live|studio|remix(?:ed)?|remaster(?:ed)?|demo|acoustic|edit|mix|version|mono|stereo)\b"
)
_BRACKETED_SUFFIX = re.compile(r"\s*(?:\(([^()]*)\)|\[([^\[\]]*)\])$")
_DASHED_SUFFIX = re.compile(r"\s[-–—]\s((?:(?!\s[-–—]\s).)+)$")


@dataclass(frozen=True)
class TrackMatch:
    """The original occurrence and the Navidrome song ID, if matched."""

    track: PlaylistTrack
    song_id: str | None
    ambiguous: bool = False

    @property
    def state(self) -> Literal["owned", "missing", "ambiguous"]:
        if self.song_id is not None:
            return "owned"
        return "ambiguous" if self.ambiguous else "missing"


def _tag_key(value: str | None) -> str:
    """Normalize case, Unicode composition and spacing while retaining title qualifiers."""
    return " ".join(unicodedata.normalize("NFC", value or "").casefold().split())


def _base_title(title: str) -> str:
    """Group plausible versions without erasing version evidence when matching."""
    while suffix := _BRACKETED_SUFFIX.search(title) or _DASHED_SUFFIX.search(title):
        qualifier = next(part for part in suffix.groups() if part is not None)
        if not _VERSION_MARKER.search(qualifier):
            break
        title = title[:suffix.start()].rstrip()
    return title


def _corroborates(track: PlaylistTrack, song: dict[str, Any]) -> bool:
    if _tag_key(track.title) != _tag_key(song["name"]):
        return False

    source_mbid = normalize_mbid(track.recording_mbid)
    local_mbid = song.get("recording_mbid")
    if source_mbid and local_mbid and local_mbid != source_mbid:
        return False

    source_album = _tag_key(track.album)
    local_album = _tag_key(song.get("album"))
    known_albums = bool(source_album and local_album)
    if known_albums and source_album != local_album:
        return False
    if not known_albums and _VERSION_MARKER.search(source_album or local_album):
        return False

    local_seconds = song.get("duration")
    if track.duration_ms and track.duration_ms > 0 and local_seconds and local_seconds > 0:
        return abs(track.duration_ms - local_seconds * 1_000) <= _DURATION_TOLERANCE_MS
    return known_albums


def _match_track(
    track: PlaylistTrack,
    song_ids: dict[str, str],
    songs_by_title: dict[tuple[str, str], list[dict[str, Any]]],
) -> TrackMatch:
    if track.conflicting_recording_mbids:
        return TrackMatch(track, None, ambiguous=True)

    mbid = normalize_mbid(track.recording_mbid)
    if mbid and (song_id := song_ids.get(mbid)):
        return TrackMatch(track, song_id)

    key = (_tag_key(track.artist), _base_title(_tag_key(track.title)))
    candidates = songs_by_title.get(key)
    if not candidates:
        return TrackMatch(track, None)
    if len(candidates) == 1 and _corroborates(track, candidates[0]):
        return TrackMatch(track, candidates[0]["id"])
    return TrackMatch(track, None, ambiguous=True)


def match_recordings(tracks: Iterable[PlaylistTrack], owned: OwnedData) -> tuple[TrackMatch, ...]:
    """Preserve each occurrence and use the lowest song ID for exact MBID duplicates."""
    song_ids: dict[str, str] = {}
    songs_by_title: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for song in owned.songs:
        mbid = song.get("recording_mbid")
        song_id = song["id"]
        if mbid and (mbid not in song_ids or song_id < song_ids[mbid]):
            song_ids[mbid] = song_id
        key = (_tag_key(song.get("artist")), _base_title(_tag_key(song.get("name"))))
        if all(key):
            songs_by_title[key].append(song)

    return tuple(_match_track(track, song_ids, songs_by_title) for track in tracks)
