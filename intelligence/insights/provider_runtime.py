"""Resumable provider-backed refresh for blind spots, hidden canon and anniversaries.

Owner-approved provider traffic (2026-11-05), bounded and slow. Each call is one *tick*:

1. ``ingest_step`` (injected, Navidrome only) records a slice of the owned library;
2. owned artists not browsed within ``ttl`` get one MusicBrainz release browse (paged) so their
   owned releases link to release groups (``sweep_owned_releases``, no extra requests);
3. each owned artist's studio discography, ListenBrainz top release groups and MusicBrainz life-span
   are fetched into the document cache (missing first, then the stalest), until the tick's
   request ``budget`` is spent;
4. only when every owned artist has been browsed and has all three documents are the three lenses
   recomputed from the cache and saved. Until then saved cards stay as they were: a half-linked
   library would show gaps that are not real.

Every HTTP call goes through a counting wrapper that raises :class:`BudgetSpent` before the call
that would exceed the budget; the fetchers pace themselves (MusicBrainz 1.1 s, ListenBrainz 0.5 s).
A provider failure stops the tick and fails the run (cached documents are kept, so the next tick
resumes). Nothing here changes an ownership flag or a recommendation weight.

Series (``series=True`` only, so a server without the series lens makes none of these requests) share
the same budget and run after the artist documents:

5. series-id discovery, batched per artist (owner rule: batch lookups whenever possible): one paged
   MusicBrainz release-group browse with ``inc=series-rels`` per owned artist (cache kind
   ``artistseries``: series ids per release group), never-fetched artists first, then the stalest.
   Owned groups under other artists (compilations) are not covered, and an artist with more than
   ``BROWSE_PAGES`` x 100 groups is truncated and reported (``series_truncated``);
6. each discovered series gets one lookup with ``inc=release-group-rels`` (cache kind ``series``);
7. only when every artist is browsed (ownership fully linked), every owned artist has been browsed for series
   and every discovered series is cached are the series cards recomputed and saved, so a half-linked
   library or a half-read series never shows chapters that are not really missing. Ids are never guessed.
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections import Counter
from datetime import date
from typing import Any, Callable, Iterable, Mapping

from ..editions import sweep_owned_releases
from ..jobs import RunResult, run_job
from . import provider_cache as cache
from . import set_builders
from .anniversaries import AnniversaryConfig, DatedAlbum, DatedArtist, find_anniversaries
from .blind_spots import BlindSpotsConfig, find_blind_spots
from .blind_spot_persistence import dismissed_set_keys, save_blind_spots
from .card_persistence import (
    dismissed_anniversary_keys, dismissed_canon_keys, dismissed_series_keys, save_anniversaries, save_canon,
    save_series,
)
from .hidden_canon import WorldAlbum, find_hidden_canon
from .series_completion import SeriesConfig, find_series_progress
from .set_fetchers import MUSICBRAINZ_SPACING_SECONDS, build_set_fetchers
from .set_job import owned_artists, owned_group_mbids

JOB = "insights_provider_lenses"
DEFAULT_BUDGET = 120
DEFAULT_TTL = 30 * cache.DAY
MUSICBRAINZ = "https://musicbrainz.org/ws/2"
BROWSE_PAGES = 5
TOP_GENRES = 8

Get = Callable[..., Any]


class BudgetSpent(Exception):
    """The tick's request budget is used up."""


class CountingGet:
    """Wraps a ``requests.get``-shaped callable and refuses calls beyond the budget."""

    def __init__(self, get: Get, budget: int):
        self._get, self.budget, self.used = get, budget, 0

    def __call__(self, url: str, **kwargs: Any) -> Any:
        if self.used >= self.budget:
            raise BudgetSpent()
        self.used += 1
        return self._get(url, **kwargs)


def _paced_json(get: Get, url: str, params: Mapping[str, Any], headers: Mapping[str, str],
                sleep: Callable[[float], Any] | None) -> Any:
    try:
        response = get(url, params=dict(params), headers=dict(headers), timeout=30)
    finally:
        if sleep is not None:
            sleep(MUSICBRAINZ_SPACING_SECONDS)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise RuntimeError(f"musicbrainz returned HTTP {response.status_code}")
    return response.json()


