"""Star Operation S2b: "More like this" and "Less like this" on an artist.

One ``discovery_feedback`` row per artist: scope ``artist_lean`` (its own scope, so it never
collides with the ``artist`` row "Not this artist" writes), ``album_key`` empty, status
``more_like_this`` or ``less_like_this``. No schema change. The two are mutually exclusive: the
newer one replaces the older, and clearing removes the row.

More boosts and seeds tag selection like a saved album (``recommendation_feedback``); Less is a soft
demotion. Neither hides anything, and neither touches owned albums or library pages. The
numbers live in ``recommendation_feedback.py`` as stated policy.
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable, Mapping
from typing import Any

from recommendation_feedback import LEAN_LESS, LEAN_MORE, LEAN_SCOPE

LEANS = {"more": LEAN_MORE, "less": LEAN_LESS}
MAX_NAME_LENGTH = 200
MAX_GENRES = 10
MAX_TEXT_LENGTH = 80


def clean_metadata(metadata: Any) -> dict[str, Any]:
    """Keep only ``genres`` (a few short strings) and ``lens`` (a short string); drop the rest."""
    if not isinstance(metadata, Mapping):
        return {}
    kept: dict[str, Any] = {}
    genres = metadata.get("genres")
    if isinstance(genres, (list, tuple)):
        names = [" ".join(g.split())[:MAX_TEXT_LENGTH] for g in genres if isinstance(g, str) and g.strip()]
        if names:
            kept["genres"] = names[:MAX_GENRES]
    lens = metadata.get("lens")
    if isinstance(lens, str) and lens.strip():
        kept["lens"] = lens.strip()[:MAX_TEXT_LENGTH]
    return kept


def set_lean(
    db_path: Any, artist: str, lean: str, music_key: Callable[[Any], str],
    metadata: Any = None,
) -> str:
    """Record ``lean`` ("more" or "less") for ``artist``, replacing any earlier one. Returns the name."""
    if lean not in LEANS:
        raise ValueError("lean must be more or less")
    name = " ".join(str(artist or "").split())[:MAX_NAME_LENGTH]
    key = music_key(name)
    if not key:
        raise ValueError("artist is required")
    now = time.time()
    with sqlite3.connect(db_path, timeout=10) as db:
        db.execute(
            "INSERT INTO discovery_feedback "
            "(scope, artist_key, album_key, artist, album, status, metadata_json, created_at, updated_at) "
            "VALUES (?, ?, '', ?, '', ?, ?, ?, ?) "
            "ON CONFLICT(scope, artist_key, album_key) DO UPDATE SET "
            "artist=excluded.artist, status=excluded.status, metadata_json=excluded.metadata_json, "
            "created_at=excluded.created_at, updated_at=excluded.updated_at",
            (LEAN_SCOPE, key, name, LEANS[lean], json.dumps(clean_metadata(metadata), ensure_ascii=False), now, now),
        )
        db.commit()
    return name


def clear_lean(db_path: Any, artist: str, music_key: Callable[[Any], str]) -> bool:
    """Remove the artist's lean. Returns True when one existed."""
    key = music_key(" ".join(str(artist or "").split())[:MAX_NAME_LENGTH])
    if not key:
        raise ValueError("artist is required")
    with sqlite3.connect(db_path, timeout=10) as db:
        removed = db.execute(
            "DELETE FROM discovery_feedback WHERE scope=? AND artist_key=? AND album_key=''",
            (LEAN_SCOPE, key),
        ).rowcount
        db.commit()
    return removed > 0


def list_leans(db_path: Any) -> list[dict[str, Any]]:
    """Every lean, newest first: ``[{"artist", "lean", "set_at"}]`` with lean ``more`` or ``less``."""
    names = {status: lean for lean, status in LEANS.items()}
    with sqlite3.connect(db_path, timeout=10) as db:
        rows = db.execute(
            "SELECT artist, status, updated_at FROM discovery_feedback WHERE scope=? "
            "ORDER BY updated_at DESC, artist",
            (LEAN_SCOPE,),
        ).fetchall()
    return [{"artist": r[0], "lean": names[r[1]], "set_at": r[2]} for r in rows if r[1] in names]
