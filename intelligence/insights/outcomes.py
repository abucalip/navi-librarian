"""Record accepted cards for every insight kind, and gather outcomes for the lens scorecard.

An accept is stored as its own ``insights`` row with ``dismissed_state = 'accepted'`` (no
migration), next to any live card. It never edits or removes the live card, so refreshes and the
existing dismissal logic are unchanged: live listings only read rows with a NULL state, and the
finders' ``dismissed_*_keys`` helpers only read ``'dismissed'`` rows. Rules:

* one accepted row per (kind, key); accepting twice returns False;
* a key already dismissed cannot be accepted (False); dismissing after an accept is allowed and
  wins in the scorecard, because :func:`score_lens` counts dismissed before accepted;
* unknown kinds raise ``ValueError``.

Nothing here fetches data or touches ownership flags or recommendation weights.
"""
from __future__ import annotations

import json
import sqlite3
import time
from typing import Any

from ..store import generations
from .anniversaries import CARD_KIND as ANNIVERSARY_KIND
from .blind_spots import CARD_KIND as BLIND_SPOT_KIND
from .forgotten_gems import CARD_KIND as GEM_KIND
from .hidden_canon import CARD_KIND as CANON_KIND
from .series_completion import CARD_KIND as SERIES_KIND

ACCEPTED = "accepted"
DISMISSED = "dismissed"
RESOURCE = "insights"
KINDS = (GEM_KIND, BLIND_SPOT_KIND, SERIES_KIND, CANON_KIND, ANNIVERSARY_KIND)
_KEY = "json_extract(payload, '$.subject.key')"


def _check(kind: str) -> None:
    if kind not in KINDS:
        raise ValueError(f"unknown insight kind: {kind!r}")


def _keys(db: sqlite3.Connection, kind: str, state: str) -> set[str]:
    _check(kind)
    rows = db.execute(
        f"SELECT {_KEY} AS key FROM insights WHERE kind = ? AND dismissed_state = ?", (kind, state)
    ).fetchall()
    return {r["key"] for r in rows if r["key"]}


def accepted_keys(db: sqlite3.Connection, kind: str) -> set[str]:
    """Subject keys the owner accepted for ``kind`` (the ``accepted`` input of :func:`score_lens`)."""
    return _keys(db, kind, ACCEPTED)


def accept_card(db: sqlite3.Connection, kind: str, key: str, now: float | None = None) -> bool:
    """Record that the owner accepted the card with subject ``key``. False if already accepted or dismissed."""
    _check(kind)
    if not key or key in _keys(db, kind, ACCEPTED) or key in _keys(db, kind, DISMISSED):
        return False
    now = time.time() if now is None else now
    with db:
        db.execute(
            "INSERT INTO insights (kind, subject_id, payload, reasons_json, generation, computed_at, dismissed_state) "
            "VALUES (?, NULL, ?, '[]', ?, ?, ?)",
            (kind, json.dumps({"subject": {"key": key}}), generations.current_generation(db), now, ACCEPTED),
        )
    generations.bump_data_version(db, RESOURCE)
    return True


def unaccept_card(db: sqlite3.Connection, kind: str, key: str) -> bool:
    """Undo an accept. False if the key was not accepted."""
    _check(kind)
    with db:
        cur = db.execute(
            f"DELETE FROM insights WHERE kind = ? AND dismissed_state = ? AND {_KEY} = ?", (kind, ACCEPTED, key)
        )
    if cur.rowcount:
        generations.bump_data_version(db, RESOURCE)
    return bool(cur.rowcount)


def lens_outcomes(db: sqlite3.Connection, kind: str) -> dict[str, Any]:
    """Judged cards plus accepted and dismissed keys for ``kind``, ready for ``score_lens``.

    ``cards`` is the live cards followed by the dismissed ones (once per key, the live listing never
    holds a dismissed key). A dismissed card is no longer live, but the owner judged it, so
    ``score_lens`` must still see it or dismissals would never lower precision.
    """
    _check(kind)
    live = [json.loads(r["payload"]) for r in db.execute(
        "SELECT payload FROM insights WHERE kind = ? AND dismissed_state IS NULL "
        "ORDER BY json_extract(payload, '$.score') DESC, id", (kind,)
    ).fetchall()]
    seen = {c.get("subject", {}).get("key") for c in live}
    dismissed_cards = []
    for r in db.execute(
        "SELECT payload FROM insights WHERE kind = ? AND dismissed_state = ? ORDER BY id", (kind, DISMISSED)
    ).fetchall():
        card = json.loads(r["payload"])
        key = (card.get("subject") or {}).get("key")
        if key and key not in seen:
            seen.add(key)
            dismissed_cards.append(card)
    return {
        "cards": live + dismissed_cards,
        "accepted": sorted(_keys(db, kind, ACCEPTED)),
        "dismissed": sorted(_keys(db, kind, DISMISSED)),
    }
