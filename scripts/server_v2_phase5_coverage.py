"""Server V2 Phase 5 coverage: which discovery path kinds have enough evidence on the owner's library.

Offline and read-only. No Navidrome, MusicBrainz or other provider traffic. The store is copied to a
temporary folder first (the copy is migrated and read; the original is never opened for writing) and
the copy is deleted afterwards. Output is aggregate counts only (no titles, paths or credentials).

    python scripts/server_v2_phase5_coverage.py --store ~/discair-mb-test/intelligence.sqlite3 --out phase5_coverage.json

For each path kind (docs/ServerV2.md, Phase 5 item 4) it reports how many owned artists reach at least
one and at least three evidence-backed stops, the time taken and the projected precompute time, and
applies the Phase 5 kill rule: a kind that is mostly empty or needs more than a day is dropped. A kind
whose inputs are absent from the store (for example before the slice is re-imported with the
forward-compatible context) is reported as ``not_measurable``, never as dropped.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intelligence.graph.path_coverage import KINDS, Criteria, measure  # noqa: E402
from intelligence.store import open_store  # noqa: E402


def run(store: Path, criteria: Criteria, kinds: tuple[str, ...] = KINDS) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "intelligence.sqlite3"
        shutil.copyfile(store, copy)
        db = open_store(copy)  # migrates the copy to the current schema
        try:
            return measure(db, criteria, kinds)
        finally:
            db.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True, help="the knowledge store (intelligence.sqlite3) holding the slice")
    parser.add_argument("--min-stops", type=int, default=Criteria.min_stops)
    parser.add_argument("--assumed-anchors", type=int, default=Criteria.assumed_anchors,
                        help="owned artists to project the precompute time to")
    parser.add_argument("--kinds", nargs="+", choices=KINDS, default=list(KINDS), help="measure only these path kinds")
    parser.add_argument("--out")
    args = parser.parse_args()
    report = run(Path(args.store).expanduser(), Criteria(min_stops=args.min_stops, assumed_anchors=args.assumed_anchors),
                 tuple(args.kinds))
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
