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
