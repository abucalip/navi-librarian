"""Bounded feedback signal for personal recommendation ranking.

Dismissals apply a decaying soft penalty and saves apply a small decaying
boost, both only to ownership-clear candidates. Nothing is excluded here; the
read-time filter in discovery_list_payload is unchanged. Negative and positive
signals use separate half-lives and expiries. Constants are explicit policy,
not fixture-calibrated quality claims, and the signal is off by default.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import replace
from typing import Any

from discovery_allocation_contract import OwnershipStatus

FEEDBACK_SIGNAL_ENABLED = True
NEGATIVE_HALF_LIFE_SECONDS = 14 * 24 * 60 * 60
NEGATIVE_EXPIRY_SECONDS = 60 * 24 * 60 * 60
POSITIVE_HALF_LIFE_SECONDS = 30 * 24 * 60 * 60
POSITIVE_EXPIRY_SECONDS = 90 * 24 * 60 * 60
ALBUM_DISMISS_PENALTY = 0.50
ARTIST_DISMISS_PENALTY = 0.30
TAG_DISMISS_PENALTY = 0.10
MAX_DISMISS_PENALTY = 0.60
SAVE_ARTIST_BOOST = 0.10


def _decay(age: float, half_life: float, expiry: float) -> float:
    """Return a 0..1 weight for an age in seconds, or 0 outside its window."""
    if age < 0 or age > expiry:
        return 0.0
    return 2.0 ** (-age / half_life)


def _timestamp(row: Mapping[str, Any], field: str) -> float | None:
    """Return a finite timestamp from a feedback row, or None for malformed data."""
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _active_dismissal(row: Mapping[str, Any], *, now: float) -> bool:
    """Return True while a dismissal is inside its negative window."""
    stamp = _timestamp(row, "updated_at")
    return stamp is not None and _decay(float(now) - stamp, NEGATIVE_HALF_LIFE_SECONDS, NEGATIVE_EXPIRY_SECONDS) > 0.0


def _artist_name_key(candidate_source: Mapping[str, Any]) -> str:
    from discovery_recommendations import music_key

    return music_key(candidate_source.get("primary_artist") or candidate_source.get("artist") or "")


def feedback_penalty(
    artist_key: str,
    album_key: str,
    tags: Iterable[str],
    dismissed_tags: frozenset[str],
    feedback: Iterable[Mapping[str, Any]],
    *,
    now: float,
) -> float:
    """Return a bounded penalty fraction for one candidate from dismissals.

    Album and artist dismissals are not summed: the larger applies, so a
    dismiss_artist album row does not double-count with its artist row. Tags
    shared with a dismissed artist add a weaker penalty to other artists only.
    Sibling albums are untouched by album-level dismissals.
    """
    album_penalty = 0.0
    artist_penalty = 0.0
    for row in feedback:
        if not isinstance(row, Mapping):
            continue
        stamp = _timestamp(row, "updated_at")
        if stamp is None:
            continue
        weight = _decay(float(now) - stamp, NEGATIVE_HALF_LIFE_SECONDS, NEGATIVE_EXPIRY_SECONDS)
        if weight == 0.0:
            continue
        if row.get("scope") == "album" and row.get("status") == "not_for_me":
            if row.get("artist_key") == artist_key and row.get("album_key") == album_key:
                album_penalty = max(album_penalty, ALBUM_DISMISS_PENALTY * weight)
        elif row.get("scope") == "artist" and row.get("status") == "not_for_me_artist":
            if row.get("artist_key") == artist_key:
                artist_penalty = max(artist_penalty, ARTIST_DISMISS_PENALTY * weight)

    tag_penalty = 0.0
    if artist_penalty == 0.0 and dismissed_tags and set(tags) & dismissed_tags:
        tag_penalty = TAG_DISMISS_PENALTY

    return min(MAX_DISMISS_PENALTY, max(album_penalty, artist_penalty) + tag_penalty)


def save_boost(artist_key: str, feedback: Iterable[Mapping[str, Any]], *, now: float) -> float:
    """Return a bounded boost fraction from saved albums by the same artist.

    Uses created_at, which is stable for saved rows; updated_at moves when the
    acquisition status changes. remove_for_me deletes the row, so it yields nothing.
    """
    boost = 0.0
    for row in feedback:
        if not isinstance(row, Mapping):
            continue
        if row.get("scope") != "album" or row.get("status") != "for_me":
            continue
        if row.get("artist_key") != artist_key:
            continue
        stamp = _timestamp(row, "created_at")
        if stamp is None:
            continue
        weight = _decay(float(now) - stamp, POSITIVE_HALF_LIFE_SECONDS, POSITIVE_EXPIRY_SECONDS)
        boost = max(boost, SAVE_ARTIST_BOOST * weight)
    return boost


def apply_feedback_signal(
    allocation_candidates: Iterable[Any],
    candidate_by_id: Mapping[str, Mapping[str, Any]],
    feedback: Iterable[Mapping[str, Any]],
    *,
    now: float,
) -> list[Any]:
    """Apply the feedback signal to ownership-clear candidates; fail open on bad input."""
    candidates = list(allocation_candidates)
    rows = [row for row in feedback if isinstance(row, Mapping)]
    if not rows:
        return candidates

    dismissed_keys = {
        row.get("artist_key") for row in rows
        if row.get("scope") == "artist" and row.get("status") == "not_for_me_artist"
        and _active_dismissal(row, now=now)
    }
    dismissed_tags: set[str] = set()
    for candidate in candidates:
        source = candidate_by_id.get(candidate.candidate_id)
        if isinstance(source, Mapping) and candidate.ownership == OwnershipStatus.CLEAR:
            if _artist_name_key(source) in dismissed_keys:
                dismissed_tags.update(candidate.tags)
    frozen_tags = frozenset(dismissed_tags)

    adjusted = []
    for candidate in candidates:
        source = candidate_by_id.get(candidate.candidate_id)
        if candidate.ownership != OwnershipStatus.CLEAR or not isinstance(source, Mapping):
            adjusted.append(candidate)
            continue
        artist_key = _artist_name_key(source)
        penalty = feedback_penalty(
            artist_key, candidate.album_key, candidate.tags, frozen_tags, rows, now=now,
        )
        boost = save_boost(artist_key, rows, now=now)
        factor = (1.0 - penalty) * (1.0 + boost)
        if factor == 1.0:
            adjusted.append(candidate)
            continue
        adjusted.append(replace(candidate, score=float(candidate.score) * factor))
    return adjusted
