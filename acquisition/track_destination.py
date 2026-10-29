"""Where a downloaded song goes in the library.

A song joins the folder the library already uses for its album, so an album stored with a year
in its folder name never gets a second folder. Only a missing album (or artist) gets a new
folder, named as an album import names it. Ambiguity refuses rather than guesses.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Callable


class DestinationError(OSError):
    """The song has no single, safe place in the library."""


def _strip_year(name: str) -> str:
    """A folder name without a release year, in the common shapes: (1999), [1999], 1999 - ."""
    name = re.sub(r"\s*[\(\[]\s*(?:19|20)\d{2}\s*[\)\]]", " ", name)
    name = re.sub(r"^\s*(?:19|20)\d{2}\s*[-_.]\s+", "", name)
    name = re.sub(r"\s+[-_.]\s*(?:19|20)\d{2}\s*$", "", name)
    return name


def _real_subdirectories(parent: Path) -> list[Path]:
    try:
        return [p for p in parent.iterdir() if p.is_dir() and not p.is_symlink()]
    except OSError as exc:
        raise DestinationError(f"Could not read {parent.name or parent}") from exc


def _single_match(candidates: list[Path], what: str) -> Path | None:
    if len(candidates) > 1:
        raise DestinationError(f"More than one existing {what} folder matches; not choosing between them.")
    return candidates[0] if candidates else None


def plan_destination(
    music_root: Path,
    artist: str,
    album: str,
    *,
    safe_folder_name: Callable[[str], str],
    music_key: Callable[[str], str],
) -> Path:
    """The album folder for the song: the library's own when it exists, else the usual new one.

    The folder may not exist yet; the importer creates it. Raises ``DestinationError`` when two
    folders match, or when the matching path is a symlink or not a directory.
    """
    artist_name, album_name = safe_folder_name(artist), safe_folder_name(album)
    artist_dir = music_root / artist_name
    if artist_dir.is_symlink() or (artist_dir.exists() and not artist_dir.is_dir()):
        raise DestinationError("The artist path is a symlink or not a directory.")
    if not artist_dir.exists():
        artist_dir = _single_match(
            [p for p in _real_subdirectories(music_root) if music_key(p.name) == music_key(artist)],
            "artist",
        ) or artist_dir
    if not artist_dir.exists():
        return artist_dir / album_name

    album_dir = artist_dir / album_name
    if album_dir.is_symlink() or (album_dir.exists() and not album_dir.is_dir()):
        raise DestinationError("The album path is a symlink or not a directory.")
    if album_dir.exists():
        return album_dir
    album_key = music_key(album)
    existing = _single_match(
        [p for p in _real_subdirectories(artist_dir) if music_key(_strip_year(p.name)) == album_key],
        "album",
    )
    return existing or album_dir
