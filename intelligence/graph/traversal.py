"""Bounded breadth-first exploration of the edge table.

Every call is capped by depth, row count and elapsed time, so a hub entity (a large
label, a session player) cannot turn a page request into an unbounded walk. Each
reachable entity appears once, at its shortest depth, however many cycles or parallel
edges lead to it; the facts behind it (relation, role, source, evidence class, match
quality) are kept on the hop, never merged away. Results are ordered deterministically
and resumed with an opaque cursor, so a client can page through them.

Nothing here writes to the store or calls a provider (docs/ServerV2.md, Phase 4 item 6).
"""
from __future__ import annotations

import base64
import binascii
import sqlite3
import time
from dataclasses import dataclass
from typing import Callable, Iterable

from intelligence.store.generations import current_generation

DIRECTIONS = ("out", "in", "both")
# Match qualities that leave the other end of an edge uncertain.
_UNCERTAIN_MATCHES = ("fuzzy_unconfirmed", "unresolved")


@dataclass(frozen=True)
class Limits:
    max_depth: int = 2
    max_rows: int = 200
    max_seconds: float = 2.0
    page_size: int = 50

    def __post_init__(self):
        if self.max_depth < 1 or self.max_rows < 1 or self.page_size < 1 or self.max_seconds <= 0:
            raise ValueError("limits must be positive")


@dataclass(frozen=True)
class Evidence:
    edge_id: int
    relation: str
    role: str | None
    direction: str  # "out": the edge leaves the parent entity; "in": it arrives at it
    evidence_class: str
    match_quality: str
    source: str
    source_url: str | None
    valid_from: str | None
    valid_to: str | None


@dataclass(frozen=True)
class Hop:
    entity_id: int
    depth: int
    via_entity_id: int  # the entity one step closer to the start
    evidence: tuple[Evidence, ...]  # every edge between via_entity_id and entity_id

    @property
    def credit(self) -> bool:
        """True only if some edge here may be shown as a credit (see :func:`is_credit`)."""
        return any(is_credit(e) for e in self.evidence)


@dataclass(frozen=True)
class Page:
    hops: tuple[Hop, ...]
    next_cursor: str | None
    # Why the walk stopped early: "rows", "time", or None when it ran out of graph or depth.
    truncated: str | None


def is_credit(evidence: Evidence) -> bool:
    """An inferred edge, or one whose other end is not firmly matched, is never a credit."""
    return evidence.evidence_class != "inferred" and evidence.match_quality not in _UNCERTAIN_MATCHES


def explore(
    db: sqlite3.Connection,
    start_id: int,
    *,
    relations: Iterable[str] | None = None,
    direction: str = "both",
    credits_only: bool = False,
    generation: int | None = None,
    limits: Limits = Limits(),
    cursor: str | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> Page:
    """Entities within ``limits.max_depth`` steps of ``start_id``, nearest first.

    ``credits_only`` drops every edge that :func:`is_credit` refuses, before the walk,
    so an uncertain edge cannot even act as a bridge to a credited neighbour.
    Edges are read for ``generation`` (default: the current one).
    """
    if direction not in DIRECTIONS:
        raise ValueError(f"direction must be one of {DIRECTIONS}")
    after = _decode_cursor(cursor)
    gen = generation if generation is not None else current_generation(db)
    wanted = frozenset(relations) if relations is not None else None
    deadline = clock() + limits.max_seconds

    seen = {start_id}
    frontier = [start_id]
    ordered: list[Hop] = []
    truncated: str | None = None

    for depth in range(1, limits.max_depth + 1):
        found: dict[int, tuple[int, list[Evidence]]] = {}
        for parent in frontier:
            if clock() > deadline:
                truncated = "time"
                break
            for neighbour, ev in _edges_at(db, parent, direction, wanted, gen, credits_only):
                # Evidence stays with the first parent to reach an entity, so a hop's
                # edges all lie between the same two entities.
                if neighbour not in seen and found.setdefault(neighbour, (parent, []))[0] == parent:
                    found[neighbour][1].append(ev)
        # Shortest path wins: an entity found at this depth is never revisited deeper.
        level = []
        for entity_id in sorted(found):
            parent, evs = found[entity_id]
            level.append(Hop(entity_id, depth, parent, tuple(sorted(evs, key=lambda e: e.edge_id))))
        room = limits.max_rows - len(ordered)
        if len(level) > room:
            level, truncated = level[:room], truncated or "rows"
        ordered.extend(level)
        seen.update(h.entity_id for h in level)
        frontier = [h.entity_id for h in level]
        if truncated or not frontier:
            break

    start = 0
    if after is not None:
        start = next((i for i, h in enumerate(ordered) if (h.depth, h.entity_id) > after), len(ordered))
    page = ordered[start:start + limits.page_size]
    more = start + limits.page_size < len(ordered)
    return Page(tuple(page), _encode_cursor(page[-1]) if more and page else None, truncated)


def _edges_at(db, entity_id, direction, wanted, generation, credits_only):
    queries = []
    if direction in ("out", "both"):
        queries.append(("out", "from_id", "to_id"))
    if direction in ("in", "both"):
        queries.append(("in", "to_id", "from_id"))
    for label, here, there in queries:
        rows = db.execute(
            f"SELECT * FROM edges WHERE {here} = ? AND generation = ? AND {there} != ? ORDER BY id",
            (entity_id, generation, entity_id),
        ).fetchall()
        for row in rows:
            if wanted is not None and row["relation"] not in wanted:
                continue
            ev = Evidence(
                row["id"], row["relation"], row["role"], label, row["evidence_class"],
                row["match_quality"], row["source"], row["source_url"], row["valid_from"], row["valid_to"],
            )
            if credits_only and not is_credit(ev):
                continue
            yield row[there], ev


def _encode_cursor(hop: Hop) -> str:
    return base64.urlsafe_b64encode(f"{hop.depth}:{hop.entity_id}".encode()).decode().rstrip("=")


def _decode_cursor(cursor: str | None) -> tuple[int, int] | None:
    if cursor is None:
        return None
    try:
        depth, entity_id = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode().split(":")
        return int(depth), int(entity_id)
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise ValueError("invalid cursor") from exc
