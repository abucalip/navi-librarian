"""Anniversary / on-this-day cards (Phase 3 item 5).

Pure and deterministic. The caller supplies the date of "today", owned albums with a release
date, and owned artists with a MusicBrainz life-span. Nothing here fetches, writes or touches
the store. A card states a dated fact ("Released 50 years ago today"); the only action is dismiss.

Rules:

* only full ``YYYY-MM-DD`` dates count. A year or year-month date is dropped and counted in
  ``partial_dates``: a day is never guessed;
* dates after today are dropped (``future_dates``); an anniversary needs at least one full year;
* the day matches when month and day equal today's, within ``window_days`` either side (default 0).
  Feb 29 is observed on Feb 28 in a non-leap year;
* ``milestone_every`` keeps only round years (default every 5; 1 keeps all). A death is never
  paired with a birthday message: the kinds and wording are separate (``artist_born``,
  ``artist_formed``, ``artist_died``, ``artist_disbanded``);
* an artist with an ``ended`` date and no begin is fine; a living artist has none. A begin date is
  treated as a birth for a person and as formation for a group; any other type is skipped (``unknown_type``);
* cards sort by milestone size, then date, then MBID; at most ``limit`` are kept;
* dismissed keys (``anniversary:<kind>:<mbid>:<year>``) are dropped. The key holds the anniversary
  year, so a dismissed 50th does not hide the 55th.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Iterable

CARD_KIND = "anniversary"

_FULL = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


@dataclass(frozen=True)
class DatedAlbum:
    group_mbid: str | None
    title: str
    artist: str | None = None
    release_date: str | None = None


@dataclass(frozen=True)
class DatedArtist:
    artist_mbid: str | None
    name: str
    kind: str | None = None          # MusicBrainz artist type: "person" or "group"
    begin: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class AnniversaryConfig:
    milestone_every: int = 5
    window_days: int = 0
    limit: int = 20


@dataclass(frozen=True)
class Anniversary:
    kind: str                        # album_release | artist_born | artist_formed | artist_died | artist_disbanded
    mbid: str
    title: str
    artist: str | None
    event_date: date
    years: int
    days_from_today: int = 0

    @property
    def key(self) -> str:
        return dismiss_key(self.kind, self.mbid, self.event_date.year + self.years)

    @property
    def reasons(self) -> list[dict[str, Any]]:
        return [{"kind": "anniversary", "evidence": {
            "event": self.kind, "date": self.event_date.isoformat(), "years": self.years}}]


@dataclass(frozen=True)
class AnniversaryResult:
    items: tuple[Anniversary, ...] = ()
    partial_dates: int = 0
    future_dates: int = 0
    unknown_type: int = 0
    suppressed: int = 0
    empty_reason: str | None = None  # "nothing_supplied" | "none_today" | None
    config: AnniversaryConfig = field(default_factory=AnniversaryConfig)


def dismiss_key(kind: str, mbid: str, year: int) -> str:
    return f"{CARD_KIND}:{kind}:{mbid}:{year}"


def _mbid(value: str | None) -> str | None:
    value = (value or "").strip().lower()
    return value or None


def _full_date(value: str | None) -> date | None:
    m = _FULL.match((value or "").strip())
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def _is_partial(value: str | None) -> bool:
    return bool((value or "").strip()) and _full_date(value) is None


def _observed(event: date, year: int) -> date:
    """The event's day in ``year``; Feb 29 falls on Feb 28 in a non-leap year."""
    if event.month == 2 and event.day == 29 and not calendar.isleap(year):
        return date(year, 2, 28)
    return date(year, event.month, event.day)


def _match(event: date, today: date, window: int) -> tuple[int, int] | None:
    """(years, days_from_today) if the event's day falls within the window of today, else None."""
    window = max(window, 0)
    for year in {today.year - 1, today.year, today.year + 1}:
        try:
            observed = _observed(event, year)
        except ValueError:
            continue
        delta = (observed - today).days
        if abs(delta) <= window:
            years = year - event.year
            if years >= 1:
                return years, delta
    return None


