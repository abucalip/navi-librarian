"""Derive a listener's core and exploration families from their own data.

Family keys come from the shipped category
rules where one matches, otherwise from a normalized tag, so genres outside the
shipped vocabulary still get a family of their own.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
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

ANCESTRY_PATH = Path(__file__).resolve().parent.parent / "settings" / "genre_ancestry.json"
# A tag that ends in one of these words belongs to that family ("doom metal").
ROOT_WORDS = frozenset({
    "metal", "punk", "rock", "pop", "jazz", "folk", "blues", "country",
    "reggae", "funk", "classical", "gospel", "latin",
})


def _load_ancestry(path: Path = ANCESTRY_PATH) -> dict[str, str]:
    """Tag -> root family from the Wikidata-built table; empty if unavailable."""
    try:
        with path.open(encoding="utf-8") as handle:
            tags = json.load(handle).get("tags", {})
    except (OSError, ValueError, AttributeError):
        return {}
    return {str(k): str(v) for k, v in tags.items()}


_ANCESTRY = _load_ancestry()
_GENERIC_SUFFIXES = {"music", "genre", "genres"}


def fallback_family(tag: str) -> str:
    """Normalized family key for a tag no shipped rule matches.

    Order: a trailing root word ("doom metal" -> metal), then the Wikidata
    ancestry table ("boom bap" -> hip-hop), then the head-noun heuristic.

    Otherwise genre names put the head noun last ("k-pop"), so the last word is
    the key. Only the table is ancestry; the other two steps are heuristics.
    """
    text = str(tag or "").casefold().strip()
    words = [w for w in text.replace("_", " ").split() if w]
    while len(words) > 1 and words[-1] in _GENERIC_SUFFIXES:
        words.pop()
    if words and words[-1] in ROOT_WORDS:
        return words[-1]
    if text in _ANCESTRY:
        return _ANCESTRY[text]
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


# Core families whose listens overlap this much (weighted Jaccard) are one taste
# cluster, so a candidate in both is not "cross-genre" (pop and rock, say).
CLUSTER_JACCARD = 0.5


class ClusteredFamilies(set):
    """Core family set that also remembers which taste cluster each belongs to."""

    cluster_of: dict[str, str]


def cluster_core(core: set[str], family_sets_and_weights) -> ClusteredFamilies:
    """Group core families whose weighted listen overlap is at least CLUSTER_JACCARD."""
    rows = [(fs & core, w) for fs, w in family_sets_and_weights]
    parent = {f: f for f in core}

    def find(f: str) -> str:
        while parent[f] != f:
            parent[f] = parent[parent[f]]
            f = parent[f]
        return f

    members = sorted(core)
    for i, a in enumerate(members):
        for b in members[i + 1:]:
            both = sum(w for fs, w in rows if a in fs and b in fs)
            either = sum(w for fs, w in rows if a in fs or b in fs)
            if either and both / either >= CLUSTER_JACCARD:
                parent[find(b)] = find(a)
    result = ClusteredFamilies(core)
    result.cluster_of = {f: find(f) for f in members}
    return result


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
    """Return (core, exploration, source).

    With sparse listening history the core comes from the candidate pool, which
    is built from the listener's similar artists, and nothing is exploration.
    """
    family_sets = [(derived_genre_families(tags), w) for tags, w in tag_lists_and_weights]
    weights: Counter = Counter()
    for families, weight in family_sets:
        for family in families:
            weights[family] += weight
    if sum(weights.values()) < MIN_PROFILE_WEIGHT:
        pool_weights: Counter = Counter()
        for tag in pool_tags:
            for family in derived_genre_families([tag]):
                pool_weights[family] += 1.0
        core = ClusteredFamilies(derive_core_families(pool_weights))
        core.cluster_of = {family: family for family in core}
        return core, set(), "candidate_pool_sparse_history" if core else "no_profile"
    core = cluster_core(derive_core_families(weights), family_sets)
    return core, derive_exploration_families(pool_tags, core), "derived"
