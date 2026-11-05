"""The unresolved queue: ambiguous matches waiting for the owner (docs/ServerV2.md 6.5).

The ladder queues a library item here with its candidate list instead of guessing. The
owner can confirm one candidate or reject them all; either answer is final, so the
ladder never re-asks. Confirming is the only way ``user_confirmed`` is produced.
Every change bumps the ``unresolved`` data_version.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..store import generations
from .normalize import normalize_mbid

RESOURCE = "unresolved"


class UnresolvedError(ValueError):
    """The requested confirm or reject is not allowed."""


def queue_unresolved(
    db: sqlite3.Connection,
    kind: str,
    navidrome_ref: str,
    candidates: list[dict[str, Any]],
    reason: str,
    *,
    now: float,
) -> tuple[int, bool]:
    """Queue a library item; returns ``(id, changed)``.

    An open item is refreshed with the latest candidates and reason (``changed`` only if
    they differ). An item the owner already answered is left exactly as it is.
    """
    candidates_json = json.dumps(candidates, sort_keys=True, ensure_ascii=False)
    with db:
        row = db.execute(
            "SELECT * FROM unresolved WHERE kind = ? AND navidrome_ref = ?", (kind, navidrome_ref)
        ).fetchone()
        if row is None:
            cur = db.execute(
                "INSERT INTO unresolved (kind, navidrome_ref, candidates_json, reason, first_seen) "
                "VALUES (?, ?, ?, ?, ?)",
                (kind, navidrome_ref, candidates_json, reason, now),
            )
            generations.bump_data_version(db, RESOURCE)
            return cur.lastrowid, True
        if row["status"] != "open" or (row["candidates_json"], row["reason"]) == (candidates_json, reason):
            return row["id"], False
        db.execute(
            "UPDATE unresolved SET candidates_json = ?, reason = ? WHERE id = ?",
            (candidates_json, reason, row["id"]),
        )
        generations.bump_data_version(db, RESOURCE)
        return row["id"], True


def get_unresolved(db: sqlite3.Connection, unresolved_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM unresolved WHERE id = ?", (unresolved_id,)).fetchone()
    return _item(row) if row else None


def find_unresolved(db: sqlite3.Connection, kind: str, navidrome_ref: str) -> dict[str, Any] | None:
    row = db.execute(
        "SELECT * FROM unresolved WHERE kind = ? AND navidrome_ref = ?", (kind, navidrome_ref)
    ).fetchone()
    return _item(row) if row else None


def list_unresolved(
    db: sqlite3.Connection,
    *,
    status: str | None = "open",
    kind: str | None = None,
    limit: int = 100,
    after_id: int = 0,
) -> list[dict[str, Any]]:
    """Queue items oldest first, paged by ``after_id``; ``status=None`` lists every status."""
    sql, args = "SELECT * FROM unresolved WHERE id > ?", [after_id]
    if status is not None:
        sql += " AND status = ?"
        args.append(status)
    if kind is not None:
        sql += " AND kind = ?"
        args.append(kind)
    sql += " ORDER BY id LIMIT ?"
    args.append(max(int(limit), 0))
    return [_item(r) for r in db.execute(sql, args).fetchall()]


def count_unresolved(db: sqlite3.Connection, status: str = "open") -> int:
    return db.execute("SELECT COUNT(*) FROM unresolved WHERE status = ?", (status,)).fetchone()[0]


def confirm_candidate(db: sqlite3.Connection, unresolved_id: int, mbid: str) -> dict[str, Any]:
    """Owner picks one candidate. The id must be one the ladder offered, never free text.

    The chosen candidate is marked ``"confirmed": true`` in the stored list (the others
    stay as evidence), and the ladder resolves the item to it from then on.
    """
    wanted = normalize_mbid(mbid)
    with db:
        row = _open_row(db, unresolved_id)
        candidates = json.loads(row["candidates_json"])
        match = [c for c in candidates if normalize_mbid(c.get("mbid")) == wanted]
        if wanted is None or len(match) != 1:
            raise UnresolvedError(f"{mbid!r} is not one of the candidates offered for item {unresolved_id}")
        for c in candidates:
            c.pop("confirmed", None)
        match[0]["confirmed"] = True
        db.execute(
            "UPDATE unresolved SET status = 'user_confirmed', candidates_json = ? WHERE id = ?",
            (json.dumps(candidates, sort_keys=True, ensure_ascii=False), unresolved_id),
        )
        generations.bump_data_version(db, RESOURCE)
    return get_unresolved(db, unresolved_id)  # type: ignore[return-value]


def reject_all(db: sqlite3.Connection, unresolved_id: int) -> dict[str, Any]:
    """Owner says none of the candidates is right; the item stays unmatched and is not re-asked."""
    with db:
        _open_row(db, unresolved_id)
        db.execute("UPDATE unresolved SET status = 'user_rejected' WHERE id = ?", (unresolved_id,))
        generations.bump_data_version(db, RESOURCE)
    return get_unresolved(db, unresolved_id)  # type: ignore[return-value]


def reopen(db: sqlite3.Connection, unresolved_id: int) -> dict[str, Any]:
    """Undo an answer: the item goes back to ``open`` and any confirmation mark is removed."""
    with db:
        row = db.execute("SELECT * FROM unresolved WHERE id = ?", (unresolved_id,)).fetchone()
        if row is None:
            raise UnresolvedError(f"no unresolved item {unresolved_id}")
        candidates = json.loads(row["candidates_json"])
        for c in candidates:
            c.pop("confirmed", None)
        db.execute(
            "UPDATE unresolved SET status = 'open', candidates_json = ? WHERE id = ?",
            (json.dumps(candidates, sort_keys=True, ensure_ascii=False), unresolved_id),
        )
        if row["status"] != "open":
            generations.bump_data_version(db, RESOURCE)
    return get_unresolved(db, unresolved_id)  # type: ignore[return-value]


def confirmed_mbid(item: dict[str, Any]) -> str | None:
    """The MBID the owner confirmed for a ``user_confirmed`` item, else ``None``."""
    if item["status"] != "user_confirmed":
        return None
    for c in item["candidates"]:
        if c.get("confirmed"):
            return normalize_mbid(c.get("mbid"))
    return None


def _open_row(db: sqlite3.Connection, unresolved_id: int) -> sqlite3.Row:
    row = db.execute("SELECT * FROM unresolved WHERE id = ?", (unresolved_id,)).fetchone()
    if row is None:
        raise UnresolvedError(f"no unresolved item {unresolved_id}")
    if row["status"] != "open":
        raise UnresolvedError(f"item {unresolved_id} is already {row['status']}; reopen it first")
    return row


def _item(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["candidates"] = json.loads(data.pop("candidates_json"))
    return data
