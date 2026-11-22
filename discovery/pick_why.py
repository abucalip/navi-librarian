"""Pure pick-reason builder for the Listening Room web client (D1 = server).

Turns one discovery album's server fields into ``why``:
``{"kind": ..., "sentence": ..., "chips": [{"type", "label", "value", "href_kind"}]}``.
Follows ``docs/plans/LISTENING_ROOM_WEB.md`` section 6 precedence and wording.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from discovery.taste_families import family_label

LENS_SENTENCES: dict[str, str] = {
    "deep_cuts": "A lesser-known record from the {tag} you play",
    "current_tastes": "Close to the {tag} you play lately",
    "genre_spread": "Through the {tag} you play",
    "repeated_tracks": "From the {tag} you keep repeating",
    "obsessions": "From your {tag} obsession",
}

LENS_LABELS: dict[str, str] = {
    "deep_cuts": "Deep cuts",
    "current_tastes": "Current tastes",
    "genre_spread": "Genre spread",
    "repeated_tracks": "Repeated tracks",
    "obsessions": "Obsessions",
}


def _chip(chip_type: str, label: str, value: Any, href_kind: str | None = None) -> dict[str, Any]:
    return {
        "type": chip_type,
        "label": label,
        "value": value,
        "href_kind": href_kind,
    }


def _join_names(names: list[str]) -> str:
    """List names with ', ' and 'and' before the last; past 2 names, 'and {n} more'."""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{names[0]}, {names[1]} and {len(names) - 2} more"


def _short_number(count: int) -> str:
    """Format listener counts concisely ('41k', '9.6k', '1.2M')."""
    if count >= 1_000_000:
        text = f"{count / 1_000_000:.1f}"
        return f"{text[:-2] if text.endswith('.0') else text}M"
    if count >= 10_000:
        return f"{round(count / 1_000)}k"
    if count >= 1_000:
        text = f"{count / 1_000:.1f}"
        return f"{text[:-2] if text.endswith('.0') else text}k"
    return str(count)


def _album_count_phrase(count: int) -> str:
    return "1 album" if count == 1 else f"{count} albums"


def _clean_names(raw: Any) -> list[str]:
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(entry).strip() for entry in raw if str(entry or "").strip()]


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _listeners_chip(item: Mapping[str, Any]) -> dict[str, Any] | None:
    listeners = _positive_int(item.get("album_listeners"))
    if listeners is None:
        listeners = _positive_int(item.get("listeners"))
    if listeners is None:
        return None
    return _chip("listeners", f"{_short_number(listeners)} listeners", listeners)


def _similar_artists_chips(names: list[str]) -> list[dict[str, Any]]:
    chips = [_chip("artist", name, name, "artist") for name in names[:2]]
    if len(names) > 2:
        chips.append(_chip("more", f"+{len(names) - 2}", len(names) - 2))
    return chips


def _lens_why(item: Mapping[str, Any], list_name: str | None) -> dict[str, Any] | None:
    lens = str(item.get("lens") or "").strip()
    if not lens and list_name in LENS_LABELS:
        lens = list_name
    seed_tag = str(item.get("seed_tag") or "").strip()
    if lens in LENS_SENTENCES and seed_tag:
        chips: list[dict[str, Any]] = [_chip("tag", seed_tag, seed_tag, "genre")]
        listeners = _listeners_chip(item)
        if listeners is not None:
            chips.append(listeners)
        seed_key = seed_tag.casefold()
        extra_tags: list[str] = []
        for tag in _clean_names(item.get("tags")):
            if tag.casefold() == seed_key or tag.casefold() in {t.casefold() for t in extra_tags}:
                continue
            extra_tags.append(tag)
            if len(extra_tags) == 2:
                break
        for tag in extra_tags:
            chips.append(_chip("tag", tag, tag, "genre"))
        return {
            "kind": "lens",
            "sentence": LENS_SENTENCES[lens].format(tag=seed_tag),
            "chips": chips,
        }
    if item.get("dashboard_category") and str(item.get("reason") or "").strip():
        listeners = _listeners_chip(item)
        return {
            "kind": "lens",
            "sentence": str(item["reason"]).strip(),
            "chips": [listeners] if listeners is not None else [],
        }
    if lens in LENS_LABELS:
        listeners = _listeners_chip(item)
        return {
            "kind": "lens",
            "sentence": f"From your {LENS_LABELS[lens]} lens",
            "chips": [listeners] if listeners is not None else [],
        }
    return None


def _deep_dive_why(item: Mapping[str, Any], list_name: str | None) -> dict[str, Any] | None:
    kind = str(item.get("deep_dive_kind") or "").strip()
    dtype = str(item.get("discovery_type") or "").strip()
    is_deep_dive = (
        list_name == "artist_deep_dive"
        or kind in {"missing_album", "similar_artist"}
        or dtype in {"artist_deep_dive", "similar_artist"}
    )
    if not is_deep_dive:
        return None
    anchor = str(item.get("anchor_artist") or "").strip()
    artist = str(item.get("artist") or "").strip()
    if kind == "similar_artist" or (not kind and dtype == "similar_artist"):
        if not anchor:
            return None
        return {
            "kind": "deep_dive_similar",
            "sentence": f"Close to {anchor}, who is well covered in your library. Nothing by this artist yet.",
            "chips": [_chip("artist", f"Close to {anchor}", anchor, "artist")],
        }
    is_missing = kind == "missing_album" or (not kind and dtype == "artist_deep_dive")
    if not is_missing and anchor and artist and anchor.casefold() != artist.casefold():
        return {
            "kind": "deep_dive_similar",
            "sentence": f"Close to {anchor}, who is well covered in your library. Nothing by this artist yet.",
            "chips": [_chip("artist", f"Close to {anchor}", anchor, "artist")],
        }
    target_artist = artist or anchor
    count = _positive_int(item.get("anchor_album_count"))
    if not target_artist or count is None:
        return None
    return {
        "kind": "deep_dive_missing",
        "sentence": f"You have {_album_count_phrase(count)} by {target_artist}. This one is not in your library yet.",
        "chips": [_chip("library_count", f"{count} in your library", count)],
    }


def _discover_why(item: Mapping[str, Any]) -> dict[str, Any] | None:
    category = str(item.get("discovery_category") or "").strip()
    if not category:
        return None
    if category == "adjacent":
        sentence = "Close to genres you already love"
    elif category == "cross_genre":
        raw_families = _clean_names(item.get("genre_families")) or _clean_names(
            item.get("recent_profile_families")
        )
        labels: list[str] = []
        for fam in raw_families:
            label = family_label(fam.replace("_", "-").casefold()).casefold()
            if label not in labels:
                labels.append(label)
            if len(labels) == 2:
                break
        if len(labels) >= 2:
            sentence = f"A bridge between {labels[0]} and {labels[1]}, both in your listening"
        else:
            sentence = "A bridge between genres in your listening"
    elif category == "adventurous":
        sentence = "A step away from your usual genres"
    elif category == "unclassified":
        sentence = "Few genre tags, so the fit is a guess"
    else:
        return None
    chips: list[dict[str, Any]] = []
    anchor = str(item.get("anchor_artist") or "").strip()
    if anchor:
        chips.append(_chip("artist", f"Similar to {anchor}", anchor, "artist"))
    listeners = _listeners_chip(item)
    if listeners is not None:
        chips.append(listeners)
    return {"kind": "discover", "sentence": sentence, "chips": chips}


def build_pick_why(item: Mapping[str, Any], *, list_name: str | None = None) -> dict[str, Any] | None:
    """Build the ``why`` dict for one discovery album, or None when no field applies."""
    if not isinstance(item, Mapping):
        return None

    bridge_label = str(item.get("bridge_label") or "").strip()
    if bridge_label:
        return {"kind": "bridge", "sentence": bridge_label, "chips": []}

    because = item.get("because")
    if isinstance(because, Mapping):
        bkind = str(because.get("kind") or "").strip()
        names = _clean_names(because.get("names"))
        if bkind == "tag" and names:
            return {
                "kind": "tag",
                "sentence": f"Because you listen to {_join_names(names)}",
                "chips": [_chip("tag", tag, tag, "genre") for tag in names],
            }
        if bkind == "similar_artists" and names:
            return {
                "kind": "similar_artists",
                "sentence": f"Shares genres with {_join_names(names)}",
                "chips": _similar_artists_chips(names),
            }

    similar_to = _clean_names(item.get("similar_to"))
    if similar_to:
        return {
            "kind": "similar_artists",
            "sentence": f"Shares genres with {_join_names(similar_to)}",
            "chips": _similar_artists_chips(similar_to),
        }

    lens_result = _lens_why(item, list_name)
    if lens_result is not None:
        return lens_result

    deep_dive_result = _deep_dive_why(item, list_name)
    if deep_dive_result is not None:
        return deep_dive_result

    if list_name == "new_releases" or item.get("discovery_type") == "new_release":
        year = _positive_int(item.get("year"))
        count = _positive_int(item.get("artist_library_album_count"))
        if year is not None and count is not None:
            return {
                "kind": "new_release",
                "sentence": f"New in {year} from an artist with a full album in your library",
                "chips": [_chip("library_count", f"{_album_count_phrase(count)} in your library", count)],
            }

    if list_name == "classics" or item.get("discovery_type") == "classic":
        count = _positive_int(item.get("artist_library_album_count"))
        if count is not None:
            listeners = _listeners_chip(item)
            return {
                "kind": "collection",
                "sentence": f"A well-known album; you have {_album_count_phrase(count)} by this artist",
                "chips": [listeners] if listeners is not None else [],
            }

    discover_result = _discover_why(item)
    if discover_result is not None:
        return discover_result

    if item.get("owned"):
        return {"kind": "owned", "sentence": "In your library", "chips": []}

    return None


def attach_why(items: list[Any], *, list_name: str | None = None) -> list[Any]:
    """Return a shallow-copied list with ``why`` attached to each dict item where applicable."""
    out: list[Any] = []
    for item in items:
        if isinstance(item, Mapping):
            why = build_pick_why(item, list_name=list_name)
            if why is not None:
                out.append({**item, "why": why})
                continue
        out.append(item)
    return out
