"""Text normalization for global search, library browsing and owned keys.

Keys are the identity used in URLs and result events (contract sections 3.3 and
4.1). They are derived from display names only, so they never depend on a
provider or a credential.
"""

from __future__ import annotations

import re
import unicodedata

_COMBINING_MARKS = re.compile(r"[̀-ͯ]")
_NON_WORD = re.compile(r"[\W_]+")
_LEADING_THE = re.compile(r"^the (?=.)")


def fold(text: object) -> str:
    """Casefold, strip diacritics and collapse punctuation to single spaces."""
    decomposed = unicodedata.normalize("NFKD", str(text or ""))
    stripped = _COMBINING_MARKS.sub("", decomposed).casefold()
    return _NON_WORD.sub(" ", stripped).strip()


def normalize_key(name: object) -> str:
    """Return the normalized key for an artist, album or song name.

    A leading "The" is dropped, so "The Beatles" and "Beatles" share a key.
    Two Navidrome artists can still share a key; the artist route resolves that
    with the Navidrome ID (contract section 3.3).
    """
    return _LEADING_THE.sub("", fold(name), count=1)


def normalize_query(text: object) -> str:
    """Normalize a search query with the same rules as keys.

    Returns an empty string when the query has no letter or digit; callers reject
    that case with HTTP 400 rather than matching everything.
    """
    return normalize_key(text)
