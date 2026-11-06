"""Manual trigger for the Server V2 MusicBrainz slice import (Phase 4, worker side).

Run on the server by the owner; never called from a web route. Downloads the MusicBrainz
export (about 7.9 GB, resumable, checksum-verified) into a scratch directory, selects the
neighbourhood of the owned library, loads it into the knowledge store and prints aggregate
numbers only (no titles, paths or credentials).

    python scripts/server_v2_mb_slice_import.py --plan                 # no download: seeds and budgets only
    python scripts/server_v2_mb_slice_import.py --scratch /big/disk/mb # the real run (needs the owner's go-ahead)

The store is ``<data dir>/intelligence.sqlite3``; the data directory comes from ``--data-dir``,
else ``DISCAIR_DATA_DIR`` (the server's own setting). Budgets are the owner-approved ones in
docs/ServerV2.md (Phase 4); a breach before the load ends as ``fallback_api_only`` without writing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intelligence.musicbrainz import job, neighbourhood  # noqa: E402
from intelligence.store import open_store  # noqa: E402
from settings.data_directory import resolve_data_dir  # noqa: E402

STORE_FILE = "intelligence.sqlite3"  # same name as app.api.insights.STORE_FILE


def plan(db) -> dict:
    """What a run would start from, without any network traffic."""
    seeds = neighbourhood.owned_seeds(db)
    budgets = job.Budgets()
    return {"seeds": {table: len(ids) for table, ids in seeds.items()},
            "budgets": {k: getattr(budgets, k) for k in job.Budgets.__dataclass_fields__}}


def run(data_dir: Path, scratch: Path, *, plan_only: bool, export: str | None, cover_art: bool,
        keep_archive: bool, hops: int) -> dict:
    data_dir.mkdir(parents=True, exist_ok=True)
    db = open_store(data_dir / STORE_FILE)
    try:
        if plan_only:
            return plan(db)
        scratch.mkdir(parents=True, exist_ok=True)
        result = job.run_slice_import(
            db, scratch, export=export, include_cover_art=cover_art, delete_archive=not keep_archive, hops=hops)
        return {"state": result.state, "error": result.error, "progress": result.progress}
    finally:
        db.close()


def default_data_dir() -> Path:
    return resolve_data_dir(os.environ, Path(__file__).resolve().parent.parent / "navidrome_server.py")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument("--scratch", type=Path, default=None, help="download directory (default: <data dir>/mb-scratch)")
    parser.add_argument("--plan", action="store_true", help="print seeds and budgets; no download")
    parser.add_argument("--export", default=None, help="export directory name (default: the newest)")
    parser.add_argument("--include-cover-art", action="store_true")
    parser.add_argument("--keep-archive", action="store_true", help="keep the downloaded archive after loading")
    parser.add_argument("--hops", type=int, default=2)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    data_dir = args.data_dir or default_data_dir()
    report = run(data_dir, args.scratch or data_dir / "mb-scratch", plan_only=args.plan, export=args.export,
                 cover_art=args.include_cover_art, keep_archive=args.keep_archive, hops=args.hops)
    text = json.dumps(report, indent=2, sort_keys=True, default=str)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    return 0 if report.get("state", "succeeded") == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
