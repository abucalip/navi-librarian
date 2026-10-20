"""Injected provider orchestration for new-music recommendations."""
from collections import Counter
from dataclasses import dataclass
from datetime import timezone
from email.utils import parsedate_to_datetime
from recommendation_run_metrics import add_stage_seconds, timed_stage
import json
import math
import time
from typing import Any, Callable

import discovery_candidate_supply as _supply
from discovery_batch_metadata import (
    fetch_batch_recordings,
    fetch_release_group_metadata,
    synthesize_recording,
)
from discovery_candidate_supply import (
    batch_title_marker_rejection,
    cf_release_group_rejection,
    classify_error,
    recording_artist_key,
    summarize_cf_albums,
    summarize_cf_recordings,
    summarize_supplementary_yield,
)
from discovery_recommendations import decayed_listen_weights, merge_discovery_source

_RETRYABLE_STATUS_CODES = (429, 500, 502, 503, 504)
_GENRE_LOOKUP_ATTEMPTS = 3
# Supplementary tag searches get one retry (one 2 s backoff). MusicBrainz declines
# over-limit requests with 503 until the rate drops, so the lane stops after a
# query that exhausts this budget instead of sending more requests.
_TAG_SEARCH_ATTEMPTS = 2
# Genre-stage circuit breaker (flagged, off by default). When enabled, the stage
# stops after this many consecutive artist lookups exhaust their retries, so a
# throttled MusicBrainz is not asked about every remaining artist. Default output
# is unchanged while the flag is off.
GENRE_CIRCUIT_BREAKER_ENABLED = False
GENRE_CIRCUIT_BREAKER_THRESHOLD = 3

# Retry-After is honored only on these statuses, and any honored wait is capped so
# a large header value cannot stall a run. Missing or unparseable values fall back
# to the fixed backoff.
_RETRY_AFTER_STATUS_CODES = (429, 503)
_RETRY_AFTER_MAX_SECONDS = 10.0


def _provider_for_url(url):
    """Return a coarse provider label for a request URL (no URL is recorded)."""
    if "musicbrainz.org" in url:
        return "musicbrainz"
    if "listenbrainz.org" in url:
        return "listenbrainz"
    return "other"


def _retry_after_seconds(response, *, now=None):
    """Return the Retry-After wait in seconds (seconds or HTTP-date form), or None."""
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    raw = headers.get("Retry-After")
    if raw is None:
        return None
    value = str(raw).strip()
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return None
        if retry_at is None:
            return None
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        current = now if now is not None else time.time()
        seconds = retry_at.timestamp() - current
    if not math.isfinite(seconds):
        return None
    return min(max(seconds, 0.0), _RETRY_AFTER_MAX_SECONDS)


def _get_with_bounded_retry(
    client,
    url,
    *,
    params,
    headers,
    sleep,
    attempts=_GENRE_LOOKUP_ATTEMPTS,
    honor_retry_after=False,
):
    """Retry transient MusicBrainz statuses a bounded number of times; never cache here.

    With ``honor_retry_after`` set, a 429/503 response's Retry-After value (capped at
    ``_RETRY_AFTER_MAX_SECONDS``) replaces the fixed backoff for that wait.
    """
    response = None
    from recommendation_run_metrics import record_provider_call

    for attempt in range(attempts):
        record_provider_call(_provider_for_url(url), "bounded_get")
        response = client.get(url, params=params, headers=headers)
        if response.status_code not in _RETRYABLE_STATUS_CODES:
            return response
        if attempt < attempts - 1:
            wait = None
            if honor_retry_after and response.status_code in _RETRY_AFTER_STATUS_CODES:
                wait = _retry_after_seconds(response)
            sleep(wait if wait is not None else 2 * (attempt + 1))
    return response


@dataclass(frozen=True)
class RecommendationProviders:
    listenbrainz_recent: Callable[..., Any]
    listenbrainz_username: Callable[[], str]
    music_key: Callable[[str], str]
    metadata_cache_get: Callable[..., Any]
    metadata_cache_set: Callable[..., Any]
    is_album_candidate: Callable[..., bool]
    api_call: Callable[..., Any]
    items: Callable[..., Any]
    http_get: Callable[..., Any]
    http_client: Callable[..., Any]
    sleep: Callable[[float], Any]
    # Optional. Only the flagged batch path uses it; None keeps per-recording lookups.
    http_post: Callable[..., Any] | None = None
    # Optional. Returns stored feedback rows; None keeps tag-query selection unseeded.
    feedback_rows: Callable[[], Any] | None = None

