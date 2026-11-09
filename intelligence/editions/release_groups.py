"""Release to release-group linking for owned albums (docs/ServerV2.md Phase 2, item 1).

A release is not a release group: an album the owner holds is one *release*, and every
reissue, remaster and deluxe edition of it shares one *release group*. This module
records that membership as a ``member_of`` edge (release -> release_group).

It makes no network calls. The caller supplies ``fetch(release_mbid)``, which returns a
MusicBrainz release document that includes its release group (``inc=release-groups``),
``None`` when MusicBrainz has no such release, or raises on a provider failure. The job
that owns provider traffic decides the rate and the budget; ``sweep_owned_releases`` only
bounds how many lookups one run may make.

Rules kept here:

- only a release the library already identified by MBID is looked up, so the link is an
  exact fact from MusicBrainz (``source_explicit``, ``exact_mbid``) and never a guess;
- a release already linked to a different group is reported as a conflict and left alone;
- a failed or missing lookup writes nothing, so a provider outage changes no data;
- the fetched document is stored as an observation, so a later rebuild needs no refetch.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from ..resolution.normalize import normalize_mbid
from ..store import repositories as repo

SOURCE = "musicbrainz"
REL_MEMBER_OF = "member_of"  # release -> release_group

Fetch = Callable[[str], Mapping[str, Any] | None]


@dataclass(frozen=True)
class ReleaseInfo:
    """The few release facts later edition grouping needs, read from a MusicBrainz release."""

    mbid: str
    group_mbid: str
    group_title: str
    title: str | None = None
    primary_type: str | None = None
    secondary_types: tuple[str, ...] = ()
    first_release_date: str | None = None
    date: str | None = None
    country: str | None = None
    status: str | None = None
    disambiguation: str | None = None


@dataclass(frozen=True)
class LinkOutcome:
    """``linked`` (new edge), ``already_linked``, ``conflict``, ``not_found``, ``deferred`` or ``invalid``."""

    outcome: str
    release_entity_id: int | None = None
    group_entity_id: int | None = None
    group_mbid: str | None = None
    reason: str | None = None


@dataclass
class SweepResult:
    looked_up: int = 0
    linked: int = 0
    already_linked: int = 0
    conflicts: int = 0
    not_found: int = 0
    deferred: int = 0
    invalid: int = 0
    remaining: int = 0
    notes: list[str] = field(default_factory=list)


def parse_release(document: Mapping[str, Any], expected_mbid: str | None = None) -> ReleaseInfo | None:
    """Read a MusicBrainz release document; ``None`` when it has no usable release group.

    A document for a different release than ``expected_mbid`` is refused, so a wrong or
    redirected response can never attach one release to another release's group.
    """
    mbid = normalize_mbid(document.get("id"))
    if mbid is None or (expected_mbid is not None and mbid != expected_mbid):
        return None
    group = document.get("release-group")
    if not isinstance(group, Mapping):
        return None
    group_mbid = normalize_mbid(group.get("id"))
    title = _text(group.get("title"))
    if group_mbid is None or title is None:
        return None
    secondary = group.get("secondary-types")
    return ReleaseInfo(
        mbid=mbid, group_mbid=group_mbid, group_title=title, title=_text(document.get("title")),
        primary_type=_text(group.get("primary-type")),
        secondary_types=tuple(s for s in (_text(x) for x in secondary) if s) if isinstance(secondary, list) else (),
        first_release_date=_text(group.get("first-release-date")),
        date=_text(document.get("date")), country=_text(document.get("country")),
        status=_text(document.get("status")), disambiguation=_text(document.get("disambiguation")),
    )


def link_release_group(
    db: sqlite3.Connection,
    release_entity_id: int,
    *,
    fetch: Fetch,
    now: float,
) -> LinkOutcome:
    """Link one release entity to its release group; safe to repeat."""
    release = repo.get_entity(db, release_entity_id)
    if release is None or release["type"] != "release":
        raise ValueError(f"not a release entity: {release_entity_id!r}")
    mbid = normalize_mbid(release["mbid"])
    if mbid is None:
        return LinkOutcome("invalid", release_entity_id, reason="release has no MBID")

    try:
        document = fetch(mbid)
    except Exception as exc:  # provider failure: write nothing, try again later
        return LinkOutcome("deferred", release_entity_id, reason=f"lookup failed: {type(exc).__name__}")
    if document is None:
        return LinkOutcome("not_found", release_entity_id, reason="MusicBrainz has no such release")
    info = parse_release(document, mbid)
    if info is None:
        return LinkOutcome("invalid", release_entity_id, reason="response has no usable release group")

    existing = [e for e in repo.edges_from(db, release_entity_id, REL_MEMBER_OF)]
    other = [e for e in existing if _group_mbid(db, e["to_id"]) != info.group_mbid]
    if other:
        return LinkOutcome("conflict", release_entity_id, group_mbid=info.group_mbid,
                           reason="release is already linked to a different release group")

    obs_id, _ = repo.add_observation(db, SOURCE, dict(document), fetched_at=now, entity_hint=f"release:{mbid}")
    group_id, _ = repo.upsert_entity(db, "release_group", info.group_title, mbid=info.group_mbid)
    db.execute(
        "INSERT INTO release_group_facts (entity_id, primary_type, secondary_types) VALUES (?, ?, ?) "
        "ON CONFLICT (entity_id) DO UPDATE SET primary_type = excluded.primary_type, secondary_types = excluded.secondary_types",
        (group_id, info.primary_type, json.dumps(sorted(info.secondary_types))))
    _, created = repo.add_edge(
        db, release_entity_id, group_id, REL_MEMBER_OF,
        evidence_class="source_explicit", match_quality="exact_mbid", source=SOURCE,
        source_url=f"https://musicbrainz.org/release/{mbid}", observation_id=obs_id,
    )
    return LinkOutcome("linked" if created else "already_linked", release_entity_id, group_id, info.group_mbid)


def sweep_owned_releases(
    db: sqlite3.Connection, *, fetch: Fetch, now: float, limit: int = 25
) -> SweepResult:
    """Link owned, MBID-identified releases that have no release group yet, at most ``limit`` lookups.

    Stops early on a provider failure so an outage does not burn the budget; what is left
    stays in ``remaining`` for the next run.
    """
    if limit < 1:
        raise ValueError("limit must be at least 1")
    result = SweepResult()
    pending = _unlinked_owned_releases(db)
    for index, release_id in enumerate(pending):
        if result.looked_up >= limit:
            result.remaining = len(pending) - index
            break
        result.looked_up += 1
        outcome = link_release_group(db, release_id, fetch=fetch, now=now)
        _tally(result, outcome)
        if outcome.outcome == "deferred":
            result.remaining = len(pending) - index - 1
            result.notes.append("stopped early: provider lookup failed")
            break
    return result


def _unlinked_owned_releases(db: sqlite3.Connection) -> list[int]:
    rows = db.execute(
        "SELECT e.id FROM entities e WHERE e.type = 'release' AND e.owned = 1 AND e.mbid IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM edges g WHERE g.from_id = e.id AND g.relation = ?) ORDER BY e.id",
        (REL_MEMBER_OF,),
    ).fetchall()
    return [r["id"] for r in rows]


def _tally(result: SweepResult, outcome: LinkOutcome) -> None:
    key = {"linked": "linked", "already_linked": "already_linked", "conflict": "conflicts",
           "not_found": "not_found", "deferred": "deferred", "invalid": "invalid"}[outcome.outcome]
    setattr(result, key, getattr(result, key) + 1)


def _group_mbid(db: sqlite3.Connection, entity_id: int) -> str | None:
    entity = repo.get_entity(db, entity_id)
    return entity["mbid"] if entity else None


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None
