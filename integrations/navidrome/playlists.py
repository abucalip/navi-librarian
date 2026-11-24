"""Navidrome playlist transport for the Inbox's managed copies."""

from dataclasses import dataclass
from hashlib import sha256
import json

import httpx

from .client import NavidromeAPIError, api_call, items


class PlaylistProviderError(RuntimeError):
    """Navidrome failed to handle or confirm a playlist operation."""


@dataclass(frozen=True)
class Playlist:
    id: str
    name: str
    owner: str
    comment: str
    public: bool
    song_count: int
    song_ids: tuple[str, ...]


def _playlist(row):
    if not isinstance(row, dict):
        raise PlaylistProviderError("Navidrome did not return a playlist.")
    song_ids = tuple(entry.get("id") if isinstance(entry, dict) else None for entry in items(row.get("entry")))
    playlist_id = row.get("id")
    count = row.get("songCount")
    public = row.get("public")
    if (not isinstance(playlist_id, str) or not playlist_id or type(count) is not int or count < 0
            or (public is not None and type(public) is not bool)
            or any(not isinstance(song_id, str) or not song_id for song_id in song_ids)):
        raise PlaylistProviderError("Navidrome returned invalid playlist data.")
    return Playlist(playlist_id, row.get("name", ""), row.get("owner", ""), row.get("comment", ""),
                    bool(public), count, song_ids)


class PlaylistClient:
    """Bind one sync to a fixed Navidrome server and account."""

    def __init__(self, config, *, client_factory=None):
        base_url, self.owner, password = config
        base_url = base_url.rstrip("/")
        self._config = (base_url, self.owner, password)
        self._client_factory = client_factory
        self.target_key = sha256(json.dumps([base_url, self.owner]).encode()).hexdigest()

    def _call(self, method, **params):
        try:
            # Form POST keeps ordered repeated parameters and avoids replay of a mutating GET.
            return api_call(method, lambda: self._config, client_factory=self._client_factory,
                            form_post=True, **params)
        except NavidromeAPIError as error:
            if method == "getPlaylist" and error.code == 70:
                return {}
            raise PlaylistProviderError("Navidrome refused a playlist operation.") from None
        except (httpx.HTTPError, ValueError, AttributeError):
            raise PlaylistProviderError("Navidrome did not confirm a playlist operation.") from None

    def list(self):
        listing = self._call("getPlaylists").get("playlists")
        if not isinstance(listing, dict):
            raise PlaylistProviderError("Navidrome did not return a playlist listing.")
        return tuple(_playlist(row) for row in items(listing.get("playlist")))

    def get(self, playlist_id):
        root = self._call("getPlaylist", id=playlist_id)
        return _playlist(root.get("playlist")) if root else None

    def scan_marker(self):
        """Return the idle scan marker, or None while the scanner is busy or failed."""
        status = self._call("getScanStatus").get("scanStatus")
        if not isinstance(status, dict) or type(status.get("scanning")) is not bool:
            raise PlaylistProviderError("Navidrome did not return valid scan status.")
        if status["scanning"] or status.get("error"):
            return None
        last_scan, count = status.get("lastScan"), status.get("count")
        if (last_scan is not None and not isinstance(last_scan, str)) or type(count) is not int or count < 0:
            raise PlaylistProviderError("Navidrome did not return a valid scan marker.")
        return last_scan, count

    def search_songs(self, _method, **params):
        """Read a search3 inventory page from the same target as the playlist writes."""
        root = self._call("search3", **params)
        result = root.get("searchResult3")
        if not isinstance(result, dict) or any(
            not isinstance(song, dict)
            or not isinstance(song.get("id"), str) or not song["id"]
            or not isinstance(song.get("title"), str) or not song["title"]
            for song in items(result.get("song"))
        ):
            raise PlaylistProviderError("Navidrome did not return a valid song inventory page.")
        return root

    def create_empty(self, name):
        return _playlist(self._call("createPlaylist", name=name).get("playlist"))

    def make_private(self, playlist_id, *, name, comment):
        self._call("updatePlaylist", playlistId=playlist_id, name=name, comment=comment, public="false")

    def replace(self, playlist, song_ids):
        if song_ids:
            root = self._call("createPlaylist", playlistId=playlist.id, songId=song_ids)
            return _playlist(root.get("playlist"))

        # Navidrome 0.64.2 skips the track update when createPlaylist has zero songId values.
        # Send all zero-based positions together so Navidrome clears them in one transaction.
        if playlist.song_count != len(playlist.song_ids):
            raise PlaylistProviderError("Navidrome did not return every playlist track for clearing.")
        positions = tuple(range(playlist.song_count))
        self._call("updatePlaylist", playlistId=playlist.id, songIndexToRemove=positions)
        return self.get(playlist.id)
