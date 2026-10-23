"""ListenBrainz tag-radio supplementary lane (flagged, off by default).

Replaces the one-MusicBrainz-search-per-tag lane: one ``GET /1/lb-radio/tags`` per tag
returns recording MBIDs, and all of them resolve through the existing ListenBrainz
batch recording and release-group endpoints. No MusicBrainz request is made. The batch
endpoints carry no secondary release types, so the batch title-marker filter always
applies. The endpoint is undocumented in the public API docs.
"""
from typing import Any, Callable

from discovery.tag_queries import tag_from_query

LB_TAG_RADIO_URL = "https://api.listenbrainz.org/1/lb-radio/tags"
TAG_RADIO_CACHE_PREFIX = "lb:tag-radio:"
TAG_RADIO_TTL_SECONDS = 30 * 24 * 60 * 60
# Recordings per tag. About 5 albums per tag are used, and every recording costs batch
# lookups; a 50-per-tag run hit the HTML browser-verification page on the release-group
# endpoint once.
TAG_RADIO_COUNT = 20
CANDIDATES_PER_QUERY = 5
RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)
# All tag GETs run at once (at most this many); once the first answer is in, the rest get
# this long before they are dropped, so one slow tag cannot hold the lane.
MAX_PARALLEL_TAG_CALLS = 8
TAG_RADIO_STRAGGLER_SECONDS = 4.0
# Popularity band of the radio, in percent. Low percent is the most popular recordings, so
# 0-100 is the whole catalogue; the owner-approved Deep cuts band is 50-75.
TAG_RADIO_POP_BEGIN = 0
TAG_RADIO_POP_END = 100


def _radio_entries(raw) -> list[tuple[str, int]]:
    """(recording MBID, radio tag_count) pairs from a response or a cached value.

    Older cache entries are plain MBID strings and carry no count (0)."""
    entries: dict[str, int] = {}
    for item in raw or []:
        if isinstance(item, str):
            entries.setdefault(item, 0)
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            count = item[1] if type(item[1]) is int and item[1] > 0 else 0
            entries.setdefault(str(item[0]), count)
    return list(entries.items())


def _radio_cache_key(tag, pop_begin, pop_end, scope=None) -> str:
    """The default band and no scope keep the original key, so existing cache entries stay valid.

    ``scope`` (for example "lens:date") gives each lens and day its own sample of a tag."""
    key = f"{TAG_RADIO_CACHE_PREFIX}{tag.casefold()}"
    if (pop_begin, pop_end) != (TAG_RADIO_POP_BEGIN, TAG_RADIO_POP_END):
        key = f"{key}:pop{pop_begin}-{pop_end}"
    return f"{key}:{scope}" if scope else key


def _tag_radio_request(providers, tag, headers, pop_begin, pop_end) -> list[list]:
    """One tag-radio GET, as [recording MBID, tag_count] pairs in radio order.
    Network only, so it is safe to run on a worker thread."""
    response = providers.http_get(
        LB_TAG_RADIO_URL,
        params={"tag": tag, "operator": "OR", "pop_begin": pop_begin, "pop_end": pop_end,
                "count": TAG_RADIO_COUNT},
        headers=dict(headers), timeout=40,
    )
    if response.status_code != 200:
        raise _RadioHTTPError(response.status_code)
    body = response.json()
    if not isinstance(body, list):
        raise RuntimeError("tag radio returned a non-list body")
    pairs: dict[str, int] = {}
    for item in body:
        if isinstance(item, dict) and item.get("recording_mbid"):
            count = item.get("tag_count")
            pairs.setdefault(str(item["recording_mbid"]),
                             count if type(count) is int and count > 0 else 0)
    return [[mbid, count] for mbid, count in pairs.items()]


class _RadioHTTPError(RuntimeError):
    def __init__(self, status):
        super().__init__(f"tag radio returned HTTP {status}")
        self.status = status


def _cache_answer(providers, cache_key, future) -> None:
    try:
        providers.metadata_cache_set(cache_key, future.result())
    except Exception:
        pass


def _fetch_all_tag_recordings(providers, tags, headers, state, pop_begin, pop_end, scope=None):
    """Return {tag: mbids or Exception}. Cached tags answer immediately; the rest are
    fetched in parallel and the first answer wins: stragglers are dropped
    ``TAG_RADIO_STRAGGLER_SECONDS`` after the first response, but still cache their answer
    if one arrives later."""
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
    from recommendation_run_metrics import record_provider_call
    import time

    results: dict[str, Any] = {}
    pending: list[str] = []
    for tag in dict.fromkeys(tags):
        cached = providers.metadata_cache_get(
            _radio_cache_key(tag, pop_begin, pop_end, scope), ttl_seconds=TAG_RADIO_TTL_SECONDS)
        if cached is not None:
            state["hits"] += 1
            results[tag] = _radio_entries(cached)
        else:
            state["misses"] += 1
            pending.append(tag)
    if not pending:
        return results
    executor = ThreadPoolExecutor(max_workers=min(len(pending), MAX_PARALLEL_TAG_CALLS))
    try:
        futures = {}
        for tag in pending:
            record_provider_call("listenbrainz", "tag_radio")
            future = executor.submit(_tag_radio_request, providers, tag, headers, pop_begin, pop_end)
            # Cache on the worker thread, so a straggler that answers after the lane moved
            # on still warms the cache for the next run (one SQLite connection per call).
            cache_key = _radio_cache_key(tag, pop_begin, pop_end, scope)
            future.add_done_callback(lambda fut, key=cache_key: _cache_answer(providers, key, fut))
            futures[future] = tag
        waiting = set(futures)
        deadline = None
        while waiting:
            timeout = None if deadline is None else max(0.0, deadline - time.monotonic())
            done, waiting = wait(waiting, timeout=timeout, return_when=FIRST_COMPLETED)
            if not done:
                break
            for future in done:
                tag = futures[future]
                try:
                    results[tag] = _radio_entries(future.result())
                except Exception as exc:
                    results[tag] = exc
                    if isinstance(exc, _RadioHTTPError) and exc.status in RETRYABLE_STATUS_CODES:
                        state["unavailable"] = True
            if deadline is None:
                deadline = time.monotonic() + TAG_RADIO_STRAGGLER_SECONDS
        for future in waiting:
            results[futures[future]] = TimeoutError("tag radio straggler dropped")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return results


