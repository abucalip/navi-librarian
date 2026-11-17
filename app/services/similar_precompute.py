"""Daily similar-artist precompute, run by the worker (efficiency W2; SEARCH_CONTRACT section 7, P3b).

``run_once`` is the worker scheduler's ``similar_precompute`` entry. It builds its own owned index for the
run, synchronously and into a local variable (the web process keeps its own index in ``app/api/search.py``),
then calls ``discovery/search/similar_precompute.run_precompute`` from the stored cursor. The index is
dropped when the run returns. Results go through the discovery list store, which the web already reads.

When the library cannot be read the run returns ``worker_schedule.NOT_READY``, so the day is not marked
done and the scheduler tries again after the entry's retry delay (30 minutes), as the old web loop did.

This module also owns the parts of the artist-page network that do not need the metadata routes
(``network_kwargs``), so the worker never imports ``app.api.metadata``.
"""
from __future__ import annotations

import logging
import os
import resource
import sys
import time

from app import worker_schedule
from discovery import store as discovery_store
from discovery.identity import load_identities
from discovery.library_snapshot import build_library_snapshot
from discovery.search.index import build_owned_data, fetch_song_inventory
from discovery.search.merge import OwnedKeys
from discovery.search.network import artist_network
from discovery.search.similar_precompute import run_precompute
from settings.service import discogs_generation, discogs_token_and_source, lastfm_generation, navidrome_generation

logger = logging.getLogger(__name__)

CURSOR = "similar-precompute-cursor"
RETRY_SECONDS = 1800.0           # the old web loop's check interval: an unusable library is retried this often


def snapshot_lists(librarian, generation):
    """Artists and albums from the library snapshot, keyed by Navidrome generation (SEARCH_CONTRACT 5.2)."""
    suffix = f":navidrome{generation}"

    def read(name):
        return librarian._discovery_read_list(name + suffix)

    def write(name, payload):
        librarian._discovery_write_list(name + suffix, payload)

    snapshot = build_library_snapshot(librarian.api_call, librarian.items, read, write)
    return snapshot["artists"], snapshot["albums"]


def cache_reader(librarian):
    """Reader for provider cache entries. The store wraps each entry as ``{"payload": entry, ...}``."""

    def read(name):
        stored = librarian._discovery_read_list(name)
        return stored.get("payload") if isinstance(stored, dict) else None

    return read


def network_kwargs(librarian) -> dict:
    """The artist-network arguments shared by the artist page and the precompute (cache, identity, keys)."""

    def navidrome_mbid(artist_id):
        # One read-only Navidrome call per artist; the library tags MBIDs on many artists.
        artist = librarian.api_call("getArtist", id=artist_id).get("artist", {})
        return artist.get("musicBrainzId") or None

    settings = librarian._discovery_settings_read()
    return {
        "cache_read": cache_reader(librarian),
        "cache_write": librarian._discovery_write_list,
        "navidrome_mbid": navidrome_mbid,
        "lastfm_api_key": str(settings.get("lastfm_api_key") or "").strip(),
        "lastfm_gen": lastfm_generation(librarian._discovery_settings_read),
        "discogs_token": discogs_token_and_source(librarian._discovery_settings_read, os.environ)[0],
        "discogs_gen": discogs_generation(librarian._discovery_settings_read),
    }


def precompute_network(librarian):
    """The network for the similar section only. Popularity and the bio feed other sections, never called here."""
    return artist_network(
        popularity=lambda mbids, can_cache: {},
        bio=lambda name: None,
        **network_kwargs(librarian),
    )


def _peak_rss_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024    # bytes on macOS, KiB on Linux


def build_owned(librarian):
    """Build the owned data for one run, synchronously, or None when the library cannot be read."""
    started = time.monotonic()
    generation = navidrome_generation(librarian._discovery_settings_read)
    try:
        artists, albums = snapshot_lists(librarian, generation)
        songs = fetch_song_inventory(librarian.api_call, librarian.items)
        identities = load_identities(
            lambda prefix: discovery_store.read_prefix(librarian.DISCOVERY_DB, prefix), generation,
        )
        data = build_owned_data(generation=generation, built_at=time.time(), artists=artists,
                                albums=albums, songs=songs, identities=identities)
    except Exception as exc:
        # Bounded diagnostics: the error type only, never provider details.
        logger.warning("Owned index for the precompute could not be built (%s)", type(exc).__name__)
        return None
    logger.info("Owned index for the precompute: %s artists, %s songs, built in %.1f s, peak RSS %.0f MB",
                len(data.artists), data.song_count, time.monotonic() - started, _peak_rss_mb())
    return data


def read_cursor(librarian) -> int:
    """Where the last pass stopped: the position in the owned artist list (0 when missing or malformed)."""
    stored = librarian._discovery_read_list(CURSOR)
    payload = stored.get("payload") if isinstance(stored, dict) else None
    position = payload.get("next", 0) if isinstance(payload, dict) else 0
    return position if isinstance(position, int) else 0


def run_once(librarian, stop=None):
    """One precompute pass from the stored cursor; ``NOT_READY`` when the owned library cannot be read."""
    data = build_owned(librarian)
    if data is None:
        return worker_schedule.NOT_READY
    counts = run_precompute(
        list(data.artists), precompute_network(librarian), OwnedKeys(data),
        start=read_cursor(librarian),
        on_progress=lambda position: librarian._discovery_write_list(CURSOR, {"next": position}),
        stop=stop,
    )
    logger.info("Similar-artist precompute finished: %s", counts)
    return counts
