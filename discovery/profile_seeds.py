"""Seed queries for history-profile lenses (Engine 2, Phase 3).

Pure: the caller supplies the listens and the cached artist tags; no I/O. The queries have
the same shape as ``select_supplementary_tag_queries`` output, so they can be passed to
``discovery.deep_cuts_supply.run_deep_cuts_tag_supply``.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from discovery.history_windows import (
    artists_with_tags,
    dominant_tags,
    repeated_track_artist_weights,
    window_artist_weights,
)
from discovery.tag_queries import MAX_PROFILE_QUERIES, select_supplementary_tag_queries


def repeated_track_seed_queries(
    listens: Iterable[Mapping[str, Any]],
    artist_tags: Mapping[str, Sequence[Any]],
    *,
    min_track_plays: int = 5,
    dominant_top_artists: int = 40,
    dominant_tag_count: int = 5,
    limit: int = MAX_PROFILE_QUERIES,
) -> list[tuple[str, str, str]]:
    """Tag queries from tracks played at least ``min_track_plays`` times by artists outside
    the all-time dominant tags.

    The dominant tags are the ``dominant_tag_count`` most common tags among the
    ``dominant_top_artists`` most played artists. Artists without tags are skipped, since
    they cannot be placed inside or outside the dominant tags. Returns an empty list when
    nothing qualifies."""
    records = list(listens)
    dominant = dominant_tags(
        window_artist_weights(records), artist_tags,
        top_artists=dominant_top_artists, count=dominant_tag_count,
    )
    weights = repeated_track_artist_weights(
        records, min_track_plays=min_track_plays,
        exclude_artists=artists_with_tags(artist_tags, dominant),
        only_artists={artist for artist, tags in artist_tags.items() if tags},
    )
    return select_supplementary_tag_queries(
        weights, artist_tags, [], profile_limit=limit, exploration_limit=0,
    )