# Bounded CF replenishment. One ListenBrainz call per page; the first page is
# required, later pages may fail without discarding earlier pages.
CF_PAGE_SIZE = 100
CF_MAX_PAGES = 2
# Uncached MusicBrainz resolutions per run. Cached recordings cost no call.
CF_MAX_UNCACHED_RESOLUTIONS = 100
# Flagged batch resolution (off by default). Uncached recordings are looked up through
# ListenBrainz batch endpoints instead of one MusicBrainz call each. It runs only when
# the batch title-marker filter is also enabled, because the batch endpoints return no
# secondary release types. Any batch failure falls back to per-recording lookups.
CF_BATCH_RESOLUTION_ENABLED = False
# Cold-start batch path: used only when no stored personal list exists yet, so the
# first build is fast. Steady-state builds are unaffected. Its output has no secondary
# release-type filter beyond the title markers, so it is a labelled first-run list.
COLD_START_BATCH_ENABLED = True
# Steady-state (warm) batch path, owner-approved 2026-10-21: uncached recordings go
# through the batch endpoints, and batch results are cached under their own key so a
# later run does not re-resolve them. Same title-marker limitation as the cold path.
WARM_BATCH_ENABLED = True
BATCH_RECORDING_CACHE_PREFIX = "mb:recording_batch:"
BATCH_RECORDING_TTL_SECONDS = 180 * 24 * 60 * 60
# Recordings per artist resolved before further cached recordings are skipped.
# The CF endpoint returns no artist, so uncached recordings must still be
# resolved to learn their artist; the cap can only skip cache-known artists.
CF_ARTIST_RESOLUTION_CAP = 10
# Supplementary tag lane: candidate cap per run, and the extra tag queries a
# replenishment pass may issue when eligible unowned supply is short. Each extra
# query costs at most one 1.1 s spacing sleep plus one 2 s retry backoff.
SUPPLEMENTARY_CANDIDATE_CAP = 60
REPLENISH_EXTRA_QUERIES = 2
# Tag-lane early stop (flagged, off by default). When off, the lane stops at the first
# query that exhausts its retries, as before. When on, the lane keeps going after an
# exhausted query and stops only after this many consecutive exhausted queries, so one
# throttled search does not end the lane while the total request count stays bounded.
TAG_LANE_EARLY_STOP_ENABLED = False
TAG_LANE_EXHAUSTION_THRESHOLD = 2
# Top CF candidate-pool artists whose genres are prefetched before the tag lane.
CANDIDATE_PREFETCH_LIMIT = 5
SHORTLIST_TARGET_DEFAULT = 10
CF_RECOMMENDATION_URL = (
    "https://api.listenbrainz.org/1/cf/recommendation/user/{username}/recording"
)


