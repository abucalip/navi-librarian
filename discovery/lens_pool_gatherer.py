"""Daily lens pools: gathers each lens's candidate pool (Engine 2, Phase 4, slice 2).

For each lens in ``LENS_LIST_ORDER`` the gatherer runs ``run_deep_cuts_tag_supply`` with the lens
name and the day as the radio scope, then looks up the album listeners (MusicBrainz release search
and Last.fm album.getInfo), the artist genre tags (one ListenBrainz artist batch per lens, cached)
and the fallback tags for pool artists with fewer than two genre tags. Its output is the input of
``discovery.lens_lists.build_lens_lists``.

Gated by ``engine2_lens_lists_enabled`` (default on): when the setting is off the function returns
before any provider call. Unwired: nothing calls it yet, and it does not read or write the
recommendation history, the cooldown or the personal list. Providers and caches are injected, so
tests use fixtures and make no network call. A failing provider leaves the pool or its tags short;
it does not raise for provider errors. See docs/engine2.md (Phase 4, slice 2).
"""
from collections.abc import Callable, Iterable, Mapping
from datetime import date
from typing import Any

from discovery.artist_links import fetch_collaborators, fetch_similar_artists
from discovery.artist_profiles import fetch_artist_profiles
from discovery.artist_tag_fallback import fallback_artist_tags, load_genre_vocabulary
from discovery.batch_metadata import ARTIST_GENRE_CACHE_PREFIX, ARTIST_GENRE_TTL_SECONDS, prefetch_artist_genres
from discovery.current_tastes import current_tastes_context, recent_window
from discovery.deep_cuts_supply import run_deep_cuts_tag_supply
from discovery.history_windows import listen_artist_mbid
from discovery.lens_lists import LENS_LIST_ORDER, history_artist_mbids, lens_seed_queries, usable_listens
from discovery.mbid_popularity import resolve_popularity
from settings.service import engine2_lens_lists_enabled_value

# Last.fm album.getInfo calls per lens. The selection reads album listeners only, so the
# artist.getInfo lookups are skipped. Approved budget: 40 to 60 album lookups per lens.
LENS_LASTFM_CALL_BUDGET = 60
# Last.fm top-tag calls per lens for pool artists with fewer than two genre tags. Each answer is
# cached for 90 days, so a repeat run costs nothing for artists already answered.
LENS_FALLBACK_CALL_BUDGET = 40


def _empty_state() -> dict[str, Any]:
    """The shared lane state ``run_deep_cuts_tag_supply`` expects, fresh for each lens."""
    return {"added": 0, "seen": 0, "hits": 0, "misses": 0, "request_index": 0,
            "unavailable": False, "exhausted_run": 0}


def _genres_from_cache(providers: Any, mbids: Iterable[str]) -> dict[str, list[str]]:
    """{artist MBID: genre tags} for the artists whose genre list is cached. Never raises."""
    tags: dict[str, list[str]] = {}
    for mbid in mbids:
        try:
            value = providers.metadata_cache_get(
                f"{ARTIST_GENRE_CACHE_PREFIX}{mbid}", ttl_seconds=ARTIST_GENRE_TTL_SECONDS)
        except Exception:
            continue
        if isinstance(value, list):
            tags[mbid] = [str(tag) for tag in value if tag]
    return tags


def _check_day(day: Any) -> None:
    if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
        raise ValueError("day must be an ISO date (YYYY-MM-DD)")


