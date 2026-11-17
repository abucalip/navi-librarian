#!/usr/bin/env python3
"""Read-only size report for the SQLite stores (efficiency S1, report part).

For every store in ``backup_stores.STORES`` under the data directory this prints the row count of
each table and the bytes of each table and index (from the ``dbstat`` virtual table when the SQLite
build has it), plus each file's size, its ``-wal`` size and ``page_count * page_size``.

Every file is opened with ``file:<path>?mode=ro``: the report never creates, writes or truncates a
store. A missing store is reported as ``missing`` and is not created. Output is names and numbers
only: the report runs ``COUNT(*)`` and ``dbstat`` sums, and never reads row values.

Usage: ``python scripts/store_size_report.py [--data-dir DIR] [--json PATH]``
Exit code: 0 report printed; 1 the data directory does not exist.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
for _path in (REPO_ROOT, SCRIPTS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from backup_stores import STORES, Store  # noqa: E402  (one store list, shared with the backup script)
from settings.data_directory import resolve_data_dir  # noqa: E402


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _sidecar(path: Path, suffix: str) -> Path:
    return Path(str(path) + suffix)


def open_read_only(path: Path) -> sqlite3.Connection:
    """Open an existing store without creating any file beside it.

    SQLite creates ``-wal``/``-shm`` even on a ``mode=ro`` connection to a WAL file, so:
    with no ``-wal`` the file holds every committed page and ``immutable=1`` reads it without
    touching the directory; with ``-wal`` and ``-shm`` both present, ``mode=ro`` only reads them.
    The caller skips a store that has ``-wal`` but no ``-shm`` (opening it would create ``-shm``).
    """
    uri = path.resolve().as_uri()
    if not _sidecar(path, "-wal").exists():
        return sqlite3.connect(f"{uri}?mode=ro&immutable=1", uri=True, timeout=30)
    return sqlite3.connect(f"{uri}?mode=ro", uri=True, timeout=30)


def query_dbstat(conn: sqlite3.Connection) -> dict[str, int]:
    """Bytes allocated per table or index name. Raises ``sqlite3.OperationalError`` without dbstat."""
    rows = conn.execute("SELECT name, SUM(pgsize) FROM dbstat GROUP BY name").fetchall()
    return {name: int(total or 0) for name, total in rows}


def probe_dbstat() -> bool:
    """True when this SQLite build provides the dbstat virtual table (checked on an empty in-memory db)."""
    try:
        query_dbstat(sqlite3.connect(":memory:"))
    except sqlite3.Error:
        return False
    return True


def store_report(store: Store, path: Path, use_dbstat: bool) -> dict[str, Any]:
    entry: dict[str, Any] = {"name": store.name, "owner": store.owner, "status": "missing", "objects": []}
    if not path.is_file():
        return entry
    wal = _sidecar(path, "-wal")
    entry["file_bytes"] = path.stat().st_size
    entry["wal_bytes"] = wal.stat().st_size if wal.is_file() else None
    if wal.is_file() and not _sidecar(path, "-shm").exists():
        entry["status"] = "skipped (-wal without -shm; opening would create -shm)"
        return entry
    try:
        conn = open_read_only(path)
    except sqlite3.Error as error:
        entry["status"] = f"error ({type(error).__name__})"
        return entry
    try:
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        page_count = conn.execute("PRAGMA page_count").fetchone()[0]
        entry.update(status="ok", page_size=page_size, page_count=page_count, allocated_bytes=page_size * page_count)
        per_object: dict[str, int] | None = None
        if use_dbstat:
            try:
                per_object = query_dbstat(conn)
            except sqlite3.Error:
                per_object = None
        objects = []
        for name, kind in conn.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'index')").fetchall():
            item: dict[str, Any] = {"name": name, "kind": kind, "rows": None, "bytes": None}
            if kind == "table":
                try:
                    item["rows"] = conn.execute(f"SELECT COUNT(*) FROM {_quote(name)}").fetchone()[0]
                except sqlite3.Error as error:
                    item["error"] = type(error).__name__
            if per_object is not None:
                item["bytes"] = per_object.get(name, 0)
            objects.append(item)
    except sqlite3.Error as error:
        entry.update(status=f"error ({type(error).__name__})", objects=[])
        return entry
    finally:
        conn.close()
    objects.sort(key=lambda o: (-(o["bytes"] or 0), -(o["rows"] or 0), o["name"]))
    entry["objects"] = objects
    return entry


def build_report(data_dir: Path, stores: tuple[Store, ...] = STORES) -> dict[str, Any]:
    use_dbstat = probe_dbstat()
    return {
        "data_dir": str(data_dir),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dbstat": use_dbstat,
        "stores": [store_report(store, data_dir / store.name, use_dbstat) for store in stores],
    }


def _bytes(value: int | None) -> str:
    return "n/a" if value is None else str(value)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SQLite store size report",
        "",
        f"Generated: {report['generated_at']}  ",
        f"dbstat: {'available' if report['dbstat'] else 'unavailable (bytes shown as n/a)'}",
        "",
        "## Files",
        "",
        "| store | status | file bytes | -wal bytes | page_count x page_size |",
        "|---|---|---:|---:|---:|",
    ]
    for store in report["stores"]:
        allocated = "-" if store["status"] != "ok" else f"{store['page_count']} x {store['page_size']} = {store['allocated_bytes']}"
        wal = "-" if store.get("wal_bytes") is None else str(store["wal_bytes"])
        lines.append(f"| {store['name']} | {store['status']} | {store.get('file_bytes', '-')} | {wal} | {allocated} |")
    lines += ["", "## Tables and indexes (by bytes, then rows)", "", "| store | table | rows | bytes |", "|---|---|---:|---:|"]
    for store in report["stores"]:
        for obj in store["objects"]:
            label = obj["name"] if obj["kind"] == "table" else f"index: {obj['name']}"
            if obj["kind"] == "table":
                rows = str(obj["rows"]) if obj["rows"] is not None else f"error ({obj.get('error', 'unknown')})"
            else:
                rows = "-"
            lines.append(f"| {store['name']} | {label} | {rows} | {_bytes(obj['bytes'])} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only row and byte report for the SQLite stores.")
    parser.add_argument("--data-dir", type=Path, default=None, help="data directory (default: DISCAIR_DATA_DIR, as the app resolves it)")
    parser.add_argument("--json", type=Path, default=None, help="also write the report as JSON to this path")
    args = parser.parse_args(argv)
    data_dir = args.data_dir or resolve_data_dir(os.environ, REPO_ROOT / "navidrome_server.py")
    if not data_dir.is_dir():
        print("data directory not found", file=sys.stderr)
        return 1
    report = build_report(data_dir)
    sys.stdout.write(render_markdown(report))
    if args.json is not None:
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"json written: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
