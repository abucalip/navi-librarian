"""Artwork probe (docs/artwork.md, slice 0): what does the Cover Art Archive hold per owned release group?

Measurement only. The intelligence store is opened read-only; nothing is written except the --out JSON
(keep it outside the repo until a decision is recorded). Provider traffic is paced at one request per
second per host and is bounded by --groups and --release-cap.

    python scripts/artwork_probe.py --store ~/discair-mb-test/intelligence.sqlite3 --out probe.json

Steps per group: owned release -> release group (one MusicBrainz lookup; no batch form exists for
resolving the group of a single release), release group -> all releases (one MusicBrainz browse, 100 per
page), then one CAA index fetch per release (the CAA has no batch or group-wide form that merges releases).
Somethin' Else (release 1edd139d-4779-4057-8e12-13c783674f0d) is always probed first.
Image bytes are never downloaded; only index JSON is read.
"""
from __future__ import annotations

import argparse
import json
import random
import sqlite3
import statistics
import time
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = "Discair/1.0 (personal music discovery)"
FIRST_RELEASE = "1edd139d-4779-4057-8e12-13c783674f0d"
MB = "https://musicbrainz.org/ws/2"
CAA = "https://coverartarchive.org"
PACE_SECONDS = 1.0
_last: dict[str, float] = {}


def _get(url: str, host: str) -> tuple[int, dict | None]:
    wait = PACE_SECONDS - (time.monotonic() - _last.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last[host] = time.monotonic()
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        return exc.code, None
    except (URLError, TimeoutError, json.JSONDecodeError):
        return 0, None


def owned_releases(store: Path, sample: int, seed: int) -> list[str]:
    db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    ids = [r[0] for r in db.execute("SELECT mbid FROM entities WHERE type='release' AND owned=1 AND mbid IS NOT NULL")]
    db.close()
    ids = [i for i in ids if i != FIRST_RELEASE]
    random.Random(seed).shuffle(ids)
    return [FIRST_RELEASE] + ids[: sample * 3]  # spare candidates: several owned releases share a group


def group_of(release: str) -> tuple[str | None, int]:
    status, data = _get(f"{MB}/release/{release}?inc=release-groups&fmt=json", "mb")
    return ((data or {}).get("release-group") or {}).get("id"), status


def releases_of(rgid: str) -> tuple[list[dict], int, int]:
    out, offset = [], 0
    while True:
        status, data = _get(f"{MB}/release?release-group={rgid}&limit=100&offset={offset}&fmt=json", "mb")
        if data is None:
            return out, status, len(out)
        out += data.get("releases", [])
        offset += 100
        if offset >= data.get("release-count", 0):
            return out, status, data.get("release-count", len(out))


def index_of(release: str) -> tuple[str, list[dict]]:
    status, data = _get(f"{CAA}/release/{release}", "caa")
    if status == 200 and data is not None:
        return "ok", data.get("images", [])
    return ("empty" if status == 404 else f"error_{status}"), []


def probe_group(rgid: str, release_cap: int) -> dict:
    started = time.monotonic()
    releases, status, total = releases_of(rgid)
    row = {"rgid": rgid, "mb_status": status, "releases_total": total, "releases_fetched": 0,
           "releases_with_images": 0, "releases_empty": 0, "release_errors": 0, "images": 0,
           "unique_images": 0, "types": Counter(), "approved": 0, "comments": 0, "truncated": total > release_cap}
    seen: set[int] = set()
    for rel in releases[:release_cap]:
        state, images = index_of(rel["id"])
        row["releases_fetched"] += 1
        if state == "ok" and images:
            row["releases_with_images"] += 1
        elif state == "empty":
            row["releases_empty"] += 1
        elif state != "ok":
            row["release_errors"] += 1
        for img in images:
            row["images"] += 1
            if img["id"] in seen:
                continue
            seen.add(img["id"])
            row["unique_images"] += 1
            row["types"].update(img.get("types") or ["(none)"])
            row["approved"] += bool(img.get("approved"))
            row["comments"] += bool(img.get("comment"))
    row["types"] = dict(row["types"])
    row["seconds"] = round(time.monotonic() - started, 1)
    return row


def summarize(rows: list[dict]) -> dict:
    def stats(key: str) -> dict:
        vals = sorted(r[key] for r in rows)
        if not vals:
            return {}
        return {"min": vals[0], "median": statistics.median(vals),
                "p90": vals[min(len(vals) - 1, int(0.9 * len(vals)))], "max": vals[-1]}

    types: Counter = Counter()
    for r in rows:
        types.update(r["types"])
    fetched = sum(r["releases_fetched"] for r in rows)
    return {
        "groups": len(rows),
        "groups_with_any_image": sum(1 for r in rows if r["unique_images"]),
        "groups_with_non_front": sum(1 for r in rows if any(t != "Front" for t in r["types"])),
        "groups_truncated_by_probe_cap": sum(1 for r in rows if r["truncated"]),
        "releases_per_group": stats("releases_total"),
        "unique_images_per_group": stats("unique_images"),
        "seconds_per_group": stats("seconds"),
        "type_mix_unique_images": dict(types.most_common()),
        "release_index_empty_rate": round(sum(r["releases_empty"] for r in rows) / fetched, 3) if fetched else None,
        "release_index_error_rate": round(sum(r["release_errors"] for r in rows) / fetched, 3) if fetched else None,
        "mb_failures": sum(1 for r in rows if r["mb_status"] != 200),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--groups", type=int, default=30)
    ap.add_argument("--release-cap", type=int, default=60, help="probe-only bound on CAA fetches per group")
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()

    rows: list[dict] = []
    seen: set[str] = set()
    for release in owned_releases(args.store, args.groups, args.seed):
        if len(rows) >= args.groups:
            break
        rgid, status = group_of(release)
        if rgid is None or rgid in seen:
            print(f"skip {release} ({'duplicate group' if rgid else f'group lookup status {status}'})")
            continue
        seen.add(rgid)
        row = probe_group(rgid, args.release_cap)
        row["owned_release"] = release
        rows.append(row)
        print(f"[{len(rows)}/{args.groups}] {rgid} releases={row['releases_total']} images={row['unique_images']} "
              f"types={row['types']} {row['seconds']}s", flush=True)
        args.out.write_text(json.dumps({"summary": summarize(rows), "groups": rows}, indent=2))
    print(json.dumps(summarize(rows), indent=2))


if __name__ == "__main__":
    main()
