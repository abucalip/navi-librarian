"""Edition grouping and tracklist differences (docs/ServerV2.md Phase 2, item 2).

Every release in one release group is an *edition* of the same album. This module reads
what the store already holds (``member_of`` edges from slice 1, the stored MusicBrainz
release documents, and ``appears_on`` edges from the Navidrome ingest) and reports:

- which edition each owned release is: the original issue, a later edition, or unknown;
- edition labels read from the title, disambiguation and secondary types (deluxe,
  remaster, live, ...), as display words and never as identity;
- how two editions' tracklists differ.

It is read-only and makes no network calls. It never merges releases or suggests
deleting one; the duplicate finder (item 3) builds on this. Anything it cannot tell
stays ``unknown`` rather than guessed.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Any

from ..resolution.normalize import edition_markers, normalize_text, title_key
from ..store import repositories as repo
from .release_groups import REL_MEMBER_OF, SOURCE, ReleaseInfo, parse_release

REL_APPEARS_ON = "appears_on"  # recording -> release; role is "disc/track"

ORIGINAL = "original_issue"
LATER = "later_edition"
UNKNOWN = "unknown"

_LABEL_WORDS = (
    "super deluxe", "deluxe", "expanded", "remastered", "remaster", "anniversary", "reissue",
    "bonus", "special edition", "collector's edition", "collectors edition", "limited edition",
    "legacy edition", "mono", "stereo", "live",
)
_LABEL_NAMES = {"remastered": "remaster", "collectors edition": "collector's edition"}
_DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


@dataclass(frozen=True)
class TrackEntry:
    position: str | None  # "disc/track" when known
    title: str
    recording_id: int
    recording_mbid: str | None = None


@dataclass(frozen=True)
class Edition:
    release_id: int
    mbid: str | None
    title: str
    owned: bool
    info: ReleaseInfo | None
    labels: tuple[str, ...]
    relation: str  # ORIGINAL, LATER or UNKNOWN
    tracks: tuple[TrackEntry, ...] = ()


@dataclass(frozen=True)
class TracklistDiff:
    shared: int
    only_in_a: tuple[str, ...] = ()
    only_in_b: tuple[str, ...] = ()
    order_changed: bool = False
    ambiguous: tuple[str, ...] = field(default=())  # titles repeated inside one tracklist

    @property
    def same(self) -> bool:
        return not (self.only_in_a or self.only_in_b or self.order_changed or self.ambiguous)


def edition_labels(info: ReleaseInfo | None, title: str | None = None) -> tuple[str, ...]:
    """Edition words found in the release title, disambiguation and group secondary types."""
    found: list[str] = []

    def add(word: str) -> None:
        word = _LABEL_NAMES.get(word, word)
        if word not in found:
            found.append(word)

    for word in edition_markers(title or (info.title if info else None)):
        add(word)
    if info is not None:
        text = normalize_text(info.disambiguation)
        padded = f" {text} "
        for word in _LABEL_WORDS:
            if f" {normalize_text(word)} " in padded:
                add(word)
        for secondary in info.secondary_types:
            if secondary.casefold() == "live":
                add("live")
    return tuple(found)


def release_relation(info: ReleaseInfo | None) -> str:
    """Compare a release date with the group's first release date, at the coarser precision.

    A release dated the same as the group's first release is the original issue; one dated
    later is a later edition. A missing or unreadable date on either side is ``unknown``.
    """
    if info is None:
        return UNKNOWN
    first, date = _date(info.first_release_date), _date(info.date)
    if first is None or date is None:
        return UNKNOWN
    size = min(len(first), len(date))
    first, date = first[:size], date[:size]
    if date == first:
        return ORIGINAL
    return LATER if date > first else UNKNOWN  # earlier than the "first" release is inconsistent data


def group_editions(db: sqlite3.Connection, group_entity_id: int, *, owned_only: bool = True) -> list[Edition]:
    """Editions of one release group, owned first by release date; empty when it has no members."""
    group = repo.get_entity(db, group_entity_id)
    if group is None or group["type"] != "release_group":
        raise ValueError(f"not a release group entity: {group_entity_id!r}")
    editions: list[Edition] = []
    for edge in repo.edges_to(db, group_entity_id, REL_MEMBER_OF):
        release = repo.get_entity(db, edge["from_id"])
        if release is None or (owned_only and not release["owned"]):
            continue
        info = _stored_info(db, release["mbid"])
        title = (info.title if info and info.title else None) or release["canonical_name"]
        editions.append(Edition(
            release_id=release["id"], mbid=release["mbid"], title=title, owned=bool(release["owned"]),
            info=info, labels=edition_labels(info, title), relation=release_relation(info),
            tracks=tracklist(db, release["id"]),
        ))
    return sorted(editions, key=lambda e: (e.info.date if e.info and e.info.date else "~", e.release_id))


def tracklist(db: sqlite3.Connection, release_entity_id: int) -> tuple[TrackEntry, ...]:
    """Recordings on a release in disc/track order; tracks without a position sort last."""
    entries = []
    for edge in repo.edges_to(db, release_entity_id, REL_APPEARS_ON):
        recording = repo.get_entity(db, edge["from_id"])
        if recording is not None:
            entries.append(TrackEntry(edge["role"], recording["canonical_name"], recording["id"], recording["mbid"]))
    return tuple(sorted(entries, key=lambda t: (_position_key(t.position), t.recording_id)))


def compare_tracklists(a: tuple[TrackEntry, ...] | list[TrackEntry], b: tuple[TrackEntry, ...] | list[TrackEntry]) -> TracklistDiff:
    """How two tracklists differ.

    Tracks pair by recording MBID first, then by normalized title. A title or MBID that
    repeats inside one tracklist cannot be paired safely, so those tracks are reported as
    ``ambiguous`` and left out of the other counts.
    """
    ambiguous = {t.title for t in (*_repeats(a), *_repeats(b))}
    left = [t for t in a if t.title not in ambiguous]
    right = [t for t in b if t.title not in ambiguous]
    pairs: list[tuple[TrackEntry, TrackEntry]] = []
    for same in (lambda x, y: bool(x.recording_mbid) and x.recording_mbid == y.recording_mbid,
                 lambda x, y: title_key(x.title) == title_key(y.title)):
        for x in list(left):
            y = next((c for c in right if same(x, c)), None)
            if y is not None:
                pairs.append((x, y))
                left.remove(x)
                right.remove(y)
    order_a = [id(x) for x, _ in sorted(pairs, key=lambda p: a.index(p[0]))]
    order_b = [id(x) for x, _ in sorted(pairs, key=lambda p: b.index(p[1]))]
    return TracklistDiff(
        shared=len(pairs), only_in_a=tuple(t.title for t in left), only_in_b=tuple(t.title for t in right),
        order_changed=order_a != order_b, ambiguous=tuple(sorted(ambiguous)),
    )


def _repeats(tracks: Any) -> list[TrackEntry]:
    titles = [title_key(t.title) for t in tracks]
    mbids = [t.recording_mbid for t in tracks if t.recording_mbid]
    return [t for t, k in zip(tracks, titles)
            if titles.count(k) > 1 or (t.recording_mbid and mbids.count(t.recording_mbid) > 1)]


def _stored_info(db: sqlite3.Connection, mbid: str | None) -> ReleaseInfo | None:
    if not mbid:
        return None
    observation = repo.latest_observation(db, SOURCE, f"release:{mbid}")
    payload: Any = observation["payload"] if observation else None
    return parse_release(payload, mbid) if isinstance(payload, dict) else None


def _date(value: str | None) -> str | None:
    match = _DATE_RE.match(value or "")
    if not match:
        return None
    return "-".join(part for part in match.groups() if part)


def _position_key(position: str | None) -> tuple[int, int, int]:
    try:
        disc, number = (int(x) for x in (position or "").split("/"))
    except ValueError:
        return (1, 0, 0)
    return (0, disc, number)
