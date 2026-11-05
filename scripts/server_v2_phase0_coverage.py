"""Server V2 Phase 0: identifier, MusicBrainz relationship and ListenBrainz mapping coverage.

Read-only. Navidrome: getArtists, getAlbumList2, paged search3. MusicBrainz: one
`release` lookup per sampled album, paced at one request per 1.1 s, hard-capped by
--mb-albums. ListenBrainz: paged listens read, hard-capped by --lb-listens.
Output is aggregate counts only (no titles, no credentials).

    python scripts/server_v2_phase0_coverage.py --mb-albums 200 --lb-listens 2000 --out coverage.json

Environment: NAVIDROME_URL/USER/PASSWORD; LISTENBRAINZ_USERNAME (and optionally LISTENBRAINZ_TOKEN).
"""

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.navidrome.client import api_call, items  # noqa: E402

UA = {"User-Agent": "Discair/1.0 (personal music discovery; phase 0 coverage sample)"}
MB_INC = "labels+recordings+artist-credits+release-groups+artist-rels+recording-rels+work-rels+release-group-level-rels+series-rels+recording-level-rels"


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


def nd(method, **params):
    return api_call(method, lambda: (os.environ["NAVIDROME_URL"].rstrip("/"), os.environ["NAVIDROME_USER"], os.environ["NAVIDROME_PASSWORD"]), **params)


def pct(n, d):
    return round(100 * n / d, 1) if d else None


def navidrome_ids():
    artists = [a for idx in nd("getArtists").get("artists", {}).get("index", []) for a in items(idx.get("artist"))]
    albums, off = [], 0
    while True:
        page = items(nd("getAlbumList2", type="alphabeticalByName", size=500, offset=off).get("albumList2", {}).get("album"))
        albums += page
        if len(page) < 500:
            break
        off += 500
    songs, off = [], 0
    while True:
        page = items(nd("search3", query="", artistCount=0, albumCount=0, songCount=500, songOffset=off).get("searchResult3", {}).get("song"))
        songs += page
        if len(page) < 500:
            break
        off += 500
    return artists, albums, songs


