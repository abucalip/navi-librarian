"""Streaming reader for the MusicBrainz full-export archive (``mbdump.tar.bz2``).

The archive is one bzip2 stream of a tar file, so it can only be read front to back:
there is no way to fetch one table or one artist. Tables arrive in the archive's own order,
and a caller that needs table B before table A makes another pass (``iter_tables`` can be
called again). Rows are decoded from PostgreSQL ``COPY`` text format lazily; nothing is
unpacked to disk, so peak disk is the archive itself.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import tarfile
from dataclasses import dataclass
from os import PathLike
from typing import Callable, Iterable, Iterator

from .schema import EXPECTED_SCHEMA_SEQUENCE, TABLES

_HASH_CHUNK = 1 << 20
COMPLETE_MARKER = "_complete.json"
_ESCAPES = {"\\": "\\", "n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v"}


class DumpError(RuntimeError):
    """The archive is not one this code can read safely."""


@dataclass(frozen=True)
class DumpInfo:
    schema_sequence: int
    timestamp: str | None


def sha256_file(path: str | PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_checksum(path: str | PathLike[str], expected_sha256: str) -> None:
    actual = sha256_file(path)
    if actual != expected_sha256.strip().lower():
        raise DumpError(f"checksum mismatch for {path}: expected {expected_sha256}, got {actual}")


def decode_field(raw: str) -> str | None:
    """One COPY-text field: ``\\N`` is NULL, backslash escapes are undone."""
    if raw == "\\N":
        return None
    if "\\" not in raw:
        return raw
    out: list[str] = []
    i = 0
    while i < len(raw):
        char = raw[i]
        if char == "\\" and i + 1 < len(raw):
            out.append(_ESCAPES.get(raw[i + 1], raw[i + 1]))
            i += 2
        else:
            out.append(char)
            i += 1
    return "".join(out)


def decode_row(line: str, columns: tuple[str, ...]) -> dict[str, str | None]:
    fields = line.rstrip("\n").split("\t")
    if len(fields) != len(columns):
        raise DumpError(f"expected {len(columns)} columns, found {len(fields)}")
    return {name: decode_field(value) for name, value in zip(columns, fields)}


def check_schema(info: DumpInfo) -> None:
    if info.schema_sequence != EXPECTED_SCHEMA_SEQUENCE:
        raise DumpError(
            f"dump has schema sequence {info.schema_sequence}; this code reads "
            f"{EXPECTED_SCHEMA_SEQUENCE}. Column layouts must be re-checked before importing."
        )


def _open(path):
    try:
        return tarfile.open(path, mode="r|bz2")
    except (tarfile.TarError, OSError, EOFError) as exc:
        raise DumpError(f"cannot open {path}: {exc}") from exc


def read_info(path: str | PathLike[str]) -> DumpInfo:
    """Read SCHEMA_SEQUENCE (and TIMESTAMP when present) from the archive's first members."""
    values: dict[str, str] = {}
    with _open(path) as archive:
        for member in archive:
            if member.name.startswith("mbdump/"):
                break
            if member.name in ("SCHEMA_SEQUENCE", "TIMESTAMP"):
                handle = archive.extractfile(member)
                values[member.name] = handle.read().decode("utf-8").strip() if handle else ""
    if "SCHEMA_SEQUENCE" not in values:
        raise DumpError("archive has no SCHEMA_SEQUENCE; not a MusicBrainz full export")
    try:
        sequence = int(values["SCHEMA_SEQUENCE"])
    except ValueError as exc:
        raise DumpError(f"unreadable SCHEMA_SEQUENCE {values['SCHEMA_SEQUENCE']!r}") from exc
    return DumpInfo(sequence, values.get("TIMESTAMP"))


def iter_tables(
    path: str | PathLike[str], wanted: Iterable[str]
) -> Iterator[tuple[str, Iterator[dict[str, str | None]]]]:
    """Yield ``(table, rows)`` for each wanted table, in archive order.

    ``rows`` must be consumed (or abandoned) before asking for the next table; the
    underlying stream cannot go back. Unknown names raise ``KeyError`` up front.
    """
    names = set(wanted)
    unknown = names - TABLES.keys()
    if unknown:
        raise KeyError(f"no column layout for: {', '.join(sorted(unknown))}")
    info = read_info(path)
    check_schema(info)
    with _open(path) as archive:
        for member in archive:
            if not member.isfile() or not member.name.startswith("mbdump/"):
                continue
            table = member.name[len("mbdump/"):]
            if table not in names:
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            yield table, _rows(handle, TABLES[table])


def _rows(handle, columns: tuple[str, ...]) -> Iterator[dict[str, str | None]]:
    for raw in handle:
        line = raw.decode("utf-8")
        if line.strip():
            yield decode_row(line, columns)


# ---------------------------------------------------------------------------------------------
# Decompress once: the wanted tables are written to plain files in one pass over the archive, and
# every later pass reads those files (docs/ServerV2.md Phase 4; owner direction 2026-11-06).

def parallel_available() -> bool:
    """True when the optional ``indexed_bzip2`` package is installed (multi-core bzip2 block decoding).

    ``pbzip2`` is not used: it only parallelises its own multi-stream files, and the MusicBrainz
    export is one ordinary bzip2 stream (measured: no speed-up over ``bzip2``).
    """
    try:
        import indexed_bzip2  # noqa: F401
    except ImportError:
        return False
    return (os.cpu_count() or 1) > 1


