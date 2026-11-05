"""Run the audio checks as a bounded, resumable job and fold results into the report.

The job saves every measurement in its progress, so a run that stops on its budget (or a
crash) continues with the files not yet done. A file that cannot be analysed is recorded as
an error with a short reason and is not retried within the same run.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Iterable

from ..ingest.navidrome import NormalizedTrack
from ..jobs import JobContext
from .audio import (
    AUDIO_CHECKS, AudioCheckError, AudioMeasurement, findings_for_all, measure_file,
)
from .report import Finding, HealthReport

JOB_NAME = "health_audio"
SEVERITY = "info"

Measure = Callable[..., AudioMeasurement]


def make_job(
    tracks: Iterable[NormalizedTrack],
    root: str,
    *,
    measure: Measure = measure_file,
    checkpoint_every: int = 1,
) -> Callable[[JobContext], bool]:
    """A job function for :func:`intelligence.jobs.run_job` over ``tracks`` (sorted by id)."""
    ordered = sorted({t.navidrome_id: t for t in tracks}.values(), key=lambda t: t.navidrome_id)

    def job(ctx: JobContext) -> bool:
        measured: dict[str, Any] = ctx.progress.setdefault("measured", {})
        errors: dict[str, str] = ctx.progress.setdefault("errors", {})
        ctx.progress["total"] = len(ordered)
        pending = 0
        for track in ordered:
            tid = track.navidrome_id
            if tid in measured or tid in errors:
                continue
            if not ctx.has_budget():
                ctx.checkpoint(ctx.progress)
                return False
            try:
                measured[tid] = measure(root, track.path, tid, track.sampling_rate).as_dict()
            except AudioCheckError as exc:
                errors[tid] = str(exc)[:120]
            pending += 1
            if pending >= checkpoint_every:
                ctx.checkpoint(ctx.progress, items=pending)
                pending = 0
        ctx.checkpoint(ctx.progress, items=pending)
        return True

    return job


def findings_from_progress(
    progress: dict[str, Any], tracks: Iterable[NormalizedTrack]
) -> list[Finding]:
    """Report findings from a job's saved progress, one per suspected track and check."""
    by_id = {t.navidrome_id: t for t in tracks}
    pairs = []
    for tid, data in sorted(progress.get("measured", {}).items()):
        suffix = by_id[tid].suffix if tid in by_id else None
        pairs.append((AudioMeasurement.from_dict({**data, "track_id": tid}), suffix))
    out = []
    for f in findings_for_all(pairs):
        out.append(Finding(f.check, SEVERITY, (f.track_id,), f.message, f.detail))
    return out


def with_audio(report: HealthReport, audio_findings: Iterable[Finding]) -> HealthReport:
    """The report plus audio findings; audio checks move out of ``not_checked``."""
    findings = sorted(
        [*report.findings, *audio_findings], key=lambda f: (f.check, f.album_ids, f.message)
    )
    not_checked = tuple(c for c in report.not_checked if c not in AUDIO_CHECKS)
    return replace(report, findings=tuple(findings), not_checked=not_checked, extra_checks=AUDIO_CHECKS)
