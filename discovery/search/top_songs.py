"""The ``top_songs`` section of the artist page (contract section 14.3).

ListenBrainz top recordings for the artist's MBID come first; Last.fm top tracks answer when
ListenBrainz has none or no MBID is known. One list never mixes the two scales. The fetched
records are cached; the ``owned`` flag is computed on every read against the current index.
"""

from __future__ import annotations

import time
from typing import Any

from discovery.search.cache import provider_cache_key, read_cached, write_cached
from discovery.search.index import OwnedData
from discovery.search.normalize import normalize_key
from discovery.search.providers import LASTFM, LISTENBRAINZ, ProviderError

TOP_SONGS_LIMIT = 10


def _dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per normalized title, keeping the most listened version, in listed order."""
    seen: set[str] = set()
    output = []
    for record in records:
        key = normalize_key(record["name"])
        if key and key not in seen:
            seen.add(key)
            output.append(record)
    return output[:TOP_SONGS_LIMIT]


def _owned_titles(data: OwnedData | None, artist_id: str | None) -> set[str]:
    if data is None or not artist_id:
        return set()
    return {song["name_key"] for song in data.songs if song["artist_id"] == artist_id}


def _fetch(network, name: str, mbid: str | None, *, remaining, cancelled):
    """``(source, records)`` from the first source that has songs. Raises when every source failed."""
    attempted = failed = 0
    if network.listenbrainz is not None and mbid:
        attempted += 1
        key = provider_cache_key("listenbrainz", 0, f"artist-top:{mbid}", "top-recordings")
        records = read_cached(network.cache_read, key, time.time())
        if records is None:
            try:
                records = network.listenbrainz.top_recordings(mbid, remaining=remaining, cancelled=cancelled)
            except Exception:
                failed += 1
            else:
                records = _dedupe(records)
                if remaining() > 0 and not cancelled.is_set():
                    write_cached(network.cache_write, key, records, time.time())
        if records:
            return LISTENBRAINZ, records
    if network.lastfm is not None:
        attempted += 1
        key = provider_cache_key("lastfm", network.lastfm_generation, f"artist-top:{normalize_key(name)}", "top-tracks")
        records = read_cached(network.cache_read, key, time.time())
        if records is None:
            try:
                records = network.lastfm.top_tracks(name, remaining=remaining, cancelled=cancelled)
            except Exception:
                failed += 1
            else:
                records = _dedupe(records)
                if remaining() > 0 and not cancelled.is_set():
                    write_cached(network.cache_write, key, records, time.time())
        if records:
            return LASTFM, records
    if attempted == 0:
        return None, None
    if failed == attempted:
        raise ProviderError("failed")
    return None, []


def top_songs(
    network,
    name: str,
    artist_id: str | None,
    owned_data: OwnedData | None,
    *,
    mbid: str | None,
    remaining,
    cancelled,
) -> dict[str, Any]:
    """The ``top_songs`` section object. Raises when every source that was tried failed."""
    source, records = _fetch(network, name, mbid, remaining=remaining, cancelled=cancelled)
    if source is None and records is None:
        return {"section": "top_songs", "available": False, "complete": False,
                "reason": "source_disabled", "items": []}
    owned = _owned_titles(owned_data, artist_id)
    items = [
        {
            "rank": position,
            "name": record["name"],
            "listen_count": record["listen_count"],
            "source": source,
            "recording_mbid": record["recording_mbid"],
            "owned": normalize_key(record["name"]) in owned,
            "album": record["album"],
        }
        for position, record in enumerate(records or [], start=1)
    ]
    return {"section": "top_songs", "available": True, "complete": True, "reason": None, "items": items}
