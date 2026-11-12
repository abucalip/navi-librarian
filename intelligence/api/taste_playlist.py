"""Body builder for ``POST /api/playlists/taste`` (docs/redesign.md A8b item 1).

Turns one taste genre into a Navidrome playlist: the owner's own songs of that genre, a random
sample, written with the Subsonic ``createPlaylist`` call. Pure rules live here; the two Navidrome
calls are passed in, so the module is tested without a server. Nothing is sent to a provider.
"""
import random
from typing import Any, Callable

PAGE = 500
MAX_PAGES = 20
PLAYLIST_SIZE = 50
MAX_GENRE_LENGTH = 100


class NoSongs(LookupError):
    """The library has no song of that genre."""


def clean_genre(value: Any) -> str | None:
    """The genre as a trimmed string, or None when it is missing, not text, empty or too long."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > MAX_GENRE_LENGTH:
        return None
    return text


def playlist_name(genre: str) -> str:
    return f"{genre} (Discair)"


def pick_song_ids(songs: list[dict[str, Any]], size: int = PLAYLIST_SIZE, rng: random.Random | None = None) -> list[str]:
    """Up to ``size`` distinct song ids in random order."""
    ids = list(dict.fromkeys(str(s["id"]) for s in songs if s.get("id")))
    return (rng or random).sample(ids, min(size, len(ids)))


def create_genre_playlist(
    genre: str,
    songs_by_genre: Callable[[str, int], list[dict[str, Any]]],
    create_playlist: Callable[[str, list[str]], str],
    rng: random.Random | None = None,
) -> dict[str, Any]:
    """Make the playlist and return ``{playlist_id, name, genre, song_count}``; raises ``NoSongs`` when empty.

    ``songs_by_genre(genre, offset)`` returns one page of songs; ``create_playlist(name, song_ids)`` returns the new id.
    """
    songs: list[dict[str, Any]] = []
    for page in range(MAX_PAGES):
        batch = songs_by_genre(genre, page * PAGE)
        songs.extend(batch)
        if len(batch) < PAGE:
            break
    ids = pick_song_ids(songs, rng=rng)
    if not ids:
        raise NoSongs(genre)
    name = playlist_name(genre)
    return {"playlist_id": create_playlist(name, ids), "name": name, "genre": genre, "song_count": len(ids)}
