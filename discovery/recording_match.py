"""Match ordered track occurrences to owned songs by recording MBID."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from discovery.search.index import OwnedData
from discovery.search.normalize import normalize_mbid
from integrations.listenbrainz.jspf import PlaylistTrack


@dataclass(frozen=True)
class TrackMatch:
    """The original occurrence and the Navidrome song ID, if matched."""

    track: PlaylistTrack
    song_id: str | None

    @property
    def state(self) -> Literal["owned", "missing"]:
        return "owned" if self.song_id is not None else "missing"


def match_recordings(tracks: Iterable[PlaylistTrack], owned: OwnedData) -> tuple[TrackMatch, ...]:
    """Preserve each source occurrence in order and pick the lowest song ID for duplicate copies."""
    song_ids: dict[str, str] = {}
    for song in owned.songs:
        mbid = song.get("recording_mbid")
        song_id = song["id"]
        if mbid and (mbid not in song_ids or song_id < song_ids[mbid]):
            song_ids[mbid] = song_id

    return tuple(
        TrackMatch(track, song_ids.get(normalize_mbid(track.recording_mbid) or ""))
        for track in tracks
    )
