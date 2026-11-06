"""The one-off job that imports the MusicBrainz neighbourhood of the owned library.

Stages, in order: seeds (owned MBIDs; no seeds means nothing is downloaded), download
(resumable, checksum-verified), select (two hops, a fixed number of passes), load (one
transaction). The wrapper in :mod:`intelligence.jobs.runner` supplies visible state and
last-known-good behaviour; progress records each finished stage so a re-run skips the download.

The owner-approved budgets (docs/ServerV2.md, Phase 4) are checked with measured numbers and
recorded in the run's progress. A breach before the load (entity cap hit, import time spent,
scratch ceiling passed) stops without writing, outcome ``fallback_api_only``, which is the
Phase 4 kill criterion. A breach seen only after the load (slice size, import time) is recorded
as ``over_budget`` with the data in place; nothing is rolled back automatically.

No provider traffic beyond the export download, no ``navidrome_server.py`` involvement, and
nothing calls this yet: a manual trigger is a separate step.
"""
from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..jobs import runner
from ..store.generations import bump_data_version
from . import download, dump, loader, neighbourhood

JOB = "musicbrainz_slice"
RESOURCE = "musicbrainz_slice"


@dataclass(frozen=True)
class Budgets:
    download_bytes: int = 7_900_000_000
    scratch_bytes: int = 25_000_000_000
    slice_bytes: int = 2_000_000_000
    import_seconds: float = 2 * 3600.0
    max_entities: int = neighbourhood.DEFAULT_MAX_ENTITIES


def store_bytes(db: sqlite3.Connection) -> int:
    """Size of the store's database file and write-ahead log (0 for an in-memory store)."""
    row = next((r for r in db.execute("PRAGMA database_list") if r[1] == "main"), None)
    path = row[2] if row else ""
    if not path:
        return 0
    return sum(os.path.getsize(p) for p in (path, path + "-wal") if os.path.exists(p))


def directory_bytes(directory) -> int:
    return sum(p.stat().st_size for p in Path(directory).glob("*") if p.is_file())


def run_slice_import(
    db: sqlite3.Connection,
    directory,
    *,
    budgets: Budgets = Budgets(),
    opener: download.Opener = download.default_opener,
    export: str | None = None,
    include_cover_art: bool = False,
    delete_archive: bool = True,
    hops: int = 2,
    clock: Callable[[], float] = time.time,
) -> runner.RunResult:
    """Run (or resume) the import as a job; see the module docstring for outcomes."""

    def work(ctx: runner.JobContext) -> bool:
        progress = dict(ctx.progress)
        progress["budgets"] = {k: getattr(budgets, k) for k in Budgets.__dataclass_fields__}
        seeds = neighbourhood.owned_seeds(db)
        if not any(seeds.values()):
            progress["outcome"] = "no_seeds"
            ctx.checkpoint(progress)
            return True

        archive = Path(directory) / download.CORE_ARCHIVE
        if progress.get("stage") not in ("downloaded", "selected"):
            files = download.download_export(directory, include_cover_art, export, opener)
            archive = files[download.CORE_ARCHIVE]
            progress["stage"] = "downloaded"
            progress["archive_bytes"] = archive.stat().st_size
            progress["scratch_bytes"] = directory_bytes(directory)
            ctx.checkpoint(progress)
        breaches = []
        if progress.get("archive_bytes", 0) > budgets.download_bytes:
            breaches.append("download_bytes")
        if progress.get("scratch_bytes", 0) > budgets.scratch_bytes:
            breaches.append("scratch_bytes")

        started = clock()
        info = dump.read_info(archive)
        dump.check_schema(info)
        read = neighbourhood.archive_reader(archive)
        selection = neighbourhood.select_neighbourhood(
            read, seeds, hops=hops, max_entities=budgets.max_entities)
        progress["selection"] = selection.summary()
        progress["select_seconds"] = round(clock() - started, 3)
        if selection.truncated:
            breaches.append("max_entities")
        if clock() - started > budgets.import_seconds:
            breaches.append("import_seconds")
        if breaches:
            progress["outcome"] = "fallback_api_only"
            progress["breaches"] = sorted(set(breaches))
            ctx.checkpoint(progress)
            return True

        before = store_bytes(db)
        result = loader.load_neighbourhood(
            db, read, selection, dump_timestamp=info.timestamp, schema_sequence=info.schema_sequence,
            clock=clock)
        progress["load"] = result.summary()
        progress["import_seconds"] = round(clock() - started, 3)
        progress["slice_bytes"] = max(0, store_bytes(db) - before)
        progress["dump_timestamp"] = info.timestamp
        if progress["slice_bytes"] > budgets.slice_bytes:
            breaches.append("slice_bytes")
        if progress["import_seconds"] > budgets.import_seconds:
            breaches.append("import_seconds")
        progress["outcome"] = "over_budget" if breaches else "loaded"
        if breaches:
            progress["breaches"] = sorted(set(breaches))
        progress["stage"] = "loaded"
        with db:
            for key, value in (("dump_timestamp", info.timestamp or ""), ("schema_sequence", info.schema_sequence),
                               ("loaded_at", clock())):
                db.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (f"musicbrainz_slice.{key}", str(value)))
        bump_data_version(db, RESOURCE)
        if delete_archive:
            archive.unlink(missing_ok=True)
            progress["archive_deleted"] = True
        ctx.checkpoint(progress)
        return True

    return runner.run_job(db, JOB, work, clock=clock)
