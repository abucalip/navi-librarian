"""Disc numbers for the album page's tracklist.

Navidrome numbers a song within its disc (``discNumber`` plus ``track``), while the outside
tracklist providers number tracks straight through the whole album. For an album whose library
songs span several discs, owned tracks keep their own disc and number, and a track the library
lacks takes the disc implied by its neighbours in the provider's straight-through order.
Single-disc albums are left exactly as they were (no ``disc_number`` key).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def disc_of(song: dict[str, Any]) -> int:
    """The song's disc; a song with no disc tag is on disc 1."""
    return song.get("disc_number") or 1


def is_multi_disc(songs: Iterable[dict[str, Any]]) -> bool:
    return len({disc_of(song) for song in songs}) > 1


def place_unmatched(count: int, known: dict[int, tuple[int, int]]) -> dict[int, tuple[int, int]]:
    """``(disc, track)`` for each position in a straight-through list of ``count`` tracks.

    ``known`` maps the positions the library has to their own ``(disc, track)``. A gap position
    counts back from the next known track while that stays at track 1 or higher (it is on that
    track's disc), otherwise forward from the previous known track. Known positions pass through.
    """
    placed = dict(known)
    ordered = sorted(known)
    for index in range(count):
        if index in known or not ordered:
            continue
        before = max((j for j in ordered if j < index), default=None)
        after = min((k for k in ordered if k > index), default=None)
        if after is not None:
            disc, track = known[after]
            if track - (after - index) >= 1:
                placed[index] = (disc, track - (after - index))
                continue
        if before is not None:
            disc, track = known[before]
            placed[index] = (disc, track + (index - before))
        else:
            disc, track = known[after]
            placed[index] = (disc, 1)
    return placed
