"""Audit: does the store already hold every place, credit and work link of the owned recordings?

Album paths 1 (Studio Crew), 3 (Same Room) and 4 (Covers and Sources) need recording-scope links of the
owned recordings. This compares the MusicBrainz export with a store: for each relation touching an owned
recording it counts the distinct (recording, other end, relation) triples in the dump and in the store and
prints the difference, so a missing slice is found by measurement and not assumed.

Read-only on the store (opened ``mode=ro``) and on the archive. Decompression runs on every core
(``indexed_bzip2``; refuses to start without it unless ``--allow-single-core``) and so does every table
scan (:mod:`intelligence.musicbrainz.scan`). Only the tables listed in ``TABLES`` are unpacked, into
``--scratch``, and removed afterwards unless ``--keep-extracted``.

    python scripts/album_slice_audit.py --archive mbdump.tar.bz2 --store intelligence.sqlite3 \
        --scratch /big/disk/audit [--out audit.json]

Prints counts only (no titles, paths or credentials).
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intelligence.musicbrainz import dump  # noqa: E402
from intelligence.musicbrainz.scan import RowFilter  # noqa: E402

# table -> (column that holds the recording, column holding the other end, store type of the other end)
LINKS = {
    "l_place_recording": ("entity1", "entity0", "place"),
    "l_area_recording": ("entity1", "entity0", "area"),
    "l_event_recording": ("entity1", "entity0", "event"),
    "l_artist_recording": ("entity1", "entity0", "artist"),
    "l_recording_work": ("entity0", "entity1", "work"),
    "l_recording_recording": ("entity0", "entity1", "recording"),  # symmetric table: both ends are checked
}
TABLES = ("recording", "link", "link_type", *LINKS)


def log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def owned_recording_gids(db: sqlite3.Connection) -> set[str]:
    return {r[0].lower() for r in db.execute(
        "SELECT mbid FROM entities WHERE type = 'recording' AND owned = 1 AND mbid IS NOT NULL")}


def store_counts(db: sqlite3.Connection) -> dict[tuple[str, str], int]:
    """``{(other end type, relation): distinct (recording, other end, relation)}`` from dump edges."""
    counts: dict[tuple[str, str], set] = collections.defaultdict(set)
    sql = ("SELECT f.id, f.type, t.id, t.type, g.relation FROM edges g "
           "JOIN entities f ON f.id = g.from_id JOIN entities t ON t.id = g.to_id "
           "WHERE g.source = 'musicbrainz_dump' AND ((f.type = 'recording' AND f.owned = 1) OR (t.type = 'recording' AND t.owned = 1))")
    owned = {r[0] for r in db.execute("SELECT id FROM entities WHERE type = 'recording' AND owned = 1")}
    for from_id, from_type, to_id, to_type, relation in db.execute(sql):
        if from_type == "recording" and from_id in owned:
            counts[(to_type, relation)].add((from_id, to_id))
        if to_type == "recording" and to_id in owned:
            counts[(from_type, relation)].add((to_id, from_id))
    return {k: len(v) for k, v in counts.items()}


def dump_counts(extract_dir: Path, gids: set[str], workers: int | None) -> dict[tuple[str, str], int]:
    reader = dump.extracted_reader(extract_dir, on_progress=lambda n, f: log(f"scan pass {n} {int(f * 100)}%")
                                   if int(f * 100) % 25 == 0 else None, workers=workers)
    found = reader.scan({"recording": RowFilter(("id", "gid"), strs=(("gid", frozenset(gids)),))})["recording"]
    ids = frozenset(int(i) for i, _ in found)
    log(f"owned recordings in dump: {len(ids)} of {len(gids)}")
    requests = {}
    for table, (mine, other, _) in LINKS.items():
        columns = ("entity0", "entity1", "link")
        if table == "l_recording_recording":
            requests[table] = RowFilter(columns, ints=(("entity0", ids), ("entity1", ids)), any_=True)
        else:
            requests[table] = RowFilter(columns, ints=((mine, ids),))
    rows = reader.scan(requests)
    link_ids = frozenset(int(lid) for table_rows in rows.values() for _, _, lid in table_rows)
    scanned = reader.scan({"link": RowFilter(("id", "link_type"), ints=(("id", link_ids),)),
                           "link_type": RowFilter(("id", "name"))})
    link_type = {int(i): int(t) for i, t in scanned["link"]}
    names = {int(i): n for i, n in scanned["link_type"]}
    distinct: dict[tuple[str, str], set] = collections.defaultdict(set)
    for table, table_rows in rows.items():
        mine, other, other_type = LINKS[table]
        for e0, e1, lid in table_rows:
            e0, e1 = int(e0), int(e1)
            relation = names.get(link_type.get(int(lid), -1))
            if not relation:
                continue
            if table == "l_recording_recording":
                for rec, oth in ((e0, e1), (e1, e0)):
                    if rec in ids:
                        distinct[(other_type, relation)].add((rec, oth))
                continue
            rec, oth = (e1, e0) if mine == "entity1" else (e0, e1)
            distinct[(other_type, relation)].add((rec, oth))
    return {k: len(v) for k, v in distinct.items()}


def run(archive: Path, store: Path, scratch: Path, *, keep: bool, allow_single_core: bool, workers: int | None) -> dict:
    parallel = dump.parallel_available()
    if not parallel and not allow_single_core and (os.cpu_count() or 1) > 1:
        raise SystemExit("indexed_bzip2 is not installed, so decompression would use one core; "
                         "install requirements.txt or pass --allow-single-core")
    db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    gids = owned_recording_gids(db)
    started = time.time()
    extract_dir = scratch / "extracted"
    try:
        dump.check_schema(dump.read_info(archive))
        log(f"extracting {len(TABLES)} tables on {os.cpu_count()} cores ({'indexed_bzip2' if parallel else 'python bz2'})")
        written = dump.extract_tables(archive, TABLES, extract_dir, parallel=parallel,
                                      on_progress=lambda f: log(f"extract {int(f * 100)}%") if int(f * 100) % 10 == 0 else None)
        extracted_at = time.time()
        theirs = dump_counts(extract_dir, gids, workers)
    finally:
        if not keep:
            shutil.rmtree(extract_dir, ignore_errors=True)
    ours = store_counts(db)
    rows = []
    for key in sorted(set(theirs) | set(ours)):
        d, s = theirs.get(key, 0), ours.get(key, 0)
        rows.append({"other_end": key[0], "relation": key[1], "dump": d, "store": s, "missing_in_store": max(0, d - s)})
    return {"owned_recordings_in_store": len(gids), "extracted_bytes": sum(written.values()),
            "extract_seconds": round(extracted_at - started, 1), "total_seconds": round(time.time() - started, 1),
            "relations": rows, "total_missing_in_store": sum(r["missing_in_store"] for r in rows)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--scratch", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--workers", type=int, default=None, help="scan workers (default: every core)")
    parser.add_argument("--keep-extracted", action="store_true")
    parser.add_argument("--allow-single-core", action="store_true")
    args = parser.parse_args(argv)
    report = run(args.archive, args.store, args.scratch, keep=args.keep_extracted,
                 allow_single_core=args.allow_single_core, workers=args.workers)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        args.out.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
