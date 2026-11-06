"""Resumable, checksum-verified downloader for MusicBrainz full-export archives.

Standard library only. The HTTP opener is injected so tests never touch the network.
A download goes to ``<name>.part`` and resumes with a ``Range`` request; the finished file
is renamed into place only after its SHA-256 matches ``SHA256SUMS``. Before any bytes are
fetched the free disk space is checked against the remaining size plus a reserve.
"""
from __future__ import annotations

import os
import shutil
import urllib.request
from pathlib import Path
from typing import Callable

from .dump import DumpError, sha256_file

BASE_URL = "https://data.metabrainz.org/pub/musicbrainz/data/fullexport"
CORE_ARCHIVE = "mbdump.tar.bz2"
COVER_ART_ARCHIVE = "mbdump-cover-art-archive.tar.bz2"
DEFAULT_RESERVE_BYTES = 2 * 1024**3
_CHUNK = 1 << 20

Opener = Callable[[str, dict], object]


class DownloadError(DumpError):
    """The download cannot continue safely (disk, server answer, or checksum)."""


def default_opener(url: str, headers: dict, timeout: float = 60.0):
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - https URL built here


def parse_sha256sums(text: str) -> dict[str, str]:
    """``SHA256SUMS`` lines are ``<hex>  <name>`` (a leading ``*`` marks binary mode)."""
    sums: dict[str, str] = {}
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            sums[parts[1].strip().lstrip("*")] = parts[0].lower()
    return sums


def _read_text(url: str, opener: Opener) -> str:
    response = opener(url, {})
    try:
        return response.read().decode("utf-8")
    finally:
        response.close()


def latest_export(opener: Opener = default_opener, base_url: str = BASE_URL) -> str:
    """Name of the newest export directory, from the server's ``LATEST`` file."""
    name = _read_text(f"{base_url}/LATEST", opener).strip()
    if not name or "/" in name or name.startswith("."):
        raise DownloadError(f"unexpected LATEST contents: {name!r}")
    return name


def fetch_checksums(export: str, opener: Opener = default_opener, base_url: str = BASE_URL) -> dict[str, str]:
    return parse_sha256sums(_read_text(f"{base_url}/{export}/SHA256SUMS", opener))


def check_free_disk(directory, needed_bytes: int, reserve_bytes: int = DEFAULT_RESERVE_BYTES) -> None:
    free = shutil.disk_usage(directory).free
    if free < needed_bytes + reserve_bytes:
        raise DownloadError(
            f"not enough free disk in {directory}: {free} bytes free, "
            f"{needed_bytes} needed plus {reserve_bytes} reserve"
        )


def _total_size(response, start: int) -> int | None:
    content_range = response.headers.get("Content-Range")
    if content_range and "/" in content_range:
        tail = content_range.rsplit("/", 1)[1]
        if tail.isdigit():
            return int(tail)
    length = response.headers.get("Content-Length")
    return start + int(length) if length and length.isdigit() else None


def download_file(
    url: str,
    destination,
    expected_sha256: str,
    opener: Opener = default_opener,
    reserve_bytes: int = DEFAULT_RESERVE_BYTES,
    max_attempts: int = 5,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> Path:
    """Fetch ``url`` to ``destination`` (resuming ``.part``), verify, and rename into place.

    A file already at ``destination`` with the right checksum is kept and nothing is fetched.
    A wrong checksum deletes the partial file (a resume cannot repair it) and raises.
    """
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = expected_sha256.strip().lower()
    if destination.exists():
        if sha256_file(destination) == expected:
            return destination
        raise DownloadError(f"{destination} exists with a different checksum; remove it first")
    part = destination.with_name(destination.name + ".part")
    last_error: Exception | None = None
    for _ in range(max_attempts):
        start = part.stat().st_size if part.exists() else 0
        try:
            response = opener(url, {"Range": f"bytes={start}-"} if start else {})
        except OSError as exc:
            last_error = exc
            continue
        try:
            status = getattr(response, "status", 200)
            if start and status == 200:
                start = 0  # server ignored the range: restart from zero
                mode = "wb"
            elif status in (200, 206):
                mode = "ab" if start else "wb"
            elif status == 416 and start:
                break  # already have every byte; fall through to verification
            else:
                raise DownloadError(f"unexpected HTTP status {status} for {url}")
            total = _total_size(response, start)
            if total is not None:
                check_free_disk(destination.parent, total - start, reserve_bytes)
            with open(part, mode) as handle:
                received = start
                try:
                    for chunk in iter(lambda: response.read(_CHUNK), b""):
                        handle.write(chunk)
                        received += len(chunk)
                        if on_progress:
                            on_progress(received, total)
                except OSError as exc:
                    last_error = exc
                    continue
            if total is not None and received < total:
                last_error = DownloadError(f"short read: {received} of {total} bytes")
                continue
            break
        finally:
            response.close()
    else:
        raise DownloadError(f"gave up on {url} after {max_attempts} attempts: {last_error}")
    if sha256_file(part) != expected:
        part.unlink(missing_ok=True)
        raise DownloadError(f"checksum mismatch for {url}; partial file removed")
    os.replace(part, destination)
    return destination


def download_export(
    directory,
    include_cover_art: bool = True,
    export: str | None = None,
    opener: Opener = default_opener,
    base_url: str = BASE_URL,
    reserve_bytes: int = DEFAULT_RESERVE_BYTES,
    on_progress: Callable[[int, int | None], None] | None = None,
) -> dict[str, Path]:
    """Download the core archive (and optionally cover-art) of one export into ``directory``."""
    export = export or latest_export(opener, base_url)
    sums = fetch_checksums(export, opener, base_url)
    wanted = [CORE_ARCHIVE] + ([COVER_ART_ARCHIVE] if include_cover_art else [])
    missing = [name for name in wanted if name not in sums]
    if missing:
        raise DownloadError(f"SHA256SUMS for {export} has no entry for: {', '.join(missing)}")
    return {
        name: download_file(f"{base_url}/{export}/{name}", Path(directory) / name, sums[name],
                            opener, reserve_bytes, on_progress=on_progress)
        for name in wanted
    }
