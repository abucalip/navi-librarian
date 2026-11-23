"""Direct Apple Music artist-biography lookup using its public iTunes and web endpoints.

The iTunes Search API resolves an exact artist name to an Apple artist ID. The public artist page
contains JSON-LD metadata; its description is accepted only when the embedded artist name matches
the requested name. No Apple developer token, Navidrome plugin, or user credential is required.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from typing import Any

APPLE_SEARCH_URL = "https://itunes.apple.com/search"
APPLE_PAGE_URL = "https://music.apple.com/{country}/artist/-/{artist_id}"
APPLE_COUNTRIES = ("us",)
APPLE_TIMEOUT = 2.0
APPLE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    ),
    "Accept": "text/html,application/json",
}
_JSON_LD = re.compile(
    r"<script\b(?=[^>]*\btype=[\"']application/ld\+json[\"'])[^>]*>(.*?)</script\s*>",
    re.IGNORECASE | re.DOTALL,
)
_TAG = re.compile(r"<[^>]+>")
_PLACEHOLDER = re.compile(r"\bApple[\s\u00a0]+Music\b", re.IGNORECASE)


def normalize_artist_name(value: str) -> str:
    """Compare names without case, accents, punctuation, or spacing differences."""
    decomposed = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(char for char in decomposed if char.isalnum())


def _clean_text(value: str) -> str:
    return " ".join(html.unescape(_TAG.sub("", value or "")).split()).strip()


def _is_placeholder(value: str) -> bool:
    first_sentence = re.split(r"(?<=[.!?])\s+", value, maxsplit=1)[0]
    return bool(_PLACEHOLDER.search(first_sentence))


def _find_description(node: Any, wanted: str, depth: int = 0) -> str | None:
    """Find a JSON-LD artist description whose name exactly matches the requested artist."""
    if depth > 12:
        return None
    if isinstance(node, dict):
        name = node.get("name")
        description = node.get("description")
        types = node.get("@type", [])
        if isinstance(types, str):
            types = [types]
        allowed = {"musicgroup", "musicartist", "person"}
        if (
            isinstance(name, str)
            and normalize_artist_name(name) == wanted
            and any(str(kind).casefold() in allowed for kind in types)
            and isinstance(description, str)
        ):
            text = _clean_text(description)
            if text and not _is_placeholder(text):
                return text
        for value in node.values():
            found = _find_description(value, wanted, depth + 1)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_description(value, wanted, depth + 1)
            if found:
                return found
    return None


def parse_artist_biography(page: str, artist: str) -> str | None:
    """Extract an exact-name Apple Music JSON-LD biography, or None for no usable bio."""
    wanted = normalize_artist_name(artist)
    if not wanted:
        return None
    for match in _JSON_LD.finditer(page or ""):
        try:
            payload = json.loads(match.group(1))
        except (TypeError, ValueError):
            continue
        bio = _find_description(payload, wanted)
        if bio:
            return bio
    return None


def _exact_artist_id(results: list[dict[str, Any]], artist: str) -> int | None:
    wanted = normalize_artist_name(artist)
    matches = {
        int(item["artistId"])
        for item in results
        if isinstance(item, dict)
        and item.get("wrapperType") == "artist"
        and normalize_artist_name(item.get("artistName", "")) == wanted
        and str(item.get("artistId", "")).isdigit()
    }
    # Same-name artists are ambiguous. Do not silently pick a different performer.
    return next(iter(matches)) if len(matches) == 1 else None


def lookup_artist_biography(get, artist: str) -> tuple[str | None, bool]:
    """Return (biography, answered): answered distinguishes a no-bio result from provider failure."""
    name = str(artist or "").strip()
    if not name:
        return None, True
    try:
        response = get(
            APPLE_SEARCH_URL,
            params={"term": name, "entity": "musicArtist", "limit": 10, "country": APPLE_COUNTRIES[0]},
            headers=APPLE_HEADERS,
            timeout=APPLE_TIMEOUT,
        )
        response.raise_for_status()
        results = response.json().get("results") or []
    except Exception:
        return None, False

    artist_id = _exact_artist_id(results, name)
    if artist_id is None:
        return None, True

    answered = False
    for country in APPLE_COUNTRIES:
        try:
            response = get(
                APPLE_PAGE_URL.format(country=country, artist_id=artist_id),
                headers=APPLE_HEADERS,
                timeout=APPLE_TIMEOUT,
            )
            response.raise_for_status()
            answered = True
            biography = parse_artist_biography(response.text, name)
            if biography:
                return biography, True
        except Exception:
            continue
    return None, answered
