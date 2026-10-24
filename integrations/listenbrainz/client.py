"""ListenBrainz HTTP client for bounded recent-listen retrieval."""
from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

import httpx


USER_AGENT = "NavidromeLibrarian/1.0 (+https://github.com/abucalip/navi-librarian)"


_token_source: Callable[[], str] | None = None


def set_token_source(source: Callable[[], str] | None) -> None:
    """Register where the saved token is read from (the app's Settings store)."""
    global _token_source
    _token_source = source


def request_headers(environ: dict[str, str] | None = None) -> dict[str, str]:
    """Identify the app honestly; add the owner's token only when one is configured.

    An explicit ``environ`` is read as given. Otherwise the saved Settings token is
    used, with the ``LISTENBRAINZ_TOKEN`` environment variable as a fallback.
    """
    headers = {"User-Agent": USER_AGENT}
    token = ""
    if environ is None and _token_source is not None:
        try:
            token = str(_token_source() or "").strip()
        except Exception:
            token = ""
    if not token:
        env = os.environ if environ is None else environ
        token = str(env.get("LISTENBRAINZ_TOKEN") or "").strip()
    if token:
        headers["Authorization"] = f"Token {token}"
    return headers


def recent_listens(
    username: str,
    days: int = 30,
    page_limit: int = 3,
    *,
    client_factory: Callable[..., Any] | None = None,
    clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> list[dict[str, Any]]:
    """Fetch recent public listens in bounded pages without application globals."""
    make_client = client_factory or httpx.Client
    now = clock or time.time
    pause = sleep or time.sleep
    min_ts = int(now()) - days * 86400
    max_ts = None
    listens: list[dict[str, Any]] = []
    page_size = 100
    headers = request_headers()

    from recommendation_run_metrics import record_provider_call

    # Pages run newest first with max_ts only. A min_ts bound makes the API return the oldest
    # page after the bound, so the window is kept by filtering each page instead.
    with make_client(timeout=30, follow_redirects=True) as client:
        for _ in range(page_limit):
            params = {"count": page_size}
            if max_ts is not None:
                params["max_ts"] = max_ts
            response = client.get(
                f"https://api.listenbrainz.org/1/user/{username}/listens",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            page = response.json().get("payload", {}).get("listens", [])
            if not page:
                break
            listens.extend(item for item in page if int(item.get("listened_at", 0)) > min_ts)
            if len(page) < page_size:
                break
            oldest = min(int(item.get("listened_at", 0)) for item in page)
            if oldest <= min_ts:
                break
            max_ts = oldest - 1
            pause(0.2)
    return listens