def find_anniversaries(
    albums: Iterable[DatedAlbum], artists: Iterable[DatedArtist], today: date,
    config: AnniversaryConfig | None = None, dismissed: Iterable[str] = (),
) -> AnniversaryResult:
    config = config or AnniversaryConfig()
    albums, artists = list(albums), list(artists)
    if not albums and not artists:
        return AnniversaryResult(empty_reason="nothing_supplied", config=config)
    every = max(config.milestone_every, 1)
    blocked = set(dismissed)
    partial = future = unknown = suppressed = 0
    found: list[Anniversary] = []
    seen: set[tuple[str, str]] = set()

    def consider(kind: str, mbid: str | None, title: str, artist: str | None, raw: str | None) -> None:
        nonlocal partial, future, suppressed
        if not (raw or "").strip():
            return
        event = _full_date(raw)
        if event is None:
            partial += 1
            return
        m = _mbid(mbid)
        if m is None or (kind, m) in seen:
            return
        if event > today:
            future += 1
            return
        hit = _match(event, today, config.window_days)
        if hit is None or hit[0] % every:
            return
        seen.add((kind, m))
        item = Anniversary(kind, m, title, artist, event, hit[0], hit[1])
        if item.key in blocked:
            suppressed += 1
            return
        found.append(item)

    for a in albums:
        consider("album_release", a.group_mbid, a.title, a.artist, a.release_date)
    for p in artists:
        t = (p.kind or "").strip().lower()
        if t not in ("person", "group"):
            if (p.begin or "").strip() or (p.end or "").strip():
                unknown += 1
            continue
        begin_kind, end_kind = ("artist_born", "artist_died") if t == "person" else ("artist_formed", "artist_disbanded")
        consider(begin_kind, p.artist_mbid, p.name, p.name, p.begin)
        consider(end_kind, p.artist_mbid, p.name, p.name, p.end)

    found.sort(key=lambda i: (-i.years, i.event_date, i.kind, i.mbid))
    kept = found[: max(config.limit, 0)]
    return AnniversaryResult(
        items=tuple(kept), partial_dates=partial, future_dates=future, unknown_type=unknown,
        suppressed=suppressed, empty_reason=None if kept else "none_today", config=config,
    )


def _when(item: Anniversary) -> str:
    if item.days_from_today == 0:
        return "today"
    n = abs(item.days_from_today)
    return f"{n} day{'s' if n != 1 else ''} {'ago' if item.days_from_today < 0 else 'from now'}"


def anniversary_card(item: Anniversary) -> dict[str, Any]:
    """Generic insight card (docs/ServerV2.md section 8). States a dated fact; never advice."""
    years = f"{item.years} year{'s' if item.years != 1 else ''}"
    when = _when(item)
    if item.kind == "album_release":
        body = f"Released {years} ago {when}" if when == "today" else f"Released {years} ago, {when}"
        body += f" ({item.event_date.isoformat()})."
        subject_type = "release_group"
    else:
        verb = {"artist_born": "Born", "artist_formed": "Formed",
                "artist_died": "Died", "artist_disbanded": "Disbanded"}[item.kind]
        body = f"{verb} {years} ago {when}" if when == "today" else f"{verb} {years} ago, {when}"
        body += f" ({item.event_date.isoformat()})."
        subject_type = "artist"
    return {
        "kind": CARD_KIND,
        "title": item.title,
        "body": body,
        "subject": {"key": item.key, "type": subject_type, "title": item.title, "artist": item.artist,
                    "mbid": item.mbid, "event": item.kind, "years": item.years},
        "actions": [{"kind": "dismiss"}],
        "reasons": item.reasons,
        "dismissible": True,
        "score": float(item.years),
    }
