"""Current tastes: the lens that replaced Now (Engine 2, Phase 4 follow-up).

Pure: the caller supplies the listens and the cached artist tags; no I/O, no clock. The lens
looks at the recent window (30 days, widening when that window is thin), drops the tags the window
plays less than the whole history does (a tag the month leans on is kept, whatever its all-time
rank), and seeds the tag radio with the rest, heaviest first. Each seed is capped at two albums by
the lens gates (``select_deep_cuts``).

Enrichments: the regional spine (the area the window's weight sits in) and the era match
(the decade of the window) rank candidates through ``ranking_boost``; their data comes from
``discovery.artist_profiles`` and the release search dates. Similar-artist and collaborator
links widen the window weights at a discount, but nothing fetches them yet, so the daily list
does not use them. See docs/engine2.md.
"""
from __future__ import annotations

import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from discovery.history_windows import window_artist_weights
from discovery.tag_queries import select_supplementary_tag_queries, tag_from_query

# Window lengths tried in order; the first one holding enough listens is used.
CURRENT_WINDOW_DAYS = (30, 90, 365)
MIN_WINDOW_LISTENS = 20
# Seeds per run. Twelve, not six: with six, the month's smaller distinctive genres (Ethiopian jazz,
# desert blues) fall below the heavier everyday ones. A starting value, not measured.
SEED_LIMIT = 12
# A window tag is dropped when its share of the window's listen weight is below this multiple of its
# share of the whole history. 1.0 keeps every tag the month plays at least as much as usual.
OVER_INDEX_RATIO = 1.0
# Weight given to a linked artist, relative to the artist it is linked from.
SIMILAR_DISCOUNT = 0.5
COLLABORATOR_DISCOUNT = 0.25
# A regional spine needs this share of the window weight in one area.
MIN_AREA_SHARE = 0.3
# Ranking boosts added to a candidate's tag strength (starting values, not measured). A release by
# an artist from the spine area gets SPINE_BOOST; a release in a window decade gets ERA_BOOST times
# that decade's share of the window weight.
SPINE_BOOST = 0.5
ERA_BOOST = 0.25
_DAY_SECONDS = 24 * 60 * 60


def _stamp(listen: Mapping[str, Any]) -> float | None:
    try:
        value = float(listen.get("listened_at"))
    except (TypeError, ValueError, AttributeError):
        return None
    return value if math.isfinite(value) else None


def _key(tag: Any) -> str:
    return str(tag).strip().casefold()


def recent_window(listens: Iterable[Mapping[str, Any]]) -> tuple[list[Mapping[str, Any]], int]:
    """Return ``(window listens, window days)`` for the first window in ``CURRENT_WINDOW_DAYS``
    that holds at least ``MIN_WINDOW_LISTENS`` dated listens, measured back from the newest
    listen (as the decayed profile is). Falls back to the longest window when none qualifies.
    Undated listens are ignored."""
    dated = [(stamp, listen) for listen in listens if (stamp := _stamp(listen)) is not None]
    if not dated:
        return [], CURRENT_WINDOW_DAYS[0]
    newest = max(stamp for stamp, _ in dated)
    window: list[Mapping[str, Any]] = []
    days = CURRENT_WINDOW_DAYS[-1]
    for days in CURRENT_WINDOW_DAYS:
        window = [listen for stamp, listen in dated if newest - stamp <= days * _DAY_SECONDS]
        if len(window) >= MIN_WINDOW_LISTENS:
            return window, days
    return window, days


def expand_artist_weights(
    weights: Mapping[str, float],
    links: Mapping[str, Sequence[str]],
    discount: float,
) -> Counter[str]:
    """Add each linked artist at ``discount`` times the weight of the artist it is linked from.

    ``links`` maps an artist MBID to the MBIDs it is linked to (similar artists, or band members
    and collaborators). Self-links are ignored. The input is not changed."""
    expanded: Counter[str] = Counter({artist: float(weight) for artist, weight in weights.items()})
    for artist, weight in weights.items():
        for linked in links.get(artist, ()):
            if linked and linked != artist:
                expanded[linked] += float(weight) * discount
    return expanded


