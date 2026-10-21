"""ListenBrainz tag-radio supplementary lane (flagged, off by default).

Replaces the one-MusicBrainz-search-per-tag lane: one ``GET /1/lb-radio/tags`` per tag
returns recording MBIDs, and all of them resolve through the existing ListenBrainz
batch recording and release-group endpoints. No MusicBrainz request is made. The batch
endpoints carry no secondary release types, so the batch title-marker filter always
applies. The endpoint is undocumented in the public API docs.
"""
from typing import Any, Callable

from discovery_tag_queries import tag_from_query

LB_TAG_RADIO_URL = "https://api.listenbrainz.org/1/lb-radio/tags"
TAG_RADIO_CACHE_PREFIX = "lb:tag-radio:"
TAG_RADIO_TTL_SECONDS = 30 * 24 * 60 * 60
# Recordings per tag. About 5 albums per tag are used, and every recording costs batch
# lookups; a 50-per-tag run hit the HTML browser-verification page on the release-group
# endpoint once.
TAG_RADIO_COUNT = 20
CANDIDATES_PER_QUERY = 5
RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)


def _fetch_tag_recordings(providers, tag, headers, state) -> list[str]:
    from recommendation_run_metrics import record_provider_call

    cache_key = f"{TAG_RADIO_CACHE_PREFIX}{tag.casefold()}"
    cached = providers.metadata_cache_get(cache_key, ttl_seconds=TAG_RADIO_TTL_SECONDS)
    if cached is not None:
        state["hits"] += 1
        return list(cached)
    state["misses"] += 1
    record_provider_call("listenbrainz", "tag_radio")
    response = providers.http_get(
        LB_TAG_RADIO_URL,
        params={"tag": tag, "operator": "OR", "pop_begin": 0, "pop_end": 100,
                "count": TAG_RADIO_COUNT},
        headers=dict(headers), timeout=40,
    )
    if response.status_code in RETRYABLE_STATUS_CODES:
        state["unavailable"] = True
    if response.status_code != 200:
        raise RuntimeError(f"tag radio returned HTTP {response.status_code}")
    body = response.json()
    if not isinstance(body, list):
        raise RuntimeError("tag radio returned a non-list body")
    mbids = list(dict.fromkeys(
        str(item["recording_mbid"]) for item in body
        if isinstance(item, dict) and item.get("recording_mbid")
    ))
    providers.metadata_cache_set(cache_key, mbids)
    return mbids


def run_lb_tag_queries(
    queries, *, providers, headers, albums, failures, state,
    resolve: Callable[[list[dict[str, str]]], dict[str, dict[str, Any]]],
    rejection: Callable[[dict[str, Any]], Any],
    merge_source: Callable[[dict[str, Any], str], Any],
    classify_error: Callable[[Exception], str],
    candidate_cap: int,
):
    """Add album candidates from tag radio. Same state and outcome contract as the
    MusicBrainz lane: one (added, error_class) pair per query attempted."""
    planned: list[tuple[str, str, str, str, list[str], str | None]] = []
    for query, family, style in queries:
        if state["unavailable"]:
            break
        tag = tag_from_query(query)
        mbids: list[str] = []
        error_class = None
        if not tag:
            error_class = "invalid_query"
        else:
            try:
                mbids = _fetch_tag_recordings(providers, tag, headers, state)
            except Exception as exc:
                error_class = classify_error(exc)
                failures.append({"source": "listenbrainz_tag_radio", "query": query,
                                 "error": str(exc)})
        planned.append((query, family, style, tag, mbids, error_class))

    wanted = list(dict.fromkeys(m for plan in planned for m in plan[4]))
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
            for mbid in mbids:
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
