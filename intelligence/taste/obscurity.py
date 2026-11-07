"""Obscurity/mainstream profile versus ListenBrainz sitewide popularity (Phase 6 item 2).

Pure and deterministic: the caller passes listens with the primary artist MBID and a map of sitewide
listen counts (``None`` or absent means the provider has no figure). Nothing here fetches, writes or
feeds a recommendation weight.

Each listen is placed in a bucket by the sitewide listen count of its primary (first) artist:
``mainstream`` (>= 1,000,000), ``known`` (>= 100,000), ``niche`` (>= 10,000), ``obscure`` (below).
Thresholds are unmeasured starting values. A listen whose artist has no figure is ``unknown`` and is
left out of the shares, so missing data is never read as obscurity.

Honesty rules, as for the time-windowed profiles: a window is ``low_sample`` when fewer than
``min_known`` listens carry a figure; a shift in the obscure share (recent or mid versus all-time) is
stated only when both sides are sound and the change is at least ``min_shift`` share points.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .profiles import DAY, WINDOWS

BUCKETS = ("mainstream", "known", "niche", "obscure")


@dataclass(frozen=True)
class ArtistListen:
    ts: float
    artist_mbid: str | None


@dataclass(frozen=True)
class ObscurityConfig:
    now: float = 0.0
    recent_days: float = 90.0
    mid_days: float = 365.0
    mainstream_at: int = 1_000_000
    known_at: int = 100_000
    niche_at: int = 10_000
    min_known: int = 50
    min_shift: float = 0.05


@dataclass(frozen=True)
class ObscurityWindow:
    window: str
    listens: int
    known: int                 # listens whose artist has a sitewide figure
    unknown: int
    low_sample: bool
    shares: Mapping[str, float]    # bucket -> share of known listens
    median_listens: int | None     # median sitewide count over known listens


@dataclass(frozen=True)
class ObscurityShift:
    window: str
    direction: str       # "more_obscure" | "more_mainstream"
    from_share: float    # obscure share, all-time
    to_share: float      # obscure share, in the window


@dataclass(frozen=True)
class ObscurityProfile:
    windows: Mapping[str, ObscurityWindow]
    shifts: tuple[ObscurityShift, ...]
    config: ObscurityConfig


def bucket_of(count: int, c: ObscurityConfig) -> str:
    if count >= c.mainstream_at:
        return "mainstream"
    if count >= c.known_at:
        return "known"
    if count >= c.niche_at:
        return "niche"
    return "obscure"


def song_bands(song_artists: Mapping[str, str | None], popularity: Mapping[str, int | None],
               c: ObscurityConfig | None = None) -> dict[str, str]:
    """Band per song id from its primary artist's sitewide count; for smart playlist rules.

    A song whose artist has no figure gets no entry, so missing data is never read as ``obscure``.
    The bands are the profile's buckets, with the same unmeasured thresholds.
    """
    c = c or ObscurityConfig()
    out: dict[str, str] = {}
    for song_id, mbid in song_artists.items():
        n = _count(popularity, mbid)
        if n is not None:
            out[song_id] = bucket_of(n, c)
    return out


def _count(popularity: Mapping[str, int | None], mbid: str | None) -> int | None:
    value = popularity.get(mbid) if mbid else None
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def obscurity_window(name: str, listens: Iterable[ArtistListen], popularity: Mapping[str, int | None],
                     c: ObscurityConfig) -> ObscurityWindow:
    """One window's obscurity shares over the given listens. Shares are meaningful only when not low_sample."""
    listens = list(listens)
    counts = [n for n in (_count(popularity, l.artist_mbid) for l in listens) if n is not None]
    tally = {b: 0 for b in BUCKETS}
    for n in counts:
        tally[bucket_of(n, c)] += 1
    known = len(counts)
    shares = {b: round(tally[b] / known, 6) if known else 0.0 for b in BUCKETS}
    median = None
    if counts:
        ordered = sorted(counts)
        mid = len(ordered) // 2
        median = ordered[mid] if len(ordered) % 2 else int(round((ordered[mid - 1] + ordered[mid]) / 2))
    return ObscurityWindow(name, len(listens), known, len(listens) - known, known < c.min_known, shares, median)


def build_obscurity(listens: Iterable[ArtistListen], popularity: Mapping[str, int | None],
                    config: ObscurityConfig) -> ObscurityProfile:
    """Recent, mid and all-time obscurity windows plus any stated shift. Listens after ``now`` are ignored."""
    everything = [l for l in listens if l.ts <= config.now]
    groups = {
        "recent": [l for l in everything if l.ts > config.now - config.recent_days * DAY],
        "mid": [l for l in everything if l.ts > config.now - config.mid_days * DAY],
        "all_time": everything,
    }
    windows = {name: obscurity_window(name, groups[name], popularity, config) for name in WINDOWS}
    base = windows["all_time"]
    shifts: list[ObscurityShift] = []
    if not base.low_sample:
        for name in ("recent", "mid"):
            w = windows[name]
            if w.low_sample:
                continue
            delta = w.shares["obscure"] - base.shares["obscure"]
            if abs(delta) >= config.min_shift:
                shifts.append(ObscurityShift(name, "more_obscure" if delta > 0 else "more_mainstream",
                                             base.shares["obscure"], w.shares["obscure"]))
    return ObscurityProfile(windows, tuple(shifts), config)


def artist_mbids(listens: Iterable[ArtistListen]) -> list[str]:
    """Distinct artist MBIDs in first-seen order, for one batch popularity request."""
    return list(dict.fromkeys(l.artist_mbid for l in listens if l.artist_mbid))


def popularity_from_response(rows: object) -> dict[str, int | None]:
    """Map a ``POST /1/popularity/artist`` response to ``{mbid: total_listen_count or None}``."""
    out: dict[str, int | None] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, Mapping) or not row.get("artist_mbid"):
            continue
        n = row.get("total_listen_count")
        out[str(row["artist_mbid"])] = n if isinstance(n, int) and not isinstance(n, bool) and n >= 0 else None
    return out
