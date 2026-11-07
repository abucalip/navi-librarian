"""Persist sitewide artist popularity in the owner-state file (Phase 6 item 2, slice 17).

Figures live in ``state.artist_popularity`` (migration 4, see :mod:`intelligence.store.state`): one row per
artist MBID with the ListenBrainz total listen count, or ``NULL`` when the provider had no figure. The
``NULL`` row is kept on purpose so an artist the provider does not know is not asked again at once.

Nothing here calls a provider or Navidrome; the caller supplies ``now``. A write is one transaction,
so a failed run never leaves half a batch. Rows are never deleted by this module: the last good figure
stays until a newer one replaces it.

Refresh rule: an MBID is *pending* when it has no row, or its row is older than ``FOUND_TTL`` (a figure)
or ``ABSENT_TTL`` (no figure). Missing artists come first, then the oldest rows.
"""
from __future__ import annotations

import sqlite3
from typing import Iterable, Mapping

FOUND_TTL = 30 * 86400.0
ABSENT_TTL = 7 * 86400.0


def save_popularity(db: sqlite3.Connection, figures: Mapping[str, int | None], now: float) -> int:
    """Upsert figures (``None`` = provider has none). Malformed MBIDs or counts are skipped. Returns rows written."""
    rows = []
    for mbid, count in figures.items():
        if not isinstance(mbid, str) or len(mbid) != 36 or mbid != mbid.lower():
            continue
        if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 0):
            continue
        rows.append((mbid, count, now))
    if not rows:
        return 0
    with db:
        db.executemany(
            "INSERT INTO state.artist_popularity (artist_mbid, listen_count, fetched_at) VALUES (?, ?, ?) "
            "ON CONFLICT(artist_mbid) DO UPDATE SET listen_count = excluded.listen_count, "
            "fetched_at = excluded.fetched_at", rows)
    return len(rows)


def load_popularity(db: sqlite3.Connection) -> dict[str, int | None]:
    """Every saved figure, ``None`` where the provider had none."""
    return {r[0]: r[1] for r in db.execute("SELECT artist_mbid, listen_count FROM state.artist_popularity")}


def pending_mbids(db: sqlite3.Connection, mbids: Iterable[str], now: float) -> list[str]:
    """MBIDs with no figure row or a stale one: unseen first (input order), then oldest first."""
    saved = {r[0]: (r[1], r[2]) for r in db.execute(
        "SELECT artist_mbid, listen_count, fetched_at FROM state.artist_popularity")}
    unseen: list[str] = []
    stale: list[tuple[float, str]] = []
    for mbid in dict.fromkeys(m for m in mbids if m):
        row = saved.get(mbid)
        if row is None:
            unseen.append(mbid)
            continue
        count, fetched = row
        if now - fetched >= (ABSENT_TTL if count is None else FOUND_TTL):
            stale.append((fetched, mbid))
    return unseen + [m for _, m in sorted(stale)]


def owned_artist_mbids(db: sqlite3.Connection) -> list[str]:
    """MBIDs of owned artists in the knowledge store, in a stable order."""
    return [r[0] for r in db.execute(
        "SELECT mbid FROM entities WHERE type = 'artist' AND owned = 1 AND mbid IS NOT NULL ORDER BY mbid")]


def artist_mbids_by_navidrome_id(db: sqlite3.Connection) -> dict[str, str]:
    """Navidrome artist id -> artist MBID, for owned artists the store knows by both."""
    return {r[0]: r[1] for r in db.execute(
        "SELECT navidrome_id, mbid FROM entities WHERE type = 'artist' AND owned = 1 "
        "AND navidrome_id IS NOT NULL AND mbid IS NOT NULL")}
