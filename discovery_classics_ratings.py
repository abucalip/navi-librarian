"""Critical-rating enrichment policy for the classics discovery list.

Provider/cache behavior stays in the injected lookup callable. This module owns
only deterministic shortlist ordering, request bounds, and candidate enrichment.
"""
from collections.abc import Callable, Iterable
from typing import Any


def enrich_critical_ratings(
    candidates: Iterable[dict[str, Any]],
    rating_lookup: Callable[..., dict[str, Any] | None],
    *,
    shortlist_limit: int = 80,
    year_limit: int = 30,
) -> None:
    """Enrich the listener-ranked shortlist in place, preserving legacy limits."""
    if shortlist_limit < 0 or year_limit < 0:
        raise ValueError("shortlist_limit and year_limit must be non-negative")

    shortlist = sorted(
        candidates,
        key=lambda item: int(item.get("lastfm_listeners") or 0),
        reverse=True,
    )[:shortlist_limit]
    for index, candidate in enumerate(shortlist):
        rating = rating_lookup(candidate.get("mbid"), include_year=index < year_limit)
        if not rating:
            continue
        candidate["musicbrainz_rating"] = rating.get("rating")
        candidate["musicbrainz_rating_votes"] = rating.get("votes", 0)
        if rating.get("year"):
            candidate["year"] = rating["year"]
