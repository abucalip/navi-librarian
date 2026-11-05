"""Lens scorecard (Phase 3 item 6): measure a lens before it may be enabled by default.

Pure and deterministic. The caller passes the cards a lens produced (generic insight cards),
the owner's accepted and dismissed subject keys, and the owned keys. Nothing here fetches,
writes or touches the store, so scoring can never change an ownership flag or a
recommendation weight.

Metrics (all 0..1 unless noted):

* precision = accepted / (accepted + dismissed) over the shown cards that have an outcome.
  Cards with no outcome are counted (``unjudged``) but not scored. Fewer than
  ``min_outcomes`` judged cards is ``insufficient_evidence``, never a guess.
* diversity = distinct artists / cards with an artist; ``top_artist_share`` is the largest
  share one artist holds.
* duplicate_rate = cards repeating an earlier subject key / cards.
* owned_leak_rate = cards whose subject key (or release-group MBID) is owned / cards.
  Any owned leak above ``max_owned_leak_rate`` fails the lens.

Verdict: ``pass`` (all gates met), ``fail`` (a measured gate missed) or
``insufficient_evidence`` (too few cards or judged outcomes). Only ``pass`` allows a lens to
be on by default; ``fail`` and ``insufficient_evidence`` keep it off (docs/ServerV2.md Phase 3 kill rule).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ScorecardConfig:
    min_cards: int = 5
    min_outcomes: int = 10
    min_precision: float = 0.5
    min_diversity: float = 0.6
    max_duplicate_rate: float = 0.0
    max_owned_leak_rate: float = 0.0


@dataclass(frozen=True)
class Scorecard:
    lens: str
    cards: int
    accepted: int = 0
    dismissed: int = 0
    unjudged: int = 0
    precision: float | None = None
    diversity: float | None = None
    top_artist_share: float | None = None
    duplicate_rate: float = 0.0
    owned_leak_rate: float = 0.0
    verdict: str = "insufficient_evidence"
    failures: tuple[str, ...] = ()
    enable_by_default: bool = False
    config: ScorecardConfig = field(default_factory=ScorecardConfig)

    def as_dict(self) -> dict[str, Any]:
        return {
            "lens": self.lens, "cards": self.cards, "accepted": self.accepted, "dismissed": self.dismissed,
            "unjudged": self.unjudged, "precision": self.precision, "diversity": self.diversity,
            "top_artist_share": self.top_artist_share, "duplicate_rate": self.duplicate_rate,
            "owned_leak_rate": self.owned_leak_rate, "verdict": self.verdict,
            "failures": list(self.failures), "enable_by_default": self.enable_by_default,
        }


def _norm(value: Any) -> str | None:
    value = str(value or "").strip().lower()
    return value or None


def score_lens(
    lens: str, cards: Iterable[Mapping[str, Any]], accepted: Iterable[str] = (),
    dismissed: Iterable[str] = (), owned: Iterable[str] = (), config: ScorecardConfig | None = None,
) -> Scorecard:
    config = config or ScorecardConfig()
    cards = list(cards)
    accepted_keys, dismissed_keys = set(accepted), set(dismissed)
    owned_keys = {n for n in (_norm(o) for o in owned) if n}

    seen: set[str] = set()
    duplicates = leaks = acc = dis = unjudged = 0
    artists: dict[str, int] = {}
    for card in cards:
        subject = card.get("subject") or {}
        key = subject.get("key")
        if key is not None:
            if key in seen:
                duplicates += 1
            seen.add(key)
        if _norm(key) in owned_keys or _norm(subject.get("group_mbid")) in owned_keys:
            leaks += 1
        artist = _norm(subject.get("artist"))
        if artist:
            artists[artist] = artists.get(artist, 0) + 1
        if key in dismissed_keys:
            dis += 1
        elif key in accepted_keys:
            acc += 1
        else:
            unjudged += 1

    n = len(cards)
    judged = acc + dis
    precision = round(acc / judged, 6) if judged else None
    with_artist = sum(artists.values())
    diversity = round(len(artists) / with_artist, 6) if with_artist else None
    top_share = round(max(artists.values()) / with_artist, 6) if with_artist else None
    dup_rate = round(duplicates / n, 6) if n else 0.0
    leak_rate = round(leaks / n, 6) if n else 0.0

    failures: list[str] = []
    if n and dup_rate > config.max_duplicate_rate:
        failures.append("duplicates")
    if n and leak_rate > config.max_owned_leak_rate:
        failures.append("owned_leak")
    if diversity is not None and n >= config.min_cards and diversity < config.min_diversity:
        failures.append("low_diversity")
    enough = n >= config.min_cards and judged >= config.min_outcomes
    if enough and precision is not None and precision < config.min_precision:
        failures.append("low_precision")

    if failures:
        verdict = "fail"
    elif not enough:
        verdict = "insufficient_evidence"
    else:
        verdict = "pass"
    return Scorecard(
        lens=lens, cards=n, accepted=acc, dismissed=dis, unjudged=unjudged, precision=precision,
        diversity=diversity, top_artist_share=top_share, duplicate_rate=dup_rate, owned_leak_rate=leak_rate,
        verdict=verdict, failures=tuple(failures), enable_by_default=verdict == "pass", config=config,
    )
