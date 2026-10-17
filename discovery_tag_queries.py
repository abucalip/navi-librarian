"""Profile-responsive, bounded MusicBrainz supplementary query selection."""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

MAX_PROFILE_QUERIES = 6
MAX_EXPLORATION_QUERIES = 2
MAX_TAG_LENGTH = 64


def _clean_tag(value: Any) -> str:
    tag = " ".join(str(value or "").strip().split())
    if not tag or len(tag) > MAX_TAG_LENGTH:
        return ""
    if any(ord(char) < 32 for char in tag):
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
) -> list[tuple[str, str, str]]:
    """Return weighted profile queries plus a small candidate-pool exploration quota.

    The caller supplies cached tag metadata; this function performs no I/O.
    Profile tags are weighted by the decayed listening weight of their artists.
    Exploration tags come only from the broader candidate pool and cannot
    displace the profile-derived quota.
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
        selected.append((_query_for_tag(tag), "profile-derived", f"{source}:{slug}"))

    for key, _weight in sorted(weights.items(), key=lambda item: (-item[1], item[0]))[:profile_limit]:
        append(display_tags[key], "profile")

    exploration_tags: dict[str, str] = {}
    for raw_tag in candidate_pool_tags:
        tag = _clean_tag(raw_tag)
        if tag:
            exploration_tags.setdefault(tag.casefold(), tag)
    exploration = sorted(
        (tag for key, tag in exploration_tags.items() if key not in selected_keys),
        key=lambda tag: tag.casefold(),
    )
    for tag in exploration[:exploration_limit]:
        append(tag, "explore")

    return selected