def gather_lens_pools(
    listens: Iterable[Mapping[str, Any]],
    *,
    day: str,
    providers: Any,
    headers: Mapping[str, str],
    lastfm_api_key: str,
    settings_read: Callable[[], Mapping[str, Any]],
) -> dict[str, Any]:
    """Gather one pool per lens for ``day`` and the popularity and genre inputs of the builder.

    ``listens`` is the listening history (ListenBrainz listen shape). ``providers`` supplies
    ``http_get``, ``http_post``, ``http_client``, ``sleep``, ``music_key``, ``is_album_candidate``,
    ``metadata_cache_get`` and ``metadata_cache_set`` (the ``RecommendationProviders`` fields).
    ``headers`` are the MusicBrainz request headers.

    Returns ``{"status": "disabled", "day": day}`` with no provider call when the setting is off.
    Otherwise returns ``status`` "gathered" with: ``seeds`` ({lens: seed queries}), ``pools``
    ({lens: album dicts}), ``popularity`` ({release group MBID: album listeners}), ``artist_tags``
    and ``fallback_tags`` ({artist MBID: tags}), and ``lenses`` (per-lens counts). Listens stamped
    before 1971 are dropped before any profile is built. Raises ``ValueError`` for a bad ``day``.
    """
    _check_day(day)
    if not engine2_lens_lists_enabled_value(settings_read):
        return {"status": "disabled", "day": day}

    get, sleep = providers.http_get, providers.sleep
    cache_get, cache_set = providers.metadata_cache_get, providers.metadata_cache_set
    usable = usable_listens(listen for listen in listens if isinstance(listen, Mapping))
    history = sorted(history_artist_mbids(usable))
    # Current tastes links: similar artists (Last.fm) and collaborators (MusicBrainz) of the window
    # artists. Their genres are needed too, or the links have no tags to seed from.
    window, _days = recent_window(usable)
    window_mbids = sorted({listen_artist_mbid(listen) for listen in window} - {""})
    similar = fetch_similar_artists(
        get, window_mbids, api_key=lastfm_api_key, cache_get=cache_get, cache_set=cache_set, sleep=sleep)
    collaborators = fetch_collaborators(
        get, window_mbids, headers=headers, cache_get=cache_get, cache_set=cache_set, sleep=sleep)
    linked = {m for values in (*similar.values(), *collaborators.values()) for m in values}
    genre_mbids = sorted(set(history) | linked)
    prefetch_artist_genres(get, genre_mbids, headers=headers, cache_get=cache_get, cache_set=cache_set)
    seeds = lens_seed_queries(
        usable, _genres_from_cache(providers, genre_mbids), similar=similar, collaborators=collaborators)

    pools: dict[str, list[dict[str, Any]]] = {}
    popularity: dict[str, Any] = {}
    artist_tags: dict[str, list[str]] = {}
    fallback_tags: dict[str, list[str]] = {}
    reports: dict[str, dict[str, Any]] = {}
    vocabulary: set[str] | None = None
    for lens in LENS_LIST_ORDER:
        queries = seeds.get(lens.name, [])
        albums: dict[Any, dict[str, Any]] = {}
        failures: list[dict[str, Any]] = []
        if queries:
            run_deep_cuts_tag_supply(
                queries, providers=providers, headers=headers, albums=albums,
                failures=failures, state=_empty_state(), lens=lens.name, day=day,
            )
        pool = list(albums.values())
        pools[lens.name] = pool

        found = resolve_popularity(
            get, pool, api_key=lastfm_api_key, headers=headers, cache_get=cache_get,
            cache_set=cache_set, sleep=sleep, max_lastfm_calls=LENS_LASTFM_CALL_BUDGET,
            with_artist_listeners=False,
        )
        popularity.update(found)

        mbids = list(dict.fromkeys(str(a["artist_mbid"]) for a in pool if a.get("artist_mbid")))
        prefetch_artist_genres(get, mbids, headers=headers, cache_get=cache_get, cache_set=cache_set)
        tags = _genres_from_cache(providers, mbids)
        artist_tags.update(tags)

        fallback: dict[str, list[str]] = {}
        if mbids:
            if vocabulary is None:
                # Loaded once per run; an empty result is kept, so a failed list is not retried per lens.
                vocabulary = load_genre_vocabulary(get, headers, cache_get, cache_set, sleep=sleep)
            fallback = fallback_artist_tags(
                mbids, tags, get=get, api_key=lastfm_api_key, vocabulary=vocabulary,
                cache_get=cache_get, cache_set=cache_set, sleep=sleep,
                max_calls=LENS_FALLBACK_CALL_BUDGET,
            )
            fallback_tags.update(fallback)

        reports[lens.name] = {
            "queries": len(queries),
            "albums": len(pool),
            "album_listeners": sum(
                1 for a in pool
                if (found.get(str(a.get("release_group_mbid"))) or {}).get("album_listeners") is not None),
            "artists": len(mbids),
            "fallback_artists": len(fallback),
            "failures": len(failures),
        }

    # Areas and first years for the regional spine and era match: the window artists (the spine
    # is set by the window) and the pool artists (their releases are ranked by it).
    wanted = set(window_mbids) | {
        str(album["artist_mbid"]) for pool in pools.values() for album in pool if album.get("artist_mbid")}
    profiles = fetch_artist_profiles(
        get, sorted(wanted - {""}), headers=headers, cache_get=cache_get, cache_set=cache_set, sleep=sleep)
    # The history and linked artists' genres belong in the returned tag map too, not only the pool's.
    artist_tags.update(_genres_from_cache(providers, genre_mbids))
    areas = {mbid: profile["area"] for mbid, profile in profiles.items() if profile.get("area")}
    years = {mbid: profile["begin_year"] for mbid, profile in profiles.items() if profile.get("begin_year")}

    return {
        "status": "gathered",
        "day": day,
        "seeds": {lens.name: list(seeds.get(lens.name, [])) for lens in LENS_LIST_ORDER},
        "pools": pools,
        "popularity": popularity,
        "artist_tags": artist_tags,
        "fallback_tags": fallback_tags,
        "artist_profiles": profiles,
        "current_context": current_tastes_context(usable, areas, years),
        "artist_links": {"similar": similar, "collaborators": collaborators},
        "lenses": reports,
    }
