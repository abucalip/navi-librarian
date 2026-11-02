"""The short file-quality tags: a song's (``FLAC 16/44``, ``MP3 320k``) and an album's (``FLAC``, ``lossless``, ``320k``).

Pure text rule over the fields Navidrome reports for a song file (Subsonic ``suffix``,
``bitRate`` in kbps, ``bitDepth`` in bits, ``samplingRate`` in Hz). Missing or unusable fields
give a shorter tag or none; nothing is guessed beyond what the suffix and fields say.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

_LOSSLESS = {"flac": "FLAC", "alac": "ALAC", "wav": "WAV", "aiff": "AIFF", "aif": "AIFF", "ape": "APE", "wv": "WV", "dsf": "DSD", "dff": "DSD"}
_LOSSY = {"mp3": "MP3", "aac": "AAC", "ogg": "OGG", "opus": "OPUS", "wma": "WMA", "mp2": "MP2"}


def _positive(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0 else None


def quality_label(suffix: Any, bit_rate: Any, bit_depth: Any, sampling_rate: Any) -> str | None:
    """The tag for one file, or None when the suffix is unknown."""
    ext = str(suffix or "").strip().lower().lstrip(".")
    depth, khz, rate = _positive(bit_depth), _positive(sampling_rate), _positive(bit_rate)
    if ext in ("m4a", "mp4"):
        # Apple's container holds AAC (lossy, no bit depth) or ALAC (lossless, has one).
        ext = "alac" if depth else "aac"
    if ext in _LOSSLESS:
        name = _LOSSLESS[ext]
        if depth and khz:
            return f"{name} {depth}/{khz // 1000}"
        return f"{name} {depth}-bit" if depth else name
    if ext in _LOSSY:
        name = _LOSSY[ext]
        return f"{name} {rate}k" if rate else name
    return ext.upper() if ext else None


def album_quality_label(songs: Iterable[Mapping[str, Any]]) -> str | None:
    """The one tag for an album, from the files of its library songs (index entries).

    ``FLAC`` when every song is FLAC, ``lossless`` when every song is lossless but not all FLAC,
    otherwise the compressed songs' average bit rate (``320k``; the format name when none reports
    one). A mix of compressed and lossless files shows the compressed rate, the lowest quality
    on the album. None when no song has a known file format.
    """
    kinds: list[str] = []
    rates: list[int] = []
    lossy_name: str | None = None
    for song in songs:
        ext = str(song.get("suffix") or "").strip().lower().lstrip(".")
        depth, rate = _positive(song.get("bit_depth")), _positive(song.get("bit_rate"))
        if ext in ("m4a", "mp4"):
            ext = "alac" if depth else "aac"
        if ext == "flac":
            kinds.append("flac")
        elif ext in _LOSSLESS:
            kinds.append("lossless")
        elif ext:
            kinds.append("lossy")
            lossy_name = lossy_name or _LOSSY.get(ext, ext.upper())
            if rate:
                rates.append(rate)
    if not kinds:
        return None
    if "lossy" in kinds:
        return f"{round(sum(rates) / len(rates))}k" if rates else lossy_name
    return "FLAC" if all(k == "flac" for k in kinds) else "lossless"
