"""Pure listening-context profiles (Phase 6 item 4: time-of-day and day-of-week lenses).

Listens are grouped by the local time they happened in a named IANA timezone (default ``UTC``) and
each group gets the same per-dimension profile the time-windowed profiles use. Nothing here reads or
writes the store, fetches a provider, schedules work, or feeds a recommendation weight.

Contexts
--------
Two independent lenses, each a partition of the listens:

* ``time_of_day``: ``night`` (00:00 to 05:59), ``morning`` (06:00 to 11:59), ``afternoon``
  (12:00 to 17:59), ``evening`` (18:00 to 23:59), by local wall-clock hour;
* ``day_type``: ``weekday`` (Monday to Friday) or ``weekend`` (Saturday and Sunday), by local date.

The boundaries are fixed starting values, not measured clusters. Local time follows the zone's DST
rules, so a listen's context is that of its wall clock on the day it happened.

Honesty rules
-------------
* a context with fewer than ``ProfileConfig.min_listens`` listens is ``low_sample``; its entries stay
  visible but it is never presented as a stable pattern; an empty context is low-sample with zero
  listens (every context of a lens is always present, so a missing context is never ambiguous);
* a dimension with fewer than ``min_attributed`` carrying listens is ``dimension_low_sample``;
* each profile keeps every value (no top-N cut), and no shift or comparison between contexts is stated.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .profiles import Listen, ProfileConfig, WindowProfile, profile_window

DEFAULT_TIMEZONE = "UTC"
TIME_OF_DAY = ("night", "morning", "afternoon", "evening")
DAY_TYPES = ("weekday", "weekend")
LENSES: Mapping[str, tuple[str, ...]] = {"time_of_day": TIME_OF_DAY, "day_type": DAY_TYPES}


@dataclass(frozen=True)
class ContextProfiles:
    timezone: str
    listens: int                                    # listens supplied (each lands in one context per lens)
    lenses: Mapping[str, Mapping[str, WindowProfile]]   # lens -> context -> profile


def _zone(timezone: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError(f"unknown timezone {timezone!r}") from exc


def time_of_day(hour: int) -> str:
    return TIME_OF_DAY[hour // 6]


def day_type(weekday: int) -> str:
    """``weekday`` is ``datetime.weekday()``: Monday is 0."""
    return "weekend" if weekday >= 5 else "weekday"


def _listen_key(listen: Listen) -> tuple:
    return (listen.ts, tuple((dim, tuple(sorted(values))) for dim, values in sorted(listen.attrs.items())))


def build_context_profiles(
    listens: Iterable[Listen],
    timezone: str = DEFAULT_TIMEZONE,
    config: ProfileConfig | None = None,
) -> ContextProfiles:
    """Profile every context of both lenses. Inputs are read, never modified."""
    zone = _zone(timezone)
    ordered = sorted(listens, key=_listen_key)   # input order never changes float sums
    groups: dict[str, dict[str, list[Listen]]] = {
        lens: {name: [] for name in names} for lens, names in LENSES.items()
    }
    for listen in ordered:
        local = datetime.fromtimestamp(listen.ts, zone)
        groups["time_of_day"][time_of_day(local.hour)].append(listen)
        groups["day_type"][day_type(local.weekday())].append(listen)
    c = replace(config or ProfileConfig(), top=None)
    lenses = {
        lens: {name: profile_window(name, groups[lens][name], c) for name in names}
        for lens, names in LENSES.items()
    }
    return ContextProfiles(timezone, len(ordered), lenses)
