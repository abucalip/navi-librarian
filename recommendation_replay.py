"""Private, deterministic replay of the recommendation ranking stage.

Capture files contain personal listening and library data. They are deliberately
created outside the repository with owner-only permissions and must never be
committed to a public repository.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

SCHEMA_VERSION = 1
_REPOSITORY_ROOT = Path(__file__).resolve().parent


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def freeze_gathered_inputs(gathered: dict[str, Any]) -> dict[str, Any]:
    """Serialize the exact post-provider inputs consumed by ranking, preserving order."""
    return {
        "listens": gathered["listens"],
        "recent_artists": dict(gathered["recent_artists"]),
        "recent_artist_mbid_counts": dict(gathered["recent_artist_mbid_counts"]),
        "albums": [
            {"key": list(key), "value": value}
            for key, value in gathered["albums"].items()
        ],
        "failures": gathered["failures"],
        "library_albums": gathered["library_albums"],
        "library_by_title": gathered["library_by_title"],
        "genre_cache": gathered["genre_cache"],
        "regional_candidates_added": gathered["regional_candidates_added"],
        "regional_results_seen": gathered["regional_results_seen"],
        "cf_recording_mbids": gathered.get("cf_recording_mbids", []),
        "cf_recordings_returned": gathered.get("cf_recordings_returned", 0),
        "cf_recordings_resolved": gathered.get("cf_recordings_resolved", 0),
        "supplementary_cache_hits": gathered.get("supplementary_cache_hits", 0),
        "supplementary_cache_misses": gathered.get("supplementary_cache_misses", 0),
        "recent_family_counts": dict(gathered["recent_family_counts"]),
        "core_families": sorted(gathered["core_families"]),
        "exploration_families": sorted(gathered["exploration_families"]),
        "profile_families": sorted(gathered["profile_families"]),
    }


def thaw_gathered_inputs(payload: dict[str, Any]) -> dict[str, Any]:
    """Restore ranking inputs without importing or invoking provider clients."""
    required = {
        "listens", "recent_artists", "recent_artist_mbid_counts", "albums",
        "failures", "library_albums", "library_by_title", "genre_cache",
        "regional_candidates_added", "regional_results_seen",
        "recent_family_counts", "core_families", "exploration_families",
        "profile_families",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError("Replay input is missing required fields: " + ", ".join(missing))
    albums = {}
    for entry in payload["albums"]:
        key = entry.get("key")
        value = entry.get("value")
        if not isinstance(key, list) or len(key) != 2 or not isinstance(value, dict):
            raise ValueError("Replay album entry has an invalid shape.")
        tuple_key = (str(key[0]), str(key[1]))
        if tuple_key in albums:
            raise ValueError("Replay contains duplicate album keys.")
        albums[tuple_key] = value
    return {
        "listens": payload["listens"],
        "recent_artists": Counter(payload["recent_artists"]),
        "recent_artist_mbid_counts": Counter(payload["recent_artist_mbid_counts"]),
        "albums": albums,
        "failures": payload["failures"],
        "library_albums": payload["library_albums"],
        "library_by_title": payload["library_by_title"],
        "genre_cache": payload["genre_cache"],
        "regional_candidates_added": payload["regional_candidates_added"],
        "regional_results_seen": payload["regional_results_seen"],
        "cf_recording_mbids": payload.get("cf_recording_mbids", []),
        "cf_recordings_returned": payload.get("cf_recordings_returned", 0),
        "cf_recordings_resolved": payload.get("cf_recordings_resolved", 0),
        "supplementary_cache_hits": payload.get("supplementary_cache_hits", 0),
        "supplementary_cache_misses": payload.get("supplementary_cache_misses", 0),
        "recent_family_counts": Counter(payload["recent_family_counts"]),
        "core_families": set(payload["core_families"]),
        "exploration_families": set(payload["exploration_families"]),
        "profile_families": set(payload["profile_families"]),
    }


def _check_private_path(path: Path, *, must_exist: bool) -> Path:
    if not path.is_absolute():
        raise ValueError("Capture path must be absolute.")
    parent = path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("Capture parent must be an existing, non-symlink directory.")
    if parent.stat().st_mode & 0o077:
        raise PermissionError("Capture directory must have owner-only permissions (chmod 700).")
    resolved = path.resolve(strict=False)
    if resolved.is_relative_to(_REPOSITORY_ROOT):
        raise ValueError("Private capture files must be outside the repository.")
    if path.is_symlink():
        raise ValueError("Capture file may not be a symlink.")
    if must_exist:
        if not path.is_file():
            raise FileNotFoundError("Capture file does not exist.")
        if path.stat().st_mode & 0o077:
            raise PermissionError("Capture file must have owner-only permissions (chmod 600).")
    elif path.exists():
        raise FileExistsError("Refusing to overwrite an existing capture.")
    return path


def write_capture(
    path: str | Path,
    *,
    gathered: dict[str, Any],
    lastfm_calls: list[dict[str, Any]],
    output: str,
    count: int,
    git_sha: str | None = None,
) -> Path:
    """Write one immutable, checksummed, owner-only capture outside the repo."""
    target = _check_private_path(Path(path), must_exist=False)
    try:
        expected_output = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise ValueError("Only a successful JSON recommendation result can be captured.") from exc
    if not isinstance(expected_output, dict) or "recommendations" not in expected_output:
        raise ValueError("Output is not a successful recommendation result.")
    try:
        sha = git_sha or subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sha = "unknown"
    payload = {
        "count": int(count),
        "gathered_inputs": freeze_gathered_inputs(gathered),
        "lastfm_calls": lastfm_calls,
        "expected_output": expected_output,
    }
    envelope = {
        "schema_version": SCHEMA_VERSION,
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": sha,
        "payload_sha256": hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest(),
        "payload": payload,
    }
    encoded = json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            target.unlink()
        except OSError:
            pass
        raise
    return target


def load_capture(path: str | Path) -> dict[str, Any]:
    target = _check_private_path(Path(path), must_exist=True)
    try:
        envelope = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Capture is not readable valid JSON.") from exc
    if envelope.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported recommendation capture schema version.")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Capture payload is missing.")
    actual = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    if actual != envelope.get("payload_sha256"):
        raise ValueError("Capture checksum mismatch; refusing replay.")
    if not isinstance(payload.get("lastfm_calls"), list):
        raise ValueError("Capture Last.fm call tape is missing.")
    if not isinstance(payload.get("expected_output"), dict):
        raise ValueError("Capture expected output is missing.")
    return envelope


class LastFmReplay:
    """Strict ordered Last.fm response tape; never accesses a network client."""
    def __init__(self, calls: list[dict[str, Any]]):
        self._calls = calls
        self._index = 0

    def __call__(self, artist: str, album: str) -> Any:
        if self._index >= len(self._calls):
            raise RuntimeError("Offline replay requested an uncaptured Last.fm response.")
        entry = self._calls[self._index]
        self._index += 1
        if entry.get("artist") != artist or entry.get("album") != album:
            raise RuntimeError(
                "Offline replay Last.fm call order mismatch at index "
                + str(self._index - 1)
            )
        value = entry.get("result")
        return tuple(value) if isinstance(value, list) and len(value) == 2 else value

    def assert_consumed(self) -> None:
        if self._index != len(self._calls):
            raise RuntimeError(
                f"Offline replay left {len(self._calls) - self._index} captured Last.fm responses unused."
            )


def _comparable_output(value: dict[str, Any]) -> dict[str, Any]:
    # Diagnostics contain timestamps and previous-run overlap by design. They
    # are not ranking outputs and are not part of deterministic equivalence.
    return {key: item for key, item in value.items()
            if key not in {"pool_diagnostics", "lastfm_last_error"}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay a private recommendation capture offline.")
    parser.add_argument("capture", help="absolute path to a private capture JSON file")
    args = parser.parse_args(argv)
    try:
        envelope = load_capture(args.capture)
        payload = envelope["payload"]
        gathered = thaw_gathered_inputs(payload["gathered_inputs"])
        lastfm = LastFmReplay(payload["lastfm_calls"])
        # Import only after the capture is validated. The ranking entry point
        # accepts frozen gathered inputs and skips every candidate provider.
        import navidrome_server
        actual_text = navidrome_server.recommend_new_music(
            count=int(payload["count"]),
            _gathered_override=gathered,
            _lastfm_popularity_fn=lastfm,
            _lastfm_available_override=bool(payload["expected_output"].get("lastfm_api_configured")),
            _record_diagnostics=False,
        )
        actual = json.loads(actual_text)
        lastfm.assert_consumed()
        expected = payload["expected_output"]
        matches = _comparable_output(actual) == _comparable_output(expected)
        report = {
            "capture_git_sha": envelope.get("git_sha"),
            "capture_schema_version": envelope["schema_version"],
            "reproduced": matches,
            "expected_recommendations": len(expected.get("recommendations", [])),
            "actual_recommendations": len(actual.get("recommendations", [])),
            "network_providers_used": 0,
            "comparison": "all stable output fields except volatile pool diagnostics and Last.fm error state",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if matches else 1
    except Exception as exc:
        print(json.dumps({"reproduced": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