def _release_browse(get: Get, artist_mbid: str, headers, sleep) -> dict[str, dict]:
    """All of an artist's releases with their release groups, keyed by lower-case release MBID."""
    docs: dict[str, dict] = {}
    for page in range(BROWSE_PAGES):
        body = _paced_json(get, f"{MUSICBRAINZ}/release",
                           {"artist": artist_mbid, "inc": "release-groups", "limit": 100,
                            "offset": page * 100, "fmt": "json"}, headers, sleep)
        batch = (body or {}).get("releases") if isinstance(body, Mapping) else None
        if not isinstance(batch, list):
            break
        docs.update({str(r["id"]).lower(): r for r in batch if isinstance(r, Mapping) and r.get("id")})
        if len(batch) < 100:
            break
    return docs


def _life_span(get: Get, artist_mbid: str, headers, sleep) -> Mapping[str, Any] | None:
    body = _paced_json(get, f"{MUSICBRAINZ}/artist/{artist_mbid}", {"fmt": "json"}, headers, sleep)
    if not isinstance(body, Mapping):
        return None
    span = body.get("life-span") if isinstance(body.get("life-span"), Mapping) else {}
    return {"name": body.get("name"), "type": body.get("type"), "begin": span.get("begin"), "end": span.get("end")}


def _artist_series(get: Get, artist_mbid: str, headers, sleep) -> Mapping[str, Any]:
    """Series ids per release group for one artist, from paged browses (not one lookup per group)."""
    groups: dict[str, list[str]] = {}
    total = None
    for page in range(BROWSE_PAGES):
        body = _paced_json(get, f"{MUSICBRAINZ}/release-group",
                           {"artist": artist_mbid, "inc": "series-rels", "limit": 100,
                            "offset": page * 100, "fmt": "json"}, headers, sleep)
        batch = body.get("release-groups") if isinstance(body, Mapping) else None
        if not isinstance(batch, list):
            break
        total = body.get("release-group-count", total)
        for group in batch:
            if not isinstance(group, Mapping) or not isinstance(group.get("id"), str):
                continue
            ids: list[str] = []
            for rel in group.get("relations") or []:
                sid = ((rel.get("series") or {}) if isinstance(rel, Mapping) else {}).get("id")
                if isinstance(sid, str) and sid.strip() and sid.lower() not in ids:
                    ids.append(sid.lower())
            groups[group["id"].lower()] = ids
        if len(batch) < 100 or (isinstance(total, int) and len(groups) >= total):
            break
    return {"groups": groups, "count": total if isinstance(total, int) else len(groups)}


def discovered_series_ids(db: sqlite3.Connection, artists: Iterable[str], owned: set[str]) -> list[str]:
    """Sorted distinct series ids of owned groups found so far (from the document cache)."""
    found: set[str] = set()
    for artist in artists:
        entry = cache.get(db, "artistseries", artist)
        groups = entry[1].get("groups") if entry and isinstance(entry[1], Mapping) else None
        for group, ids in (groups or {}).items():
            if group in owned:
                found.update(ids)
    return sorted(found)


# --------------------------------------------------------------------------- compute


def _library_taste(db: sqlite3.Connection) -> tuple[list[str], dict[str, tuple[str, ...]]]:
    """Top genres and an artist-level genre proxy, read from the stored Navidrome album observations."""
    rows = db.execute(
        "SELECT payload FROM observations WHERE source = 'navidrome' AND entity_hint LIKE 'album:%' "
        "AND id IN (SELECT MAX(id) FROM observations WHERE source = 'navidrome' GROUP BY entity_hint)"
    ).fetchall()
    counts: Counter = Counter()
    by_artist: dict[str, tuple[str, ...]] = {}
    for row in rows:
        data = json.loads(row["payload"])
        genres = tuple(g.strip().lower() for g in data.get("genres") or [] if isinstance(g, str) and g.strip())
        counts.update(genres)
        if data.get("artist_mbid"):
            by_artist.setdefault(str(data["artist_mbid"]).lower(), genres)
    return [g for g, _ in counts.most_common(TOP_GENRES)], by_artist


