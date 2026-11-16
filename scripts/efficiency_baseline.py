#!/usr/bin/env python3
"""Repeatable request timing for the Phase P steps of docs/efficiency.md (step M2).

Against a running instance, the script logs in, reads ``/api/diagnostics/runtime`` (M1), requests a fixed
list of routes ``--runs`` times each, records the wall time and the ``Server-Timing`` duration of every
response, reads the diagnostics route again, and writes one JSON file and a short Markdown table.

Attribution (M2 follow-up): each route is run as its own block, with a runtime snapshot before and after the
block, so ``per_route_runtime`` shows the outbound requests (by provider; ``other`` is the Navidrome LAN
server) that each route caused. Routes run one after another, not interleaved, so the delta belongs to one
route. Background threads in the web process that call a provider or Navidrome during a block are counted
too; compare with a no-request window if that matters.

Only standard library is used. The password is read from the environment variable named by
``--password-env`` and is never printed or written. Output contains route labels and aggregate numbers
only: no artist or album keys, no paths with keys, no library names, no cookies.

Warm-cache by default: the script does not warm anything. Run it after the caches are warm; any provider
request caused by a cold route appears in the ``runtime`` delta, so check that delta before quoting a
number. Results from a development machine are indicative only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8090"
SESSION_COOKIE = "navil_session"
TIMEOUT_SECONDS = 60
SERVER_TIMING_RE = re.compile(r"dur=([0-9.]+)")


def percentile(values: list[float], fraction: float) -> float | None:
    """Nearest-rank percentile; None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def parse_server_timing(header: str | None) -> float | None:
    """Return the ``dur`` value of the ``app`` metric in a Server-Timing header, in milliseconds."""
    if not header:
        return None
    match = SERVER_TIMING_RE.search(header)
    return float(match.group(1)) if match else None


def zero_like(value: Any) -> Any:
    """A snapshot shaped like ``value`` with every numeric leaf set to zero (a counter not yet seen)."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return 0
    if isinstance(value, dict):
        return {key: zero_like(item) for key, item in value.items()}
    return None


def numeric_delta(before: Any, after: Any) -> Any:
    """Recursively subtract numeric leaves of two snapshots.

    A key that appears only in ``after`` counts from zero, so a provider first seen during a block is kept.
    A key that appears only in ``before`` is skipped.
    """
    if isinstance(before, bool) or isinstance(after, bool):
        return None
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return after - before
    if isinstance(before, dict) and isinstance(after, dict):
        out = {}
        for key in after:
            base = before[key] if key in before else zero_like(after[key])
            value = numeric_delta(base, after[key])
            if value is not None and value != {}:
                out[key] = value
        return out
    return None


def summarize(samples: list[tuple[float, float | None, int]]) -> dict[str, Any]:
    """Aggregate ``(wall_ms, server_ms, status)`` samples for one route label."""
    wall = [s[0] for s in samples]
    server = [s[1] for s in samples if s[1] is not None]
    statuses: dict[str, int] = {}
    for _, _, status in samples:
        statuses[str(status)] = statuses.get(str(status), 0) + 1
    return {
        "count": len(samples),
        "statuses": statuses,
        "wall_median_ms": round(statistics.median(wall), 1) if wall else None,
        "wall_p95_ms": _round(percentile(wall, 0.95)),
        "server_median_ms": round(statistics.median(server), 1) if server else None,
        "server_p95_ms": _round(percentile(server, 0.95)),
    }


def _round(value: float | None) -> float | None:
    return None if value is None else round(value, 1)


def build_routes(artist_key: str, album_key: str, artist_id: str, artist_name: str) -> list[tuple[str, str]]:
    """Fixed route list as ``(label, path_with_query)``. Labels carry no keys."""
    artist = urllib.parse.quote(artist_key, safe="")
    artist_id_q = urllib.parse.quote(artist_id, safe="")
    artist_name_q = urllib.parse.quote(artist_name, safe="")
    album = urllib.parse.quote(album_key, safe="")
    return [
        ("library_artists", "/api/library/artists?limit=50"),
        ("library_albums", "/api/library/albums?limit=50"),
        ("artist_page", f"/api/artists/{artist_name_q}?id={artist_id_q}"),
        ("album_page", f"/api/albums/{artist}/{album}?id={album}"),
        ("search", "/api/search?q=baseline&scope=owned"),
        ("knowledge_connections", f"/api/knowledge/connections?navidrome_id={album}&type=release_group"),
        ("knowledge_paths_album_gaps", f"/api/knowledge/paths?kind=album_gaps&navidrome_id={album}&type=release_group"),
    ]


class Client:
    """Minimal authenticated JSON client over urllib (no redirects followed, no body logging)."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.cookie: str | None = None

    def login(self, username: str, password: str) -> None:
        body = json.dumps({"username": username, "password": password}).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + "/api/auth/login", data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                cookie_header = response.headers.get("Set-Cookie", "")
        except urllib.error.HTTPError as error:
            raise SystemExit(f"Login failed with HTTP {error.code}.") from None
        match = re.search(rf"{SESSION_COOKIE}=([^;]+)", cookie_header)
        if not match:
            raise SystemExit("Login did not return a session cookie.")
        self.cookie = f"{SESSION_COOKIE}={match.group(1)}"

    def get(self, path: str) -> tuple[int, float, str | None, bytes]:
        request = urllib.request.Request(self.base_url + path, headers={"Cookie": self.cookie or ""})
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                body = response.read()
                status = response.status
                timing = response.headers.get("Server-Timing")
        except urllib.error.HTTPError as error:
            body = error.read()
            status = error.code
            timing = error.headers.get("Server-Timing")
        wall_ms = (time.perf_counter() - started) * 1000
        return status, wall_ms, timing, body


