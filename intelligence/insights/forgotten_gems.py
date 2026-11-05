"""Forgotten Gems: owned music that was loved once and has gone quiet (Phase 3 item 1).

Pure and deterministic. Callers pass plain play records (from Navidrome play count, last
played, stars and ratings); nothing here fetches, writes or touches the store, so a gem
can never change an ownership flag or a recommendation weight.

The "rediscovery score" is a transparent product:

    score = affinity * dormancy

* affinity (0..1) = ``w_plays`` * play_share + ``w_star`` * starred + ``w_rating`` * rating_share
  (weights are normalised, so only their ratios matter). play_share is
  ``log1p(plays) / log1p(plays_cap)``, capped at 1; rating_share is ``(rating - 1) / 4``
  for a 1..5 rating, 0 when unrated.
* dormancy (0..1) rises linearly from 0 at ``min_dormant_days`` since the last play to 1 at
  ``full_dormant_days``. Anything played more recently is never a gem.

A record needs at least ``min_plays`` plays or a star/rating to count as once loved. Sparse
history yields an empty result with a stated reason, never a guess. Dismissed keys are
dropped before ranking (suppression memory).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

CARD_KIND = "forgotten_gem"
DAY = 86400.0


@dataclass(frozen=True)
class PlayRecord:
    key: str                      # stable id, e.g. "album:<navidrome id>"
    kind: str                     # "album" or "track"
    title: str
    artist: str | None = None
    play_count: int = 0
    last_played: float | None = None   # epoch seconds; None = never played
    starred: bool = False
    rating: int | None = None          # 1..5, None = unrated


@dataclass(frozen=True)
class GemsConfig:
    now: float = 0.0
    w_plays: float = 0.6
    w_star: float = 0.25
    w_rating: float = 0.15
    plays_cap: int = 50
    min_plays: int = 5
    min_dormant_days: float = 180.0
    full_dormant_days: float = 730.0
    min_records_with_history: int = 20   # records with plays/star/rating before any list is stated
    limit: int = 20


@dataclass(frozen=True)
class Gem:
    record: PlayRecord
    score: float
    affinity: float
    dormancy: float
    days_dormant: int

    @property
    def reasons(self) -> list[dict[str, Any]]:
        r = self.record
        reasons: list[dict[str, Any]] = [
            {"kind": "dormant", "evidence": {"days_since_last_play": self.days_dormant}},
        ]
        if r.play_count:
            reasons.append({"kind": "played_often", "evidence": {"play_count": r.play_count}})
        if r.starred:
            reasons.append({"kind": "starred", "evidence": {}})
        if r.rating:
            reasons.append({"kind": "rated", "evidence": {"rating": r.rating}})
        return reasons


@dataclass(frozen=True)
class GemsResult:
    gems: tuple[Gem, ...] = ()
    empty_reason: str | None = None     # "sparse_history" | "no_candidates" | None
    records_with_history: int = 0
    suppressed: int = 0
    config: GemsConfig = field(default_factory=GemsConfig)


def _has_history(r: PlayRecord) -> bool:
    return r.play_count > 0 or r.starred or bool(r.rating)


def _affinity(r: PlayRecord, c: GemsConfig) -> float:
    total = c.w_plays + c.w_star + c.w_rating
    if total <= 0:
        return 0.0
    plays = min(1.0, math.log1p(max(r.play_count, 0)) / math.log1p(c.plays_cap))
    rating = 0.0
    if r.rating:
        rating = (min(max(r.rating, 1), 5) - 1) / 4
    return (c.w_plays * plays + c.w_star * (1.0 if r.starred else 0.0) + c.w_rating * rating) / total


def _dormancy(days: float, c: GemsConfig) -> float:
    if days < c.min_dormant_days:
        return 0.0
    span = max(c.full_dormant_days - c.min_dormant_days, 1.0)
    return min(1.0, (days - c.min_dormant_days) / span)


def find_forgotten_gems(
    records: Iterable[PlayRecord], config: GemsConfig, dismissed: Iterable[str] = ()
) -> GemsResult:
    records = list(records)
    history = sum(1 for r in records if _has_history(r))
    if history < config.min_records_with_history:
        return GemsResult(empty_reason="sparse_history", records_with_history=history, config=config)
    blocked = set(dismissed)
    gems: list[Gem] = []
    suppressed = 0
    for r in records:
        if r.last_played is None or not _has_history(r):
            continue
        if r.play_count < config.min_plays and not (r.starred or r.rating):
            continue
        days = max(0.0, (config.now - r.last_played) / DAY)
        dormancy = _dormancy(days, config)
        if dormancy <= 0:
            continue
        if r.key in blocked:
            suppressed += 1
            continue
        affinity = _affinity(r, config)
        gems.append(Gem(r, round(affinity * dormancy, 6), round(affinity, 6), round(dormancy, 6), int(days)))
    gems.sort(key=lambda g: (-g.score, g.record.key))
    gems = gems[: max(config.limit, 0)]
    return GemsResult(
        gems=tuple(gems), empty_reason=None if gems else "no_candidates",
        records_with_history=history, suppressed=suppressed, config=config,
    )


def gem_card(gem: Gem) -> dict[str, Any]:
    """Generic insight card (docs/ServerV2.md section 8): clients that do not know the kind can still draw it."""
    r = gem.record
    years, rest = divmod(gem.days_dormant, 365)
    quiet = f"{years} year{'s' if years != 1 else ''}" if years else f"{max(rest // 30, 1)} months"
    return {
        "kind": CARD_KIND,
        "title": r.title,
        "body": f"Not played for {quiet}." + (f" Played {r.play_count} times before." if r.play_count else ""),
        "subject": {"key": r.key, "type": r.kind, "title": r.title, "artist": r.artist},
        "actions": [{"kind": "dismiss"}],
        "reasons": gem.reasons,
        "dismissible": True,
        "score": gem.score,
    }
