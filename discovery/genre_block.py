"""Star Operation S2a: block a genre.

A blocked genre is one ``discovery_feedback`` row: scope ``genre``, ``artist_key`` the
normalized genre name, empty ``album_key``, status ``blocked_genre``. No schema change.
Unlike a dismissal it never decays; it stays until the owner unblocks it.

A block hides picks, never the library: it applies to the personal list, the lens lists,
classics and the other discovery lists, at selection time (so the list is built without
them) and at read time (so a stored list changes at once). Owned albums, the library pages
and "For me" are not touched. A block with no matching item changes nothing.

Selection-time coverage: Personal (``cooldown.prepare_ranking_inputs``), the lens lists, Classics and Deep Dives
(``drop_blocked_items`` after their genre enrichment). New releases candidates carry no genres at build, so
that list is not excluded at build time.
"""
from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any

SCOPE = "genre"
STATUS = "blocked_genre"
MAX_GENRE_LENGTH = 80


def clean_genre(genre: Any) -> str:
    """The display name of a genre, trimmed and bounded; empty when unusable."""
    return " ".join(str(genre or "").split())[:MAX_GENRE_LENGTH]


def blocked_genre_keys(
    feedback: Iterable[Mapping[str, Any]],
    music_key: Callable[[Any], str],
) -> frozenset[str]:
    """Normalized keys of every blocked genre in ``feedback`` (other rows are ignored)."""
    return frozenset(
        row["artist_key"] for row in feedback
        if isinstance(row, Mapping) and row.get("scope") == SCOPE
        and row.get("status") == STATUS and row.get("artist_key")
    )


def has_blocked_genre(
    genres: Iterable[Any] | None,
    blocked: frozenset[str],
    music_key: Callable[[Any], str],
) -> bool:
    """True when any of ``genres`` is a blocked genre."""
    if not blocked or not genres or isinstance(genres, str):
        return False
    return any(music_key(genre) in blocked for genre in genres)


def item_genres(item: Mapping[str, Any]) -> list[Any]:
    """The genre names a stored list item carries (``genres`` on lists, ``tags`` on lenses)."""
    found: list[Any] = []
    for field in ("genres", "tags"):
        value = item.get(field)
        if isinstance(value, (list, tuple)):
            found.extend(value)
    return found


def blocked_item_predicate(
    feedback: Iterable[Mapping[str, Any]],
    music_key: Callable[[Any], str],
) -> Callable[[Mapping[str, Any]], bool]:
    """A read-time check: True for a stored list item with a blocked genre."""
    blocked = blocked_genre_keys(feedback, music_key)
    return lambda item: has_blocked_genre(item_genres(item), blocked, music_key)


def drop_blocked_candidates(
    candidates: Iterable[Any],
    blocked: frozenset[str],
    music_key: Callable[[Any], str],
) -> list[Any]:
    """Selection-time exclusion: allocation candidates (``.tags``) without a blocked genre."""
    candidates = list(candidates)
    if not blocked:
        return candidates
    return [c for c in candidates if not has_blocked_genre(c.tags, blocked, music_key)]


def drop_blocked_items(
    items: Iterable[Any],
    blocked: frozenset[str],
    music_key: Callable[[Any], str],
) -> list[Any]:
    """Selection-time exclusion for list builders that hold dict candidates (``genres`` or ``tags``)."""
    items = list(items)
    if not blocked:
        return items
    return [i for i in items
            if not (isinstance(i, Mapping) and has_blocked_genre(item_genres(i), blocked, music_key))]


def current_blocked_keys(
    feedback_fn: Callable[[], Iterable[Mapping[str, Any]]],
    music_key: Callable[[Any], str],
) -> frozenset[str]:
    """Blocked genre keys now; empty when the feedback cannot be read (the read-time check still applies)."""
    try:
        return blocked_genre_keys(feedback_fn(), music_key)
    except Exception:
        return frozenset()


def list_blocked(db_path: Any) -> list[dict[str, Any]]:
    """Blocked genres, newest first: ``[{"genre", "blocked_at"}]``."""
    with sqlite3.connect(db_path, timeout=10) as db:
        rows = db.execute(
            "SELECT artist, created_at FROM discovery_feedback "
            "WHERE scope=? AND status=? ORDER BY created_at DESC, artist",
            (SCOPE, STATUS),
        ).fetchall()
    return [{"genre": row[0], "blocked_at": row[1]} for row in rows]


def block_genre(db_path: Any, genre: str, music_key: Callable[[Any], str]) -> str:
    """Block ``genre`` (idempotent). Returns the stored display name."""
    name = clean_genre(genre)
    key = music_key(name)
    if not key:
        raise ValueError("genre is required")
    now = time.time()
    with sqlite3.connect(db_path, timeout=10) as db:
        db.execute(
            "INSERT INTO discovery_feedback "
            "(scope, artist_key, album_key, artist, album, status, metadata_json, created_at, updated_at) "
            "VALUES (?, ?, '', ?, '', ?, '{}', ?, ?) "
            "ON CONFLICT(scope, artist_key, album_key) DO UPDATE SET "
            "status=excluded.status, updated_at=excluded.updated_at",
            (SCOPE, key, name, STATUS, now, now),
        )
        db.commit()
    return name


def unblock_genre(db_path: Any, genre: str, music_key: Callable[[Any], str]) -> bool:
    """Remove a block. Returns True when one existed."""
    key = music_key(clean_genre(genre))
    if not key:
        raise ValueError("genre is required")
    with sqlite3.connect(db_path, timeout=10) as db:
        removed = db.execute(
            "DELETE FROM discovery_feedback WHERE scope=? AND artist_key=? AND album_key=''",
            (SCOPE, key),
        ).rowcount
        db.commit()
    return removed > 0
