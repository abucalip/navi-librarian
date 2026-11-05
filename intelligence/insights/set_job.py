"""Fetch comparison sets and refresh blind-spot cards (Phase 3 item 2, job side).

Feeds :mod:`.set_builders` and :mod:`.blind_spots` and saves through :mod:`.blind_spot_persistence`.
It makes no network calls itself: the caller injects one fetcher per source, each returning the
provider document (``None`` when the provider has nothing, raising on a provider failure). The
caller owns rate limits and wiring, so this module adds no provider traffic and cannot change an
ownership flag or a recommendation weight.

Rules:

* artists come only from owned artist entities that carry an MBID, in id order, and one run makes
  at most ``max_lookups`` fetches across all sources (a bound the caller sets);
* a failed fetch skips that set only; the run stops early on a failure so an outage does not burn
  the budget, and when any fetch failed the saved cards are left untouched (last known good), so an
  outage never clears a gap that was real a day ago;
* owned release groups are those linked (``member_of``) from owned releases; an owned release with
  no group link is simply not counted, so the library never looks more complete than it is;
* explicit series MBIDs come from the caller; none are guessed.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping

from . import set_builders
from .blind_spot_persistence import dismissed_set_keys, save_blind_spots
from .blind_spots import BlindSpotsConfig, ComparisonSet, find_blind_spots

Fetch = Callable[[str], Mapping[str, Any] | None]
REL_MEMBER_OF = "member_of"


@dataclass(frozen=True)
class SetFetchers:
    """Any fetcher may be ``None``: that source is then not used."""

    studio: Fetch | None = None       # artist MBID -> MusicBrainz release-group browse document
    listenbrainz: Fetch | None = None  # artist MBID -> ListenBrainz top release groups document
    series: Fetch | None = None       # series MBID -> MusicBrainz series lookup with release-group-rels


@dataclass
class SetJobResult:
    looked_up: int = 0
    sets: int = 0
    failed: int = 0
    not_found: int = 0
    invalid: int = 0
    remaining: int = 0
    saved: int | None = None          # cards stored; None when the saved cards were left untouched
    notes: list[str] = field(default_factory=list)


def owned_artists(db: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = db.execute(
        "SELECT mbid, canonical_name FROM entities WHERE type = 'artist' AND owned = 1 "
        "AND mbid IS NOT NULL ORDER BY id"
    ).fetchall()
    return [(r["mbid"], r["canonical_name"]) for r in rows]


def owned_group_mbids(db: sqlite3.Connection) -> set[str]:
    rows = db.execute(
        "SELECT DISTINCT g.mbid FROM entities r "
        "JOIN edges e ON e.from_id = r.id AND e.relation = ? "
        "JOIN entities g ON g.id = e.to_id AND g.type = 'release_group' "
        "WHERE r.type = 'release' AND r.owned = 1 AND g.mbid IS NOT NULL",
        (REL_MEMBER_OF,),
    ).fetchall()
    return {r["mbid"].lower() for r in rows}


def refresh_blind_spots(
    db: sqlite3.Connection,
    fetchers: SetFetchers,
    *,
    config: BlindSpotsConfig | None = None,
    series_mbids: Iterable[str] = (),
    max_lookups: int = 25,
    now: float | None = None,
) -> SetJobResult:
    if max_lookups < 1:
        raise ValueError("max_lookups must be at least 1")
    config = config or BlindSpotsConfig()
    result = SetJobResult()
    docs: list[tuple[Fetch, str, Callable[[Mapping[str, Any] | None], ComparisonSet | None]]] = []
    for mbid, name in owned_artists(db):
        if fetchers.studio:
            docs.append((fetchers.studio, mbid,
                         lambda d, m=mbid, n=name: set_builders.studio_discography_set(m, n, d)))
        if fetchers.listenbrainz:
            docs.append((fetchers.listenbrainz, mbid,
                         lambda d, m=mbid, n=name: set_builders.listenbrainz_top_set(m, n, d)))
    if fetchers.series:
        for mbid in series_mbids:
            docs.append((fetchers.series, mbid, set_builders.series_set))
    built: list[ComparisonSet] = []
    for index, (fetch, mbid, build) in enumerate(docs):
        if result.looked_up >= max_lookups:
            result.remaining = len(docs) - index
            result.notes.append("stopped at the lookup budget")
            break
        result.looked_up += 1
        try:
            document = fetch(mbid)
        except Exception as exc:  # provider failure: keep the last good cards
            result.failed += 1
            result.remaining = len(docs) - index - 1
            result.notes.append(f"stopped early: lookup failed ({type(exc).__name__})")
            break
        if document is None:
            result.not_found += 1
            continue
        comparison = build(document)
        if comparison is None:
            result.invalid += 1
            continue
        built.append(comparison)
    result.sets = len(built)
    if result.failed or result.remaining:
        result.notes.append("saved cards left unchanged: the run did not cover every set")
        return result
    found = find_blind_spots(built, owned_group_mbids(db), config, dismissed_set_keys(db))
    result.saved = save_blind_spots(db, found, now=now)
    return result
