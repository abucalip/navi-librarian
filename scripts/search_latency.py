#!/usr/bin/env python3
"""Measure global search latency against the targets in docs/SEARCH_CONTRACT.md section 2.1 (P5).

The script serves only the search router in a throwaway app and times real HTTP/SSE requests against
it, so the route, the owned index and the stream framing are the production code. It reads the
Navidrome, Last.fm and other settings from the environment, like the app. Run it with an isolated
``NAVIDROME_LIBRARIAN_DATA_DIR`` so it never touches the app's own data.

``--network`` adds ``scope=all`` runs, which call the live providers; run those only with the
owner's approval. Output is aggregate timings only: no library names, no credentials.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

# Section 2.1 targets, in milliseconds.
TARGETS_MS = {
    "owned_first_result_p95": 100,
    "owned_done_p95": 3100,
    "external_first_result_p95": 1500,
    "done_p95": 3100,
    "cache_hit_done_p95": 300,
    "index_build": 10_000,
}


def percentile(values: list[float], fraction: float) -> float | None:
    """Nearest-rank percentile; None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(fraction * len(ordered)))
    return ordered[rank - 1]


def validate_isolated_data_dir(raw_path: str | None, root: Path) -> Path:
    """Require an existing, copied data directory outside the source tree."""
    if not raw_path or not raw_path.strip():
        raise ValueError("Set NAVIDROME_LIBRARIAN_DATA_DIR to an isolated copy of the app data directory.")
    path = Path(raw_path).expanduser().resolve()
    source_root = root.resolve()
    if path == source_root or source_root in path.parents:
        raise ValueError("The data directory must be outside the repository.")
    if not path.is_dir():
        raise ValueError("The isolated data directory must already exist.")
    if not (path / "navidrome_discovery.sqlite3").is_file():
        raise ValueError("The isolated directory must contain a copied navidrome_discovery.sqlite3.")
    return path


def summarize(values: list[float]) -> dict[str, Any]:
    return {
        "n": len(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": max(values) if values else None,
    }


def parse_sse(lines) -> Any:
    """Yield ``(event, payload)`` from an iterator of SSE text lines."""
    event, data = None, []
    for line in lines:
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].strip())
        elif not line and event is not None:
            yield event, json.loads("\n".join(data))
            event, data = None, []


def time_search(client, base: str, params: dict[str, str]) -> dict[str, Any]:
    """One streamed search. Times are milliseconds from sending the request."""
    started = time.monotonic()
    first_result = first_external = None
    done_ms = None
    sources: dict[str, str] = {}
    done: dict[str, Any] = {}
    with client.stream("GET", f"{base}/api/search", params=params, headers={"accept": "text/event-stream"}) as response:
        response.raise_for_status()
        for event, payload in parse_sse(response.iter_lines()):
            now = (time.monotonic() - started) * 1000
            if event == "result":
                if first_result is None:
                    first_result = now
                if payload.get("owned") is False and first_external is None:
                    first_external = now
            elif event == "source":
                sources[payload.get("source", "?")] = payload.get("state", "?")
            elif event == "done":
                done = payload
                done_ms = now
    return {
        "first_result_ms": first_result,
        "first_external_ms": first_external,
        "done_ms": done_ms,
        "stream_end_ms": (time.monotonic() - started) * 1000,
        "deadline_hit": bool(done["deadline_hit"]) if "deadline_hit" in done else None,
        "partial": bool(done.get("partial")),
        "sources": sources,
    }


def wait_for_index(index, generation, *, timeout: float) -> tuple[float, str]:
    """Start a forced build and wait until it finishes; return (seconds, state).

    A rebuild keeps serving the last good data, so the state alone cannot show completion: the build
    is done when ``built_at`` changes (or, for a first build, when the state leaves ``building``).
    """
    before = index.view().data
    built_before = before.built_at if before is not None else None
    started = time.monotonic()
    index.ensure(generation, force=True)
    while time.monotonic() - started < timeout:
        view = index.view()
        built_now = view.data.built_at if view.data is not None else None
        if built_now != built_before or (before is None and view.state != "building"):
            return time.monotonic() - started, view.state
        time.sleep(0.05)
    return time.monotonic() - started, "timeout"


def serve(app) -> tuple[Any, str]:
    import uvicorn

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.02)
    return server, f"http://127.0.0.1:{port}"


