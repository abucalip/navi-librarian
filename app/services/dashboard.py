"""Dashboard-pick assembly independent of FastAPI and app initialization."""

import random
from collections.abc import Callable
from typing import Any


_CATEGORIES = (
    ("personal", "Personal discoveries"),
    ("classics", "Add to your collection"),
    ("artist_deep_dive", "Artist Deep Dives"),
)


def build_dashboard_picks(
    read_list: Callable[[str, int], Any],
    is_album_candidate: Callable[[dict[str, Any]], bool],
    count: int,
    *,
    shuffle: Callable[[list[Any]], None] = random.shuffle,
) -> dict[str, Any]:
    """Build balanced, case-insensitively deduplicated dashboard picks.

    Discovery reads and album eligibility are injected so the service can be
    tested without importing the legacy librarian module or FastAPI routes.
    A failed lane is skipped as before; the remaining lanes still contribute.
    """
    combined: list[dict[str, Any]] = []
    by_category: dict[str, list[dict[str, Any]]] = {
        label: [] for _, label in _CATEGORIES
    }
    seen: set[tuple[str, str]] = set()

    for list_name, label in _CATEGORIES:
        try:
            data = read_list(list_name, 150)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        items = data.get("items") or data.get("recommendations") or []
        for item in items:
            if not isinstance(item, dict):
                continue
            artist = str(item.get("artist") or item.get("album_artist") or "").strip()
            album = str(item.get("album") or item.get("title") or "").strip()
            if not is_album_candidate(item):
                continue
            identity = (artist.casefold(), album.casefold())
            if not artist or not album or identity in seen:
                continue
            seen.add(identity)
            candidate = {**item, "artist": artist, "album": album, "dashboard_category": label}
            combined.append(candidate)
            by_category[label].append(candidate)

    # Guarantee balanced representation when every lane has data, then fill
    # remaining slots from the whole deduplicated pool.
    picks: list[dict[str, Any]] = []
    quota = max(1, count // len(_CATEGORIES))
    for _, label in _CATEGORIES:
        lane = by_category[label]
        shuffle(lane)
        picks.extend(lane[:quota])
    picked_ids = {
        (item["artist"].casefold(), item["album"].casefold())
        for item in picks
    }
    remainder = [
        item for item in combined
        if (item["artist"].casefold(), item["album"].casefold()) not in picked_ids
    ]
    shuffle(remainder)
    picks.extend(remainder[:max(0, count - len(picks))])
    shuffle(picks)
    return {
        "items": picks[:count],
        "count": min(count, len(picks)),
        "pool_size": len(combined),
    }