def read_runtime(client: Client) -> Any:
    status, _, _, body = client.get("/api/diagnostics/runtime")
    if status != 200:
        raise SystemExit(f"Diagnostics route returned HTTP {status}; cannot take a runtime snapshot.")
    return json.loads(body)


def run(args: argparse.Namespace) -> dict[str, Any]:
    password = os.environ.get(args.password_env)
    if not password:
        raise SystemExit(f"Set {args.password_env} to the app password (it is not printed).")
    client = Client(args.base_url)
    client.login(args.username, password)

    routes = build_routes(args.artist_key, args.album_key, args.artist_id, args.artist_name)
    runtime_before = read_runtime(client)
    samples: dict[str, list[tuple[float, float | None, int]]] = {label: [] for label, _ in routes}
    per_route_runtime: dict[str, Any] = {}
    for label, path in routes:
        route_before = read_runtime(client)
        for _ in range(args.runs):
            status, wall_ms, timing, _ = client.get(path)
            samples[label].append((wall_ms, parse_server_timing(timing), status))
        per_route_runtime[label] = numeric_delta(route_before, read_runtime(client))
    runtime_after = read_runtime(client)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs": args.runs,
        "routes": {label: summarize(samples[label]) for label, _ in routes},
        "per_route_runtime": per_route_runtime,
        "runtime_delta": numeric_delta(runtime_before, runtime_after),
    }


def outbound_per_run(delta: Any, runs: int) -> dict[str, float]:
    """Web-process requests per run by provider from one route's runtime delta (``other`` is the Navidrome LAN server).

    The diagnostics snapshot nests the counters under ``web`` (and ``worker``); only ``web`` is read here,
    because the worker snapshot is saved every few minutes and is not per route.
    """
    web = delta.get("web") if isinstance(delta, dict) else None
    requests = web.get("requests") if isinstance(web, dict) else None
    if not isinstance(requests, dict):
        return {}
    return {
        provider: round(row["count"] / runs, 2)
        for provider, row in sorted(requests.items())
        if isinstance(row, dict) and row.get("count")
    }


def markdown_table(result: dict[str, Any]) -> str:
    lines = [
        "| Route | Count | Statuses | Wall median ms | Wall p95 ms | Server median ms | Server p95 ms | Outbound per run |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, stats in result["routes"].items():
        statuses = ", ".join(f"{code}×{n}" for code, n in sorted(stats["statuses"].items()))
        outbound = outbound_per_run(result.get("per_route_runtime", {}).get(label), result["runs"])
        outbound_text = ", ".join(f"{k} {v}" for k, v in outbound.items()) or "none"
        lines.append(
            f"| {label} | {stats['count']} | {statuses} | {stats['wall_median_ms']} | {stats['wall_p95_ms']} "
            f"| {stats['server_median_ms']} | {stats['server_p95_ms']} | {outbound_text} |"
        )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password-env", default="NAVI_BASELINE_PASSWORD")
    parser.add_argument("--artist-key", required=True, help="artist key used by /api/artists/{key}")
    parser.add_argument("--artist-name", required=True, help="artist name; the artist route matches on its normalized form")
    parser.add_argument("--artist-id", required=True, help="artist id (the id query parameter of /api/artists/{key})")
    parser.add_argument("--album-key", required=True, help="album navidrome id used by the album routes")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--out", type=Path, required=True, help="JSON output file")
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(markdown_table(result))
    print(f"\nWrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
