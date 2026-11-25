"""Build Playlist Inbox responses from stored editions and the owned song index."""

from dataclasses import asdict, fields, replace
from datetime import datetime, timezone
from itertools import islice
from unicodedata import normalize

from acquisition.track_service import track_job_album
from discovery.recording_match import match_recordings
from discovery.search.normalize import normalize_mbid
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


def list_items(editions, owned, jobs, now):
    """Index the library once, even when the list contains several editions."""
    if owned is None:
        return [_summary(edition, None, now) for edition in editions]
    source_jobs = _source_jobs(jobs)
    tracks = (
        _with_resolved_album(track, job)
        for edition in editions for track, job in _tracks_with_sparse_jobs(edition, source_jobs)
    )
    matches = iter(match_recordings(tracks, owned)) if any(e.snapshot.tracks for e in editions) else iter(())
    return [
        _summary(edition, sum(match.state == "owned" for match in islice(matches, len(edition.snapshot.tracks))), now)
        for edition in editions
    ]


def _label(value):
    return " ".join(normalize("NFC", value).casefold().split()) if isinstance(value, str) else ""


def download_source(edition_id, track):
    """Use the same source identity when saving and reading albumless jobs."""
    recording = normalize_mbid(track.recording_mbid)
    if recording:
        return f"{recording}/{normalize_mbid(track.release_mbid) or ''}"
    return f"{edition_id}/{track.position}"


def _source_jobs(jobs):
    by_source = {}
    for job in jobs.values():
        if job.inbox_source:
            key = (job.inbox_source, _label(job.artist), _label(job.title))
            by_source[key] = job if key not in by_source else None
    return by_source


def _sparse_job(track, edition_id, source_jobs):
    artist, title = _label(track.artist), _label(track.title)
    if not artist or not title or _label(track.album) or track.conflicting_recording_mbids:
        return None
    job = source_jobs.get((download_source(edition_id, track), artist, title))
    if job and _same_recording(track, job):
        return job
    return None


def _tracks_with_sparse_jobs(edition, source_jobs):
    def identity(track):
        return (track.artist, track.title, track.album, track.recording_mbid,
                track.release_mbid, track.duration_ms, track.conflicting_recording_mbids)

    tracks = [(track, _sparse_job(track, edition.id, source_jobs)) for track in edition_tracks(edition)]
    repeated_jobs = {}
    for track, job in tracks:
        if job:
            repeated_jobs.setdefault(identity(track), set()).add(job)
    for track, job in tracks:
        repeated = repeated_jobs.get(identity(track))
        yield track, job or (next(iter(repeated)) if repeated and len(repeated) == 1 else None)


def _with_resolved_album(track, job):
    if not job or not _label(job.album):
        return track
    return replace(track, album=job.album, recording_mbid=track.recording_mbid or normalize_mbid(job.recording_mbid))


def _same_recording(track, job):
    track_mbid = normalize_mbid(track.recording_mbid)
    job_mbid = normalize_mbid(job.recording_mbid)
    return not (track_mbid and job_mbid and track_mbid != job_mbid)


def _acquisition_job(track, state, jobs, music_key):
    if state in (None, "ambiguous") or not all(_label(x) for x in (track.artist, track.album, track.title)):
        return None
    identity = (music_key(track.artist), music_key(track_job_album(track.album, track.title)))
    job = jobs.get(identity)
    if job is None or not _same_recording(track, job):
        return None
    # The job key folds punctuation. Require the saved labels to agree too.
    if tuple(map(_label, (job.artist, job.album, job.title))) == tuple(map(_label, (track.artist, track.album, track.title))):
        return job
    return None


def edition_detail(edition, owned, jobs, music_key, now):
    tracks = tuple(_tracks_with_sparse_jobs(edition, _source_jobs(jobs)))
    matches = None if owned is None else match_recordings(
        (_with_resolved_album(track, job) for track, job in tracks), owned,
    )
    rows = []
    for offset, (track, sparse_job) in enumerate(tracks):
        match = matches[offset] if matches is not None else None
        state = match.state if match else None
        job = sparse_job or _acquisition_job(track, state, jobs, music_key)
        rows.append({
            **asdict(track),
            "match_state": state,
            "song_id": match.song_id if match else None,
            "acquisition_status": job.status if job else None,
        })
        if job:
            rows[-1]["acquisition_key"] = {"artist": job.artist, "job_album": job.job_album}
    owned_count = None if matches is None else sum(match.state == "owned" for match in matches)
    return {**_summary(edition, owned_count, now), "tracks": rows}
