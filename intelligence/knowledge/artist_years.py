"""An artist's stored life span by MusicBrainz ID, for the artist page's active years (Index theme I0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..store import open_readonly
from ..store import repositories as repo
from .pages import _life_span


def read_life_span(store_path: Path, mbid: str) -> dict[str, Any] | None:
    """The stored ``begin``, ``end`` and ``ended`` for the artist with this MBID; None when unknown or unreadable."""
    try:
        db = open_readonly(store_path)
        try:
            entity = repo.find_entity(db, "artist", mbid=mbid.lower())
            return _life_span(db, entity["id"]) if entity else None
        finally:
            db.close()
    except Exception:
        return None
