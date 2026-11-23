"""CritiqueBrainz inline album reviews client (CB-1).

Pure HTTP ``get`` callable injection with no ``app/`` imports.
Fetches Creative Commons-licensed ``release_group`` reviews from
``https://critiquebrainz.org/ws/1/review/``, filters to ``en``/``fr``/``ar``,
reflows unbroken text into ~90-word paragraphs at sentence boundaries, and
orders by popularity descending.
"""

from __future__ import annotations

import re
from typing import Any, Callable

CRITIQUEBRAINZ_REVIEW_URL = "https://critiquebrainz.org/ws/1/review/"
CRITIQUEBRAINZ_WEB_REVIEW_BASE = "https://critiquebrainz.org/review/"
USER_AGENT = "navi-librarian/1.0 (https://github.com/abucalip/navi-librarian)"

REVIEW_PAGE_TIMEOUT = 4.0
REVIEW_CONNECT_TIMEOUT = 1.5
PAGE_LIMIT = 50
MAX_PAGES = 5
MIN_REVIEW_CHARS = 40
TARGET_PARAGRAPH_WORDS = 90
SENTENCE_WINDOW_WORDS = 35
ELIGIBLE_LANGUAGES = frozenset({"en", "fr", "ar"})

_SENTENCE_END_RE = re.compile(r"[.!?؟](?=\s)")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")


def reflow_paragraphs(
    text: str,
    target_words: int = TARGET_PARAGRAPH_WORDS,
    window_words: int = SENTENCE_WINDOW_WORDS,
) -> list[str]:
    """Normalize line breaks and split unbroken >90-word blocks into paragraphs.

    If ``text`` already contains multiple non-empty lines or ``\\n\\n`` breaks,
    those paragraph breaks are preserved. Otherwise, an unbroken block longer
    than ``target_words`` is split near ``target_words`` at the closest
    sentence-ending punctuation (``.``, ``!``, ``?``, ``؟``) followed by
    whitespace, falling back to the nearest whitespace if no sentence boundary
    exists within ``±window_words``.
    """
    normalized = _MULTI_NEWLINE_RE.sub("\n\n", str(text or "").replace("\r\n", "\n")).strip()
    if not normalized:
        return []

    if "\n" in normalized:
        lines = [line.strip() for line in normalized.split("\n") if line.strip()]
        if len(lines) > 1:
            return lines
        normalized = lines[0] if lines else ""

    words = normalized.split()
    if len(words) <= target_words:
        return [normalized]

    paragraphs: list[str] = []
    remaining = normalized
    while len(remaining.split()) > target_words:
        split_idx = _find_split_index(remaining, target_words, window_words)
        if split_idx <= 0 or split_idx >= len(remaining):
            break
        head = remaining[:split_idx].strip()
        tail = remaining[split_idx:].strip()
        if head:
            paragraphs.append(head)
        if not tail:
            remaining = ""
            break
        remaining = tail

    if remaining.strip():
        paragraphs.append(remaining.strip())
    return paragraphs


def _find_split_index(text: str, target_words: int, window_words: int) -> int:
    """Return the character index at which to split ``text`` near ``target_words``."""
    word_spans = [(m.start(), m.end()) for m in re.finditer(r"\S+", text)]
    if len(word_spans) <= target_words:
        return len(text)

    target_char = word_spans[target_words - 1][1]
    min_word = max(1, target_words - window_words)
    max_word = min(len(word_spans) - 1, target_words + window_words)
    min_char = word_spans[min_word - 1][0]
    max_char = word_spans[max_word - 1][1]

    best_sentence_end: int | None = None
    best_distance: int | None = None
    for match in _SENTENCE_END_RE.finditer(text, min_char, max_char + 1):
        end_pos = match.end()
        dist = abs(end_pos - target_char)
        if best_distance is None or dist < best_distance:
            best_distance = dist
            best_sentence_end = end_pos

    if best_sentence_end is not None:
        return best_sentence_end

    # Fallback: split right after the target_words-th word.
    return target_char


