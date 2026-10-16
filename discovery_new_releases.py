"""Pure MusicBrainz release-group eligibility for New Releases discovery."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_new_release_lookup(
    artist: str,
    *,
    artist_key: str,
    earliest_year: int,
    current_year: int,
) -> tuple[str, str]:
    """Build the stable cache key and MusicBrainz query for one library artist."""
    cache_key = f"mb:new-releases:v1:{earliest_year}:{artist_key}"
    escaped_artist = artist.replace("\\", "\\\\").replace('"', '\\"')
    query = (
        f'artist:"{escaped_artist}" AND primarytype:album '
        f'AND firstreleasedate:[{earliest_year} TO {current_year}]'
    )
    return cache_key, query


def select_artist_release_candidates(
    release_groups: list[Any],
    *,
    artist: str,
    artist_record: Mapping[str, Any],
    owned: set[tuple[str, str]],
    cutoff_date: str,
    current_year: int,
    music_key: Callable[[Any], str],
    is_album_candidate: Callable[[Any], bool],
    exact_artist_credit_matches: Callable[[Any, str], bool],
    is_various_artists: Callable[[Any], bool],
) -> dict[tuple[str, str], dict[str, Any]]:
    """Select eligible, unowned release groups credited exactly to one library artist.

    Provider retrieval, cache/error handling, rate limiting, and global candidate
    merging remain with the caller. Dependencies are injected to preserve the
    existing discovery rules without importing the server module.
    """
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for group in release_groups:
        if not isinstance(group, dict) or group.get("primary-type") != "Album":
            continue
        title = str(group.get("title") or "").strip()
        release_date = str(group.get("first-release-date") or "")
        year_text = release_date[:4]
        if not title or not year_text.isdigit():
            continue
        year = int(year_text)
        if release_date < cutoff_date or year > current_year:
            continue
        candidate = {
            "artist": artist,
            "album": title,
            "year": year,
            "first_release_date": release_date,
            "mbid": group.get("id"),
            "primary_type": group.get("primary-type"),
            "secondary_types": group.get("secondary-types") or [],
            "discovery_type": "new_release",
            "discovery_source": "MusicBrainz recent release groups",
            "reason": f"Released in {year} by an artist with a full album in your library",
            "artist_library_album_count": int(artist_record.get("album_count") or 0),
        }
        if not is_album_candidate(candidate):
            continue
        artist_credit = group.get("artist-credit")
        if not exact_artist_credit_matches(artist_credit, artist):
            continue
        if is_various_artists(artist):
            continue
        credited_names = " ".join(
            str((part.get("artist") or {}).get("name") or part.get("name") or "")
            for part in (artist_credit or [])
            if isinstance(part, dict)
        )
        if is_various_artists(credited_names):
            continue
        identity = (music_key(artist), music_key(title))
        if identity in owned:
            continue
        old = selected.get(identity)
        if old is None or release_date > old.get("first_release_date", ""):
            selected[identity] = candidate
    return selected


def prepare_new_release_library_scope(
    artists: list[dict[str, Any]],
    albums: list[dict[str, Any]],
    *,
    music_key: Callable[[Any], str],
    is_various_artists: Callable[[Any], bool],
) -> tuple[set[tuple[str, str]], list[dict[str, Any]]]:
    """Return normalized owned identities and full-album-qualified artists.

    This pure inventory policy preserves the existing six-track threshold,
    Various Artists exclusion, stable album-count ordering, and untruncated
    qualified-artist count. Provider access, date-window policy, and the 120
    artist request bound remain with the caller.
    """
    owned = {
        (music_key(item.get("artist", "")), music_key(item.get("album", "")))
        for item in albums
    }
    full_album_artist_keys = {
        music_key(item.get("artist", ""))
        for item in albums
        if int(item.get("song_count") or 0) >= 6 and item.get("artist")
    }
    qualified_artists = [
        artist for artist in artists
        if artist.get("name")
        and not is_various_artists(artist["name"])
        and music_key(artist["name"]) in full_album_artist_keys
    ]
    qualified_artists.sort(key=lambda item: int(item.get("album_count") or 0), reverse=True)
    return owned, qualified_artists


def merge_release_candidates(existing: dict[tuple[str, str], dict[str, Any]], incoming: Mapping[tuple[str, str], dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    """Merge per-artist candidates, keeping the newest release per identity.

    Inputs are not mutated. Existing candidates win equal-date ties, preserving
    the server adapter's prior stable merge behavior.
    """
    merged = dict(existing)
    for identity, candidate in incoming.items():
        old = merged.get(identity)
        if old is None or str(candidate.get("first_release_date") or "") > str(old.get("first_release_date") or ""):
            merged[identity] = candidate
    return merged


def build_new_release_response(
    candidates: Mapping[tuple[str, str], dict[str, Any]],
    *,
    qualified_library_artists: int,
    artists_scanned: int,
    lookup_errors: list[dict[str, str]],
    earliest_year: int,
    cutoff_date: str,
    generated_at: float,
) -> dict[str, Any]:
    """Sort selected candidates and shape the established New Releases payload.

    This is deliberately a pure response boundary: discovery/provider calls,
    date-window calculation, candidate eligibility, and error collection remain
    in the server adapter. Explicit metadata inputs make the response contract
    directly testable without clocks, network access, or a Navidrome server.
    """
    items_out = sorted(
        candidates.values(),
        key=lambda item: (
            str(item.get("first_release_date") or ""),
            str(item.get("artist") or "").casefold(),
            str(item.get("album") or "").casefold(),
        ),
        reverse=True,
    )
    return {
        "list": "new_releases",
        "source": "MusicBrainz release groups matched against the Navidrome library",
        "generated_at": generated_at,
        "year_from": earliest_year,
        "date_from": cutoff_date,
        "qualified_library_artists": qualified_library_artists,
        "artists_scanned": artists_scanned,
        "items": items_out[:200],
        "lookup_errors": lookup_errors[:20],
        "limitations": [
            "Only artists with at least one library album containing six or more tracks qualify.",
            "The release window is the previous 730 days.",
            "MusicBrainz release-group coverage and release dates may be incomplete.",
            "The initial refresh is bounded to the 120 library artists with the largest album counts.",
        ],
    }
