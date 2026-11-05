"""Deterministic text and identifier normalization for matching (docs/ServerV2.md 6.5).

Pure functions, no I/O. Normalized strings are matching aids only: they decide whether
two spellings are *candidates* for the same thing, never that they are the same thing.
Edition words (deluxe, remaster, live) are kept in the comparison key on purpose, so a
release and its reissue never compare equal.
"""
from __future__ import annotations

import re
import unicodedata

_MBID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_ISRC_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{3}[0-9]{7}$")
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)
_SPACES = re.compile(r"\s+")
# Marker words that name an edition; used only to report them, never to strip them from keys.
_EDITION_WORDS = (
    "deluxe", "expanded", "remaster", "remastered", "anniversary", "reissue", "bonus",
    "special edition", "collector's edition", "collectors edition", "live", "mono", "stereo",
    "super deluxe", "legacy edition", "limited edition",
)
_BRACKETED = re.compile(r"[\(\[]([^\)\]]*)[\)\]]")


def normalize_text(value: str | None) -> str:
    """Case-, accent-, punctuation- and spacing-insensitive form of a name or title.

    ``&`` reads as "and"; apostrophes and other punctuation vanish; letters from any
    script are kept. ``None`` and blanks give ``""``.
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value).replace("&", " and ")
    text = "".join(c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c))
    text = _NON_WORD.sub("", text.casefold().replace("-", " ").replace("_", " "))
    return _SPACES.sub(" ", text).strip()


def artist_key(value: str | None) -> str:
    """Comparison key for an artist or album-artist string; a leading "The" is ignored."""
    key = normalize_text(value)
    return key[4:] if key.startswith("the ") and len(key) > 4 else key


def title_key(value: str | None) -> str:
    """Comparison key for an album or track title; edition words stay in the key."""
    return normalize_text(value)


def edition_markers(title: str | None) -> list[str]:
    """Edition words found inside brackets of a title, lower-case, in order of appearance."""
    found: list[str] = []
    for group in _BRACKETED.findall(title or ""):
        lowered = group.casefold()
        found.extend(word for word in _EDITION_WORDS if word in lowered and word not in found)
    return found


def normalize_mbid(value: str | None) -> str | None:
    """Lower-case MusicBrainz id, or ``None`` when the value is not a well-formed UUID."""
    if not value:
        return None
    candidate = value.strip().casefold()
    return candidate if _MBID_RE.match(candidate) else None


def normalize_isrc(value: str | None) -> str | None:
    """Upper-case ISRC without hyphens or spaces, or ``None`` if it is not 12 valid characters."""
    if not value:
        return None
    candidate = re.sub(r"[\s-]", "", value).upper()
    return candidate if _ISRC_RE.match(candidate) else None


def durations_match(left_ms: int | None, right_ms: int | None, tolerance_ms: int = 3000) -> bool:
    """True when both lengths are known and differ by at most the tolerance."""
    if left_ms is None or right_ms is None:
        return False
    return abs(int(left_ms) - int(right_ms)) <= tolerance_ms