def _extract_quote(text: str, max_sentences: int = 2, max_chars: int = 280) -> str:
    """Return the first 1-2 sentences as a short quote fallback."""
    flat = " ".join(text.split())
    if not flat:
        return ""
    ends = [m.end() for m in _SENTENCE_END_RE.finditer(flat)]
    if ends:
        idx = ends[min(max_sentences, len(ends)) - 1]
        snippet = flat[:idx].strip()
        if len(snippet) <= max_chars:
            return snippet
    if len(flat) <= max_chars:
        return flat
    cut = flat[:max_chars].rsplit(" ", 1)[0].strip()
    return f"{cut}..." if cut else flat[:max_chars]


def _extract_author(raw: dict[str, Any]) -> str:
    user = raw.get("user")
    if isinstance(user, dict):
        name = str(user.get("display_name") or user.get("name") or "").strip()
        if name:
            return name
    return str(raw.get("author") or "").strip()


def _extract_license(raw: dict[str, Any]) -> tuple[str, str]:
    lic = raw.get("license")
    if isinstance(lic, dict):
        name = str(lic.get("id") or lic.get("full_name") or lic.get("name") or "").strip()
        url = str(lic.get("info_url") or lic.get("url") or "").strip()
        return name, url
    if isinstance(lic, str):
        return lic.strip(), str(raw.get("license_url") or "").strip()
    return "", ""


def _safe_rating(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def _popularity_score(raw: dict[str, Any]) -> float:
    for key in ("popularity", "votes_positive_count", "votes_count"):
        val = raw.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            return float(val)
    return 0.0


def _normalize_review(raw: dict[str, Any]) -> tuple[tuple[float, int, str], dict[str, Any]] | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("is_draft") or raw.get("is_hidden"):
        return None

    language = str(raw.get("language") or "").strip().lower()
    if language not in ELIGIBLE_LANGUAGES:
        return None

    text = str(raw.get("text") or "").strip()
    if len(text) < MIN_REVIEW_CHARS:
        return None

    review_id = str(raw.get("id") or "").strip()
    if not review_id:
        return None

    paragraphs = reflow_paragraphs(text)
    full_text = "\n\n".join(paragraphs)
    origin = str(raw.get("source") or "").strip() or None
    published_on = str(raw.get("published_on") or "").strip()
    license_name, license_url = _extract_license(raw)

    item = {
        "id": review_id,
        "source": "CritiqueBrainz",
        "origin": origin,
        "full_text": full_text,
        "paragraphs": paragraphs,
        "quote": _extract_quote(full_text),
        "url": f"{CRITIQUEBRAINZ_WEB_REVIEW_BASE}{review_id}",
        "language": language,
        "author": _extract_author(raw),
        "rating": _safe_rating(raw.get("rating")),
        "license": license_name,
        "license_url": license_url,
        "published_on": published_on,
    }
    sort_key = (
        _popularity_score(raw),
        1 if origin == "BBC" else 0,
        published_on,
    )
    return sort_key, item


def fetch_critiquebrainz_reviews(
    mbid: str,
    *,
    get: Callable[..., Any],
    max_pages: int = MAX_PAGES,
    page_limit: int = PAGE_LIMIT,
    timeout: float = REVIEW_PAGE_TIMEOUT,
) -> list[dict[str, Any]]:
    """Fetch, filter, reflow, and sort CritiqueBrainz reviews for a release-group MBID."""
    clean_mbid = str(mbid or "").strip()
    if not clean_mbid:
        return []

    raw_reviews: list[dict[str, Any]] = []
    offset = 0
    for _ in range(max(1, max_pages)):
        params = {
            "entity_id": clean_mbid,
            "entity_type": "release_group",
            "sort": "popularity",
            "limit": page_limit,
            "offset": offset,
        }
        response = get(
            CRITIQUEBRAINZ_REVIEW_URL,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
        )
        payload = response.json() if hasattr(response, "json") else response
        if not isinstance(payload, dict):
            break

        batch = payload.get("reviews")
        if not isinstance(batch, list) or not batch:
            break
        raw_reviews.extend(item for item in batch if isinstance(item, dict))

        total_count = payload.get("count")
        if not isinstance(total_count, int) or offset + page_limit >= total_count:
            break
        offset += page_limit

    normalized: list[tuple[tuple[float, int, str], dict[str, Any]]] = []
    for raw in raw_reviews:
        entry = _normalize_review(raw)
        if entry is not None:
            normalized.append(entry)

    normalized.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in normalized]
