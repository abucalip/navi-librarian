"""Server V2 Phase 0: read-only Navidrome field and capability probe.

Makes only read calls (ping, getOpenSubsonicExtensions, getAlbumList2, getAlbum,
getSong, getSonicSimilarTracks, findSonicPath) against the configured Navidrome.
Prints aggregate counts only: no credentials, no track or album titles.

    python scripts/server_v2_phase0_probe.py --albums 100 --out probe.json

Reads NAVIDROME_URL, NAVIDROME_USER and NAVIDROME_PASSWORD from the environment.
"""

import argparse
import json
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.navidrome.client import api_call, items  # noqa: E402


def load_config_env(path=None):
    """Load KEY=VALUE lines from the local config.env (walking up from this file) without overriding the environment."""
    candidates = [Path(path)] if path else [p / "config.env" for p in Path(__file__).resolve().parents]
    for candidate in candidates:
        if candidate.is_file():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
            return str(candidate.name)
    return None


def call(method, **params):
    return api_call(
        method,
        lambda: (os.environ["NAVIDROME_URL"].rstrip("/"), os.environ["NAVIDROME_USER"], os.environ["NAVIDROME_PASSWORD"]),
        **params,
    )


def populated(value):
    return value not in (None, "", [], {}, 0)


def field_matrix(records):
    """Return {field: {"returned": n, "populated": n}} over a list of dict records."""
    returned, filled = Counter(), Counter()
    for record in records:
        for key, value in record.items():
            returned[key] += 1
            if populated(value):
                filled[key] += 1
    total = len(records)
    return {
        key: {"returned_pct": round(100 * returned[key] / total, 1), "populated_pct": round(100 * filled[key] / total, 1)}
        for key in sorted(returned)
    } if total else {}


def try_call(method, **params):
    try:
        return {"ok": True, "root": call(method, **params)}
    except Exception as exc:  # noqa: BLE001 - record the failure kind only; request URLs carry auth tokens
        status = getattr(getattr(exc, "response", None), "status_code", None)
        return {"ok": False, "error": type(exc).__name__ + (f" HTTP {status}" if status else "")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--albums", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    load_config_env()
    report = {}

    ping = call("ping")
    report["server"] = {k: ping.get(k) for k in ("version", "type", "serverVersion", "openSubsonic")}

    ext = try_call("getOpenSubsonicExtensions")
    report["extensions"] = (
        [{"name": e.get("name"), "versions": e.get("versions")} for e in items(ext["root"].get("openSubsonicExtensions"))]
        if ext["ok"] else ext
    )

    # Whole-library album listing in pages, then a seeded random sample.
    all_albums, offset = [], 0
    while True:
        page = items(call("getAlbumList2", type="alphabeticalByName", size=500, offset=offset).get("albumList2", {}).get("album"))
        all_albums.extend(page)
        if len(page) < 500:
            break
        offset += 500
    report["library"] = {"albums": len(all_albums)}
    report["album_list_fields"] = field_matrix(all_albums)

    rng = random.Random(args.seed)
    sample = rng.sample(all_albums, min(args.albums, len(all_albums)))
    full_albums, songs = [], []
    for stub in sample:
        album = call("getAlbum", id=stub["id"]).get("album", {})
        full_albums.append({k: v for k, v in album.items() if k != "song"})
        songs.extend(items(album.get("song")))
    report["sample"] = {"albums": len(full_albums), "tracks": len(songs), "seed": args.seed}
    report["getAlbum_album_fields"] = field_matrix(full_albums)
    report["getAlbum_song_fields"] = field_matrix(songs)

    # Nested OpenSubsonic structures on songs (artists, contributors, replayGain, ...).
    nested = defaultdict(Counter)
    for song in songs:
        for key in ("artists", "albumArtists", "contributors", "genres", "moods", "replayGain", "explicitStatus", "isrc", "musicBrainzId"):
            if populated(song.get(key)):
                nested[key]["populated"] += 1
    report["song_nested_populated"] = {k: v["populated"] for k, v in nested.items()}
    report["formats"] = dict(Counter(str(s.get("suffix")) for s in songs).most_common())

    # Sonic endpoints: record working vs not.
    song_id = songs[0]["id"] if songs else None
    report["getSonicSimilarTracks"] = (
        {k: (v if k != "root" else {"keys": sorted(v)}) for k, v in try_call("getSonicSimilarTracks", id=song_id, count=5).items()}
        if song_id else "no sample song"
    )
    if len(songs) > 1:
        r = try_call("findSonicPath", startSongId=songs[0]["id"], endSongId=songs[1]["id"], count=5)
        report["findSonicPath"] = {k: (v if k != "root" else {"keys": sorted(v)}) for k, v in r.items()}

    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps({k: report[k] for k in ("server", "library", "sample")}, indent=2))


if __name__ == "__main__":
    main()
