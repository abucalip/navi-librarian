"""Artist page sections for the owned-only build (contract sections 3.3 and 3.8)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from discovery.search.events import (
    NOT_IN_BUILD,
    availability,
    owned_index_capability,
    owned_type_available,
    source_capabilities,
)
from discovery.search.artist_sections import ArtistNetwork, network_sections
from discovery.search.index import IndexView
from discovery.search.query import find_artist, owned_albums

SECTION_ORDER = ("artist", "owned_albums", "bio", "missing_albums", "similar")
_NETWORK_SECTIONS = ("bio", "missing_albums", "similar")


@dataclass
class ArtistPage:
    """Result of one artist lookup. ``status`` is ``ok``, ``unknown`` or ``ambiguous``."""

    status: str
    capabilities: dict[str, Any] = field(default_factory=dict)
    sections: dict[str, dict[str, Any]] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    partial: bool = False


def artist_capabilities(view: IndexView, network: ArtistNetwork | None = None) -> dict[str, Any]:
    owned_ok = owned_type_available(view)
    sections = {
        "artist": availability(owned_ok, view.reason),
        "owned_albums": availability(owned_ok, view.reason),
    }
    for name in _NETWORK_SECTIONS:
        if network is None:
            sections[name] = availability(False, NOT_IN_BUILD)
        elif name == "similar":
            sections[name] = availability(False, NOT_IN_BUILD)
        else:
            sections[name] = availability(True)
    return {
        "sections": sections,
        "sources": dict(network.sources) if network is not None else source_capabilities(),
        "owned_index": owned_index_capability(view),
    }


def _unavailable(name: str, reason: str | None) -> dict[str, Any]:
    section: dict[str, Any] = {
        "section": name,
        "available": False,
        "complete": False,
        "reason": reason,
    }
    if name == "artist":
        section["artist"] = None
    elif name == "owned_albums":
        section["items"] = []
    elif name == "bio":
        section["bio"] = None
    else:
        section["items"] = []
    return section


def artist_page(
    view: IndexView,
    key: str,
    artist_id: str | None,
    network: ArtistNetwork | None = None,
) -> ArtistPage:
    """Build every section for one artist key, or report why the key cannot be served."""
    capabilities = artist_capabilities(view, network)
    if not owned_type_available(view):
        # Owned sections cannot be served yet. The response is still 200, never 404.
        sections = {
            "artist": _unavailable("artist", view.reason),
            "owned_albums": _unavailable("owned_albums", view.reason),
        }
        for name in _NETWORK_SECTIONS:
            if network is not None:
                sections[name] = _unavailable(name, view.reason)
        return _finish(ArtistPage("ok", capabilities, sections), view)

    status, artist, candidates = find_artist(view.data, key, artist_id)
    if status != "ok":
        return ArtistPage(status, capabilities, candidates=candidates)

    sections = {
        "artist": {
            "section": "artist",
            "available": True,
            "complete": True,
            "reason": None,
            "artist": {
                "id": artist["id"],
                "name": artist["name"],
                "mbid": None,
                "owned": True,
                "album_count": artist["album_count"],
            },
        },
        "owned_albums": {
            "section": "owned_albums",
            "available": True,
            "complete": True,
            "reason": None,
            "items": owned_albums(view.data, artist["id"]),
        },
    }
    if network is not None:
        sections.update(network_sections(network, artist["name"], artist["id"], view.data))
    return _finish(ArtistPage("ok", capabilities, sections), view)


def _finish(page: ArtistPage, view: IndexView) -> ArtistPage:
    """Fill the not-in-this-build sections and compute ``partial``."""
    for name in SECTION_ORDER:
        if name not in page.sections:
            page.sections[name] = _unavailable(name, NOT_IN_BUILD)
    ordered = {name: page.sections[name] for name in SECTION_ORDER}
    page.sections = ordered
    # Contract section 3.8: a section that ended early or failed makes the page partial.
    page.partial = not owned_type_available(view) or any(
        section["reason"] in ("deadline", "source_failed") for section in ordered.values()
    )
    return page


def section_events(page: ArtistPage) -> list[dict[str, Any]]:
    """Section payloads in contract order, for the stream form."""
    return [page.sections[name] for name in SECTION_ORDER]


def json_sections(page: ArtistPage) -> dict[str, dict[str, Any]]:
    """Section objects without the ``section`` key, as the JSON form requires (section 3.3)."""
    return {
        name: {k: v for k, v in section.items() if k != "section"}
        for name, section in page.sections.items()
    }