def mb_get(client, path, **params):
    for attempt in range(3):
        time.sleep(1.1)
        r = client.get(f"https://musicbrainz.org/ws/2/{path}", params={"fmt": "json", **params}, headers=UA, timeout=30)
        if r.status_code in (429, 503):
            time.sleep(5 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()
    return None


def mb_sample(album_mbids, limit, seed):
    rng = random.Random(seed)
    chosen = rng.sample(album_mbids, min(limit, len(album_mbids)))
    stats = dict.fromkeys(
        ["looked_up", "not_found", "label", "catalog_number", "barcode", "release_group_rels", "series", "tracks", "tracks_with_recording_rels",
         "tracks_with_work", "tracks_with_credit_rels", "albums_with_any_recording_credit", "albums_with_work_link", "albums_with_artist_rels", "tracks_with_isrc"], 0)
    with httpx.Client() as client:
        for mbid in chosen:
            rel = mb_get(client, f"release/{mbid}", inc=MB_INC)
            if rel is None:
                stats["not_found"] += 1
                continue
            stats["looked_up"] += 1
            infos = rel.get("label-info") or []
            stats["label"] += any((i.get("label") or {}).get("id") for i in infos)
            stats["catalog_number"] += any(i.get("catalog-number") for i in infos)
            stats["barcode"] += bool(rel.get("barcode"))
            rg = rel.get("release-group") or {}
            stats["release_group_rels"] += bool(rg.get("relations"))
            stats["series"] += any(r.get("target-type") == "series" for r in (rel.get("relations") or []) + (rg.get("relations") or []))
            stats["albums_with_artist_rels"] += any(r.get("target-type") == "artist" for r in rel.get("relations") or [])
            any_credit = any_work = False
            for medium in rel.get("media") or []:
                for track in medium.get("tracks") or []:
                    rec = track.get("recording") or {}
                    rels = rec.get("relations") or []
                    stats["tracks"] += 1
                    stats["tracks_with_isrc"] += bool(rec.get("isrcs"))
                    stats["tracks_with_recording_rels"] += bool(rels)
                    has_work = any(r.get("target-type") == "work" for r in rels)
                    has_credit = any(r.get("target-type") == "artist" for r in rels)
                    stats["tracks_with_work"] += has_work
                    stats["tracks_with_credit_rels"] += has_credit
                    any_work |= has_work
                    any_credit |= has_credit
            stats["albums_with_any_recording_credit"] += any_credit
            stats["albums_with_work_link"] += any_work
    n, t = stats["looked_up"], stats["tracks"]
    album_keys = ["label", "catalog_number", "barcode", "release_group_rels", "series", "albums_with_any_recording_credit", "albums_with_work_link", "albums_with_artist_rels"]
    track_keys = ["tracks_with_recording_rels", "tracks_with_work", "tracks_with_credit_rels", "tracks_with_isrc"]
    return {
        "sampled": len(chosen), "looked_up": n, "not_found": stats["not_found"], "tracks": t, "requests": len(chosen),
        **{f"{k}_pct_of_albums": pct(stats[k], n) for k in album_keys},
        **{f"{k}_pct_of_tracks": pct(stats[k], t) for k in track_keys},
    }


def lb_mapping(limit):
    user = os.environ.get("LISTENBRAINZ_USERNAME")
    if not user:
        return {"skipped": "LISTENBRAINZ_USERNAME not set"}
    headers = dict(UA)
    if os.environ.get("LISTENBRAINZ_TOKEN"):
        headers["Authorization"] = "Token " + os.environ["LISTENBRAINZ_TOKEN"]
    seen = mapped = rec = rel_ = art = 0
    max_ts, requests, stopped = None, 0, None
    with httpx.Client() as client:
        count = client.get(f"https://api.listenbrainz.org/1/user/{user}/listen-count", headers=headers, timeout=30).json().get("payload", {}).get("count")
        while seen < limit:
            params = {"count": 1000}
            if max_ts:
                params["max_ts"] = max_ts
            r = None
            for attempt in range(3):
                r = client.get(f"https://api.listenbrainz.org/1/user/{user}/listens", params=params, headers=headers, timeout=30)
                requests += 1
                if r.status_code < 500:
                    break
                time.sleep(3 * (attempt + 1))
            if r.status_code >= 400:
                stopped = f"HTTP {r.status_code} after {seen} listens"
                break
            listens = r.json()["payload"]["listens"]
            if not listens:
                break
            for listen in listens:
                meta = listen.get("track_metadata") or {}
                m = meta.get("mbid_mapping") or {}
                seen += 1
                rec += bool(m.get("recording_mbid"))
                rel_ += bool(m.get("release_mbid"))
                art += bool(m.get("artist_mbids"))
                mapped += bool(m.get("recording_mbid"))
            max_ts = listens[-1]["listened_at"]
            time.sleep(0.3)
    return {"stopped_early": stopped, "total_listens": count, "sampled": seen, "requests": requests, "recording_mapped_pct": pct(rec, seen),
            "release_mapped_pct": pct(rel_, seen), "artist_mapped_pct": pct(art, seen)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mb-albums", type=int, default=200)
    ap.add_argument("--lb-listens", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--skip-mb", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    load_config_env()

    artists, albums, songs = navidrome_ids()
    report = {
        "navidrome": {
            "artists": len(artists), "albums": len(albums), "tracks": len(songs),
            "artist_mbid_pct": pct(sum(bool(a.get("musicBrainzId")) for a in artists), len(artists)),
            "album_mbid_pct": pct(sum(bool(a.get("musicBrainzId")) for a in albums), len(albums)),
            "track_recording_mbid_pct": pct(sum(bool(s.get("musicBrainzId")) for s in songs), len(songs)),
            "track_isrc_pct": pct(sum(bool(s.get("isrc")) for s in songs), len(songs)),
            "track_artist_mbid_pct": pct(sum(bool((s.get("artists") or [{}])[0].get("musicBrainzId")) for s in songs), len(songs)),
            "album_with_recordLabels_pct": pct(sum(bool(a.get("recordLabels")) for a in albums), len(albums)),
            "album_with_all_tracks_mbid_pct": None,
        },
    }
    by_album = {}
    for s in songs:
        by_album.setdefault(s.get("albumId"), []).append(bool(s.get("musicBrainzId")))
    report["navidrome"]["album_with_all_tracks_mbid_pct"] = pct(sum(all(v) for v in by_album.values()), len(by_album))
    # NOTE: release-group MBID is not exposed by Navidrome's album payload; recorded as a gap.
    report["navidrome"]["release_group_mbid_available"] = any("musicBrainzReleaseGroupId" in a for a in albums)

    if not args.skip_mb:
        mbids = [a["musicBrainzId"] for a in albums if a.get("musicBrainzId")]
        report["musicbrainz_sample"] = mb_sample(mbids, args.mb_albums, args.seed)
        Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True))
    report["listenbrainz"] = lb_mapping(args.lb_listens)
    Path(args.out).write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
