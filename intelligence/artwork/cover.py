"""Which cover an owned album shows (docs/artwork.md, slice 4: edition picker and grid fallback).

* The owner's pick (``album_choice``) always wins, on every screen that loads the album's cover.
* With no pick, the library cover is used. It is replaced by the group's best front only when the library
  has no cover or the cover is small (its longer side under ``SMALL_COVER_PX``) and the best front is larger.
* A pick must be a Front image of the album's own release group. Nothing here reads taste or play data and
  nothing contacts a provider from a client request: an unbuilt group is queued for the background build.
"""
from __future__ import annotations

import struct

from .service import NOT_LOADED, ArtworkService

SMALL_COVER_PX = 300


def long_side(body: bytes) -> int | None:
    """Longer side in pixels of a JPEG or PNG from its header; ``None`` for anything else or a bad header."""
    try:
        if body[:8] == b"\x89PNG\r\n\x1a\n" and body[12:16] == b"IHDR":
            width, height = struct.unpack(">II", body[16:24])
            return max(width, height)
        if body[:2] == b"\xff\xd8":
            i = 2
            while i + 9 < len(body):
                if body[i] != 0xFF:
                    i += 1
                    continue
                marker = body[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7 or marker == 0xFF:
                    i += 1 if marker == 0xFF else 2
                    continue
                length = struct.unpack(">H", body[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    height, width = struct.unpack(">HH", body[i + 5:i + 9])
                    return max(width, height)
                i += 2 + length
    except struct.error:
        return None
    return None


def front_images(view: dict) -> list[dict]:
    """The picker's candidates from an index body: images typed Front (any format but PDF), best first."""
    return [i for i in view.get("images", []) if "Front" in (i.get("types") or []) and i.get("format") != "pdf"]


def choose(service: ArtworkService, album_id: str, rgid: str, image_id: int) -> str:
    """Store the owner's pick. ``ok``, ``not_loaded`` (the index is not built yet) or ``not_a_front``."""
    view = service.index(rgid)
    if view["status"] == NOT_LOADED:
        return NOT_LOADED
    if image_id not in {i["image_id"] for i in front_images(view)}:
        return "not_a_front"
    service.store.set_choice(album_id, rgid, image_id)
    return "ok"


def larger_front(service: ArtworkService, rgid: str, owned_release: str | None, have_px: int | None) -> int | None:
    """``best_front`` image id when it is larger than ``have_px`` (``None`` means no library cover)."""
    view = service.index(rgid, owned_release)
    best = view.get("best_front")
    if best is None:
        return None
    entry = next((i for i in view["images"] if i["image_id"] == best), None)
    side = max(entry.get("width") or 0, entry.get("height") or 0) if entry else 0
    if have_px is None or side > have_px:
        return best
    return None
