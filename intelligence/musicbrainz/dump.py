"""Streaming reader for the MusicBrainz full-export archive (``mbdump.tar.bz2``).

The archive is one bzip2 stream of a tar file, so it can only be read front to back:
there is no way to fetch one table or one artist. Tables arrive in the archive's own order,
and a caller that needs table B before table A makes another pass (``iter_tables`` can be
called again). Rows are decoded from PostgreSQL ``COPY`` text format lazily; nothing is
unpacked to disk, so peak disk is the archive itself.
"""
from __future__ import annotations

import hashlib
import tarfile
from dataclasses import dataclass
from os import PathLike
from typing import Iterable, Iterator

from .schema import EXPECTED_SCHEMA_SEQUENCE, TABLES

_HASH_CHUNK = 1 << 20
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
