"""Read ListenBrainz sources for the Playlist Inbox."""

from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite
from threading import Lock
import time
from urllib.parse import quote
from uuid import UUID

import httpx

from integrations.listenbrainz.client import request_headers
from integrations.listenbrainz.jspf import (
    ParsedPlaylist,
    PlaylistMetadata,
    parse_playlist,
    parse_playlist_metadata,
)


_API = "https://api.listenbrainz.org/1"
_PLAYLIST_PAGE_SIZE = 25
_MAX_PLAYLIST_PAGES = 100
_REQUEST_SPACING = 0.2  # Match the spacing of the recent-listens client.


@dataclass(frozen=True)
class RecordingRecommendation:
    recording_mbid: str
    score: float


@dataclass(frozen=True)
class RecommendationPage:
    last_updated: int | None  # Unix seconds, used to identify the source edition.
    recordings: tuple[RecordingRecommendation, ...]
    total_count: int


class PlaylistInboxClient:
    """Paced, read-only adapter using a caller-owned HTTP client.

    Reuse an instance across listing, detail and recommendation reads to share
    pacing. None means unconfigured. Empty results mean a successful read with
    no items. HTTP, transport and malformed-response errors propagate to the caller.
    """

    def __init__(
        self,
        client: httpx.Client,
        username: str | None,
        *,
        token: str | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._client = client
        self._username = quote((username or "").strip(), safe="")
        self._headers = request_headers(None if token is None else {"LISTENBRAINZ_TOKEN": token})
        self._clock = clock
        self._sleep = sleep
        self._lock = Lock()
        self._next_request = float("-inf")

    @property
    def configured(self) -> bool:
        return bool(self._username and self._headers.get("Authorization"))

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        with self._lock:
            wait = self._next_request - self._clock()
            if wait > 0:
                self._sleep(wait)
            self._next_request = self._clock() + _REQUEST_SPACING
            response = self._client.request(
                method, f"{_API}/{path}", headers=self._headers,
                timeout=15, follow_redirects=False, **kwargs,
            )
        return response.raise_for_status()

    def created_for_me(self) -> tuple[PlaylistMetadata, ...] | None:
        """Read the listing in source order. Details are fetched separately by MBID."""
        if not self.configured:
            return None
        playlists: list[PlaylistMetadata] = []
        seen: set[str] = set()
        for _ in range(_MAX_PLAYLIST_PAGES):
            offset = len(playlists)
            response = self._request(
                "GET", f"user/{self._username}/playlists/createdfor",
                params={"count": _PLAYLIST_PAGE_SIZE, "offset": offset},
            )
            body = response.json()
            if not isinstance(body, dict) or not isinstance(body.get("playlists"), list):
                raise ValueError("Invalid ListenBrainz playlist listing")
            page = body["playlists"]
            total = body.get("playlist_count")
            if type(total) is not int or total < offset + len(page) or body.get("offset") != offset:
                raise ValueError("Invalid ListenBrainz playlist pagination")
            for item in page:
                playlist = parse_playlist_metadata(item)
                mbid = playlist.playlist_mbid
                if mbid is None or mbid in seen:
                    raise ValueError("Missing or repeated MBID in ListenBrainz playlist listing")
                seen.add(mbid)
                playlists.append(playlist)
            if len(playlists) == total:
                return tuple(playlists)
            if not page:
                raise ValueError("ListenBrainz playlist listing ended before its reported total")
        raise ValueError("ListenBrainz playlist listing exceeded the page limit")

    def playlist_details(self, playlist_mbid: str) -> ParsedPlaylist | None:
        """Read one complete playlist, including its ordered track occurrences."""
        if not self.configured:
            return None
        mbid = str(UUID(playlist_mbid))
        playlist = parse_playlist(self._request("GET", f"playlist/{mbid}").json())
        if playlist.playlist_mbid != mbid:
            raise ValueError("ListenBrainz playlist detail does not match the requested MBID")
        return playlist

    def recording_recommendations(self, *, count: int = 25, offset: int = 0) -> RecommendationPage | None:
        """Read one ranked CF page. The default fetches the first 25 recommendations."""
        if not self.configured:
            return None
        if count <= 0 or offset < 0:
            raise ValueError("Recommendation count must be positive and offset non-negative")
        response = self._request(
            "GET", f"cf/recommendation/user/{self._username}/recording",
            params={"count": count, "offset": offset},
        )
        if response.status_code == 204:
            return RecommendationPage(None, (), 0)
        body = response.json()
        payload = body.get("payload") if isinstance(body, dict) else None
        if not isinstance(payload, dict) or not isinstance(payload.get("mbids"), list):
            raise ValueError("Invalid ListenBrainz recommendations payload")
        updated, total = payload.get("last_updated"), payload.get("total_mbid_count")
        if type(updated) is not int or updated < 0 or type(total) is not int or total < 0:
            raise ValueError("Invalid ListenBrainz recommendations metadata")
        recordings = tuple(_parse_recommendation(item) for item in payload["mbids"])
        return RecommendationPage(updated, recordings, total)

    def recording_metadata(self, mbids: tuple[str, ...]) -> dict:
        """Enrich one bounded CF page with a single recording metadata lookup."""
        ids = tuple(dict.fromkeys(mbids))
        body = self._request("POST", "metadata/recording/", json={
            "recording_mbids": ids, "inc": "artist release",
        }).json()
        if not isinstance(body, dict) or any(not isinstance(row, dict) for row in body.values()):
            raise ValueError("Invalid ListenBrainz recording metadata")
        return body


def _parse_recommendation(item: object) -> RecordingRecommendation:
    mbid = item.get("recording_mbid") if isinstance(item, dict) else None
    score = item.get("score") if isinstance(item, dict) else None
    if not isinstance(mbid, str) or type(score) not in (float, int) or not isfinite(score):
        raise ValueError("Invalid ListenBrainz recording recommendation")
    return RecordingRecommendation(str(UUID(mbid)), float(score))
