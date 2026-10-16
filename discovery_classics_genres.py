"""Bounded genre enrichment policy for the classics discovery list.

Provider/cache behavior stays in the injected lookup callable. The helper owns
only normalized-artist lookup deduplication, the enrichment bound, and fallback
metadata for candidates outside the enriched prefix.
"""
from collections.abc import Callable, Iterable
from typing import Any
import unicodedata


def _artist_key(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return "".join(char.casefold() for char in value if char.isalnum())


def enrich_classic_genres(
    ranked: Iterable[dict[str, Any]],
    genre_lookup: Callable[[str], list[str]],
    family_classifier: Callable[[Iterable[str]], Iterable[str]],
    *,
    limit: int = 300,
) -> None:
    """Enrich the ranked prefix in place while preserving candidate order."""
    if limit < 0:
        raise ValueError("limit must be non-negative")

    candidates = list(ranked)
    genre_cache: dict[str, list[str]] = {}
    for item in candidates[:limit]:
        artist = item.get("artist", "")
        key = _artist_key(artist)
        if key not in genre_cache:
            genre_cache[key] = genre_lookup(artist)
        genres = genre_cache[key]
        item["genres"] = genres
        families = sorted(family_classifier(genres))
        item["genre_families"] = families or ["other"]

    for item in candidates[limit:]:
        item["genres"] = []
        item["genre_families"] = ["other"]
