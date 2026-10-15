"""Fail-safe cleanup of a single verified slskd acquisition source folder.

All network and application-specific behavior is injected by the caller so this
module can be tested directly without importing the MCP/FastAPI application.
The implementation intentionally preserves the legacy cleanup preflight and
refusal behavior; it never recursively deletes a directory.
"""
from pathlib import Path


def clean_acquisition_source(
    download_root, candidate, base_url, headers, *,
    safe_folder_name, download_transfer_files, http_client,
):
    """
    Cancel only transfers belonging to the exact remote album directory.

    Preflight every local file before changing anything. Refuse cleanup if
    source identity or local file ownership is ambiguous.
    """
    import os
    import re
    import stat
    from urllib.parse import quote

    def normalized_path(value):
        """Normalize separators without treating different paths as equal."""
        value = str(value or "").replace("\\", "/")
        parts = [part for part in value.split("/") if part not in ("", ".")]

        if any(part == ".." for part in parts):
            return None

        return "/".join(parts).casefold()

    def basename(value):
        return str(value or "").replace("\\", "/").rsplit("/", 1)[-1]

    username = str(candidate.get("username") or "")
    files = candidate.get("files") or []

    if not username or not files:
        return False

    # Build an unambiguous expected-track inventory.
    expected_by_name = {}
    remote_directories = set()

    for item in files:
        filename = str(item.get("filename") or "")
        name = basename(filename)

        try:
            size = int(item.get("size"))
        except (TypeError, ValueError):
            return False

        # A missing or invalid advertised size makes safe cleanup impossible.
        if not name or size <= 0:
            return False

        remote_path = normalized_path(filename)
        if remote_path is None or "/" not in remote_path:
            return False

        remote_directory = remote_path.rsplit("/", 1)[0]
        remote_directories.add(remote_directory)

        key = name.casefold()

        # Duplicate basenames make local file ownership ambiguous.
        if key in expected_by_name:
            return False

        expected_by_name[key] = {
            "name": name,
            "size": size,
        }

    # Every advertised track must belong to one identifiable remote directory.
    if len(remote_directories) != 1:
        return False

    expected_remote_directory = next(iter(remote_directories))

    # Reject a symlink at the configured path before resolving it.
    try:
        original_root = Path(download_root).expanduser()
        if original_root.is_symlink():
            return False
        root = original_root.resolve(strict=True)
    except (OSError, RuntimeError):
        return False

    if not root.is_dir():
        return False

    wanted = safe_folder_name(candidate.get("folder"))
    if not wanted:
        return False

    direct = root / wanted

    # Do not follow a symlink, even if it points inside the download root.
    if direct.is_symlink():
        return False

    if direct.is_dir():
        targets = [direct]
    elif direct.exists():
        # A file or other object with the expected folder name is ambiguous.
        return False
    else:
        try:
            targets = [
                path
                for path in root.rglob(wanted)
                if path.name == wanted
                and path.is_dir()
                and not path.is_symlink()
            ]
        except OSError:
            return False

    # Never guess which of multiple same-named folders belongs to this job.
    if len(targets) > 1:
        return False

    target = targets[0] if targets else None

    planned_deletions = []
    target_identity = None

    # Preflight the entire local folder. Nothing has been cancelled or
    # deleted yet. Any unexpected entry aborts cleanup.
    if target is not None:
        try:
            resolved_target = target.resolve(strict=True)

            if (
                resolved_target == root
                or root not in resolved_target.parents
                or target.is_symlink()
            ):
                return False

            target_stat = target.stat(follow_symlinks=False)
            if not stat.S_ISDIR(target_stat.st_mode):
                return False
            target_identity = (target_stat.st_dev, target_stat.st_ino)

            for actual in target.iterdir():
                # Never follow symlinks, recurse into directories, or remove
                # special files.
                if actual.is_symlink() or not actual.is_file():
                    return False

                actual_name = actual.name
                key = actual_name.casefold()

                expected = expected_by_name.get(key)

                try:
                    actual_stat = actual.stat(follow_symlinks=False)
                except OSError:
                    return False

                if not stat.S_ISREG(actual_stat.st_mode):
                    return False
                actual_size = actual_stat.st_size

                if expected is not None:
                    # Exact-name tracks may be incomplete downloads, but
                    # must not exceed their advertised size.
                    if actual_size > expected["size"]:
                        return False

                    planned_deletions.append((actual_name, actual_stat.st_dev, actual_stat.st_ino))
                    continue

                # Collision-suffixed files are identifiable only when
                # exactly one expected track matches and the size is exact.
                collision_matches = []

                for expected_item in expected_by_name.values():
                    expected_name = expected_item["name"]
                    expected_size = expected_item["size"]

                    stem = Path(expected_name).stem
                    suffix = Path(expected_name).suffix

                    pattern = re.compile(
                        r"^"
                        + re.escape(stem)
                        + r"_\d+"
                        + re.escape(suffix)
                        + r"$",
                        re.IGNORECASE,
                    )

                    if (
                        pattern.fullmatch(actual_name)
                        and actual_size == expected_size
                    ):
                        collision_matches.append(expected_item)

                if len(collision_matches) != 1:
                    # An unrelated or ambiguous file means we cannot
                    # safely claim that cleanup is complete.
                    return False

                planned_deletions.append((actual_name, actual_stat.st_dev, actual_stat.st_ino))

        except (OSError, RuntimeError):
            return False

    # Inspect the peer's current transfers. Do not cancel by basename alone.
    try:
        tracked = download_transfer_files(
            base_url, headers, username
        )
    except Exception:
        return False

    active_states = {
        "queued",
        "initializing",
        "requested",
        "inprogress",
        "transferring",
        "downloading",
    }

    transfers_to_cancel = []

    for item in tracked:
        name = basename(item.get("filename"))
        expected = expected_by_name.get(name.casefold())

        if expected is None:
            continue

        state = (
            str(item.get("state") or "")
            .replace("_", "")
            .casefold()
        )

        if state not in active_states:
            continue

        # A tracked file's directory must be explicit. If it is missing,
        # derive it only from a full remote filename.
        tracked_directory = item.get("_transfer_directory")

        if tracked_directory is None:
            tracked_filename = str(item.get("filename") or "")
            normalized_filename = normalized_path(tracked_filename)

            if normalized_filename is None or "/" not in normalized_filename:
                return False

            tracked_directory = normalized_filename.rsplit("/", 1)[0]

        normalized_tracked_directory = normalized_path(tracked_directory)

        if normalized_tracked_directory is None:
            return False

        # A known, different directory belongs to a different remote file:
        # leave it alone.
        if normalized_tracked_directory != expected_remote_directory:
            continue

        # For the matching remote directory, require an identifiable
        # transfer ID and consistent advertised size.
        try:
            tracked_size = int(item.get("size"))
        except (TypeError, ValueError):
            return False

        if tracked_size != expected["size"]:
            return False

        file_id = str(item.get("id") or "")
        if not file_id:
            return False

        transfers_to_cancel.append((file_id, name.casefold()))

    # All checks above are read-only. Only now begin cancelling transfers.
    for file_id, _name in transfers_to_cancel:
        try:
            response = http_client.delete(
                f"{base_url}/api/v0/transfers/downloads/"
                f"{quote(username, safe='')}/"
                f"{quote(file_id, safe='')}",
                headers=headers,
                timeout=8,
            )

            if response.status_code not in (200, 202, 204, 404):
                return False

        except http_client.HTTPError:
            return False

    # Verify that no active transfer remains for this exact source directory.
    try:
        remaining = download_transfer_files(
            base_url, headers, username
        )
    except Exception:
        return False

    for item in remaining:
        name = basename(item.get("filename"))
        expected = expected_by_name.get(name.casefold())

        if expected is None:
            continue

        state = (
            str(item.get("state") or "")
            .replace("_", "")
            .casefold()
        )

        if state not in active_states:
            continue

        directory = item.get("_transfer_directory")

        if directory is None:
            normalized_filename = normalized_path(item.get("filename"))

            if normalized_filename is None or "/" not in normalized_filename:
                return False

            directory = normalized_filename.rsplit("/", 1)[0]

        normalized_directory = normalized_path(directory)

        if normalized_directory is None:
            return False

        if normalized_directory == expected_remote_directory:
            # Cancellation is not confirmed; do not delete local files.
            return False

    # Transfers are now confirmed stopped. Re-open the verified directory
    # without following any path-component symlinks, then delete relative to
    # that pinned directory descriptor. This prevents a folder swapped for a
    # symlink during the transfer callbacks from redirecting unlink() outside
    # the intended album directory.
    open_fds = []
    try:
        target_fd = None
        parent_fd = None
        target_name = None

        if target is not None:
            parts = target.relative_to(root).parts
            if not parts or target_identity is None:
                return False

            directory_flags = (
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0)
            )
            current_fd = os.open(root, directory_flags)
            open_fds.append(current_fd)

            for component in parts[:-1]:
                next_fd = os.open(component, directory_flags, dir_fd=current_fd)
                open_fds.append(next_fd)
                current_fd = next_fd

            parent_fd = current_fd
            target_name = parts[-1]
            target_fd = os.open(target_name, directory_flags, dir_fd=parent_fd)
            open_fds.append(target_fd)

            opened_stat = os.fstat(target_fd)
            current_stat = os.stat(
                target_name, dir_fd=parent_fd, follow_symlinks=False
            )
            if (
                not stat.S_ISDIR(opened_stat.st_mode)
                or (opened_stat.st_dev, opened_stat.st_ino) != target_identity
                or (current_stat.st_dev, current_stat.st_ino) != target_identity
                or not stat.S_ISDIR(current_stat.st_mode)
            ):
                return False

            # Validate every planned file identity before the first unlink.
            for name, device, inode in planned_deletions:
                current_file = os.stat(name, dir_fd=target_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(current_file.st_mode)
                    or (current_file.st_dev, current_file.st_ino) != (device, inode)
                ):
                    return False

            for name, device, inode in planned_deletions:
                current_file = os.stat(name, dir_fd=target_fd, follow_symlinks=False)
                if (
                    not stat.S_ISREG(current_file.st_mode)
                    or (current_file.st_dev, current_file.st_ino) != (device, inode)
                ):
                    return False
                os.unlink(name, dir_fd=target_fd)

            # Remove only the same now-empty directory entry, relative to its
            # pinned parent. Never recursively delete a directory.
            current_stat = os.stat(
                target_name, dir_fd=parent_fd, follow_symlinks=False
            )
            if (
                (current_stat.st_dev, current_stat.st_ino) != target_identity
                or not stat.S_ISDIR(current_stat.st_mode)
            ):
                return False
            os.rmdir(target_name, dir_fd=parent_fd)
        elif planned_deletions:
            return False

    except (OSError, RuntimeError, ValueError):
        return False
    finally:
        for fd in reversed(open_fds):
            try:
                os.close(fd)
            except OSError:
                pass

    return True
