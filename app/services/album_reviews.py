"""Pure parsing and matching for the album page's Reviews tab.

Each source yields at most one review: the outlet's own summary line (its "dek"), a link to the
full review, and the outlet's name. A review is used only when its artist and album match the
request exactly, because a quote under the wrong record is worse than none. Nothing here fetches;
the caller passes the page text or the decoded JSON.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any
from urllib.parse import urljoin

from discovery.search.normalize import fold

MAX_REVIEWS = 3
MIN_DEK_LENGTH = 30
MAX_DEK_LENGTH = 300
MAX_DEK_SENTENCES = 2

_TAG = re.compile(r"<[^>]+>")
_BLOCK_END = re.compile(r"<br\s*/?>|</(?:p|div|li)>", re.IGNORECASE)
_BRACKETED = re.compile(r"\s*[(\[][^)\]]*[)\]]")
_SENTENCE_END = re.compile(r"(?<=[.!?])[\"'”’)]*\s+(?=[\"'“‘(]*[A-Z0-9])")
# Lines an outlet shows instead of a summary of the record: Pitchfork's weekly reissue reviews, and the
# stub Angry Metal Guy leaves where it removed a post.
_BOILERPLATE = ("each sunday, pitchfork", "this post has been removed", "this review has been removed")


# "Kind of Blue: 50th Anniversary Edition" is a review of Kind of Blue; the edition is not another album.
_EDITION_SUFFIX = re.compile(
    r"\s*[:\-–—]\s*(?:the\s+)?(?:\d+(?:st|nd|rd|th)\s+)?(?:anniversary|deluxe|expanded|remaster(?:ed)?|reissue|"
    r"legacy|special|collector'?s|limited|super deluxe|bonus|mono|stereo)\b.*$", re.IGNORECASE)


_DISC_SUFFIX = re.compile(r"\s+(?:disc|cd)\s*\d+\s*$", re.IGNORECASE)


def match_key(text: object) -> str:
    """A name reduced for exact comparison: no edition brackets or suffix, "and", or leading "The"."""
    original = fold(text)
    stripped = fold(_EDITION_SUFFIX.sub("", _DISC_SUFFIX.sub("", _BRACKETED.sub("", str(text or ""))))) or original
    words = [word for word in stripped.split() if word != "and"]
    if words and words[0] == "the" and len(words) > 1:
        words = words[1:]
    return " ".join(words)


_EDITION_NOISE = re.compile(r"(?:\s*[(\[][^)\]]*[)\]]|\s+(?:disc|cd)\s*\d+)+\s*$", re.IGNORECASE)


def search_text(artist: str, album: str) -> str:
    """A search query for an artist and album, without trailing edition brackets or "Disc 1"."""
    parts = [re.sub(r"\s+", " ", _EDITION_NOISE.sub("", part)).strip() or part.strip() for part in (artist, album)]
    return " ".join(part for part in parts if part)


def _plain(text: object) -> str:
    # Inline tags (<em>) vanish without a gap so punctuation stays attached; block ends become spaces.
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub("", _BLOCK_END.sub(" ", str(text or ""))))).strip()


def clean_dek(text: object) -> str | None:
    """The summary line as plain text, or None when it is not a usable one-or-two-sentence summary.

    A dek that is really the opening of the review (more than two sentences), a cut-off page
    description, or a fixed line a site uses for a whole series is rejected.
    """
    dek = _plain(text)
    if not (MIN_DEK_LENGTH <= len(dek) <= MAX_DEK_LENGTH):
        return None
    if dek.endswith(("...", "…")) or dek.casefold().startswith(_BOILERPLATE):
        return None
    if len(_SENTENCE_END.split(dek)) > MAX_DEK_SENTENCES:
        return None
    return dek


def review(source: str, quote: object, url: str) -> dict[str, str] | None:
    dek = clean_dek(quote)
    return {"source": source, "quote": dek, "url": url} if dek and url.startswith("https://") else None


_HEADLINE_BREAK = re.compile(r"\s+reviews?\b|\s+[–—]\s+|\s+\|\s+", re.IGNORECASE)
_CATCHPHRASE = re.compile(r"(?:[!?…]|\.{3})\s*")


def _title_candidates(title: object) -> list[str]:
    """The headline without its leading "Review:" label or catchphrase, whole and cut at each review or tagline break.

    "AAHHH! John Coltrane: Afro Blue Impressions" also yields "John Coltrane: Afro Blue Impressions".
    """
    text = re.sub(r"^(?:album|ep|lp)?\s*reviews?\s*[:\-–—|]\s*", "", _plain(title), flags=re.IGNORECASE)
    starts = [0] + [match.end() for match in _CATCHPHRASE.finditer(text)]
    found = []
    for start in starts:
        rest = text[start:]
        found += [rest] + [rest[:match.start()] for match in _HEADLINE_BREAK.finditer(rest)]
    return found


def title_matches(title: object, artist: str, album: str) -> bool:
    """True when a headline is exactly "Artist: Album" in either order, before any review label or tagline."""
    artist_key, album_key = match_key(artist), match_key(album)
    if not artist_key or not album_key:
        return False
    wanted = (f"{artist_key} {album_key}", f"{album_key} {artist_key}")
    return any(match_key(candidate) in wanted for candidate in _title_candidates(title))


# --- Pitchfork -----------------------------------------------------------------------------------

_PRELOADED_STATE = re.compile(r"window\.__PRELOADED_STATE__\s*=\s*(\{.*?\});?\s*</script>", re.S)


def parse_pitchfork_search(page: str) -> list[dict[str, str]]:
    """The review results of a Pitchfork search page: artist, album, dek and path of each."""
    match = _PRELOADED_STATE.search(page or "")
    if not match:
        return []
    try:
        groups = json.loads(match.group(1))["transformed"]["search"]["items"]
    except (ValueError, KeyError, TypeError):
        return []
    found = []
    for group in groups if isinstance(groups, list) else []:
        for item in group.get("items") or []:
            if not isinstance(item, dict) or item.get("contentType") != "review":
                continue
            sub = item.get("subHed") if isinstance(item.get("subHed"), dict) else {}
            found.append({
                "artist": _plain(sub.get("name")), "album": _plain(item.get("dangerousHed")),
                "dek": item.get("dangerousDek") or "", "path": str(item.get("url") or sub.get("url") or ""),
            })
    return found


def pick_pitchfork(results: list[dict[str, str]], artist: str, album: str) -> dict[str, str] | None:
    for item in results:
        if match_key(item["artist"]) == match_key(artist) and match_key(item["album"]) == match_key(album):
            if item["path"]:
                return review("Pitchfork", item["dek"], urljoin("https://pitchfork.com/", item["path"].strip("/") + "/"))
    return None


# --- The Guardian --------------------------------------------------------------------------------

def pick_guardian(payload: Any, artist: str, album: str) -> dict[str, str] | None:
    """The Guardian Open Platform answer's first review whose headline names the album exactly."""
    results = ((payload or {}).get("response") or {}).get("results") if isinstance(payload, dict) else None
    for item in results or []:
        if not isinstance(item, dict) or not title_matches(item.get("webTitle"), artist, album):
            continue
        found = review("The Guardian", (item.get("fields") or {}).get("trailText"), str(item.get("webUrl") or ""))
        if found:
            return found
    return None


