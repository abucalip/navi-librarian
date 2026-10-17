"""Compare captured recommendation output with offline MMR shortlists.

This tool consumes the captured gathered inputs and expected output only. It
intentionally never replays provider events, imports the application, or writes
application state. Keep reports private when they include candidate identities.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

from discovery_mmr import diversity_metrics, mmr_rerank
from recommendation_replay import load_capture

DEFAULT_LAMBDAS = (0.0, 0.1, 0.25, 0.5, 0.75, 1.0)


def _key(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _identity(item: dict[str, Any]) -> tuple[str, str]:
    artist = item.get("artist") or item.get("artist_name") or item.get("name") or ""
    album = item.get("album") or item.get("title") or ""
    return _key(artist), _key(album)


def _artist_key(item: dict[str, Any]) -> str:
    return str(item.get("artist_mbid") or item.get("artist_id") or _key(
        item.get("artist") or item.get("artist_name")
    ))


def _tags(item: dict[str, Any]) -> list[str]:
    value = item.get("genres") or item.get("tags") or item.get("genre_tags") or []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(tag) for tag in value if str(tag).strip()]
    return []


def _is_hard_rejection(item: dict[str, Any]) -> bool:
    decision = _key(item.get("selection_decision") or item.get("decision"))
    return bool(item.get("exact_owned")) or decision in {
        "already_owned", "ineligible", "ineligible_release", "not_album",
        "various_artists", "ambiguous_artist",
    }


def _rankable_candidates(expected: dict[str, Any]) -> list[dict[str, Any]]:
    debug = expected.get("debug_all_candidates")
    if not isinstance(debug, list) or not debug:
        raise ValueError(
            "Capture expected_output has no debug_all_candidates pool; "
            "cannot evaluate MMR without inventing candidate scores."
        )
    result = []
    for row in debug:
        if not isinstance(row, dict) or _is_hard_rejection(row):
            continue
        raw_score = row.get("discovery_score", row.get("score"))
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            continue
        if not math.isfinite(score):
            continue
        artist = row.get("artist") or row.get("artist_name")
        album = row.get("album") or row.get("title")
        if not artist or not album:
            continue
        result.append({
            **row,
            "artist_key": _artist_key(row),
            "score": score,
            "tags": _tags(row),
        })
    if not result:
        raise ValueError("No eligible, scored candidates found in captured debug output.")
    identities = [_identity(row) for row in result]
    if len(identities) != len(set(identities)):
        raise ValueError("Captured scored pool contains duplicate artist/album identities.")
    return result


def _baseline(expected: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    rows = expected.get("recommendations")
    if not isinstance(rows, list):
        raise ValueError("Capture expected_output has no recommendations list.")
    result = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        result.append({**row, "artist_key": _artist_key(row), "tags": _tags(row)})
    return result


def _candidate_identities(rows: Iterable[dict[str, Any]]) -> set[tuple[str, str]]:
    return {_identity(row) for row in rows}


def evaluate_capture(envelope: dict[str, Any], *, limit: int = 10,
                     lambdas: Iterable[float] = DEFAULT_LAMBDAS) -> dict[str, Any]:
    """Return identity-free relevance/diversity metrics for a validated capture."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Capture payload is missing.")
    gathered = payload.get("gathered_inputs")
    if not isinstance(gathered, dict):
        raise ValueError("Capture gathered_inputs is missing.")
    expected = payload.get("expected_output")
    if not isinstance(expected, dict):
        raise ValueError("Capture expected_output is missing.")

    pool = _rankable_candidates(expected)
    baseline = _baseline(expected, limit)
    pool_by_id = {_identity(row): row for row in pool}
    baseline_ids = _candidate_identities(baseline)
    baseline_scored = [pool_by_id[_identity(row)] for row in baseline
                       if _identity(row) in pool_by_id]
    original_top = sorted(pool, key=lambda row: -row["score"])[:limit]
    baseline_order = [_identity(row) for row in baseline]
    original_order = [_identity(row) for row in original_top]
    overlap_denominator = len(set(baseline_order) | set(original_order))
    jaccard = (len(set(baseline_order) & set(original_order)) / overlap_denominator
               if overlap_denominator else 1.0)

    results = []
    for lambda_value in lambdas:
        lambda_value = float(lambda_value)
        reranked = mmr_rerank(pool, limit=limit, lambda_=lambda_value)
        ids = [_identity(row) for row in reranked]
        selected_ids = set(ids)
        baseline_retained = len(selected_ids & baseline_ids)
        selected_scores = [float(row["score"]) for row in reranked]
        baseline_score_by_id = {_identity(row): row["score"] for row in baseline_scored}
        retained_scores = [baseline_score_by_id[key] for key in ids
                           if key in baseline_score_by_id]
        metrics = diversity_metrics(reranked)
        artists = [_key(row.get("artist_key")) for row in reranked]
        nonempty_artists = [artist for artist in artists if artist]
        repeated = mmr_rerank(pool, limit=limit, lambda_=lambda_value)
        results.append({
            "lambda": lambda_value,
            "selected_count": len(reranked),
            "baseline_top_k_retained": baseline_retained,
            "baseline_top_k_retention_rate": (
                baseline_retained / len(baseline_ids) if baseline_ids else 1.0
            ),
            "mean_pairwise_similarity": metrics["mean_pairwise_similarity"],
            "unique_artists": metrics["unique_artists"],
            "mean_selected_relevance_score": (
                sum(selected_scores) / len(selected_scores) if selected_scores else 0.0
            ),
            "baseline_relevance_score_retention": (
                sum(retained_scores) / sum(row["score"] for row in baseline_scored)
                if baseline_scored and sum(row["score"] for row in baseline_scored) != 0
                else None
            ),
            "duplicate_nonempty_artist_keys": len(nonempty_artists) - len(set(nonempty_artists)),
            "all_selected_from_eligible_pool": all(key in pool_by_id for key in ids),
            "deterministic_repeat": ids == [_identity(row) for row in repeated],
            "selected_identities": ids,
        })

    return {
        "capture_git_sha": envelope.get("git_sha"),
        "capture_schema_version": envelope.get("schema_version"),
        "network_providers_used": 0,
        "provider_tape_replayed": False,
        "gathered_album_count": len(gathered.get("albums", [])) if isinstance(gathered.get("albums"), list) else None,
        "gathered_library_album_count": len(gathered.get("library_albums", [])) if isinstance(gathered.get("library_albums"), list) else None,
        "scored_candidate_pool_size": len(pool),
        "baseline_recommendation_count": len(baseline),
        "baseline_top_k_overlap_with_score_order": jaccard,
        "baseline_candidates_with_captured_scores": len(baseline_scored),
        "candidate_rows_rejected_for_hard_eligibility_or_missing_score": (
            len(expected.get("debug_all_candidates", [])) - len(pool)
        ),
        "lambda_results": results,
        "interpretation_notes": [
            "Scores are captured discovery_score values; MMR min-max-normalizes relevance within this candidate pool.",
            "This frozen single-run comparison is not a future-listen hit-rate or nDCG evaluation.",
            "Missing tags contribute zero tag similarity; exact non-empty artist identity still contributes similarity 1.",
            "Candidate identities are included only in this local report. Do not publish or attach the report.",
            "The evaluator excludes rows explicitly marked owned/ineligible and requires finite captured scores; inspect the local fixture's field semantics before treating those flags as a complete eligibility audit.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare captured recommendation output against offline MMR lambda values."
    )
    parser.add_argument("capture", help="absolute path to owner-only recommendation capture")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--lambdas", default="0,0.1,0.25,0.5,0.75,1",
                        help="comma-separated MMR lambda grid")
    parser.add_argument("--identity-free", action="store_true",
                        help="omit selected artist/album identities from printed output")
    args = parser.parse_args(argv)
    try:
        envelope = load_capture(Path(args.capture))
        values = [float(value.strip()) for value in args.lambdas.split(",") if value.strip()]
        report = evaluate_capture(envelope, limit=args.limit, lambdas=values)
        if args.identity_free:
            for row in report["lambda_results"]:
                row.pop("selected_identities", None)
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"evaluated": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
