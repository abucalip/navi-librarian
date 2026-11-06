"""The one-off job that imports the MusicBrainz neighbourhood of the owned library.

Stages, in order: seeds (owned MBIDs; no seeds means nothing is downloaded), download
(resumable, checksum-verified), extract (one pass over the archive, on every core when indexed_bzip2
is installed, writing only the tables the slice reads to plain files), select (two hops, a
fixed number of passes over those plain files, so nothing is decompressed twice), load (one
transaction). The wrapper in :mod:`intelligence.jobs.runner` supplies visible state and
last-known-good behaviour; progress records each finished stage so a re-run skips the download.

The owner-approved budgets (docs/ServerV2.md, Phase 4) are checked with measured numbers and
recorded in the run's progress. A breach before the load (entity cap hit, import time spent,
scratch ceiling passed) stops without writing, outcome ``fallback_api_only``, which is the
Phase 4 kill criterion. A breach seen only after the load (slice size, import time) is recorded
as ``over_budget`` with the data in place; nothing is rolled back automatically.

A newer import replaces the previous slice in the load's own transaction (edges that left the
dump are removed). A dump that keeps too little of the previous slice is refused, outcome
``rejected``, with the previous slice untouched. Each run records a ``source_state`` row
(``musicbrainz_dump``, ``slice_import``, ``core``): ``ok`` after a load, ``blocked`` after a
budget fallback, ``error`` after a rejection.

After a load, API-sourced edges the dump now states identically are dropped
(:func:`api_fill.absorb_api_edges`; the API fill job covers the gap between imports).

No provider traffic beyond the export download, no ``navidrome_server.py`` involvement, and
nothing calls this yet: a manual trigger is a separate step.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from ..jobs import runner
from ..store import source_state
from ..store.generations import bump_data_version
from . import api_fill, download, dump, loader, neighbourhood
from .neighbourhood import LINK_TABLES, SEED_TYPES

EXTRACT_DIR = "extracted"
NEEDED_TABLES = tuple(sorted(set(SEED_TYPES) | set(loader.ENTITY_TABLES) | set(LINK_TABLES) | set(loader.FACT_TABLES)
                             | {"link", "link_attribute", "link_type", "link_attribute_type"}))

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


def _record(db: sqlite3.Connection, outcome: str, clock: Callable[[], float]) -> None:
    source_state.record_outcome(db, loader.SOURCE, "slice_import", "core", outcome, now=clock())


def run_slice_import(
    db: sqlite3.Connection,
    directory,
    *,
    budgets: Budgets = Budgets(),
    opener: download.Opener = download.default_opener,
    export: str | None = None,
    include_cover_art: bool = False,
    delete_archive: bool = True,
    keep_extracted: bool = False,
    hops: int = 2,
    clock: Callable[[], float] = time.time,
    on_progress: Callable[[str, int], None] | None = None,
) -> runner.RunResult:
    """Run (or resume) the import as a job; see the module docstring for outcomes."""

    def work(ctx: runner.JobContext) -> bool:
        progress = dict(ctx.progress)
        last = {}

        def report(stage: str, fraction: float) -> None:
            """Tell the caller each whole percent, and save every 5% so other tools can see it."""
            percent = int(100 * min(1.0, max(0.0, fraction)))
            if last.get(stage) == percent:
                return
            last[stage] = percent
            if on_progress:
                on_progress(stage, percent)
            if percent % 5 == 0:
                progress["current"] = {"stage": stage, "percent": percent}
                ctx.checkpoint(progress)

        progress["budgets"] = {k: getattr(budgets, k) for k in Budgets.__dataclass_fields__}
        seeds = neighbourhood.owned_seeds(db)
        if not any(seeds.values()):
            progress["outcome"] = "no_seeds"
            ctx.checkpoint(progress)
            return True

        archive = Path(directory) / download.CORE_ARCHIVE
        if progress.get("stage") not in ("downloaded", "extracted", "selected"):
            files = download.download_export(
                directory, include_cover_art, export, opener,
                on_progress=lambda got, total: report("download", got / total if total else 0.0))
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
        extract_dir = Path(directory) / EXTRACT_DIR
        parallel = dump.parallel_available()
        progress["decompressor"] = "indexed_bzip2" if parallel else "python-bz2"
        extracted = dump.extract_tables(archive, NEEDED_TABLES, extract_dir, parallel=parallel,
                                        on_progress=lambda f: report("extract", f))
        progress["extract_seconds"] = round(clock() - started, 3)
        progress["extracted_bytes"] = sum(extracted.values())
        progress["scratch_bytes"] = directory_bytes(directory) + directory_bytes(extract_dir)
        if progress["scratch_bytes"] > budgets.scratch_bytes:
            breaches.append("scratch_bytes")
        progress["stage"] = "extracted"
        ctx.checkpoint(progress)
        phase = ["select"]
        read = dump.extracted_reader(extract_dir, on_progress=lambda n, f: report(f"{phase[0]} pass {n}", f))
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
            _record(db, "blocked", clock)
            ctx.checkpoint(progress)
            return True

        before = store_bytes(db)
        phase[0] = "load"
        try:
            result = loader.load_neighbourhood(
                db, read, selection, dump_timestamp=info.timestamp, schema_sequence=info.schema_sequence,
                clock=clock)
        except loader.SliceValidationError as exc:
            progress["outcome"] = "rejected"
            progress["rejected_reason"] = str(exc)
            _record(db, "error", clock)
            ctx.checkpoint(progress)
            return True
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
        _record(db, "ok", clock)
        progress["api_edges_absorbed"] = api_fill.absorb_api_edges(db)
        bump_data_version(db, RESOURCE)
        if delete_archive:
            archive.unlink(missing_ok=True)
            progress["archive_deleted"] = True
        if not keep_extracted:
            shutil.rmtree(extract_dir, ignore_errors=True)
            progress["extracted_deleted"] = True
        ctx.checkpoint(progress)
        return True

    return runner.run_job(db, JOB, work, clock=clock)
