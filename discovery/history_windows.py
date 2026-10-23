"""History windows: artist-MBID weights for one listening window.

Feeds the tag-lane seed selection (``discovery.tag_queries``) with a window's artists
instead of the default 30-day profile. Pure: the caller supplies the listens.
See docs/engine2.md (Phase 3).
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from discovery.recommendations import windowed_listen_weights


def listen_artist_mbid(listen: Mapping[str, Any]) -> str:
    """Return the artist MBID a ListenBrainz-shaped listen carries, or ``""``.

    Mirrors the gather path: ``artist_mbid`` first, else the first of ``artist_mbids``."""
    additional_info = (listen.get("track_metadata") or {}).get("additional_info") or {}
    artist_mbid = additional_info.get("artist_mbid")
    if not artist_mbid:
        artist_mbids = additional_info.get("artist_mbids")
        if isinstance(artist_mbids, list) and artist_mbids:
            artist_mbid = artist_mbids[0]
    return str(artist_mbid or "")


def window_artist_weights(
    listens: Iterable[Mapping[str, Any]],
    *,
    window_days: float | None = None,
    half_life_days: float | None = None,
) -> Counter[str]:
    """Return {artist MBID: weight} for one window, using ``windowed_listen_weights``.

    Listens without an artist MBID contribute nothing. The result can be passed as the
    ``recent_artist_weights`` argument of ``select_supplementary_tag_queries``.
    """
    records = list(listens)
    weights = windowed_listen_weights(
        records, window_days=window_days, half_life_days=half_life_days,
    )
    totals: Counter[str] = Counter()
    for listen, weight in zip(records, weights):
        artist_mbid = listen_artist_mbid(listen)
        if artist_mbid and weight > 0:
            totals[artist_mbid] += weight
    return totals
