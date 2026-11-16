"""In-process runtime counters: provider requests, gate waits and store opens (docs/efficiency.md M1).

Labels are a provider name from a fixed table and an outcome class, or a store operation name.
No URL, query string, identifier or name is ever recorded. Each update is a dict increment under
one lock. The web process reads its own counters; the worker saves a snapshot to the knowledge
store's ``meta`` table (``WORKER_META_KEY``) for the diagnostics route to read.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

WORKER_META_KEY = "runtime_metrics.worker"
SLOW_STORE_SECONDS = 0.25
OUTCOMES = ("ok", "not_found", "rate_limited", "timeout", "error")

# Fixed host -> provider table. A host not listed here counts as "other".
_HOSTS = {
    "musicbrainz.org": "musicbrainz",
    "coverartarchive.org": "coverartarchive",
    "wikidata.org": "wikidata",
    "wikipedia.org": "wikipedia",
    "deezer.com": "deezer",
    "apple.com": "apple",
    "itunes.apple.com": "apple",
    "qobuz.com": "qobuz",
    "discogs.com": "discogs",
    "last.fm": "lastfm",
    "listenbrainz.org": "listenbrainz",
}

_lock = threading.Lock()
_started = time.time()
_requests: dict[tuple[str, str], list[float]] = {}   # (provider, outcome) -> [count, seconds]
_gate: dict[str, list[float]] = {}                    # provider -> [reservations, refused, wait seconds]
_store: dict[str, list[float]] = {}                   # operation -> [count, seconds, slow, locked]


def provider_for_host(host: str | None) -> str:
    host = (host or "").lower().rstrip(".")
    while host:
        if host in _HOSTS:
            return _HOSTS[host]
        host = host.partition(".")[2]
    return "other"


def provider_for_url(url) -> str:
    try:
        return provider_for_host(urlsplit(str(url)).hostname)
    except ValueError:
        return "other"


def outcome_for_status(status: int) -> str:
    if status in (429, 503):
        return "rate_limited"
    if status in (404, 410):
        return "not_found"
    return "ok" if status < 400 else "error"


def outcome_for_exception(exc: BaseException) -> str:
    return "timeout" if isinstance(exc, httpx.TimeoutException) else "error"


def record_request(provider: str, outcome: str, seconds: float) -> None:
    with _lock:
        entry = _requests.setdefault((provider, outcome), [0, 0.0])
        entry[0] += 1
        entry[1] += max(0.0, seconds)


def record_gate(provider: str, waited: float, granted: bool) -> None:
    with _lock:
        entry = _gate.setdefault(provider, [0, 0, 0.0])
        entry[0 if granted else 1] += 1
        entry[2] += max(0.0, waited)


def record_store(operation: str, seconds: float, locked: bool = False) -> None:
    slow = seconds > SLOW_STORE_SECONDS
    with _lock:
        entry = _store.setdefault(operation, [0, 0.0, 0, 0])
        entry[0] += 1
        entry[1] += max(0.0, seconds)
        entry[2] += slow
        entry[3] += locked
    if locked:
        logger.warning("Store %s: database is locked after %.0f ms", operation, seconds * 1000)
    elif slow:
        logger.warning("Store %s took %.0f ms", operation, seconds * 1000)


_ORIGINAL_SEND = httpx.Client.send
_ORIGINAL_ASEND = httpx.AsyncClient.send


def _counted_send(request, call):
    provider = provider_for_url(request.url)
    started = time.perf_counter()
    try:
        response = call()
    except Exception as exc:
        record_request(provider, outcome_for_exception(exc), time.perf_counter() - started)
        raise
    record_request(provider, outcome_for_status(response.status_code), time.perf_counter() - started)
    return response


class MeteredClient(httpx.Client):
    """An ``httpx.Client`` that counts each request by provider and outcome class."""

    def send(self, request, **kwargs):
        return _counted_send(request, lambda: _ORIGINAL_SEND(self, request, **kwargs))


def _patched_send(self, request, **kwargs):
    return _counted_send(request, lambda: _ORIGINAL_SEND(self, request, **kwargs))


async def _patched_asend(self, request, **kwargs):
    provider = provider_for_url(request.url)
    started = time.perf_counter()
    try:
        response = await _ORIGINAL_ASEND(self, request, **kwargs)
    except Exception as exc:
        record_request(provider, outcome_for_exception(exc), time.perf_counter() - started)
        raise
    record_request(provider, outcome_for_status(response.status_code), time.perf_counter() - started)
    return response


def count_all_httpx() -> None:
    """Count every httpx request in this process (``httpx.get``/``post``, any ``Client``, ``AsyncClient``).

    Idempotent. A ``MeteredClient`` bypasses the patched method, so nothing is counted twice.
    """
    httpx.Client.send = _patched_send
    httpx.AsyncClient.send = _patched_asend


def snapshot() -> dict:
    with _lock:
        requests: dict[str, dict] = {}
        for (provider, outcome), (count, seconds) in sorted(_requests.items()):
            row = requests.setdefault(provider, {"count": 0, "seconds": 0.0, "outcomes": {}})
            row["count"] += int(count)
            row["seconds"] = round(row["seconds"] + seconds, 3)
            row["outcomes"][outcome] = int(count)
        gate = {p: {"reservations": int(v[0]), "refused": int(v[1]), "wait_seconds": round(v[2], 3)}
                for p, v in sorted(_gate.items())}
        store = {op: {"count": int(v[0]), "seconds": round(v[1], 3), "slow": int(v[2]), "locked": int(v[3])}
                 for op, v in sorted(_store.items())}
    return {"since": _started, "requests": requests, "gate": gate, "store": store}


def reset() -> None:
    """Clear all counters (tests)."""
    global _started
    with _lock:
        _requests.clear()
        _gate.clear()
        _store.clear()
        _started = time.time()


def install() -> None:
    """Connect the gate and the store to these counters (call once at web and worker startup)."""
    from integrations import provider_gate
    from intelligence.store import db
    count_all_httpx()
    provider_gate.set_observer(record_gate)
    db.set_observer(record_store)


def save_worker_snapshot(db, now: float | None = None) -> None:
    payload = json.dumps({"written_at": time.time() if now is None else now, **snapshot()})
    with db:
        db.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                   (WORKER_META_KEY, payload))


def load_worker_snapshot(db) -> dict | None:
    row = db.execute("SELECT value FROM meta WHERE key = ?", (WORKER_META_KEY,)).fetchone()
    if row is None:
        return None
    try:
        data = json.loads(row["value"])
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None
