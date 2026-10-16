"""Read-only MusicBrainz tag audit for a bounded music-library batch."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


AUDIO_EXTENSIONS = {
    ".flac", ".mp3", ".m4a", ".mp4", ".ogg",
    ".opus", ".wma", ".aiff", ".aif", ".wav",
}
ID_FIELDS = {
    "track_mbid": {"musicbrainz_trackid", "musicbrainz_track_id"},
    "album_mbid": {"musicbrainz_albumid", "musicbrainz_album_id"},
    "artist_mbid": {"musicbrainz_artistid", "musicbrainz_artist_id"},
    "albumartist_mbid": {"musicbrainz_albumartistid", "musicbrainz_album_artist_id"},
}


def scan_missing_mbids(
    music_dir: Path | str,
    max_files: int = 1000,
    offset: int = 0,
    *,
    audio_file_reader: Callable[..., Any],
) -> dict[str, Any] | str:
    """Inspect a bounded, sorted batch without modifying audio files."""
    root = Path(music_dir)
    if not root.is_dir():
        return f"Music directory is unavailable: {root}"
    if not 1 <= max_files <= 5000:
        return "max_files must be between 1 and 5000."
    if offset < 0:
        return "offset must be non-negative."

    files = sorted(
        path for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )
    batch = files[offset:offset + max_files]
    missing = []
    unreadable = 0

    for path in batch:
        try:
            audio = audio_file_reader(path, easy=False)
            if audio is None:
                unreadable += 1
                continue
            tags = audio.tags or {}
            normalized = {str(key).casefold(): value for key, value in tags.items()}
            absent = []
            for field, keys in ID_FIELDS.items():
                values = [normalized[key] for key in keys if key in normalized]
                has_value = any(
                    str(value).strip()
                    for group in values
                    for value in (group if isinstance(group, (list, tuple)) else [group])
                )
                if not has_value:
                    absent.append(field)
            if absent:
                missing.append({
                    "file": str(path.relative_to(root)),
                    "missing_ids": absent,
                })
        except Exception:
            unreadable += 1

    return {
        "directory": str(root),
        "total_audio_files_found": len(files),
        "offset": offset,
        "files_in_batch": len(batch),
        "files_with_missing_ids": len(missing),
        "unreadable_files": unreadable,
        "next_offset": offset + len(batch),
        "more_files_remaining": offset + len(batch) < len(files),
        "results": missing,
        "read_only": True,
    }
