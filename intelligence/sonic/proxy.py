"""Proxy for Navidrome's ``getSonicSimilarTracks`` and ``findSonicPath`` (Server V2 Phase 7, work item 1).

Pure logic: the Navidrome call is injected (``api_call(method, **params)``, the legacy client's shape), so
nothing here touches the network, the store or a provider. No audio analysis of our own.

Rules measured by the 2026-11-07 probe (docs/ServerV2.md, Phase 7):
- Similarity sits in a narrow band (median 0.92), so matches keep Navidrome's order and the score is
  informational only; callers must not threshold on it.
- Near-duplicates of the seed (another edition or language version of the same recording) appear among
  the matches and are dropped here: same MusicBrainz recording id, or same normalised title by the same artist.
- Path steps carry ``similarity: -1`` (every step on the owner's server, re-checked 2026-11-07; the probe
  note said only the first); that means "no score" and becomes ``None``.
- A song the sonic plugin has not analysed (2 of 250 sampled, 2026-11-07: error 0, "AudioMuse-AI returned
  status 404") is ``empty``, not ``unavailable``: the feature works, this song has no matches.
- Navidrome answers error 70 for an unknown song and error 0 when the sonic plugin fails; neither is
  an exception to the caller, each is a ``status`` the client can hide or retry.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

MAX_COUNT = 50
OVERFETCH = 2  # ask for extra matches so dropping duplicates still leaves ``count``

_ERROR_CODE = re.compile(r"API error (\d+)")
_BRACKETS = re.compile(r"[\(\[][^)\]]*[\)\]]")
_SUFFIX = re.compile(r"\s+-\s+.*$")
_NON_WORD = re.compile(r"[^\w]+")
_NOT_ANALYSED = re.compile(r"AudioMuse-AI returned status 404")

STATUSES = ("ok", "empty", "not_found", "unavailable")


@dataclass
class SonicResult:
    status: str
    seed: dict[str, Any] | None = None
    tracks: list[dict[str, Any]] = field(default_factory=list)
    dropped: dict[str, int] = field(default_factory=dict)

    def payload(self) -> dict[str, Any]:
        return {"status": self.status, "seed": self.seed, "tracks": self.tracks, "dropped": dict(self.dropped)}


def _error_code(exc: Exception) -> int | None:
    found = _ERROR_CODE.search(str(exc))
    return int(found.group(1)) if found else None


def _clamp(count: int, low: int = 1) -> int:
    return max(low, min(int(count), MAX_COUNT))


def normalize_title(title: str) -> str:
    """Lower-case title without bracketed notes (remaster, live) or a ' - suffix', punctuation removed."""
    text = _SUFFIX.sub("", _BRACKETS.sub(" ", str(title or "")).lower())
    return _NON_WORD.sub(" ", text).strip()


def _artist_key(entry: dict[str, Any]) -> str:
    return str(entry.get("artistId") or "").strip() or _NON_WORD.sub(" ", str(entry.get("artist") or "").lower()).strip()


def public_track(entry: dict[str, Any], similarity: float | None = None) -> dict[str, Any]:
    """The few fields a client needs; every song in Navidrome is owned by definition."""
    return {
        "navidrome_id": entry.get("id"), "title": entry.get("title"), "artist": entry.get("artist"),
        "artist_id": entry.get("artistId"), "album": entry.get("album"), "album_id": entry.get("albumId"),
        "duration": entry.get("duration"), "year": entry.get("year"), "mbid": entry.get("musicBrainzId") or None,
        "cover_art": entry.get("coverArt"), "owned": True, "similarity": similarity,
    }


def _score(raw: Any) -> float | None:
    """Navidrome's ``-1`` (path start) and anything non-numeric mean no score."""
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw < 0:
        return None
    return round(float(raw), 4)


def _is_same_recording(seed: dict[str, Any], entry: dict[str, Any]) -> bool:
    if entry.get("id") == seed.get("id"):
        return True
    seed_mbid, mbid = seed.get("musicBrainzId"), entry.get("musicBrainzId")
    if seed_mbid and seed_mbid == mbid:
        return True
    title = normalize_title(entry.get("title"))
    return bool(title) and title == normalize_title(seed.get("title")) and _artist_key(entry) == _artist_key(seed)


def _call(api_call: Callable[..., dict], method: str, **params) -> tuple[dict | None, str | None]:
    """``(root, None)`` on success, ``(None, status)`` when Navidrome says not found or the plugin fails."""
    try:
        return api_call(method, **params), None
    except RuntimeError as exc:
        code = _error_code(exc)
        if code == 70:
            return None, "not_found"
        if code == 0 and _NOT_ANALYSED.search(str(exc)):  # song has no analysis data: nothing to match, not a failure
            return None, "empty"
        if code in (0, 30):  # plugin failure or unsupported method: hide the feature (a refused login still raises)
            return None, "unavailable"
        raise


def similar_tracks(api_call: Callable[..., dict], song_id: str, *, count: int = 10) -> SonicResult:
    """Up to ``count`` sonically similar owned tracks for one song, near-duplicates of the seed removed."""
    count = _clamp(count)
    song, status = _call(api_call, "getSong", id=song_id)
    if status:
        return SonicResult(status)
    seed = (song or {}).get("song") or {}
    if not seed.get("id"):
        return SonicResult("not_found")
    root, status = _call(api_call, "getSonicSimilarTracks", id=song_id, count=_clamp(count * OVERFETCH))
    if status:
        return SonicResult(status, seed=public_track(seed))
    tracks, seen, dropped = [], set(), {"same_recording": 0, "repeat": 0}
    for match in (root or {}).get("sonicMatch") or []:
        entry = match.get("entry") or {}
        if not entry.get("id"):
            continue
        if _is_same_recording(seed, entry):
            dropped["same_recording"] += 1
            continue
        key = (normalize_title(entry.get("title")), _artist_key(entry))
        if key in seen:
            dropped["repeat"] += 1
            continue
        seen.add(key)
        if len(tracks) < count:
            tracks.append(public_track(entry, _score(match.get("similarity"))))
    return SonicResult("ok" if tracks else "empty", seed=public_track(seed), tracks=tracks, dropped=dropped)


def sonic_path(api_call: Callable[..., dict], start_id: str, end_id: str, *, count: int = 10) -> SonicResult:
    """Ordered steps from one song to another through sound; the first entry is the start song."""
    if start_id == end_id:
        raise ValueError("start and end must be different songs")
    root, status = _call(api_call, "findSonicPath", startSongId=start_id, endSongId=end_id, count=_clamp(count, 2))
    if status:
        return SonicResult(status)
    steps = [public_track(m["entry"], _score(m.get("similarity")))
             for m in (root or {}).get("sonicMatch") or [] if (m.get("entry") or {}).get("id")]
    return SonicResult("ok" if steps else "empty", seed=steps[0] if steps else None, tracks=steps)
