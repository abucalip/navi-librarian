"""Time-windowed taste profiles (Phase 6 item 1).

Pure and deterministic: the caller passes plain listens whose attributes (genre, era, area,
label, collaborator) were already resolved; nothing here fetches, writes or reads the store, and
nothing feeds a recommendation weight (a separate owner decision, per the Phase 6 exit).

Three windows end at ``config.now``: recent, mid and all-time. For each window and dimension the
profile lists each value's share of that dimension's attribute mass (a listen with several genres
splits one unit across them, so shares sum to 1).

Honesty rules:

* a window with fewer than ``min_listens`` listens is ``low_sample``: its entries are still
  listed (with counts) but it is never used to state a shift;
* a dimension where fewer than ``min_attributed`` listens in the window carry any value is
  ``low_sample`` for that dimension, so missing metadata is not read as taste;
* a shift between a window and all-time is stated only when both sides are sound, and only when the
  share changed by at least ``min_shift`` (absolute share points).
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable, Mapping

DAY = 86400.0
DIMENSIONS = ("genre", "era", "area", "label", "collaborator")
WINDOWS = ("recent", "mid", "all_time")


@dataclass(frozen=True)
class Listen:
    ts: float                                                    # epoch seconds
    attrs: Mapping[str, tuple[str, ...]] = field(default_factory=dict)   # dimension -> values


@dataclass(frozen=True)
class ProfileConfig:
    now: float = 0.0
    recent_days: float = 90.0
    mid_days: float = 365.0
    min_listens: int = 50          # listens in a window before it counts as sound
    min_attributed: int = 30       # listens carrying a value before a dimension counts as sound
    min_shift: float = 0.05        # absolute share change worth stating
    top: int = 10


@dataclass(frozen=True)
class ProfileEntry:
    value: str
    count: int          # listens carrying this value
    share: float        # of the dimension's attribute mass, 0..1


@dataclass(frozen=True)
class WindowProfile:
    window: str
    listens: int
    low_sample: bool
    dimensions: Mapping[str, tuple[ProfileEntry, ...]]
    attributed: Mapping[str, int]
    dimension_low_sample: Mapping[str, bool]


@dataclass(frozen=True)
class Shift:
    window: str
    dimension: str
    value: str
    direction: str       # "up" | "down"
    from_share: float    # all-time
    to_share: float      # in the window


@dataclass(frozen=True)
class TasteProfiles:
    windows: Mapping[str, WindowProfile]
    shifts: tuple[Shift, ...]
    config: ProfileConfig


def _profile(name: str, listens: list[Listen], c: ProfileConfig) -> WindowProfile:
    dims: dict[str, tuple[ProfileEntry, ...]] = {}
    attributed: dict[str, int] = {}
    dim_low: dict[str, bool] = {}
    for dim in DIMENSIONS:
        mass: dict[str, float] = defaultdict(float)
        counts: dict[str, int] = defaultdict(int)
        n = 0
        for listen in listens:
            values = tuple(dict.fromkeys(v for v in listen.attrs.get(dim, ()) if v))
            if not values:
                continue
            n += 1
            for v in values:
                mass[v] += 1.0 / len(values)
                counts[v] += 1
        total = sum(mass.values())
        ranked = sorted(mass, key=lambda v: (-mass[v], v))[: max(c.top, 0)]
        dims[dim] = tuple(ProfileEntry(v, counts[v], round(mass[v] / total, 6)) for v in ranked) if total else ()
        attributed[dim] = n
        dim_low[dim] = n < c.min_attributed
    return WindowProfile(name, len(listens), len(listens) < c.min_listens, dims, attributed, dim_low)


def _shares(dim: str, listens: list[Listen]) -> dict[str, float]:
    mass: dict[str, float] = defaultdict(float)
    for listen in listens:
        values = tuple(dict.fromkeys(v for v in listen.attrs.get(dim, ()) if v))
        for v in values:
            mass[v] += 1.0 / len(values)
    total = sum(mass.values())
    return {v: m / total for v, m in mass.items()} if total else {}


def build_profiles(listens: Iterable[Listen], config: ProfileConfig) -> TasteProfiles:
    """Recent, mid and all-time profiles plus the stated shifts. Listens after ``now`` are ignored."""
    everything = [l for l in listens if l.ts <= config.now]
    cut = {"recent": config.now - config.recent_days * DAY, "mid": config.now - config.mid_days * DAY}
    groups = {
        "recent": [l for l in everything if l.ts > cut["recent"]],
        "mid": [l for l in everything if l.ts > cut["mid"]],
        "all_time": everything,
    }
    windows = {name: _profile(name, groups[name], config) for name in WINDOWS}
    baseline = windows["all_time"]
    shifts: list[Shift] = []
    if not baseline.low_sample:
        for name in ("recent", "mid"):
            w = windows[name]
            if w.low_sample:
                continue
            for dim in DIMENSIONS:
                if w.dimension_low_sample[dim] or baseline.dimension_low_sample[dim]:
                    continue
                then, now = _shares(dim, groups["all_time"]), _shares(dim, groups[name])
                for value in sorted(set(then) | set(now)):
                    delta = now.get(value, 0.0) - then.get(value, 0.0)
                    if abs(delta) >= config.min_shift:
                        shifts.append(Shift(name, dim, value, "up" if delta > 0 else "down",
                                            round(then.get(value, 0.0), 6), round(now.get(value, 0.0), 6)))
    shifts.sort(key=lambda s: (-abs(s.to_share - s.from_share), s.window, s.dimension, s.value))
    return TasteProfiles(windows, tuple(shifts), config)