@contextlib.contextmanager
def _open_stream(path, parallel: bool):
    """Yield ``(tar stream, position)``; ``position()`` is the compressed bytes consumed so far.

    With ``parallel`` the bzip2 blocks are decoded on every core by ``indexed_bzip2``; otherwise
    Python's single-threaded bz2 is used.
    """
    if parallel:
        import indexed_bzip2
        source = indexed_bzip2.open(os.fspath(path), parallelization=os.cpu_count() or 1)
        try:
            with tarfile.open(fileobj=source, mode="r|") as archive:
                yield archive, lambda: source.tell_compressed() // 8
        finally:
            source.close()
        return
    with open(path, "rb") as source:
        try:
            with tarfile.open(fileobj=source, mode="r|bz2") as archive:
                yield archive, lambda: os.lseek(source.fileno(), 0, os.SEEK_CUR)
        except (tarfile.TarError, OSError, EOFError) as exc:
            raise DumpError(f"cannot open {path}: {exc}") from exc


def extract_tables(
    path: str | PathLike[str],
    wanted: Iterable[str],
    dest: str | PathLike[str],
    *,
    parallel: bool | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> dict[str, int]:
    """One pass over the archive: write each wanted table to ``dest/<table>`` (raw COPY text).

    Returns bytes written per table. A folder already holding every wanted table for this same
    archive (``_complete.json``) is reused and nothing is decompressed. Files appear under their
    final name only when complete, and the marker is written last, so an interrupted run is redone.
    """
    names = set(wanted)
    unknown = names - TABLES.keys()
    if unknown:
        raise KeyError(f"no column layout for: {', '.join(sorted(unknown))}")
    dest = os.fspath(dest)
    archive_size = os.path.getsize(path)
    marker = os.path.join(dest, COMPLETE_MARKER)
    if os.path.exists(marker):
        with open(marker) as handle:
            done = json.load(handle)
        if done.get("archive_bytes") == archive_size and names <= set(done.get("tables", {})):
            return {t: done["tables"][t] for t in names}
    check_schema(read_info(path))
    os.makedirs(dest, exist_ok=True)
    if os.path.exists(marker):
        os.unlink(marker)
    if parallel is None:
        parallel = parallel_available()
    written: dict[str, int] = {}

    def report(position):
        if on_progress:
            on_progress(min(1.0, position() / archive_size))

    with _open_stream(path, parallel) as (archive, position):
        for member in archive:
            if not member.isfile() or not member.name.startswith("mbdump/"):
                continue
            table = member.name[len("mbdump/"):]
            if table not in names or table in written:
                continue
            handle = archive.extractfile(member)
            if handle is None:
                continue
            temporary = os.path.join(dest, table + ".tmp")
            with open(temporary, "wb") as out:
                for chunk in iter(lambda: handle.read(1 << 22), b""):
                    out.write(chunk)
                    report(position)
            os.replace(temporary, os.path.join(dest, table))
            written[table] = os.path.getsize(os.path.join(dest, table))
            if len(written) == len(names):
                break  # everything wanted is out: no need to decompress the rest of the archive
    missing = names - written.keys()
    if missing:
        raise DumpError(f"archive lacks tables: {', '.join(sorted(missing))}")
    if on_progress:
        on_progress(1.0)
    with open(marker, "w") as handle:
        json.dump({"archive_bytes": archive_size, "tables": written}, handle)
    return written


class ExtractedReader:
    """A table reader over a folder written by :func:`extract_tables`.

    Calling it behaves like ``iter_tables`` (rows of the named tables, one pass in the given
    order). ``scan`` answers ``{table: RowFilter}`` on every core (see :mod:`.scan`). Both count
    as one pass for progress: ``on_progress(pass_number, fraction)``.
    """

    def __init__(self, dest, on_progress: Callable[[int, float], None] | None = None, workers: int | None = None):
        self.dest = os.fspath(dest)
        self.on_progress = on_progress
        self.workers = workers
        self.passes = 0

    def _files(self, names: list[str]) -> list[str]:
        unknown = set(names) - TABLES.keys()
        if unknown:
            raise KeyError(f"no column layout for: {', '.join(sorted(unknown))}")
        files = [os.path.join(self.dest, table) for table in names]
        for file in files:
            if not os.path.exists(file):
                raise DumpError(f"{file} was not extracted")
        return files

    def __call__(self, wanted: Iterable[str]):
        names = list(wanted)
        files = self._files(names)
        self.passes += 1
        number, total, done = self.passes, max(1, sum(os.path.getsize(f) for f in files)), [0]
        for table, file in zip(names, files):
            with open(file, "rb") as handle:
                yield table, _counted_rows(handle, TABLES[table], done, total, number, self.on_progress)

    def scan(self, requests):
        from .scan import scan_files
        names = list(requests)
        files = self._files(names)
        self.passes += 1
        number = self.passes
        callback = (lambda fraction: self.on_progress(number, fraction)) if self.on_progress else None
        return scan_files({t: (f, requests[t]) for t, f in zip(names, files)}, workers=self.workers, on_progress=callback)


def extracted_reader(dest: str | PathLike[str], on_progress: Callable[[int, float], None] | None = None,
                     workers: int | None = None) -> ExtractedReader:
    """See :class:`ExtractedReader`."""
    return ExtractedReader(dest, on_progress, workers)


def _counted_rows(handle, columns, done, total, number, on_progress):
    last = -1
    for raw in handle:
        done[0] += len(raw)
        if on_progress:
            percent = int(100 * done[0] / total)
            if percent != last:
                last = percent
                on_progress(number, done[0] / total)
        line = raw.decode("utf-8")
        if line.strip():
            yield decode_row(line, columns)
