#!/usr/bin/env python3
"""Request-time provider inventory for step K1 of docs/efficiency.md.

Against a running local instance, read a targets file (owned and unowned artists and albums, made by the
operator and kept outside the repository), request every route the artist and album pages use for each
target once cold and then ``--warm-runs`` times warm, and attribute provider requests to each request by
reading ``/api/diagnostics/runtime`` (M1) before and after it. Requests are strictly sequential, so a
delta belongs to one request; provider pacing and budgets stay on the server. ``--max-provider-requests``
stops the session when the provider total passes the cap.

With ``--data-dir`` (the instance's data directory, read only), the script also lists the cache rows
(``metadata_cache`` and ``discovery_lists``) before and after each request, so a request that called a
provider can be classed as ``never_fetched`` (a row was created), ``expired`` (an existing row was
rewritten) or ``not_cached`` (no row written: a failure, a negative answer kept in memory, or a result the
route does not store).

Only standard library is used. The password is read from the environment variable named by
``--password-env``. The output holds route labels, target indexes and aggregate numbers; no names, keys
or cookies.

Targets file: a JSON list of objects with ``kind`` (``owned_artist``, ``owned_album``, ``unowned_artist``
or ``unowned_album``) and the fields ``artist``, ``artist_key`` and, depending on the kind, ``id``,
``album``, ``year`` and ``mbid``.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from efficiency_baseline import Client, numeric_delta, percentile, read_runtime  # noqa: E402

OUTLET_ROUTES = ("album_reviews",)  # this route calls review outlets (hosts the gate table does not name) and no Navidrome
PAGE_ROUTES = ("artist_page", "album_page")  # the clients open these as an event stream (Accept: text/event-stream)
KINDS = ("owned_artist", "owned_album", "unowned_artist", "unowned_album")
CACHE_TABLES = (
    ("navidrome_metadata_cache.sqlite3", "metadata_cache", "cache_key", "cached_at"),
    ("navidrome_discovery.sqlite3", "discovery_lists", "name", "generated_at"),
)


def _q(value: Any) -> str:
    return urllib.parse.quote(str(value), safe="")


def routes_for(target: dict[str, Any]) -> list[tuple[str, str]]:
    """``(label, path)`` for the routes the artist or album page of ``target`` calls. Labels carry no names."""
    kind = target["kind"]
    if kind not in KINDS:
        raise ValueError(f"unknown target kind {kind!r}")
    artist, artist_key = target["artist"], target.get("artist_key") or target["artist"]
    if kind.endswith("artist"):
        if kind == "owned_artist":
            page = f"/api/artists/{_q(artist)}?id={_q(target['id'])}"
        else:
            page = f"/api/artists/{_q(artist_key)}?name={_q(artist)}"
            if target.get("mbid"):
                page += f"&mbid={_q(target['mbid'])}"
        return [
            ("artist_page", page),
            ("artist_bio", f"/api/artist-bio?artist={_q(artist)}"),
            ("artist_image", f"/api/artist-image?name={_q(artist)}"),
        ]
    album = target["album"]
    pair = f"artist={_q(artist)}&album={_q(album)}"
    if kind == "owned_album":
        page = f"/api/albums/{_q(artist_key)}/{_q(target['id'])}?id={_q(target['id'])}"
    else:
        page = f"/api/albums/{_q(artist_key)}/{_q(target.get('album_key') or album)}?artist={_q(artist)}&name={_q(album)}"
        if target.get("year"):
            page += f"&year={_q(target['year'])}"
        if target.get("mbid"):
            page += f"&mbid={_q(target['mbid'])}"
    links = f"/api/album-links?{pair}" + (f"&mbid={_q(target['mbid'])}" if target.get("mbid") else "")
    routes = [("album_page", page)]
    if kind == "unowned_album":  # the web client asks for these two for an album card or popup that is not owned
        routes += [("album_details", f"/api/album-details?{pair}"), ("album_artwork", f"/api/artwork?{pair}")]
    return routes + [("album_reviews", f"/api/album-reviews?{pair}"), ("album_links", links)]


def provider_use(delta: Any, outlets: bool = False) -> dict[str, Any]:
    """From one request's runtime delta: provider requests, outcomes, seconds and gate wait.

    ``other`` (the Navidrome LAN server) is reported separately and is not a provider. Only the web
    process is read. With ``outlets`` the ``other`` row is the review outlets (a route that makes no
    Navidrome call), so it is reported as the provider ``review_outlets``.
    """
    web = delta.get("web") if isinstance(delta, dict) else None
    web = web if isinstance(web, dict) else {}
    requests = web.get("requests") if isinstance(web.get("requests"), dict) else {}
    gate = web.get("gate") if isinstance(web.get("gate"), dict) else {}
    providers: dict[str, dict[str, Any]] = {}
    for name, row in requests.items():
        if name == "other" or not isinstance(row, dict) or not row.get("count"):
            continue
        providers[name] = {
            "count": row["count"], "seconds": round(row.get("seconds", 0.0), 3),
            "outcomes": dict(row.get("outcomes") or {}),
        }
    other = requests.get("other") if isinstance(requests.get("other"), dict) else {}
    if outlets and other.get("count"):
        providers["review_outlets"] = {
            "count": other["count"], "seconds": round(other.get("seconds", 0.0), 3), "outcomes": dict(other.get("outcomes") or {}),
        }
        other = {}
    return {
        "providers": providers,
        "navidrome": other.get("count", 0),
        "navidrome_seconds": round(other.get("seconds", 0.0), 3),
        "gate_wait_seconds": round(sum(row.get("wait_seconds", 0.0) for row in gate.values() if isinstance(row, dict)), 3),
        "gate_refused": sum(row.get("refused", 0) for row in gate.values() if isinstance(row, dict)),
    }


def read_cache_rows(data_dir: Path | None) -> dict[str, float]:
    """``table:key -> timestamp`` for the cache tables under ``data_dir`` (read only); empty without it."""
    rows: dict[str, float] = {}
    if data_dir is None:
        return rows
    for filename, table, key_column, time_column in CACHE_TABLES:
        path = data_dir / filename
        if not path.exists():
            continue
        connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            for key, stamp in connection.execute(f"SELECT {key_column}, {time_column} FROM {table}"):
                rows[f"{table}:{key}"] = stamp
        except sqlite3.Error:
            pass
        finally:
            connection.close()
    return rows


def classify_miss(before: dict[str, float], after: dict[str, float], outcomes: dict[str, int]) -> tuple[str, list[float]]:
    """The cause of a request that called a provider, and the ages of the rows it rewrote.

    ``never_fetched``: a cache row was created. ``expired``: an existing row was rewritten (its old age is
    the new stamp minus the old one; it was past its time limit). ``failed_not_cached``: no row written and
    some provider outcome was not ``ok``. ``not_cached_ok``: no row written although every provider
    answered ``ok`` (a negative or memory-only answer, or a late answer the route dropped).
    """
    ages = [round(stamp - before[key], 1) for key, stamp in after.items() if key in before and stamp != before[key]]
    if any(key not in before for key in after):
        return "never_fetched", ages
    if ages:
        return "expired", ages
    if any(outcome != "ok" for outcome in outcomes):
        return "failed_not_cached", ages
    return "not_cached_ok", ages


def total_provider_requests(record: dict[str, Any]) -> int:
    return sum(row["count"] for row in record["providers"].values())


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate request records of one route and phase (cold or warm)."""
    count = len(records)
    totals = [total_provider_requests(r) for r in records]
    called = [r for r in records if total_provider_requests(r)]
    per_provider: dict[str, int] = {}
    outcomes: dict[str, int] = {}
    for record in records:
        for name, row in record["providers"].items():
            per_provider[name] = per_provider.get(name, 0) + row["count"]
            for outcome, n in row["outcomes"].items():
                outcomes[outcome] = outcomes.get(outcome, 0) + n
    walls = [r["wall_ms"] for r in records if r["status"]]  # a request that never answered has no wall time
    waits = [sum(row["seconds"] for row in r["providers"].values()) for r in called]
    gate_waits = [r["gate_wait_seconds"] for r in called]
    causes: dict[str, int] = {}
    for record in called:
        if record.get("miss_cause"):
            causes[record["miss_cause"]] = causes.get(record["miss_cause"], 0) + 1
    return {
        "requests": count,
        "statuses": {str(s): sum(1 for r in records if r["status"] == s) for s in sorted({r["status"] for r in records})},
        "provider_requests_per_request": round(sum(totals) / count, 2) if count else None,
        "by_provider": dict(sorted(per_provider.items())),
        "outcomes": dict(sorted(outcomes.items())),
        "navidrome_per_request": round(sum(r["navidrome"] for r in records) / count, 2) if count else None,
        "hit_rate": round(1 - len(called) / count, 3) if count else None,
        "requests_with_provider_call": len(called),
        "provider_seconds_median": round(statistics.median(waits), 3) if waits else None,
        "provider_seconds_p95": round(percentile(waits, 0.95), 3) if waits else None,
        "gate_wait_seconds_median": round(statistics.median(gate_waits), 3) if gate_waits else None,
        "gate_wait_seconds_p95": round(percentile(gate_waits, 0.95), 3) if gate_waits else None,
        "wall_ms_median": round(statistics.median(walls), 1) if walls else None,
        "wall_ms_p95": round(percentile(walls, 0.95), 1) if walls else None,
        "miss_causes": dict(sorted(causes.items())),
    }


