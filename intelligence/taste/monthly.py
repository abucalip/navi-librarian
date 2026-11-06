"""Pure monthly snapshots of listening (Phase 6 item 3, "then vs now").

A snapshot records what was listened to during one calendar month, from listens the caller passes
in as plain values. Nothing here reads or writes the store, fetches a provider, schedules work, or
feeds a recommendation weight. The output does not depend on the library after the input is
supplied, so a later library change cannot alter an earlier month.

Month boundaries
----------------
A month is ``[start, end)`` in epoch seconds: ``start`` is local midnight on the 1st of the month and
``end`` is local midnight on the 1st of the next month, in the IANA timezone the caller names
(default ``UTC``). A listen belongs to the month when ``start <= ts < end``. Months therefore differ
in length across a DST change, and a listen exactly at ``end`` belongs to the next month. Where a
zone has no local midnight on the 1st (a DST switch at midnight), the boundary is the instant
``zoneinfo`` resolves for that wall-clock time, so the month still begins on that local date.

Reuse
-----
The per-dimension shares come from the same ``profile_window`` the time-windowed profiles use
(genre, era, area, label, collaborator), and the obscurity shares from ``obscurity_window``. Both
are called with the snapshot's listens only, so the snapshot is the month's own profile rather
than a copy of the current one. Unlike the live profile, the snapshot keeps every value (no top-N
cut), so two months can be compared value by value without losing values outside the top ten.

Honesty rules
-------------
* a month with fewer than ``ProfileConfig.min_listens`` listens is ``low_sample``, and an empty
  month is simply low-sample with zero listens;
* a dimension with fewer than ``min_attributed`` listens carrying a value is flagged
  ``dimension_low_sample``; observed entries and counts remain visible, but the dimension is not
  treated as reliable evidence (a dimension with no attributed listens has no entries);
* obscurity shares are meaningful only when the window is not ``low_sample``; when no popularity
  figures are supplied the obscurity part is ``None`` ("not supplied"), never zero.
* the snapshot states no shift; comparing months is left to a later, explicitly reviewed step.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Iterable, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .obscurity import ArtistListen, ObscurityConfig, ObscurityWindow, obscurity_window
from .profiles import Listen, ProfileConfig, WindowProfile, profile_window

DEFAULT_TIMEZONE = "UTC"
MONTH_LABEL = "month"


@dataclass(frozen=True)
class MonthBounds:
    year: int
    month: int
    timezone: str
    start: float      # inclusive, epoch seconds
    end: float        # exclusive, epoch seconds


@dataclass(frozen=True)
class MonthlySnapshot:
    year: int
    month: int
    timezone: str
    start: float
    end: float
    listens: int                        # listens inside [start, end)
    profile: WindowProfile              # all values per dimension, with attributed counts
    obscurity: ObscurityWindow | None   # None when no popularity figures were supplied


def month_bounds(year: int, month: int, timezone: str = DEFAULT_TIMEZONE) -> MonthBounds:
    """``[start, end)`` of a calendar month in the named IANA timezone. Years 1 to 9998."""
    if isinstance(year, bool) or not isinstance(year, int) or not 1 <= year <= 9998:
        raise ValueError(f"year must be an integer from 1 to 9998, not {year!r}")
    if isinstance(month, bool) or not isinstance(month, int) or not 1 <= month <= 12:
        raise ValueError(f"month must be an integer from 1 to 12, not {month!r}")
    try:
        zone = ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValueError(f"unknown timezone {timezone!r}") from exc
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    start = datetime(year, month, 1, tzinfo=zone).timestamp()
    end = datetime(next_year, next_month, 1, tzinfo=zone).timestamp()
    return MonthBounds(year, month, timezone, start, end)


def _listen_key(listen: Listen) -> tuple:
    """Total order over listens, so float sums do not depend on the caller's input order."""
    return (listen.ts, tuple((dim, tuple(sorted(values))) for dim, values in sorted(listen.attrs.items())))


def build_monthly_snapshot(
    listens: Iterable[Listen],
    year: int,
    month: int,
    timezone: str = DEFAULT_TIMEZONE,
    *,
    artist_listens: Iterable[ArtistListen] | None = None,
    popularity: Mapping[str, int | None] | None = None,
    profile_config: ProfileConfig | None = None,
    obscurity_config: ObscurityConfig | None = None,
) -> MonthlySnapshot:
    """Snapshot one calendar month. Inputs are read, never modified; output shares no mutable state with them."""
    bounds = month_bounds(year, month, timezone)
    inside = sorted(
        (l for l in listens if bounds.start <= l.ts < bounds.end),
        key=_listen_key,
    )
    config = replace(profile_config or ProfileConfig(), now=bounds.end, top=None)
    profile = profile_window(MONTH_LABEL, inside, config)

    obscurity = None
    if popularity is not None:
        artists = sorted(
            (a for a in (artist_listens or ()) if bounds.start <= a.ts < bounds.end),
            key=lambda a: (a.ts, a.artist_mbid or ""),
        )
        ob_config = obscurity_config or ObscurityConfig(now=bounds.end)
        obscurity = obscurity_window(MONTH_LABEL, artists, popularity, ob_config)

    return MonthlySnapshot(
        year=bounds.year,
        month=bounds.month,
        timezone=bounds.timezone,
        start=bounds.start,
        end=bounds.end,
        listens=len(inside),
        profile=profile,
        obscurity=obscurity,
    )
