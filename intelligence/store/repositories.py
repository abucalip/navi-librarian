"""Typed access to observations, entities, aliases and edges.

Every function takes an open connection from :func:`intelligence.store.open_store` and
commits its own write. Nothing here touches the network or decides what a match means;
the resolution ladder builds on these calls.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from .generations import current_generation
from .migrations import ENTITY_TYPES, EVIDENCE_CLASSES, MATCH_QUALITIES

# Identifier columns an entity can be looked up and de-duplicated by.
_ID_COLUMNS = ("mbid", "navidrome_id", "discogs_id", "wikidata_id")


# ---------------------------------------------------------------- observations

def payload_hash(payload: Any) -> str:
    """Stable SHA-256 of a JSON-serialisable payload (key order does not matter)."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def add_observation(
    db: sqlite3.Connection,
    source: str,
    payload: Any,
    *,
    fetched_at: float,
    entity_hint: str | None = None,
    expires_at: float | None = None,
) -> tuple[int, bool]:
    """Store a fetched document; returns ``(id, created)``.

    A document with the same source and content is not stored twice: the existing id
    comes back with ``created`` False. Stored rows are never edited.
    """
    digest = payload_hash(payload)
    with db:
        row = db.execute(
            "SELECT id FROM observations WHERE source = ? AND payload_hash = ?", (source, digest)
        ).fetchone()
        if row:
            return row["id"], False
        cur = db.execute(
            "INSERT INTO observations "
            "(source, entity_hint, payload_hash, payload, fetched_at, expires_at, generation) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                source, entity_hint, digest,
                json.dumps(payload, sort_keys=True, ensure_ascii=False),
                fetched_at, expires_at, current_generation(db),
            ),
        )
        return cur.lastrowid, True