def build_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """``kind/route -> {cold, warm}`` over all records."""
    groups: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for record in records:
        phase = "cold" if record["pass"] == 0 else "warm"
        groups.setdefault(f"{record['kind']}/{record['route']}", {"cold": [], "warm": []})[phase].append(record)
    return {name: {phase: summarize(rows) for phase, rows in phases.items()} for name, phases in sorted(groups.items())}


def provider_counts(snapshot: Any) -> dict[str, int]:
    web = snapshot.get("web") if isinstance(snapshot, dict) else None
    requests = web.get("requests") if isinstance(web, dict) else None
    return {k: v.get("count", 0) for k, v in (requests or {}).items() if k != "other" and isinstance(v, dict)}


def settled_runtime(client: Client, interval: float, limit: float, sleep=time.sleep) -> Any:
    """Read the runtime snapshot once the provider counters stop moving (a late answer is not the next request's).

    Two reads ``interval`` seconds apart must show the same provider counts; stops waiting after ``limit`` seconds.
    """
    waited, last = 0.0, read_runtime(client)
    while waited < limit:
        sleep(interval)
        waited += interval
        current = read_runtime(client)
        if provider_counts(current) == provider_counts(last):
            return current
        last = current
    return last


def quiet_window(client: Client, seconds: float, sleep=time.sleep) -> dict[str, Any]:
    """Provider and Navidrome requests the web process makes with no request from this script."""
    before = read_runtime(client)
    sleep(seconds)
    return {"seconds": seconds, **provider_use(numeric_delta(before, read_runtime(client)))}


