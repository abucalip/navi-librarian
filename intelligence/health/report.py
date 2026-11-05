"""Library Health report built from normalized Navidrome albums.

Pure and deterministic: the same albums always give the same report, in the same order. It
makes no network calls, reads no files and writes nothing, not even to the intelligence
store. The output is a worklist for external tagging tools; the server never edits files.

Only checks that need nothing beyond Navidrome's own fields live here. Checks that need the
audio itself (suspected upsampling or transcoding, clipping, measured loudness) are listed
in :data:`NOT_CHECKED` and are not run, so the report never implies they passed.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..ingest.navidrome import NormalizedAlbum
from ..resolution.normalize import artist_key

CHECKS = (
    "missing_album_mbid",
    "missing_artist_mbid",
    "missing_track_mbid",
    "missing_genre",
    "track_count_mismatch",
    "track_number_problem",
    "disc_gap",
    "mixed_years",
    "replaygain_missing",
    "inconsistent_album_artist",
)
NOT_CHECKED = (
    "suspected_upsampled_or_transcoded",
    "clipping",
    "measured_loudness",
)
_SEVERITY = {
    "missing_album_mbid": "info", "missing_artist_mbid": "info", "missing_track_mbid": "info",
    "missing_genre": "info", "track_count_mismatch": "warn", "track_number_problem": "warn",
    "disc_gap": "warn", "mixed_years": "info", "replaygain_missing": "info",
    "inconsistent_album_artist": "warn",
}


@dataclass(frozen=True)
class Finding:
    check: str
    severity: str
    album_ids: tuple[str, ...]
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check, "severity": self.severity, "album_ids": list(self.album_ids),
            "message": self.message, "detail": self.detail,
        }


@dataclass(frozen=True)
class HealthReport:
    albums_checked: int
    findings: tuple[Finding, ...]
    not_checked: tuple[str, ...] = NOT_CHECKED
    extra_checks: tuple[str, ...] = ()  # checks added by the optional audio job

    @property
    def counts(self) -> dict[str, int]:
        counts = {check: 0 for check in (*CHECKS, *self.extra_checks)}
        for finding in self.findings:
            counts[finding.check] += 1
        return counts

    def as_dict(self) -> dict[str, Any]:
        return {
            "albums_checked": self.albums_checked,
            "counts": self.counts,
            "findings": [f.as_dict() for f in self.findings],
            "not_checked": list(self.not_checked),
        }


def build_report(albums: Iterable[NormalizedAlbum]) -> HealthReport:
    """Run every Navidrome-field check over ``albums``; duplicates by id keep the first."""
    unique: dict[str, NormalizedAlbum] = {}
    for album in albums:
        unique.setdefault(album.navidrome_id, album)
    ordered = sorted(unique.values(), key=lambda a: a.navidrome_id)
    findings: list[Finding] = []
    for album in ordered:
        findings.extend(_album_findings(album))
    findings.extend(_artist_spelling(ordered))
    findings.sort(key=lambda f: (f.check, f.album_ids, f.message))
    return HealthReport(albums_checked=len(ordered), findings=tuple(findings))


def _finding(check: str, album_ids: Iterable[str], message: str, **detail: Any) -> Finding:
    return Finding(check, _SEVERITY[check], tuple(album_ids), message, detail)


def _label(album: NormalizedAlbum) -> str:
    return f"{album.artist or 'Unknown artist'} - {album.name or 'Untitled'}"


def _album_findings(album: NormalizedAlbum) -> list[Finding]:
    out: list[Finding] = []
    aid, label, tracks = album.navidrome_id, _label(album), album.tracks

    if not album.mbid:
        out.append(_finding("missing_album_mbid", [aid], f"{label}: no MusicBrainz release id"))
    if not album.artist_mbid:
        out.append(_finding("missing_artist_mbid", [aid], f"{label}: album artist has no MusicBrainz id"))
    missing = sorted(t.navidrome_id for t in tracks if not t.mbid)
    if missing:
        out.append(_finding("missing_track_mbid", [aid], f"{label}: {len(missing)} of {len(tracks)} tracks have no MusicBrainz recording id", track_ids=missing))
    if not album.genres and not any(t.genres for t in tracks):
        out.append(_finding("missing_genre", [aid], f"{label}: no genre on the album or any track"))

    if album.song_count is not None and tracks and album.song_count != len(tracks):
        out.append(_finding("track_count_mismatch", [aid], f"{label}: album says {album.song_count} tracks, {len(tracks)} found", expected=album.song_count, found=len(tracks)))

    by_disc: dict[int, list[int | None]] = defaultdict(list)
    for t in tracks:
        by_disc[t.disc_number or 1].append(t.track_number)
    problems = {}
    for disc, numbers in sorted(by_disc.items()):
        issue = _numbering_issue(numbers)
        if issue:
            problems[str(disc)] = issue
    if problems:
        out.append(_finding("track_number_problem", [aid], f"{label}: track numbering problems on disc(s) {', '.join(problems)}", discs=problems))

    discs = sorted(by_disc)
    if discs and discs != list(range(1, discs[-1] + 1)):
        gaps = [d for d in range(1, discs[-1] + 1) if d not in by_disc]
        out.append(_finding("disc_gap", [aid], f"{label}: disc number(s) {gaps} missing", present=discs, missing=gaps))

    years = sorted({t.year for t in tracks if t.year})
    if len(years) > 1 and album.is_compilation is not True:
        out.append(_finding("mixed_years", [aid], f"{label}: tracks carry different years {years}; possible mixed editions", years=years))

    if tracks:
        without = sorted(t.navidrome_id for t in tracks if not t.replay_gain)
        if without:
            out.append(_finding("replaygain_missing", [aid], f"{label}: {len(without)} of {len(tracks)} tracks have no ReplayGain", track_ids=without))
    return out


def _numbering_issue(numbers: list[int | None]) -> dict[str, Any] | None:
    known = sorted(n for n in numbers if n is not None)
    issue: dict[str, Any] = {}
    unnumbered = len(numbers) - len(known)
    if unnumbered:
        issue["unnumbered"] = unnumbered
    duplicates = sorted({n for n in known if known.count(n) > 1})
    if duplicates:
        issue["duplicates"] = duplicates
    if known:
        gaps = [n for n in range(1, known[-1] + 1) if n not in set(known)]
        if gaps:
            issue["missing"] = gaps
    return issue or None


def _artist_spelling(albums: list[NormalizedAlbum]) -> list[Finding]:
    groups: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for album in albums:
        key = artist_key(album.artist)
        if key and album.artist:
            groups[key][album.artist].append(album.navidrome_id)
    out = []
    for key, spellings in sorted(groups.items()):
        if len(spellings) < 2:
            continue
        ids = sorted(i for group in spellings.values() for i in group)
        shown = {name: sorted(group) for name, group in sorted(spellings.items())}
        out.append(_finding("inconsistent_album_artist", ids, f"album artist spelled {len(spellings)} ways: {', '.join(sorted(spellings))}", spellings=shown))
    return out
