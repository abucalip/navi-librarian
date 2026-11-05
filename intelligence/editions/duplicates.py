"""Duplicate finder (docs/ServerV2.md Phase 2, item 3).

Two kinds of suggestion, both read-only and both built from what the store already holds:

- ``duplicate_album``: two or more *owned* releases that share one MusicBrainz release
  group, i.e. the same album held as several editions. Each suggestion carries the
  editions and how every later edition's tracklist differs from the first.
- ``duplicate_recording``: one recording (identified by its MusicBrainz recording ID)
  that appears on two or more owned releases. When those releases are editions of one
  album the overlap is expected and says so; when they are different albums (a
  compilation, a single, a best-of) the suggestion says that instead.

Rules kept here:

- suggestions only. Nothing is merged, hidden, edited or deleted, no route or action
  deletes anything, and every suggestion says ``suggestion_only: true``;
- every suggestion carries ``reasons[]`` with the evidence it rests on, so it can explain
  itself; recordings without an MBID are not compared (a title match is not identity)
  and are counted in ``skipped_recordings`` so the gap is visible, never silent;
- no network calls, and the output order is deterministic.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from ..store import repositories as repo
from .grouping import REL_APPEARS_ON, Edition, TracklistDiff, compare_tracklists, group_editions
from .release_groups import REL_MEMBER_OF

DUPLICATE_ALBUM = "duplicate_album"
DUPLICATE_RECORDING = "duplicate_recording"


@dataclass(frozen=True)
class Reason:
    code: str
    detail: str


@dataclass(frozen=True)
class EditionDifference:
    """How one later edition's tracklist differs from the first owned edition's."""

    release_id: int
    against_release_id: int
    diff: TracklistDiff


@dataclass(frozen=True)
class DuplicateAlbum:
    group_entity_id: int
    group_mbid: str | None
    title: str
    editions: tuple[Edition, ...]
    differences: tuple[EditionDifference, ...]
    reasons: tuple[Reason, ...]
    kind: str = DUPLICATE_ALBUM
    suggestion_only: bool = True


@dataclass(frozen=True)
class RecordingAppearance:
    release_id: int
    release_title: str
    position: str | None
    group_entity_id: int | None


@dataclass(frozen=True)
class DuplicateRecording:
    recording_entity_id: int
    recording_mbid: str
    title: str
    appearances: tuple[RecordingAppearance, ...]
    same_album: bool  # every appearance is in one release group: an edition overlap, expected
    reasons: tuple[Reason, ...]
    kind: str = DUPLICATE_RECORDING
    suggestion_only: bool = True


@dataclass
class DuplicateReport:
    albums: list[DuplicateAlbum] = field(default_factory=list)
    recordings: list[DuplicateRecording] = field(default_factory=list)
    skipped_recordings: int = 0  # on two or more owned releases but without an MBID
    truncated: bool = False


def find_duplicate_albums(db: sqlite3.Connection) -> list[DuplicateAlbum]:
    """Release groups with two or more owned editions, ordered by group title then id."""
    groups = db.execute(
        "SELECT g.id FROM entities g WHERE g.type = 'release_group' AND ("
        "  SELECT COUNT(DISTINCT e.from_id) FROM edges e JOIN entities r ON r.id = e.from_id "
        "  WHERE e.to_id = g.id AND e.relation = ? AND r.owned = 1) >= 2 "
        "ORDER BY g.canonical_name COLLATE NOCASE, g.id",
        (REL_MEMBER_OF,),
    ).fetchall()
    found: list[DuplicateAlbum] = []
    for row in groups:
        group = repo.get_entity(db, row["id"])
        editions = tuple(_distinct(group_editions(db, row["id"], owned_only=True)))
        if group is None or len(editions) < 2:
            continue
        first = editions[0]
        differences = tuple(
            EditionDifference(e.release_id, first.release_id, compare_tracklists(first.tracks, e.tracks))
            for e in editions[1:]
        )
        found.append(DuplicateAlbum(
            group_entity_id=group["id"], group_mbid=group["mbid"], title=group["canonical_name"],
            editions=editions, differences=differences, reasons=_album_reasons(group, editions),
        ))
    return found


def find_duplicate_recordings(db: sqlite3.Connection) -> tuple[list[DuplicateRecording], int]:
    """Recordings on two or more owned releases, and how many more could not be compared."""
    rows = db.execute(
        "SELECT rec.id AS rid, rec.mbid AS mbid, rec.canonical_name AS name, "
        "       rel.id AS release_id, rel.canonical_name AS release_title, e.role AS role "
        "FROM edges e "
        "JOIN entities rec ON rec.id = e.from_id AND rec.type = 'recording' "
        "JOIN entities rel ON rel.id = e.to_id AND rel.type = 'release' AND rel.owned = 1 "
        "WHERE e.relation = ? ORDER BY rec.id, rel.id, e.role",
        (REL_APPEARS_ON,),
    ).fetchall()
    by_recording: dict[int, list[Any]] = {}
    for row in rows:
        by_recording.setdefault(row["rid"], []).append(row)

    groups_of: dict[int, int | None] = {}

    def group_of(release_id: int) -> int | None:
        if release_id not in groups_of:
            edge = next(iter(repo.edges_from(db, release_id, REL_MEMBER_OF)), None)
            groups_of[release_id] = edge["to_id"] if edge else None
        return groups_of[release_id]

    found: list[DuplicateRecording] = []
    skipped = 0
    for rid, appearances in by_recording.items():
        distinct = _first_per_release(appearances)
        if len(distinct) < 2:
            continue
        if not appearances[0]["mbid"]:
            skipped += 1
            continue
        entries = tuple(
            RecordingAppearance(a["release_id"], a["release_title"], a["role"], group_of(a["release_id"]))
            for a in distinct
        )
        group_ids = {a.group_entity_id for a in entries}
        same_album = len(group_ids) == 1 and None not in group_ids
        found.append(DuplicateRecording(
            recording_entity_id=rid, recording_mbid=appearances[0]["mbid"], title=appearances[0]["name"],
            appearances=entries, same_album=same_album,
            reasons=_recording_reasons(appearances[0]["mbid"], entries, same_album),
        ))
    found.sort(key=lambda r: (r.same_album, r.title.casefold(), r.recording_entity_id))
    return found, skipped


def find_duplicates(db: sqlite3.Connection, *, limit: int | None = None) -> DuplicateReport:
    """Both finders in one report; ``limit`` caps each list and sets ``truncated``."""
    albums = find_duplicate_albums(db)
    recordings, skipped = find_duplicate_recordings(db)
    report = DuplicateReport(skipped_recordings=skipped)
    if limit is not None and limit >= 0:
        report.truncated = len(albums) > limit or len(recordings) > limit
        albums, recordings = albums[:limit], recordings[:limit]
    report.albums, report.recordings = albums, recordings
    return report


def _distinct(editions: list[Edition]) -> list[Edition]:
    seen: set[int] = set()
    return [e for e in editions if not (e.release_id in seen or seen.add(e.release_id))]


def _first_per_release(rows: list[Any]) -> list[Any]:
    seen: set[int] = set()
    return [r for r in rows if not (r["release_id"] in seen or seen.add(r["release_id"]))]


def _album_reasons(group: dict[str, Any], editions: tuple[Edition, ...]) -> tuple[Reason, ...]:
    reasons = [Reason(
        "same_release_group",
        f"{len(editions)} owned releases are members of MusicBrainz release group {group['mbid']}",
    )]
    labelled = sorted({word for e in editions for word in e.labels})
    if labelled:
        reasons.append(Reason("edition_labels", "edition words in the titles: " + ", ".join(labelled)))
    if any(not e.tracks for e in editions):
        reasons.append(Reason("tracklist_unknown", "at least one edition has no stored tracklist to compare"))
    return tuple(reasons)


def _recording_reasons(mbid: str, entries: tuple[RecordingAppearance, ...], same_album: bool) -> tuple[Reason, ...]:
    reasons = [Reason("same_recording_mbid", f"recording {mbid} appears on {len(entries)} owned releases")]
    if same_album:
        reasons.append(Reason("edition_overlap", "all of those releases are editions of one album, so the overlap is expected"))
    else:
        reasons.append(Reason("different_albums", "those releases are not editions of one album"))
    return tuple(reasons)