# --- WordPress review sites ----------------------------------------------------------------------

def pick_wordpress_post(results: Any, artist: str, album: str) -> str | None:
    """The address of the first search result whose headline names the album exactly."""
    for item in results if isinstance(results, list) else []:
        if isinstance(item, dict) and title_matches(item.get("title"), artist, album):
            url = str(item.get("url") or "")
            if url.startswith("https://"):
                return url
    return None


_META_DESCRIPTION = re.compile(
    r"<meta\s+(?:[^>]*?\s)?(?:property|name)=[\"'](?:og:description|description)[\"'][^>]*?\scontent=[\"']([^\"']*)[\"']"
    r"|<meta\s+(?:[^>]*?\s)?content=[\"']([^\"']*)[\"'][^>]*?\s(?:property|name)=[\"'](?:og:description|description)[\"']",
    re.IGNORECASE,
)


def page_dek(page: str) -> str | None:
    """The summary a review page gives in its description metadata, when it is a usable dek."""
    for match in _META_DESCRIPTION.finditer(page or ""):
        dek = clean_dek(match.group(1) or match.group(2))
        if dek:
            return dek
    return None


def pick_reviews(found: list[dict[str, str] | None]) -> list[dict[str, str]]:
    """Up to three reviews in source order, one per outlet and one per distinct link."""
    picked: list[dict[str, str]] = []
    for item in found:
        if item and all(item["source"] != p["source"] and item["url"] != p["url"] for p in picked):
            picked.append(item)
    return picked[:MAX_REVIEWS]
