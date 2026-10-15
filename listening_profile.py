"""Pure aggregation for recent listening history."""

from collections import Counter
from typing import Any, Iterable


def build_listening_profile(
    listens: Iterable[dict[str, Any]], username: str, days: int
) -> dict[str, Any]:
    """Build the stable public profile payload from ListenBrainz listen records."""
    records = list(listens)
    artists: Counter[str] = Counter()
    albums: Counter[tuple[str, str]] = Counter()

    for listen in records:
        meta = listen.get("track_metadata", {})
        artist = meta.get("artist_name", "")
        album = meta.get("release_name", "")
        if artist:
            artists[artist] += 1
        if artist and album:
            albums[(artist, album)] += 1

    return {
        "source": "ListenBrainz",
        "username": username,
        "period_days": days,
        "listens_retrieved": len(records),
        "distinct_artists": len(artists),
        "top_artists": [
            {"artist": artist, "listens": count}
            for artist, count in artists.most_common(15)
        ],
        "top_albums": [
            {"artist": artist, "album": album, "listens": count}
            for (artist, album), count in albums.most_common(10)
        ],
        "note": (
            "History retrieval is bounded to three pages of up to 100 "
            "listens each. If the limit is reached, results may be incomplete."
        ),
        "read_only": True,
    }
