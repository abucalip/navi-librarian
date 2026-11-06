"""Server V2 Phase 5 exit verification against the knowledge store holding the MusicBrainz slice.

Offline and read-only. No Navidrome, MusicBrainz, Wikidata or other provider traffic. The store is
copied to a temporary folder first (the copy is migrated and read, the original is never opened for
writing; the path cache is written to the copy only) and the copy is deleted afterwards. Output is
aggregate counts and store ids only (no titles, paths or credentials).

    python scripts/server_v2_phase5_exit.py --store ~/discair-mb-test/intelligence.sqlite3 --out phase5_exit.json

Checks (docs/ServerV2.md, Phase 5 exit and kill rule):
  1. each stop explainable: for every owned artist and every built path kind, every stop has at
     least one reason; every reason names its code, readable text, the entity in between (via), the
     library entity it hangs on (anchor) and stored evidence; no stop is the start or repeats
  2. no path without evidence: evidence is credit-grade only (never inferred, never an unmatched
     end), an artist with no evidence gets ``empty`` and no stops, kinds without a builder are
     refused; proven on the real store and on a synthetic store holding inferred and unmatched
     edges next to real ones
  3. latency budget on the real library: cold build time per kind over every owned artist (median,
     95th percentile, slowest) against the per-request time limit, no build cut short by time, and a
     warm read from the path cache
  4. kill rule: the projected precompute time for the whole library stays under a day per kind, and
     no built kind is mostly empty (fewer than half of the owned artists reaching a stop)
"""
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from intelligence.graph.path_coverage import DAY_SECONDS, NONEMPTY_MIN  # noqa: E402
from intelligence.graph.paths import PATH_KINDS, NOT_BUILT, PathLimits, build_path, cached_path  # noqa: E402
from intelligence.store import open_store  # noqa: E402
from intelligence.store import repositories as repo  # noqa: E402

DUMP = "musicbrainz_dump"
WARM_SAMPLE = 100
CHUNK = 10
LIMITS = PathLimits()


def _uncertain(ev: dict) -> bool:
    return ev.get("evidence_class") == "inferred" or ev.get("match_quality") in ("fuzzy_unconfirmed", "unresolved")


def audit_path(path: dict) -> list[str]:
    """Every way a built path breaks the exit rule; empty when it holds."""
    problems: list[str] = []
    start = (path.get("start") or {}).get("id")
    if path["status"] == "empty" and path["stops"]:
        problems.append("empty_with_stops")
    if path["status"] == "ok" and not path["stops"]:
        problems.append("ok_without_stops")
    seen: set[int] = set()
    for stop in path["stops"]:
        entity = stop.get("entity") or {}
        if entity.get("id") in seen:
            problems.append("repeated_stop")
        seen.add(entity.get("id"))
        if entity.get("id") == start:
            problems.append("start_is_a_stop")
        if not stop["reasons"]:
            problems.append("stop_without_reason")
        for reason in stop["reasons"]:
            if not reason.get("code"):
                problems.append("reason_without_code")
            if not reason.get("text"):
                problems.append("reason_text_missing")
            via, anchor = reason.get("via"), reason.get("anchor")
            if not via or not anchor:
                problems.append("reason_without_via_or_anchor")
            elif not via.get("canonical_name") or not anchor.get("canonical_name"):
                problems.append("reason_names_unresolved")  # the text would show a placeholder
            evidence = reason.get("evidence") or []
            if not evidence:
                problems.append("reason_without_evidence")
            for ev in evidence:
                if not ev.get("source"):
                    problems.append("evidence_without_source")
                if _uncertain(ev):
                    problems.append("uncertain_evidence_used")
    return problems


_WORKER_DB = None


def _init_worker(path: str) -> None:
    global _WORKER_DB
    _WORKER_DB = open_store(Path(path))


def _build_chunk(task: tuple[str, list[int]]) -> list[tuple]:
    kind, ids = task
    out = []
    for aid in ids:
        started = time.monotonic()
        path = build_path(_WORKER_DB, aid, kind, limits=LIMITS)
        elapsed = time.monotonic() - started
        out.append((kind, elapsed, audit_path(path), len(path["stops"]),
                    sum(len(s["reasons"]) for s in path["stops"]), path["truncated"]))
    return out


