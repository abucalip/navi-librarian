"""Server V2 Phase 0: build golden-set CANDIDATES for owner verification.

Picks about 50 albums across strata (clear single edition, multi-edition release
groups, compilations, multi-disc, no MBID, probable duplicates), then records what
Navidrome says and what MusicBrainz says about each. Nothing here is verified:
the owner confirms or corrects every entry, and only then does it become a golden set.

Read-only. MusicBrainz: at most 2 requests per MBID album (release + release-group
editions) and 1 search per un-tagged album, paced at 1.1 s. The output names the
owner's albums, so write it OUTSIDE the repository (the repository is public).

    python scripts/server_v2_phase0_golden.py --out ../golden-set-phase0/candidates.json
"""

import argparse
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from integrations.navidrome.client import api_call, items  # noqa: E402

UA = {"User-Agent": "Discair/1.0 (personal music discovery; phase 0 golden set)"}
EDITION_WORDS = re.compile(r"\b(deluxe|remaster(ed)?|expanded|anniversary|edition|bonus|special|collector'?s|reissue|version|mono|stereo|legacy|super)\b", re.I)
STRATA = {"clear_single": 8, "multi_edition": 10, "compilation": 5, "multi_disc": 5, "no_mbid": 10, "probable_duplicate": 6, "edition_in_title": 6}


def load_config_env():
    for p in Path(__file__).resolve().parents:
        f = p / "config.env"
        if f.is_file():
            for line in f.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


def nd(method, **params):
    return api_call(method, lambda: (os.environ["NAVIDROME_URL"].rstrip("/"), os.environ["NAVIDROME_USER"], os.environ["NAVIDROME_PASSWORD"]), **params)


def norm(text):
    return re.sub(r"[^a-z0-9]+", "", EDITION_WORDS.sub("", re.sub(r"[\(\[].*?[\)\]]", "", text.lower())))


def mb(client, path, **params):
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


def all_albums():
    out, off = [], 0
    while True:
        page = items(nd("getAlbumList2", type="alphabeticalByName", size=500, offset=off).get("albumList2", {}).get("album"))
        out += page
        if len(page) < 500:
            return out
        off += 500


def pick(rng, pool, n, used):
    pool = [a for a in pool if a["id"] not in used]
    chosen = rng.sample(pool, min(n, len(pool)))
    used.update(a["id"] for a in chosen)
    return chosen


