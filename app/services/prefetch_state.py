"""State and budgets of the owned-entity prefetch (efficiency K3), with no job or network code.

The prefetch (``app/services/owned_prefetch.py``) is off unless the owner sets daily per-provider caps
in the worker's environment, for example ``OWNED_PREFETCH_BUDGETS="musicbrainz=300,lastfm=600"``. A
provider that is not listed has a cap of zero, and a request to it is refused before it is sent, so the
job can never call a source the owner did not name. Nothing here imports a job, a provider client or
the web app: the diagnostics route reads ``read_coverage`` without loading worker code.

Everything persistent lives in the knowledge store's ``meta`` table:

- ``prefetch:spent``: ``{"date": "YYYY-MM-DD", "spent": {provider: requests}}``. A new local date starts
  from zero; a restart on the same date keeps what was spent, so a restart does not reset the caps.
- ``prefetch:cursor``: ``{"artists": n, "albums": n}``, the next position in each ordered walk.
- ``prefetch:coverage``: the last run's counts, for ``/api/diagnostics/runtime``.
"""
import json
import os
import threading
import time
from datetime import datetime
from urllib.parse import urlsplit
from typing import Callable, Optional

import httpx

from app import worker_schedule
from app.services.runtime_metrics import provider_for_host

ENV_BUDGETS = "OWNED_PREFETCH_BUDGETS"
SPENT_KEY = "prefetch:spent"
CURSOR_KEY = "prefetch:cursor"
COVERAGE_KEY = "prefetch:coverage"
# The only sources the artist and album page networks call. A name outside this set is ignored. Deezer, Apple and
# Wikipedia (K3 part 2) feed only the album page's tracklist and description hooks, which are given to the
# network only when their providers are named (``owned_prefetch.prefetch_network``).
PROVIDERS = ("musicbrainz", "listenbrainz", "lastfm", "discogs", "deezer", "apple", "wikipedia")


def provider_of(url) -> str:
    """The provider a URL belongs to, by the diagnostics host table plus Last.fm's API host.

    ``runtime_metrics`` counts ``ws.audioscrobbler.com`` as ``other``; a cap must name Last.fm's real API host.
    """
    try:
        host = (urlsplit(str(url)).hostname or "").lower()
    except ValueError:
        return "other"
    if host == "audioscrobbler.com" or host.endswith(".audioscrobbler.com"):
        return "lastfm"
    return provider_for_host(host)


class BudgetExhausted(httpx.TransportError):
    """Raised instead of sending a request that would pass a provider's daily cap (counts as a failed request)."""


def parse_budgets(text: Optional[str]) -> dict:
    """``{provider: cap}`` from ``"musicbrainz=300,lastfm=600"``. Unknown names, bad numbers and negatives are dropped."""
    caps = {}
    for part in (text or "").split(","):
        name, _, number = part.partition("=")
        name = name.strip().lower()
        try:
            cap = int(number.strip())
        except ValueError:
            continue
        if name in PROVIDERS and cap > 0:
            caps[name] = cap
    return caps


def budgets_from_env(environ=None) -> dict:
    return parse_budgets((os.environ if environ is None else environ).get(ENV_BUDGETS))


def local_date(now: float) -> str:
    return datetime.fromtimestamp(now).date().isoformat()


def due(environ=None) -> Callable[[float, Optional[float]], bool]:
    """The scheduler rule: never while no cap is set (nothing is recorded, so setting caps takes effect at once), then daily."""
    daily = worker_schedule.daily()

    def rule(now: float, last_run: Optional[float]) -> bool:
        return bool(budgets_from_env(environ)) and daily(now, last_run)
    return rule


class Spend:
    """Counts and caps the requests one run sends. Safe to share across the page networks' threads."""

    def __init__(self, caps: dict, spent: Optional[dict] = None, *, get=None, post=None):
        self.caps = dict(caps)
        self.spent = {name: int((spent or {}).get(name, 0)) for name in PROVIDERS}
        self.cap_reached = set()  # named providers whose cap stopped a request in this run
        self.not_named = set()    # providers asked for that have no cap at all (a failed source, not a reason to stop)
        self._get, self._post = get, post
        self._lock = threading.Lock()

    def take(self, url) -> None:
        provider = provider_of(url)
        with self._lock:
            if provider not in self.caps:
                self.not_named.add(provider)
                raise BudgetExhausted(f"no cap set for {provider}")
            if self.spent.get(provider, 0) >= self.caps[provider]:
                self.cap_reached.add(provider)
                raise BudgetExhausted(f"daily cap reached for {provider}")
            self.spent[provider] += 1

    def get(self, url, **kwargs):
        self.take(url)
        return (self._get or httpx.get)(url, **kwargs)

    def post(self, url, **kwargs):
        self.take(url)
        return (self._post or httpx.post)(url, **kwargs)

    def exhausted(self) -> bool:
        """True once any capped provider has no requests left (a request to an unnamed provider does not count)."""
        with self._lock:
            return bool(self.cap_reached) or any(self.spent[name] >= cap for name, cap in self.caps.items())

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self.spent)


def _read_json(db, key):
    row = db.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    try:
        value = json.loads(row["value"])
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _write_json(db, key, value) -> None:
    with db:
        db.execute("INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                   (key, json.dumps(value, separators=(",", ":"))))


def load_spent(db, date: str) -> dict:
    """What was spent on ``date``; nothing when the stored day is another one."""
    stored = _read_json(db, SPENT_KEY)
    if not stored or stored.get("date") != date or not isinstance(stored.get("spent"), dict):
        return {}
    return {name: int(stored["spent"].get(name, 0) or 0) for name in PROVIDERS}


def save_spent(db, date: str, spent: dict) -> None:
    _write_json(db, SPENT_KEY, {"date": date, "spent": spent})


def load_cursor(db) -> dict:
    stored = _read_json(db, CURSOR_KEY) or {}
    return {name: stored[name] if isinstance(stored.get(name), int) and stored[name] >= 0 else 0
            for name in ("artists", "albums")}


def save_cursor(db, cursor: dict) -> None:
    _write_json(db, CURSOR_KEY, {"artists": int(cursor["artists"]), "albums": int(cursor["albums"])})


def save_coverage(db, coverage: dict) -> None:
    _write_json(db, COVERAGE_KEY, {**coverage, "written_at": time.time()})


def read_coverage(db) -> Optional[dict]:
    """The last run's coverage counts, or None when the job has never run."""
    return _read_json(db, COVERAGE_KEY)
