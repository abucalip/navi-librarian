"""Pure helpers that pick an album's Wikipedia article and read its lead as description paragraphs.

Used when Apple Music has no editorial notes. An article is taken only when its title is the album's
name (or the album's name with a disambiguation naming the artist), it is described as an album,
and its description or excerpt names the artist. Anything less could describe a different record.
"""

from __future__ import annotations

import re
from typing import Any

from app.services.album_reviews import _plain, match_key

LICENSE = "CC BY-SA 4.0"
_ALBUM_KIND = re.compile(r"\b(?:album|ep|soundtrack|compilation|mixtape|single|live)\b", re.IGNORECASE)
_DISAMBIGUATION = re.compile(r"^(.*?)\s+\(([^)]*)\)$")


def pick_album_article(pages: Any, artist: str, album: str) -> str | None:
    """The key of the first search result that is exactly this artist's album, or None."""
    artist_key, album_key = match_key(artist), match_key(album)
    if not artist_key or not album_key:
        return None
    for page in pages if isinstance(pages, list) else []:
        if not isinstance(page, dict) or not page.get("key"):
            continue
        title = str(page.get("title") or "")
        split = _DISAMBIGUATION.match(title)
        base, qualifier = (split.group(1), split.group(2)) if split else (title, "")
        if match_key(base) != album_key:
            continue
        text = match_key(f"{page.get('description') or ''} {_plain(page.get('excerpt'))} {qualifier}")
        if _ALBUM_KIND.search(f"{page.get('description') or ''} {qualifier}") and f" {artist_key} " in f" {text} ":
            return str(page["key"])
    return None


def description_from_summary(summary: Any) -> dict[str, Any] | None:
    """``{"paragraphs", "source", "url", "license"}`` from a Wikipedia page-summary answer, or None."""
    if not isinstance(summary, dict) or summary.get("type") == "disambiguation":
        return None
    paragraphs = [part.strip() for part in str(summary.get("extract") or "").split("\n") if part.strip()]
    url = ((summary.get("content_urls") or {}).get("desktop") or {}).get("page")
    if not paragraphs or not isinstance(url, str) or not url.startswith("https://"):
        return None
    return {"paragraphs": paragraphs, "source": "Wikipedia", "url": url, "license": LICENSE}
