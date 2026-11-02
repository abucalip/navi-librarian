"""Pure selection and shaping policy for Deezer artwork results."""

from collections.abc import Iterable
from typing import Any

from app.services.deezer_album_matching import artwork_match_score, release_year


def select_album_artwork(
    albums: Iterable[dict[str, Any]], artist: str, album: str
) -> dict[str, Any] | None:
    """Choose a sufficiently relevant album result and shape its artwork payload."""
    candidates = list(albums)
    if not candidates:
        return None

    match = max(candidates, key=lambda item: artwork_match_score(item, artist, album))
    if artwork_match_score(match, artist, album) < 9:
        return None

    # Cards show covers at most ~220 CSS px wide, so the 500px image is plenty; the 1000px
    # cover_xl is several times the bytes and made rows of covers slow to fill in.
    artwork = match.get("cover_big") or match.get("cover_xl") or match.get("cover_medium")
    return {
        "artwork_url": artwork.replace("http://", "https://", 1) if artwork else None,
        "image_kind": "album",
        "source": "Deezer",
        "matched_artist": (match.get("artist") or {}).get("name"),
        "matched_album": match.get("title"),
        "year": release_year(match.get("release_date")),
    }


def _fans(value: Any) -> int:
    """Deezer's fan count as a number; a missing or odd value counts as none."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


def pick_artist(artists: Iterable[dict[str, Any]], artist: str) -> dict[str, Any] | None:
    """The Deezer artist with exactly this name (case aside), or None.

    Deezer lists several unrelated artists with the same name (a label's one-off release, a
    tribute act) in a changing order, so the first exact match is not necessarily the artist.
    Among the exact names, the one with the most fans is the artist people mean; the list order
    breaks ties.
    """
    artist_key = artist.casefold()
    if not artist_key:
        return None
    exact = [item for item in artists if str(item.get("name") or "").casefold() == artist_key]
    return max(exact, key=lambda item: _fans(item.get("nb_fan"))) if exact else None


def select_artist_artwork(
    artists: Iterable[dict[str, Any]], artist: str, year: int | None = None
) -> dict[str, Any] | None:
    """Select the exact-name artist (see ``pick_artist``) and shape its photo payload."""
    match = pick_artist(artists, artist)
    if match is None:
        return None

    photo = match.get("picture_big") or match.get("picture_xl") or match.get("picture_medium")
    if not photo:
        return None

    return {
        "artwork_url": photo.replace("http://", "https://", 1),
        "image_kind": "artist",
        "source": "Deezer",
        "matched_artist": match.get("name"),
        "year": year,
    }
