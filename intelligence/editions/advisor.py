"""Edition advisor (docs/ServerV2.md Phase 2, item 4).

For an album owned as two or more editions (the slice 3 duplicate albums), summarise what
the optional audio job *measured* for each edition so the owner can compare them:
integrated loudness, loudness range, true peak, peak-to-loudness ratio (true peak minus
integrated loudness, a dynamic-range indicator) and clipped tracks.

Rules kept here:

- wording is "measured", never "better" or "worse". The advisor reports numbers and how far
  apart they are; it does not rank editions or recommend keeping or removing one;
- read-only and suggestion-only: no file, tag, entity or edge is written, nothing is deleted,
  and every advice item says ``suggestion_only: true``;
- no decoding and no network calls here. Measurements come from the audio job's saved
  progress (``AudioMeasurement`` per Navidrome track id), so an edition with nothing
  measured reports "not measured" instead of a guess;
- editions are compared only when every owned track of both has a measurement and the two
  tracklists match, so a bonus track or a missing measurement cannot masquerade as a
  difference between mastering; otherwise the reason is stated.
"""
from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from statistics import median
from typing import Any, Iterable, Mapping

from ..health.audio import CLIP_MIN_PEAK_COUNT, CLIP_PEAK_DBFS, AudioMeasurement
from ..store import repositories as repo
from .duplicates import DuplicateAlbum, Reason
from .grouping import Edition

ADVICE_KIND = "edition_advice"
MEANINGFUL_DELTA = 1.0  # dB or LU; a smaller gap is reported as "about the same". Untuned
METRICS = ("integrated_lufs", "loudness_range_lu", "true_peak_dbfs", "peak_to_loudness_db")

_LABELS = {
    "integrated_lufs": ("integrated loudness", "LUFS"),
    "loudness_range_lu": ("loudness range", "LU"),
    "true_peak_dbfs": ("true peak", "dBFS"),
    "peak_to_loudness_db": ("peak-to-loudness ratio", "dB"),
}


@dataclass(frozen=True)
class EditionMeasures:
    release_id: int
    title: str
    tracks_total: int
    tracks_measured: int
    integrated_lufs: float | None = None  # median over measured tracks
    loudness_range_lu: float | None = None  # median
    true_peak_dbfs: float | None = None  # highest
    peak_to_loudness_db: float | None = None  # median of (true peak - integrated loudness)
    clipped_tracks: int = 0

    @property
    def complete(self) -> bool:
        return self.tracks_total > 0 and self.tracks_measured == self.tracks_total


@dataclass(frozen=True)
class MetricDelta:
    metric: str
    value: float  # later edition minus the first edition
    meaningful: bool


@dataclass(frozen=True)
class EditionComparison:
    release_id: int
    against_release_id: int
    comparable: bool
    reasons: tuple[Reason, ...]
    deltas: tuple[MetricDelta, ...] = ()
    statements: tuple[str, ...] = ()


@dataclass(frozen=True)
class EditionAdvice:
    group_entity_id: int
    title: str
    editions: tuple[EditionMeasures, ...]
    comparisons: tuple[EditionComparison, ...]
    kind: str = ADVICE_KIND
    suggestion_only: bool = True


@dataclass
class AdviceReport:
    advice: list[EditionAdvice] = field(default_factory=list)
    not_measured: int = 0  # duplicate albums with no measured track at all


def edition_track_ids(db: sqlite3.Connection, albums: Iterable[DuplicateAlbum]) -> list[str]:
    """Navidrome track ids of every owned track in these albums' editions, sorted.

    This is what the audio job should measure for the advisor; nothing else is read.
    """
    ids: set[str] = set()
    for album in albums:
        for edition in album.editions:
            ids.update(_track_ids(db, edition))
    return sorted(ids)


def advise(
    db: sqlite3.Connection,
    albums: Iterable[DuplicateAlbum],
    measurements: Mapping[str, AudioMeasurement | Mapping[str, Any]],
) -> AdviceReport:
    """One advice item per duplicate album, from saved measurements keyed by track id."""
    report = AdviceReport()
    for album in albums:
        per_edition = [_measures(db, edition, measurements) for edition in album.editions]
        if not any(m.tracks_measured for m in per_edition):
            report.not_measured += 1
        report.advice.append(EditionAdvice(
            group_entity_id=album.group_entity_id, title=album.title, editions=tuple(per_edition),
            comparisons=_comparisons(album, per_edition),
        ))
    return report


