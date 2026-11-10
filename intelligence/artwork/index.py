"""Merge the Cover Art Archive images of every release in a release group into one index.

No network and no store here: the caller passes the two fetchers, so the rules (merge, de-duplication,
best front, per-type slots, caps, ``truncated``) are tested directly and the cache and endpoint slices
wrap this unchanged. Limits are the ones recorded in docs/artwork.md ("Limits (set from the probe)").

Rules:

* Caps limit what is stored and served, never whether the index is fetched: every release up to
  ``RELEASES_CAP`` is indexed, then the merged list is trimmed.
* Releases are fetched owned-first, then newest first (undated last, MBID breaks ties).
* A release index that failed is ``unavailable`` and is never counted as ``empty``. A group with no
  images and any failed release is ``unavailable``; ``empty`` means every release answered "no images".
* The same image on several releases appears once, with every release it is on.
* Selection uses explicit rules only (approved, type, size, date, id). Taste and play data are never
  inputs, and an image is never chosen because it resembles anything.
* Image text (``comment``) is carried as plain text; the clients must never render it as markup.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Mapping

RELEASES_CAP = 60
IMAGES_STORED_CAP = 400
IMAGES_SERVED_CAP = 250
BOOKLET_PAGES_CAP = 100
BUILD_SECONDS = 180.0
SLOT_TYPES = ("Front", "Back", "Spine", "Obi", "Medium", "Tray", "Sticker", "Poster")

OK, EMPTY, UNAVAILABLE = "ok", "empty", "unavailable"
_UNDATED = "9999-99-99"


@dataclass(frozen=True)
class ReleaseInfo:
    mbid: str
    date: str = ""
    country: str = ""
    format: str = ""

    @property
    def label(self) -> str:
        """"1999 Japan CD": whatever of year, country and format MusicBrainz gave; "" when none."""
        return " ".join(p for p in (self.date[:4], self.country, self.format) if p)


@dataclass(frozen=True)
class ReleaseIndex:
    """One release's CAA answer. ``images`` are the CAA image dicts in CAA order."""
    state: str
    images: tuple = ()


@dataclass
class ImageEntry:
    image_id: int
    release: str                      # the preferred release this image is on (owned first, then fetch order)
    releases: list[str]               # every fetched release it is on
    edition: str
    types: list[str]
    comment: str
    approved: bool
    width: int | None
    height: int | None
    date: str                         # release date of `release`, "" when unknown
    positions: dict[str, int] = field(default_factory=dict)   # release -> place in that release's CAA list
    format: str = "jpg"               # file type of the original: jpg, png, gif, webp or pdf

    @property
    def side(self) -> int:
        return max(self.width or 0, self.height or 0)

    def to_dict(self) -> dict:
        return {"image_id": self.image_id, "release": self.release, "releases": list(self.releases),
                "edition": self.edition, "types": list(self.types), "comment": self.comment,
                "approved": self.approved, "width": self.width, "height": self.height,
                "format": self.format}


@dataclass
class GroupIndex:
    rgid: str
    status: str                       # ok | empty | unavailable
    images: list[ImageEntry]
    owned_release: str | None
    releases_total: int
    releases_fetched: int
    releases_empty: int
    releases_failed: int
    truncated: bool
    truncated_reason: str | None      # release_cap | time | partial | stored_cap
    seconds: float
    labels: dict[str, str] = field(default_factory=dict)      # release -> edition label
    dates: dict[str, str] = field(default_factory=dict)       # release -> date


def parse_release(doc: Mapping) -> ReleaseInfo:
    """A release from a MusicBrainz browse/lookup JSON document. Missing parts become ``""``."""
    media = doc.get("media") or []
    formats = []
    for m in media:
        f = (m.get("format") or "").strip()
        if f and f not in formats:
            formats.append(f)
    return ReleaseInfo(
        mbid=str(doc.get("id") or "").lower(),
        date=str(doc.get("date") or ""),
        country=str(doc.get("country") or ""),
        format=" + ".join(formats),
    )


def _release_order(releases: Iterable[ReleaseInfo], owned: str | None) -> list[ReleaseInfo]:
    seen: dict[str, ReleaseInfo] = {}
    for r in releases:
        if r.mbid and r.mbid not in seen:
            seen[r.mbid] = r
    newest = sorted(seen.values(), key=lambda r: r.mbid)
    newest.sort(key=lambda r: r.date or "", reverse=True)
    newest.sort(key=lambda r: not r.date)               # undated last (stable, keeps the order above)
    newest.sort(key=lambda r: r.mbid != owned)          # owned first
    return newest


