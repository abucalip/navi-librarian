"""Save an Inbox feed's owned tracks as one rolling private Navidrome playlist."""

from contextlib import closing
from dataclasses import dataclass
from fcntl import LOCK_EX, LOCK_NB, flock
from pathlib import Path
from typing import Literal
from uuid import uuid4

from discovery.playlist_inbox import edition_tracks
from discovery.recording_match import match_recordings
from discovery.search.index import OwnedData
from integrations.navidrome.playlists import PlaylistClient, PlaylistProviderError
from intelligence.store import open_writer
from intelligence.store.playlist_editions import (
    CopyIntent,
    ManagedCopy,
    advance_copy_intent,
    current_edition_id,
    get_copy_intent,
    get_edition,
    get_managed_copy,
    record_copy_intent,
    save_managed_copy,
)


@dataclass(frozen=True)
class SyncResult:
    state: Literal["synced", "busy", "pending", "conflict", "missing", "unlinked", "superseded", "index_unavailable"]
    playlist_id: str | None = None


def sync_edition(store_path, navidrome: PlaylistClient, *, feed_key: str, edition_id: int,
                 name: str, owned: OwnedData | None) -> SyncResult:
    """Sync the caller's selected feed edition using the target's owned index.

    A feed key identifies a recurring feed across upstream edition IDs. The
    worker or caller selects that feed's latest edition. A missing owned index
    needs a retry, while a complete index with zero matches can clear the copy.
    """
    if not feed_key.strip() or not name.strip():
        raise ValueError("A feed key and playlist name are required.")
    if owned is None:
        return SyncResult("index_unavailable")
    path = Path(store_path).resolve()

    # Web and worker share this directory. Closing the descriptor (including on
    # process exit) releases the lock without holding a SQLite write transaction over HTTP.
    with path.with_suffix(".playlist-sync.lock").open("a") as lock:
        try:
            flock(lock, LOCK_EX | LOCK_NB)
        except BlockingIOError:
            return SyncResult("busy")
        with closing(open_writer(path)) as db:
            edition = get_edition(db, edition_id)
            if edition is None:
                raise ValueError("Playlist Inbox edition does not exist.")
            snapshot = edition.snapshot
            if current_edition_id(db, snapshot.source_kind, snapshot.source_key) != edition_id:
                return SyncResult("superseded")
            matches = match_recordings(edition_tracks(edition), owned)
            song_ids = tuple(match.song_id for match in matches if match.song_id is not None)
            return _sync(db, navidrome, feed_key, edition_id, name, song_ids)


def _sync(db, navidrome, feed_key, edition_id, name, song_ids):
    link = get_managed_copy(db, feed_key)
    if link is not None and link.unlinked:
        return SyncResult("unlinked")
    intent = get_copy_intent(db, feed_key)
    if intent is None and link is not None:
        return SyncResult("conflict")
    if intent is not None and intent.target_key != navidrome.target_key:
        return SyncResult("conflict")
    if intent is not None:
        if edition_id < intent.edition_id:
            return SyncResult("superseded")
        if edition_id > intent.edition_id:
            intent = advance_copy_intent(db, feed_key, intent, edition_id)

    if link is None:
        intent, link, state = _link_copy(db, navidrome, feed_key, edition_id, intent)
        if state is not None:
            return SyncResult(state)

    playlist = navidrome.get(link.playlist_id)
    if playlist is None:
        return SyncResult("missing")
    staging_name = _staging_name(intent)
    comment = f"Managed by Discair · {intent.token}"
    if playlist.id != link.playlist_id or playlist.owner != navidrome.owner:
        return SyncResult("conflict")
    if playlist.comment != comment and (playlist.name != staging_name or playlist.song_count):
        return SyncResult("conflict")

    if playlist.name == staging_name or playlist.public:
        private_name = name if playlist.name == staging_name else playlist.name
        navidrome.make_private(playlist.id, name=private_name, comment=comment)
        playlist = navidrome.get(link.playlist_id)
        _verify_private(playlist, link.playlist_id, navidrome.owner, comment)
        if playlist.name != private_name:
            raise PlaylistProviderError("Navidrome did not confirm the managed playlist's name.")

    if playlist.song_ids != song_ids or playlist.song_count != len(song_ids):
        playlist = navidrome.replace(playlist, song_ids)
        _verify_private(playlist, link.playlist_id, navidrome.owner, comment)
        if playlist.song_ids != song_ids or playlist.song_count != len(song_ids):
            raise PlaylistProviderError("Navidrome did not confirm the complete ordered playlist.")
    return SyncResult("synced", link.playlist_id)


def _link_copy(db, navidrome, feed_key, edition_id, intent):
    if intent is None:
        # A read first lets auth and availability failures retry before an intent exists.
        navidrome.list()
        intent = CopyIntent(navidrome.target_key, uuid4().hex, edition_id)
        record_copy_intent(db, feed_key, intent)
        try:
            playlist = navidrome.create_empty(_staging_name(intent))
        except PlaylistProviderError:
            return intent, None, "pending"
    else:
        matches = [p for p in navidrome.list() if p.name == _staging_name(intent) and p.owner == navidrome.owner]
        if len(matches) != 1:
            return intent, None, "conflict" if matches else "pending"
        playlist = matches[0]

    if playlist.name != _staging_name(intent) or playlist.owner != navidrome.owner or playlist.song_count:
        return intent, None, "conflict"
    link = ManagedCopy(feed_key, playlist.id)
    if not save_managed_copy(db, link, expected=None):
        return intent, None, "conflict"
    return intent, link, None


def _staging_name(intent):
    return f"Discair setup · {intent.token}"


def _verify_private(playlist, playlist_id, owner, comment):
    if (playlist is None or playlist.id != playlist_id or playlist.public
            or playlist.owner != owner or playlist.comment != comment):
        raise PlaylistProviderError("Navidrome did not confirm the private managed playlist.")