def _tag_shares(
    weights: Mapping[str, float],
    artist_tags: Mapping[str, Sequence[Any]],
) -> dict[str, float]:
    """Share of the total listen weight carried by each tag (casefolded), an artist adding its
    weight once to each of its tags. Shares of different tags need not sum to one."""
    total = sum(float(weight) for weight in weights.values())
    if total <= 0:
        return {}
    shares: Counter[str] = Counter()
    for artist, weight in weights.items():
        for tag in {_key(t) for t in artist_tags.get(artist, ()) if t}:
            shares[tag] += float(weight) / total
    return dict(shares)


def _under_represented_tags(
    window_played: Mapping[str, float],
    long_term: Mapping[str, float],
    artist_tags: Mapping[str, Sequence[Any]],
) -> set[str]:
    """Casefolded tags the window plays less than the whole history does, by ``OVER_INDEX_RATIO``.

    Only tags the window actually plays can be under-represented; a tag from a linked artist the
    listener did not play is never dropped by this rule."""
    window_shares = _tag_shares(window_played, artist_tags)
    long_shares = _tag_shares(long_term, artist_tags)
    return {tag for tag, share in window_shares.items()
            if share < OVER_INDEX_RATIO * long_shares.get(tag, 0.0)}


def _seed_queries(
    kept_weights: Mapping[str, float],
    kept_tags: Mapping[str, Sequence[str]],
    played_weights: Mapping[str, float],
    history_shares: Mapping[str, float],
    limit: int,
) -> list[tuple[str, str, str]]:
    """Tag queries for ``limit`` seeds: the rarest kept tag of each of the heaviest played artists
    first, then the heaviest kept tags to fill the rest.

    Rarest means the smallest share of all history (``history_shares``), so a distinctive tag such
    as one an artist alone carries is seeded even when common tags outweigh it. Each heavy artist
    contributes one tag; a tag is seeded once."""
    heavy = sorted((a for a in played_weights if a in kept_tags),
                   key=lambda a: (-played_weights[a], a))[:limit]
    rarest = {
        artist: min(kept_tags[artist], key=lambda t: (history_shares.get(_key(t), 0.0), _key(t)))
        for artist in heavy
    }
    queries = select_supplementary_tag_queries(
        {artist: kept_weights[artist] for artist in heavy},
        {artist: [rarest[artist]] for artist in heavy}, [],
        profile_limit=limit, exploration_limit=0)
    seen = {_key(tag_from_query(query)) for query, _family, _style in queries}
    if len(queries) < limit:
        for query, family, style in select_supplementary_tag_queries(
                kept_weights, kept_tags, [], profile_limit=limit, exploration_limit=0):
            if len(queries) >= limit:
                break
            if _key(tag_from_query(query)) not in seen:
                seen.add(_key(tag_from_query(query)))
                queries.append((query, family, style))
    return queries


