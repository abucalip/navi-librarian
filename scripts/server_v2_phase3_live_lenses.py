"""Server V2 Phase 3 live run of blind spots, series, hidden canon and anniversaries.

Owner-approved provider traffic (2026-11-05), bounded: Navidrome reads, then MusicBrainz and
ListenBrainz requests for a small sample of the owner's artists (``--artists``, default 12), paced
1.1 s / 0.5 s and counted. The intelligence store is a temporary file deleted afterwards, so the
owner's real accept/dismiss history is not read or changed. Output is aggregate counts only
(no titles, paths or credentials).

    python scripts/server_v2_phase3_live_lenses.py --artists 12 --out phase3_live_lenses.json

How each lens is fed (no guessing):
  * owned artists/releases: Navidrome getAlbum for the sampled artists' albums, ingested with no search
  * owned release groups: MusicBrainz release lookup per owned release (``sweep_owned_releases``)
  * blind spots: studio discography + ListenBrainz top release groups per sampled artist
  * series: series ids discovered from the owned groups' own MusicBrainz series relations
  * hidden canon: ListenBrainz top release groups of the sampled artists as the "world" pool, with the
    owner's top Navidrome genres; a candidate's genres are its artist's library genres (a proxy)
  * anniversaries: first-release dates from the discography documents for owned groups, and the
    sampled artists' MusicBrainz life-span (window 30 days around today)
Each card list goes through ``score_lens`` with this temporary store's outcomes (none), so the verdict
is ``insufficient_evidence`` unless the gates fail; duplicates, owned leaks and diversity are measured.
Environment: NAVIDROME_URL/USER/PASSWORD (or the local config.env).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from collections import Counter
from datetime import date
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_v2_phase0_coverage import load_config_env, nd  # noqa: E402

from integrations.navidrome.client import items  # noqa: E402
from intelligence.editions import sweep_owned_releases  # noqa: E402
from intelligence.ingest.navidrome import ingest_album  # noqa: E402
from intelligence.insights import (  # noqa: E402
    AnniversaryConfig, BlindSpotsConfig, CanonConfig, DatedAlbum, DatedArtist, SeriesConfig, SetFetchers,
    WorldAlbum, anniversary_card, blind_spot_card, build_set_fetchers, canon_card, find_anniversaries,
    find_blind_spots, find_hidden_canon, find_series_progress, list_anniversary_cards, list_blind_spot_cards,
    list_canon_cards, list_series_cards, owned_group_mbids, refresh_blind_spots, save_anniversaries, save_canon,
    save_series, score_lens, series_card,
)
from intelligence.insights import set_builders  # noqa: E402
from intelligence.insights.set_job import owned_artists  # noqa: E402
from intelligence.store import open_store  # noqa: E402

HEADERS = {"User-Agent": "Discair/1.0 (personal music discovery)"}
MB = "https://musicbrainz.org/ws/2"
CALLS: Counter = Counter()


class Paced:
    """requests.get that counts calls per provider and adds the ListenBrainz token to ListenBrainz URLs only."""

    def __call__(self, url, **kw):
        lb = "listenbrainz" in url
        CALLS["listenbrainz" if lb else "musicbrainz"] += 1
        token = os.environ.get("LISTENBRAINZ_TOKEN")
        if lb and token:
            kw["headers"] = {**kw.get("headers", {}), "Authorization": f"Token {token}"}
        for wait in (0, 5, 20):
            time.sleep(wait)
            response = requests.get(url, **kw)
            if response.status_code not in (429, 503):
                break
            CALLS[f"{'listenbrainz' if lb else 'musicbrainz'}_retries"] += 1
        if response.status_code not in (200, 404):
            CALLS[f"status_{response.status_code}"] += 1
        return response


get = Paced()


def mb_json(path: str, **params):
    """MusicBrainz GET with backoff on 503/429; returns None on 404 or after repeated failure (counted)."""
    for wait in (0, 5, 15):
        time.sleep(wait)
        CALLS["musicbrainz"] += 1
        r = requests.get(f"{MB}/{path}", params={"fmt": "json", **params}, headers=HEADERS, timeout=30)
        time.sleep(1.1)
        if r.status_code == 404:
            return None
        if r.status_code in (429, 503):
            CALLS["musicbrainz_retries"] += 1
            continue
        r.raise_for_status()
        return r.json()
    CALLS["musicbrainz_gave_up"] += 1
    return None


def sample_albums(count: int) -> tuple[list[dict], list[str], list[dict]]:
    """All library albums, the owner's top genres, and the full albums of the busiest MBID artists."""
    albums, off = [], 0
    while True:
        page = items(nd("getAlbumList2", type="alphabeticalByName", size=500, offset=off).get("albumList2", {}).get("album"))
        albums += page
        if len(page) < 500:
            break
        off += 500
    genres = Counter(g.get("name", "").strip().lower() for a in albums for g in (a.get("genres") or []) if g.get("name"))
    # artist MBIDs come from getArtists (getAlbum carries none on this server); Various Artists is skipped
    artists = [a for i in nd("getArtists")["artists"]["index"] for a in items(i.get("artist"))]
    artists = [a for a in artists if a.get("musicBrainzId") and a["name"].strip().lower() != "various artists"]
    artists.sort(key=lambda a: (-a.get("albumCount", 0), a["id"]))
    full = []
    for artist in artists[:count]:
        for stub in items(nd("getArtist", id=artist["id"])["artist"].get("album")):
            album = nd("getAlbum", id=stub["id"])["album"]
            album["artists"] = [{"id": artist["id"], "name": artist["name"], "musicBrainzId": artist["musicBrainzId"]}]
            full.append(album)
    return albums, [g for g, _ in genres.most_common(8)], full