def _docs(db: sqlite3.Connection, kind: str, mbid: str):
    entry = cache.get(db, kind, mbid)
    return entry[1] if entry else None


def compute_and_save(db: sqlite3.Connection, today: date, now: float) -> dict[str, int]:
    """Recompute the three lenses from cached documents and save them."""
    owned = owned_group_mbids(db)
    artists = owned_artists(db)
    names = {m.lower(): n for m, n in artists}
    top_genres, artist_genres = _library_taste(db)

    sets, world, dated_albums, dated_artists = [], [], [], []
    for mbid, name in artists:
        studio, lb, life = _docs(db, "studio", mbid), _docs(db, "lb", mbid), _docs(db, "life", mbid)
        for built in (studio and set_builders.studio_discography_set(mbid, name, studio),
                      lb and set_builders.listenbrainz_top_set(mbid, name, lb)):
            if built:
                sets.append(built)
        for rg in ((lb or {}).get("payload") or {}).get("release_groups") or []:
            info = set_builders.listenbrainz_group(rg)
            world.append(WorldAlbum(info["mbid"], info["title"], info["artist"] or name, year=info["year"],
                                    genres=artist_genres.get(mbid.lower(), ()), listens=info["listens"]))
        for g in (studio or {}).get("release-groups") or []:
            if (g.get("id") or "").lower() in owned:
                dated_albums.append(DatedAlbum(g["id"], g.get("title") or "", name, g.get("first-release-date")))
        if life:
            kind = (life.get("type") or "").lower() or None
            dated_artists.append(DatedArtist(mbid, life.get("name") or name, kind, life.get("begin"), life.get("end")))

    spots = find_blind_spots(sets, owned, BlindSpotsConfig(), dismissed_set_keys(db))
    canon = find_hidden_canon(world, owned, top_genres, dismissed=dismissed_canon_keys(db))
    ann = find_anniversaries(dated_albums, dated_artists, today, AnniversaryConfig(window_days=30),
                             dismissed_anniversary_keys(db))
    return {
        "blind_spot": save_blind_spots(db, spots, now=now),
        "hidden_canon": save_canon(db, canon, now=now),
        "anniversary": save_anniversaries(db, ann, now=now),
    }


def compute_series(db: sqlite3.Connection, now: float) -> int:
    """Recompute the series cards from cached series documents and save them."""
    owned = owned_group_mbids(db)
    ids = discovered_series_ids(db, [m for m, _ in owned_artists(db)], owned)
    built = [set_builders.series_set(_docs(db, "series", sid)) for sid in ids]
    result = find_series_progress([b for b in built if b], owned, SeriesConfig(), dismissed_series_keys(db))
    return save_series(db, result, now=now)


# --------------------------------------------------------------------------- tick


def _needs(db: sqlite3.Connection, kind: str, mbid: str, now: float, ttl: float) -> tuple[int, float]:
    """Sort key: 0 for never fetched, 1 for stale (oldest first); fresh entries are excluded by the caller."""
    entry = cache.get(db, kind, mbid)
    return (0, 0.0) if entry is None else (1, entry[0])


def _series_steps(db, counting, fetchers, headers, sleep, now, ttl, progress) -> bool:
    """Steps 5 and 6. Returns True when the budget ran out."""
    artists = [m for m, _ in owned_artists(db)]
    todo = [a for a in artists if not cache.is_fresh(cache.get(db, "artistseries", a), now, ttl)]
    todo.sort(key=lambda a: _needs(db, "artistseries", a, now, ttl))
    try:
        for artist in todo:
            cache.put(db, "artistseries", artist, _artist_series(counting, artist, headers, sleep), now)
        ids = discovered_series_ids(db, artists, owned_group_mbids(db))
        pending = [s for s in ids if not cache.is_fresh(cache.get(db, "series", s), now, ttl)]
        pending.sort(key=lambda s: _needs(db, "series", s, now, ttl))
        for sid in pending:
            cache.put(db, "series", sid, fetchers.series(sid), now)
    except BudgetSpent:
        return True
    return False


