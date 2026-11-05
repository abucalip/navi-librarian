"""Optional audio checks for Library Health: clipping, loudness and suspected transcodes.

These checks read audio files, so they are separate from the pure Navidrome-field report in
:mod:`.report` and run only as a bounded job. They are read-only: files are opened by
``ffmpeg`` for decoding and never written, the audio never leaves the server, and the only
output is measurements plus a worklist of "suspected" findings.

``ffmpeg`` is optional. When it is not installed, :func:`ffmpeg_available` is False and
callers report the audio checks as not checked instead of passing them.

Measurements (one decode pass per file):

* ``peak_dbfs`` and ``peak_count`` from ``astats`` -> clipping
* ``integrated_lufs``, ``loudness_range_lu`` and ``true_peak_dbfs`` from ``ebur128``
* ``hf_rms_dbfs``: RMS level of the band above a cutoff chosen from the sampling rate
  -> suspected upsampling or lossy-to-lossless transcode

Findings are heuristics. A quiet or old recording can legitimately have no high band, so
every finding says "suspected" and carries the measured numbers.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

CHECK_TRANSCODE = "suspected_upsampled_or_transcoded"
CHECK_CLIPPING = "clipping"
AUDIO_CHECKS = (CHECK_TRANSCODE, CHECK_CLIPPING)

LOSSLESS_SUFFIXES = frozenset({"flac", "wav", "wave", "aif", "aiff", "alac", "ape", "wv"})

CLIP_PEAK_DBFS = -0.1  # at or above this counts as touching full scale
CLIP_MIN_PEAK_COUNT = 50  # a lone peak is mastering, a run of them is clipping
HF_SILENT_DBFS = -75.0  # band RMS at or below this is treated as empty; 16-bit quantization alone measured -81.6 on a lowpassed test tone, so -85 would miss real transcodes. Untuned on the real library
LOSSY_BAND_HZ = 16000  # 44.1/48 kHz material: lossy encoders typically cut here or lower
HIRES_BAND_HZ = 22500  # above 48 kHz: content above this exists only in true hi-res
DEFAULT_TIMEOUT = 300.0

_INF = float("-inf")
_FLOAT = r"(-?inf|-?\d+(?:\.\d+)?)"


class AudioCheckError(Exception):
    """A file could not be analysed (missing, unsafe path, decode failure, timeout)."""


@dataclass(frozen=True)
class AudioMeasurement:
    track_id: str
    peak_dbfs: float | None = None
    peak_count: int | None = None
    integrated_lufs: float | None = None
    loudness_range_lu: float | None = None
    true_peak_dbfs: float | None = None
    hf_cutoff_hz: int | None = None
    hf_rms_dbfs: float | None = None  # -inf means digital silence in the band

    def as_dict(self) -> dict[str, Any]:
        """JSON-safe: infinite values become the strings "-inf" / "inf"."""
        data = asdict(self)
        for key, value in data.items():
            if isinstance(value, float) and value in (_INF, float("inf")):
                data[key] = "-inf" if value < 0 else "inf"
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AudioMeasurement":
        return cls(**{k: (float(v) if isinstance(v, str) and k != "track_id" else v) for k, v in data.items()})


@dataclass(frozen=True)
class AudioFinding:
    check: str
    track_id: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {"check": self.check, "track_id": self.track_id, "message": self.message, "detail": self.detail}


def ffmpeg_available(binary: str = "ffmpeg") -> bool:
    return shutil.which(binary) is not None


def resolve_under_root(root: str | Path, relative: str | None) -> Path:
    """The real path of ``relative`` inside ``root``, or :class:`AudioCheckError`.

    Rejects empty paths, traversal and symlinks that leave the root, and anything that is
    not an existing regular file. Navidrome paths are normally relative to the library; an
    absolute path is accepted only when it is already inside the root.
    """
    if not relative or "\x00" in relative:
        raise AudioCheckError("no path")
    base = Path(root).resolve()
    candidate = Path(relative)
    target = (candidate if candidate.is_absolute() else base / candidate).resolve()
    if base not in target.parents:
        raise AudioCheckError("path is outside the music root")
    if not target.is_file():
        raise AudioCheckError("file not found")
    return target


def hf_cutoff_for(sampling_rate: int | None) -> int | None:
    """The band edge to test for a file's sampling rate, or None when no test applies."""
    if not sampling_rate or sampling_rate < 32000:
        return None
    return HIRES_BAND_HZ if sampling_rate > 48000 else LOSSY_BAND_HZ


def build_command(path: Path, hf_cutoff: int | None, binary: str = "ffmpeg") -> list[str]:
    """The decode-only ffmpeg command. Output goes to the null muxer; nothing is written."""
    if hf_cutoff:
        graph = (
            "[0:a]asplit=3[a][b][c];"
            "[a]astats@full=metadata=0:reset=0[o1];"
            "[b]ebur128@lufs=peak=true[o2];"
            f"[c]highpass=f={int(hf_cutoff)},astats@hf=metadata=0:reset=0[o3];"
            "[o1][o2][o3]amix=inputs=3[out]"
        )
    else:
        graph = (
            "[0:a]asplit=2[a][b];"
            "[a]astats@full=metadata=0:reset=0[o1];"
            "[b]ebur128@lufs=peak=true[o2];"
            "[o1][o2]amix=inputs=2[out]"
        )
    return [
        binary, "-nostdin", "-hide_banner", "-nostats", "-v", "info",
        "-i", f"file:{path}", "-filter_complex", graph, "-map", "[out]", "-f", "null", "-",
    ]


