"""Parse ListenBrainz JSPF playlist details without provider I/O."""

from dataclasses import dataclass, field
from datetime import datetime
import re


_MBID_PATTERN = r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
_MBID = re.compile(_MBID_PATTERN, re.IGNORECASE)
_MUSICBRAINZ_URL = re.compile(
    r"https?://musicbrainz\.org/(recording|artist|release)/" + _MBID_PATTERN,
    re.IGNORECASE,
)
_PLAYLIST_URL = re.compile(r"https?://listenbrainz\.org/playlist/" + _MBID_PATTERN, re.IGNORECASE)
_JSPF = "https://musicbrainz.org/doc/jspf"


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
    artist_mbids: tuple[str, ...] = ()
    release_mbid: str | None = None
    caa_id: int | None = None
    caa_release_mbid: str | None = None


@dataclass(frozen=True)
class PlaylistMetadata:
    """Metadata shared by playlist listings and details."""

    identifier: str | None
    title: str | None
    generated_at: datetime | None
    last_modified_at: datetime | None = field(default=None, kw_only=True)
    source_patch: str | None = field(default=None, kw_only=True)
    creator: str | None = field(default=None, kw_only=True)

    @property
    def playlist_mbid(self) -> str | None:
        match = _PLAYLIST_URL.fullmatch(self.identifier or "")
        return match[1].lower() if match else None


@dataclass(frozen=True)
class ParsedPlaylist(PlaylistMetadata):
    """Playlist metadata and its ordered track occurrences."""

    tracks: tuple[PlaylistTrack, ...]


def _text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def _musicbrainz_mbid(value: object, entity: str) -> str | None:
    if isinstance(value, str):
        match = _MUSICBRAINZ_URL.fullmatch(value)
        if match and match[1].lower() == entity:
            return match[2].lower()
    return None


def _timestamp(value: object) -> datetime | None:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed
    return None


def _object(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _playlist_object(payload: object) -> dict:
    playlist = payload.get("playlist") if isinstance(payload, dict) else None
    if not isinstance(playlist, dict):
        raise ValueError("JSPF payload must contain a playlist object")
    return playlist


def _metadata_fields(playlist: dict) -> dict:
    extension = _object(_object(playlist.get("extension")).get(f"{_JSPF}#playlist"))
    additional = _object(extension.get("additional_metadata"))
    algorithm = _object(additional.get("algorithm_metadata", extension.get("algorithm_metadata")))
    return {
        "identifier": _text(playlist.get("identifier")),
        "title": _text(playlist.get("title")),
        "generated_at": _timestamp(playlist.get("date")),
        "last_modified_at": _timestamp(extension.get("last_modified_at")),
        "source_patch": _text(algorithm.get("source_patch")) or _text(extension.get("source_patch")),
        "creator": _text(extension.get("creator")) or _text(playlist.get("creator")),
    }


def parse_playlist_metadata(payload: object) -> PlaylistMetadata:
    """Parse a JSPF listing entry without requiring tracks."""
    return PlaylistMetadata(**_metadata_fields(_playlist_object(payload)))


def _parse_track(track: dict, position: int) -> PlaylistTrack:
    identifiers = track.get("identifier")
    if not isinstance(identifiers, list):
        identifiers = [identifiers]
    mbids = {mbid for value in identifiers if (mbid := _musicbrainz_mbid(value, "recording"))}
    extension = _object(_object(track.get("extension")).get(f"{_JSPF}#track"))
    additional = _object(extension.get("additional_metadata"))
    artists = extension.get("artist_identifiers")
    if not isinstance(artists, list):
        artists = []
    duration = track.get("duration")
    caa_id = additional.get("caa_id", extension.get("caa_id"))
    caa_release = _text(additional.get("caa_release_mbid"))
    return PlaylistTrack(
        position=position,
        recording_mbid=next(iter(mbids)) if len(mbids) == 1 else None,
        title=_text(track.get("title")),
        artist=_text(track.get("creator")),
        album=_text(track.get("album")),
        duration_ms=duration if type(duration) is int and duration >= 0 else None,
        conflicting_recording_mbids=len(mbids) > 1,
        artist_mbids=tuple(mbid for value in artists if (mbid := _musicbrainz_mbid(value, "artist"))),
        release_mbid=_musicbrainz_mbid(extension.get("release_identifier"), "release"),
        caa_id=caa_id if type(caa_id) is int and caa_id > 0 else None,
        caa_release_mbid=caa_release.lower() if caa_release and _MBID.fullmatch(caa_release) else None,
    )


def parse_playlist(payload: object) -> ParsedPlaylist:
    """Parse a JSPF detail response, raising ValueError for an invalid track list.

    Missing, invalid or conflicting recording IDs leave the occurrence unresolved.
    The generation date comes from the playlist date when it includes a timezone.
    """
    playlist = _playlist_object(payload)

    source_tracks = playlist.get("track")
    if not isinstance(source_tracks, list):
        raise ValueError("JSPF playlist must contain a track list")

    tracks = []
    for position, track in enumerate(source_tracks):
        if not isinstance(track, dict):
            raise ValueError(f"JSPF track at position {position} must be an object")
        tracks.append(_parse_track(track, position))

    return ParsedPlaylist(**_metadata_fields(playlist), tracks=tuple(tracks))
