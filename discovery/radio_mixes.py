"""Radio preview actions, separate from recurring managed Inbox feeds."""

from contextlib import closing, contextmanager
from fcntl import LOCK_EX, LOCK_NB, flock
from time import time

from acquisition.state import read_track_statuses
from discovery.playlist_download import download_track
from discovery.playlist_inbox import edition_detail
from discovery.recording_match import match_recordings
from discovery.search.index import build_owned_data, fetch_song_inventory
from integrations.listenbrainz.jspf import PlaylistTrack
from integrations.navidrome.client import items
from integrations.navidrome.playlists import PlaylistClient, PlaylistProviderError
from intelligence.store import open_readonly, open_writer
from intelligence.store.playlist_editions import PlaylistEdition, PlaylistSnapshot
from intelligence.store.radio_mixes import create_preview, get_preview, record_save


class MixActionError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def track_source(row):
    return PlaylistTrack(**{key: row.get(key) for key in (
        "position", "recording_mbid", "title", "artist", "album", "duration_ms",
        "conflicting_recording_mbids", "release_mbid",
    )})


def store_preview(path, navidrome, payload):
    with action_lock(path), closing(open_writer(path)) as db:
        return create_preview(db, navidrome.target_key, payload, time())


def read_preview(path, navidrome, preview_id):
    with closing(open_readonly(path)) as db:
        preview = get_preview(db, preview_id, navidrome.target_key)
    if preview is None:
        raise MixActionError(404, "This mix preview is no longer available. Generate a new preview.")
    return preview


@contextmanager
def action_lock(path):
    with path.with_suffix(".radio-mixes.lock").open("a") as lock:
        try:
            flock(lock, LOCK_EX | LOCK_NB)
        except BlockingIOError as error:
            raise MixActionError(409, "Another mix action is running. Try again shortly.") from error
        yield


def current_library(navidrome):
    marker = navidrome.scan_marker()
    if marker is None:
        raise MixActionError(503, "The library is scanning. Try again when it finishes.")
    songs = fetch_song_inventory(navidrome.search_songs, items)
    owned = build_owned_data(generation=navidrome.target_key, built_at=time(), artists=(), albums=(), songs=songs)
    if navidrome.scan_marker() != marker:
        raise MixActionError(503, "The library changed. Try again.")
    return owned, marker


def matched_rows(payload, owned):
    rows = payload["tracks"]
    if owned is None:
        return [{**row, "match_state": None, "song_id": None} for row in rows]
    if payload["kind"] == "artist":
        # Artist Radio selects exact local files, including untagged distinct versions.
        songs = {song["id"]: song for song in owned.songs}
        matches = []
        for row in rows:
            song = songs.get(row["song_id"])
            same = song is not None and all(row.get(key) == song.get(other) for key, other in (
                ("title", "name"), ("artist", "artist"), ("album", "album"),
                ("recording_mbid", "recording_mbid"),
            ))
            if same and row.get("duration_ms") is not None:
                same = song.get("duration") is not None and row["duration_ms"] == song["duration"] * 1000
            matches.append({**row, "match_state": "owned" if same else "missing",
                            "song_id": row["song_id"] if same else None})
        return matches
    matches = match_recordings(tuple(track_source(row) for row in rows), owned)
    return [{**row, "match_state": match.state, "song_id": match.song_id}
            for row, match in zip(rows, matches)]


def preview_rows(librarian, preview, owned):
    payload = preview["payload"]
    if payload["kind"] == "artist":
        return matched_rows(payload, owned)
    snapshot = PlaylistSnapshot("radio", preview["id"], preview["id"], {}, tuple(payload["tracks"]))
    edition = PlaylistEdition(f"radio-{preview['id']}", snapshot, preview["created_at"])
    return edition_detail(edition, owned, read_track_statuses(librarian.DISCOVERY_DB),
                          librarian._music_key, time())["tracks"]


def download_preview_track(librarian, path, preview_id, position):
    navidrome = PlaylistClient(librarian._navidrome_config())
    preview = read_preview(path, navidrome, preview_id)
    payload = preview["payload"]
    if payload["kind"] != "discovery" or position >= len(payload["tracks"]):
        raise MixActionError(404, "Discovery track not found.")
    row = payload["tracks"][position]
    # Reuse fresh complete ownership checks, metadata resolution and acquisition deduplication.
    return download_track(librarian, f"radio-{preview_id}", track_source(row))


