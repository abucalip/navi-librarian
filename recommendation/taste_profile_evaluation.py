"""Offline derived taste profile evaluation on synthetic profiles.

Each profile is a weighted listening history plus a candidate pool, all tag
lists with no artist identities. The evaluator runs the real profile derivation,
classification and exploration-bonus code and reports aggregates only. Synthetic
profiles show whether classification adapts to different tastes; they are not
evidence about real listeners.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from typing import Any

from discovery import derived_profile
from discovery.recommendations import (
    apply_familiarity_exploration_bonus,
    classify_recommendation_category,
)

CATEGORIES = ("adjacent", "cross_genre", "adventurous", "unclassified")


def _hist(*groups: tuple[list[str], int]) -> list[tuple[list[str], float]]:
    return [(tags, 1.0) for tags, n in groups for _ in range(n)]


# name -> (listening history, candidate pool as one tag list per candidate)
SYNTHETIC_PROFILES: dict[str, tuple[list, list[list[str]]]] = {
    "jazz": (
        _hist((["hard bop", "jazz"], 10), (["bebop"], 6), (["hip hop"], 3)),
        [["jazz"], ["post-bop"], ["afrobeat"], ["hip hop"], ["gnawa"], ["soul"],
         ["experimental"], ["folk"], ["bossa nova"], ["ambient"]],
    ),
    "metal": (
        _hist((["heavy metal"], 8), (["thrash metal", "metal"], 6),
              (["death metal"], 5), (["doom metal", "folk"], 2)),
        [["black metal"], ["power metal"], ["doom metal"], ["hardcore punk"],
         ["folk metal"], ["folk"], ["progressive rock"], ["industrial"], ["jazz"],
         ["noise"]],
    ),
    "classical": (
        _hist((["baroque", "classical"], 9), (["romantic classical"], 7),
              (["opera"], 4), (["minimalism", "contemporary classical"], 3)),
        [["chamber music"], ["classical"], ["opera"], ["early music"],
         ["choral"], ["film score"], ["ambient"], ["jazz"], ["drone"], ["folk"]],
    ),
    "k-pop": (
        _hist((["k-pop"], 12), (["korean pop", "dance-pop"], 6),
              (["k-rap", "hip hop"], 4), (["korean r&b"], 3)),
        [["k-pop"], ["j-pop"], ["dance-pop"], ["korean hip hop"], ["city pop"],
         ["synthpop"], ["r&b"], ["electropop"], ["indie rock"], ["afropop"]],
    ),
    "mixed": (
        _hist((["jazz"], 5), (["metal"], 5), (["hip hop"], 5), (["classical"], 5)),
        [["jazz fusion"], ["thrash metal"], ["rap"], ["baroque"], ["folk"],
         ["afrobeat"], ["noise"], ["house"], ["gnawa"], ["soul"]],
    ),
}


def evaluate_profile(history, pool: list[list[str]]) -> dict[str, Any]:
    pool_tags = [tag for tags in pool for tag in tags]
    core, expl, source = derived_profile.derive_profile(history, pool_tags)
    categories: Counter = Counter()
    families: Counter = Counter()
    bonus_hits = 0
    outside_everything = 0
    for tags in pool:
        category, fams = classify_recommendation_category(
            {"artist": "synthetic"}, tags, core, expl)
        categories[category] += 1
        families.update(fams)
        outside_everything += category == "adventurous" and not (fams & expl)
        boosted = apply_familiarity_exploration_bonus({"score": 1.0}, 1.5, tags, expl)
        plain = apply_familiarity_exploration_bonus({"score": 1.0}, 1.5, tags, set())
        bonus_hits += boosted > plain
    total = len(pool)
    return {
        "profile_source": source,
        "core_families": sorted(core),
        "exploration_families": sorted(expl),
        "category_counts": {c: categories.get(c, 0) for c in CATEGORIES},
        "adventurous_share": round(categories["adventurous"] / total, 3),
        "adventurous_outside_exploration_share": round(outside_everything / total, 3),
        "unclassified_share": round(categories["unclassified"] / total, 3),
        "distinct_candidate_families": len(families),
        "exploration_bonus_candidates": bonus_hits,
    }


def evaluate_all() -> dict[str, Any]:
    return {name: evaluate_profile(*spec) for name, spec in SYNTHETIC_PROFILES.items()}


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(evaluate_all(), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
