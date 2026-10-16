"""Pure response projection for personal music recommendations.

Ownership decisions and their selected/review payload annotations are applied by
the server adapter after allocation; this helper only projects candidate data.
"""
from __future__ import annotations

from typing import Any, Mapping


def build_personal_recommendation_payload(
    candidate: Mapping[str, Any],
    recent_artist_listens: int,
) -> dict[str, Any]:
    """Build the legacy base payload for a prepared personal recommendation."""
    category = candidate["discovery_category"]
    reason = {
        "adjacent": (
            "Genre tags connect this artist to your established musical interests."
        ),
        "cross_genre": (
            "Genre tags suggest a bridge between multiple musical families in your profile."
        ),
        "adventurous": (
            "Available genre tags suggest a departure from the strongest mapped genre matches."
        ),
        "unclassified": (
            "Genre metadata is unavailable, so this candidate's musical fit is uncertain."
        ),
    }[category]
    if not candidate["genre_metadata_available"]:
        reason += (
            " Genre metadata was unavailable, so this classification has low confidence."
        )

    return {
        "artist": candidate["artist"],
        "album": candidate["album"],
        "discovery_category": category,
        "diversity_style": candidate.get("diversity_style", "other"),
        "genres": candidate["genres"],
        "genre_families": candidate["genre_families"],
        "recent_profile_family": candidate.get("recent_profile_family"),
        "recent_profile_families": candidate.get("recent_profile_families", []),
        "recent_profile_bonus": round(candidate.get("recent_profile_bonus", 1.0), 3),
        "genre_metadata_available": candidate["genre_metadata_available"],
        "listenbrainz_score": (
            candidate["score"]
            if candidate.get("discovery_source", "listenbrainz") == "listenbrainz"
            else None
        ),
        "discovery_source": candidate.get("discovery_source", "listenbrainz"),
        "discovery_score": round(candidate["discovery_score"], 6),
        "recent_artist_listens": recent_artist_listens,
        "lastfm_listeners": candidate.get("lastfm_listeners"),
        "lastfm_playcount": candidate.get("lastfm_playcount"),
        "lastfm_tags": candidate.get("lastfm_tags", []),
        "lastfm_popularity_bonus": round(
            candidate.get("lastfm_popularity_bonus", 1.0), 3
        ),
        "suggested_tracks": candidate["tracks"][:3],
        "reason": reason,
    }