def check_real(db, store_path: Path, workers: int) -> tuple[dict, dict, dict]:
    """Builds every path of every kind on ``workers`` processes (each reads the same migrated copy).

    Timings are per build under that load, so they are conservative against an idle server.
    """
    owned = [r["id"] for r in db.execute("SELECT id FROM entities WHERE type = 'artist' AND owned = 1 ORDER BY id")]
    tasks = [(kind, owned[i:i + CHUNK]) for kind in PATH_KINDS for i in range(0, len(owned), CHUNK)]
    results: dict[str, list[tuple]] = {kind: [] for kind in PATH_KINDS}
    with multiprocessing.Pool(workers, initializer=_init_worker, initargs=(str(store_path),)) as pool:
        for chunk in pool.imap_unordered(_build_chunk, tasks):
            results[chunk[0][0]].extend(chunk) if chunk else None
    explain: dict[str, dict] = {}
    latency: dict[str, dict] = {}
    kill: dict[str, dict] = {}
    for kind in PATH_KINDS:
        rows = results[kind]
        times = [r[1] for r in rows]
        problems: dict[str, int] = {}
        for r in rows:
            for p in r[2]:
                problems[p] = problems.get(p, 0) + 1
        stops, reasons = sum(r[3] for r in rows), sum(r[4] for r in rows)
        nonempty = sum(1 for r in rows if r[3])
        truncated_time = sum(1 for r in rows if r[5] == "time")
        truncated_other = sum(1 for r in rows if r[5] and r[5] != "time")
        explain[kind] = {"owned_artists": len(owned), "artists_with_stops": nonempty, "stops_checked": stops,
                         "reasons_checked": reasons, "problems": problems,
                         "pass": not problems and len(rows) == len(owned) > 0}
        ordered = sorted(times)
        p95 = ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] if ordered else 0.0
        latency[kind] = {"builds": len(times), "workers": workers,
                         "median_seconds": round(statistics.median(times), 4) if times else None,
                         "p95_seconds": round(p95, 4), "slowest_seconds": round(max(times), 4) if times else None,
                         "total_seconds": round(sum(times), 3), "cut_short_by_time": truncated_time,
                         "cut_short_by_rows_or_stops": truncated_other, "time_limit_seconds": LIMITS.max_seconds,
                         "pass": bool(times) and truncated_time == 0 and p95 <= LIMITS.max_seconds}
        share = nonempty / len(owned) if owned else 0.0
        projected = sum(times) / max(len(owned), 1) * 10_000
        kill[kind] = {"share_of_artists_reaching_a_stop": round(share, 3), "mostly_empty": share < NONEMPTY_MIN,
                      "projected_precompute_seconds_for_10000_artists": round(projected, 1),
                      "over_a_day": projected > DAY_SECONDS, "pass": share >= NONEMPTY_MIN and projected <= DAY_SECONDS}
    # Warm read: the second request for the same (start, kind, generation) comes from the cache.
    sample = owned[:WARM_SAMPLE]
    warm: list[float] = []
    hits = 0
    for aid in sample:
        for kind in PATH_KINDS:
            first = cached_path(db, aid, kind, limits=LIMITS)
            started = time.monotonic()
            again = cached_path(db, aid, kind, limits=LIMITS)
            warm.append(time.monotonic() - started)
            hits += 1 if first == again else 0
    latency["warm_cache_read"] = {"reads": len(warm), "identical_to_first_build": hits,
                                  "median_seconds": round(statistics.median(warm), 5) if warm else None,
                                  "slowest_seconds": round(max(warm), 5) if warm else None,
                                  "pass": bool(warm) and hits == len(warm)}
    return explain, latency, kill


def check_refusals(db) -> dict:
    any_artist = db.execute("SELECT id FROM entities WHERE type = 'artist' LIMIT 1").fetchone()
    refused = {}
    for kind in (*NOT_BUILT, "nonsense"):
        try:
            build_path(db, any_artist["id"], kind)
            refused[kind] = False
        except ValueError:
            refused[kind] = True
    return {"refused": refused, "pass": all(refused.values())}


