"""Navidrome ingest adapter (docs/ServerV2.md section 9, Phase 1 item 4).

Takes an OpenSubsonic ``getAlbum`` album object (already fetched by the caller) and:

1. normalizes every useful field into one internal shape (:func:`normalize_album`);
2. stores that shape as an append-only observation (re-ingesting an unchanged album
   stores nothing new);
3. runs the resolution ladder for the artist, the release and each recording;
4. links the resolved entities with edges that carry their evidence.

This module makes no network calls and never writes to Navidrome or to music files. The
caller owns the fetching, pacing and the optional MusicBrainz ``search`` callable. Items
the ladder cannot resolve are queued in ``unresolved`` and get no entity or edge, so a
guess never reaches the graph. Only fields Navidrome actually returned are kept; a
missing field stays ``None`` rather than becoming a default.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..resolution import LibraryRef, resolve
from ..resolution.ladder import Search
from ..resolution.normalize import normalize_mbid
from ..store import repositories as repo

SOURCE = "navidrome"
REL_APPEARS_ON = "appears_on"   # recording -> release
REL_CREDITED_TO = "credited_to"  # release -> artist


@dataclass(frozen=True)
class NormalizedTrack:
    navidrome_id: str
    title: str | None = None
    artist: str | None = None
    artist_id: str | None = None
    mbid: str | None = None
    isrcs: tuple[str, ...] = ()
    track_number: int | None = None
    disc_number: int | None = None
    year: int | None = None
    duration_ms: int | None = None
    bit_rate: int | None = None
    bit_depth: int | None = None
    sampling_rate: int | None = None
    channel_count: int | None = None
    size: int | None = None
    suffix: str | None = None
    content_type: str | None = None
    path: str | None = None
    genres: tuple[str, ...] = ()
    replay_gain: dict[str, float] | None = None
    play_count: int | None = None
    bpm: int | None = None


@dataclass(frozen=True)
class NormalizedAlbum:
    navidrome_id: str
    name: str | None = None
    artist: str | None = None
    artist_id: str | None = None
    artist_mbid: str | None = None
    mbid: str | None = None
    year: int | None = None
    original_release_date: str | None = None
    release_date: str | None = None
    genres: tuple[str, ...] = ()
    song_count: int | None = None
    duration_ms: int | None = None
    record_labels: tuple[str, ...] = ()
    release_types: tuple[str, ...] = ()
    disc_titles: dict[int, str] = field(default_factory=dict)
    is_compilation: bool | None = None
    version: str | None = None
    play_count: int | None = None
    tracks: tuple[NormalizedTrack, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """JSON-ready form stored as the observation payload."""
        data = _plain(self)
        data["disc_titles"] = {str(k): v for k, v in self.disc_titles.items()}
        return data


@dataclass
class IngestResult:
    album_id: str
    observation_id: int | None = None
    new_observation: bool = False
    release_entity_id: int | None = None
    artist_entity_id: int | None = None
    recordings_resolved: int = 0
    unresolved: int = 0
    deferred: int = 0
    edges_created: int = 0
    notes: list[str] = field(default_factory=list)


# -------------------------------------------------------------- normalization

def normalize_album(album: Mapping[str, Any]) -> NormalizedAlbum:
    """Normalize one ``getAlbum`` album object; raises ``ValueError`` without an id."""
    album_id = _text(album.get("id"))
    if not album_id:
        raise ValueError("album has no id")
    songs = album.get("song") or []
    if isinstance(songs, Mapping):
        songs = [songs]
    tracks = tuple(_track(s) for s in songs if isinstance(s, Mapping) and _text(s.get("id")))
    artist_id = _text(album.get("artistId"))
    return NormalizedAlbum(
        navidrome_id=album_id,
        name=_text(album.get("name") or album.get("title")),
        artist=_text(album.get("artist")),
        artist_id=artist_id,
        artist_mbid=_album_artist_mbid(album, artist_id),
        mbid=normalize_mbid(_text(album.get("musicBrainzId"))),
        year=_int(album.get("year")),
        original_release_date=_date(album.get("originalReleaseDate")),
        release_date=_date(album.get("releaseDate")),
        genres=_genres(album),
        song_count=_int(album.get("songCount")),
        duration_ms=_seconds_to_ms(album.get("duration")),
        record_labels=_names(album.get("recordLabels")),
        release_types=_names(album.get("releaseTypes")),
        disc_titles=_disc_titles(album.get("discTitles")),
        is_compilation=album.get("isCompilation") if isinstance(album.get("isCompilation"), bool) else None,
        version=_text(album.get("version")),
        play_count=_int(album.get("playCount")),
        tracks=tracks,
    )


def _track(song: Mapping[str, Any]) -> NormalizedTrack:
    return NormalizedTrack(
        navidrome_id=_text(song.get("id")) or "",
        title=_text(song.get("title")),
        artist=_text(song.get("artist")),
        artist_id=_text(song.get("artistId")),
        mbid=normalize_mbid(_text(song.get("musicBrainzId"))),
        isrcs=_names(song.get("isrc")),
        track_number=_int(song.get("track")),
        disc_number=_int(song.get("discNumber")),
        year=_int(song.get("year")),
        duration_ms=_seconds_to_ms(song.get("duration")),
        bit_rate=_int(song.get("bitRate")),
        bit_depth=_int(song.get("bitDepth")),
        sampling_rate=_int(song.get("samplingRate")),
        channel_count=_int(song.get("channelCount")),
        size=_int(song.get("size")),
        suffix=_text(song.get("suffix")),
        content_type=_text(song.get("contentType")),
        path=_text(song.get("path")),
        genres=_genres(song),
        replay_gain=_replay_gain(song.get("replayGain")),
        play_count=_int(song.get("playCount")),
        bpm=_int(song.get("bpm")),
    )


def _album_artist_mbid(album: Mapping[str, Any], artist_id: str | None) -> str | None:
    """MBID of the album artist when Navidrome supplies one for the matching artist entry."""
    for entry in album.get("artists") or []:
        if isinstance(entry, Mapping) and _text(entry.get("id")) == artist_id:
            mbid = normalize_mbid(_text(entry.get("musicBrainzId")))
            if mbid:
                return mbid
    return normalize_mbid(_text(album.get("artistMusicBrainzId")))


# ------------------------------------------------------------------- ingest

def ingest_album(
    db: sqlite3.Connection,
    album: Mapping[str, Any],
    *,
    now: float,
    search: Search | None = None,
) -> IngestResult:
    """Normalize, record and resolve one album; safe to repeat for the same album."""
    data = normalize_album(album)
    result = IngestResult(album_id=data.navidrome_id)
    result.observation_id, result.new_observation = repo.add_observation(
        db, SOURCE, data.as_dict(), fetched_at=now, entity_hint=f"album:{data.navidrome_id}"
    )

    release = resolve(db, _release_ref(data), now=now, search=search)
    _count(result, release)
    result.release_entity_id = release.entity_id

    if data.artist_id and data.artist and data.artist_mbid:
        artist = resolve(
            db,
            LibraryRef("artist", data.artist_id, mbid=data.artist_mbid, artist=data.artist, title=data.artist),
            now=now, search=None,
        )
        _count(result, artist)
        result.artist_entity_id = artist.entity_id
        if release.entity_id and artist.entity_id:
            _edge(db, result, release.entity_id, artist.entity_id, REL_CREDITED_TO, artist)
    elif data.artist_id:
        result.notes.append("album artist has no MBID; artist left for a later phase")

    for track in data.tracks:
        rec = resolve(db, _recording_ref(data, track), now=now, search=None)
        _count(result, rec, recording=True)
        if rec.entity_id and release.entity_id:
            _edge(db, result, rec.entity_id, release.entity_id, REL_APPEARS_ON, rec,
                  role=_position(track))
    return result


def _release_ref(data: NormalizedAlbum) -> LibraryRef:
    durations = tuple(t.duration_ms for t in data.tracks if t.duration_ms is not None)
    complete = len(durations) == len(data.tracks)
    return LibraryRef(
        "release", data.navidrome_id, mbid=data.mbid, artist=data.artist, title=data.name,
        track_count=data.song_count if data.song_count is not None else (len(data.tracks) or None),
        durations_ms=durations if complete else (),
    )


def _recording_ref(data: NormalizedAlbum, track: NormalizedTrack) -> LibraryRef:
    isrc = next((code for code in track.isrcs), None)
    return LibraryRef(
        "recording", track.navidrome_id, mbid=track.mbid, isrc=isrc,
        artist=track.artist or data.artist, title=track.title,
        durations_ms=(track.duration_ms,) if track.duration_ms is not None else (),
    )


def _position(track: NormalizedTrack) -> str | None:
    """Disc and track number as ``disc/track`` (the edge role), when Navidrome knows the track number."""
    if track.track_number is None:
        return None
    return f"{track.disc_number or 1}/{track.track_number}"


def _count(result: IngestResult, resolution: Any, *, recording: bool = False) -> None:
    if resolution.outcome == "resolved":
        result.recordings_resolved += int(recording)
    elif resolution.outcome == "deferred":
        result.deferred += 1
    else:
        result.unresolved += 1


def _edge(db, result, from_id, to_id, relation, resolution, role=None) -> None:
    _, created = repo.add_edge(
        db, from_id, to_id, relation,
        evidence_class=resolution.evidence_class or "derived",
        match_quality=resolution.match_quality,
        source=SOURCE, role=role, observation_id=result.observation_id,
    )
    result.edges_created += int(created)


# ------------------------------------------------------------------ coercion

def _text(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return text or None


def _int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _seconds_to_ms(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(round(float(value) * 1000))
    except (TypeError, ValueError):
        return None


def _date(value: Any) -> str | None:
    """``YYYY[-MM[-DD]]`` from a string or an OpenSubsonic ``{year, month, day}`` object."""
    if isinstance(value, Mapping):
        year, month, day = _int(value.get("year")), _int(value.get("month")), _int(value.get("day"))
        if not year:
            return None
        parts = [f"{year:04d}"]
        if month:
            parts.append(f"{month:02d}")
            if day:
                parts.append(f"{day:02d}")
        return "-".join(parts)
    return _text(value)


def _names(value: Any) -> tuple[str, ...]:
    """A list of strings or of ``{name: ...}`` objects (or one bare string), de-duplicated in order."""
    if value is None:
        return ()
    items = value if isinstance(value, (list, tuple)) else [value]
    out: list[str] = []
    for item in items:
        text = _text(item.get("name") if isinstance(item, Mapping) else item)
        if text and text not in out:
            out.append(text)
    return tuple(out)


def _genres(source: Mapping[str, Any]) -> tuple[str, ...]:
    listed = _names(source.get("genres"))
    return listed or _names(source.get("genre"))


def _disc_titles(value: Any) -> dict[int, str]:
    out: dict[int, str] = {}
    for item in value or []:
        if isinstance(item, Mapping):
            disc, title = _int(item.get("disc")), _text(item.get("title"))
            if disc is not None and title:
                out[disc] = title
    return out


def _replay_gain(value: Any) -> dict[str, float] | None:
    if not isinstance(value, Mapping):
        return None
    out: dict[str, float] = {}
    for key in ("trackGain", "albumGain", "trackPeak", "albumPeak", "baseGain", "fallbackGain"):
        try:
            if value.get(key) is not None and not isinstance(value.get(key), bool):
                out[key] = float(value[key])
        except (TypeError, ValueError):
            continue
    return out or None


def _plain(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {k: _plain(getattr(value, k)) for k in value.__dataclass_fields__}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value
