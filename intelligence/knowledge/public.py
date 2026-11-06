"""Public shape of the knowledge pages (owner decision, 2026-11-06).

Pages are built with store ids internally (they key the walks). Before a body leaves the reader it
passes through :func:`public`, which drops every internal or secondary identifier so a client sees
``mbid`` only, and turns every ``owned`` flag into a real boolean.
"""
from __future__ import annotations

from typing import Any

INTERNAL_KEYS = frozenset({"id", "created_generation", "navidrome_id", "discogs_id", "wikidata_id"})


def public(value: Any) -> Any:
    """A copy of a page body without internal ids, with every ``owned`` as a boolean."""
    if isinstance(value, dict):
        return {k: (bool(v) if k == "owned" else public(v)) for k, v in value.items() if k not in INTERNAL_KEYS}
    if isinstance(value, list):
        return [public(v) for v in value]
    return value
