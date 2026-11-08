"""MusicBrainz release search for the identity-resolution ladder's step 3 (Server V2 automatic API fill).

Builds the ``search`` callable :func:`intelligence.resolution.ladder.resolve` takes for an album that has
no release MBID tag. The ladder accepts a result only when exactly one candidate matches the artist,
title, track count and every track duration, so this module only has to supply honest candidates:

* one search request (``release:"title" AND artist:"name"``, plus the track count when known);
* for each candidate whose artist and title already match and whose track count fits, one lookup that
  returns the track durations (only when the library item has durations to compare).

Every request goes through the caller's :class:`api_fill.Paced` (one per 1.1 s). Candidates are capped at
``MAX_CANDIDATES`` so one album costs at most ``1 + MAX_CANDIDATES`` requests. A failed request raises
:class:`api_fill.ApiError`, which the ladder turns into a ``deferred`` outcome (nothing written).
"""
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlencode

from ..resolution.ladder import LibraryRef
from ..resolution.normalize import artist_key, title_key
from .api_fill import BASE, Fetch

MAX_CANDIDATES = 5


def _quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _credit(release: dict) -> str:
    phrase = "".join(f"{c.get('name', '')}{c.get('joinphrase', '')}" for c in release.get("artist-credit") or []
                     if isinstance(c, dict))
    return phrase


def make_search(fetch: Fetch) -> Callable[[LibraryRef], list[dict[str, Any]]]:
    def search(ref: LibraryRef) -> list[dict[str, Any]]:
        query = f"release:{_quote(ref.title or '')} AND artist:{_quote(ref.artist or '')}"
        if ref.track_count:
            query += f" AND tracksrelease:{int(ref.track_count)}"
        body = fetch(BASE + "release?" + urlencode({"query": query, "fmt": "json", "limit": 10}))
        found: list[dict[str, Any]] = []
        for release in body.get("releases") or []:
            if len(found) >= MAX_CANDIDATES:
                break
            count = release.get("track-count")
            if count is None:
                count = sum(m.get("track-count", 0) for m in release.get("media") or []) or None
            candidate = {"mbid": str(release.get("id") or ""), "title": release.get("title"),
                         "artist": _credit(release), "track_count": count}
            if (artist_key(candidate["artist"]) != artist_key(ref.artist)
                    or title_key(candidate["title"]) != title_key(ref.title)
                    or (ref.track_count is not None and count != ref.track_count)):
                continue  # the ladder would reject it; do not spend a lookup on it
            if ref.durations_ms:
                detail = fetch(BASE + f"release/{candidate['mbid']}?" + urlencode({"inc": "recordings", "fmt": "json"}))
                candidate["durations_ms"] = [t.get("length") if t.get("length") is not None
                                             else (t.get("recording") or {}).get("length")
                                             for m in detail.get("media") or [] for t in m.get("tracks") or []]
                if any(d is None for d in candidate["durations_ms"]):
                    continue  # MusicBrainz lacks a length, so the durations cannot be checked
            found.append(candidate)
        return found
    return search