def get_observation(db: sqlite3.Connection, observation_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM observations WHERE id = ?", (observation_id,)).fetchone()
    return _observation(row) if row else None


def latest_observation(db: sqlite3.Connection, source: str, entity_hint: str) -> dict[str, Any] | None:
    """Most recently fetched document for a source and hint."""
    row = db.execute(
        "SELECT * FROM observations WHERE source = ? AND entity_hint = ? "
        "ORDER BY fetched_at DESC, id DESC LIMIT 1",
        (source, entity_hint),
    ).fetchone()
    return _observation(row) if row else None


def expired_observations(db: sqlite3.Connection, now: float, limit: int = 100) -> list[dict[str, Any]]:
    """Documents whose cache lifetime has passed, oldest first, for a bounded refresh job."""
    rows = db.execute(
        "SELECT * FROM observations WHERE expires_at IS NOT NULL AND expires_at <= ? "
        "ORDER BY expires_at, id LIMIT ?",
        (now, max(int(limit), 0)),
    ).fetchall()
    return [_observation(r) for r in rows]


def _observation(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["payload"] = json.loads(data["payload"])
    return data


# -------------------------------------------------------------------- entities

def upsert_entity(
    db: sqlite3.Connection,
    type: str,
    canonical_name: str,
    *,
    sort_name: str | None = None,
    owned: bool | None = None,
    **ids: str | None,
) -> tuple[int, bool]:
    """Create an entity or update the one these identifiers already name; ``(id, created)``.

    An existing entity is found by the first identifier among ``mbid``, ``navidrome_id``,
    ``discogs_id`` and ``wikidata_id`` that matches one of the same type. Identifiers
    already set are never overwritten with a different value (that is a conflict to
    surface, not to resolve silently), and ``owned`` is only changed when passed.
    """
    if type not in ENTITY_TYPES:
        raise ValueError(f"unknown entity type: {type!r}")
    unknown = set(ids) - set(_ID_COLUMNS)
    if unknown:
        raise ValueError(f"unknown identifier columns: {sorted(unknown)}")
    given = {k: v for k, v in ids.items() if v}
    with db:
        existing = _find_by_ids(db, type, given)
        if existing is None:
            cols = {
                "type": type, "canonical_name": canonical_name, "sort_name": sort_name,
                "owned": int(bool(owned)), "created_generation": current_generation(db), **given,
            }
            cur = db.execute(
                f"INSERT INTO entities ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                tuple(cols.values()),
            )
            return cur.lastrowid, True
        updates: dict[str, Any] = {k: v for k, v in given.items() if existing[k] is None}
        if sort_name is not None and existing["sort_name"] is None:
            updates["sort_name"] = sort_name
        if owned is not None and int(bool(owned)) != existing["owned"]:
            updates["owned"] = int(bool(owned))
        if updates:
            db.execute(
                f"UPDATE entities SET {', '.join(f'{k} = ?' for k in updates)} WHERE id = ?",
                (*updates.values(), existing["id"]),
            )
        return existing["id"], False


def _find_by_ids(db: sqlite3.Connection, type: str, ids: dict[str, str]) -> sqlite3.Row | None:
    for column in _ID_COLUMNS:
        if column in ids:
            row = db.execute(
                f"SELECT * FROM entities WHERE type = ? AND {column} = ?", (type, ids[column])
            ).fetchone()
            if row:
                return row
    return None


def get_entity(db: sqlite3.Connection, entity_id: int) -> dict[str, Any] | None:
    row = db.execute("SELECT * FROM entities WHERE id = ?", (entity_id,)).fetchone()
    return dict(row) if row else None


def find_entity(db: sqlite3.Connection, type: str, **ids: str) -> dict[str, Any] | None:
    """Look up one entity by identifier, e.g. ``find_entity(db, "artist", mbid="...")``."""
    unknown = set(ids) - set(_ID_COLUMNS)
    if unknown:
        raise ValueError(f"unknown identifier columns: {sorted(unknown)}")
    row = _find_by_ids(db, type, {k: v for k, v in ids.items() if v})
    return dict(row) if row else None


def find_entities_by_name(db: sqlite3.Connection, type: str, name: str) -> list[dict[str, Any]]:
    """Entities of a type whose canonical name or alias equals ``name`` exactly (case-sensitive)."""
    rows = db.execute(
        "SELECT DISTINCT e.* FROM entities e LEFT JOIN entity_aliases a ON a.entity_id = e.id "
        "WHERE e.type = ? AND (e.canonical_name = ? OR a.alias = ?) ORDER BY e.id",
        (type, name, name),
    ).fetchall()
    return [dict(r) for r in rows]


def add_alias(db: sqlite3.Connection, entity_id: int, alias: str, kind: str = "alias") -> bool:
    """Attach an alternative name; returns False if it was already there."""
    with db:
        cur = db.execute(
            "INSERT OR IGNORE INTO entity_aliases (entity_id, alias, kind) VALUES (?, ?, ?)",
            (entity_id, alias, kind),
        )
        return cur.rowcount == 1


def aliases(db: sqlite3.Connection, entity_id: int) -> list[tuple[str, str]]:
    """``(alias, kind)`` pairs for an entity, sorted."""
    rows = db.execute(
        "SELECT alias, kind FROM entity_aliases WHERE entity_id = ? ORDER BY alias, kind", (entity_id,)
    ).fetchall()
    return [(r["alias"], r["kind"]) for r in rows]


# ----------------------------------------------------------------------- edges

def add_edge(
    db: sqlite3.Connection,
    from_id: int,
    to_id: int,
    relation: str,
    *,
    evidence_class: str,
    match_quality: str,
    source: str,
    role: str | None = None,
    source_url: str | None = None,
    observation_id: int | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    generation: int | None = None,
) -> tuple[int, bool]:
    """Record a relationship; returns ``(id, created)``.

    Repeating the same edge (same endpoints, relation, role, source and generation) is
    a no-op that returns the existing id, so jobs can re-run safely.
    """
    if evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"unknown evidence class: {evidence_class!r}")
    if match_quality not in MATCH_QUALITIES:
        raise ValueError(f"unknown match quality: {match_quality!r}")
    with db:
        gen = generation if generation is not None else current_generation(db)
        row = db.execute(
            "SELECT id FROM edges WHERE from_id = ? AND to_id = ? AND relation = ? "
            "AND COALESCE(role, '') = COALESCE(?, '') AND source = ? AND generation = ?",
            (from_id, to_id, relation, role, source, gen),
        ).fetchone()
        if row:
            return row["id"], False
        cur = db.execute(
            "INSERT INTO edges (from_id, to_id, relation, role, evidence_class, match_quality, source, "
            "source_url, observation_id, valid_from, valid_to, generation) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (from_id, to_id, relation, role, evidence_class, match_quality, source,
             source_url, observation_id, valid_from, valid_to, gen),
        )
        return cur.lastrowid, True


def edges_from(
    db: sqlite3.Connection, entity_id: int, relation: str | None = None, generation: int | None = None
) -> list[dict[str, Any]]:
    return _edges(db, "from_id", entity_id, relation, generation)


def edges_to(
    db: sqlite3.Connection, entity_id: int, relation: str | None = None, generation: int | None = None
) -> list[dict[str, Any]]:
    return _edges(db, "to_id", entity_id, relation, generation)


def _edges(
    db: sqlite3.Connection, column: str, entity_id: int, relation: str | None, generation: int | None
) -> list[dict[str, Any]]:
    sql, args = f"SELECT * FROM edges WHERE {column} = ?", [entity_id]
    if relation is not None:
        sql += " AND relation = ?"
        args.append(relation)
    if generation is not None:
        sql += " AND generation = ?"
        args.append(generation)
    return [dict(r) for r in db.execute(sql + " ORDER BY id", args).fetchall()]


def delete_edges_before_generation(db: sqlite3.Connection, generation: int) -> int:
    """Drop edges derived under older generations once a rebuild has replaced them.

    Observations are untouched, so a rebuild never refetches, and edges the owner
    confirmed (``user_confirmed``) are kept. Returns the number of rows removed.
    """
    with db:
        return db.execute(
            "DELETE FROM edges WHERE generation < ? AND evidence_class != 'user_confirmed'", (generation,)
        ).rowcount
