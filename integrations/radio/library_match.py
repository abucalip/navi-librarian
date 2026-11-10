"""Is a radio song already in the Navidrome library? One search, exact match on artist and title."""
from __future__ import annotations

from integrations.navidrome.client import items


def _same(a: str | None, b: str | None) -> bool:
    return " ".join(str(a or "").split()).casefold() == " ".join(str(b or "").split()).casefold()


def find_song(api_call, artist: str, title: str) -> dict | None:
    """The library song with exactly this artist and title (ignoring case and spacing), or None.

    Costs one Navidrome search. The caller keeps the answer for the song, so it is not repeated
    on every client request.
    """
    root = api_call("search3", query=f"{artist} {title}", artistCount=0, albumCount=0, songCount=20)
    songs = items((root.get("searchResult3") or {}).get("song"))
    return next((song for song in songs
                 if _same(song.get("artist"), artist) and _same(song.get("title"), title)), None)


class OwnedCache:
    """Remembers library answers per song so the Heard list does not search Navidrome on every refresh.

    A song found in the library is kept; a song not found is kept for ``miss_seconds`` so a later
    import shows up. A failed lookup is not kept, so it is retried.
    """

    def __init__(self, miss_seconds: float = 300.0, clock=None):
        import threading
        import time
        self._miss_seconds = miss_seconds
        self._clock = clock or time.monotonic
        self._items: dict[tuple[str, str], tuple[bool, float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(artist: str, title: str) -> tuple[str, str]:
        return (" ".join(artist.split()).casefold(), " ".join(title.split()).casefold())

    def owned(self, api_call, artist: str | None, title: str | None) -> bool:
        if not artist or not title:
            return False
        key = self._key(artist, title)
        with self._lock:
            cached = self._items.get(key)
        if cached and (cached[0] or self._clock() - cached[1] < self._miss_seconds):
            return cached[0]
        try:
            found = find_song(api_call, artist, title) is not None
        except Exception:
            return False
        with self._lock:
            self._items[key] = (found, self._clock())
        return found


OWNED = OwnedCache()
