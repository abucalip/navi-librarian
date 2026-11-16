"""Bridge from the lens lists to the stored Artist Deep Dives list.

Pure: the caller supplies the built lens list and the stored Deep Dives payload; no I/O, no clock,
no provider call. The genres a lens list represents (the genre families of its albums' tags and of
its seed tags) pick extra albums out of Deep Dives, so the list grows from lookups already made.

The per-artist cap of the Deep Dives list does not apply here: the extras come from the Deep Dives
items plus ``extra_items``, the ranked candidates its diversity pass held back (stored beside
``items``), so one artist may supply several albums. Each extra is labelled "Discover more <artist>"
and marked ``source: "deep_dive"``; it carries its lens so a save or dismissal counts to that lens.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from discovery.recommendations import deep_dive_genre_families

SOURCE = "deep_dive"
# Extras per genre family, and extras in all, for one lens list (the owner-approved starting values).
PER_FAMILY = 2
TOTAL = 10


def _family(value: Any) -> str:
    return str(value or "").strip().replace("_", "-").casefold()


def _tag_keys(tags: Iterable[Any]) -> set[str]:
    return {" ".join(str(tag).split()).casefold() for tag in tags if str(tag or "").strip()}


def lens_families(albums: Iterable[Mapping[str, Any]], seed_tags: Iterable[Any] = ()) -> list[str]:
    """Genre families the lens list represents, most common first (ties in first-seen order)."""
    counts: Counter[str] = Counter()
    for tags in [[tag] for tag in seed_tags] + [
            album.get("tags") for album in albums if isinstance(album, Mapping)]:
        if not isinstance(tags, (list, tuple)):
            continue
        for family in dict.fromkeys(_family(f) for f in deep_dive_genre_families(tags)):
            if family:
                counts[family] += 1
    return [family for family, _count in counts.most_common()]


def _item_families(item: Mapping[str, Any]) -> list[str]:
    stored = item.get("genre_families")
    families = [_family(f) for f in stored] if isinstance(stored, list) else []
    if not any(families):
        genres = item.get("genres")
        families = [_family(f) for f in deep_dive_genre_families(genres if isinstance(genres, list) else [])]
    return [family for family in families if family]


def deep_dive_pool(payload: Mapping[str, Any] | None) -> list[Mapping[str, Any]]:
    """The stored Deep Dives albums: the shown ``items`` first, then the held-back ``extra_items``
    (absent from lists stored before the bridge, which then bridge from ``items`` alone)."""
    if not isinstance(payload, Mapping):
        return []
    pool: list[Mapping[str, Any]] = []
    for key in ("items", "extra_items"):
        value = payload.get(key)
        if isinstance(value, list):
            pool.extend(item for item in value if isinstance(item, Mapping))
    return pool


def _as_lens_album(item: Mapping[str, Any], lens: str) -> dict[str, Any]:
    artist = str(item.get("artist") or "").strip()
    genres = [str(g) for g in item.get("genres") or [] if g] if isinstance(item.get("genres"), list) else []
    return {
        **item,
        "lens": lens,
        "artist": artist,
        "primary_artist": artist,
        "album": str(item.get("album") or "").strip(),
        "artist_mbid": None,
        "release_group_mbid": None,
        "seed": None,
        "seed_tag": None,
        "tags": genres,
        "source": SOURCE,
        "bridge_label": f"Discover more {artist}",
        # The reason line the clients already show; the Deep Dives wording is kept beside it.
        "reason": f"Discover more {artist}",
        "deep_dive_reason": item.get("reason"),
    }


def bridge_albums(
    lens: str,
    lens_albums: Iterable[Mapping[str, Any]],
    seed_tags: Iterable[Any],
    deep_dive_payload: Mapping[str, Any] | None,
    music_key: Callable[[Any], str],
    *,
    is_excluded: Callable[[Mapping[str, Any]], bool] | None = None,
    per_family: int = PER_FAMILY,
    total: int = TOTAL,
) -> list[dict[str, Any]]:
    """Extra albums for one lens list, in lens-list shape, without a rank.

    Each represented family (most common first) takes up to ``per_family`` Deep Dives albums,
    those sharing the most tags with the lens list first, then the Deep Dives order; ``total`` caps the
    whole set. An album already in the lens list, repeated, or matched by ``is_excluded`` (owned,
    dismissed or blocked-genre) is skipped. Same input, same output."""
    albums = [a for a in lens_albums if isinstance(a, Mapping)]
    families = lens_families(albums, seed_tags)
    if not families:
        return []
    lens_tags = _tag_keys(tag for album in albums if isinstance(album.get("tags"), list) for tag in album["tags"])
    lens_tags |= _tag_keys(seed_tags)
    seen = {(music_key(a.get("artist") or ""), music_key(a.get("album") or "")) for a in albums}
    candidates: list[tuple[Mapping[str, Any], list[str]]] = []
    for item in deep_dive_pool(deep_dive_payload):
        key = (music_key(item.get("artist") or ""), music_key(item.get("album") or ""))
        if not key[0] or not key[1] or key in seen or (is_excluded is not None and is_excluded(item)):
            continue
        seen.add(key)
        candidates.append((item, _item_families(item)))
    chosen: list[Mapping[str, Any]] = []
    for family in families:
        matching = [item for item, item_families in candidates
                    if family in item_families and not any(item is done for done in chosen)]
        matching.sort(key=lambda item: -len(_tag_keys(item.get("genres") or []) & lens_tags))
        chosen.extend(matching[:max(0, min(per_family, total - len(chosen)))])
    return [_as_lens_album(item, lens) for item in chosen]
