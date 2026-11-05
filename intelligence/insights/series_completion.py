"""Series completion counters (Phase 3 item 3).

Pure and deterministic. The caller supplies MusicBrainz series as ``ComparisonSet`` objects
(kind ``series``, built by :func:`set_builders.series_set`) and the release-group MBIDs the
library owns. Nothing here fetches, writes or touches the store, so a counter can never change
an ownership flag or a recommendation weight.

Unlike blind spots, a series is a finite, ordered list, so the counter keeps the series' own
order and reports the missing chapters as runs of consecutive positions ("missing 3-5"). Output
states a fact ("you own 41 of 68 in <series>"), never "you should own".

Rules:

* membership is by release-group MBID only (case-insensitive); a title is never matched;
* items with no MBID or repeated in a series count once or not at all, and are reported as skipped;
* a series with fewer than ``min_size`` members is left out (``series_too_small``), and a series where
  the library owns none is left out (``not_started``): both with a stated reason, never guessed at;
* a finished series (nothing missing) is reported in ``complete``, not as a card;
* sets of another kind are left out (``not_a_series``);
* dismissed keys (``series_completion:<set key>``) are dropped before ranking (suppression memory).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .blind_spots import ComparisonSet, SetItem

CARD_KIND = "series_completion"


@dataclass(frozen=True)
class SeriesConfig:
    min_size: int = 3
    min_owned: int = 1
    max_runs_listed: int = 10
    limit: int = 20


@dataclass(frozen=True)
class MissingRun:
    """Consecutive missing members; positions are 1-based in the series' own order."""

    first_position: int
    items: tuple[SetItem, ...]

    @property
    def last_position(self) -> int:
        return self.first_position + len(self.items) - 1


@dataclass(frozen=True)
class SeriesProgress:
    set: ComparisonSet
    owned: int
    total: int
    runs: tuple[MissingRun, ...]
    skipped_items: int = 0

    @property
    def missing(self) -> int:
        return self.total - self.owned

    @property
    def share_owned(self) -> float:
        return self.owned / self.total if self.total else 0.0

    @property
    def score(self) -> float:
        """Ranking only: series closest to finished rank first, tie-broken by key."""
        return round(self.share_owned, 6)

    @property
    def reasons(self) -> list[dict[str, Any]]:
        return [{"kind": "series_progress", "evidence": {
            "source": self.set.source, "owned": self.owned, "total": self.total,
            "missing_runs": len(self.runs)}}]


@dataclass(frozen=True)
class SeriesResult:
    progress: tuple[SeriesProgress, ...] = ()
    complete: tuple[str, ...] = ()
    left_out: tuple[tuple[str, str], ...] = ()     # (series key, reason)
    suppressed: int = 0
    empty_reason: str | None = None                # "no_series" | "no_candidates" | None
    config: SeriesConfig = field(default_factory=SeriesConfig)


def dismiss_key(set_key: str) -> str:
    return f"{CARD_KIND}:{set_key}"


def _norm(mbid: str | None) -> str | None:
    value = (mbid or "").strip().lower()
    return value or None


def find_series_progress(
    series: Iterable[ComparisonSet], owned_group_mbids: Iterable[str], config: SeriesConfig | None = None,
    dismissed: Iterable[str] = (),
) -> SeriesResult:
    config = config or SeriesConfig()
    series = list(series)
    if not series:
        return SeriesResult(empty_reason="no_series", config=config)
    owned = {m for m in (_norm(x) for x in owned_group_mbids) if m}
    blocked = set(dismissed)
    found: list[SeriesProgress] = []
    complete: list[str] = []
    left_out: list[tuple[str, str]] = []
    suppressed = 0
    for s in series:
        if s.kind != "series":
            left_out.append((s.key, "not_a_series"))
            continue
        seen: set[str] = set()
        members: list[SetItem] = []
        skipped = 0
        for item in s.items:
            m = _norm(item.group_mbid)
            if m is None or m in seen:
                skipped += 1
                continue
            seen.add(m)
            members.append(SetItem(m, item.title, item.year))
        if len(members) < config.min_size:
            left_out.append((s.key, "series_too_small"))
            continue
        have = sum(1 for i in members if i.group_mbid in owned)
        if have < max(config.min_owned, 1):
            left_out.append((s.key, "not_started"))
            continue
        if have == len(members):
            complete.append(s.key)
            continue
        if dismiss_key(s.key) in blocked:
            suppressed += 1
            continue
        found.append(SeriesProgress(s, have, len(members), _runs(members, owned), skipped))
    found.sort(key=lambda p: (-p.score, p.set.key))
    found = found[: max(config.limit, 0)]
    return SeriesResult(
        progress=tuple(found), complete=tuple(complete), left_out=tuple(left_out), suppressed=suppressed,
        empty_reason=None if found else "no_candidates", config=config,
    )


def _runs(members: list[SetItem], owned: set[str]) -> tuple[MissingRun, ...]:
    runs: list[MissingRun] = []
    start = 0
    current: list[SetItem] = []
    for position, item in enumerate(members, start=1):
        if item.group_mbid in owned:
            if current:
                runs.append(MissingRun(start, tuple(current)))
                current = []
            continue
        if not current:
            start = position
        current.append(item)
    if current:
        runs.append(MissingRun(start, tuple(current)))
    return tuple(runs)


def series_card(progress: SeriesProgress, config: SeriesConfig | None = None) -> dict[str, Any]:
    """Generic insight card (docs/ServerV2.md section 8). States counts and chapters; never advice."""
    cap = (config or SeriesConfig()).max_runs_listed
    s = progress.set
    return {
        "kind": CARD_KIND,
        "title": s.label,
        "body": f"You own {progress.owned} of {progress.total} in this series; {progress.missing} not in your library.",
        "subject": {"key": dismiss_key(s.key), "type": s.kind, "title": s.label},
        "owned": progress.owned,
        "total": progress.total,
        "missing_total": progress.missing,
        "missing_runs": [
            {"first_position": r.first_position, "last_position": r.last_position,
             "items": [{"group_mbid": i.group_mbid, "title": i.title, "year": i.year} for i in r.items]}
            for r in progress.runs[: max(cap, 0)]
        ],
        "actions": [{"kind": "dismiss"}],
        "reasons": progress.reasons,
        "dismissible": True,
        "score": progress.score,
    }
