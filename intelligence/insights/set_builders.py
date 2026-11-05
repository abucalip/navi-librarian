"""Comparison-set builders for blind spots (Phase 3 item 2, input side).

Pure parsers: each takes a provider document the caller already fetched and returns a
``ComparisonSet`` for ``blind_spots.find_blind_spots``. Nothing here makes a network call,
touches the store, or decides what to fetch, so it adds no provider traffic and cannot change
an ownership flag or a recommendation weight.

Rules:

* a studio discography is the artist's release groups with primary type ``Album`` and no
  secondary type (no live, compilation, soundtrack, remix, demo and so on); a missing or
  empty type list is treated as "unknown" and left out rather than guessed to be a studio album;
* a ListenBrainz top list keeps the provider's order and only entries that carry a release-group MBID;
* a series keeps the series' own ordering (``ordering-key``, then the ``number`` attribute, then
  document order) and only release-group relations;
* a malformed document yields ``None``; a bad entry inside a document is skipped, never raised on;
* members repeated by MBID are dropped here once, so the set size is the number of distinct groups.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

from .blind_spots import ComparisonSet, SetItem

_MBID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _mbid(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text if _MBID.match(text) else None


def _text(value: Any) -> str:
    return str(value).strip() if isinstance(value, (str, int)) and str(value).strip() else ""


def _year(value: Any) -> int | None:
    match = re.match(r"^(\d{4})", str(value or ""))
    return int(match.group(1)) if match else None


def _dedupe(items: list[SetItem]) -> tuple[SetItem, ...]:
    seen: set[str] = set()
    out: list[SetItem] = []
    for item in items:
        if item.group_mbid in seen:
            continue
        seen.add(item.group_mbid or "")
        out.append(item)
    return tuple(out)


def studio_discography_set(
    artist_mbid: str, artist_name: str, document: Mapping[str, Any] | None,
) -> ComparisonSet | None:
    """Release-group browse result (``/release-group?artist=<mbid>``) -> studio albums, oldest first."""
    artist = _mbid(artist_mbid)
    if artist is None or not isinstance(document, Mapping):
        return None
    groups = document.get("release-groups")
    if not isinstance(groups, list):
        return None
    items: list[SetItem] = []
    for g in groups:
        if not isinstance(g, Mapping):
            continue
        group = _mbid(g.get("id"))
        secondary = g.get("secondary-types")
        if group is None or g.get("primary-type") != "Album" or not isinstance(secondary, list) or secondary:
            continue
        items.append(SetItem(group, _text(g.get("title")), _year(g.get("first-release-date"))))
    items.sort(key=lambda i: (i.year is None, i.year or 0, i.title.lower(), i.group_mbid or ""))
    name = _text(artist_name) or "this artist"
    return ComparisonSet(
        key=f"artist:{artist}:studio", kind="studio_discography",
        label=f"{name} studio albums", items=_dedupe(items), artist=_text(artist_name) or None,
        source="musicbrainz",
    )


def listenbrainz_top_set(
    artist_mbid: str, artist_name: str, document: Mapping[str, Any] | None,
) -> ComparisonSet | None:
    """ListenBrainz top release groups for an artist (``payload.release_groups``), in provider order."""
    artist = _mbid(artist_mbid)
    if artist is None or not isinstance(document, Mapping):
        return None
    payload = document.get("payload")
    groups = payload.get("release_groups") if isinstance(payload, Mapping) else None
    if not isinstance(groups, list):
        return None
    items: list[SetItem] = []
    for g in groups:
        if not isinstance(g, Mapping):
            continue
        group = _mbid(g.get("release_group_mbid"))
        if group is None:
            continue
        items.append(SetItem(group, _text(g.get("release_group_name")), None))
    name = _text(artist_name) or "this artist"
    return ComparisonSet(
        key=f"artist:{artist}:lb_top", kind="listenbrainz_top",
        label=f"{name} most listened albums on ListenBrainz", items=_dedupe(items),
        artist=_text(artist_name) or None, source="listenbrainz",
    )


def series_set(document: Mapping[str, Any] | None) -> ComparisonSet | None:
    """MusicBrainz series lookup with ``inc=release-group-rels`` -> members in the series' order."""
    if not isinstance(document, Mapping):
        return None
    series = _mbid(document.get("id"))
    relations = document.get("relations")
    if series is None or not isinstance(relations, list):
        return None
    ranked: list[tuple[tuple[int, float, int], SetItem]] = []
    for position, rel in enumerate(relations):
        if not isinstance(rel, Mapping) or rel.get("target-type") != "release_group":
            continue
        group = rel.get("release_group")
        if not isinstance(group, Mapping):
            continue
        mbid = _mbid(group.get("id"))
        if mbid is None:
            continue
        order = _order(rel)
        ranked.append(((0 if order is not None else 1, order if order is not None else 0.0, position),
                       SetItem(mbid, _text(group.get("title")), _year(group.get("first-release-date")))))
    ranked.sort(key=lambda r: r[0])
    name = _text(document.get("name")) or "this series"
    return ComparisonSet(
        key=f"series:{series}", kind="series", label=name,
        items=_dedupe([item for _, item in ranked]), source="musicbrainz",
    )


def _order(rel: Mapping[str, Any]) -> float | None:
    for raw in (rel.get("ordering-key"), (rel.get("attribute-values") or {}).get("number")
                if isinstance(rel.get("attribute-values"), Mapping) else None):
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None
