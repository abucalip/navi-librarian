"""Blind spots and discography gaps (Phase 3 item 2).

Pure and deterministic. The caller supplies explicit comparison sets (an artist's studio
release groups from MusicBrainz, ListenBrainz top release groups, or a MusicBrainz series)
and the set of release-group MBIDs the library owns. Nothing here fetches, writes or touches
the store, so a blind spot can never change an ownership flag or a recommendation weight.

Output states a fact about a named set: "you own 41 of 68 in <set>", with the missing
members listed in the set's own order. Wording never says "you should own"; the only action
is dismiss.

Rules:

* membership is by release-group MBID only (case-insensitive); a title is never matched;
* items with no MBID or repeated in a set count once or not at all, and are reported as skipped;
* a set smaller than ``min_set_size`` is too small to call a gap, and a set where the library
  owns fewer than ``min_owned`` is a set the owner does not collect: both are left out with a
  stated reason, not guessed at;
* a complete set (nothing missing) is reported as complete, not as a card;
* dismissed keys (``blind_spot:<set key>``) are dropped before ranking (suppression memory).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

CARD_KIND = "blind_spot"
SET_KINDS = ("studio_discography", "listenbrainz_top", "series")


@dataclass(frozen=True)
class SetItem:
    group_mbid: str | None
    title: str
    year: int | None = None


@dataclass(frozen=True)
class ComparisonSet:
    key: str                      # stable id, e.g. "artist:<mbid>:studio" or "series:<mbid>"
    kind: str                     # one of SET_KINDS
    label: str                    # e.g. "Miles Davis studio albums" or the series name
    items: tuple[SetItem, ...] = ()
    artist: str | None = None
    source: str = "musicbrainz"   # provenance shown in the card


@dataclass(frozen=True)
class BlindSpotsConfig:
    min_set_size: int = 5
    min_owned: int = 2
    max_missing_listed: int = 10
    limit: int = 20


@dataclass(frozen=True)
class BlindSpot:
    set: ComparisonSet
    owned: int
    total: int
    missing: tuple[SetItem, ...]
    skipped_items: int = 0

    @property
    def share_owned(self) -> float:
        return self.owned / self.total if self.total else 0.0

    @property
    def score(self) -> float:
        """Ranking only: sets you own most of rank first, tie-broken by key."""
        return round(self.share_owned, 6)

    @property
    def reasons(self) -> list[dict[str, Any]]:
        return [{"kind": "comparison_set", "evidence": {
            "set_kind": self.set.kind, "source": self.set.source,
            "owned": self.owned, "total": self.total}}]


@dataclass(frozen=True)
class BlindSpotsResult:
    spots: tuple[BlindSpot, ...] = ()
    complete: tuple[str, ...] = ()                 # set keys fully owned
    left_out: tuple[tuple[str, str], ...] = ()     # (set key, reason)
    suppressed: int = 0
    empty_reason: str | None = None                # "no_sets" | "no_candidates" | None
    config: BlindSpotsConfig = field(default_factory=BlindSpotsConfig)


def dismiss_key(set_key: str) -> str:
    return f"{CARD_KIND}:{set_key}"


def _norm(mbid: str | None) -> str | None:
    value = (mbid or "").strip().lower()
    return value or None


def find_blind_spots(
    sets: Iterable[ComparisonSet], owned_group_mbids: Iterable[str], config: BlindSpotsConfig,
    dismissed: Iterable[str] = (),
) -> BlindSpotsResult:
    sets = list(sets)
    if not sets:
        return BlindSpotsResult(empty_reason="no_sets", config=config)
    owned = {m for m in (_norm(x) for x in owned_group_mbids) if m}
    blocked = set(dismissed)
    spots: list[BlindSpot] = []
    complete: list[str] = []
    left_out: list[tuple[str, str]] = []
    suppressed = 0
    for s in sets:
        if s.kind not in SET_KINDS:
            left_out.append((s.key, "unknown_kind"))
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
        if len(members) < config.min_set_size:
            left_out.append((s.key, "set_too_small"))
            continue
        have = sum(1 for i in members if i.group_mbid in owned)
        if have < config.min_owned:
            left_out.append((s.key, "not_collected"))
            continue
        missing = tuple(i for i in members if i.group_mbid not in owned)
        if not missing:
            complete.append(s.key)
            continue
        if dismiss_key(s.key) in blocked:
            suppressed += 1
            continue
        spots.append(BlindSpot(s, have, len(members), missing, skipped))
    spots.sort(key=lambda b: (-b.score, b.set.key))
    spots = spots[: max(config.limit, 0)]
    return BlindSpotsResult(
        spots=tuple(spots), complete=tuple(complete), left_out=tuple(left_out), suppressed=suppressed,
        empty_reason=None if spots else "no_candidates", config=config,
    )


def blind_spot_card(spot: BlindSpot, config: BlindSpotsConfig | None = None) -> dict[str, Any]:
    """Generic insight card (docs/ServerV2.md section 8). States counts and members; never advice."""
    cap = (config or BlindSpotsConfig()).max_missing_listed
    s = spot.set
    listed = spot.missing[: max(cap, 0)]
    return {
        "kind": CARD_KIND,
        "title": s.label,
        "body": f"You own {spot.owned} of {spot.total} in this set; {len(spot.missing)} not in your library.",
        "subject": {"key": dismiss_key(s.key), "type": s.kind, "title": s.label, "artist": s.artist},
        "missing": [{"group_mbid": i.group_mbid, "title": i.title, "year": i.year} for i in listed],
        "missing_total": len(spot.missing),
        "actions": [{"kind": "dismiss"}],
        "reasons": spot.reasons,
        "dismissible": True,
        "score": spot.score,
    }
