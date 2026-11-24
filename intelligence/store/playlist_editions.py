"""Persist complete Inbox editions and independent Navidrome feed links."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, replace
from datetime import timezone
from math import isfinite
from typing import TYPE_CHECKING, Any

from .repositories import payload_hash

if TYPE_CHECKING:
    from integrations.listenbrainz.jspf import ParsedPlaylist


@dataclass(frozen=True)
class PlaylistSnapshot:
    source_kind: str
    source_key: str
    edition_key: str
    metadata: dict[str, Any]
    tracks: tuple[dict[str, Any], ...]

    @classmethod
    def from_hosted(cls, playlist: ParsedPlaylist) -> PlaylistSnapshot:
        """Build a snapshot from a full JSPF detail response."""
        mbid = playlist.playlist_mbid
        if mbid is None:
            raise ValueError("Hosted playlist must have a ListenBrainz MBID")
        fields = asdict(playlist)
        tracks = fields.pop("tracks")
        for track in tracks:
            track["artist_mbids"] = list(track["artist_mbids"])
        fields["identifier"] = f"https://listenbrainz.org/playlist/{mbid}"
        for field in ("generated_at", "last_modified_at"):
            if fields[field] is not None:
                fields[field] = fields[field].astimezone(timezone.utc).isoformat()
        return cls("hosted", mbid, mbid, fields, tracks)


@dataclass(frozen=True)
class PlaylistEdition:
    id: int
    snapshot: PlaylistSnapshot
    fetched_at: float


@dataclass(frozen=True)
class ManagedCopy:
    feed_key: str
    playlist_id: str | None
    unlinked: bool = False


@dataclass(frozen=True)
class CopyIntent:
    target_key: str
    token: str
    edition_id: int


def publish_edition(
    db: sqlite3.Connection,
    snapshot: PlaylistSnapshot,
    *,
    expected_current_id: int | None,
    fetched_at: float,
) -> int | None:
    """Publish one complete edition; return its ID, or None if superseded.

    Read the expected current ID before fetching the source. An identical retry
    of the current edition succeeds even with an older expectation. A refresh
    that lost a race to a different edition must read the source again before
    trying to publish. Failed reads have no snapshot to pass here.

    For CF and local mixes, use a stable source key for the recurring recipe
    (scoped to the account for CF) and a source or scheduled edition key.
    """
    if not isfinite(fetched_at):
        raise ValueError("Playlist fetch time must be finite")
    for position, track in enumerate(snapshot.tracks):
        if type(track.get("position")) is not int or track["position"] != position:
            raise ValueError("Playlist tracks must be complete and ordered by position")
    payload = {"metadata": snapshot.metadata, "tracks": snapshot.tracks}
    encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    digest = payload_hash(payload)
    source = (snapshot.source_kind, snapshot.source_key)
    with db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute(
            "SELECT e.id, e.edition_key, e.content_hash "
            "FROM playlist_current_editions AS c JOIN playlist_editions AS e ON e.id = c.edition_id "
            "WHERE c.source_kind = ? AND c.source_key = ?",
            source,
        ).fetchone()
        current_id = current["id"] if current else None
        if current and (current["edition_key"], current["content_hash"]) == (snapshot.edition_key, digest):
            return current_id
        if current_id != expected_current_id:
            return None

        edition_id = db.execute(
            "INSERT INTO playlist_editions (source_kind, source_key, edition_key, content_hash, payload, fetched_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (*source, snapshot.edition_key, digest, encoded, fetched_at),
        ).lastrowid
        db.execute(
            "INSERT INTO playlist_current_editions (source_kind, source_key, edition_id) VALUES (?, ?, ?) "
            "ON CONFLICT (source_kind, source_key) DO UPDATE SET edition_id = excluded.edition_id",
            (*source, edition_id),
        )
        return edition_id


def current_edition_id(db: sqlite3.Connection, source_kind: str, source_key: str) -> int | None:
    row = db.execute(
        "SELECT edition_id FROM playlist_current_editions WHERE source_kind = ? AND source_key = ?",
        (source_kind, source_key),
    ).fetchone()
    return row["edition_id"] if row else None


def get_edition(db: sqlite3.Connection, edition_id: int) -> PlaylistEdition | None:
    row = db.execute("SELECT * FROM playlist_editions WHERE id = ?", (edition_id,)).fetchone()
    return _edition(row) if row else None


def list_current_editions(db: sqlite3.Connection) -> list[PlaylistEdition]:
    rows = db.execute(
        "SELECT e.* FROM playlist_current_editions AS c JOIN playlist_editions AS e ON e.id = c.edition_id "
        "ORDER BY e.fetched_at DESC, e.id DESC"
    )
    return [_edition(row) for row in rows]


def _edition(row: sqlite3.Row) -> PlaylistEdition:
    payload = json.loads(row["payload"])
    snapshot = PlaylistSnapshot(
        row["source_kind"], row["source_key"], row["edition_key"],
        payload["metadata"], tuple(payload["tracks"]),
    )
    return PlaylistEdition(row["id"], snapshot, row["fetched_at"])


def get_managed_copy(db: sqlite3.Connection, feed_key: str) -> ManagedCopy | None:
    row = db.execute("SELECT * FROM playlist_managed_copies WHERE feed_key = ?", (feed_key,)).fetchone()
    return ManagedCopy(row["feed_key"], row["playlist_id"], bool(row["unlinked"])) if row else None


def list_linked_feed_keys(db: sqlite3.Connection, target_key: str) -> tuple[str, ...]:
    """Find active managed copies for this Navidrome connection."""
    rows = db.execute(
        "SELECT c.feed_key FROM playlist_managed_copies AS c "
        "JOIN playlist_copy_intents AS i ON i.feed_key = c.feed_key "
        "WHERE c.unlinked = 0 AND i.target_key = ? ORDER BY c.feed_key",
        (target_key,),
    )
    return tuple(row["feed_key"] for row in rows)


def save_managed_copy(db: sqlite3.Connection, copy: ManagedCopy, *, expected: ManagedCopy | None) -> bool:
    """Change a feed's link only if it still matches the state the caller observed."""
    with db:
        db.execute("BEGIN IMMEDIATE")
        current = get_managed_copy(db, copy.feed_key)
        if current == copy:
            return True
        if current != expected:
            return False
        db.execute(
            "INSERT INTO playlist_managed_copies (feed_key, playlist_id, unlinked) VALUES (?, ?, ?) "
            "ON CONFLICT (feed_key) DO UPDATE SET playlist_id = excluded.playlist_id, unlinked = excluded.unlinked",
            (copy.feed_key, copy.playlist_id, copy.unlinked),
        )
        return True


def get_copy_intent(db: sqlite3.Connection, feed_key: str) -> CopyIntent | None:
    row = db.execute(
        "SELECT target_key, token, edition_id FROM playlist_copy_intents WHERE feed_key = ?", (feed_key,),
    ).fetchone()
    return CopyIntent(**dict(row)) if row else None


def record_copy_intent(db: sqlite3.Connection, feed_key: str, intent: CopyIntent) -> None:
    """Commit the unique remote creation marker before the first create request."""
    with db:
        db.execute(
            "INSERT INTO playlist_copy_intents (feed_key, target_key, token, edition_id) VALUES (?, ?, ?, ?)",
            (feed_key, intent.target_key, intent.token, intent.edition_id),
        )


def advance_copy_intent(db: sqlite3.Connection, feed_key: str, intent: CopyIntent, edition_id: int) -> CopyIntent:
    """Keep a delayed sync from rolling a feed back to a previously seen edition."""
    with db:
        db.execute("UPDATE playlist_copy_intents SET edition_id = ? WHERE feed_key = ?", (edition_id, feed_key))
    return replace(intent, edition_id=edition_id)
