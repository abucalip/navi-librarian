#!/usr/bin/env python3
"""Copy every SQLite store under the data directory while the app runs (efficiency S2).

Each store is copied with ``sqlite3.Connection.backup`` (never a file copy: the stores run in WAL mode,
so the main file alone is not a consistent snapshot). The source is opened without creating it and is
never written. Every copy is created with mode 0600 inside a 0700 backup directory, checked with
``PRAGMA integrity_check`` and left as one self-contained file (no ``-wal``/``-shm``).

The store list below is explicit, not a glob. ``tests/test_backup_stores.py`` checks each entry against
the code that owns the file name. The settings file (``navidrome_discovery.sqlite3``) holds credentials
(settings, and the acquisition state and discovery lists that share it), so treat the backup directory
as secret. Output is file name, size and status only: never row contents or values.

Usage: ``python scripts/backup_stores.py --dest /backups [--data-dir /data]``
Exit code: 0 all present stores copied; 1 a copy failed or no store was found.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from typing import NamedTuple
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.provider_gate import GATE_FILE  # noqa: E402  (stdlib-only module)
from intelligence.store.state import default_state_path  # noqa: E402
from settings.data_directory import resolve_data_dir  # noqa: E402

KNOWLEDGE_FILE = "intelligence.sqlite3"


class Store(NamedTuple):
    name: str  # path relative to the data directory
    owner: str  # what lives in it, and where the name is defined (checked by the tests)


# Names that are only string literals in heavy runtime modules (navidrome_server, app.api.*) are
# duplicated here on purpose; importing them would start the whole application.
STORES: tuple[Store, ...] = (
    Store("navidrome_discovery.sqlite3", "settings and credentials, acquisitions, discovery lists: navidrome_server.DISCOVERY_DB"),
    Store(KNOWLEDGE_FILE, "knowledge store: app/api/*.py STORE_FILE"),
    Store(Path(default_state_path(KNOWLEDGE_FILE)).name, "owner state (decisions): intelligence/store/state.py default_state_path"),
    Store("navidrome_metadata_cache.sqlite3", "metadata cache: navidrome_server.METADATA_CACHE_DB"),
    Store(GATE_FILE, "provider gate: integrations/provider_gate.py GATE_FILE"),
    Store("radio.sqlite3", "radio: app/api/radio.py"),
    Store("artwork/artwork.sqlite3", "artwork index: app/api/artwork.py (root) and intelligence/artwork/store.py"),
    Store("song_peaks.sqlite3", "waveform peaks: app/api/waveform.py"),
)


def _fix_mode(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def _create_private(path: Path) -> None:
    """Create an empty file that is 0600 from its first moment (umask cannot widen it)."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    _fix_mode(path, 0o600)


def backup_one(source: Path, target: Path) -> int:
    """Copy one store with the backup API and verify the copy. Returns the copy's size in bytes."""
    target.parent.mkdir(parents=True, exist_ok=True)
    _fix_mode(target.parent, 0o700)
    _create_private(target)
    src = sqlite3.connect(f"file:{source}?mode=rw", uri=True, timeout=30)  # mode=rw never creates a file
    try:
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
            dst.execute("PRAGMA journal_mode = DELETE")  # one self-contained file
            verdict = dst.execute("PRAGMA integrity_check").fetchone()
            if not verdict or verdict[0] != "ok":
                raise sqlite3.DatabaseError("integrity_check failed on the copy")
        finally:
            dst.close()
    finally:
        src.close()
    for suffix in ("-wal", "-shm", "-journal"):
        Path(str(target) + suffix).unlink(missing_ok=True)
    _fix_mode(target, 0o600)
    return target.stat().st_size


def run_backup(data_dir: Path, dest: Path, stores: tuple[Store, ...] = STORES) -> list[tuple[str, str, int]]:
    """Back up every present store into ``dest``; returns ``(name, status, size)`` rows.

    Status is ``ok``, ``skipped`` (no such file) or ``failed`` (a partial copy is removed).
    """
    dest.mkdir(parents=True, exist_ok=True)
    _fix_mode(dest, 0o700)
    results = []
    for store in stores:
        source = data_dir / store.name
        target = dest / store.name
        if not source.is_file():
            results.append((store.name, "skipped", 0))
            continue
        try:
            results.append((store.name, "ok", backup_one(source, target)))
        except Exception as error:  # report the type only; messages can carry paths or values
            target.unlink(missing_ok=True)
            results.append((store.name, f"failed ({type(error).__name__})", 0))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Back up every SQLite store under the data directory.")
    parser.add_argument("--dest", required=True, type=Path, help="directory that receives a new timestamped subdirectory")
    parser.add_argument("--data-dir", type=Path, default=None, help="data directory (default: DISCAIR_DATA_DIR, as the app resolves it)")
    args = parser.parse_args(argv)
    data_dir = args.data_dir or resolve_data_dir(os.environ, REPO_ROOT / "navidrome_server.py")
    if not data_dir.is_dir():
        print("data directory not found", file=sys.stderr)
        return 1
    dest = args.dest.expanduser() / ("stores-" + time.strftime("%Y%m%dT%H%M%S", time.gmtime()))
    if dest.resolve().is_relative_to(data_dir.resolve()):
        print("refusing to write the backup inside the data directory", file=sys.stderr)
        return 1
    results = run_backup(data_dir, dest)
    for name, status, size in results:
        print(f"{status:<8} {name}  {size} bytes" if status == "ok" else f"{status:<8} {name}")
    print(f"backup directory: {dest}")
    ok = sum(1 for _, status, _ in results if status == "ok")
    failed = sum(1 for _, status, _ in results if status.startswith("failed"))
    return 1 if failed or not ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