def run_lb_tag_queries(
    queries, *, providers, headers, albums, failures, state,
    resolve: Callable[[list[dict[str, str]]], dict[str, dict[str, Any]]],
    rejection: Callable[[dict[str, Any]], Any],
    merge_source: Callable[[dict[str, Any], str], Any],
    classify_error: Callable[[Exception], str],
    candidate_cap: int,
    pop_begin: int = TAG_RADIO_POP_BEGIN,
    pop_end: int = TAG_RADIO_POP_END,
    scope: str | None = None,
):
    """Add album candidates from tag radio. Same state and outcome contract as the
    MusicBrainz lane: one (added, error_class) pair per query attempted. ``pop_begin``
    and ``pop_end`` set the radio popularity band (percent, 0-100). ``scope`` keys the
    radio answers, so callers that need their own sample of a tag pass their own scope."""
    if not (0 <= pop_begin < pop_end <= 100):
        raise ValueError("tag radio popularity band must satisfy 0 <= begin < end <= 100")
    planned: list[tuple[str, str, str, str, list[tuple[str, int]], str | None]] = []
    tags = {query: tag_from_query(query) for query, _f, _s in queries}
    fetched = _fetch_all_tag_recordings(
        providers, [t for t in tags.values() if t], headers, state, pop_begin, pop_end, scope)
    for query, family, style in queries:
        tag = tags[query]
        mbids: list[tuple[str, int]] = []
        error_class = None
        if not tag:
            error_class = "invalid_query"
        else:
            got = fetched.get(tag)
            if isinstance(got, Exception):
                error_class = classify_error(got)
                failures.append({"source": "listenbrainz_tag_radio", "query": query,
                                 "error": str(got)})
            else:
                mbids = got or []
        planned.append((query, family, style, tag, mbids, error_class))

    wanted = list(dict.fromkeys(m for plan in planned for m, _count in plan[4]))
    try:
        recordings = resolve([{"recording_mbid": m} for m in wanted]) if wanted else {}
    except Exception as exc:
        recordings = {}
        failures.append({"source": "listenbrainz_tag_radio", "query": "resolve",
                         "error": str(exc)})

    outcomes = []
    for query, family, style, tag, mbids, error_class in planned:
        added = 0
        if error_class is None:
            source = "profile_tag_search" if style.startswith("profile:") else "exploration_tag_search"
            for mbid, tag_count in mbids:
                recording = recordings.get(mbid)
                if not recording:
                    continue
                credit = recording.get("artist-credit") or []
                artist = "".join(
                    p.get("name", "") + p.get("joinphrase", "") for p in credit if isinstance(p, dict)
                ).strip()
                first = next((p for p in credit if isinstance(p, dict) and p.get("name")), None)
                if not artist or first is None:
                    continue
                for release in recording.get("releases") or []:
                    group = release.get("release-group") or {}
                    state["seen"] += 1
                    if rejection(group):
                        continue
                    title = group.get("title", "").strip()
                    key = (providers.music_key(first["name"]), providers.music_key(title))
                    if key in albums:
                        existing = albums[key]
                        if tag_count > existing.get("tag_strength", 0):
                            existing["tag_strength"] = float(tag_count)
                        merge_source(existing, source)
                        families = existing.setdefault("regional_families", [])
                        if family not in families:
                            families.append(family)
                        styles = existing.setdefault("regional_styles", [])
                        if style not in styles:
                            styles.append(style)
                        continue
                    if state["added"] >= candidate_cap:
                        break
                    albums[key] = {
                        "artist": artist,
                        "primary_artist": first["name"],
                        "artist_mbid": (first.get("artist") or {}).get("id"),
                        "album": title,
                        "release_group_mbid": group.get("id"),
                        "score": 0.035,
                        "tag_strength": float(tag_count),
                        "tracks": [],
                        "discovery_source": "listenbrainz_tag_radio",
                        "discovery_sources": [source],
                        "regional_families": [family],
                        "regional_styles": [style],
                    }
                    state["added"] += 1
                    added += 1
                if added >= CANDIDATES_PER_QUERY or state["added"] >= candidate_cap:
                    break
        outcomes.append((added, error_class))
    return outcomes
