"""Import-completion orchestration with injected persistence and filesystem services.

This module owns destination validation and the authoritative importing-status
guard. The legacy server remains a thin adapter for locks, status persistence,
path naming, and the hardened track importer.
"""
from __future__ import annotations

from pathlib import Path


def import_completed_source_locked(
    artist, album, source, music_root, candidate, *,
    safe_folder_name, update_status, import_matched_album_files, now,
):
    """Validate the destination and import only after status is persisted.

    The caller must hold the acquisition transition lock and arbitrate dismissal.
    No filesystem mutation may begin unless the authoritative importing state
    update succeeds. Dependencies are injected for direct-import regression tests.
    """
    try:
        music_root = Path(music_root).expanduser().resolve(strict=True)
    except (OSError, RuntimeError, TypeError, ValueError):
        music_root = None

    if music_root is None or not music_root.is_dir():
        update_status(artist, album, "library_mount_unavailable", {
            "source_folder": str(source), "downloads_path": str(Path(source).parent),
            "library_path": str(music_root),
        })
        return "failed"

    try:
        music_device = music_root.stat().st_dev
    except OSError:
        music_device = None
    if music_device is None:
        update_status(artist, album, "library_mount_unavailable", {
            "source_folder": str(source), "library_path": str(music_root),
        })
        return "failed"

    artist_dir = music_root / safe_folder_name(artist)
    album_dir = artist_dir / safe_folder_name(album)
    if artist_dir.is_symlink() or (artist_dir.exists() and not artist_dir.is_dir()):
        update_status(artist, album, "download_complete_move_failed", {
            "error": "Unsafe import destination: artist path is a symlink or not a directory.",
        })
        return "failed"

    if artist_dir.exists():
        try:
            resolved_artist = artist_dir.resolve(strict=True)
        except (OSError, RuntimeError):
            resolved_artist = None
        if resolved_artist is None or resolved_artist.parent != music_root:
            update_status(artist, album, "download_complete_move_failed", {
                "error": "Unsafe import destination: artist directory is outside the music root.",
            })
            return "failed"

    # exists() alone misses broken symlinks.
    if album_dir.exists() or album_dir.is_symlink():
        update_status(artist, album, "destination_exists", {
            "source_folder": str(source), "destination": str(album_dir),
        })
        return "failed"

    if not update_status(artist, album, "importing", {
        "source_folder": str(source), "destination": str(album_dir),
        "music_root_device": music_device,
    }):
        return "failed"

    try:
        if music_root.stat().st_dev != music_device:
            raise OSError("Music-library filesystem changed before import")
        artist_dir.mkdir(parents=True, exist_ok=True)
        if artist_dir.is_symlink() or not artist_dir.is_dir():
            raise OSError("Artist destination is not a real directory")
        resolved_artist = artist_dir.resolve(strict=True)
        if resolved_artist.parent != music_root:
            raise OSError("Artist destination resolves outside the music root")
        if album_dir.exists() or album_dir.is_symlink():
            raise FileExistsError(str(album_dir))
        if music_root.stat().st_dev != music_device or artist_dir.stat().st_dev != music_device:
            raise OSError("Music-library filesystem changed before import")
        import_matched_album_files(
            source, album_dir, candidate,
            expected_music_root=music_root, expected_device=music_device,
        )
    except OSError as exc:
        update_status(artist, album, "download_complete_move_failed", {
            "source_folder": str(source), "destination": str(album_dir),
            "error": str(exc), "downloads_path": str(Path(source).parent),
        })
        return "failed"
    except Exception as exc:
        update_status(artist, album, "download_complete_move_failed", {
            "source_folder": str(source), "destination": str(album_dir),
            "error": f"Unexpected import error ({type(exc).__name__}): {exc}",
            "downloads_path": str(Path(source).parent),
        })
        return "failed"

    update_status(artist, album, "imported", {
        "source_folder": str(source), "destination": str(album_dir),
        "source_username": candidate.get("username"), "imported_at": now(),
    })
    return "imported"
