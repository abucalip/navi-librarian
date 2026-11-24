"""Parse ListenBrainz JSPF playlist details without provider I/O."""

from dataclasses import dataclass
from datetime import datetime
import re


_RECORDING_URL = re.compile(
    r"https?://musicbrainz\.org/recording/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PlaylistTrack:
    """One occurrence of a track, indexed from zero in the source playlist."""

    position: int
    recording_mbid: str | None
    title: str | None
    artist: str | None
    album: str | None
    duration_ms: int | None
    conflicting_recording_mbids: bool = False


@dataclass(frozen=True)
class ParsedPlaylist:
    """Playlist metadata and its ordered track occurrences."""

    identifier: str | None
    title: str | None
    generated_at: datetime | None
    tracks: tuple[PlaylistTrack, ...]


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _recording_mbids(value: object) -> set[str]:
    identifiers = value if isinstance(value, list) else [value]
    mbids = set()
    for identifier in identifiers:
        if isinstance(identifier, str):
            match = _RECORDING_URL.fullmatch(identifier)
            if match:
                mbids.add(match[1].lower())
    return mbids


def _generated_at(value: object) -> datetime | None:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed
    return None


def parse_playlist(payload: object) -> ParsedPlaylist:
    """Parse a JSPF detail response, raising ValueError for an invalid track list.

    Missing, invalid or conflicting recording IDs leave the occurrence unresolved.
    The generation date comes from the playlist date when it includes a timezone.
    """
    playlist = payload.get("playlist") if isinstance(payload, dict) else None
    if not isinstance(playlist, dict):
        raise ValueError("JSPF payload must contain a playlist object")

    source_tracks = playlist.get("track")
    if not isinstance(source_tracks, list):
        raise ValueError("JSPF playlist must contain a track list")

    tracks = []
    for position, track in enumerate(source_tracks):
        if not isinstance(track, dict):
            raise ValueError(f"JSPF track at position {position} must be an object")
        duration = track.get("duration")
        mbids = _recording_mbids(track.get("identifier"))
        tracks.append(PlaylistTrack(
            position=position,
            recording_mbid=next(iter(mbids)) if len(mbids) == 1 else None,
            title=_text(track.get("title")),
            artist=_text(track.get("creator")),
            album=_text(track.get("album")),
            duration_ms=duration if type(duration) is int and duration >= 0 else None,
            conflicting_recording_mbids=len(mbids) > 1,
        ))

    return ParsedPlaylist(
        identifier=_text(playlist.get("identifier")),
        title=_text(playlist.get("title")),
        generated_at=_generated_at(playlist.get("date")),
        tracks=tuple(tracks),
    )
