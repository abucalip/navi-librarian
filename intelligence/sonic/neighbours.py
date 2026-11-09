"""Neighbours by Ear (``album_sonic_neighbours``): owned albums that sound like one album.

Composed from the Sonic routes, not a graph path (docs/ALBUM_PATHS_PROPOSAL.md, path 8). Pure logic: the
Navidrome call is injected, so nothing here touches the network, the store or a provider.

Rules (owner decisions 2026-11-09):
- At most ``MAX_SEEDS`` (8) seeds per album, evenly spaced over the tracklist, always including the first
  and last track. Selection is deterministic, so the one-hour cache applies; no random sampling.
- A seed with no analysis data is skipped and reported in ``skipped``; it does not count against the cap,
  so the next unused track (tracklist order) takes its place, within ``MAX_ATTEMPTS`` calls.
- Matches on the album itself are dropped. The per-artist cap of 2 per seed is ``similar_tracks``' own rule.
- Albums are ranked by how many distinct seeds returned a track from them; ties break by the earliest
  release year, then album id. ``similarity`` is never read, sorted on or thresholded.
- A time bound applies; when it is hit the answer is what was gathered, with ``truncated: "time"``.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from .proxy import similar_tracks

MAX_SEEDS = 8
MAX_ATTEMPTS = 16
PER_SEED = 10  # similar tracks requested per seed
TIME_LIMIT = 5.0  # seconds
REASON_CODE = "sonic_neighbour"
STATUSES = ("ok", "empty", "not_found", "unavailable")


def album_tracks(api_call: Callable[..., dict], album_id: str) -> tuple[dict | None, list[dict[str, Any]], str | None]:
    """``(album, tracks in disc/track order, None)`` or ``(None, [], status)``."""
    try:
        root = api_call("getAlbum", id=album_id)
    except RuntimeError as exc:
        text = str(exc)
        if "API error 70" in text:
            return None, [], "not_found"
        if "API error 0" in text or "API error 30" in text:
            return None, [], "unavailable"
        raise
    album = (root or {}).get("album") or {}
    if not album.get("id"):
        return None, [], "not_found"
    songs = [s for s in album.get("song") or [] if s.get("id")]
    songs.sort(key=lambda s: (s.get("discNumber") or 1, s.get("track") or 0))
    return album, songs, None


def pick_seeds(track_ids: list[str], limit: int = MAX_SEEDS) -> list[str]:
    """Up to ``limit`` ids evenly spaced over ``track_ids``, first and last included, then the rest in order.

    The first ``limit`` entries are the primary seeds; the remainder are replacements for skipped seeds.
    """
    n = len(track_ids)
    if n <= limit:
        return list(track_ids)
    idx = sorted({round(i * (n - 1) / (limit - 1)) for i in range(limit)})
    spare = (i for i in range(n) if i not in set(idx))
    return [track_ids[i] for i in idx] + [track_ids[i] for i in spare]


def _year(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def album_neighbours(api_call: Callable[..., dict], album_id: str, *, max_seeds: int = MAX_SEEDS,
                     time_limit: float = TIME_LIMIT, clock: Callable[[], float] = time.monotonic) -> dict[str, Any]:
    """The neighbours answer for one Navidrome album id (status, start, stops, seeds, skipped, truncated)."""
    album, songs, status = album_tracks(api_call, album_id)
    if status:
        return {"status": status, "start": None, "stops": [], "seeds": [], "skipped": [], "truncated": None}
    start = {"album_id": album["id"], "album": album.get("name") or album.get("title"),
             "artist": album.get("artist"), "year": _year(album.get("year")), "tracks": len(songs)}
    titles = {s["id"]: s.get("title") for s in songs}
    order = pick_seeds([s["id"] for s in songs], max_seeds)
    deadline = clock() + time_limit
    groups: dict[str, dict[str, Any]] = {}
    used, skipped, truncated = [], [], None
    for seed_id in order[:MAX_ATTEMPTS]:
        if len(used) >= max_seeds:
            break
        if clock() >= deadline:
            truncated = "time"
            break
        result = similar_tracks(api_call, seed_id, count=PER_SEED)
        if result.status == "unavailable":
            return {"status": "unavailable", "start": start, "stops": [], "seeds": [], "skipped": [],
                    "truncated": None}
        if result.status == "not_found" or (result.status == "empty" and not result.dropped):
            skipped.append({"navidrome_id": seed_id, "title": titles.get(seed_id), "reason": "no_analysis"})
            continue
        used.append(seed_id)
        for track in result.tracks:
            target = track.get("album_id")
            if not target or target == album["id"]:
                continue
            g = groups.setdefault(target, {"album_id": target, "album": track.get("album"),
                                           "artist": track.get("artist"), "artist_id": track.get("artist_id"),
                                           "cover_art": track.get("cover_art"), "year": None, "by_seed": {}})
            g["year"] = min((y for y in (g["year"], _year(track.get("year"))) if y is not None), default=None)
            g["by_seed"].setdefault(seed_id, []).append(
                {"navidrome_id": track.get("navidrome_id"), "title": track.get("title")})
    stops = []
    for g in groups.values():
        count = len(g["by_seed"])
        matches = [{"seed": {"navidrome_id": sid, "title": titles.get(sid)}, "tracks": found}
                   for sid, found in g["by_seed"].items()]
        stops.append({"album_id": g["album_id"], "album": g["album"], "artist": g["artist"],
                      "artist_id": g["artist_id"], "cover_art": g["cover_art"], "year": g["year"],
                      "match_count": count, "matches": matches, "owned": True,
                      "reasons": [{"code": REASON_CODE, "count": count,
                                   "text": f"Sounds like {count} of this album's tracks"}]})
    stops.sort(key=lambda s: (-s["match_count"], s["year"] is None, s["year"] or 0, s["album_id"]))
    return {"status": "ok" if stops else "empty", "start": start, "stops": stops,
            "seeds": [{"navidrome_id": s, "title": titles.get(s)} for s in used],
            "skipped": skipped, "truncated": truncated}