def check_synthetic() -> dict:
    """Inferred and unmatched evidence beside real evidence: only the real one may make a stop."""
    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "s.sqlite3")
        n = [0]

        def ent(kind, name, **kw):
            n[0] += 1
            return repo.upsert_entity(db, kind, name, mbid=f"f0000000-0000-0000-0000-{n[0]:012d}", **kw)[0]

        def edge(a, b, rel, ec="source_explicit", mq="exact_mbid", src=DUMP, **kw):
            return repo.add_edge(db, a, b, rel, source=src, evidence_class=ec, match_quality=mq, **kw)[0]

        def library(name):
            artist, release, rec = ent("artist", name, owned=True), ent("release", name + " LP", owned=True), ent("recording", name + " Song", owned=True)
            edge(release, artist, "credited_to", ec="library_tag", src="navidrome")
            edge(rec, release, "appears_on", ec="library_tag", src="navidrome")
            return artist, rec

        anchor, rec = library("Anchor")
        real, guessed, unmatched = ent("artist", "Real"), ent("artist", "Guessed"), ent("artist", "Unmatched")
        keep, drop_a, drop_b = ent("recording", "Keep"), ent("recording", "DropGuess"), ent("recording", "DropUnmatched")
        for who, target, kw in ((real, keep, {}), (guessed, drop_a, {"ec": "inferred"}), (unmatched, drop_b, {"mq": "unresolved"})):
            edge(who, rec, "instrument")
            edge(who, target, "instrument", **kw)
        lone, lone_rec = library("Lone")
        stray, stray_rec = ent("artist", "Stray"), ent("recording", "StrayOnly")
        edge(stray, lone_rec, "instrument", ec="inferred")
        edge(stray, stray_rec, "instrument")
        db.commit()

        path = build_path(db, anchor, "follow_the_musician")
        names = [s["entity"]["canonical_name"] for s in path["stops"]]
        lone_path = {k: build_path(db, lone, k) for k in PATH_KINDS}
        lone_empty = all(p["status"] == "empty" and p["stops"] == [] for p in lone_path.values())
        problems = audit_path(path) + [x for p in lone_path.values() for x in audit_path(p)]
        db.close()
    ok = names == ["Keep"] and lone_empty and not problems
    return {"stops_from_real_inferred_unmatched": names, "artist_with_only_inferred_evidence_is_empty": lone_empty,
            "problems": problems, "pass": ok}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True, help="the knowledge store (intelligence.sqlite3) holding the slice")
    parser.add_argument("--workers", type=int, default=os.cpu_count() or 1, help="processes (default: all cores)")
    parser.add_argument("--out")
    args = parser.parse_args()
    store = Path(args.store).expanduser()

    result: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "intelligence.sqlite3"
        shutil.copyfile(store, copy)
        state = store.with_name("intelligence.state.sqlite3")
        if state.exists():
            shutil.copyfile(state, Path(tmp) / "intelligence.state.sqlite3")
        db = open_store(copy)
        result["store"] = {t: n for t, n in db.execute("SELECT type, COUNT(*) FROM entities GROUP BY type")}
        explain, latency, kill = check_real(db, copy, args.workers)
        result["1_each_stop_explainable"] = explain
        result["2_no_path_without_evidence"] = {"refusals": check_refusals(db), "synthetic": check_synthetic()}
        result["3_latency"] = latency
        result["4_kill_rule"] = kill
        db.close()
    verdicts = [v["pass"] for v in result["1_each_stop_explainable"].values()]
    verdicts += [result["2_no_path_without_evidence"]["refusals"]["pass"], result["2_no_path_without_evidence"]["synthetic"]["pass"]]
    verdicts += [v["pass"] for v in result["3_latency"].values()]
    verdicts += [v["pass"] for v in result["4_kill_rule"].values()]
    result["exit_passed"] = all(v is True for v in verdicts)
    text = json.dumps(result, indent=2, sort_keys=True, default=str)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0 if result["exit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
