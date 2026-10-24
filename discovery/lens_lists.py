"""Daily lens lists: one finished list per lens from already-gathered pools (Engine 2, Phase 4).

Pure: the caller gathers each lens's pool (``run_deep_cuts_tag_supply`` with the lens name
and day as the radio scope), the album listeners, the artist genre tags, the fallback tags
and the known-artist inputs; this module makes no provider calls and reads no clock. The
gates are the lens's own (``run_lens`` through ``partition_lens_pools``), and every lens list
is independent of the recommendation history and cooldown. Unwired; see docs/engine2.md
(Phase 4, slice 1).
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Container, Iterable, Mapping, Sequence
from datetime import date
from typing import Any

from discovery.allocation_contract import CATEGORIES, MAX_RECOMMENDATION_COUNT
from discovery.allocation_inputs import build_allocation_inputs
from discovery.history_windows import (
    densest_window_listens,
    listen_artist_mbid,
    window_artist_weights,
)
from discovery.lenses import DEEP_CUTS, LENSES, OBSESSIONS, REPEATED_TRACKS, Lens, partition_lens_pools
from discovery.profile_seeds import obsession_seed_queries, repeated_track_seed_queries
from discovery.recommendations import artist_identity, music_key
from discovery.tag_queries import MAX_PROFILE_QUERIES, select_supplementary_tag_queries, tag_from_query

# Scarcest supply first, so a lens with plenty of candidates cannot take the few another
# lens has (partitioning removes an artist from the lenses after the one that picked it).
# Measured 2026-10-24 on one history: Repeated tracks seeds niche tags and filled 8 of 10
# without the fallback tags; Obsessions seeds broad tags and filled 10 of 10 either way;
# Deep cuts seeds the dense-month window, which sits between the two.
LENS_LIST_ORDER = (REPEATED_TRACKS, DEEP_CUTS, OBSESSIONS)
LENS_LIST_SIZE = 10
# Deep cuts window: the densest month of the history. When the history is shorter than
# that, the densest window is the whole recent activity, as the lens definition asks.
DEEP_CUTS_WINDOW_DAYS = 30
# Listens stamped before 1971 are bad export rows (a Last.fm export stamps some at 0).
_EARLIEST_LISTEN = 365 * 24 * 60 * 60


def _dated_sanely(listen: Mapping[str, Any]) -> bool:
    """False for a listen stamped before 1971; undated listens are kept for the profiles
    that do not need a date."""
    try:
        stamp = float(listen.get("listened_at"))
    except (TypeError, ValueError, AttributeError):
        return True
    return not math.isfinite(stamp) or stamp >= _EARLIEST_LISTEN


def history_artist_mbids(listens: Iterable[Mapping[str, Any]]) -> set[str]:
    """Artist MBIDs in the listening history, for ``known_artist_mbids``. Listens without
    an artist MBID add nothing; those artists are still caught by a library name match."""
    return {mbid for listen in listens if (mbid := listen_artist_mbid(listen))}


def lens_seed_queries(
    listens: Iterable[Mapping[str, Any]],
    artist_tags: Mapping[str, Sequence[Any]],
    *,
    limit: int = MAX_PROFILE_QUERIES,
) -> dict[str, list[tuple[str, str, str]]]:
    """Seed queries for each lens in ``LENS_LIST_ORDER``, derived from the listening history.

    Repeated tracks and Obsessions use their seed builders with the approved defaults; Deep
    cuts takes the profile tags of the densest ``DEEP_CUTS_WINDOW_DAYS`` window, with flat
    weights. Listens stamped before 1971 are dropped first. Pure; the queries go to
    ``run_deep_cuts_tag_supply``, one lens at a time."""
    records = [listen for listen in listens if _dated_sanely(listen)]
    window = densest_window_listens(records, DEEP_CUTS_WINDOW_DAYS)
    return {
        REPEATED_TRACKS.name: repeated_track_seed_queries(records, artist_tags, limit=limit),
        DEEP_CUTS.name: select_supplementary_tag_queries(
            window_artist_weights(window), artist_tags, [],
            profile_limit=limit, exploration_limit=0),
        OBSESSIONS.name: obsession_seed_queries(records, artist_tags, limit=limit),
    }


def merge_artist_tags(
    artist_tags: Mapping[str, Sequence[Any]],
    fallback_tags: Mapping[str, Sequence[Any]] | None,
) -> dict[str, list[str]]:
    """The genre tags with the fallback tags (``fallback_artist_tags`` output) after them:
    existing tags first and in order, then fallback tags not already present."""
    merged = {str(mbid): [str(tag) for tag in tags if tag is not None]
              for mbid, tags in artist_tags.items()}
    for mbid, tags in (fallback_tags or {}).items():
        current = merged.setdefault(str(mbid), [])
        for tag in tags:
            if tag is not None and str(tag) not in current:
                current.append(str(tag))
    return merged


def _usable(album: Any) -> bool:
    return (isinstance(album, Mapping) and bool(str(album.get("album") or "").strip())
            and bool(str(album.get("primary_artist") or "").strip()))


def _as_candidate(album: Mapping[str, Any]) -> dict[str, Any]:
    """A copy with the allocator fields the tag lane does not set. The Deep cuts gates use
    neither: the category is only counted and the score is not used for ranking."""
    category = album.get("discovery_category")
    score = album.get("discovery_score")
    return {
        **album,
        "discovery_category": category if category in CATEGORIES else "unclassified",
        "discovery_score": (float(score) if isinstance(score, (int, float))
                            and not isinstance(score, bool) and math.isfinite(score) else 0.0),
    }


def _validate(lenses: Sequence[Lens], pools: Mapping[str, Any], day: Any, count: Any) -> None:
    if type(count) is not int or not 1 <= count <= MAX_RECOMMENDATION_COUNT:
        raise ValueError("count must be between 1 and 20")
    if not isinstance(day, str):
        raise ValueError("day must be an ISO date (YYYY-MM-DD)")
    try:
        parsed = date.fromisoformat(day)
    except ValueError:
        raise ValueError("day must be an ISO date (YYYY-MM-DD)") from None
    if parsed.isoformat() != day:
        raise ValueError("day must be an ISO date (YYYY-MM-DD)")
    for lens in lenses:
        if LENSES.get(getattr(lens, "name", None)) is not lens or lens.kind != "deep_cuts":
            raise ValueError("lenses must be registered lenses with the Deep cuts gates")
    if len({lens.name for lens in lenses}) != len(lenses):
        raise ValueError("lens names must be unique")
    if not isinstance(pools, Mapping):
        raise ValueError("pools must map lens names to albums")
    unknown = set(pools) - {lens.name for lens in lenses}
    if unknown:
        raise ValueError(f"pools name lenses that are not built: {sorted(unknown)}")


def build_lens_lists(
    pools: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    day: str,
    popularity: Mapping[str, Mapping[str, Any]],
    artist_tags: Mapping[str, Sequence[Any]],
    library_by_title: Mapping[str, list],
    fallback_tags: Mapping[str, Sequence[Any]] | None = None,
    known_artist_mbids: Container[str] = (),
    library_artist_mbids: Mapping[str, str] | None = None,
    seeds: Mapping[str, Sequence[tuple[str, str, str]]] | None = None,
    lenses: Sequence[Lens] = LENS_LIST_ORDER,
    count: int = LENS_LIST_SIZE,
) -> dict[str, dict[str, Any]]:
    """Build one list of ``count`` albums per lens for ``day``, in ``lenses`` order.

    ``pools`` maps a lens name to the albums its supply gathered (a missing lens has an
    empty pool); ``popularity`` is {release_group_mbid: {"album_listeners": ...}};
    ``artist_tags`` are the genre tags by artist MBID, extended by ``fallback_tags``; the
    known-artist and ownership inputs are those of ``build_allocation_inputs``. ``seeds``
    (the queries each lens was gathered with) only adds the seed tag names to the payload.

    An artist or album title selected by one lens is not offered to the lenses after it.
    Entries that are not albums (no title or no primary artist) are skipped and counted.
    Returns {lens name: payload}; each payload is JSON-serialisable and depends only on
    the arguments. Raises ``ValueError`` before any work on an invalid argument."""
    _validate(lenses, pools, day, count)
    genre_cache = merge_artist_tags(artist_tags, fallback_tags)
    by_lens: dict[str, dict[str, Mapping[str, Any]]] = {}
    candidates: dict[str, list] = {}
    skipped: dict[str, int] = {}
    for lens in lenses:
        albums = list(pools.get(lens.name, ()))
        usable = [_as_candidate(album) for album in albums if _usable(album)]
        skipped[lens.name] = len(albums) - len(usable)
        by_lens[lens.name], candidates[lens.name] = build_allocation_inputs(
            usable, library_by_title=library_by_title, genre_cache=genre_cache,
            music_key=music_key, artist_identity=artist_identity, popularity=popularity,
            known_artist_mbids=known_artist_mbids, library_artist_mbids=library_artist_mbids,
        )
    results = partition_lens_pools(candidates, count, lenses)

    lists: dict[str, dict[str, Any]] = {}
    for lens, result in zip(lenses, results):
        seed_tags = {style: tag_from_query(query) or None
                     for query, _family, style in (seeds or {}).get(lens.name, ())}
        chosen = {item.candidate_id: item for item in candidates[lens.name]}
        albums = []
        for rank, cid in enumerate(result.selected_candidate_ids, start=1):
            album, item = by_lens[lens.name][cid], chosen[cid]
            albums.append({
                "rank": rank,
                "artist": str(album.get("artist") or album["primary_artist"]),
                "primary_artist": str(album["primary_artist"]),
                "album": str(album["album"]),
                "artist_mbid": str(album["artist_mbid"]) if album.get("artist_mbid") else None,
                "release_group_mbid": (str(album["release_group_mbid"])
                                       if album.get("release_group_mbid") else None),
                "seed": item.seed,
                "seed_tag": seed_tags.get(item.seed),
                "album_listeners": item.audience,
                "tag_strength": item.tag_strength,
                "tags": list(item.tags),
            })
        statuses = Counter(decision.status for decision in result.decisions)
        lists[lens.name] = {
            "lens": lens.name,
            "label": lens.label,
            "day": day,
            "requested": count,
            "albums": albums,
            "seed_tags": [tag for tag in seed_tags.values() if tag],
            "pool_size": len(candidates[lens.name]),
            "skipped_entries": skipped[lens.name],
            "checked": result.checked_count,
            "decisions": dict(sorted(statuses.items())),
        }
    return lists