def _num(text: str) -> float | None:
    if text.lstrip("-") == "inf":
        return _INF if text.startswith("-") else float("inf")
    try:
        return float(text)
    except ValueError:
        return None


def _overall(text: str, tag: str) -> str:
    """The "Overall" block of the astats instance named ``tag``."""
    lines = [line for line in text.splitlines() if f"[{tag} @" in line]
    joined = "\n".join(lines)
    return joined.split("Overall", 1)[1] if "Overall" in joined else ""


def parse_output(stderr: str, track_id: str, hf_cutoff: int | None = None) -> AudioMeasurement:
    """Read the filter summaries from ffmpeg's log. Missing values stay None."""
    overall = _overall(stderr, "astats@full")
    peak = re.search(r"Peak level dB:\s*" + _FLOAT, overall)
    count = re.search(r"Peak count:\s*(\d+)", overall)

    tail = stderr.rsplit("Summary:", 1)[1] if "Summary:" in stderr else ""
    integrated = re.search(r"\bI:\s*" + _FLOAT + r"\s*LUFS", tail)
    lra = re.search(r"\bLRA:\s*" + _FLOAT + r"\s*LU\b", tail)
    true_peak = re.search(r"\bPeak:\s*" + _FLOAT + r"\s*dBFS", tail)

    hf_rms = None
    if hf_cutoff:
        match = re.search(r"RMS level dB:\s*" + _FLOAT, _overall(stderr, "astats@hf"))
        hf_rms = _num(match.group(1)) if match else None

    return AudioMeasurement(
        track_id=track_id,
        peak_dbfs=_num(peak.group(1)) if peak else None,
        peak_count=int(count.group(1)) if count else None,
        integrated_lufs=_num(integrated.group(1)) if integrated else None,
        loudness_range_lu=_num(lra.group(1)) if lra else None,
        true_peak_dbfs=_num(true_peak.group(1)) if true_peak else None,
        hf_cutoff_hz=hf_cutoff,
        hf_rms_dbfs=hf_rms,
    )


Runner = Callable[[list[str], float], str]


def _run_ffmpeg(command: list[str], timeout: float) -> str:
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise AudioCheckError("analysis timed out") from exc
    except OSError as exc:
        raise AudioCheckError(f"ffmpeg could not start: {exc.__class__.__name__}") from exc
    if proc.returncode != 0:
        raise AudioCheckError(f"ffmpeg exited with {proc.returncode}")
    return proc.stderr


def measure_file(
    root: str | Path,
    relative_path: str | None,
    track_id: str,
    sampling_rate: int | None = None,
    *,
    binary: str = "ffmpeg",
    timeout: float = DEFAULT_TIMEOUT,
    runner: Runner = _run_ffmpeg,
) -> AudioMeasurement:
    """Decode one file under ``root`` and return its measurements.

    ``runner`` takes the command and a timeout and returns ffmpeg's log; tests replace it.
    Error text never includes the file path.
    """
    path = resolve_under_root(root, relative_path)
    cutoff = hf_cutoff_for(sampling_rate)
    return parse_output(runner(build_command(path, cutoff, binary), timeout), track_id, cutoff)


def findings_for(measurement: AudioMeasurement, suffix: str | None) -> list[AudioFinding]:
    """Turn one measurement into suspected-problem findings (possibly none)."""
    out: list[AudioFinding] = []
    m = measurement
    if (
        m.peak_dbfs is not None and m.peak_count is not None
        and m.peak_dbfs >= CLIP_PEAK_DBFS and m.peak_count >= CLIP_MIN_PEAK_COUNT
    ):
        out.append(AudioFinding(
            CHECK_CLIPPING, m.track_id,
            f"peak {m.peak_dbfs:.2f} dBFS reached {m.peak_count} times; possible clipping",
            {"peak_dbfs": m.peak_dbfs, "peak_count": m.peak_count},
        ))
    lossless = (suffix or "").lower().lstrip(".") in LOSSLESS_SUFFIXES
    if lossless and m.hf_cutoff_hz and m.hf_rms_dbfs is not None and m.hf_rms_dbfs <= HF_SILENT_DBFS:
        silent = m.hf_rms_dbfs == _INF
        kind = "upsampled from a lower rate" if m.hf_cutoff_hz == HIRES_BAND_HZ else "transcoded from a lossy source"
        shown = "silent" if silent else f"{m.hf_rms_dbfs:.1f} dBFS"
        out.append(AudioFinding(
            CHECK_TRANSCODE, m.track_id,
            f"band above {m.hf_cutoff_hz} Hz is {shown}; suspected {kind}",
            {"hf_cutoff_hz": m.hf_cutoff_hz, "hf_rms_dbfs": None if silent else m.hf_rms_dbfs, "hf_silent": silent},
        ))
    return out


def findings_for_all(items: Iterable[tuple[AudioMeasurement, str | None]]) -> list[AudioFinding]:
    """Findings for many ``(measurement, suffix)`` pairs, in a stable order."""
    found = [f for m, suffix in items for f in findings_for(m, suffix)]
    return sorted(found, key=lambda f: (f.check, f.track_id))