def _date_key(date: str) -> str:
    return date or _UNDATED


def _quality_key(e: ImageEntry) -> tuple:
    """Best first: approved, larger side, earlier release date, lower image id."""
    return (not e.approved, -e.side, _date_key(e.date), e.image_id)


def _merge(infos: list[ReleaseInfo], results: dict[str, ReleaseIndex]) -> list[ImageEntry]:
    by_id: dict[int, ImageEntry] = {}
    order: list[int] = []
    for info in infos:
        res = results.get(info.mbid)
        if res is None or res.state != OK:
            continue
        for pos, raw in enumerate(res.images):
            try:
                image_id = int(raw["id"])
            except (KeyError, TypeError, ValueError):
                continue
            entry = by_id.get(image_id)
            if entry is None:
                types = [str(t) for t in (raw.get("types") or [])]
                entry = by_id[image_id] = ImageEntry(
                    image_id=image_id, release=info.mbid, releases=[], edition=info.label, types=types,
                    comment=str(raw.get("comment") or ""), approved=bool(raw.get("approved")),
                    width=_dim(raw.get("width")), height=_dim(raw.get("height")), date=info.date,
                    format=_format_of(raw))
                order.append(image_id)
            if info.mbid not in entry.releases:
                entry.releases.append(info.mbid)
                entry.positions[info.mbid] = pos
    return [by_id[i] for i in order]


FORMATS = ("jpg", "png", "gif", "webp", "pdf")


def _format_of(raw: Mapping) -> str:
    """Type of the original file from the CAA ``image`` URL; ``jpg`` when it is missing or odd (as the store does)."""
    name = str(raw.get("image") or "").rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return ext if ext in FORMATS else "jpg"