def _verify(playlist, navidrome, preview_id, playlist_id):
    if (playlist is None or playlist.id != playlist_id or playlist.owner != navidrome.owner or playlist.public
            or playlist.comment != f"Discair saved mix · {preview_id}"):
        raise MixActionError(409, "Could not confirm this private playlist.")


def save_preview(librarian, path, preview_id):
    config = librarian._navidrome_config()
    navidrome = PlaylistClient(config)
    with action_lock(path), closing(open_writer(path)) as db:
        preview = get_preview(db, preview_id, navidrome.target_key)
        if preview is None:
            raise MixActionError(404, "Mix preview not found. Generate a new preview.")
        if preview["saved"]:
            return {"state": "saved", "playlist_id": preview["playlist_id"],
                    "saved_count": len(preview["save_songs"])}
        owned, marker = current_library(navidrome)
        if librarian._navidrome_config() != config:
            raise MixActionError(409, "The Navidrome connection changed. Generate a new preview.")
        songs = preview["save_songs"]
        new_intent = songs is None
        rows = preview_rows(librarian, preview, owned)
        confirmed = tuple(row["song_id"] for row in rows if row["song_id"])
        if new_intent:
            songs = confirmed
            if not songs:
                raise MixActionError(409, "This mix has no confirmed owned tracks to save.")
            positions = tuple(row["position"] for row in rows if row["song_id"])
            record_save(db, preview_id, songs=songs, positions=positions)
        elif any(rows[position]["song_id"] != song_id
                 for position, song_id in zip(preview["save_positions"], songs)):
            raise MixActionError(409, "Some selected tracks left the library. Generate a new preview.")

        staging = f"Discair mix setup · {preview_id}"
        playlist_id = preview["playlist_id"]
        if playlist_id:
            playlist = navidrome.get(playlist_id)
            if playlist is None:
                raise MixActionError(409, "The saved playlist was deleted. Generate a new preview to save again.")
        elif new_intent:
            playlist = navidrome.create_empty(staging)
        else:
            candidates = [p for p in navidrome.list() if p.name == staging and p.owner == navidrome.owner]
            if len(candidates) != 1:
                raise MixActionError(409, "The previous save is unconfirmed. Retry later; a second playlist will not be created.")
            playlist = navidrome.get(candidates[0].id)
        if not playlist_id:
            if (playlist is None or playlist.name != staging or playlist.owner != navidrome.owner
                    or playlist.song_count):
                raise MixActionError(409, "Could not safely identify the new empty playlist.")
            playlist_id = playlist.id
            record_save(db, preview_id, playlist_id=playlist_id)
        if playlist.id != playlist_id or playlist.owner != navidrome.owner:
            raise MixActionError(409, "Could not confirm the selected playlist owner.")
        comment = f"Discair saved mix · {preview_id}"
        if playlist.comment != comment and (playlist.name != staging or playlist.song_count):
            raise MixActionError(409, "The playlist was changed outside Discair. Generate a new preview.")
        navidrome.make_private(playlist_id, name=preview["payload"]["title"], comment=comment)
        playlist = navidrome.get(playlist_id)
        _verify(playlist, navidrome, preview_id, playlist_id)
        if playlist.name != preview["payload"]["title"]:
            raise PlaylistProviderError("Navidrome did not confirm the playlist name.")
        if navidrome.scan_marker() != marker or librarian._navidrome_config() != config:
            raise MixActionError(409, "The library or connection changed. Retry this save.")
        playlist = navidrome.replace(playlist, songs)
        _verify(playlist, navidrome, preview_id, playlist_id)
        if playlist.id != playlist_id or playlist.song_ids != songs or playlist.song_count != len(songs):
            raise PlaylistProviderError("Navidrome did not confirm every selected track.")
        record_save(db, preview_id, playlist_id=playlist_id, saved=True)
        return {"state": "saved", "playlist_id": playlist_id, "saved_count": len(songs)}
