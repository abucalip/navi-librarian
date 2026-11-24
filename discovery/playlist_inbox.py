"""Build Playlist Inbox responses from stored editions and the owned song index."""

from dataclasses import asdict, fields
from datetime import datetime, timezone
from itertools import islice
from unicodedata import normalize

from acquisition.track_service import track_job_album
from discovery.recording_match import match_recordings
from integrations.listenbrainz.jspf import PlaylistTrack


SNAPSHOT_MAX_AGE = 7 * 24 * 60 * 60
_TRACK_FIELDS = {field.name for field in fields(PlaylistTrack)}
_PLAYLIST_FIELDS = ("identifier", "title", "creator", "source_patch", "generated_at", "last_modified_at")


def edition_tracks(edition):
    """Decode the common track shape, including sparse generated editions."""
    for row in edition.snapshot.tracks:
        values = dict(recording_mbid=None, title=None, artist=None, album=None, duration_ms=None)
        values.update((key, value) for key, value in row.items() if key in _TRACK_FIELDS)
        yield PlaylistTrack(**values)


def _summary(edition, owned_count, now):
    snapshot = edition.snapshot
    return {
        "edition_id": edition.id,
        "source_kind": snapshot.source_kind,
        "source_key": snapshot.source_key,
        **{name: snapshot.metadata.get(name) for name in _PLAYLIST_FIELDS},
        "fetched_at": datetime.fromtimestamp(edition.fetched_at, tz=timezone.utc).isoformat(),
        "stale": now - edition.fetched_at >= SNAPSHOT_MAX_AGE,
        "total_count": len(snapshot.tracks),
        "owned_count": owned_count,
    }


def list_items(editions, owned, now):
    """Index the library once, even when the list contains several editions."""
    if owned is None:
        return [_summary(edition, None, now) for edition in editions]
    tracks = (track for edition in editions for track in edition_tracks(edition))
    matches = iter(match_recordings(tracks, owned)) if any(e.snapshot.tracks for e in editions) else iter(())
    return [
        _summary(edition, sum(match.state == "owned" for match in islice(matches, len(edition.snapshot.tracks))), now)
        for edition in editions
    ]


def _label(value):
    return " ".join(normalize("NFC", value or "").casefold().split())


def _acquisition_status(track, state, jobs, music_key):
    if state in (None, "ambiguous") or not all(_label(x) for x in (track.artist, track.album, track.title)):
        return None
    identity = (music_key(track.artist), music_key(track_job_album(track.album, track.title)))
    job = jobs.get(identity)
    if job is None:
        return None
    artist, album, title, status = job
    # The job key folds punctuation. Require the saved labels to agree too.
    if tuple(map(_label, (artist, album, title))) == tuple(map(_label, (track.artist, track.album, track.title))):
        return status
    return None


def edition_detail(edition, owned, jobs, music_key, now):
    tracks = tuple(edition_tracks(edition))
    matches = None if owned is None else match_recordings(tracks, owned)
    rows = []
    for offset, track in enumerate(tracks):
        match = matches[offset] if matches is not None else None
        state = match.state if match else None
        rows.append({
            **asdict(track),
            "match_state": state,
            "song_id": match.song_id if match else None,
            "acquisition_status": _acquisition_status(track, state, jobs, music_key),
        })
    owned_count = None if matches is None else sum(match.state == "owned" for match in matches)
    return {**_summary(edition, owned_count, now), "tracks": rows}
