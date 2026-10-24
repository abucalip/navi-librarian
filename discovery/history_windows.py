"""History windows: artist-MBID weights for one listening window.

Feeds the tag-lane seed selection (``discovery.tag_queries``) with a window's artists
instead of the default 30-day profile. Pure: the caller supplies the listens.
See docs/engine2.md (Phase 3).
"""
from __future__ import annotations

from collections import Counter
import math
from collections.abc import Iterable, Mapping
from typing import Any

from discovery.recommendations import windowed_listen_weights


def _mapping_or_empty(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def listen_artist_mbid(listen: Mapping[str, Any]) -> str:
    """Return the artist MBID a ListenBrainz-shaped listen carries, or ``""``.

    Mirrors the gather path (``artist_mbid`` first, else the first of ``artist_mbids``), then
    falls back to ``track_metadata.mbid_mapping.artist_mbids``.
    Malformed nesting (a non-mapping ``track_metadata`` or ``additional_info``) yields ``""``."""
    track_metadata = _mapping_or_empty(_mapping_or_empty(listen).get("track_metadata"))
    additional_info = _mapping_or_empty(track_metadata.get("additional_info"))
    artist_mbid = additional_info.get("artist_mbid")
    if not artist_mbid:
        artist_mbids = additional_info.get("artist_mbids")
        if isinstance(artist_mbids, list) and artist_mbids:
            artist_mbid = artist_mbids[0]
    if not artist_mbid:
        # ListenBrainz keeps the matched artist here for most imported history.
        mapped = _mapping_or_empty(track_metadata.get("mbid_mapping")).get("artist_mbids")
        if isinstance(mapped, list) and mapped:
            artist_mbid = mapped[0]
    if isinstance(artist_mbid, (str, int)) and str(artist_mbid):
        return str(artist_mbid)
    return ""


def _listen_time(listen: Mapping[str, Any]) -> float | None:
    try:
        value = float(listen.get("listened_at"))
    except (TypeError, ValueError, AttributeError):
        return None
    return value if math.isfinite(value) else None


def _positive_days(value: Any) -> float:
    """Return ``value`` as a positive finite number of days, or raise ``ValueError``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("window_days must be a positive finite number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError("window_days must be a positive finite number")
    return float(value)


def densest_window_listens(
    listens: Iterable[Mapping[str, Any]],
    window_days: float,
) -> list[Mapping[str, Any]]:
    """Return the listens inside the ``window_days`` span holding the most dated listens.

    Undated listens are ignored. Ties go to the earliest span. Empty when nothing is dated.
    Raises ``ValueError`` for any ``window_days`` that is not a positive finite number,
    including non-numeric values.
    """
    window_days = _positive_days(window_days)
    width = window_days * 24 * 60 * 60
    dated = sorted(
        ((time, listen) for listen in listens if (time := _listen_time(listen)) is not None),
        key=lambda item: item[0],
    )
    best_start, best_count = 0, 0
    end = 0
    for start in range(len(dated)):
        if end < start:
            end = start
        while end < len(dated) and dated[end][0] - dated[start][0] <= width:
            end += 1
        if end - start > best_count:
            best_start, best_count = start, end - start
    if best_count == 0:
        return []
    first, last = best_start, best_start + best_count
    return [listen for _time, listen in dated[first:last]]


def window_artist_weights(
    listens: Iterable[Mapping[str, Any]],
    *,
    window_days: float | None = None,
    half_life_days: float | None = None,
) -> Counter[str]:
    """Return {artist MBID: weight} for one window, using ``windowed_listen_weights``.

    Listens without an artist MBID contribute nothing. The result can be passed as the
    ``recent_artist_weights`` argument of ``select_supplementary_tag_queries``.
    """
    records = list(listens)
    weights = windowed_listen_weights(
        records, window_days=window_days, half_life_days=half_life_days,
    )
    totals: Counter[str] = Counter()
    for listen, weight in zip(records, weights):
        artist_mbid = listen_artist_mbid(listen)
        if artist_mbid and weight > 0:
            totals[artist_mbid] += weight
    return totals


def _artist_listen_times(
    listens: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, list[float]], float | None]:
    """Dated listen times per artist MBID, and the newest dated listen overall.

    Undated listens and listens without an artist MBID are ignored."""
    times: dict[str, list[float]] = {}
    newest: float | None = None
    for listen in listens:
        time = _listen_time(listen)
        artist_mbid = listen_artist_mbid(listen)
        if time is None or not artist_mbid:
            continue
        times.setdefault(artist_mbid, []).append(time)
        newest = time if newest is None else max(newest, time)
    return times, newest


def _artists_idle_since(
    listens: Iterable[Mapping[str, Any]], idle_days: float, min_listens: int,
) -> Counter[str]:
    """{artist MBID: listen count} for artists with at least ``min_listens`` listens and none
    within ``idle_days`` of the newest dated listen overall."""
    idle_days = _positive_days(idle_days)
    if isinstance(min_listens, bool) or not isinstance(min_listens, int) or min_listens < 1:
        raise ValueError("min_listens must be a positive integer")
    times, newest = _artist_listen_times(listens)
    if newest is None:
        return Counter()
    cutoff = newest - idle_days * 24 * 60 * 60
    return Counter({
        artist: len(stamps) for artist, stamps in times.items()
        if len(stamps) >= min_listens and max(stamps) < cutoff
    })


def dormant_artist_weights(
    listens: Iterable[Mapping[str, Any]],
    *,
    dormant_days: float = 365,
    min_listens: int = 1,
) -> Counter[str]:
    """Rediscovery profile: flat weights (listen counts) for artists once played at least
    ``min_listens`` times and not at all in the last ``dormant_days``, measured back from the
    newest dated listen. Pass the result as ``recent_artist_weights`` of
    ``select_supplementary_tag_queries``."""
    return _artists_idle_since(listens, dormant_days, min_listens)


def dominant_tags(
    weights: Mapping[str, float],
    artist_tags: Mapping[str, Iterable[str]],
    *,
    top_artists: int = 40,
    count: int = 5,
) -> set[str]:
    """The ``count`` most common tags among the ``top_artists`` heaviest artists.

    ``artist_tags`` maps artist MBID to tags; artists without an entry add nothing."""
    for value in (top_artists, count):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError("top_artists and count must be positive integers")
    heaviest = sorted(weights, key=lambda artist: -weights[artist])[:top_artists]
    tally = Counter(tag for artist in heaviest for tag in set(artist_tags.get(artist, ())))
    return {tag for tag, _ in tally.most_common(count)}


def artists_with_tags(artist_tags: Mapping[str, Iterable[str]], tags: Iterable[str]) -> set[str]:
    """Artist MBIDs carrying at least one of ``tags``."""
    wanted = set(tags)
    return {artist for artist, own in artist_tags.items() if wanted.intersection(own)}


def repeated_track_artist_weights(
    listens: Iterable[Mapping[str, Any]],
    *,
    min_track_plays: int = 5,
    exclude_artists: Iterable[str] = (),
    only_artists: Iterable[str] | None = None,
) -> Counter[str]:
    """Repeated-track profile: per artist, the plays of tracks played at least
    ``min_track_plays`` times. A track is an artist MBID plus a case-folded track name;
    listens without either are ignored.

    ``exclude_artists`` drops artists (for example those with the dominant tags, see
    ``dominant_tags``); ``only_artists`` keeps only the given artists (for example those
    with known tags)."""
    if isinstance(min_track_plays, bool) or not isinstance(min_track_plays, int) or min_track_plays < 1:
        raise ValueError("min_track_plays must be a positive integer")
    plays: Counter[tuple[str, str]] = Counter()
    for listen in listens:
        artist_mbid = listen_artist_mbid(listen)
        name = _mapping_or_empty(_mapping_or_empty(listen).get("track_metadata")).get("track_name")
        track = " ".join(name.casefold().split()) if isinstance(name, str) else ""
        if artist_mbid and track:
            plays[(artist_mbid, track)] += 1
    excluded = set(exclude_artists)
    allowed = None if only_artists is None else set(only_artists)
    totals: Counter[str] = Counter()
    for (artist_mbid, _track), count in plays.items():
        if count < min_track_plays or artist_mbid in excluded:
            continue
        if allowed is not None and artist_mbid not in allowed:
            continue
        totals[artist_mbid] += count
    return totals


def burst_artist_weights(
    listens: Iterable[Mapping[str, Any]],
    *,
    min_listens: int = 20,
    span_days: float = 30,
    min_share: float = 0.7,
) -> Counter[str]:
    """Obsession profile: listen counts for artists with at least ``min_listens`` dated
    listens, ``min_share`` or more of them inside one span of ``span_days``."""
    span_days = _positive_days(span_days)
    if isinstance(min_listens, bool) or not isinstance(min_listens, int) or min_listens < 1:
        raise ValueError("min_listens must be a positive integer")
    if (isinstance(min_share, bool) or not isinstance(min_share, (int, float))
            or not math.isfinite(min_share) or not 0 < min_share <= 1):
        raise ValueError("min_share must be a number above 0 and at most 1")
    width = span_days * 24 * 60 * 60
    times, _newest = _artist_listen_times(listens)
    totals: Counter[str] = Counter()
    for artist_mbid, stamps in times.items():
        if len(stamps) < min_listens:
            continue
        stamps.sort()
        best, start = 0, 0
        for end, stamp in enumerate(stamps):
            while stamp - stamps[start] > width:
                start += 1
            best = max(best, end - start + 1)
        if best / len(stamps) >= min_share:
            totals[artist_mbid] = len(stamps)
    return totals


def new_artist_weights(
    listens: Iterable[Mapping[str, Any]],
    *,
    first_heard_since: float,
) -> Counter[str]:
    """New-artist profile: listen counts for artists whose first dated listen is at or after
    ``first_heard_since`` (epoch seconds)."""
    if (isinstance(first_heard_since, bool) or not isinstance(first_heard_since, (int, float))
            or not math.isfinite(first_heard_since)):
        raise ValueError("first_heard_since must be a finite number of epoch seconds")
    times, _newest = _artist_listen_times(listens)
    return Counter({
        artist: len(stamps) for artist, stamps in times.items() if min(stamps) >= first_heard_since
    })
