"""Filter one big table straight out of the export archive, on every core, without unpacking it.

``track`` is several gigabytes and ``artist_credit_name`` more than a gigabyte; the slice needs a few
hundred thousand rows of each, and the ids to keep are only known after the earlier steps. So these
two tables are never extracted: the archive (one bzip2 stream of a tar file) is read front to back
once per call, the bzip2 blocks are decoded on every core by ``indexed_bzip2`` when it is installed,
and the line filtering runs in a pool of worker processes, one block of lines per task. Only the
wanted columns of matching rows come back; nothing is written to disk.

Rows are PostgreSQL ``COPY`` text, as in :mod:`dump`. A key column is a number that is never null
in the tables this is used for; a row whose key is not a number is skipped, never guessed at.
"""
from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from os import PathLike
from typing import Callable, Iterable

from . import dump

BLOCK_BYTES = 16 << 20
IN_FLIGHT_PER_WORKER = 3  # blocks queued per worker: enough to keep every core busy, bounded memory

# Column positions in the export (``mbdump/<table>``), the same order as the table definition.
TRACK_RECORDING, TRACK_MEDIUM = 2, 3
CREDIT_NAME_CREDIT, CREDIT_NAME_ARTIST = 0, 2

_key = 0
_keep: frozenset[int] = frozenset()
_take: tuple[int, ...] = ()


def _init(key: int, keep: frozenset[int], take: tuple[int, ...]) -> None:
    global _key, _keep, _take
    _key, _keep, _take = key, keep, take


def filter_block(block: bytes) -> list[tuple[int, ...]]:
    """Rows of one block of whole lines whose key column is in the kept set."""
    out = []
    for line in block.split(b"\n"):
        if not line:
            continue
        fields = line.split(b"\t")
        try:
            if int(fields[_key]) in _keep:
                out.append(tuple(int(fields[i]) for i in _take))
        except (ValueError, IndexError):
            continue
    return out


def filter_table(
    path: str | PathLike[str],
    table: str,
    key_column: int,
    keep: Iterable[int],
    take: tuple[int, ...],
    *,
    workers: int | None = None,
    parallel: bool | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> list[tuple[int, ...]]:
    """``take`` columns (as integers) of every row of ``table`` whose ``key_column`` is in ``keep``.

    Rows come back in archive order. An archive without the table is an error, not an empty answer.
    """
    wanted = frozenset(int(k) for k in keep)
    workers = workers or os.cpu_count() or 1
    parallel = dump.parallel_available() if parallel is None else parallel
    size = max(1, os.path.getsize(path))
    results: list[tuple[int, ...]] = []
    found = False
    pending: list = []
    with dump._open_stream(path, parallel) as (archive, position), \
            ProcessPoolExecutor(workers, initializer=_init, initargs=(key_column, wanted, take)) as pool:
        for member in archive:
            if not member.isfile() or member.name != "mbdump/" + table:
                continue
            found = True
            handle = archive.extractfile(member)
            while True:
                block = handle.read(BLOCK_BYTES)
                if not block:
                    break
                if not block.endswith(b"\n"):
                    block += handle.readline()
                pending.append(pool.submit(filter_block, block))
                while len(pending) >= workers * IN_FLIGHT_PER_WORKER:
                    results.extend(pending.pop(0).result())
                    if on_progress:
                        on_progress(min(1.0, position() / size))
            break  # the rest of the archive is not needed
        for future in pending:
            results.extend(future.result())
    if not found:
        raise dump.DumpError(f"archive lacks table: {table}")
    if on_progress:
        on_progress(1.0)
    return results
