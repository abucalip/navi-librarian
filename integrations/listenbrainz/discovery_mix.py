"""Short-lived LB Radio source cache and bounded in-process request coalescing."""

from concurrent.futures import Future, TimeoutError as FutureTimeout
import hashlib
import threading
import time

import httpx

from integrations.listenbrainz.jspf import parse_playlist
from recommendation_run_metrics import record_provider_call

TTL = 300
REQUEST_BUDGET = 12.0
MAX_INFLIGHT = 16
MAX_TRACKS = 200
MAX_RESPONSE_BYTES = 1_048_576
URL = "https://api.listenbrainz.org/1/explore/lb-radio"


class MixError(Exception):
    """Sanitized, stable error code; no provider body or credentials escape."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _parse(jspf):
    source = jspf.get("playlist") if isinstance(jspf, dict) else None
    tracks = source.get("track") if isinstance(source, dict) else None
    if not isinstance(tracks, list) or len(tracks) > MAX_TRACKS:
        raise ValueError("Invalid mix track list")
    return parse_playlist(jspf)


def _cached(read, key):
    entry = read(key)
    if not isinstance(entry, dict) or not isinstance(entry.get("at"), (int, float)):
        return None
    if not 0 <= time.time() - entry["at"] < TTL:
        return None
    try:
        return _parse(entry.get("jspf"))
    except (ValueError, TypeError):
        return None


def cache_key(prompt, mode, username, token):
    """Separate credentials and requests without storing a token in cache keys."""
    identity = hashlib.sha256(f"{username}\0{token}\0{mode}\0{prompt}".encode()).hexdigest()
    return f"lb:discovery-mix:v1:{identity}"


class MixClient:
    """Share successes and failures with callers already waiting on the same fetch."""

    def __init__(self):
        self._lock = threading.Lock()
        self._inflight = {}

    def fetch(self, *, key, prompt, mode, read, write, headers, limiter, get=None):
        deadline = time.monotonic() + REQUEST_BUDGET
        with self._lock:
            try:
                cached = _cached(read, key)
            except Exception as error:
                raise MixError("unavailable") from error
            if cached is not None:
                return cached
            future = self._inflight.get(key)
            leader = future is None
            if leader:
                if len(self._inflight) >= MAX_INFLIGHT:
                    raise MixError("busy")
                future = Future()
                self._inflight[key] = future
        if not leader:
            try:
                return future.result(timeout=max(0, deadline - time.monotonic()))
            except FutureTimeout as error:
                raise MixError("timeout") from error
        try:
            playlist = self._fetch(prompt, mode, write, key, headers, limiter, deadline, get or httpx.get)
            future.set_result(playlist)
        except Exception as error:
            # Always release waiters, including on unexpected store/transport failures.
            safe = error if isinstance(error, MixError) else MixError("unavailable")
            future.set_exception(safe)
            raise safe from None
        finally:
            with self._lock:
                del self._inflight[key]
        return playlist

    @staticmethod
    def _fetch(prompt, mode, write, key, headers, limiter, deadline, get):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise MixError("timeout")
        if not limiter.admit("listenbrainz", max(0, remaining - 0.1)):
            raise MixError("rate_limited")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise MixError("timeout")
        try:
            record_provider_call("listenbrainz", "discovery_mix")
            response = get(URL, params={"prompt": prompt, "mode": mode}, headers=headers,
                           timeout=min(10.0, remaining), follow_redirects=False)
            if response.status_code == 429:
                raise MixError("rate_limited")
            response.raise_for_status()
            if len(response.content) > MAX_RESPONSE_BYTES:
                raise ValueError("Mix response too large")
            body = response.json()
            payload = body.get("payload") if isinstance(body, dict) else None
            jspf = payload.get("jspf") if isinstance(payload, dict) else None
            playlist = _parse(jspf)
        except httpx.TimeoutException as error:
            raise MixError("timeout") from error
        except (httpx.HTTPError, ValueError, TypeError) as error:
            raise MixError("upstream_error") from error
        if time.monotonic() >= deadline:
            raise MixError("timeout")
        write(key, {"at": time.time(), "jspf": jspf})
        return playlist
