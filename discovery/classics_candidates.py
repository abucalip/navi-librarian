"""Candidate collection policy for the classics discovery list.

Provider access and the final ranking pipeline are injected by the server adapter.
"""
from collections.abc import Callable, Iterable
from typing import Any


def _listeners(item: dict[str, Any]) -> int:
    return int(item.get("listeners") or 0)


def _with_listener_aliases(album: dict[str, Any]) -> dict[str, Any]:
    out = dict(album)
    listeners = album.get("listeners")
    if listeners is not None:
        out["listeners"] = int(listeners)
    playcount = album.get("playcount")
    if playcount is not None:
        out["playcount"] = int(playcount)
    return out


def collect_classic_candidates(
    library_artists: Iterable[dict[str, Any]],
    owned: set[tuple[str, str]],
    *,
    top_albums_lookup: Callable[..., list[dict[str, Any]]],
    music_key: Callable[[str], str],
    is_album_candidate: Callable[[dict[str, Any]], bool],
    pause: Callable[[], Any] | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    """Collect unowned eligible top-album candidates, retaining legacy deduplication.

    Artists are visited in descending library-album-count order. For duplicate
    normalized artist/album identities, the record with the greatest
    listener count wins. The optional pause callback is invoked after each fifth
    artist (excluding the first) to preserve provider pacing without owning a timer.
    """
    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    ordered_artists = sorted(
        library_artists,
        key=lambda item: item["album_count"],
        reverse=True,
    )
    for index, artist_record in enumerate(ordered_artists):
        artist = artist_record["name"]
        for album in top_albums_lookup(artist, limit=8):
            key = (music_key(album["artist"]), music_key(album["album"]))
            if key in owned:
                continue
            old = candidates.get(key)
            if old is None or _listeners(album) > _listeners(old):
                candidates[key] = {
                    **_with_listener_aliases(album),
                    "discovery_type": "classic",
                    "discovery_source": "ListenBrainz artist top albums",
                    "artist_library_album_count": artist_record["album_count"],
                }
        if pause is not None and index and index % 5 == 0:
            pause()

    return {
        key: item for key, item in candidates.items()
        if is_album_candidate(item)
    }
