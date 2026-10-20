"""ListenBrainz HTTP client for bounded recent-listen retrieval."""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import httpx


# Default cap: 5 pages of 100 = 500 listens within the window.
RECENT_LISTENS_PAGE_LIMIT = 5


def recent_listens(
    username: str,
    days: int = 30,
    page_limit: int = RECENT_LISTENS_PAGE_LIMIT,
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
    headers = {"User-Agent": "NavidromeLibrarian/1.0"}

    from recommendation_run_metrics import record_provider_call

    with make_client(timeout=30, follow_redirects=True) as client:
        for _ in range(page_limit):
            params = {"min_ts": min_ts, "count": page_size}
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
            listens.extend(page)
            if len(page) < page_size:
                break
            oldest = min(int(item.get("listened_at", 0)) for item in page)
            if oldest <= min_ts:
                break
            max_ts = oldest - 1
            pause(0.2)
    return listens
