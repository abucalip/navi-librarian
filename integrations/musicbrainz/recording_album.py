"""Find which album a song (artist and title only, as web radios announce it) is from."""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from integrations.provider_gate import musicbrainz_lane

RECORDING_MAX_WAIT = 15.0  # a radio "Get" click waits for a slot only this long


def _norm(value) -> str:
    return "".join(ch.casefold() for ch in str(value or "") if ch.isalnum())


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _fetch_recordings(query: str, limit: int):
    request = Request(
        "https://musicbrainz.org/ws/2/recording/?" + urlencode({"query": query, "fmt": "json", "limit": limit}),
        headers={"User-Agent": "Discair/1.0 (personal music discovery)"},
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


def _matching_recordings(artist: str, title: str, fetch=_fetch_recordings, lane=None):
    """Return MusicBrainz recordings whose title and artist credit exactly match after normalisation."""
    query = f'recording:"{_escape(title)}" AND artist:"{_escape(artist)}"'
    lane = lane or musicbrainz_lane(RECORDING_MAX_WAIT)
    if not lane.acquire():
        raise OSError("MusicBrainz is rate limited")
    try:
        recordings = fetch(query, 10)
    except HTTPError as exc:
        if exc.code in (429, 503):
            lane.penalize(None)
        raise
    matches = []
    for recording in recordings:
        if _norm(recording.get("title")) != _norm(title):
            continue
        credit = "".join(c.get("name", "") + c.get("joinphrase", "") for c in recording.get("artist-credit") or [])
        if _norm(credit) != _norm(artist):
            continue
        matches.append(recording)
    return matches


def lookup_recording_album(artist: str, title: str, fetch=_fetch_recordings, lane=None):
    """``{"album": str, "year": int | None}`` for the best exact match, else None.

    The request takes a MusicBrainz slot from the shared gate; no slot within the wait raises
    ``OSError`` like any failed lookup."""
    candidates = []
    for recording in _matching_recordings(artist, title, fetch=fetch, lane=lane):
        candidates.extend(r for r in recording.get("releases") or [] if r.get("title"))
    if not candidates:
        return None
    best = min(candidates, key=_rank)
    return {"album": best["title"], "year": _year(best)}


def lookup_recording_mbid(artist: str, title: str, fetch=_fetch_recordings, lane=None) -> str | None:
    """Return the MusicBrainz recording MBID for the best exact match, else None."""
    best_mbid: str | None = None
    best_rank = None
    for recording in _matching_recordings(artist, title, fetch=fetch, lane=lane):
        mbid = str(recording.get("id") or "").strip()
        if not mbid:
            continue
        releases = [r for r in recording.get("releases") or [] if r.get("title")]
        rank = min((_rank(r) for r in releases), default=(2, 2, 9999))
        if best_mbid is None or rank < best_rank:
            best_mbid = mbid
            best_rank = rank
    return best_mbid