def pick_queries(data, count: int) -> list[str]:
    """Artist and album names spread across the library, plus a prefix of each."""
    names = [item["name"] for item in data.artists if item.get("name")]
    titles = [item["name"] for item in data.albums if item.get("name")]
    step = max(1, len(names) // max(1, count // 2))
    chosen = names[::step][: count // 2] + titles[:: max(1, len(titles) // max(1, count // 2))][: count - count // 2]
    queries = []
    for text in chosen:
        queries.append(text)
        queries.append(text[: max(3, len(text) // 2)])
    return queries[: count * 2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--builds", type=int, default=3, help="forced index builds to time (the first is cold)")
    parser.add_argument("--queries", type=int, default=20, help="library-derived queries for the owned run")
    parser.add_argument("--network", action="store_true", help="also time scope=all (calls live providers)")
    parser.add_argument("--network-queries", type=int, default=5)
    parser.add_argument(
        "--network-gap", type=float, default=5.0,
        help="seconds to wait between network searches, so the shared provider pacing is idle (one person typing)",
    )
    parser.add_argument("--out", help="write the JSON report to this path")
    args = parser.parse_args(argv)
    if args.builds < 1:
        parser.error("--builds must be at least 1")
    if args.queries < 1:
        parser.error("--queries must be at least 1")
    if args.network_queries < 1:
        parser.error("--network-queries must be at least 1")
    if args.network_gap < 0:
        parser.error("--network-gap cannot be negative")
    try:
        data_dir = validate_isolated_data_dir(os.environ.get("NAVIDROME_LIBRARIAN_DATA_DIR"), ROOT)
    except ValueError as exc:
        parser.error(str(exc))

    sys.path.insert(0, str(ROOT))
    import httpx
    from fastapi import FastAPI

    from app.api import search as search_api
    from app.api.dependencies import get_librarian
    from settings.service import navidrome_generation

    librarian = get_librarian()
    # Build a measurement-only index. The normal route index starts an identity resolver after
    # each build, which writes to the discovery DB and calls MusicBrainz even without --network.
    # This isolated index deliberately has no after_build callback; only --network may call providers.
    if search_api._owned_index is not None:
        parser.error("The search router index was initialized before the measurement harness.")
    generation = navidrome_generation(librarian._discovery_settings_read)
    from discovery import store as discovery_store
    from discovery.identity import load_identities
    from discovery.search.index import OwnedIndex, fetch_song_inventory

    index = OwnedIndex(
        load_library=lambda: search_api._snapshot_lists(
            librarian, navidrome_generation(librarian._discovery_settings_read)
        ),
        load_songs=lambda: fetch_song_inventory(librarian.api_call, librarian.items),
        load_identities=lambda current_generation: load_identities(
            lambda prefix: discovery_store.read_prefix(librarian.DISCOVERY_DB, prefix),
            current_generation,
        ),
        after_build=None,
    )
    search_api._owned_index = index

    report: dict[str, Any] = {"targets_ms": TARGETS_MS}
    builds = []
    for number in range(args.builds):
        seconds, state = wait_for_index(index, generation, timeout=600)
        builds.append({"run": number + 1, "cold": number == 0, "seconds": round(seconds, 2), "state": state})
    view = index.view()
    if view.data is None:
        report["error"] = f"owned index not usable: {view.state}"
        print(json.dumps(report, indent=2))
        return 1
    report["index_builds"] = [
        {
            "run": build["run"],
            "cold": build["cold"],
            "milliseconds": round(build["seconds"] * 1000, 2),
            "state": build["state"],
        }
        for build in builds
    ]
    report["library"] = {
        "songs": view.data.song_count, "artists": len(view.data.artists), "albums": len(view.data.albums),
    }

    app = FastAPI()
    app.include_router(search_api.router)
    server, base = serve(app)
    try:
        with httpx.Client(timeout=30.0) as client:
            queries = pick_queries(view.data, args.queries)
            owned = [time_search(client, base, {"q": q, "scope": "owned"}) for q in queries]
            report["owned"] = {
                "queries": len(queries),
                "first_result_ms": summarize([r["first_result_ms"] for r in owned if r["first_result_ms"] is not None]),
                "done_ms": summarize([r["done_ms"] for r in owned if r["done_ms"] is not None]),
                "no_result": sum(1 for r in owned if r["first_result_ms"] is None),
                "no_done": sum(1 for r in owned if r["done_ms"] is None),
            }
            if args.network:
                sample = queries[: args.network_queries]
                def run_all():
                    results = []
                    for q in sample:
                        results.append(time_search(client, base, {"q": q, "scope": "all"}))
                        time.sleep(args.network_gap)
                    return results

                cold = run_all()
                warm = run_all()
                report["network_miss"] = {
                    "first_external_ms": summarize([r["first_external_ms"] for r in cold if r["first_external_ms"] is not None]),
                    "done_ms": summarize([r["done_ms"] for r in cold if r["done_ms"] is not None]),
                    "no_done": sum(1 for r in cold if r["done_ms"] is None),
                    "deadline_hit": sum(r["deadline_hit"] is True for r in cold),
                    "source_states": sorted({f"{k}:{v}" for r in cold for k, v in r["sources"].items()}),
                }
                report["network_hit"] = {
                    "done_ms": summarize([r["done_ms"] for r in warm if r["done_ms"] is not None]),
                    "no_done": sum(1 for r in warm if r["done_ms"] is None),
                    "source_states": sorted({f"{k}:{v}" for r in warm for k, v in r["sources"].items()}),
                }
    finally:
        server.should_exit = True

    text = json.dumps(report, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
