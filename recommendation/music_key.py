"""Stdlib-only identity key shared by discovery, feedback and provider clients."""
from __future__ import annotations

import unicodedata
from typing import Any


def music_key(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return "".join(c.casefold() for c in value if c.isalnum())
