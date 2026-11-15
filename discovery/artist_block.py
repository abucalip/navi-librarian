"""Star Operation S2c: list and lift "Not this artist".

"Not this artist" (``dismiss_artist``) already writes one ``discovery_feedback`` row: scope
``artist``, empty ``album_key``, status ``not_for_me_artist``. It hides the artist at read time
(``list_payload``) and applies a decaying score penalty (``recommendation_feedback``). This module
adds the two things the blocklist screen needs and nothing else: list those rows, and delete one.
Deleting the row lifts both the hide and the penalty. Album rows ("Not this album") are separate
and stay. No schema change.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from typing import Any

SCOPE = "artist"
STATUS = "not_for_me_artist"
MAX_NAME_LENGTH = 200


def list_blocked(db_path: Any) -> list[dict[str, Any]]:
    """Artists hidden by "Not this artist", newest first: ``[{"artist", "blocked_at"}]``."""
    with sqlite3.connect(db_path, timeout=10) as db:
        rows = db.execute(
            "SELECT artist, created_at FROM discovery_feedback "
            "WHERE scope=? AND status=? AND album_key='' ORDER BY created_at DESC, artist",
            (SCOPE, STATUS),
        ).fetchall()
    return [{"artist": row[0], "blocked_at": row[1]} for row in rows]


def unblock_artist(db_path: Any, artist: str, music_key: Callable[[Any], str]) -> bool:
    """Lift the artist's "Not this artist" row. Returns True when one existed."""
    key = music_key(" ".join(str(artist or "").split())[:MAX_NAME_LENGTH])
    if not key:
        raise ValueError("artist is required")
    with sqlite3.connect(db_path, timeout=10) as db:
        removed = db.execute(
            "DELETE FROM discovery_feedback WHERE scope=? AND artist_key=? AND album_key='' AND status=?",
            (SCOPE, key, STATUS),
        ).rowcount
        db.commit()
    return removed > 0