def run_session(client: Client, targets: list[dict[str, Any]], warm_runs: int, data_dir: Path | None,
                max_provider_requests: int, log=print, settle_interval: float = 0.3, settle_limit: float = 8.0,
                quiet_seconds: float = 0.0, sleep=time.sleep) -> dict[str, Any]:
    plan = [(index, target, routes_for(target)) for index, target in enumerate(targets)]
    records: list[dict[str, Any]] = []
    quiet = {"before": quiet_window(client, quiet_seconds, sleep)} if quiet_seconds else {}
    spent = 0
    stopped = False
    for pass_number in range(warm_runs + 1):
        for index, target, routes in plan:
            for label, path in routes:
                rows_before = read_cache_rows(data_dir)
                before = settled_runtime(client, settle_interval, settle_limit, sleep)
                started_at = time.time()
                try:
                    status, wall_ms, _, _ = client.get(path, "text/event-stream" if label in PAGE_ROUTES else None)
                except OSError:  # a timeout or refused connection is a recorded failure, not the end of the session
                    status, wall_ms = 0, 0.0
                use = provider_use(
                    numeric_delta(before, settled_runtime(client, settle_interval, settle_limit, sleep)), label in OUTLET_ROUTES)
                record = {
                    "pass": pass_number, "target": index, "kind": target["kind"], "route": label, "t": round(started_at, 1),
                    "status": status, "wall_ms": round(wall_ms, 1), **use,
                }
                if total_provider_requests(record) and data_dir:
                    outcomes = {o: n for row in record["providers"].values() for o, n in row["outcomes"].items()}
                    record["miss_cause"], record["rewritten_row_ages_s"] = classify_miss(rows_before, read_cache_rows(data_dir), outcomes)
                records.append(record)
                spent += total_provider_requests(record)
                if spent > max_provider_requests:
                    log(f"Stopped: provider request cap {max_provider_requests} passed.")
                    stopped = True
                    break
            if stopped:
                break
        if stopped:
            break
        log(f"pass {pass_number} done, provider requests so far {spent}")
    if quiet_seconds:
        quiet["after"] = quiet_window(client, min(quiet_seconds, 30.0), sleep)
    return {"stopped_at_cap": stopped, "provider_requests": spent, "quiet": quiet, "records": records}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default="http://127.0.0.1:8091")
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-env", default="NAVI_BASELINE_PASSWORD")
    parser.add_argument("--targets", type=Path, required=True, help="JSON targets file (keep it outside the repository)")
    parser.add_argument("--warm-runs", type=int, default=5)
    parser.add_argument("--data-dir", type=Path, default=None, help="instance data directory, read only, for miss causes")
    parser.add_argument("--max-provider-requests", type=int, default=2000)
    parser.add_argument("--quiet-seconds", type=float, default=60.0, help="idle window before (and half of it after) the session")
    parser.add_argument("--out", type=Path, required=True, help="JSON output file")
    args = parser.parse_args(argv)
    if args.warm_runs < 1:
        parser.error("--warm-runs must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    password = os.environ.get(args.password_env)
    if not password:
        raise SystemExit(f"Set {args.password_env} to the app password (it is not printed).")
    targets = json.loads(args.targets.read_text(encoding="utf-8"))
    client = Client(args.base_url)
    client.login(args.username, password)
    result = run_session(client, targets, args.warm_runs, args.data_dir, args.max_provider_requests,
                         quiet_seconds=args.quiet_seconds)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "warm_runs": args.warm_runs,
        "targets": [{"index": i, "kind": t["kind"]} for i, t in enumerate(targets)],
        "stopped_at_cap": result["stopped_at_cap"],
        "provider_requests": result["provider_requests"],
        "quiet_windows": result["quiet"],
        "summary": build_summary(result["records"]),
        "records": result["records"],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
