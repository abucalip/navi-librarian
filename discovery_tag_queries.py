"""Profile-responsive, bounded MusicBrainz supplementary query selection."""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

MAX_PROFILE_QUERIES = 6
MAX_EXPLORATION_QUERIES = 2
MAX_TAG_LENGTH = 64
# Rotation (opt-in): the top ROTATION_ANCHORS profile tags always stay; the remaining
# profile slots rotate through the next ROTATION_SPREAD ranked tags.
ROTATION_ANCHORS = 3
ROTATION_SPREAD = 3
ROTATION_EXPLORATION_SPREAD = 2


def _rotate_window(items: list, keep: int, spread: int, rotation: int) -> list:
    """Pick `keep` items from the first keep+spread, starting at a rotated offset."""
    window = items[:keep + spread]
    if len(window) <= keep:
        return window
    start = rotation % len(window)
    return [window[(start + i) % len(window)] for i in range(keep)]


def _clean_tag(value: Any) -> str:
    raw = str(value or "").strip()
    if any(ord(char) < 32 for char in raw):
        return ""
    tag = " ".join(raw.split())
    if not tag or len(tag) > MAX_TAG_LENGTH:
        return ""
    return tag


def _query_for_tag(tag: str) -> str:
    # MusicBrainz Lucene query syntax: quote multiword tags and escape syntax.
    escaped = tag.replace("\\", "\\\\").replace('"', '\\"')
    if re.fullmatch(r"[\w-]+", tag, flags=re.UNICODE):
        return f"primarytype:album AND tag:{escaped}"
    return f'primarytype:album AND tag:"{escaped}"'


def select_supplementary_tag_queries(
    recent_artist_weights: Mapping[str, float],
    profile_tags_by_artist: Mapping[str, Sequence[Any]],
    candidate_pool_tags: Sequence[Any],
    *,
    profile_limit: int = MAX_PROFILE_QUERIES,
    exploration_limit: int = MAX_EXPLORATION_QUERIES,
    rotation: int | None = None,
) -> list[tuple[str, str, str]]:
    """Return weighted profile queries plus a small candidate-pool exploration quota.

    The caller supplies cached tag metadata; this function performs no I/O.
    Profile tags are weighted by the decayed listening weight of their artists.
    Exploration tags come only from the broader candidate pool and cannot
    displace the profile-derived quota.

    `rotation=None` keeps the fixed top-N choice. An integer rotates the non-anchor
    profile slots and the exploration slots through a small window of the next-ranked
    tags; the same value always gives the same queries, and the query count is unchanged.
    """
    if profile_limit < 0 or exploration_limit < 0:
        raise ValueError("query limits must be non-negative")

    weights: Counter[str] = Counter()
    display_tags: dict[str, str] = {}
    for artist_id, artist_weight in recent_artist_weights.items():
        try:
            weight = float(artist_weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        for raw_tag in profile_tags_by_artist.get(artist_id, ()):
            tag = _clean_tag(raw_tag)
            key = tag.casefold()
            if not key:
                continue
            weights[key] += weight
            display_tags.setdefault(key, tag)

    selected: list[tuple[str, str, str]] = []
    selected_keys: set[str] = set()

    def append(tag: str, source: str) -> None:
        key = tag.casefold()
        if key in selected_keys:
            return
        selected_keys.add(key)
        slug = re.sub(r"[^a-z0-9]+", "_", tag.casefold()).strip("_") or "other"
        from discovery_recommendations import genre_families
        families = sorted(genre_families([tag]))
        family = families[0] if families else "other"
        selected.append((_query_for_tag(tag), family, f"{source}:{slug}"))

    ranked = sorted(weights.items(), key=lambda item: (-item[1], item[0]))
    if rotation is None or profile_limit <= ROTATION_ANCHORS:
        chosen = ranked[:profile_limit]
    else:
        chosen = ranked[:ROTATION_ANCHORS] + _rotate_window(
            ranked[ROTATION_ANCHORS:], profile_limit - ROTATION_ANCHORS,
            ROTATION_SPREAD, rotation,
        )
    for key, _weight in chosen:
        append(display_tags[key], "profile")

    exploration_tags: dict[str, str] = {}
    for raw_tag in candidate_pool_tags:
        tag = _clean_tag(raw_tag)
        if tag:
            exploration_tags.setdefault(tag.casefold(), tag)
    # Preserve the input order: the caller supplies tags from candidates ranked
    # by CF score, so earlier unseen tags come from stronger candidates.
    exploration = [
        tag for key, tag in exploration_tags.items() if key not in selected_keys
    ]
    if rotation is None:
        exploration = exploration[:exploration_limit]
    else:
        exploration = _rotate_window(
            exploration, exploration_limit, ROTATION_EXPLORATION_SPREAD, rotation,
        )
    for tag in exploration:
        append(tag, "explore")

    return selected