def current_tastes_plan(
    listens: Iterable[Mapping[str, Any]],
    artist_tags: Mapping[str, Sequence[Any]],
    *,
    similar: Mapping[str, Sequence[str]] | None = None,
    collaborators: Mapping[str, Sequence[str]] | None = None,
    limit: int = SEED_LIMIT,
) -> dict[str, Any]:
    """The seeds for Current tastes, with the report that explains them.

    Returns ``window_days``, ``window_listens``, ``excluded_tags`` (window tags the month under-represents
    long term), ``seeds`` (one entry per tag query: ``tag`` and ``query``) and ``queries``
    (the tag queries, in the shape ``run_deep_cuts_tag_supply`` takes). ``similar`` and
    ``collaborators`` are optional links; without them the window alone sets the weights."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")
    records = list(listens)
    window, days = recent_window(records)
    window_weights: Counter[str] = window_artist_weights(window)
    if similar:
        window_weights = expand_artist_weights(window_weights, similar, SIMILAR_DISCOUNT)
    if collaborators:
        window_weights = expand_artist_weights(window_weights, collaborators, COLLABORATOR_DISCOUNT)

    under_represented = _under_represented_tags(
        window_artist_weights(window), window_artist_weights(records), artist_tags)

    window_tags = {
        str(tag) for artist in window_weights for tag in artist_tags.get(artist, ()) if tag
    }
    excluded = sorted(tag for tag in window_tags if _key(tag) in under_represented)

    kept_tags: dict[str, list[str]] = {}
    for artist in window_weights:
        tags = [str(tag) for tag in artist_tags.get(artist, ()) if tag and _key(tag) not in under_represented]
        if tags:
            kept_tags[artist] = tags
    kept_weights = {artist: weight for artist, weight in window_weights.items() if artist in kept_tags}
    queries = _seed_queries(
        kept_weights, kept_tags, window_artist_weights(window),
        _tag_shares(window_artist_weights(records), artist_tags), limit)

    seeds = [{"tag": tag_from_query(query), "query": query} for query, _family, _style in queries]
    return {
        "window_days": days,
        "window_listens": len(window),
        "excluded_tags": excluded,
        "seeds": seeds,
        "queries": queries,
    }


def dominant_area(
    window_weights: Mapping[str, float],
    artist_areas: Mapping[str, str],
    *,
    min_share: float = MIN_AREA_SHARE,
) -> tuple[str, float] | None:
    """The area holding the largest share of the window weight, when it reaches ``min_share``.

    Returns ``(area, share)`` or None. The share is taken over all window weight, so artists
    without an area lower it. Ties go to the alphabetically first area."""
    total = sum(float(weight) for weight in window_weights.values())
    if total <= 0:
        return None
    share: Counter[str] = Counter()
    for artist, weight in window_weights.items():
        area = artist_areas.get(artist)
        if area:
            share[str(area)] += float(weight)
    if not share:
        return None
    area, weight = min(share.items(), key=lambda item: (-item[1], item[0]))
    return (area, weight / total) if weight / total >= min_share else None


def decade_shares(
    window_weights: Mapping[str, float],
    artist_years: Mapping[str, int],
) -> dict[int, float]:
    """Share of the window weight per decade (1970 for 1970 to 1979), over artists with a year."""
    total = sum(float(weight) for weight in window_weights.values())
    if total <= 0:
        return {}
    shares: Counter[int] = Counter()
    for artist, weight in window_weights.items():
        year = artist_years.get(artist)
        if isinstance(year, int) and not isinstance(year, bool):
            shares[year // 10 * 10] += float(weight) / total
    return dict(shares)


def era_match(release_year: Any, shares: Mapping[int, float]) -> float:
    """How strongly a release year matches the window's decades: that decade's share, else 0."""
    if isinstance(release_year, bool) or not isinstance(release_year, int):
        return 0.0
    return float(shares.get(release_year // 10 * 10, 0.0))


def current_tastes_context(
    listens: Iterable[Mapping[str, Any]],
    artist_areas: Mapping[str, str],
    artist_years: Mapping[str, int],
) -> dict[str, Any]:
    """The window's regional spine and decade shares, for ``ranking_boost``.

    ``spine_area`` is the area the window's weight is concentrated in (or None); ``decades`` maps
    decade starts to their share of the window weight. Pure: the caller supplies the areas and
    first years of the artists (``discovery.artist_profiles``)."""
    window, _days = recent_window(listens)
    weights = window_artist_weights(window)
    spine = dominant_area(weights, artist_areas)
    return {
        "spine_area": spine[0] if spine else None,
        "decades": decade_shares(weights, artist_years),
    }


def ranking_boost(
    *,
    artist_area: str | None,
    release_year: Any,
    spine_area: str | None,
    decades: Mapping[int, float],
) -> float:
    """The boost for one candidate: SPINE_BOOST when its artist is in the spine area, plus
    ERA_BOOST times the share of the release's decade. Zero when neither applies."""
    boost = 0.0
    if spine_area and artist_area == spine_area:
        boost += SPINE_BOOST
    return boost + ERA_BOOST * era_match(release_year, decades)
