"""Artist page data-list fields for the Index theme (I0): plays, active years, owned of total albums."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

ActiveYearsReader = Callable[[str], "dict[str, Any] | None"]


def active_years(span: dict[str, Any] | None) -> dict[str, Any] | None:
    """``{"begin", "end", "ended"}`` (years as ints) from a stored life span, or None without a begin year.

    ``end`` is None while the artist is still active or MusicBrainz states no end year.
    """
    if not span:
        return None
    begin = _year(span.get("begin"))
    if begin is None:
        return None
    return {"begin": begin, "end": _year(span.get("end")), "ended": bool(span.get("ended"))}


def _year(value: Any) -> int | None:
    text = str(value or "")[:4]
    return int(text) if text.isdigit() else None


def album_counts(catalog: list[dict[str, Any]]) -> tuple[int, int] | None:
    """``(owned, total)`` over the albums a provider lists, or None when no provider listed any.

    Owned albums only the library holds (live albums, compilations) are not counted: the total
    is what the providers say exists, so "5 of 9" never exceeds itself.
    """
    listed = [a for a in catalog if any(s != "navidrome" for s in a.get("sources") or ())]
    if not listed:
        return None
    return sum(1 for a in listed if a.get("owned")), len(listed)
