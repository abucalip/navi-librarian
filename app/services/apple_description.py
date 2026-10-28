"""Read Apple Music's editorial album notes out of an album page's embedded data.

Apple's catalogue API needs a developer token, so the notes are taken from the public album page,
which ships them in its ``serialized-server-data`` script for the albums that have any. Many albums
have none. Nothing here fetches; the caller passes the page text.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

_DATA_SCRIPT = re.compile(r'<script type="application/json" id="serialized-server-data">(.*?)</script>', re.S)
_BREAK = re.compile(r"<br\s*/?>", re.I)
_TAG = re.compile(r"<[^>]+>")


def _find_notes(node: Any, depth: int = 0) -> str | None:
    """The first ``paragraphText`` inside a ``modalPresentationDescriptor`` (where the notes sit)."""
    if depth > 12:
        return None
    if isinstance(node, dict):
        descriptor = node.get("modalPresentationDescriptor")
        if isinstance(descriptor, dict) and isinstance(descriptor.get("paragraphText"), str):
            return descriptor["paragraphText"]
        for value in node.values():
            found = _find_notes(value, depth + 1)
            if found:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _find_notes(value, depth + 1)
            if found:
                return found
    return None


_LEADING_LABEL = re.compile(r"^\s*<b>.*?</b>\s*", re.S | re.I)


def paragraphs_from_markup(markup: str) -> list[str]:
    """Plain-text paragraphs from the notes' light markup (``<br />`` breaks, ``<i>`` emphasis).

    A bold label at the very start ("100 Best Albums") is a badge, not part of the text, and is dropped.
    """
    parts = _BREAK.split(_LEADING_LABEL.sub("", markup, count=1))
    cleaned = (re.sub(r"\s+", " ", html.unescape(_TAG.sub("", part))).strip() for part in parts)
    return [part for part in cleaned if part]


def parse_editorial_notes(page: str) -> list[str] | None:
    """The album's editorial notes as paragraphs, or None when the page carries none."""
    match = _DATA_SCRIPT.search(page or "")
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except ValueError:
        return None
    markup = _find_notes(data)
    paragraphs = paragraphs_from_markup(markup) if markup else []
    return paragraphs or None
