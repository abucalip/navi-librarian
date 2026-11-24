"""Worker entry point for refreshing already-linked Playlist Inbox copies."""

from contextlib import closing
from time import time

from app.worker_schedule import NOT_READY
from discovery.playlist_sync import reconcile_linked
from discovery.search.index import SongInventoryError, build_owned_data, fetch_song_inventory
from integrations.navidrome.client import items
from integrations.navidrome.playlists import PlaylistClient, PlaylistProviderError
from intelligence.store import open_readonly
from intelligence.store.playlist_editions import list_linked_feed_keys


class PlaylistReconciler:
    """Keep a scan checkpoint for the lifetime of one worker."""

    def __init__(self, store_path):
        self._store_path = store_path
        self._checkpoint = None

    def run_once(self, navidrome: PlaylistClient, *, worker_refresh: bool = False):
        """Refresh after a scan change or a worker refresh, retrying incomplete passes."""
        with closing(open_readonly(self._store_path)) as db:
            feeds = list_linked_feed_keys(db, navidrome.target_key)
        if not feeds:
            self._checkpoint = None
            return None

        try:
            marker = navidrome.scan_marker()
            if marker is None:
                return NOT_READY
            checkpoint = (navidrome.target_key, marker, feeds)
            if not worker_refresh and checkpoint == self._checkpoint:
                return None

            self._checkpoint = None
            songs = fetch_song_inventory(navidrome.search_songs, items)
            owned = build_owned_data(
                generation=navidrome.target_key, built_at=time(), artists=(), albums=(), songs=songs,
            )
            if not reconcile_linked(self._store_path, navidrome, owned, scan_marker=marker):
                return NOT_READY
        except (PlaylistProviderError, SongInventoryError):
            return NOT_READY

        self._checkpoint = checkpoint
        return None
