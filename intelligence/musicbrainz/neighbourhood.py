"""Pick the part of MusicBrainz worth loading: entities within two hops of owned MBIDs.

The full export is one stream that can only be read front to back, so the walk is a fixed
number of passes over it, never a lookup per entity:

* pass 0 reads the entity tables to turn owned MBIDs (gids) into internal ids;
* pass 1 reads the relationship tables once and adds every entity linked to a seed;
* pass 2 reads them again and expands the entities added in pass 1.

Hub guard: at the second hop only recordings, releases, release groups and works are
expanded. An artist or label reached at hop 1 is kept (so its credit is shown) but its whole
catalogue is not pulled in, because one session player or one large label would otherwise
bring in thousands of unrelated releases. ``max_entities`` caps the total; hitting it stops
the walk and says so, so the caller can fall back to API-only with a tighter scope (the
Phase 4 kill criterion) instead of importing a surprise.

Nothing here writes to the store or touches the network.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from os import PathLike
from typing import Callable, Iterable, Iterator, Mapping

from . import dump
from .scan import RowFilter, scan_rows

# Relationship table -> (type of entity0, type of entity1), using dump table names.
LINK_TABLES: dict[str, tuple[str, str]] = {
    "l_artist_artist": ("artist", "artist"),
    "l_artist_label": ("artist", "label"),
    "l_artist_recording": ("artist", "recording"),
    "l_artist_release": ("artist", "release"),
    "l_artist_release_group": ("artist", "release_group"),
    "l_artist_work": ("artist", "work"),
    "l_label_release": ("label", "release"),
    "l_recording_work": ("recording", "work"),
    "l_work_work": ("work", "work"),
}
# Owned entity types that can be resolved from a gid; the dump table has the same name.
SEED_TYPES = ("artist", "release", "release_group", "recording")
# Types whose own relationships are followed at the second hop (see the hub guard above).
SECOND_HOP_TYPES = frozenset({"recording", "release", "release_group", "work"})
DEFAULT_MAX_ENTITIES = 3_000_000

TableReader = Callable[[Iterable[str]], Iterator[tuple[str, Iterator[Mapping[str, str | None]]]]]


@dataclass
class Neighbourhood:
    """Internal MusicBrainz ids chosen for import, by entity type."""

    selected: dict[str, set[int]] = field(default_factory=dict)
    seeds_requested: int = 0
    seeds_found: int = 0
    hop_added: list[int] = field(default_factory=list)  # new entities per hop
    passes: int = 0
    truncated: str | None = None  # "entity_cap" when the walk stopped early

    def count(self) -> int:
        return sum(len(ids) for ids in self.selected.values())

    @property
    def seeds_missing(self) -> int:
        return self.seeds_requested - self.seeds_found

    def summary(self) -> dict[str, object]:
        return {
            "passes": self.passes,
            "entities": self.count(),
            "by_type": {t: len(ids) for t, ids in sorted(self.selected.items())},
            "seeds_requested": self.seeds_requested,
            "seeds_found": self.seeds_found,
            "hop_added": list(self.hop_added),
            "truncated": self.truncated,
        }


def archive_reader(path: str | PathLike[str]) -> TableReader:
    """A reader that streams the named tables out of one dump archive, in archive order."""
    return lambda tables: dump.iter_tables(path, tables)


def owned_seeds(db: sqlite3.Connection) -> dict[str, set[str]]:
    """MBIDs of owned entities the dump can resolve, by dump table name."""
    seeds: dict[str, set[str]] = {t: set() for t in SEED_TYPES}
    rows = db.execute(
        "SELECT type, mbid FROM entities WHERE owned = 1 AND mbid IS NOT NULL AND type IN (%s)"
        % ", ".join("?" * len(SEED_TYPES)),
        SEED_TYPES,
    )
    for row in rows:
        seeds[row["type"]].add(row["mbid"].lower())
    return seeds


def select_neighbourhood(
    read: TableReader,
    seeds: Mapping[str, Iterable[str]],
    *,
    hops: int = 2,
    max_entities: int = DEFAULT_MAX_ENTITIES,
) -> Neighbourhood:
    """Walk ``hops`` (1 or 2) relationship steps out from the seed gids."""
    if hops not in (1, 2) or max_entities < 1:
        raise ValueError("hops must be 1 or 2 and max_entities positive")
    wanted = {t: {g.lower() for g in seeds.get(t, ())} for t in SEED_TYPES}
    result = Neighbourhood(seeds_requested=sum(len(g) for g in wanted.values()))
    if not result.seeds_requested:
        return result

    frontier = _resolve_seeds(read, wanted, result)
    result.passes += 1
    for hop in range(1, hops + 1):
        if not frontier or result.truncated:
            break
        if hop == 2:
            frontier = {t: ids for t, ids in frontier.items() if t in SECOND_HOP_TYPES}
        frontier = _expand(read, frontier, result, max_entities)
        result.passes += 1
        result.hop_added.append(sum(len(ids) for ids in frontier.values()))
    return result


def _resolve_seeds(read, wanted, result: Neighbourhood) -> dict[str, set[int]]:
    requests = {t: RowFilter(("id", "gid"), strs=(("gid", frozenset(wanted[t])),)) for t in SEED_TYPES if wanted[t]}
    frontier: dict[str, set[int]] = {}
    for table, rows in scan_rows(read, requests).items():
        frontier[table] = {int(row_id) for row_id, _ in rows}
    for table, ids in frontier.items():
        result.selected.setdefault(table, set()).update(ids)
        result.seeds_found += len(ids)
    return {t: ids for t, ids in frontier.items() if ids}


def _expand(read, frontier, result: Neighbourhood, max_entities: int) -> dict[str, set[int]]:
    added: dict[str, set[int]] = {}
    total = result.count()
    requests = {}
    for table, (type0, type1) in LINK_TABLES.items():
        from0, from1 = frontier.get(type0), frontier.get(type1)
        if not from0 and not from1:
            continue
        conditions = tuple((column, frozenset(ids)) for column, ids in (("entity0", from0), ("entity1", from1)) if ids)
        requests[table] = RowFilter(("entity0", "entity1"), ints=conditions, any_=True)
    for table, rows in scan_rows(read, requests).items():
        type0, type1 = LINK_TABLES[table]
        from0, from1 = frontier.get(type0), frontier.get(type1)
        for row in rows:
            id0, id1 = int(row[0]), int(row[1])
            for here, there, there_type, source in ((id0, id1, type1, from0), (id1, id0, type0, from1)):
                if not source or here not in source:
                    continue
                known = result.selected.setdefault(there_type, set())
                if there in known:
                    continue
                if total >= max_entities:
                    result.truncated = "entity_cap"
                    return added
                known.add(there)
                added.setdefault(there_type, set()).add(there)
                total += 1
    return added
