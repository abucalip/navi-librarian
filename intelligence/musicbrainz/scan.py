"""Parallel, chunked scans over the extracted dump tables (every core).

The slice import asks the same kind of question many times: "which rows of this table have an id
in this set?" A request names a table and a :class:`RowFilter`; the table file is cut into byte
ranges that each worker process filters, and the answers are joined in file order, so the result is
exactly what a single sequential pass would give. Only matching rows travel back to the caller, as
tuples of the requested columns. Anything without a ``scan`` method (the test fakes) is served by
:func:`scan_rows` with the same filter applied row by row.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .schema import TABLES

MIN_CHUNK_BYTES = 8 << 20
CHUNKS_PER_WORKER = 4
INLINE_BYTES = 32 << 20  # below this much data in total a pool costs more than it saves


@dataclass(frozen=True)
class RowFilter:
    """Which rows to keep and which columns to return.

    ``ints``: (column, allowed integer values); ``strs``: (column, allowed lower-case strings).
    A row is kept when it meets all conditions, or any of them when ``any_`` is set; with no
    conditions every row is kept.
    """
    columns: tuple[str, ...]
    ints: tuple[tuple[str, frozenset], ...] = ()
    strs: tuple[tuple[str, frozenset], ...] = ()
    any_: bool = False
    optional: tuple[str, ...] = ()  # columns a stand-in reader may omit (a real table always has every column)


def _decode(raw: bytes) -> str | None:
    from .dump import decode_field
    return decode_field(raw.decode("utf-8"))


def scan_range(path: str, table: str, flt: RowFilter, start: int, end: int) -> list[tuple]:
    """Filter the lines of ``path`` that begin in ``[start, end)``."""
    from .dump import DumpError
    names = TABLES[table]
    position = {name: i for i, name in enumerate(names)}
    ints = [(position[c], values) for c, values in flt.ints]
    strs = [(position[c], values) for c, values in flt.strs]
    out = [position.get(c) if c in flt.optional else position[c] for c in flt.columns]  # None: this table lacks it
    width, any_, conditions = len(names), flt.any_, bool(ints or strs)
    rows: list[tuple] = []
    with open(path, "rb") as handle:
        if start > 0:
            handle.seek(start - 1)
            handle.readline()  # the rest of the line that began before this range belongs to the previous one
        offset = handle.tell()
        for raw in handle:
            if offset >= end:
                break
            offset += len(raw)
            line = raw.rstrip(b"\n")
            if not line.strip():
                continue
            fields = line.split(b"\t")
            if len(fields) != width:
                raise DumpError(f"{table}: expected {width} columns, found {len(fields)}")
            if conditions:
                matched = _matches(fields, ints, strs, any_)
                if not matched:
                    continue
            rows.append(tuple(None if i is None else _decode(fields[i]) for i in out))
    return rows


def _matches(fields, ints, strs, any_: bool) -> bool:
    results = []
    for index, values in ints:
        try:
            results.append(int(fields[index]) in values)
        except ValueError:
            results.append(False)
        if any_ == results[-1]:
            return any_
    for index, values in strs:
        results.append(fields[index].decode("utf-8").lower() in values)
        if any_ == results[-1]:
            return any_
    return not any_


_FILTERS: dict[str, tuple[str, RowFilter]] = {}


def _init(filters: dict[str, tuple[str, RowFilter]]) -> None:
    _FILTERS.update(filters)


def _task(args: tuple[str, str, int, int]) -> list[tuple]:
    table, path, start, end = args
    return scan_range(path, table, _FILTERS[table][1], start, end)


def plan_chunks(size: int, workers: int) -> list[tuple[int, int]]:
    count = max(1, min(workers * CHUNKS_PER_WORKER, size // MIN_CHUNK_BYTES))
    step = -(-size // count) if size else 1
    return [(start, min(size, start + step)) for start in range(0, max(size, 1), step)] or [(0, 0)]


def scan_files(
    requests: Mapping[str, tuple[str, RowFilter]],
    *,
    workers: int | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> dict[str, list[tuple]]:
    """Run ``{table: (file path, filter)}`` on every core; rows come back in file order per table."""
    workers = workers or os.cpu_count() or 1
    sizes = {table: os.path.getsize(path) for table, (path, _) in requests.items()}
    total = max(1, sum(sizes.values()))
    done = [0]

    def advance(amount: int) -> None:
        done[0] += amount
        if on_progress:
            on_progress(min(1.0, done[0] / total))

    results: dict[str, list[tuple]] = {}
    if workers == 1 or total < INLINE_BYTES:
        for table, (path, flt) in requests.items():
            results[table] = scan_range(path, table, flt, 0, sizes[table] + 1)
            advance(sizes[table])
        if on_progress:
            on_progress(1.0)
        return results
    plans = {table: plan_chunks(size, workers) for table, size in sizes.items()}
    with ProcessPoolExecutor(max_workers=workers, initializer=_init, initargs=(dict(requests),)) as pool:
        futures: dict[str, list[Any]] = {}
        size_of: dict[Any, int] = {}
        for table, chunks in plans.items():
            path = requests[table][0]
            futures[table] = []
            for start, end in chunks:
                future = pool.submit(_task, (table, path, start, end))
                size_of[future] = end - start
                futures[table].append(future)
        for future in as_completed(size_of):  # progress is reported here, on the caller's thread
            future.result()
            advance(size_of[future])
        for table, group in futures.items():
            results[table] = [row for future in group for row in future.result()]
    if on_progress:
        on_progress(1.0)
    return results


def scan_rows(read: Any, requests: Mapping[str, RowFilter]) -> dict[str, list[tuple]]:
    """Answer ``{table: filter}`` through ``read.scan`` when it has one, else by iterating ``read``."""
    scan = getattr(read, "scan", None)
    if scan is not None:
        return scan(requests)
    results: dict[str, list[tuple]] = {table: [] for table in requests}
    for table, rows in read(list(requests)):
        flt = requests[table]
        for row in rows:
            if _row_matches(row, flt):
                results[table].append(tuple(row.get(c) if c in flt.optional else row[c] for c in flt.columns))
    return results


def _row_matches(row: Mapping[str, str | None], flt: RowFilter) -> bool:
    checks = []
    for column, values in flt.ints:
        try:
            checks.append(int(row[column]) in values)
        except (TypeError, ValueError):
            checks.append(False)
    for column, values in flt.strs:
        checks.append((row[column] or "").lower() in values)
    if not checks:
        return True
    return any(checks) if flt.any_ else all(checks)
