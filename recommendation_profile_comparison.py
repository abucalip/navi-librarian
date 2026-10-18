"""Offline full-engine comparison of contrasting ListenBrainz profiles.

The evaluator keeps the captured candidate/library snapshot, ranking timestamp,
recommendation history, diversity setting, and Last.fm responses fixed. It
reports aggregates only; artist and album identities never enter its report.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Mapping

from discovery_recommendations import decayed_listen_weights, recent_style_families
from discovery_recommendations import music_key
from recommendation_replay import load_capture, thaw_gathered_inputs, _validate_ranking_context

_DAY = 24 * 60 * 60


def load_history(path: str | Path) -> list[dict[str, Any]]:
    """Load a ListenBrainz history JSON array without logging listen metadata."""
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("History file is not readable valid JSON.") from exc
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise ValueError("History must be a JSON array of ListenBrainz listen objects.")
    valid = []
    for row in value:
        try:
            timestamp = float(row.get("listened_at"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(timestamp) and isinstance(row.get("track_metadata"), dict):
            valid.append(row)
    if len(valid) < 2:
        raise ValueError("History needs at least two timestamped listens.")
    return valid


def _timestamp(listen: Mapping[str, Any]) -> float:
    return float(listen["listened_at"])


def first_last_five_day_windows(
    listens: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str]]:
    """Return non-overlapping first and last five-day windows by listen time."""
    timestamps = [_timestamp(row) for row in listens]
    earliest, latest = min(timestamps), max(timestamps)
    first_end = earliest + 5 * _DAY
    last_start = latest - 5 * _DAY
    if first_end > last_start:
        raise ValueError("History span is too short for non-overlapping five-day windows.")
    first = [row for row in listens if earliest <= _timestamp(row) < first_end]
    last = [row for row in listens if last_start <= _timestamp(row) <= latest]
    if not first or not last:
        raise ValueError("Both five-day windows must contain timestamped listens.")
    bounds = {
        "first_start_utc": datetime.fromtimestamp(earliest, timezone.utc).isoformat(),
        "first_end_utc": datetime.fromtimestamp(first_end, timezone.utc).isoformat(),
        "last_start_utc": datetime.fromtimestamp(last_start, timezone.utc).isoformat(),
        "last_end_utc": datetime.fromtimestamp(latest, timezone.utc).isoformat(),
    }
    return first, last, bounds


def _artist_mbid(listen: Mapping[str, Any]) -> str | None:
    metadata = listen.get("track_metadata") or {}
    info = metadata.get("additional_info") or {}
    value = info.get("artist_mbid")
    mbids = info.get("artist_mbids")
    if not value and isinstance(mbids, list) and mbids:
        value = mbids[0]
    return str(value) if value else None


def build_profile_variant(
    gathered_template: dict[str, Any],
    listens: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Clone the frozen snapshot and replace only listen-derived profile fields."""
    from discovery_recommendations import music_key as normalize_music_key

    gathered = copy.deepcopy(gathered_template)
    weights = decayed_listen_weights(listens, half_life_days=14.0)
    recent_artists: Counter[str] = Counter()
    artist_play_counts: Counter[str] = Counter()
    artist_mbid_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    family_play_counts: Counter[str] = Counter()
    genre_cache = gathered["genre_cache"]
    classified_listens = 0

    for listen, weight in zip(listens, weights):
        metadata = listen.get("track_metadata") or {}
        artist = metadata.get("artist_name")
        if artist:
            key = normalize_music_key(artist)
            recent_artists[key] += weight
            artist_play_counts[key] += 1
        mbid = _artist_mbid(listen)
        if not mbid:
            continue
        artist_mbid_counts[mbid] += weight
        tags = genre_cache.get(mbid, [])
        if tags:
            classified_listens += 1
        for family in recent_style_families(tags):
            family_counts[family] += weight
            family_play_counts[family] += 1

    gathered["listens"] = list(listens)
    gathered["recent_artists"] = recent_artists
    gathered["recent_artist_play_counts"] = artist_play_counts
    gathered["recent_artist_mbid_counts"] = artist_mbid_counts
    gathered["recent_family_counts"] = family_counts
    gathered["recent_family_play_counts"] = family_play_counts

    profile = {
        "listens": len(listens),
        "distinct_artists": len(recent_artists),
        "artist_mbid_listens": sum(1 for row in listens if _artist_mbid(row)),
        "genre_classified_listens": classified_listens,
        "profile_families_present": len(family_counts),
    }
    return gathered, profile


