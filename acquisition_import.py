"""Safety-critical filesystem operations for importing completed albums.

The orchestration layer remains responsible for choosing a verified source and
recording acquisition state. This module stages only the expected tracks,
prevents destination overwrite, checks storage identity, and rolls back partial
moves when it is safe to do so.
"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Callable, Any

from acquisition_completion import match_completed_album_files


def import_matched_album_files(
    source: str | Path,
    destination: str | Path,
    candidate: dict[str, Any],
    expected_music_root: str | Path | None = None,
    expected_device: int | None = None,
    *,
    match_files: Callable[[str | Path, dict[str, Any]], dict[str, Path] | None]
    | None = None,
) -> None:
    """Stage verified expected tracks and publish the album without overwriting.

    Unrelated files in the source folder are deliberately left behind. On a
    failed move, staged tracks are restored when storage identity is unchanged;
    otherwise the recovery manifest and staged data are retained for recovery.
    """
    matcher = match_files or match_completed_album_files
    matched = matcher(source, candidate)
    if not matched:
        raise OSError("Expected tracks no longer match files in the completed folder")

    destination = Path(destination)
    parent = destination.parent

    # Refuse existing destinations, including broken symlinks, before
    # creating any staging directory.
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(str(destination))
    if parent.is_symlink() or not parent.is_dir():
        raise OSError("Import destination parent is not a real directory")

    manifest_name = ".navidrome-import.json"
    if any(name.casefold() == manifest_name.casefold() for name in matched):
        raise OSError("A track name conflicts with the reserved import manifest")

    def assert_music_storage_identity() -> None:
        # If a mount disappears, the same path can expose the underlying local
        # directory. Device checks prevent continuing an import on that fallback.
        if expected_device is None:
            return
        if expected_music_root is None:
            raise OSError("Music-library root is required when checking storage identity")
        root = Path(expected_music_root)
        if root.stat().st_dev != expected_device or parent.stat().st_dev != expected_device:
            raise OSError("Music-library filesystem changed during import; refusing further writes")

    assert_music_storage_identity()
    staging = parent / (".navidrome-import-" + uuid.uuid4().hex)
    staging.mkdir(parents=True, exist_ok=False)
    manifest = staging / manifest_name
    manifest_data = {
        "source": str(Path(source).resolve()),
        "destination": str(destination),
        "tracks": {
            name: int(path.stat().st_size)
            for name, path in matched.items()
        },
    }
    moved: list[tuple[Path, Path]] = []
    try:
        manifest.write_text(json.dumps(manifest_data, ensure_ascii=False), encoding="utf-8")
        for expected_name, actual_path in matched.items():
            assert_music_storage_identity()
            expected_size = int(manifest_data["tracks"][expected_name])
            try:
                source_stat = actual_path.lstat()
            except OSError as exc:
                raise OSError(f"Expected track disappeared before staging: {expected_name}") from exc
            if not actual_path.is_file() or actual_path.is_symlink() or source_stat.st_size != expected_size:
                raise OSError(f"Expected track changed before staging: {expected_name}")
            staged_path = staging / expected_name
            shutil.move(str(actual_path), str(staged_path))
            # Record the move before post-move validation so rollback can restore
            # even a path swapped for a symlink between lstat and move.
            moved.append((staged_path, actual_path))
            staged_stat = staged_path.lstat()
            if staged_path.is_symlink() or not staged_path.is_file() or staged_stat.st_size != expected_size:
                raise OSError(f"Staged track failed validation: {expected_name}")
        assert_music_storage_identity()
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(str(destination))
        # Rename first while the recovery manifest is present. If the process
        # dies immediately afterward, reconciliation can still identify this
        # complete import and remove the manifest safely.
        staging.rename(destination)
        try:
            (destination / manifest_name).unlink()
        except OSError:
            # A completed destination plus its manifest is recoverable on restart.
            pass
    except Exception:
        rollback_complete = True
        for staged_path, original_path in reversed(moved):
            if staged_path.exists() and not original_path.exists():
                try:
                    assert_music_storage_identity()
                    shutil.move(str(staged_path), str(original_path))
                except OSError:
                    # If the library mount changed, leave staged data and its
                    # manifest untouched for later/manual recovery.
                    rollback_complete = False
            elif staged_path.exists() or not original_path.exists():
                rollback_complete = False
        try:
            if rollback_complete:
                manifest.unlink(missing_ok=True)
                staging.rmdir()
        except OSError:
            # Keep the manifest and remaining staged tracks for restart recovery.
            pass
        raise
