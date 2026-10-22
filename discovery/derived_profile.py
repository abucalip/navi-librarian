"""Derive a listener's core and exploration families from their own data.

Used only when the taste profile mode is "derived". The fixed tables in
taste_families stay the default. Family keys come from the shipped category
rules where one matches, otherwise from a normalized tag, so genres outside the
shipped vocabulary still get a family of their own.
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping, Sequence

from discovery import taste_families

# Share of the decayed listen weight the core families must cover.
CORE_COVERAGE = 0.80
MAX_CORE_FAMILIES = 8
# Below this much tagged listen weight the profile is too sparse to trust.
MIN_PROFILE_WEIGHT = 5.0
# A non-core family needs this share of the candidate pool tags to explore.
EXPLORATION_MIN_POOL_SHARE = 0.05
MAX_EXPLORATION_FAMILIES = 3

_GENERIC_SUFFIXES = {"music", "genre", "genres"}


def fallback_family(tag: str) -> str:
    """Normalized family key for a tag no shipped rule matches.

    Genre names put the head noun last ("heavy metal", "dream pop"), so the last
    word groups sub-genres under their root. This is a heuristic, not ancestry.
    """
    words = [w for w in str(tag or "").casefold().replace("_", " ").split() if w]
    while len(words) > 1 and words[-1] in _GENERIC_SUFFIXES:
        words.pop()
    return words[-1].strip("-") if words else ""


def derived_genre_families(tags: Iterable[str]) -> set[str]:
    """Families for tags: shipped rules first, normalized tag when none match."""
    families: set[str] = set()
    for tag in tags:
        text = str(tag or "").casefold()
        matched = {
            family for family, terms in taste_families.CATEGORY_RULES
            if any(term in text for term in terms)
        }
        families.update(matched or ({fallback_family(text)} - {""}))
    return families


def family_weights(
    tag_lists_and_weights: Iterable[tuple[Iterable[str], float]],
) -> Counter:
    """Sum listen weight per derived family; each listen counts once per family."""
    totals: Counter = Counter()
    for tags, weight in tag_lists_and_weights:
        for family in derived_genre_families(tags):
            totals[family] += weight
    return totals


def derive_core_families(weights: Mapping[str, float]) -> set[str]:
    """Top families covering about CORE_COVERAGE of the total family weight."""
    total = sum(weights.values())
    if total <= 0:
        return set()
    core: set[str] = set()
    covered = 0.0
    for family, weight in sorted(weights.items(), key=lambda kv: (-kv[1], kv[0])):
        core.add(family)
        covered += weight
        if covered / total >= CORE_COVERAGE or len(core) >= MAX_CORE_FAMILIES:
            break
    return core


def derive_exploration_families(
    pool_tags: Sequence[str], core: set[str],
) -> set[str]:
    """Families well represented in the candidate pool but outside the core."""
    counts = Counter()
    for tag in pool_tags:
        for family in derived_genre_families([tag]):
            counts[family] += 1
    total = sum(counts.values())
    if total <= 0:
        return set()
    ranked = sorted(
        ((f, c) for f, c in counts.items() if f not in core),
        key=lambda kv: (-kv[1], kv[0]),
    )
    return {
        f for f, c in ranked[:MAX_EXPLORATION_FAMILIES]
        if c / total >= EXPLORATION_MIN_POOL_SHARE
    }


def derive_profile(
    tag_lists_and_weights: Iterable[tuple[Iterable[str], float]],
    pool_tags: Sequence[str],
) -> tuple[set[str], set[str], str]:
    """Return (core, exploration, source); sparse history falls back to defaults."""
    weights = family_weights(tag_lists_and_weights)
    if sum(weights.values()) < MIN_PROFILE_WEIGHT:
        return (
            set(taste_families.CORE_FAMILIES),
            set(taste_families.EXPLORATION_FAMILIES),
            "defaults_sparse_history",
        )
    core = derive_core_families(weights)
    return core, derive_exploration_families(pool_tags, core), "derived"