def card_stats(lens: str, cards: list[dict], owned: set[str]) -> dict:
    s = score_lens(lens, cards, owned=owned).as_dict()
    return {k: s[k] for k in ("cards", "diversity", "top_artist_share", "duplicate_rate", "owned_leak_rate", "verdict", "failures", "enable_by_default")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artists", type=int, default=12)
    parser.add_argument("--series-lookups", type=int, default=3)
    parser.add_argument("--out")
    args = parser.parse_args()
    load_config_env()
    result: dict = {}
    t0 = time.time()

    library, top_genres, full = sample_albums(args.artists)
    result["navidrome"] = {"library_albums": len(library), "sampled_albums": len(full), "top_genres_known": len(top_genres)}

    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "live.sqlite3")
        for album in full:
            ingest_album(db, album, now=1.0, search=None)

        # owned release groups through the real linking sweep
        # batch: one browse request per artist returns all of that artist's releases with their
        # release groups, instead of one lookup per owned release
        release_docs: dict[str, dict] = {}
        for artist_mbid, _ in owned_artists(db):
            offset = 0
            while True:
                page = mb_json("release", artist=artist_mbid, inc="release-groups", limit=100, offset=offset)
                batch = (page or {}).get("releases") or []
                release_docs.update({r["id"].lower(): r for r in batch})
                offset += 100
                if len(batch) < 100 or offset >= 500:
                    break

        def fetch_release(mbid):
            return release_docs.get(mbid.lower())  # absent from the batch: not found, no extra request
        sweep = sweep_owned_releases(db, fetch=fetch_release, now=2.0, limit=len(full) + 5)
        owned = owned_group_mbids(db)
        result["ownership"] = {"releases_looked_up": sweep.looked_up, "release_docs_batched": len(release_docs), "owned_release_groups": len(owned),
                               "sweep_remaining": sweep.remaining, "notes": list(sweep.notes)}

        fetchers = build_set_fetchers(get, headers=HEADERS, sleep=time.sleep)
        # keep the documents for the lenses that reuse them
        docs: dict[str, dict] = {"studio": {}, "lb": {}}

        def studio(m):
            docs["studio"][m] = fetchers.studio(m)
            return docs["studio"][m]

        def lb(m):
            docs["lb"][m] = fetchers.listenbrainz(m)
            return docs["lb"][m]

        # 1. blind spots through the real set job
        job = refresh_blind_spots(db, SetFetchers(studio=studio, listenbrainz=lb), max_lookups=args.artists * 2 + 4, now=3.0)
        spots = list_blind_spot_cards(db, limit=100)
        result["blind_spots"] = {"lookups": job.looked_up, "sets": job.sets, "failed": job.failed, "not_found": job.not_found,
                                 "invalid": job.invalid, "remaining": job.remaining, "saved": job.saved, "notes": job.notes,
                                 "listed": len(spots), "scorecard": card_stats("blind_spot", spots, owned)}

        # 2. series: ids discovered from the owned groups' own relations
        series_ids: list[str] = []
        for group in sorted(owned)[:10]:
            if len(series_ids) >= args.series_lookups:
                break
            doc = mb_json(f"release-group/{group}", inc="series-rels")
            for rel in (doc or {}).get("relations") or []:
                sid = (rel.get("series") or {}).get("id")
                if sid and sid not in series_ids and len(series_ids) < args.series_lookups:
                    series_ids.append(sid)
        sets = []
        for sid in series_ids:
            built = set_builders.series_set(fetchers.series(sid))
            if built:
                sets.append(built)
        series = find_series_progress(sets, owned, SeriesConfig())
        save_series(db, series, now=4.0)
        series_cards = list_series_cards(db, limit=100)
        result["series"] = {"discovered_ids": len(series_ids), "sets_built": len(sets), "progress": len(series.progress),
                            "complete": len(series.complete), "left_out": [r for _, r in series.left_out],
                            "empty_reason": series.empty_reason, "listed": len(series_cards),
                            "scorecard": card_stats("series", series_cards, owned)}

        # 3. hidden canon: the sampled artists' sitewide popular groups against the owner's top genres
        artist_genres: dict[str, tuple[str, ...]] = {}
        for album in full:
            names = tuple(g.get("name", "").strip().lower() for g in album.get("genres") or [] if g.get("name"))
            for art in album.get("artists") or []:
                if art.get("musicBrainzId"):
                    artist_genres.setdefault(art["musicBrainzId"].lower(), names)
        world = []
        for mbid, doc in docs["lb"].items():
            for rg in ((doc or {}).get("payload") or {}).get("release_groups") or []:
                world.append(WorldAlbum(rg.get("release_group_mbid"), rg.get("release_group_name") or "", rg.get("artist_name"),
                                        genres=artist_genres.get(mbid.lower(), ()), listens=int(rg.get("total_listen_count") or 0)))
        canon = find_hidden_canon(world, owned, top_genres)
        save_canon(db, canon, now=5.0)
        canon_cards = list_canon_cards(db, limit=100)
        result["hidden_canon"] = {"pool": len(world), "picks": len(canon.picks), "owned_excluded": canon.owned_excluded,
                                  "dropped": canon.dropped, "empty_reason": canon.empty_reason, "listed": len(canon_cards),
                                  "scorecard": card_stats("hidden_canon", canon_cards, owned)}

        # 4. anniversaries: owned groups' first-release dates and the sampled artists' life-span
        dated = []
        for doc in docs["studio"].values():
            for g in (doc or {}).get("release-groups") or []:
                if (g.get("id") or "").lower() in owned:
                    dated.append(DatedAlbum(g["id"], g.get("title") or "", None, g.get("first-release-date")))
        artists = []
        for mbid in docs["studio"]:
            doc = mb_json(f"artist/{mbid}")
            if doc:
                span = doc.get("life-span") or {}
                artists.append(DatedArtist(mbid, doc.get("name") or "", doc.get("type", "").lower() or None,
                                           span.get("begin"), span.get("end")))
        today = date.today()
        ann = find_anniversaries(dated, artists, today, AnniversaryConfig(window_days=30))
        save_anniversaries(db, ann, now=6.0)
        ann_cards = list_anniversary_cards(db, limit=100)
        result["anniversaries"] = {"dated_albums": len(dated), "dated_artists": len(artists), "items": len(ann.items),
                                   "partial_dates": ann.partial_dates, "future_dates": ann.future_dates,
                                   "unknown_type": ann.unknown_type, "empty_reason": ann.empty_reason,
                                   "listed": len(ann_cards), "scorecard": card_stats("anniversary", ann_cards, owned)}
        db.close()

    result["provider_calls"] = dict(CALLS)
    result["seconds"] = round(time.time() - t0, 1)
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
