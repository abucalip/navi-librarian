"""Find which album a song (artist and title only, as web radios announce it) is from."""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def _norm(value) -> str:
    return "".join(ch.casefold() for ch in str(value or "") if ch.isalnum())


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _fetch_recordings(query: str, limit: int):
    request = Request(
        "https://musicbrainz.org/ws/2/recording/?" + urlencode({"query": query, "fmt": "json", "limit": limit}),
        headers={"User-Agent": "NavidromeLibrarian/1.0 (personal music discovery)"},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8")).get("recordings") or []


def _year(release) -> int | None:
    text = str(release.get("date") or "")[:4]
    return int(text) if text.isdigit() else None


def _rank(release):
    """Lower is better: a plain official studio album, then the earliest."""
    group = release.get("release-group") or {}
    plain = group.get("primary-type") == "Album" and not group.get("secondary-types")
    official = release.get("status") == "Official"
    return (0 if plain else 1, 0 if official else 1, _year(release) or 9999)


def lookup_recording_album(artist: str, title: str, fetch=_fetch_recordings):
    """``{"album": str, "year": int | None}`` for the best exact match, else None."""
    query = f'recording:"{_escape(title)}" AND artist:"{_escape(artist)}"'
    candidates = []
    for recording in fetch(query, 10):
        if _norm(recording.get("title")) != _norm(title):
            continue
        credit = "".join(c.get("name", "") + c.get("joinphrase", "") for c in recording.get("artist-credit") or [])
        if _norm(credit) != _norm(artist):
            continue
        candidates.extend(r for r in recording.get("releases") or [] if r.get("title"))
    if not candidates:
        return None
    best = min(candidates, key=_rank)
    return {"album": best["title"], "year": _year(best)}
