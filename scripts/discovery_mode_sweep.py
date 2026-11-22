"""Offline sweep of the discovery-mode knobs over frozen private inputs (Star Operation S4b).

Reads a pickled lens-build input (the arguments ``discovery.lens_service.build`` passes to
``build_lens_lists``) and, optionally, a private personal-list capture. Makes no network call.
Prints aggregates only: counts, medians, shares and overlaps. No artist, album or tag name is
printed. Inputs contain personal data and stay outside the repository.

    python scripts/discovery_mode_sweep.py LENS_INPUT.pkl [--personal CAPTURE.json]
"""
from __future__ import annotations

import argparse
import json
import math
import pickle
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery import discovery_mode as dm
from discovery.lens_lists import build_lens_lists

OBSCURE_CEILING = 50_000
BAND_SCALES = ((0.5, 0.5), (0.5, 1.0), (1.0, 0.5), (1.0, 1.0), (1.0, 2.0), (2.0, 1.0), (2.0, 2.0))
FLOOR_DIVISORS = (10, 7, 5, 3, 2, 1)


def _key(album: dict[str, Any]) -> tuple[str, str]:
    return (str(album.get("primary_artist")), str(album.get("album")))


def lens_row(payload: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
    """Aggregates of one lens list; ``baseline`` is the balanced payload of the same lens."""
    albums = payload["albums"]
    audiences = [a["album_listeners"] for a in albums if a.get("album_listeners") is not None]
    first_tags = {(a.get("tags") or [None])[0] for a in albums if a.get("tags")}
    row = {
        "fill": len(albums),
        "pool": payload.get("pool_size"),
        "known_audience": len(audiences),
        "median_audience": statistics.median(audiences) if audiences else None,
        "obscure_share": round(sum(1 for v in audiences if v <= OBSCURE_CEILING) / len(audiences), 2) if audiences else None,
        "first_tags": len(first_tags),
    }
    if baseline is not None:
        row["overlap_with_balanced"] = len({_key(a) for a in albums} & {_key(a) for a in baseline["albums"]})
    return row


def sweep_lenses(inputs: dict[str, Any]) -> dict[str, Any]:
    def build(knobs: dm.DiscoveryKnobs) -> dict[str, Any]:
        return build_lens_lists(*inputs["args"], **inputs["kwargs"], knobs=knobs)

    balanced = build(dm.BALANCED)
    out: dict[str, Any] = {"balanced": {name: lens_row(p, None) for name, p in balanced.items()}}
    for low, high in BAND_SCALES:
        built = build(dm.DiscoveryKnobs(audience_min_scale=low, audience_max_scale=high))
        out[f"band min x{low} max x{high}"] = {n: lens_row(p, balanced[n]) for n, p in built.items()}
    for divisor in FLOOR_DIVISORS:
        built = build(dm.DiscoveryKnobs(adventurous_floor_divisor=divisor))
        out[f"floor divisor {divisor}"] = {n: lens_row(p, balanced[n]) for n, p in built.items()}
    return out


def _entropy(families: Iterable[str]) -> float:
    counts = Counter(families)
    total = sum(counts.values())
    return round(-sum(c / total * math.log2(c / total) for c in counts.values()), 2) if total else 0.0


def sweep_personal(capture: str) -> dict[str, Any]:
    import navidrome_server as server
    from recommendation.replay import (LastFmReplay, _validate_ranking_context, load_capture,
                                       thaw_gathered_inputs)

    payload = load_capture(capture)["payload"]

    def run(knobs: dm.DiscoveryKnobs) -> dict[str, Any]:
        dm.MODE_KNOBS = {"balanced": knobs}
        server._discovery_settings_read = lambda: {
            "discovery_mode": "balanced", "recommendation_selection_policy": "family_coverage"}
        return json.loads(server.recommend_new_music(
            count=int(payload["count"]), _gathered_override=thaw_gathered_inputs(payload["gathered_inputs"]),
            _ranking_context_override=_validate_ranking_context(payload["ranking_context"]),
            _lastfm_popularity_fn=LastFmReplay(payload["lastfm_calls"]),
            _lastfm_available_override=bool(payload["expected_output"].get("lastfm_api_configured")),
            _record_diagnostics=False))

    def row(output: dict[str, Any], baseline: set | None) -> dict[str, Any]:
        recs = output["recommendations"]
        listeners = [r["listeners"] for r in recs if r.get("listeners") is not None]
        keys = {(r["artist"], r["album"]) for r in recs}
        result = {
            "fill": len(recs),
            "categories": dict(Counter(r["discovery_category"] for r in recs)),
            "candidate_categories": output.get("debug_candidate_category_counts"),
            "families": len({f for r in recs for f in (r.get("genre_families") or [])[:1]}),
            "family_entropy": _entropy(f for r in recs for f in (r.get("genre_families") or [])[:1]),
            "median_listeners": statistics.median(listeners) if listeners else None,
            "obscure_share": round(sum(1 for v in listeners if v <= OBSCURE_CEILING) / len(listeners), 2) if listeners else None,
        }
        if baseline is not None:
            result["overlap_with_balanced"] = len(keys & baseline)
        return result, keys

    base_out = run(dm.BALANCED)
    base_row, base_keys = row(base_out, None)
    out = {"balanced": base_row}
    for divisor in FLOOR_DIVISORS:
        out[f"floor divisor {divisor}"] = row(run(dm.DiscoveryKnobs(adventurous_floor_divisor=divisor)), base_keys)[0]
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lens_input")
    parser.add_argument("--personal")
    args = parser.parse_args(argv)
    with open(args.lens_input, "rb") as handle:
        report = {"lenses": sweep_lenses(pickle.load(handle))}  # private file written by the owner's own run
    if args.personal:
        report["personal"] = sweep_personal(args.personal)
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