def refresh_provider_lenses(
    db: sqlite3.Connection,
    *,
    get: Get,
    headers: Mapping[str, str],
    sleep: Callable[[float], Any] | None = time.sleep,
    ingest_step: Callable[[sqlite3.Connection], Any] | None = None,
    budget: int = DEFAULT_BUDGET,
    ttl: float = DEFAULT_TTL,
    now: float | None = None,
    today: date | None = None,
    series: bool = False,
) -> RunResult:
    if budget < 1:
        raise ValueError("budget must be at least 1")
    now = time.time() if now is None else now
    today = today or date.fromtimestamp(now)
    counting = CountingGet(get, budget)

    def work(ctx) -> bool:
        progress: dict[str, Any] = {}
        if ingest_step is not None:
            ingest_step(db)
        fetchers = build_set_fetchers(counting, headers=headers, sleep=sleep)
        artists = owned_artists(db)
        spent = False
        # 2. ownership: browse artists whose releases are not yet linked or whose marker is stale
        release_docs: dict[str, dict] = {}
        browsed = 0
        try:
            for mbid, _ in artists:
                if cache.is_fresh(cache.get(db, "browse", mbid), now, ttl):
                    continue
                release_docs.update(_release_browse(counting, mbid, headers, sleep))
                cache.put(db, "browse", mbid, {}, now)  # only after a complete browse
                browsed += 1
        except BudgetSpent:
            spent = True
        if release_docs:  # link what was browsed even when the budget ran out part-way
            sweep = sweep_owned_releases(db, fetch=lambda m: release_docs.get(m.lower()), now=now, limit=100000)
            progress["linked"] = sweep.linked
        progress["browsed"] = browsed
        # 3. documents, never-fetched before stale
        if not spent:
            wanted = [(kind, mbid) for mbid, _ in artists for kind in ("studio", "lb", "life")
                      if not cache.is_fresh(cache.get(db, kind, mbid), now, ttl)]
            wanted.sort(key=lambda w: _needs(db, w[0], w[1], now, ttl))
            fetch = {"studio": fetchers.studio, "lb": fetchers.listenbrainz,
                     "life": lambda m: _life_span(counting, m, headers, sleep)}
            try:
                for kind, mbid in wanted:
                    cache.put(db, kind, mbid, fetch[kind](mbid), now)
            except BudgetSpent:
                spent = True
        if series and not spent:
            spent = _series_steps(db, counting, fetchers, headers, sleep, now, ttl, progress)
        progress["stopped"] = "budget" if spent else None
        progress["requests"] = counting.used

        complete = bool(artists) and all(
            cache.get(db, kind, mbid) is not None for mbid, _ in artists for kind in ("browse", "studio", "lb", "life"))
        progress["artists"] = len(artists)
        progress["complete"] = complete
        if complete:
            progress["saved"] = compute_and_save(db, today, now)
        if series:
            owned = owned_group_mbids(db)
            browsed_all = bool(artists) and all(cache.get(db, "browse", m) is not None for m, _ in artists)
            docs = [cache.get(db, "artistseries", m) for m, _ in artists]
            ids = discovered_series_ids(db, [m for m, _ in artists], owned)
            progress["series_ids"] = len(ids)
            progress["series_truncated"] = sum(
                1 for e in docs if e and isinstance(e[1], Mapping) and e[1].get("count", 0) > len(e[1].get("groups") or {}))
            progress["series_complete"] = bool(
                browsed_all and owned and all(e is not None for e in docs)
                and all(cache.get(db, "series", sid) is not None for sid in ids))
            if progress["series_complete"]:
                progress.setdefault("saved", {})["series_completion"] = compute_series(db, now)
        ctx.checkpoint(progress)
        return True

    return run_job(db, JOB, work)
