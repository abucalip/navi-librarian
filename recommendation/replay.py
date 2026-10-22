"""Private, deterministic replay of candidate gathering and recommendation ranking.

Capture files contain personal listening and library data. They are deliberately
created outside the repository with owner-only permissions and must never be
committed to a public repository.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import math
import threading
from typing import Any, Callable

SCHEMA_VERSION = 2
_REPOSITORY_ROOT = Path(__file__).resolve().parent.parent


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


# These fields are derived while ranking mutates the gathered candidate objects.
# Captures must preserve the provider/gathering state, not a post-ranking snapshot;
# otherwise counterfactual profile runs can inherit bonuses from the original profile.
_RANKING_DERIVED_CANDIDATE_FIELDS = frozenset({
    "discovery_score",
    "discovery_category",
    "diversity_style",
    "recent_profile_family",
    "recent_profile_families",
    "recent_profile_bonus",
    "lastfm_listeners",
    "lastfm_playcount",
    "lastfm_tags",
    "lastfm_popularity_bonus",
    "listening_families",
})


def _raw_candidate_input(candidate: dict[str, Any]) -> dict[str, Any]:
    """Copy a gathered candidate without mutable ranking-derived fields."""
    return {
        key: value for key, value in candidate.items()
        if key not in _RANKING_DERIVED_CANDIDATE_FIELDS
    }


def freeze_gathered_inputs(gathered: dict[str, Any]) -> dict[str, Any]:
    """Serialize the exact post-provider inputs consumed by ranking, preserving order."""
    return {
        "listens": gathered["listens"],
        "recent_artists": dict(gathered["recent_artists"]),
        "recent_artist_mbid_counts": dict(gathered["recent_artist_mbid_counts"]),
        "recent_artist_play_counts": dict(gathered.get("recent_artist_play_counts", gathered["recent_artists"])),
        "albums": [
            {"key": list(key), "value": _raw_candidate_input(value)}
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
        "recent_family_play_counts": dict(gathered.get("recent_family_play_counts", gathered["recent_family_counts"])),
        "core_families": sorted(gathered["core_families"]),
        "exploration_families": sorted(gathered["exploration_families"]),
        "profile_families": sorted(gathered["profile_families"]),
        "profile_mode": gathered.get("profile_mode", "fixed"),
    }


def thaw_gathered_inputs(payload: dict[str, Any]) -> dict[str, Any]:
    """Restore ranking inputs without importing or invoking provider clients."""
    required = {
        "listens", "recent_artists", "recent_artist_mbid_counts", "recent_artist_play_counts", "albums",
        "failures", "library_albums", "library_by_title", "genre_cache",
        "regional_candidates_added", "regional_results_seen",
        "recent_family_counts", "recent_family_play_counts", "core_families", "exploration_families",
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
        albums[tuple_key] = _raw_candidate_input(value)
    return {
        "listens": payload["listens"],
        "recent_artists": Counter(payload["recent_artists"]),
        "recent_artist_mbid_counts": Counter(payload["recent_artist_mbid_counts"]),
        "recent_artist_play_counts": Counter(payload["recent_artist_play_counts"]),
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
        "recent_family_play_counts": Counter(payload["recent_family_play_counts"]),
        "core_families": set(payload["core_families"]),
        "exploration_families": set(payload["exploration_families"]),
        "profile_families": set(payload["profile_families"]),
        "profile_mode": payload.get("profile_mode", "fixed"),
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
    provider_events: list[dict[str, Any]],
    output: str,
    count: int,
    git_sha: str | None = None,
    ranking_context: dict[str, Any] | None = None,
) -> Path:
    """Write one immutable, checksummed, owner-only capture outside the repo."""
    target = _check_private_path(Path(path), must_exist=False)
    try:
        expected_output = json.loads(output)
    except (ValueError, TypeError) as exc:
        raise ValueError("Only a successful JSON recommendation result can be captured.") from exc
    if not isinstance(expected_output, dict) or "recommendations" not in expected_output:
        raise ValueError("Output is not a successful recommendation result.")
    sha = (
        git_sha
        or os.environ.get("LIBRARIAN_RECOMMENDATION_CAPTURE_GIT_SHA")
        or os.environ.get("GITHUB_SHA")
    )
    if not sha:
        try:
            sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=_REPOSITORY_ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            sha = "unknown"
    frozen_ranking_context = _validate_ranking_context(ranking_context)
    payload = {
        "count": int(count),
        "gathered_inputs": freeze_gathered_inputs(gathered),
        "ranking_context": frozen_ranking_context,
        "lastfm_calls": lastfm_calls,
        "provider_events": provider_events,
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


def _validate_ranking_context(value: Any) -> dict[str, Any]:
    """Validate every mutable ranking input that must be frozen for replay."""
    if not isinstance(value, dict):
        raise ValueError("Capture is missing frozen ranking context; recapture with the current version.")
    required = {"ranking_now", "history", "diversity_setting"}
    missing = sorted(required - value.keys())
    if missing:
        raise ValueError("Ranking context is missing required fields: " + ", ".join(missing))
    timestamp = value["ranking_now"]
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) or not math.isfinite(float(timestamp)):
        raise ValueError("Ranking context ranking_now must be a finite timestamp.")
    history = value["history"]
    if not isinstance(history, list) or any(not isinstance(row, dict) for row in history):
        raise ValueError("Ranking context history must be a list of objects.")
    for row in history:
        if not {"identity_hash", "generated_at", "rank"} <= row.keys():
            raise ValueError("Ranking context history row is missing required fields.")
    diversity = value["diversity_setting"]
    if type(diversity) is not int or not 0 <= diversity <= 100:
        raise ValueError("Ranking context diversity_setting must be an integer from 0 to 100.")
    frozen = {"ranking_now": float(timestamp), "history": history, "diversity_setting": diversity}
    if "feedback" in value:
        feedback = value["feedback"]
        if not isinstance(feedback, list) or any(not isinstance(row, dict) for row in feedback):
            raise ValueError("Ranking context feedback must be a list of objects.")
        frozen["feedback"] = feedback
    return frozen


def load_capture(path: str | Path) -> dict[str, Any]:
    target = _check_private_path(Path(path), must_exist=True)
    try:
        envelope = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Capture is not readable valid JSON.") from exc
    version = envelope.get("schema_version")
    if version == 1:
        raise ValueError("Legacy schema v1 capture lacks frozen ranking context; recapture with the current version.")
    if version != SCHEMA_VERSION:
        raise ValueError("Unsupported recommendation capture schema version.")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Capture payload is missing.")
    actual = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    if actual != envelope.get("payload_sha256"):
        raise ValueError("Capture checksum mismatch; refusing replay.")
    if not isinstance(payload.get("lastfm_calls"), list):
        raise ValueError("Capture Last.fm call tape is missing.")
    if not isinstance(payload.get("provider_events"), list):
        raise ValueError("Capture provider response tape is missing.")
    if not isinstance(payload.get("expected_output"), dict):
        raise ValueError("Capture expected output is missing.")
    _validate_ranking_context(payload.get("ranking_context"))
    thaw_gathered_inputs(payload.get("gathered_inputs", {}))
    return envelope


def prepare_provider_tape(tape: Any, capture_path: str | None) -> Any:
    """Return a supplied tape or create a recorder when capture is enabled."""
    return tape if tape is not None or not capture_path else ProviderTape("record")


def prepare_lastfm_callback(
    capture_path: str | None,
    gathered_override: Any,
    supplied_tape: Any,
    requested_callback: Callable[..., Any] | None,
    live_callback: Callable[..., Any],
) -> tuple[Callable[..., Any], list[dict[str, Any]]]:
    """Select the Last.fm callback and record exactly the values ranking consumes."""
    calls: list[dict[str, Any]] = []
    callback = requested_callback or live_callback
    if capture_path and gathered_override is None and supplied_tape is None:
        def capture_result(artist: str, album: str) -> Any:
            value = live_callback(artist, album)
            calls.append({"artist": artist, "album": album, "result": value})
            return value
        callback = capture_result
    return callback, calls


_CAPTURE_CLAIM_LOCK = threading.Lock()
_CLAIMED_CAPTURE_PATHS: set[str] = set()


def write_capture_safely(
    path: str,
    gathered: dict[str, Any],
    lastfm_calls: list[dict[str, Any]],
    provider_tape: Any,
    output: str,
    count: int,
    *,
    ranking_context: dict[str, Any],
) -> None:
    """Capture failure must not break recommendation serving; emit a safe warning.

    The environment variable is process-wide, so overlapping recommendation runs
    can all carry the same capture path. The first run to finish claims the one-shot
    capture; later runs in this process skip the write rather than hitting the
    refuse-to-overwrite check and logging a false failure.
    """
    import logging
    try:
        with _CAPTURE_CLAIM_LOCK:
            if path in _CLAIMED_CAPTURE_PATHS:
                return
            _CLAIMED_CAPTURE_PATHS.add(path)
        write_capture(
            path,
            gathered=gathered,
            lastfm_calls=lastfm_calls,
            provider_events=provider_tape.events if provider_tape is not None else [],
            output=output,
            count=count,
            ranking_context=ranking_context,
        )
    except Exception as exc:
        logging.getLogger("navidrome_server").warning(
            "Recommendation replay capture failed (%s).", type(exc).__name__
        )
    finally:
        if os.environ.get("LIBRARIAN_RECOMMENDATION_CAPTURE_PATH") == path:
            os.environ.pop("LIBRARIAN_RECOMMENDATION_CAPTURE_PATH", None)


class ProviderTape:
    """Record/replay every external/cache boundary used by candidate gathering.

    Replay compares call identity and serves captured results only. It never
    calls the wrapped provider functions or opens a real HTTP client.
    """
    _GENERIC = (
        "listenbrainz_recent", "listenbrainz_username", "metadata_cache_get",
        "metadata_cache_set", "api_call",
    )

    def __init__(self, mode: str, events: list[dict[str, Any]] | None = None):
        if mode not in {"record", "replay"}:
            raise ValueError("Provider tape mode must be 'record' or 'replay'.")
        self.mode = mode
        self.events = list(events or [])
        self._index = 0

    def _event(self, operation: str, args: Any, kwargs: Any) -> dict[str, Any] | None:
        normalized_args = json.loads(_canonical_json(args))
        normalized_kwargs = json.loads(_canonical_json(kwargs))
        if self.mode == "record":
            event = {"operation": operation, "args": normalized_args, "kwargs": normalized_kwargs}
            self.events.append(event)
            return event
        if self._index >= len(self.events):
            raise RuntimeError("Offline replay requested an uncaptured provider call: " + operation)
        event = self.events[self._index]
        self._index += 1
        if (
            event.get("operation") != operation
            or event.get("args") != normalized_args
            or event.get("kwargs") != normalized_kwargs
        ):
            raise RuntimeError("Offline replay provider call mismatch at event " + str(self._index - 1))
        return event

    def call(self, operation: str, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        event = self._event(operation, args, kwargs)
        if self.mode == "replay":
            if event.get("error"):
                raise RuntimeError(event["error"].get("message", "Recorded provider error"))
            return event.get("result")
        try:
            result = function(*args, **kwargs)
        except Exception as exc:
            event["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise
        event["result"] = result
        return result

    def response(self, operation: str, function: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        event = self._event(operation, args, kwargs)
        if self.mode == "replay":
            if event.get("error"):
                raise RuntimeError(event["error"].get("message", "Recorded HTTP error"))
            import httpx
            # HTTPX embeds method and fully resolved URL in HTTPStatusError text.
            # Preserve both, including query parameters passed separately via kwargs.
            request_url = event.get("request_url")
            if not request_url:
                request_url = str(args[0]) if args else "https://invalid.example/"
            request_method = event.get("request_method", "GET")
            request = httpx.Request(request_method, request_url)
            return httpx.Response(
                int(event["status_code"]),
                json=event.get("json"),
                request=request,
            )
        try:
            response = function(*args, **kwargs)
            try:
                body = response.json()
            except Exception as exc:
                event["error"] = {"type": type(exc).__name__, "message": str(exc)}
                return response
            event["status_code"] = int(response.status_code)
            event["json"] = body
            request = getattr(response, "request", None)
            if request is not None:
                event["request_method"] = request.method
                event["request_url"] = str(request.url)
            return response
        except Exception as exc:
            event["error"] = {"type": type(exc).__name__, "message": str(exc)}
            raise

    def wrap(self, providers: Any) -> Any:
        """Wrap the injected RecommendationProviders value for capture/replay."""
        wrapped = {}
        for name in self._GENERIC:
            original = getattr(providers, name)
            wrapped[name] = lambda *a, _name=name, _fn=original, **kw: self.call(_name, _fn, *a, **kw)

        original_http_get = providers.http_get
        wrapped["http_get"] = lambda *a, **kw: self.response("http_get", original_http_get, *a, **kw)

        original_factory = providers.http_client
        tape = self

        class ClientProxy:
            def __init__(self, client):
                self._client = client
            def __enter__(self):
                self._client.__enter__()
                return self
            def __exit__(self, *args):
                return self._client.__exit__(*args)
            def get(self, *args, **kwargs):
                return tape.response("http_client.get", self._client.get, *args, **kwargs)

        class ReplayClient:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def get(self, *args, **kwargs):
                return tape.response("http_client.get", lambda *a, **kw: None, *args, **kwargs)

        def http_client(*args, **kwargs):
            tape._event("http_client.open", args, kwargs)
            if tape.mode == "replay":
                return ReplayClient()
            return ClientProxy(original_factory(*args, **kwargs))

        wrapped["http_client"] = http_client
        if self.mode == "replay":
            wrapped["sleep"] = lambda *_args, **_kwargs: None
        else:
            wrapped["sleep"] = providers.sleep
        return replace(providers, **wrapped)

    def assert_consumed(self) -> None:
        if self._index != len(self.events):
            raise RuntimeError(
                f"Offline replay left {len(self.events) - self._index} provider tape events unused."
            )


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
        ranking_context = _validate_ranking_context(payload["ranking_context"])
        lastfm = LastFmReplay(payload["lastfm_calls"])
        # The frozen post-gathering snapshot is authoritative. Provider events
        # remain provenance for the capture and are deliberately not replayed.
        import navidrome_server
        actual_text = navidrome_server.recommend_new_music(
            count=int(payload["count"]),
            _gathered_override=gathered,
            _ranking_context_override=ranking_context,
            _lastfm_popularity_fn=lastfm,
            _lastfm_available_override=bool(payload["expected_output"].get("lastfm_api_configured")),
            _record_diagnostics=False,
        )
        actual = json.loads(actual_text)
        lastfm.assert_consumed()
        from discovery.candidate_supply import candidate_supply_report
        expected = payload["expected_output"]
        matches = _comparable_output(actual) == _comparable_output(expected)
        report = {
            "capture_git_sha": envelope.get("git_sha"),
            "capture_schema_version": envelope["schema_version"],
            "reproduced": matches,
            "expected_recommendations": len(expected.get("recommendations", [])),
            "actual_recommendations": len(actual.get("recommendations", [])),
            "network_providers_used": 0,
            "provider_events_replayed": 0,
            "provider_events_provenance_only": len(payload["provider_events"]),
            "lastfm_events_replayed": len(payload["lastfm_calls"]),
            "provider_event_policy": "provenance only; frozen gathered inputs are authoritative",
            "comparison": "all stable output fields except volatile pool diagnostics and Last.fm error state",
            "candidate_supply": candidate_supply_report(payload, actual.get("debug_all_candidates", [])),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if matches else 1
    except Exception as exc:
        print(json.dumps({"reproduced": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
