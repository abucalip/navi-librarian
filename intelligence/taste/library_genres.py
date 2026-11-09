"""Song genres by recording MBID, read from the saved Navidrome observations (read-only).

The taste loader needs ``genres_by_recording`` for the genre dimension; the knowledge store keeps no
genre. Library ingest already records every owned track's MBID and genres in the ``navidrome``
observations, so the map comes from there. Observations are never edited, so rows are read oldest
first and a newer document for the same track replaces an older one. A listen of a track the library
does not own simply has no genre.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Mapping

SOURCE = "navidrome"


def genres_by_recording(db: sqlite3.Connection) -> Mapping[str, tuple[str, ...]]:
    out: dict[str, tuple[str, ...]] = {}
    for row in db.execute("SELECT payload FROM observations WHERE source = ? ORDER BY fetched_at, id", (SOURCE,)):
        try:
            tracks = json.loads(row["payload"]).get("tracks") or []
        except (TypeError, ValueError, AttributeError):
            continue
        for track in tracks:
            if not isinstance(track, dict):
                continue
            mbid = str(track.get("mbid") or "").strip().lower()
            genres = tuple(dict.fromkeys(str(g) for g in track.get("genres") or () if g))
            if mbid and genres:
                out[mbid] = genres
    return out
