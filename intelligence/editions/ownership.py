"""Edition awareness for "do I own this?" (docs/ServerV2.md Phase 2, item 5).

The ownership matcher (``OwnedKeys`` and ``_owned_match``) decides *owned or not* from the album
name key and year, and it is left exactly as it was. This module adds a second, separate answer
for an album the matcher calls unowned: does the library hold *another edition* of it?

- ``same_edition``: the matcher's own rule holds (same album name key, compatible year).
- ``other_edition``: the library holds an album with the same title once edition words in
  brackets are set aside ("Rumours" owned, "Rumours (Deluxe Edition)" asked about), and at
  least one of the two names carries such a word.
- ``not_owned``: nothing owned fits.

Edition information is display-only. It never changes an ``owned`` flag, so it cannot merge two
different albums. "Live" is not an edition of the studio album and never produces
``other_edition``. Behind the ``NAVI_EDITION_AWARE_OWNERSHIP`` flag, off by default.
"""
from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from discovery.search.normalize import album_match_key
from ..resolution.normalize import edition_markers

FLAG_ENV = "NAVI_EDITION_AWARE_OWNERSHIP"
SAME_EDITION = "same_edition"
OTHER_EDITION = "other_edition"
NOT_OWNED = "not_owned"

_TRUE = {"1", "true", "yes", "on"}
_BRACKETED = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")


@dataclass(frozen=True)
class EditionMatch:
    status: str
    owned_id: str | None = None
    owned_name: str | None = None
    owned_markers: tuple[str, ...] = ()
    candidate_markers: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "owned_id": self.owned_id,
            "owned_name": self.owned_name,
            "owned_editions": list(self.owned_markers),
            "editions": list(self.candidate_markers),
        }


def edition_awareness_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """True when the owner switched the flag on. Unset, empty or anything else is off."""
    env = os.environ if environ is None else environ
    return str(env.get(FLAG_ENV, "")).strip().casefold() in _TRUE


def base_key(name: object) -> str:
    """Album key with bracketed edition groups removed; other brackets stay in the key."""
    text = str(name or "")

    def strip(match: re.Match[str]) -> str:
        return "" if edition_markers(match.group(0)) else match.group(0)

    return album_match_key(_BRACKETED.sub(strip, text))


def _years_compatible(first: Any, second: Any) -> bool:
    return first is None or second is None or first == second


def edition_match(candidate: Mapping[str, Any], owned_albums: Iterable[Mapping[str, Any]]) -> EditionMatch:
    """Which edition of ``candidate`` (``name``, ``year``) the library holds, if any.

    Owned entries are ``owned_albums`` items (``name``, ``year``, ``id``). A candidate that
    matches several owned editions reports the first by id, so the answer is stable.
    """
    name = candidate.get("name")
    full = album_match_key(name)
    base = base_key(name)
    markers = tuple(edition_markers(str(name or "")))
    entries = sorted(owned_albums, key=lambda e: str(e.get("id") or ""))
    for entry in entries:
        if album_match_key(entry.get("name")) == full and _years_compatible(candidate.get("year"), entry.get("year")):
            return EditionMatch(SAME_EDITION, entry.get("id"), entry.get("name"),
                                tuple(edition_markers(str(entry.get("name") or ""))), markers)
    if not base or "live" in markers:
        return EditionMatch(NOT_OWNED, candidate_markers=markers)
    for entry in entries:
        owned_markers = tuple(edition_markers(str(entry.get("name") or "")))
        if (
            base_key(entry.get("name")) == base
            and "live" not in owned_markers
            and (markers or owned_markers)
        ):
            return EditionMatch(OTHER_EDITION, entry.get("id"), entry.get("name"), owned_markers, markers)
    return EditionMatch(NOT_OWNED, candidate_markers=markers)