def release_summary(rel):
    return {
        "mbid": rel.get("id"), "title": rel.get("title"), "date": rel.get("date"), "country": rel.get("country"),
        "status": rel.get("status"), "barcode": rel.get("barcode"), "disambiguation": rel.get("disambiguation"),
        "labels": [{"label": (i.get("label") or {}).get("name"), "catno": i.get("catalog-number")} for i in rel.get("label-info") or []],
        "formats": sorted({m.get("format") or "?" for m in rel.get("media") or []}),
        "track_count": sum(m.get("track-count", 0) for m in rel.get("media") or []),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    load_config_env()
    rng = random.Random(args.seed)

    albums = all_albums()
    by_key = {}
    for a in albums:
        by_key.setdefault((norm(a.get("artist", "")), norm(a.get("name", ""))), []).append(a)
    dup_groups = [g for k, g in by_key.items() if len(g) > 1 and k[1]]
    with_mbid = [a for a in albums if a.get("musicBrainzId")]
    pools = {
        "probable_duplicate": [a for g in dup_groups for a in g],
        "compilation": [a for a in albums if a.get("isCompilation")],
        "no_mbid": [a for a in albums if not a.get("musicBrainzId")],
        "edition_in_title": [a for a in with_mbid if EDITION_WORDS.search(a.get("name", "")) or a.get("version")],
        "multi_disc": [a for a in with_mbid if a.get("discTitles")],
    }
    used, picked = set(), []
    for stratum in ("probable_duplicate", "compilation", "multi_disc", "edition_in_title", "no_mbid"):
        for a in pick(rng, pools[stratum], STRATA[stratum], used):
            picked.append((stratum, a))
    rest = [a for a in with_mbid if a["id"] not in used]
    # multi_edition and clear_single are decided after the release-group lookup, so draw extras for both.
    drawn = pick(rng, rest, 40, used)

    entries, mb_requests = [], 0
    with httpx.Client() as client:
        def describe(stratum, a):
            nonlocal mb_requests
            full = nd("getAlbum", id=a["id"]).get("album", {})
            songs = items(full.get("song"))
            entry = {
                "stratum": stratum,
                "navidrome": {
                    "id": a["id"], "artist": a.get("artist"), "title": a.get("name"), "year": a.get("year"), "version": a.get("version"),
                    "release_mbid": a.get("musicBrainzId"), "songCount": a.get("songCount"), "discs": sorted({s.get("discNumber") or 1 for s in songs}),
                    "formats": sorted({s.get("suffix") for s in songs if s.get("suffix")}), "labels": [x.get("name") for x in items(a.get("recordLabels"))],
                    "tracks_with_recording_mbid": sum(bool(s.get("musicBrainzId")) for s in songs), "isCompilation": bool(a.get("isCompilation")),
                },
                "musicbrainz": None,
                "owner_verification": {"status": "unverified", "correct_release_mbid": None, "notes": ""},
            }
            return entry

        for stratum, a in picked:
          try:
            entry = describe(stratum, a)
            if not a.get("musicBrainzId"):
                found = mb(client, "release", query=f'release:"{a.get("name","")}" AND artist:"{a.get("artist","")}"', limit=3)
                mb_requests += 1
                entry["musicbrainz"] = {"search_candidates": [release_summary(r) for r in (found or {}).get("releases", [])[:3]]}
            else:
                rel = mb(client, f"release/{a['musicBrainzId']}", inc="labels+release-groups+media+artist-credits")
                mb_requests += 1
                if rel:
                    rg = (rel.get("release-group") or {}).get("id")
                    editions = (mb(client, "release", **{"release-group": rg, "inc": "labels+media", "limit": 100}) or {}).get("releases", []) if rg else []
                    mb_requests += bool(rg)
                    entry["musicbrainz"] = {"matched_release": release_summary(rel), "release_group_mbid": rg, "edition_count": len(editions),
                                            "editions": [release_summary(r) for r in editions[:15]]}
            entries.append(entry)
          except httpx.HTTPError as exc:
            print("skipped one entry:", type(exc).__name__, file=sys.stderr)

        want_multi, want_single = STRATA["multi_edition"], STRATA["clear_single"]
        multi, single = 0, 0
        for a in drawn:
            if multi >= want_multi and single >= want_single:
                break
            rel = mb(client, f"release/{a['musicBrainzId']}", inc="labels+release-groups+media+artist-credits")
            mb_requests += 1
            rg = ((rel or {}).get("release-group") or {}).get("id")
            if not rg:
                continue
            editions = (mb(client, "release", **{"release-group": rg, "inc": "labels+media", "limit": 100}) or {}).get("releases", [])
            mb_requests += 1
            stratum = "multi_edition" if len(editions) >= 3 else "clear_single" if len(editions) == 1 else None
            if stratum == "multi_edition" and multi < want_multi:
                multi += 1
            elif stratum == "clear_single" and single < want_single:
                single += 1
            else:
                continue
            entry = describe(stratum, a)
            entry["musicbrainz"] = {"matched_release": release_summary(rel), "release_group_mbid": rg, "edition_count": len(editions),
                                    "editions": [release_summary(r) for r in editions[:15]]}
            entries.append(entry)

    report = {"seed": args.seed, "libraries_albums": len(albums), "probable_duplicate_groups_in_library": len(dup_groups),
              "musicbrainz_requests": mb_requests, "counts": {s: sum(e["stratum"] == s for e in entries) for s in STRATA}, "entries": entries}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: report[k] for k in ("libraries_albums", "probable_duplicate_groups_in_library", "musicbrainz_requests", "counts")}, indent=2))


if __name__ == "__main__":
    main()
