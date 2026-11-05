"""Identity resolution ladder (docs/ServerV2.md 6.5).

For one library item, in order:

1. a well-formed MBID tag from Navidrome is trusted (``library_tag``, ``exact_mbid``);
2. an ISRC that names exactly one known recording;
3. a MusicBrainz search whose candidates are supplied by the caller: accepted only when
   exactly one candidate clears every check, never the first result;
4. anything else is queued in ``unresolved`` with its candidate list.

This module makes no network calls. Step 3 takes a ``search`` callable, so the job that
owns provider traffic (and its rate limit) decides when and how often it runs. A search
that raises is a transient failure: nothing is written and the outcome is ``deferred``,
so a provider outage leaves existing data and the queue unchanged.

A release is not a release group and a recording is not a work: each ``kind`` resolves to
an entity of that type only. If the library item is already linked to a different MBID,
or the MBID is already linked to a different library item, the item is queued as a
conflict instead of being merged or overwritten.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from ..store import repositories as repo
from . import unresolved as queue
from .normalize import artist_key, durations_match, normalize_isrc, normalize_mbid, title_key

KINDS = ("artist", "recording", "release", "release_group")
ISRC_ALIAS_KIND = "isrc"
DEFAULT_DURATION_TOLERANCE_MS = 3000

Search = Callable[["LibraryRef"], Sequence[dict[str, Any]]]


@dataclass(frozen=True)
class LibraryRef:
    """What Navidrome knows about one item. ``kind`` is the entity type it should become."""

    kind: str
    navidrome_ref: str
    mbid: str | None = None
    isrc: str | None = None
    artist: str | None = None
    title: str | None = None
    track_count: int | None = None
    durations_ms: tuple[int, ...] = ()
    owned: bool = True


@dataclass(frozen=True)
class Resolution:
    """Outcome of one resolution.

    ``outcome`` is ``resolved`` (``entity_id`` set), ``unresolved`` (queued, see
    ``unresolved_id``) or ``deferred`` (a transient failure; nothing was written).
    ``rung`` names the step that decided: ``mbid_tag``, ``isrc``, ``search``,
    ``user_confirmed`` or ``user_rejected``.
    """

    outcome: str
    rung: str | None = None
    entity_id: int | None = None
    mbid: str | None = None
    match_quality: str = "unresolved"
    evidence_class: str | None = None
    reason: str | None = None
    unresolved_id: int | None = None
    candidates: list[dict[str, Any]] = field(default_factory=list)


def add_isrc(db: sqlite3.Connection, recording_id: int, isrc: str) -> bool:
    """Record an ISRC for a recording entity (a matching aid, kept as an alias)."""
    code = normalize_isrc(isrc)
    if code is None:
        raise ValueError(f"not a valid ISRC: {isrc!r}")
    return repo.add_alias(db, recording_id, code, ISRC_ALIAS_KIND)


def resolve(
    db: sqlite3.Connection,
    ref: LibraryRef,
    *,
    now: float,
    search: Search | None = None,
    duration_tolerance_ms: int = DEFAULT_DURATION_TOLERANCE_MS,
) -> Resolution:
    """Run the ladder for one item; see the module docstring."""
    if ref.kind not in KINDS:
        raise ValueError(f"unknown kind: {ref.kind!r}")
    if not ref.navidrome_ref:
        raise ValueError("navidrome_ref is required")

    earlier = queue.find_unresolved(db, ref.kind, ref.navidrome_ref)
    if earlier is not None and earlier["status"] == "user_rejected":
        return Resolution("unresolved", "user_rejected", reason="the owner rejected every candidate",
                          unresolved_id=earlier["id"], candidates=earlier["candidates"])
    if earlier is not None and earlier["status"] == "user_confirmed":
        mbid = queue.confirmed_mbid(earlier)
        if mbid is not None:
            chosen = next(c for c in earlier["candidates"] if c.get("confirmed"))
            return _attach(db, ref, mbid, chosen.get("title") or ref.title or mbid,
                           rung="user_confirmed", match_quality="fuzzy_confirmed",
                           evidence_class="user_confirmed", now=now)

    tag = normalize_mbid(ref.mbid)
    if tag is not None:
        return _attach(db, ref, tag, ref.title or tag, rung="mbid_tag", match_quality="exact_mbid",
                       evidence_class="library_tag", now=now)

    isrc = normalize_isrc(ref.isrc)
    if isrc is not None and ref.kind == "recording":
        known = _recordings_with_isrc(db, isrc)
        if len(known) == 1:
            entity = known[0]
            if entity["navidrome_id"] not in (None, ref.navidrome_ref):
                return _queue(db, ref, [_candidate(entity)], "isrc names a recording linked to another library item", now)
            return _attach(db, ref, entity["mbid"], entity["canonical_name"], rung="isrc",
                           match_quality="isrc", evidence_class="derived", now=now, entity_id=entity["id"])
        if len(known) > 1:
            return _queue(db, ref, [_candidate(e) for e in known], "isrc names more than one recording", now)

    if search is None:
        return _queue(db, ref, [], "no search available for this item", now)
    try:
        found = list(search(ref))
    except Exception as exc:  # provider failure: write nothing, try again later
        return Resolution("deferred", "search", reason=f"search failed: {type(exc).__name__}")

    passing, notes = _passing_candidates(ref, found, duration_tolerance_ms)
    if len(passing) == 1:
        chosen = passing[0]
        return _attach(db, ref, normalize_mbid(chosen["mbid"]) or "", chosen.get("title") or ref.title or "",
                       rung="search", match_quality="fuzzy_confirmed", evidence_class="derived", now=now)
    if not passing:
        return _queue(db, ref, [_clean(c) for c in found], notes or "no candidate cleared every check", now)
    return _queue(db, ref, [_clean(c) for c in passing], "more than one candidate cleared every check", now)


# ------------------------------------------------------------------ internals

def _passing_candidates(
    ref: LibraryRef, found: Sequence[dict[str, Any]], tolerance_ms: int
) -> tuple[list[dict[str, Any]], str | None]:
    """Candidates that clear every check, plus a reason when the item cannot be checked at all."""
    if not artist_key(ref.artist) or not title_key(ref.title):
        return [], "artist and title are both needed to search"
    if ref.track_count is None and not ref.durations_ms:
        return [], "names alone are not enough: no track count or durations to check"
    return [c for c in found if normalize_mbid(c.get("mbid")) and _clears(ref, c, tolerance_ms)], None


def _clears(ref: LibraryRef, c: dict[str, Any], tolerance_ms: int) -> bool:
    if artist_key(c.get("artist")) != artist_key(ref.artist):
        return False
    if title_key(c.get("title")) != title_key(ref.title):
        return False
    if ref.track_count is not None and c.get("track_count") != ref.track_count:
        return False
    if ref.durations_ms:
        theirs = c.get("durations_ms") or []
        if len(theirs) != len(ref.durations_ms):
            return False
        if not all(durations_match(a, b, tolerance_ms) for a, b in zip(ref.durations_ms, theirs)):
            return False
    return True


def _attach(
    db: sqlite3.Connection,
    ref: LibraryRef,
    mbid: str,
    name: str,
    *,
    rung: str,
    match_quality: str,
    evidence_class: str,
    now: float,
    entity_id: int | None = None,
) -> Resolution:
    """Link the library item to the entity for ``mbid``, or queue a conflict; never overwrite."""
    mine = repo.find_entity(db, ref.kind, navidrome_id=ref.navidrome_ref)
    if mine is not None and mine["mbid"] not in (None, mbid):
        return _queue(db, ref, [{"mbid": mbid, "title": name}, {"mbid": mine["mbid"], "title": mine["canonical_name"]}],
                      "library item is already linked to a different MBID", now)
    by_mbid = repo.find_entity(db, ref.kind, mbid=mbid)
    if by_mbid is not None and by_mbid["navidrome_id"] not in (None, ref.navidrome_ref):
        # Same MBID, another library item (for example two copies of an album): keep the
        # entity as it is and report it; linking a second item needs its own decision.
        return Resolution("resolved", rung, by_mbid["id"], mbid, match_quality, evidence_class)
    ids = {"mbid": mbid, "navidrome_id": ref.navidrome_ref}
    eid, _ = repo.upsert_entity(db, ref.kind, name, owned=ref.owned, **ids)
    if entity_id is not None and eid != entity_id:
        return _queue(db, ref, [{"mbid": mbid, "title": name}], "isrc match and library item point at different entities", now)
    if ref.kind == "recording" and normalize_isrc(ref.isrc):
        add_isrc(db, eid, ref.isrc)  # type: ignore[arg-type]
    return Resolution("resolved", rung, eid, mbid, match_quality, evidence_class)


def _queue(db: sqlite3.Connection, ref: LibraryRef, candidates: list[dict[str, Any]], reason: str, now: float) -> Resolution:
    uid, _ = queue.queue_unresolved(db, ref.kind, ref.navidrome_ref, candidates, reason, now=now)
    return Resolution("unresolved", None, reason=reason, unresolved_id=uid, candidates=candidates)


def _recordings_with_isrc(db: sqlite3.Connection, isrc: str) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT DISTINCT e.* FROM entities e JOIN entity_aliases a ON a.entity_id = e.id "
        "WHERE e.type = 'recording' AND e.mbid IS NOT NULL AND a.kind = ? AND a.alias = ? ORDER BY e.id",
        (ISRC_ALIAS_KIND, isrc),
    ).fetchall()
    return [dict(r) for r in rows]


def _candidate(entity: dict[str, Any]) -> dict[str, Any]:
    return {"mbid": entity["mbid"], "title": entity["canonical_name"]}


def _clean(c: dict[str, Any]) -> dict[str, Any]:
    keep = ("mbid", "artist", "title", "track_count", "durations_ms", "date", "country", "disambiguation")
    return {k: c[k] for k in keep if k in c}
