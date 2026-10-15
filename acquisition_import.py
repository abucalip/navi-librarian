"""Safety-critical filesystem operations for importing completed albums.

The orchestration layer remains responsible for choosing a verified source and
recording acquisition state. This module stages only expected tracks, prevents
destination overwrite, checks storage identity, and rolls back partial moves
when it is safe to do so.
"""
from __future__ import annotations

import errno
import json
import os
import shutil
import stat
import uuid
from pathlib import Path
from typing import Any, Callable

from acquisition_completion import match_completed_album_files


_DIRECTORY_FLAGS = (
    os.O_RDONLY
    | getattr(os, "O_DIRECTORY", 0)
    | getattr(os, "O_NOFOLLOW", 0)
)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _open_directory_path_no_follow(path: str | Path) -> int:
    """Open an absolute directory path without following any component symlink."""
    absolute = Path(path)
    if not absolute.is_absolute():
        raise OSError("Directory path must be absolute")

    current_fd = os.open(os.path.sep, _DIRECTORY_FLAGS)
    try:
        for component in absolute.parts[1:]:
            next_fd = os.open(component, _DIRECTORY_FLAGS, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except Exception:
        os.close(current_fd)
        raise


def _entry_stat(directory_fd: int, name: str):
    try:
        return os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _copy_fd_to_directory(
    source_fd: int,
    destination_fd: int,
    destination_name: str,
    source_stat,
) -> None:
    """Copy an opened regular file into a directory without following paths."""
    output_fd = os.open(
        destination_name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
        0o600,
        dir_fd=destination_fd,
    )
    try:
        with os.fdopen(os.dup(source_fd), "rb") as source_file:
            with os.fdopen(output_fd, "wb") as destination_file:
                output_fd = -1
                shutil.copyfileobj(source_file, destination_file)
                destination_file.flush()
                os.fsync(destination_file.fileno())
                os.fchmod(
                    destination_file.fileno(),
                    stat.S_IMODE(source_stat.st_mode),
                )
        os.utime(
            destination_name,
            ns=(source_stat.st_atime_ns, source_stat.st_mtime_ns),
            dir_fd=destination_fd,
            follow_symlinks=False,
        )
        copied = os.stat(
            destination_name, dir_fd=destination_fd, follow_symlinks=False
        )
        if not stat.S_ISREG(copied.st_mode) or copied.st_size != source_stat.st_size:
            raise OSError("Copied import track failed validation")
    except Exception:
        if output_fd >= 0:
            os.close(output_fd)
        try:
            os.unlink(destination_name, dir_fd=destination_fd)
        except OSError:
            pass
        raise


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
    """Stage verified tracks and publish without following mutable source paths.

    Source and destination-parent directories are pinned by file descriptor.
    Track moves, rollback, staging, and publication use descriptor-relative
    operations so a path swapped for a symlink cannot redirect file movement.
    """
    source_path = Path(source).expanduser()
    destination_path = Path(destination).expanduser()
    if source_path.is_symlink():
        raise OSError("Import source must not be a symlink")
    if destination_path.parent.is_symlink() or not destination_path.parent.is_dir():
        raise OSError("Import destination parent is not a real directory")

    try:
        source_root = source_path.resolve(strict=True)
        parent_root = destination_path.parent.resolve(strict=True)
        if not source_root.is_dir() or not parent_root.is_dir():
            raise OSError("Import source and destination parent must be directories")
        source_stat = source_root.stat()
        parent_stat = parent_root.stat()
    except (OSError, RuntimeError) as exc:
        raise OSError("Could not verify import source or destination parent") from exc

    source_identity = (source_stat.st_dev, source_stat.st_ino)
    parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
    destination_name = destination_path.name
    if not destination_name or destination_name in {".", ".."}:
        raise OSError("Import destination name is invalid")
    destination = parent_root / destination_name

    matcher = match_files or match_completed_album_files
    matched = matcher(source_root, candidate)
    if not matched:
        raise OSError("Expected tracks no longer match files in the completed folder")

    manifest_name = ".navidrome-import.json"
    if any(str(name).casefold() == manifest_name.casefold() for name in matched):
        raise OSError("A track name conflicts with the reserved import manifest")

    source_fd = None
    parent_fd = None
    staging_fd = None
    staging_name = ".navidrome-import-" + uuid.uuid4().hex
    staging_created = False
    staging_published = False
    moved: list[tuple[str, str]] = []
    manifest_written = False

    def assert_directory_path_identity(path, resolved_path, identity, label):
        try:
            if Path(path).resolve(strict=True) != resolved_path:
                raise OSError(f"{label} path changed during import")
            current = resolved_path.stat()
        except (OSError, RuntimeError) as exc:
            raise OSError(f"{label} path changed during import") from exc
        if (current.st_dev, current.st_ino) != identity:
            raise OSError(f"{label} directory identity changed during import")

    def assert_music_storage_identity():
        if expected_device is None:
            return
        if expected_music_root is None:
            raise OSError("Music-library root is required when checking storage identity")
        music_root = Path(expected_music_root)
        if music_root.stat().st_dev != expected_device:
            raise OSError(
                "Music-library filesystem changed during import; refusing further writes"
            )
        if parent_fd is None or os.fstat(parent_fd).st_dev != expected_device:
            raise OSError(
                "Music-library filesystem changed during import; refusing further writes"
            )

    try:
        # The matcher is an injected boundary. Revalidate both directory paths
        # afterward before opening and pinning them for any filesystem mutation.
        assert_directory_path_identity(
            source_path, source_root, source_identity, "Import source"
        )
        assert_directory_path_identity(
            destination_path.parent, parent_root, parent_identity, "Destination parent"
        )

        source_fd = _open_directory_path_no_follow(source_root)
        parent_fd = _open_directory_path_no_follow(parent_root)
        if (os.fstat(source_fd).st_dev, os.fstat(source_fd).st_ino) != source_identity:
            raise OSError("Import source directory changed while opening")
        if (os.fstat(parent_fd).st_dev, os.fstat(parent_fd).st_ino) != parent_identity:
            raise OSError("Import destination parent changed while opening")

        if _entry_stat(parent_fd, destination_name) is not None:
            raise FileExistsError(str(destination))

        # Snapshot every matched source entry through the pinned directory.
        source_files = {}
        for expected_name, actual_path_value in matched.items():
            expected_name = str(expected_name)
            actual_path = Path(actual_path_value)
            actual_name = actual_path.name
            if (
                not expected_name
                or Path(expected_name).name != expected_name
                or expected_name in {".", ".."}
                or not actual_name
                or Path(actual_name).name != actual_name
                or actual_name in {".", ".."}
                or actual_path.parent != source_root
            ):
                raise OSError("Matched import track is not a direct child of the source folder")

            file_fd = os.open(
                actual_name, os.O_RDONLY | _NOFOLLOW, dir_fd=source_fd
            )
            try:
                opened = os.fstat(file_fd)
                named = os.stat(
                    actual_name, dir_fd=source_fd, follow_symlinks=False
                )
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or not stat.S_ISREG(named.st_mode)
                    or (opened.st_dev, opened.st_ino)
                    != (named.st_dev, named.st_ino)
                ):
                    raise OSError(f"Expected track changed before staging: {expected_name}")
                source_files[expected_name] = {
                    "source_name": actual_name,
                    "device": opened.st_dev,
                    "inode": opened.st_ino,
                    "size": opened.st_size,
                }
            finally:
                os.close(file_fd)

        manifest_data = {
            "source": str(source_root),
            "destination": str(destination),
            "tracks": {
                name: info["size"] for name, info in source_files.items()
            },
        }

        os.mkdir(staging_name, dir_fd=parent_fd)
        staging_created = True
        staging_fd = os.open(staging_name, _DIRECTORY_FLAGS, dir_fd=parent_fd)
        if not stat.S_ISDIR(os.fstat(staging_fd).st_mode):
            raise OSError("Import staging path is not a real directory")

        manifest_fd = os.open(
            manifest_name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW,
            0o600,
            dir_fd=staging_fd,
        )
        with os.fdopen(manifest_fd, "w", encoding="utf-8") as manifest_file:
            json.dump(manifest_data, manifest_file, ensure_ascii=False)
            manifest_file.flush()
            os.fsync(manifest_file.fileno())
        manifest_written = True

        for expected_name, snapshot in source_files.items():
            assert_music_storage_identity()
            assert_directory_path_identity(
                source_path, source_root, source_identity, "Import source"
            )
            source_name = snapshot["source_name"]
            file_fd = os.open(
                source_name, os.O_RDONLY | _NOFOLLOW, dir_fd=source_fd
            )
            try:
                opened = os.fstat(file_fd)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or (opened.st_dev, opened.st_ino)
                    != (snapshot["device"], snapshot["inode"])
                    or opened.st_size != snapshot["size"]
                ):
                    raise OSError(f"Expected track changed before staging: {expected_name}")

                try:
                    os.rename(
                        source_name,
                        expected_name,
                        src_dir_fd=source_fd,
                        dst_dir_fd=staging_fd,
                    )
                    moved.append((expected_name, source_name))
                    staged_stat = os.stat(
                        expected_name, dir_fd=staging_fd, follow_symlinks=False
                    )
                    if (
                        not stat.S_ISREG(staged_stat.st_mode)
                        or (staged_stat.st_dev, staged_stat.st_ino)
                        != (snapshot["device"], snapshot["inode"])
                        or staged_stat.st_size != snapshot["size"]
                    ):
                        raise OSError(f"Staged track failed validation: {expected_name}")
                except OSError as exc:
                    if exc.errno != errno.EXDEV:
                        raise
                    _copy_fd_to_directory(
                        file_fd, staging_fd, expected_name, opened
                    )
                    moved.append((expected_name, source_name))
                    staged_stat = os.stat(
                        expected_name, dir_fd=staging_fd, follow_symlinks=False
                    )
                    if (
                        not stat.S_ISREG(staged_stat.st_mode)
                        or staged_stat.st_size != snapshot["size"]
                    ):
                        raise OSError(f"Staged track failed validation: {expected_name}")

                    # Move the source name to a private name, verify its inode,
                    # and only then unlink it. This prevents deleting a swapped
                    # replacement entry during cross-filesystem copy fallback.
                    quarantine_name = ".navidrome-import-source-" + uuid.uuid4().hex
                    os.rename(
                        source_name,
                        quarantine_name,
                        src_dir_fd=source_fd,
                        dst_dir_fd=source_fd,
                    )
                    quarantined = os.stat(
                        quarantine_name, dir_fd=source_fd, follow_symlinks=False
                    )
                    if (
                        not stat.S_ISREG(quarantined.st_mode)
                        or (quarantined.st_dev, quarantined.st_ino)
                        != (snapshot["device"], snapshot["inode"])
                    ):
                        if _entry_stat(source_fd, source_name) is None:
                            os.rename(
                                quarantine_name,
                                source_name,
                                src_dir_fd=source_fd,
                                dst_dir_fd=source_fd,
                            )
                        os.unlink(expected_name, dir_fd=staging_fd)
                        raise OSError(
                            f"Expected track changed during staging: {expected_name}"
                        )
                    os.unlink(quarantine_name, dir_fd=source_fd)

            finally:
                os.close(file_fd)

        assert_music_storage_identity()
        assert_directory_path_identity(
            source_path, source_root, source_identity, "Import source"
        )
        assert_directory_path_identity(
            destination_path.parent, parent_root, parent_identity, "Destination parent"
        )
        if _entry_stat(parent_fd, destination_name) is not None:
            raise FileExistsError(str(destination))

        # Publish the complete staging directory relative to the pinned parent.
        os.rename(
            staging_name,
            destination_name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        staging_published = True
        try:
            os.unlink(manifest_name, dir_fd=staging_fd)
            manifest_written = False
        except OSError:
            # A completed destination plus its manifest is recoverable on restart.
            pass

    except Exception:
        if staging_created and not staging_published and parent_fd is not None:
            rollback_complete = True
            if staging_fd is not None:
                for staged_name, source_name in reversed(moved):
                    staged_stat = _entry_stat(staging_fd, staged_name)
                    source_stat_now = _entry_stat(source_fd, source_name) if source_fd is not None else None
                    if staged_stat is None:
                        if source_stat_now is None:
                            rollback_complete = False
                        continue
                    if source_stat_now is not None:
                        rollback_complete = False
                        continue
                    try:
                        os.rename(
                            staged_name,
                            source_name,
                            src_dir_fd=staging_fd,
                            dst_dir_fd=source_fd,
                        )
                    except OSError as exc:
                        if exc.errno != errno.EXDEV:
                            rollback_complete = False
                            continue
                        try:
                            staged_file_fd = os.open(
                                staged_name, os.O_RDONLY | _NOFOLLOW, dir_fd=staging_fd
                            )
                            try:
                                staged_file_stat = os.fstat(staged_file_fd)
                                _copy_fd_to_directory(
                                    staged_file_fd,
                                    source_fd,
                                    source_name,
                                    staged_file_stat,
                                )
                                os.unlink(staged_name, dir_fd=staging_fd)
                            finally:
                                os.close(staged_file_fd)
                        except OSError:
                            rollback_complete = False

                if rollback_complete:
                    if _entry_stat(staging_fd, manifest_name) is not None:
                        try:
                            os.unlink(manifest_name, dir_fd=staging_fd)
                        except OSError:
                            rollback_complete = False

            if rollback_complete:
                try:
                    os.rmdir(staging_name, dir_fd=parent_fd)
                except OSError:
                    # Keep the manifest and staged data for manual/restart recovery.
                    pass
        raise
    finally:
        for fd in (staging_fd, source_fd, parent_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
