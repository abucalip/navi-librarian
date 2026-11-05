"""Server V2 Phase 1 exit verification against the owner's live Navidrome.

Read-only. Navidrome: getAlbumList2 (paged) and getAlbum per album. No MusicBrainz or other
provider traffic. The intelligence store is a temporary file that is deleted afterwards.
Output is aggregate counts and timings only (no titles, paths or credentials).

    python scripts/server_v2_phase1_exit.py --sample 200 --out phase1_exit.json

Checks (docs/ServerV2.md, Phase 1 exit):
  1. a bounded sample is fully resolved or explicitly unresolved, and re-ingest changes nothing
  2. the health report is identical across two independent fetches of the real library
  3. a failing provider search leaves stored rows and the health body unchanged
Environment: NAVIDROME_URL/USER/PASSWORD (or the local config.env).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_v2_phase0_coverage import load_config_env, nd  # noqa: E402

from integrations.navidrome.client import items  # noqa: E402
from intelligence.api import build_health_body  # noqa: E402
from intelligence.health import build_report  # noqa: E402
from intelligence.ingest.navidrome import ingest_album, normalize_album  # noqa: E402
from intelligence.resolution.unresolved import count_unresolved  # noqa: E402
from intelligence.store import open_store  # noqa: E402

TABLES = ("observations", "entities", "edges", "unresolved", "aliases")


def fetch_albums(limit: int | None = None) -> list[dict]:
    ids, off = [], 0
    while True:
        page = items(nd("getAlbumList2", type="alphabeticalByName", size=500, offset=off).get("albumList2", {}).get("album"))
        ids += [a["id"] for a in page]
        if len(page) < 500:
            break
        off += 500
    if limit:
        ids = ids[:limit]
    return [nd("getAlbum", id=i)["album"] for i in ids]


def row_counts(db) -> dict[str, int]:
    out = {}
    for table in TABLES:
        try:
            out[table] = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except Exception:  # table name differs in this schema; report it as absent
            out[table] = -1
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--out")
    args = parser.parse_args()
    load_config_env()
    result: dict = {}

    t0 = time.time()
    first = fetch_albums()
    result["library"] = {"albums": len(first), "fetch_seconds": round(time.time() - t0, 1)}

    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "exit.sqlite3")

        # 1. bounded sample: resolved or explicitly unresolved, idempotent
        sample = random.Random(args.seed).sample(first, min(args.sample, len(first)))
        items_expected = sum(1 + len(normalize_album(a).tracks) for a in sample)  # releases + recordings
        t1 = time.time()
        results = [ingest_album(db, album, now=1.0, search=None) for album in sample]
        releases_resolved = sum(r.release_entity_id is not None for r in results)
        recordings_resolved = sum(r.recordings_resolved for r in results)
        queued = sum(r.unresolved for r in results)
        deferred = sum(r.deferred for r in results)
        ingest_seconds = round(time.time() - t1, 2)
        after_first = row_counts(db)
        unresolved_open = count_unresolved(db)
        for album in sample:
            ingest_album(db, album, now=2.0, search=None)
        after_second = row_counts(db)
        result["sample"] = {
            "albums": len(sample), "items_expected": items_expected,
            "unresolved_open": unresolved_open,
            "releases_resolved": releases_resolved, "recordings_resolved": recordings_resolved,
            "queued_unresolved": queued, "deferred": deferred,
            "every_item_accounted_for": releases_resolved + recordings_resolved + queued + deferred == items_expected, "rows_after_first": after_first,
            "reingest_changed_nothing": after_first == after_second,
            "ingest_seconds": ingest_seconds,
        }

        # 2. health report reproducible across two independent fetches
        report_a = build_report(normalize_album(a) for a in first)
        t2 = time.time()
        second = fetch_albums()
        report_b = build_report(normalize_album(a) for a in second)
        body_a = json.dumps(report_a.as_dict(), sort_keys=True)
        body_b = json.dumps(report_b.as_dict(), sort_keys=True)
        result["health"] = {
            "albums_checked": report_a.albums_checked, "counts": report_a.counts,
            "not_checked": list(report_a.not_checked),
            "identical_across_two_fetches": body_a == body_b,
            "same_from_shuffled_input": body_a == json.dumps(
                build_report(normalize_album(a) for a in random.Random(9).sample(first, len(first))).as_dict(), sort_keys=True),
            "second_fetch_seconds": round(time.time() - t2, 1),
        }

        # 3. provider failure: stored rows and the health body stay the same
        def failing_search(ref):
            raise TimeoutError("simulated provider outage")

        body_before = json.dumps(build_health_body(db, report_a), sort_keys=True)
        rows_before = row_counts(db)
        # items already resolved or queued are found first; use fresh store state with new refs
        fresh = [dict(a, id=f"sim-{a['id']}", song=[dict(s, id=f"sim-{s['id']}", musicBrainzId=None) for s in a.get("song", [])],
                      musicBrainzId=None) for a in sample[:20]]
        for album in fresh:
            ingest_album(db, album, now=3.0, search=failing_search)
        rows_after = row_counts(db)
        body_after = json.dumps(build_health_body(db, report_a), sort_keys=True)
        result["provider_failure"] = {
            "simulated_albums": len(fresh),
            "health_body_unchanged": body_before == body_after,
            "rows_before": rows_before, "rows_after": rows_after,
            "unresolved_rows_added": rows_after["unresolved"] - rows_before["unresolved"],
        }
        db.close()

    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
