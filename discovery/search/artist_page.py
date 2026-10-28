"""Artist page sections for the owned-only build (contract sections 3.3 and 3.8)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from discovery.search.events import (
    NOT_IN_BUILD,
    availability,
    owned_index_capability,
    owned_type_available,
    source_capabilities,
)
from discovery.search.artist_sections import ArtistNetwork, iter_network_sections, network_sections
from discovery.search.index import IndexView
from discovery.search.query import find_artist, owned_albums

SECTION_ORDER = ("artist", "owned_albums", "bio", "tags", "albums", "missing_albums", "similar")
_NETWORK_SECTIONS = ("bio", "tags", "albums", "missing_albums", "similar")


@dataclass
class ArtistPage:
    """Result of one artist lookup. ``status`` is ``ok``, ``unknown`` or ``ambiguous``."""

    status: str
    capabilities: dict[str, Any] = field(default_factory=dict)
    sections: dict[str, dict[str, Any]] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    partial: bool = False
    # Network sections not yet run (``defer_network``); a generator that yields each as it finishes.
    deferred: Iterator[dict[str, Any]] | None = None


def artist_capabilities(view: IndexView, network: ArtistNetwork | None = None) -> dict[str, Any]:
    owned_ok = owned_type_available(view)
    sections = {
        "artist": availability(owned_ok, view.reason),
        "owned_albums": availability(owned_ok, view.reason),
    }
    for name in _NETWORK_SECTIONS:
        if network is None:
            sections[name] = availability(False, NOT_IN_BUILD)
        elif name == "similar" and network.lastfm is None and network.listenbrainz is None:
            sections[name] = availability(False, "source_disabled")
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
    *,
    name: str | None = None,
    mbid: str | None = None,
    defer_network: bool = False,
) -> ArtistPage:
    """Build every section for one artist key, or report why the key cannot be served.

    An artist the library does not have is served from the network sections alone when the caller
    names it (``name``, with ``mbid`` when known): that is the page of an unowned search result.
    """
    capabilities = artist_capabilities(view, network)
    sections_for = iter_network_sections if defer_network else network_sections
    if not owned_type_available(view) and name and not artist_id and network is not None:
        # No ownership can be checked yet, so the named artist is served from the network alone.
        return _build(ArtistPage("ok", capabilities, {}), view, _unowned_sections(view, network, name, mbid, sections_for))
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
    if status == "unknown" and name and not artist_id and network is not None:
        return _build(ArtistPage("ok", capabilities, {}), view, _unowned_sections(view, network, name, mbid, sections_for))
    if status != "ok":
        return ArtistPage(status, capabilities, candidates=candidates)
    albums = owned_albums(view.data, artist["id"])

    sections = {
        "artist": {
            "section": "artist",
            "available": True,
            "complete": True,
            "reason": None,
            "artist": {
                "id": artist["id"],
                "name": artist["name"],
                "mbid": artist.get("mbid"),
                "owned": True,
                "album_count": artist["album_count"],
                "genre": artist.get("genre"),
            },
        },
        "owned_albums": {
            "section": "owned_albums",
            "available": True,
            "complete": True,
            "reason": None,
            "items": albums,
        },
    }
    page = ArtistPage("ok", capabilities, sections)
    if network is not None:
        network_part = sections_for(
            network, artist["name"], artist["id"], view.data, known_mbid=artist.get("mbid"),
            owned_album_items=albums, library_genre=artist.get("genre"),
        )
        return _attach(page, view, network_part)
    return _finish(page, view)


def _attach(page: ArtistPage, view: IndexView, network_part: Any) -> ArtistPage:
    """Add the network sections now, or keep the generator for the stream to drain."""
    if isinstance(network_part, dict):
        page.sections.update(network_part)
        return _finish(page, view)
    page.deferred = network_part
    return page


def _build(page: ArtistPage, view: IndexView, parts: tuple[dict[str, dict[str, Any]], Any]) -> ArtistPage:
    owned_part, network_part = parts
    page.sections.update(owned_part)
    return _attach(page, view, network_part)


def drain_deferred(page: ArtistPage, view: IndexView) -> Iterator[dict[str, Any]]:
    """Yield the deferred network sections as they finish, then complete the page (``partial``)."""
    for section in page.deferred or ():
        page.sections[section["section"]] = section
        yield section
    page.deferred = None
    _finish(page, view)


def _unowned_sections(
    view: IndexView, network: ArtistNetwork, name: str, mbid: str | None, sections_for: Any,
) -> tuple[dict[str, dict[str, Any]], Any]:
    sections = {
        "artist": {
            "section": "artist", "available": True, "complete": True, "reason": None,
            "artist": {"id": None, "name": name, "mbid": mbid or None, "owned": False,
                       "album_count": 0, "genre": None},
        },
        "owned_albums": {
            "section": "owned_albums", "available": True, "complete": True, "reason": None, "items": [],
        },
    }
    return sections, sections_for(network, name, None, view.data, known_mbid=mbid or None)


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