def _fetch_cf_recommendations(providers: RecommendationProviders) -> tuple[list[Any], dict[str, Any]]:
    """Fetch up to CF_MAX_PAGES pages of CF recordings, deduplicated by MBID.

    Raises when the first page fails. A later page failure stops paging and is
    reported by class only.
    """
    url = CF_RECOMMENDATION_URL.format(username=providers.listenbrainz_username())
    recordings: list[Any] = []
    seen_mbids: set[str] = set()
    paging = {"pages_requested": 0, "pages_fetched": 0, "page_failure_class": None,
              "total_mbid_count": None}
    for page in range(CF_MAX_PAGES):
        paging["pages_requested"] += 1
        try:
            from recommendation_run_metrics import record_provider_call

            record_provider_call("listenbrainz", "cf_recommendations")
            response = providers.http_get(
                url,
                params={"count": CF_PAGE_SIZE, "offset": page * CF_PAGE_SIZE},
                headers={"User-Agent": "NavidromeLibrarian/1.0"},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json().get("payload", {})
            items = payload.get("mbids", [])
        except Exception as exc:
            if page == 0:
                raise
            paging["page_failure_class"] = classify_error(exc)
            break
        paging["pages_fetched"] += 1
        # Aggregate pool size from the response already fetched; no extra request.
        total = payload.get("total_mbid_count")
        if page == 0 and isinstance(total, int) and not isinstance(total, bool) and total >= 0:
            paging["total_mbid_count"] = total
        for item in items[:CF_PAGE_SIZE]:
            mbid = item.get("recording_mbid") if isinstance(item, dict) else None
            if not mbid or str(mbid) in seen_mbids:
                continue
            seen_mbids.add(str(mbid))
            recordings.append(item)
        if len(items) < CF_PAGE_SIZE:
            break
    return recordings, paging


def _batch_resolution_enabled(providers: RecommendationProviders, cold_start: bool = False) -> bool:
    # Cold-start and warm batch paths have separate switches. The legacy opt-in
    # path requires both CF_BATCH_RESOLUTION_ENABLED and the title-filter flag.
    if providers.http_post is None:
        return False
    if (COLD_START_BATCH_ENABLED if cold_start else WARM_BATCH_ENABLED):
        return True
    return (
        CF_BATCH_RESOLUTION_ENABLED
        and _supply.BATCH_TITLE_FILTER_ENABLED
    )


def _prefetch_batch_recordings(
    providers: RecommendationProviders, recommendations: list[Any], *, headers: dict[str, str],
) -> dict[str, dict[str, Any]]:
    """Return MusicBrainz-shaped recordings for uncached CF recordings, keyed by MBID.

    Covers every uncached recording the CF pages returned (batch requests carry
    100 each), so batch hits do not spend the per-recording MusicBrainz budget.
    Returns {} on any batch failure, so the loop uses per-recording lookups.
    """
    uncached: list[str] = []
    cached_batch: dict[str, dict[str, Any]] = {}
    for item in recommendations:
        mbid = item.get("recording_mbid") if isinstance(item, dict) else None
        if not mbid or providers.metadata_cache_get(
            f"mb:recording:{mbid}", ttl_seconds=180 * 24 * 60 * 60,
        ) is not None:
            continue
        # Batch results live under their own key: they lack secondary release types,
        # so they must never satisfy the full per-recording lookup.
        known = providers.metadata_cache_get(
            f"{BATCH_RECORDING_CACHE_PREFIX}{mbid}", ttl_seconds=BATCH_RECORDING_TTL_SECONDS,
        )
        if known is not None:
            cached_batch[str(mbid)] = known
            continue
        uncached.append(str(mbid))
    if not uncached:
        return cached_batch
    try:
        entries = fetch_batch_recordings(providers.http_post, uncached, headers=headers)
        release_group_ids = [
            str(((entry.get("release") or {}).get("release_group_mbid")))
            for entry in entries.values()
            if (entry.get("release") or {}).get("release_group_mbid")
        ]
        # A release-group chunk that still fails after one retry is skipped, not fatal:
        # recordings that depend on it stay out of the batch result (and out of the
        # cache) and fall back to per-recording lookups; the rest keep their batch hit.
        failed_groups: set[str] = set()
        release_groups = fetch_release_group_metadata(
            providers.http_get, release_group_ids, headers=headers,
            retries=1, sleep=providers.sleep, failed=failed_groups,
        ) if release_group_ids else {}
    except Exception:
        return cached_batch
    recordings = dict(cached_batch)
    for mbid, entry in entries.items():
        if str((entry.get("release") or {}).get("release_group_mbid")) in failed_groups:
            continue
        recording = synthesize_recording(
            entry, release_groups,
            # The batch path always filters titles: its endpoints return no secondary types.
            title_rejection=lambda title: batch_title_marker_rejection(title, enabled=True),
        )
        if recording is not None:
            recordings[mbid] = recording
            try:
                providers.metadata_cache_set(f"{BATCH_RECORDING_CACHE_PREFIX}{mbid}", recording)
            except Exception:
                pass  # caching is an optimisation; never fail the run for it
    return recordings


def _run_tag_queries(
    queries, *, providers, client, headers, albums, failures, state,
):
    """Run supplementary MusicBrainz tag searches and add new album candidates.

    ``state`` holds counters and the lane-unavailable flag shared by every pass,
    so the candidate cap and the stop-on-exhausted-retry rule also bound
    replenishment. Returns one (added, error_class) pair per query attempted.
    """
    outcomes = []
    for query, regional_family, regional_style in queries:
        if state["added"] >= SUPPLEMENTARY_CANDIDATE_CAP or state["unavailable"]:
            break
        regional_query_added = 0
        query_error_class = None
        cache_key = f"mb:release-group-search:{query}"
        try:
            search_data = providers.metadata_cache_get(
                cache_key,
                ttl_seconds=30 * 24 * 60 * 60,
            )
            if search_data is None:
                state["misses"] += 1
            else:
                state["hits"] += 1

            if search_data is None:
                if state["request_index"]:
                    providers.sleep(1.1)

                response = _get_with_bounded_retry(
                    client,
                    "https://musicbrainz.org/ws/2/release-group/",
                    params={
                        "query": query,
                        "fmt": "json",
                        "limit": 10,
                    },
                    headers=headers,
                    sleep=providers.sleep,
                    attempts=_TAG_SEARCH_ATTEMPTS,
                )
                state["request_index"] += 1
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    state["exhausted_run"] += 1
                    if (
                        not TAG_LANE_EARLY_STOP_ENABLED
                        or state["exhausted_run"] >= TAG_LANE_EXHAUSTION_THRESHOLD
                    ):
                        state["unavailable"] = True
                else:
                    state["exhausted_run"] = 0
                response.raise_for_status()
                search_data = response.json()
                providers.metadata_cache_set(cache_key, search_data)

            for group in search_data.get("release-groups", []):
                state["seen"] += 1

                if group.get("primary-type") != "Album":
                    continue

                secondary_types = {
                    str(value).casefold()
                    for value in group.get("secondary-types", [])
                }
                if secondary_types & {
                    "compilation", "soundtrack", "live",
                    "remix", "dj-mix",
                }:
                    continue

                album_title = group.get("title", "").strip()
                if not album_title or not providers.is_album_candidate({
                    "album": album_title,
                    "primary_type": group.get("primary-type"),
                    "secondary_types": group.get("secondary-types", []),
                }):
                    continue

                credit = group.get("artist-credit", [])
                artist = "".join(
                    part.get("name", "") + part.get("joinphrase", "")
                    for part in credit
                    if isinstance(part, dict)
                ).strip()

                primary_artist = next(
                    (
                        part.get("name", "")
                        for part in credit
                        if isinstance(part, dict) and part.get("name")
                    ),
                    artist,
                )

                artist_mbid = next(
                    (
                        part.get("artist", {}).get("id")
                        for part in credit
                        if isinstance(part, dict)
                        and isinstance(part.get("artist"), dict)
                        and part["artist"].get("id")
                    ),
                    None,
                )

                if not artist or not primary_artist:
                    continue

                key = (
                    providers.music_key(primary_artist),
                    providers.music_key(album_title),
                )

                source = (
                    "profile_tag_search"
                    if regional_style.startswith("profile:")
                    else "exploration_tag_search"
                )
                if key in albums:
                    albums[key]["discovery_source"] = (
                        albums[key].get("discovery_source", "listenbrainz")
                    )
                    merge_discovery_source(albums[key], source)
                    regional_families = albums[key].setdefault(
                        "regional_families", []
                    )
                    if regional_family not in regional_families:
                        regional_families.append(regional_family)
                    regional_styles = albums[key].setdefault("regional_styles", [])
                    if regional_style not in regional_styles:
                        regional_styles.append(regional_style)
                    continue

                if state["added"] >= SUPPLEMENTARY_CANDIDATE_CAP:
                    break

                albums[key] = {
                    "artist": artist,
                    "primary_artist": primary_artist,
                    "artist_mbid": artist_mbid,
                    "album": album_title,
                    "score": 0.035,
                    "tracks": [],
                    "discovery_source": "musicbrainz_tag_search",
                    "discovery_sources": [source],
                    "regional_families": [regional_family],
                    "regional_styles": [regional_style],
                }
                state["added"] += 1
                regional_query_added += 1
                if regional_query_added >= 5:
                    break

            if state["added"] >= SUPPLEMENTARY_CANDIDATE_CAP:
                break

        except Exception as exc:
            query_error_class = classify_error(exc)
            failures.append({
                "source": "musicbrainz_tag_search",
                "query": query,
                "error": str(exc),
            })
        finally:
            # Runs on the cap break inside the try, so the final query is recorded too.
            outcomes.append((regional_query_added, query_error_class))
    return outcomes


def count_eligible_unowned_albums(albums, library_by_title, music_key) -> int:
    """Count unique candidate albums that could reach the shortlist.

    Mirrors the caller's ownership check: an exact artist and title match is
    owned, and a same-title album under another artist is a title conflict that
    goes to review. Neither counts as eligible supply.
    """
    identities = set()
    for candidate in albums.values():
        same_title = library_by_title.get(music_key(candidate["album"]), [])
        exact_owned = any(
            music_key(match.get("artist", "")) == music_key(candidate["primary_artist"])
            for match in same_title
        )
        if not exact_owned and not same_title:
            identities.add((music_key(candidate["primary_artist"]), music_key(candidate["album"])))
    return len(identities)


@timed_stage('candidate_gathering')
def gather_recommendation_candidates(
    providers: RecommendationProviders,
    *,
    shortlist_target: int = SHORTLIST_TARGET_DEFAULT,
    cold_start: bool = False,
) -> dict[str, Any] | str:
    """Gather providers in legacy order; early errors retain their JSON contract."""
    import time
    import httpx
    try:
        listens = providers.listenbrainz_recent(days=30)
    except Exception as exc:
        return json.dumps({
            "error": f"Could not retrieve recent listening history: {exc}"
        }, ensure_ascii=False, indent=2)

    recent_artists = Counter()
    recent_artist_play_counts = Counter()
    recent_artist_mbid_counts = Counter()
    mbid_by_artist_key = {}
    listens_with_artist_mbid = 0
    listen_weights = decayed_listen_weights(listens, half_life_days=14.0)
    for listen, weight in zip(listens, listen_weights):
        metadata = listen.get("track_metadata", {})
        artist = metadata.get("artist_name")
        if artist:
            key = providers.music_key(artist)
            recent_artists[key] += weight
            recent_artist_play_counts[key] += 1
        additional_info = metadata.get("additional_info", {})
        artist_mbid = additional_info.get("artist_mbid")
        artist_mbids = additional_info.get("artist_mbids", [])
        if not artist_mbid and isinstance(artist_mbids, list) and artist_mbids:
            artist_mbid = artist_mbids[0]
        if artist_mbid:
            recent_artist_mbid_counts[artist_mbid] += weight
            listens_with_artist_mbid += 1
            if artist:
                mbid_by_artist_key.setdefault(providers.music_key(artist), artist_mbid)

    try:
        recommendations, cf_paging = _fetch_cf_recommendations(providers)
        cf_recordings_returned = len(recommendations)
        cf_recording_mbids = [
            str(item["recording_mbid"]) for item in recommendations
        ]
    except Exception as exc:
        return json.dumps({
            "error": f"Could not retrieve ListenBrainz recommendations: {exc}"
        }, ensure_ascii=False, indent=2)

    if not recommendations:
        return json.dumps({
            "recommendations": [],
            "message": "ListenBrainz returned no recording recommendations."
        }, ensure_ascii=False, indent=2)

    # Resolve a bounded number of recordings through MusicBrainz.
    # Group tracks by album before checking Navidrome.
    albums = {}
    cf_recordings_resolved = 0
    cf_recording_records = []
    failures = []
    headers = {
        "User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"
    }

    artist_resolved_counts = Counter()
    resolution_calls = 0
    cf_skips = Counter()
    metadata_started = time.monotonic()
    batch_recordings = (
        _prefetch_batch_recordings(providers, recommendations, headers=headers)
        if _batch_resolution_enabled(providers, cold_start) else {}
    )
    with providers.http_client(timeout=20, follow_redirects=True) as client:
        for item in recommendations:
            mbid = item.get("recording_mbid")
            if not mbid:
                continue

            record = {"resolved": False, "artist_key": None, "error_class": None}
            recorded = False
            try:
                recording = providers.metadata_cache_get(
                    f"mb:recording:{mbid}",
                    ttl_seconds=180 * 24 * 60 * 60,
                )
                if recording is not None:
                    cf_skips["cache_known"] += 1
                    # Artist cap before any call: only cache-known artists can be
                    # skipped, because the CF response carries no artist.
                    cached_artist = recording_artist_key(recording, providers.music_key)
                    if cached_artist and artist_resolved_counts[cached_artist] >= CF_ARTIST_RESOLUTION_CAP:
                        cf_skips["artist_cap"] += 1
                        continue
                elif resolution_calls >= CF_MAX_UNCACHED_RESOLUTIONS and str(mbid) not in batch_recordings:
                    cf_skips["resolution_budget"] += 1
                    continue
                cf_recording_records.append(record)
                recorded = True

                if recording is None and str(mbid) in batch_recordings:
                    # Batch hit: no MusicBrainz call, no spacing sleep, no cache write,
                    # so it does not spend the uncached MusicBrainz budget.
                    recording = batch_recordings[str(mbid)]
                if recording is None:
                    if resolution_calls:
                        providers.sleep(1.1)
                    resolution_calls += 1

                    response = None
                    for attempt in range(3):
                        from recommendation_run_metrics import record_provider_call

                        record_provider_call("musicbrainz", "recording_lookup")
                        response = client.get(
                            f"https://musicbrainz.org/ws/2/recording/{mbid}",
                            params={
                                "fmt": "json",
                                "inc": "artists+releases+release-groups",
                            },
                            headers=headers,
                        )
                        if response.status_code not in (
                            429, 500, 502, 503, 504
                        ):
                            break
                        if attempt < 2:
                            providers.sleep(2 * (attempt + 1))

                    response.raise_for_status()
                    recording = response.json()
                    providers.metadata_cache_set(f"mb:recording:{mbid}", recording)

                cf_recordings_resolved += 1
                record["resolved"] = True
                credit = recording.get("artist-credit", [])
                artist = "".join(
                    part.get("name", "") + part.get("joinphrase", "")
                    for part in credit
                    if isinstance(part, dict)
                ).strip()
                primary_artist = next(
                    (
                        part.get("name", "")
                        for part in credit
                        if isinstance(part, dict) and part.get("name")
                    ),
                    artist,
                )
                if not artist:
                    artist = primary_artist
                record["artist_key"] = providers.music_key(primary_artist) if primary_artist else None
                if record["artist_key"]:
                    artist_resolved_counts[record["artist_key"]] += 1

                primary_artist_mbid = next(
                    (
                        part.get("artist", {}).get("id")
                        for part in credit
                        if isinstance(part, dict)
                        and isinstance(part.get("artist"), dict)
                        and part["artist"].get("id")
                    ),
                    None,
                )

                releases = recording.get("releases", [])
                album_groups = {}

                # Prefer album release-groups that are not compilations,
                # soundtracks, live albums, remixes, or DJ mixes, and skip
                # sampler albums and retrospective collections. The same rules
                # feed the offline eligibility counts in discovery_candidate_supply.
                for release in releases:
                    group = release.get("release-group") or {}
                    if cf_release_group_rejection(
                        group,
                        is_album_candidate=providers.is_album_candidate,
                        music_key=providers.music_key,
                    ):
                        continue

                    title = group.get("title", "").strip()
                    group_id = group.get("id") or providers.music_key(title)
                    album_groups[group_id] = title

                # Do not mistake a single's title for an album title.
                if not artist or not album_groups:
                    continue

                album_title = next(iter(album_groups.values()))

                key = (providers.music_key(primary_artist), providers.music_key(album_title))
                score = item.get("score", 0)

                if key not in albums:
                    albums[key] = {
                        "artist": artist,
                        "primary_artist": primary_artist,
                        "artist_mbid": primary_artist_mbid,
                        "album": album_title,
                        "score": score,
                        "tracks": [],
                        "discovery_source": "listenbrainz",
                        "discovery_sources": ["listenbrainz_cf"],
                    }

                candidate = albums[key]
                candidate["score"] = max(candidate["score"], score)
                track = recording.get("title", "")
                if track and track not in candidate["tracks"]:
                    candidate["tracks"].append(track)

            except Exception as exc:
                if not recorded:
                    cf_recording_records.append(record)
                record["error_class"] = classify_error(exc)
                failures.append({"recording_mbid": mbid, "error": str(exc)})

    add_stage_seconds("metadata_resolution", time.monotonic() - metadata_started)

    # Warm the genre cache before the tag lane reads it. Without this, a cold cache
    # plans fewer supplementary queries because the genre stage below runs after
    # the lane. The prefetch covers the top listening-profile artists and the top
    # CANDIDATE_PREFETCH_LIMIT candidate-pool artists by CF score. The genre stage
    # looks up these same artists later in the run, so these calls reorder lookups
    # rather than add them, except when the tag lane displaces a candidate from the
    # genre stage's top-60 set. Best-effort: failures are left for the genre stage
    # to retry and record. An exhausted retry stops only the candidate prefetch.
    genre_prefetch_started = time.monotonic()
    profile_prefetch_ids = [
        artist_id for artist_id, _listen_count in recent_artist_mbid_counts.most_common(15)
    ]
    candidate_artist_ids = list(dict.fromkeys(
        candidate["artist_mbid"]
        for candidate in sorted(albums.values(), key=lambda album: album["score"], reverse=True)
        if candidate.get("artist_mbid")
    ))
    candidate_prefetch_ids = [
        artist_id for artist_id in candidate_artist_ids[:CANDIDATE_PREFETCH_LIMIT]
        if artist_id not in profile_prefetch_ids
    ]
    prefetch_ids = profile_prefetch_ids + candidate_prefetch_ids
    candidate_prefetch_stopped = False
    # Shares the genre-stage breaker flag. Once the streak opens, the remaining
    # prefetch lookups are skipped and counted, not sent.
    prefetch_exhausted_streak = 0
    with providers.http_client(timeout=15, follow_redirects=True) as client:
        for index, artist_id in enumerate(prefetch_ids):
            if candidate_prefetch_stopped and index >= len(profile_prefetch_ids):
                break
            try:
                if providers.metadata_cache_get(
                    f"mb:artist-genres:{artist_id}",
                    ttl_seconds=90 * 24 * 60 * 60,
                ) is not None:
                    continue

                if index:
                    providers.sleep(1.1)

                response = _get_with_bounded_retry(
                    client,
                    f"https://musicbrainz.org/ws/2/artist/{artist_id}",
                    params={"fmt": "json", "inc": "genres"},
                    headers=headers,
                    sleep=providers.sleep,

                    honor_retry_after=True,
                )
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    if index >= len(profile_prefetch_ids):
                        candidate_prefetch_stopped = True
                    prefetch_exhausted_streak += 1
                    if (
                        GENRE_CIRCUIT_BREAKER_ENABLED
                        and prefetch_exhausted_streak >= GENRE_CIRCUIT_BREAKER_THRESHOLD
                    ):
                        failures.append({
                            "source": "profile_genre_circuit_breaker",
                            "skipped_artists": len(prefetch_ids) - index - 1,
                        })
                        break
                    continue
                prefetch_exhausted_streak = 0
                response.raise_for_status()
                prefetched_genres = sorted({
                    item.get("name", "").strip().casefold()
                    for item in response.json().get("genres", [])
                    if item.get("name", "").strip()
                })
                providers.metadata_cache_set(
                    f"mb:artist-genres:{artist_id}",
                    prefetched_genres,
                )
            except Exception:
                continue

    add_stage_seconds("genre_prefetch", time.monotonic() - genre_prefetch_started)

    # Select supplementary queries from cached listening-profile genres and
    # reserve a small exploration quota for tags found in the CF candidate pool.
    # Cache reads are bounded and do not add provider calls or bypass TTL policy.
    from discovery_tag_queries import (
        MAX_EXPLORATION_QUERIES,
        MAX_PROFILE_QUERIES,
        select_supplementary_tag_queries,
    )

    profile_tags_by_artist = {}
    for artist_id, _weight in recent_artist_mbid_counts.most_common(15):
        try:
            tags = providers.metadata_cache_get(
                f"mb:artist-genres:{artist_id}",
                ttl_seconds=90 * 24 * 60 * 60,
            )
            if isinstance(tags, (list, tuple)):
                profile_tags_by_artist[artist_id] = tags
        except Exception:
            # Supplementary discovery must not fail because one cache read failed.
            continue

    # Saved albums seed tag-query selection for artists whose MBID this run already
    # knows (listens, CF candidates). Cache reads only: no lookups are added, and
    # the query quotas are unchanged, so a seed can reorder or replace a query.
    tag_query_weights = recent_artist_mbid_counts
    # Snapshot before seeding adds cache entries: the budget cap compares against
    # the plan the run would have made without any save.
    baseline_profile_tags = dict(profile_tags_by_artist)
    seed_counts = None
    if providers.feedback_rows is not None:
        from recommendation_feedback import (
            FEEDBACK_SIGNAL_ENABLED, saved_artist_seed_genres, saved_artist_seed_weights,
        )
        if FEEDBACK_SIGNAL_ENABLED:
            try:
                rows = list(providers.feedback_rows())
                seeds = saved_artist_seed_weights(rows, now=time.time())
                stored_genres = saved_artist_seed_genres(rows, now=time.time())
                for candidate in albums.values():
                    if candidate.get("artist_mbid"):
                        mbid_by_artist_key.setdefault(
                            providers.music_key(candidate["primary_artist"]), candidate["artist_mbid"],
                        )
                tag_query_weights = Counter(recent_artist_mbid_counts)
                counts = {"saved_artists": len(seeds), "from_cached_genres": 0,
                          "from_metadata_genres": 0, "skipped_no_genres": 0,
                          "mbid_known_no_cached_genres": 0}
                for artist_key, seed_weight in seeds.items():
                    seed_mbid = mbid_by_artist_key.get(artist_key)
                    if not seed_mbid:
                        # MBID unknown this run: use the genres stored with the save.
                        if not stored_genres.get(artist_key):
                            counts["skipped_no_genres"] += 1
                        else:
                            counts["from_metadata_genres"] += 1
                            seed_mbid = f"saved:{artist_key}"
                            profile_tags_by_artist[seed_mbid] = stored_genres[artist_key]
                            tag_query_weights[seed_mbid] += seed_weight
                        continue
                    tag_query_weights[seed_mbid] += seed_weight
                    if seed_mbid not in profile_tags_by_artist:
                        tags = providers.metadata_cache_get(
                            f"mb:artist-genres:{seed_mbid}",
                            ttl_seconds=90 * 24 * 60 * 60,
                        )
                        if isinstance(tags, (list, tuple)):
                            profile_tags_by_artist[seed_mbid] = tags
                    # Counted by outcome: genres actually available, not just a known MBID.
                    counts["from_cached_genres" if seed_mbid in profile_tags_by_artist
                           else "mbid_known_no_cached_genres"] += 1
                seed_counts = counts
            except Exception:
                # Feedback must not fail supplementary discovery; fall back to unseeded.
                tag_query_weights = recent_artist_mbid_counts
                seed_counts = None

    candidate_pool_tags = []
    candidate_artist_cache_hits = 0
    seen_candidate_artist_ids = set()
    for candidate in sorted(
        albums.values(), key=lambda album: album["score"], reverse=True
    ):
        artist_id = candidate.get("artist_mbid")
        if not artist_id or artist_id in seen_candidate_artist_ids:
            continue
        seen_candidate_artist_ids.add(artist_id)
        try:
            tags = providers.metadata_cache_get(
                f"mb:artist-genres:{artist_id}",
                ttl_seconds=90 * 24 * 60 * 60,
            )
        except Exception:
            continue
        if isinstance(tags, (list, tuple)):
            candidate_pool_tags.extend(tags)
            candidate_artist_cache_hits += 1
        if len(seen_candidate_artist_ids) >= 60:
            break

    regional_queries = select_supplementary_tag_queries(
        tag_query_weights,
        profile_tags_by_artist,
        candidate_pool_tags,
    )
    initial_changed = 0
    if tag_query_weights is not recent_artist_mbid_counts:
        # A seed may replace a planned query but never add one (query budget).
        unseeded_plan = select_supplementary_tag_queries(
            recent_artist_mbid_counts, baseline_profile_tags, candidate_pool_tags,
        )
        regional_queries = regional_queries[:len(unseeded_plan)]
        unseeded_plan_queries = {item[0] for item in unseeded_plan}
        initial_changed = sum(1 for item in regional_queries if item[0] not in unseeded_plan_queries)
    regional_state = {
        "added": 0, "seen": 0, "hits": 0, "misses": 0,
        "request_index": 0, "unavailable": False, "exhausted_run": 0,
    }
    tag_lane_started = time.monotonic()
    supplementary_query_outcomes = []
    with providers.http_client(timeout=20, follow_redirects=True) as client:
        supplementary_query_outcomes.extend(_run_tag_queries(
            regional_queries, providers=providers, client=client,
            headers=headers, albums=albums, failures=failures,
            state=regional_state,
        ))

    add_stage_seconds("supplementary_tag_lane", time.monotonic() - tag_lane_started)

    # Build a complete, paginated Navidrome album inventory.

    from discovery_library_snapshot import (
        AlbumInventoryLimitError,
        fetch_album_inventory,
    )

    try:
        library_albums = fetch_album_inventory(providers.api_call, providers.items)
    except AlbumInventoryLimitError as exc:
        return json.dumps({
            "error": "Album inventory exceeded the safety limit.",
            "albums_retrieved": exc.albums_retrieved,
            "recommendations": [],
        }, ensure_ascii=False, indent=2)
    except Exception as exc:
        return json.dumps({
            "error": "Could not retrieve the Navidrome album inventory.",
            "details": str(exc),
            "recommendations": [],
        }, ensure_ascii=False, indent=2)

    library_by_title = {}
    for album in library_albums:
        title_key = providers.music_key(album.get("name", ""))
        if title_key:
            library_by_title.setdefault(title_key, []).append(album)

    # Replenish only when eligible unowned supply is short of the shortlist target.
    # The gate needs ownership, so it runs after the inventory above. Extra queries
    # are the next-ranked tags not already searched, and the pass shares the lane's
    # candidate cap and stop-on-exhausted-retry rule.
    eligible_before = count_eligible_unowned_albums(albums, library_by_title, providers.music_key)
    replenish_triggered = (
        eligible_before < shortlist_target
        and not regional_state["unavailable"]
        and regional_state["added"] < SUPPLEMENTARY_CANDIDATE_CAP
    )
    replenish_started = time.monotonic()
    replenish_queries = []
    replenish_attempted = 0
    replenish_added_before = regional_state["added"]
    replenish_changed = 0
    if replenish_triggered:
        issued_queries = {query for query, _family, _style in regional_queries}
        wider_queries = select_supplementary_tag_queries(
            tag_query_weights,
            profile_tags_by_artist,
            candidate_pool_tags,
            profile_limit=MAX_PROFILE_QUERIES + REPLENISH_EXTRA_QUERIES,
            exploration_limit=MAX_EXPLORATION_QUERIES + REPLENISH_EXTRA_QUERIES,
        )
        replenish_queries = [
            item for item in wider_queries if item[0] not in issued_queries
        ][:REPLENISH_EXTRA_QUERIES]
        if tag_query_weights is not recent_artist_mbid_counts:
            unseeded_wider = select_supplementary_tag_queries(
                recent_artist_mbid_counts, baseline_profile_tags, candidate_pool_tags,
                profile_limit=MAX_PROFILE_QUERIES + REPLENISH_EXTRA_QUERIES,
                exploration_limit=MAX_EXPLORATION_QUERIES + REPLENISH_EXTRA_QUERIES,
            )
            unseeded_issued = {item[0] for item in select_supplementary_tag_queries(
                recent_artist_mbid_counts, baseline_profile_tags, candidate_pool_tags,
            )}
            unseeded_extra = [
                item for item in unseeded_wider if item[0] not in unseeded_issued
            ][:REPLENISH_EXTRA_QUERIES]
            replenish_queries = replenish_queries[:len(unseeded_extra)]
            unseeded_extra_queries = {item[0] for item in unseeded_extra}
            replenish_changed = sum(
                1 for item in replenish_queries if item[0] not in unseeded_extra_queries
            )
        if replenish_queries:
            with providers.http_client(timeout=20, follow_redirects=True) as client:
                replenish_outcomes = _run_tag_queries(
                    replenish_queries, providers=providers, client=client,
                    headers=headers, albums=albums, failures=failures,
                    state=regional_state,
                )
            supplementary_query_outcomes.extend(replenish_outcomes)
            replenish_attempted = len(replenish_outcomes)
    add_stage_seconds("replenishment", time.monotonic() - replenish_started)
    if seed_counts is not None:
        from recommendation_run_metrics import record_count
        for name, value in {
            **seed_counts, "initial_queries_changed": initial_changed,
            "replenish_queries_changed": replenish_changed,
        }.items():
            record_count(f"save_seed.{name}", value)
    eligible_after = count_eligible_unowned_albums(albums, library_by_title, providers.music_key)

    # Retrieve MusicBrainz genre tags for a bounded number of artists.
    # Cache results by artist MBID and respect the public API rate limit.
    genre_cache = {}
    artist_ids = []
    seen_artist_ids = set()

    for candidate in sorted(
        albums.values(), key=lambda album: album["score"], reverse=True
    ):
        artist_id = candidate.get("artist_mbid")
        if artist_id and artist_id not in seen_artist_ids:
            seen_artist_ids.add(artist_id)
            artist_ids.append(artist_id)
        if len(artist_ids) >= 60:
            break

    # Add recently scrobbled artists when candidate metadata leaves spare slots.
    # recently, so the genre profile follows current listening rather than
    # only the recommendation candidate pool.
    for artist_id, _listen_count in recent_artist_mbid_counts.most_common(15):
        if artist_id not in seen_artist_ids and len(artist_ids) < 75:
            seen_artist_ids.add(artist_id)
            artist_ids.append(artist_id)

    genre_lookup_started = time.monotonic()
    genre_exhausted_streak = 0
    with providers.http_client(timeout=15, follow_redirects=True) as client:
        for index, artist_id in enumerate(artist_ids):
            try:
                cached_genres = providers.metadata_cache_get(
                    f"mb:artist-genres:{artist_id}",
                    ttl_seconds=90 * 24 * 60 * 60,
                )
                if cached_genres is not None:
                    genre_cache[artist_id] = cached_genres
                    continue

                if index:
                    providers.sleep(1.1)

                response = _get_with_bounded_retry(
                    client,
                    f"https://musicbrainz.org/ws/2/artist/{artist_id}",
                    params={"fmt": "json", "inc": "genres"},
                    headers=headers,
                    sleep=providers.sleep,

                    honor_retry_after=True,
                )
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    failures.append({
                        "artist_mbid": artist_id,
                        "error": f"MusicBrainz returned HTTP {response.status_code}",
                    })
                    genre_exhausted_streak += 1
                    if (
                        GENRE_CIRCUIT_BREAKER_ENABLED
                        and genre_exhausted_streak >= GENRE_CIRCUIT_BREAKER_THRESHOLD
                    ):
                        failures.append({
                            "source": "genre_circuit_breaker",
                            "skipped_artists": len(artist_ids) - index - 1,
                        })
                        break
                    continue
                genre_exhausted_streak = 0
                response.raise_for_status()
                artist_data = response.json()
                genre_cache[artist_id] = sorted({
                    item.get("name", "").strip().casefold()
                    for item in artist_data.get("genres", [])
                    if item.get("name", "").strip()
                })
                providers.metadata_cache_set(
                    f"mb:artist-genres:{artist_id}",
                    genre_cache[artist_id],
                )
            except Exception as exc:
                failures.append({
                    "artist_mbid": artist_id,
                    "error": str(exc),
                })

    add_stage_seconds("genre_lookup", time.monotonic() - genre_lookup_started)

    # Broad musical families suggested by the recent listening profile.
    # These are ranking heuristics, not definitive genre classifications.
    from discovery_recommendations import (
        classify_diversity_style,
        genre_families,
        primary_recent_family,
        recent_style_families,
    )

    # Count musical families from actual recent scrobbles. The profile is
    # dynamic: jazz, soul, rock, Brazilian music, and other families rise or
    # fall with the user's listening over the rolling 30-day window.
    recent_family_counts = Counter()
    recent_family_play_counts = Counter()
    for listen, weight in zip(listens, listen_weights):
        metadata = listen.get("track_metadata", {})
        additional_info = metadata.get("additional_info", {})
        artist_mbid = additional_info.get("artist_mbid")
        artist_mbids = additional_info.get("artist_mbids", [])
        if not artist_mbid and isinstance(artist_mbids, list) and artist_mbids:
            artist_mbid = artist_mbids[0]
        if not artist_mbid:
            continue
        for family in recent_style_families(genre_cache.get(artist_mbid, [])):
            recent_family_counts[family] += weight
            recent_family_play_counts[family] += 1

    # Core interests are used to identify close recommendations.
    # African and North African/Middle Eastern music are explicit
    # exploration interests: they should be represented without making
    # every unfamiliar genre automatically count as a core match.
    core_families = {
        "jazz", "hip-hop", "alternative", "rock", "brazilian",
        "rnb-soul", "electronic", "funk",
    }
    exploration_families = {
        "african", "north-african-middle-eastern",
    }
    profile_families = core_families | exploration_families


    candidate_supply = {
        "cf_recordings": summarize_cf_recordings(
            cf_recording_records, returned=cf_recordings_returned,
        ),
        "cf_albums": summarize_cf_albums(albums.values(), providers.music_key),
        "cf_paging": {
            **cf_paging,
            "page_size": CF_PAGE_SIZE,
            "max_pages": CF_MAX_PAGES,
            "artist_cap": CF_ARTIST_RESOLUTION_CAP,
            "artist_cap_skipped": cf_skips["artist_cap"],
            "uncached_resolution_budget": CF_MAX_UNCACHED_RESOLUTIONS,
            "uncached_resolution_calls": resolution_calls,
            # Reached means the budget was spent; skipped > 0 means it was exceeded.
            "uncached_resolution_budget_reached": resolution_calls >= CF_MAX_UNCACHED_RESOLUTIONS,
            "resolution_budget_skipped": cf_skips["resolution_budget"],
            "cache_known_recordings": cf_skips["cache_known"],
        },
        # Aggregate counts that separate an empty tag input from a cache miss.
        "tag_lane": {
            "listens_total": len(listens),
            "listens_with_artist_mbid": listens_with_artist_mbid,
            "profile_artist_mbids": len(recent_artist_mbid_counts),
            "profile_top_artists_considered": len(recent_artist_mbid_counts.most_common(15)),
            "profile_top_artist_cache_hits": len(profile_tags_by_artist),
            "profile_tag_count": sum(len(tags) for tags in profile_tags_by_artist.values()),
            "candidate_artists_considered": len(seen_candidate_artist_ids),
            "candidate_artist_cache_hits": candidate_artist_cache_hits,
            "candidate_pool_tag_count": len(candidate_pool_tags),
        },
        "supplementary": summarize_supplementary_yield(
            supplementary_query_outcomes,
            planned=len(regional_queries) + len(replenish_queries),
        ),
    }

    candidate_supply["replenishment"] = {
        "shortlist_target": shortlist_target,
        "eligible_unowned_before": eligible_before,
        "eligible_unowned_after": eligible_after,
        "triggered": replenish_triggered,
        "extra_queries_planned": len(replenish_queries),
        "extra_queries_attempted": replenish_attempted,
        "extra_candidates_added": regional_state["added"] - replenish_added_before,
        "extra_query_cap": REPLENISH_EXTRA_QUERIES,
    }
    regional_candidates_added = regional_state["added"]
    regional_results_seen = regional_state["seen"]
    supplementary_cache_hits = regional_state["hits"]
    supplementary_cache_misses = regional_state["misses"]

    return {
        "candidate_supply": candidate_supply,
        "listens": listens, "recent_artists": recent_artists,
        "recent_artist_play_counts": recent_artist_play_counts,
        "recent_artist_mbid_counts": recent_artist_mbid_counts,
        "albums": albums, "failures": failures,
        "library_albums": library_albums,
        "library_by_title": library_by_title, "genre_cache": genre_cache,
        "regional_candidates_added": regional_candidates_added,
        "regional_results_seen": regional_results_seen,
        "cf_recording_mbids": cf_recording_mbids,
        "cf_recordings_returned": cf_recordings_returned,
        "cf_recordings_resolved": cf_recordings_resolved,
        "supplementary_cache_hits": supplementary_cache_hits,
        "supplementary_cache_misses": supplementary_cache_misses,
        "recent_family_counts": recent_family_counts,
        "recent_family_play_counts": recent_family_play_counts,
        "core_families": core_families,
        "exploration_families": exploration_families, "profile_families": profile_families,
    }
