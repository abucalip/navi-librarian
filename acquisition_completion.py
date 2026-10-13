"""Inspectable evidence for locating completed slskd album folders.

This module deliberately does not decide that a transfer is complete. It only
examines the local download tree after the watcher has established transfer
completion, and explains why a completed folder could not safely be selected.
The existing track matcher remains the authority for filename/size validation.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Any


def safe_folder_name(value: Any) -> str:
    """Return a safe final path component for the advertised remote folder."""
    value = str(value or "").replace("\\\\", "/").split("/")[-1]
    value = "".join(character for character in value if character != "\\0")
    value = value.strip().strip(".")
    return value or "Unknown"


def filename_key(value: Any) -> str:
    """Normalize filename identity across Unicode forms and case-sensitive filesystems."""
    import unicodedata

    return unicodedata.normalize("NFC", str(value or "")).casefold()


def match_completed_album_files(
    folder: str | Path,
    candidate: dict[str, Any],
) -> dict[str, Path] | None:
    """Match every unique expected basename to one safe local file by name and size.

    Numeric collision suffixes such as Track_1.flac are accepted only when
    exactly one candidate has the advertised size. Unknown/non-positive sizes
    and conflicting duplicate remote basenames fail closed.
    """
    import re
    import unicodedata

    folder = Path(folder)
    files = [path for path in folder.iterdir() if path.is_file() and not path.is_symlink()]
    used: set[Path] = set()
    matched: dict[str, Path] = {}
    expected_by_name: dict[str, tuple[str, int]] = {}

    for item in candidate.get("files", []):
        name = str(item.get("filename") or "").replace("\\\\", "/").rsplit("/", 1)[-1]
        if not name:
            continue
        key = filename_key(name)
        try:
            size = int(item.get("size"))
        except (TypeError, ValueError):
            return None
        # A missing/zero size could mistake a partial transfer for a completed track.
        if size <= 0:
            return None
        if key in expected_by_name and expected_by_name[key][1] != size:
            return None
        expected_by_name.setdefault(key, (name, size))

    for key, (expected_name, expected_size) in expected_by_name.items():
        exact = [
            path for path in files
            if filename_key(path.name) == key
            and path not in used
            and path.stat().st_size == expected_size
        ]
        selected = exact[0] if len(exact) == 1 else None

        if selected is None:
            normalized_expected = unicodedata.normalize("NFC", expected_name)
            stem, suffix = Path(normalized_expected).stem, Path(normalized_expected).suffix
            pattern = re.compile(
                r"^" + re.escape(stem) + r"_\d+" + re.escape(suffix) + r"$",
                re.IGNORECASE,
            )
            alternatives = [
                path for path in files
                if path not in used
                and pattern.match(unicodedata.normalize("NFC", path.name))
                and path.stat().st_size == expected_size
            ]
            if len(alternatives) == 1:
                selected = alternatives[0]

        if selected is None:
            return None

        matched[expected_name] = selected
        used.add(selected)

    return matched or None


def inspect_completed_album(
    download_root: str | Path,
    candidate: dict[str, Any],
    *,
    safe_folder_name: Callable[[Any], str],
    filename_key: Callable[[Any], str],
    match_files: Callable[[str | Path, dict[str, Any]], dict[str, Path] | None],
) -> dict[str, Any]:
    """Return the uniquely verified folder, or bounded actionable diagnostics.

    The tree is walked once. A folder is eligible only when the existing strict
    matcher confirms all expected files and its basename matches the advertised
    slskd folder name. Diagnostics never relax those safety requirements.
    """
    root = Path(download_root).expanduser()
    expected_folder = safe_folder_name(candidate.get("folder"))
    expected_key = filename_key(expected_folder)
    expected_by_name: dict[str, tuple[str, int]] = {}

    for item in candidate.get("files") or []:
        raw_name = str(item.get("filename") or "").replace("\\", "/").rsplit("/", 1)[-1]
        if not raw_name:
            continue
        try:
            size = int(item.get("size"))
        except (TypeError, ValueError):
            size = 0
        expected_by_name.setdefault(filename_key(raw_name), (raw_name, size))

    base_diagnostics = {
        "expected_folder": expected_folder,
        "expected_files": len(expected_by_name),
        "diagnostic_candidates": [],
    }
    if not root.is_dir():
        return {
            "path": None,
            "diagnostics": {
                **base_diagnostics,
                "folder_diagnostic": "downloads_root_unavailable",
                "downloads_path_available": False,
            },
        }

    matching_named: list[Path] = []
    track_matches_other_names = False
    diagnostics: list[dict[str, Any]] = []
    named_folder_seen = False

    for current, directories, _filenames in os.walk(root, followlinks=False):
        directories[:] = [
            name for name in directories
            if not name.startswith(".") and not (Path(current) / name).is_symlink()
        ]
        folder = Path(current)
        if folder.resolve() == root.resolve():
            continue

        folder_name_matches = filename_key(folder.name) == expected_key
        named_folder_seen = named_folder_seen or folder_name_matches
        try:
            matched = match_files(folder, candidate)
        except (OSError, ValueError, RuntimeError):
            matched = None

        if matched:
            if folder_name_matches:
                # Two matches are enough to establish ambiguity; avoid retaining
                # every duplicate path in a large download tree.
                if len(matching_named) < 2:
                    matching_named.append(folder)
            else:
                track_matches_other_names = True

        if (folder_name_matches or matched) and len(diagnostics) < 25:
            try:
                actual_files = [
                    path for path in folder.iterdir()
                    if path.is_file() and not path.is_symlink()
                ]
            except OSError:
                diagnostics.append({
                    "folder_name": folder.name,
                    "folder_name_matches": folder_name_matches,
                    "track_files_match": bool(matched),
                    "matched_expected_tracks": len(matched or {}),
                    "expected_tracks": len(expected_by_name),
                    "reason": "folder_unreadable",
                    "missing_expected_files": [],
                    "size_mismatches": [],
                })
                continue
            actual_by_key = {filename_key(path.name): path for path in actual_files}
            matched_by_key = {
                filename_key(name): path for name, path in (matched or {}).items()
            }
            missing = []
            size_mismatches = []
            for key, (expected_name, expected_size) in expected_by_name.items():
                # Prefer the authoritative match result so collision-suffixed
                # filenames are not incorrectly reported as missing.
                actual = matched_by_key.get(key) or actual_by_key.get(key)
                if actual is None:
                    missing.append(expected_name)
                elif expected_size > 0 and actual.stat().st_size != expected_size:
                    size_mismatches.append(expected_name)

            reason = (
                "track_files_match"
                if matched
                else "expected_folder_tracks_mismatch"
                if folder_name_matches
                else "tracks_match_but_folder_name_differs"
            )
            diagnostics.append({
                "folder_name": folder.name,
                "folder_name_matches": folder_name_matches,
                "track_files_match": bool(matched),
                "matched_expected_tracks": len(matched or {}),
                "expected_tracks": len(expected_by_name),
                "reason": reason,
                "missing_expected_files": sorted(missing)[:10],
                "size_mismatches": sorted(size_mismatches)[:10],
            })

    diagnostics.sort(
        key=lambda item: (
            not item["folder_name_matches"],
            not item["track_files_match"],
            item["folder_name"].casefold(),
        )
    )
    summary = {
        **base_diagnostics,
        "downloads_path_available": True,
        "diagnostic_candidates": diagnostics[:5],
    }

    if len(matching_named) == 1:
        return {"path": matching_named[0], "diagnostics": {**summary, "folder_diagnostic": "matched"}}
    if len(matching_named) > 1:
        return {"path": None, "diagnostics": {**summary, "folder_diagnostic": "ambiguous_named_folder_matches"}}
    if track_matches_other_names:
        return {"path": None, "diagnostics": {**summary, "folder_diagnostic": "tracks_match_but_folder_name_differs"}}
    if named_folder_seen:
        return {"path": None, "diagnostics": {**summary, "folder_diagnostic": "expected_folder_tracks_mismatch"}}
    return {"path": None, "diagnostics": {**summary, "folder_diagnostic": "expected_folder_not_found"}}
