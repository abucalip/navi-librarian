"""Dashboard and health API routes.

These HTTP handlers use the shared lazy librarian dependency; discovery behavior
and Navidrome connectivity remain owned by the existing service implementation.
"""
import random

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.utils import parse_result

router = APIRouter()


@router.get("/api/health")
def health(librarian=Depends(get_librarian)):
    """Check whether Navidrome responds to an authenticated API request."""
    try:
        result = librarian.api_call("ping")
        return {
            "status": "ok",
            "service": "Navidrome",
            "message": result.get("status", "Connected"),
        }
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Navidrome is unavailable or authentication failed.",
        )


@router.get("/api/dashboard-picks")
def dashboard_picks(count: int = 10, librarian=Depends(get_librarian)):
    if not 1 <= count <= 20:
        raise HTTPException(status_code=400, detail="count must be between 1 and 20")
    combined = []
    by_category = {}
    seen = set()
    categories = (
        ("personal", "Personal discoveries"),
        ("classics", "Add to your collection"),
        ("artist_deep_dive", "Artist Deep Dives"),
    )
    for _list_name, label in categories:
        by_category[label] = []
    for list_name, label in categories:
        try:
            data = parse_result(librarian.discovery_get_list(list_name=list_name, count=150))
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
            if not librarian._discovery_is_album_candidate(item):
                continue
            identity = (artist.casefold(), album.casefold())
            if not artist or not album or identity in seen:
                continue
            seen.add(identity)
            candidate = {**item, "artist": artist, "album": album, "dashboard_category": label}
            combined.append(candidate)
            by_category[label].append(candidate)

    # Guarantee a balanced representation when all discovery lanes have data,
    # then fill the remaining slots from the whole deduplicated pool.
    random_picks = []
    quota = max(1, count // len(categories))
    for label in [entry[1] for entry in categories]:
        lane = by_category[label]
        random.shuffle(lane)
        random_picks.extend(lane[:quota])
    picked_ids = {
        (item["artist"].casefold(), item["album"].casefold())
        for item in random_picks
    }
    remainder = [
        item for item in combined
        if (item["artist"].casefold(), item["album"].casefold()) not in picked_ids
    ]
    random.shuffle(remainder)
    random_picks.extend(remainder[:max(0, count - len(random_picks))])
    random.shuffle(random_picks)
    return {"items": random_picks[:count], "count": min(count, len(random_picks)), "pool_size": len(combined)}
