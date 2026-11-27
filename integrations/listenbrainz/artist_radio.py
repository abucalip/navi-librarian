"""Bounded top-recordings read for Artist Radio and future Missing Essentials."""

import threading
import time

import httpx

from discovery.search.cache import read_cached, write_cached
from discovery.search.normalize import normalize_mbid
from recommendation_run_metrics import record_provider_call

TTL = 30 * 24 * 60 * 60
MAX_RECORDINGS = 10_000
# Fixed stripes avoid an unbounded per-artist lock registry.
_LOCKS = tuple(threading.Lock() for _ in range(16))


def _parse(body):
    if not isinstance(body, list) or len(body) > MAX_RECORDINGS:
        raise ValueError("Invalid top recordings response")
    rows = []
    for row in body:
        if not isinstance(row, dict) or not isinstance(row.get("recording_name"), str):
            raise ValueError("Invalid top recording")
        mbid = normalize_mbid(row.get("recording_mbid"))
        if not mbid:
            raise ValueError("Invalid recording ID")
        length = row.get("length")
        rows.append({"recording_mbid": mbid, "title": row["recording_name"],
                     "artist": row.get("artist_name") if isinstance(row.get("artist_name"), str) else None,
                     "album": row.get("release_name") if isinstance(row.get("release_name"), str) else None,
                     "duration_ms": length if isinstance(length, int) and length > 0 else None})
    return rows


def top_recordings(mbid, *, read, write, headers, limiter, remaining, get=httpx.get):
    """Return ranked metadata or None on failure; cache complete responses only."""
    key = f"lb:popularity:top-recordings:v1:{mbid}"
    cached = read_cached(read, key, time.time(), positive_ttl=TTL)
    if cached is not None:
        return cached
    lock = _LOCKS[hash(mbid) % len(_LOCKS)]
    if not lock.acquire(timeout=max(0, remaining())):
        return None
    try:
        cached = read_cached(read, key, time.time(), positive_ttl=TTL)
        if cached is not None:
            return cached
        if remaining() <= 0 or not limiter.admit("listenbrainz", max(0, remaining() - 0.1)):
            return None
        timeout = min(4.0, remaining())
        if timeout <= 0:
            return None
        record_provider_call("listenbrainz", "artist_radio_top_recordings")
        response = get(f"https://api.listenbrainz.org/1/popularity/top-recordings-for-artist/{mbid}",
                       headers=headers, timeout=timeout, follow_redirects=False)
        response.raise_for_status()
        rows = _parse(response.json())
        write_cached(write, key, rows, time.time())
        return rows
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    finally:
        lock.release()
