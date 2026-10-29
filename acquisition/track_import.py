"""Safety-critical import of one downloaded song into an album folder.

The album import publishes a whole new folder; a song joins a folder that may already hold the
album. This module therefore never replaces anything: the destination file is created
exclusively, the library path is checked at every level, the source and the album folder are
pinned by file descriptor (a path swapped for a symlink cannot redirect the move), and a
failure removes only what this call created.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

from acquisition.import_files import _NOFOLLOW, _copy_fd_to_directory, _open_directory_path_no_follow


def destination_filename(remote_filename: str) -> str:
    """The song's file name in the library: the remote basename, made a single safe component."""
    name = str(remote_filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(character for character in name if character != "\0" and ord(character) >= 32).strip()
    if not name or name in {".", ".."} or name.startswith("."):
        raise OSError("Import destination file name is invalid")
    return name


def _real_directory_under(path: Path, parent: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise OSError(f"{path.name} is not a real directory")
    if path.resolve(strict=True).parent != parent:
        raise OSError(f"{path.name} resolves outside its parent")


def import_track_file(
    source_file: str | Path,
    album_dir: str | Path,
    music_root: str | Path,
    remote_filename: str,
    expected_size: int,
) -> Path:
    """Move one verified file into ``<music root>/<artist>/<album>/`` without overwriting.

    ``album_dir`` must be exactly two levels under the music root. Missing artist and album
    folders are created; one this call created is removed again if the import fails and it is
    still empty. Returns the destination path. Raises ``FileExistsError`` when the file is
    already there and ``OSError`` for any unsafe or inconsistent state.
    """
    if expected_size <= 0:
        raise OSError("Expected file size is unknown")
    root = Path(music_root).expanduser().resolve(strict=True)
    album_dir = Path(album_dir)
    artist_dir = album_dir.parent
    if artist_dir.parent != root or not album_dir.name or album_dir.name in {".", ".."}:
        raise OSError("Song destination is not <music root>/<artist>/<album>")
    if not root.is_dir():
        raise OSError("Music root is not a directory")
    root_device = root.stat().st_dev
    name = destination_filename(remote_filename)

    source = Path(source_file)
    source_dir = source.parent
    if source.is_symlink() or source_dir.is_symlink():
        raise OSError("Import source must not be a symlink")

    created: list[Path] = []
    source_dir_fd = destination_dir_fd = source_fd = -1
    try:
        for directory, parent in ((artist_dir, root), (album_dir, None)):
            if not directory.exists() and not directory.is_symlink():
                directory.mkdir()
                created.append(directory)
            _real_directory_under(directory, parent if parent is not None else artist_dir.resolve(strict=True))
            if directory.stat().st_dev != root_device:
                raise OSError("Music-library filesystem changed before import")

        source_dir_fd = _open_directory_path_no_follow(source_dir.resolve(strict=True))
        before = os.stat(source.name, dir_fd=source_dir_fd, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_size != expected_size:
            raise OSError("Downloaded file is not the expected regular file")
        source_fd = os.open(source.name, os.O_RDONLY | _NOFOLLOW, dir_fd=source_dir_fd)
        opened = os.fstat(source_fd)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino) or opened.st_size != expected_size:
            raise OSError("Downloaded file changed during import")

        destination_dir_fd = _open_directory_path_no_follow(album_dir.resolve(strict=True))
        try:
            os.stat(name, dir_fd=destination_dir_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError(str(album_dir / name))
        # O_EXCL inside the copy is the authoritative no-overwrite guard.
        _copy_fd_to_directory(source_fd, destination_dir_fd, name, opened)
        os.unlink(source.name, dir_fd=source_dir_fd)
    except BaseException:
        for directory in reversed(created):
            try:
                directory.rmdir()
            except OSError:
                pass
        raise
    finally:
        for descriptor in (source_fd, source_dir_fd, destination_dir_fd):
            if descriptor >= 0:
                os.close(descriptor)
    try:
        source_dir.rmdir()
    except OSError:
        pass  # not empty: other downloads or files live there
    return album_dir / name