def _dim(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def build_group_index(
    rgid: str,
    fetch_releases: Callable[[str], list[Mapping] | None],
    fetch_release_index: Callable[[str], ReleaseIndex],
    *,
    owned_release: str | None = None,
    cached: Mapping[str, ReleaseIndex] | None = None,
    releases_cap: int = RELEASES_CAP,
    stored_cap: int = IMAGES_STORED_CAP,
    time_bound: float = BUILD_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> GroupIndex:
    """Build the merged index for one release group.

    ``fetch_releases(rgid)`` is the one MusicBrainz lookup for the group's releases (``None`` when it
    failed). ``fetch_release_index(release)`` returns one CAA answer and must not raise. ``cached`` holds
    fresh per-release answers from earlier builds; those releases are not fetched again, so a build that
    stopped on time resumes where it left off.
    """
    started = clock()
    owned = owned_release.lower() if owned_release else None
    docs = fetch_releases(rgid)
    if docs is None:
        return GroupIndex(rgid, UNAVAILABLE, [], owned, 0, 0, 0, 0, False, None, clock() - started)
    infos = _release_order((parse_release(d) for d in docs), owned)
    total = len(infos)
    wanted = infos[:releases_cap]
    results: dict[str, ReleaseIndex] = {}
    fetched = 0
    stopped = False
    for info in wanted:
        known = (cached or {}).get(info.mbid)
        if known is not None and known.state in (OK, EMPTY):
            results[info.mbid] = known
            continue
        if clock() - started >= time_bound:
            stopped = True
            break
        res = fetch_release_index(info.mbid)
        fetched += 1
        results[info.mbid] = res if res.state in (OK, EMPTY) else ReleaseIndex(UNAVAILABLE)
    handled = [i for i in wanted if i.mbid in results]
    empty = sum(1 for i in handled if results[i.mbid].state == EMPTY)
    failed = sum(1 for i in handled if results[i.mbid].state == UNAVAILABLE)
    images = _merge(handled, results)
    reason = None
    if stopped:
        reason = "time"
    elif failed and images:
        reason = "partial"
    elif total > releases_cap:
        reason = "release_cap"
    if len(images) > stored_cap:
        images = _trim(images, stored_cap, owned, {i.mbid: i.date for i in infos})
        reason = reason or "stored_cap"
    if images:
        status = OK
    elif failed or stopped:
        status = UNAVAILABLE
    else:
        status = EMPTY
    return GroupIndex(
        rgid=rgid, status=status, images=images, owned_release=owned, releases_total=total,
        releases_fetched=len(handled), releases_empty=empty, releases_failed=failed,
        truncated=reason is not None, truncated_reason=reason, seconds=clock() - started,
        labels={i.mbid: i.label for i in infos}, dates={i.mbid: i.date for i in infos})


def _has(e: ImageEntry, kind: str) -> bool:
    return kind in e.types


def best_front(images: Iterable[ImageEntry]) -> ImageEntry | None:
    """Approved, Front type, larger side, earlier release date, lower id. ``None`` when nothing is typed Front.

    Never an artist photo and never an untyped image: a group with no Front image has no best front.
    """
    fronts = [e for e in images if _has(e, "Front")]
    return min(fronts, key=_quality_key) if fronts else None


def _slot_winner(images: list[ImageEntry], kind: str, owned: str | None) -> ImageEntry | None:
    pool = [e for e in images if _has(e, kind)]
    own = [e for e in pool if owned and owned in e.releases]
    pool = own or pool
    return min(pool, key=_quality_key) if pool else None


def _booklet(images: list[ImageEntry], owned: str | None, dates: Mapping[str, str]) -> tuple[str | None, list[ImageEntry]]:
    pages: dict[str, list[ImageEntry]] = {}
    for e in images:
        if _has(e, "Booklet"):
            for rel in e.releases:
                pages.setdefault(rel, []).append(e)
    if not pages:
        return None, []
    # most pages; then the owned release; then the earlier date; then MBID
    chosen = min(pages, key=lambda r: (-len(pages[r]), r != owned, _date_key(dates.get(r, "")), r))
    ordered = sorted(pages[chosen], key=lambda e: (e.positions.get(chosen, 0), e.image_id))
    return chosen, ordered[:BOOKLET_PAGES_CAP]


def slots_view(index: GroupIndex) -> dict:
    """One best image per slot type, plus the booklet as one ordered set from a single release."""
    owned = index.owned_release
    slots: dict[str, dict] = {}
    for kind in SLOT_TYPES:
        win = _slot_winner(index.images, kind, owned)
        if win is None:
            continue
        own = bool(owned and owned in win.releases)
        slots[kind] = {"image_id": win.image_id, "release": owned if own else win.release,
                       "edition": index.labels.get(owned, "") if own else win.edition, "from_owned": own}
    rel, pages = _booklet(index.images, owned, index.dates)
    booklet = ({"release": rel, "edition": index.labels.get(rel, ""), "image_ids": [p.image_id for p in pages]}
               if rel else None)
    return {"slots": slots, "booklet": booklet}


def _priority(images: list[ImageEntry], owned: str | None, dates: Mapping[str, str] | None = None) -> list[ImageEntry]:
    """Trim order: slot winners, booklet pages, then the rest by quality."""
    winners = [w for k in SLOT_TYPES if (w := _slot_winner(images, k, owned))]
    _rel, pages = _booklet(images, owned, dates or {})
    seen: set[int] = set()
    out: list[ImageEntry] = []
    for e in [*winners, *pages, *sorted(images, key=_quality_key)]:
        if e.image_id not in seen:
            seen.add(e.image_id)
            out.append(e)
    return out


def _trim(images: list[ImageEntry], cap: int, owned: str | None, dates: Mapping[str, str] | None = None) -> list[ImageEntry]:
    keep = {e.image_id for e in _priority(images, owned, dates)[:cap]}
    return [e for e in images if e.image_id in keep]


def to_response(index: GroupIndex, *, served_cap: int = IMAGES_SERVED_CAP) -> dict:
    """The index as the endpoint returns it. ``status`` is ``ok``, ``empty`` or ``unavailable``.

    Past ``served_cap`` images the list is trimmed (slot winners, booklet pages, then the rest by
    quality) and ``truncated`` is true with ``truncated_reason`` ``served_cap`` unless an earlier reason
    already applies. Served order is the quality order, so clients show the best images first.
    """
    reason = index.truncated_reason
    images = index.images
    if len(images) > served_cap:
        images = _trim(images, served_cap, index.owned_release, index.dates)
        reason = reason or "served_cap"
    served = sorted(images, key=_quality_key)
    view = slots_view(GroupIndex(**{**index.__dict__, "images": served})) if served else {"slots": {}, "booklet": None}
    front = best_front(served)
    return {
        "status": index.status,
        "rgid": index.rgid,
        "truncated": reason is not None,
        "truncated_reason": reason,
        "releases": {"total": index.releases_total, "fetched": index.releases_fetched,
                     "empty": index.releases_empty, "failed": index.releases_failed},
        "best_front": front.image_id if front else None,
        "slots": view["slots"],
        "booklet": view["booklet"],
        "images": [e.to_dict() for e in served],
    }