def _track_ids(db: sqlite3.Connection, edition: Edition) -> list[str]:
    ids = []
    for entry in edition.tracks:
        recording = repo.get_entity(db, entry.recording_id)
        if recording is not None and recording["navidrome_id"]:
            ids.append(recording["navidrome_id"])
    return ids


def _measure(value: AudioMeasurement | Mapping[str, Any]) -> AudioMeasurement:
    return value if isinstance(value, AudioMeasurement) else AudioMeasurement.from_dict(dict(value))


def _finite(values: Iterable[float | None]) -> list[float]:
    return [v for v in values if v is not None and math.isfinite(v)]


def _measures(db: sqlite3.Connection, edition: Edition, measurements: Mapping[str, Any]) -> EditionMeasures:
    ids = _track_ids(db, edition)
    found = [_measure(measurements[i]) for i in ids if i in measurements]
    lufs = _finite(m.integrated_lufs for m in found)
    lra = _finite(m.loudness_range_lu for m in found)
    peaks = _finite(m.true_peak_dbfs for m in found)
    plr = _finite(
        m.true_peak_dbfs - m.integrated_lufs
        for m in found
        if m.true_peak_dbfs is not None and m.integrated_lufs is not None
        and math.isfinite(m.true_peak_dbfs) and math.isfinite(m.integrated_lufs)
    )
    clipped = sum(
        1 for m in found
        if m.peak_dbfs is not None and m.peak_count is not None
        and m.peak_dbfs >= CLIP_PEAK_DBFS and m.peak_count >= CLIP_MIN_PEAK_COUNT
    )
    return EditionMeasures(
        release_id=edition.release_id, title=edition.title, tracks_total=len(edition.tracks),
        tracks_measured=len(found),
        integrated_lufs=_round(median(lufs)) if lufs else None,
        loudness_range_lu=_round(median(lra)) if lra else None,
        true_peak_dbfs=_round(max(peaks)) if peaks else None,
        peak_to_loudness_db=_round(median(plr)) if plr else None,
        clipped_tracks=clipped,
    )


def _round(value: float) -> float:
    return round(value, 2)


def _comparisons(album: DuplicateAlbum, measures: list[EditionMeasures]) -> tuple[EditionComparison, ...]:
    if len(measures) < 2:
        return ()
    first = measures[0]
    out = []
    for later, difference in zip(measures[1:], album.differences):
        reasons: list[Reason] = []
        if not first.complete or not later.complete:
            reasons.append(Reason(
                "not_fully_measured",
                f"measured {first.tracks_measured}/{first.tracks_total} and "
                f"{later.tracks_measured}/{later.tracks_total} tracks; both need every track measured",
            ))
        if not difference.diff.same:
            reasons.append(Reason("tracklists_differ", "the tracklists differ, so the figures cover different tracks"))
        if reasons:
            out.append(EditionComparison(later.release_id, first.release_id, False, tuple(reasons)))
            continue
        deltas = tuple(
            MetricDelta(metric, _round(getattr(later, metric) - getattr(first, metric)),
                        abs(getattr(later, metric) - getattr(first, metric)) >= MEANINGFUL_DELTA)
            for metric in METRICS
            if getattr(later, metric) is not None and getattr(first, metric) is not None
        )
        out.append(EditionComparison(
            later.release_id, first.release_id, True, (), deltas, _statements(first, later, deltas),
        ))
    return tuple(out)


def _statements(first: EditionMeasures, later: EditionMeasures, deltas: tuple[MetricDelta, ...]) -> tuple[str, ...]:
    lines = []
    for delta in deltas:
        label, unit = _LABELS[delta.metric]
        a, b = getattr(first, delta.metric), getattr(later, delta.metric)
        if delta.meaningful:
            lines.append(f"measured {label}: {later.title} {b:g} {unit}, {first.title} {a:g} {unit} ({delta.value:+g})")
        else:
            lines.append(f"measured {label}: about the same ({a:g} and {b:g} {unit})")
    if first.clipped_tracks != later.clipped_tracks:
        lines.append(
            f"measured clipped tracks: {later.title} {later.clipped_tracks}, {first.title} {first.clipped_tracks}"
        )
    return tuple(lines)
