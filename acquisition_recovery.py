"""Conservative recovery of interrupted acquisition imports.

This module coordinates persisted state with filesystem evidence through injected
dependencies. It never guesses a destination or mount identity, and it restores
staged files only when the manifest, names, sizes, and source ownership match.
"""
from pathlib import Path


def reconcile_interrupted_import(
    artist, album, candidate, *,
    transition_lock, is_dismissed, music_key, list_acquisition_jobs,
    music_dir, safe_folder_name, match_completed_album_files,
    update_status, json_module, now, move_file,
):
    """Mark a previously completed filesystem move imported after a process crash.

    Reconciliation is deliberately limited to jobs still marked importing and
    to the exact destination recorded before the move began.
    """
    with transition_lock:
        if is_dismissed(artist, album):
            return False

        identity = (music_key(artist), music_key(album))
        job = next((
            item for item in list_acquisition_jobs()
            if (item.get("artist_key"), item.get("album_key")) == identity
        ), None)
        if not job or job.get("status") != "importing":
            return False

        details = job.get("details") or {}
        expected_destination = details.get("destination")
        if not expected_destination:
            return False

        try:
            music_root = Path(music_dir).expanduser().resolve(strict=True)
            recorded_device = details.get("music_root_device")
            # Older jobs lack this proof of mount identity. Do not mutate or
            # reconcile their files automatically: the mountpoint may now be
            # exposing an unrelated underlying local directory.
            if recorded_device is None or music_root.stat().st_dev != int(recorded_device):
                return False
            artist_dir = music_root / safe_folder_name(artist)
            album_dir = artist_dir / safe_folder_name(album)
            # macOS commonly exposes temporary paths through /var -> /private/var.
            # Normalize recorded paths before comparing them with the resolved library
            # root, otherwise valid recovery manifests are rejected on that platform.
            destination = Path(expected_destination).expanduser().resolve()
            if destination != album_dir.resolve():
                return False
            if artist_dir.is_symlink() or album_dir.is_symlink():
                return False
            if not artist_dir.is_dir():
                return False
            if album_dir.exists() and not album_dir.is_dir():
                return False
            if artist_dir.resolve(strict=True).parent != music_root:
                return False
            if album_dir.is_dir() and album_dir.resolve(strict=True).parent != artist_dir.resolve(strict=True):
                return False

            expected_names = {
                str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
                for item in candidate.get("files", [])
                if str(item.get("filename") or "").strip()
            }
            matched = (
                match_completed_album_files(album_dir, candidate)
                if album_dir.is_dir() and not album_dir.is_symlink()
                else None
            )
            if expected_names and matched and set(matched) == expected_names:
                # If the process stopped after publishing the directory but
                # before removing its manifest, remove only a matching manifest.
                manifest = album_dir / ".navidrome-import.json"
                if manifest.is_file() and not manifest.is_symlink():
                    try:
                        manifest_data = json_module.loads(manifest.read_text(encoding="utf-8"))
                        expected_sizes = {
                            str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1].casefold():
                                int(item.get("size") or 0)
                            for item in candidate.get("files", [])
                            if str(item.get("filename") or "").strip()
                        }
                        manifest_tracks = {
                            str(name).casefold(): int(size)
                            for name, size in manifest_data.get("tracks", {}).items()
                        }
                        source_value = details.get("source_folder")
                        if (
                            manifest_data.get("destination")
                            and Path(manifest_data["destination"]).expanduser().resolve() == album_dir.resolve()
                            and source_value
                            and manifest_data.get("source") == str(Path(source_value).expanduser().resolve())
                            and manifest_tracks == expected_sizes
                        ):
                            manifest.unlink()
                    except (OSError, RuntimeError, ValueError, TypeError):
                        pass
                update_status(artist, album, "imported", {
                    "source_folder": details.get("source_folder"),
                    "destination": str(album_dir),
                    "source_username": candidate.get("username"),
                    "imported_at": now(),
                    "recovered_after_restart": True,
                })
                return True

            # A crash during cross-filesystem moves can leave some tracks in a
            # hidden staging directory and others in the source folder. Restore
            # those staged tracks only when ownership and sizes are unambiguous.
            source_folder_value = details.get("source_folder")
            if not source_folder_value:
                return False
            source_folder = Path(source_folder_value).expanduser()
            if not source_folder.is_dir() or source_folder.is_symlink():
                return False
            expected_sizes = {}
            for item in candidate.get("files", []):
                name = str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1]
                if not name:
                    continue
                try:
                    size = int(item.get("size") or 0)
                except (TypeError, ValueError):
                    return False
                key = name.casefold()
                if key in expected_sizes and expected_sizes[key] != size:
                    return False
                expected_sizes[key] = size
            if not expected_sizes:
                return False

            staging_dirs = [
                path for path in artist_dir.glob(".navidrome-import-*")
                if path.is_dir() and not path.is_symlink()
            ]
            recoverable = []
            for staging in staging_dirs:
                try:
                    manifest = staging / ".navidrome-import.json"
                    if manifest.is_symlink() or not manifest.is_file():
                        continue
                    manifest_data = json_module.loads(manifest.read_text(encoding="utf-8"))
                    if (
                        manifest_data.get("source") != str(source_folder.resolve(strict=True))
                        or not manifest_data.get("destination")
                        or Path(manifest_data["destination"]).expanduser().resolve() != album_dir.resolve()
                        or {str(k).casefold(): int(v) for k, v in manifest_data.get("tracks", {}).items()} != expected_sizes
                    ):
                        continue
                    entries = [item for item in staging.iterdir() if item != manifest]
                    if not entries or any(
                        item.is_symlink() or not item.is_file() for item in entries
                    ):
                        continue
                    valid = True
                    for item in entries:
                        key = item.name.casefold()
                        if key not in expected_sizes or item.stat(follow_symlinks=False).st_size != expected_sizes[key]:
                            valid = False
                            break
                        if (source_folder / item.name).exists() or (source_folder / item.name).is_symlink():
                            valid = False
                            break
                    if valid:
                        recoverable.append((staging, entries, manifest))
                except (OSError, RuntimeError, ValueError, TypeError):
                    continue

            if len(recoverable) != 1:
                return False
            staging, entries, manifest = recoverable[0]
            for item in entries:
                move_file(str(item), str(source_folder / item.name))
            manifest.unlink()
            staging.rmdir()
            return False
        except (OSError, RuntimeError, TypeError, ValueError):
            return False

        update_status(artist, album, "imported", {
            "source_folder": details.get("source_folder"),
            "destination": str(album_dir),
            "source_username": candidate.get("username"),
            "imported_at": now(),
            "recovered_after_restart": True,
        })
        return True