class IdentityLastFmReplay:
    """Replay captured Last.fm values by artist/album identity, never over the network."""

    def __init__(self, calls: list[dict[str, Any]]):
        self._results: dict[tuple[str, str], list[Any]] = defaultdict(list)
        for call in calls:
            key = (str(call.get("artist") or ""), str(call.get("album") or ""))
            self._results[key].append(call.get("result"))
        self._used: Counter[tuple[str, str]] = Counter()

    def __call__(self, artist: str, album: str) -> Any:
        key = (str(artist or ""), str(album or ""))
        values = self._results.get(key)
        if not values or self._used[key] >= len(values):
            raise RuntimeError(
                "The private capture's Last.fm tape does not cover this counterfactual run. "
                "No live request was made; a broader captured tape is required."
            )
        result = values[self._used[key]]
        self._used[key] += 1
        return tuple(result) if isinstance(result, list) and len(result) == 2 else result

    @property
    def unique_entries_used(self) -> int:
        return len(self._used)


def _identity(row: Mapping[str, Any]) -> tuple[str, str]:
    return (
        music_key(row.get("artist") or row.get("primary_artist") or ""),
        music_key(row.get("album") or ""),
    )


def _ranked_identities(output: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [
        _identity(row)
        for row in output.get("debug_all_candidates", [])
        if _identity(row) != ("", "")
    ]


def _recommendation_identities(output: Mapping[str, Any]) -> list[tuple[str, str]]:
    return [
        _identity(row)
        for row in output.get("recommendations", [])
        if _identity(row) != ("", "")
    ]


def compare_outputs(first: Mapping[str, Any], last: Mapping[str, Any]) -> dict[str, Any]:
    """Produce aggregate-only responsiveness metrics; never serialize identities."""
    first_recs = _recommendation_identities(first)
    last_recs = _recommendation_identities(last)
    first_set, last_set = set(first_recs), set(last_recs)
    union = first_set | last_set
    first_rank = _ranked_identities(first)
    last_rank = _ranked_identities(last)
    first_positions = {identity: index for index, identity in enumerate(first_rank)}
    last_positions = {identity: index for index, identity in enumerate(last_rank)}
    shared_ranked = set(first_positions) & set(last_positions)
    changed_positions = sum(
        first_positions[item] != last_positions[item] for item in shared_ranked
    )
    displacements = [
        abs(first_positions[item] - last_positions[item]) for item in shared_ranked
    ]
    first_artists = {artist for artist, _ in first_recs if artist}
    last_artists = {artist for artist, _ in last_recs if artist}
    return {
        "first_recommendations": len(first_recs),
        "last_recommendations": len(last_recs),
        "recommendation_overlap": len(first_set & last_set),
        "recommendation_jaccard": round(len(first_set & last_set) / len(union), 4) if union else 1.0,
        "recommendation_positions_changed": sum(
            i < len(last_recs) and first_recs[i] != last_recs[i]
            for i in range(min(len(first_recs), len(last_recs)))
        ),
        "distinct_recommended_artists_first": len(first_artists),
        "distinct_recommended_artists_last": len(last_artists),
        "ranked_candidates_first": len(first_rank),
        "ranked_candidates_last": len(last_rank),
        "shared_candidates_with_changed_rank": changed_positions,
        "shared_candidates_max_rank_displacement": max(displacements, default=0),
        "ranked_candidate_order_changed": first_rank != last_rank,
        "recommendation_order_changed": first_recs != last_recs,
    }


def evaluate(capture_path: str, history_path: str) -> dict[str, Any]:
    envelope = load_capture(capture_path)
    payload = envelope["payload"]
    base_gathered = thaw_gathered_inputs(payload["gathered_inputs"])
    ranking_context = _validate_ranking_context(payload["ranking_context"])
    history = load_history(history_path)
    first_listens, last_listens, bounds = first_last_five_day_windows(history)
    first_gathered, first_profile = build_profile_variant(base_gathered, first_listens)
    last_gathered, last_profile = build_profile_variant(base_gathered, last_listens)

    # All external responses are replayed from the private capture, keyed by
    # identity so changed profile ordering cannot misalign a sequential tape.
    import navidrome_server

    def run(gathered: dict[str, Any]) -> tuple[dict[str, Any], IdentityLastFmReplay]:
        lastfm = IdentityLastFmReplay(payload["lastfm_calls"])
        gathered_for_run = copy.deepcopy(gathered)
        raw = navidrome_server.recommend_new_music(
            count=int(payload["count"]),
            _gathered_override=gathered_for_run,
            _ranking_context_override=ranking_context,
            _lastfm_popularity_fn=lastfm,
            _lastfm_available_override=bool(
                payload["expected_output"].get("lastfm_api_configured")
            ),
            _record_diagnostics=False,
        )
        result = json.loads(raw)
        if "error" in result:
            raise RuntimeError("Recommendation engine returned an error during offline comparison.")
        return result, lastfm

    first_output, first_tape = run(first_gathered)
    last_output, last_tape = run(last_gathered)
    # Repeat each condition to verify deterministic output with identical inputs.
    first_repeat, _ = run(first_gathered)
    last_repeat, _ = run(last_gathered)
    comparison = compare_outputs(first_output, last_output)
    comparison["first_profile_repeatable"] = (
        _recommendation_identities(first_output) == _recommendation_identities(first_repeat)
        and _ranked_identities(first_output) == _ranked_identities(first_repeat)
    )
    comparison["last_profile_repeatable"] = (
        _recommendation_identities(last_output) == _recommendation_identities(last_repeat)
        and _ranked_identities(last_output) == _ranked_identities(last_repeat)
    )
    return {
        "completed": True,
        "capture_schema_version": envelope["schema_version"],
        "capture_git_sha": envelope.get("git_sha"),
        "history_records_used": len(history),
        "window_bounds": bounds,
        "first_window_profile": first_profile,
        "last_window_profile": last_profile,
        "controls": {
            "candidate_pool_fixed": True,
            "library_and_ownership_snapshot_fixed": True,
            "ranking_timestamp_fixed": ranking_context["ranking_now"],
            "recommendation_history_fixed": True,
            "diversity_setting_fixed": ranking_context["diversity_setting"],
            "lastfm_responses": "captured values replayed by artist/album identity",
            "network_providers_used": 0,
        },
        "lastfm_unique_entries_used": {
            "first_profile": first_tape.unique_entries_used,
            "last_profile": last_tape.unique_entries_used,
        },
        "comparison": comparison,
        "interpretation_limit": (
            "This measures responsiveness on one frozen post-gathering candidate/library snapshot. "
            "The capture postdates both listening windows, so this is not a chronological "
            "future-listen hit-rate/nDCG evaluation or a prediction of future listening."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare first/last five-day ListenBrainz profiles against one private frozen candidate snapshot."
    )
    parser.add_argument("capture", help="absolute path to a private schema-v2 recommendation capture")
    parser.add_argument("history", help="path to the timestamped ListenBrainz history JSON array")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(evaluate(args.capture, args.history), ensure_ascii=False, indent=2))
    except Exception as exc:
        # Do not include exception messages, which may contain personal identities.
        print(json.dumps({"completed": False, "error_type": type(exc).__name__,
                          "error": "Offline profile comparison could not be completed."}))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
