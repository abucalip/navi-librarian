"""The two provider fetchers for ``build_group_index`` (docs/artwork.md, slice 1).

* ``fetch_releases(rgid)``: one MusicBrainz browse of the group's releases, 100 per page with
  ``inc=media`` (the batch form; there is no per-release lookup). MusicBrainz does not accept
  ``cover-art-archive`` as an ``inc`` value on the release browse (checked 2026-11-10), so releases
  without cover art cannot be skipped up front: every release is asked of the CAA.
* ``fetch_release_index(release)``: one CAA index per release (the CAA has no batch or group form, the
  only single-lookup fallback here). 200 is ``ok``, 404 is ``empty``, anything else is ``unavailable``.

All traffic goes through one ``HostPacer``: at most one request start per second per host, and after a
429 or 503 the host is closed (no request is sent) until ``Retry-After`` or 60 s, doubling to 15 minutes.
A closed host answers ``unavailable``; it is never read as "no images". Index JSON may only be redirected
to the CAA and archive.org hosts. No image bytes are fetched here.
"""
from __future__ import annotations

import json
import threading
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .index import EMPTY, OK, UNAVAILABLE, ReleaseIndex

USER_AGENT = "Discair/1.0 (personal music discovery)"
MB_BASE = "https://musicbrainz.org/ws/2"
CAA_BASE = "https://coverartarchive.org"
PACE_SECONDS = 1.0
BACKOFF_START, BACKOFF_MAX = 60.0, 900.0
PAGE = 100
MAX_PAGES = 5               # 500 releases; the group cap is 60, so this only stops a runaway loop
MAX_BYTES = 8 * 1024 * 1024
MAX_IMAGE_BYTES = {"thumb": 2 * 1024 * 1024, "display": 4 * 1024 * 1024, "full": 100 * 1024 * 1024}
SIZE_SUFFIX = {"thumb": "-250.jpg", "display": "-500.jpg", "full": None}   # CAA serves 250, 500, 1200 and the original
IMAGE_EXTENSIONS = ("jpg", "png", "gif", "webp", "pdf")
TIMEOUT = 30
ALLOWED_REDIRECT_HOSTS = ("coverartarchive.org", "archive.org")


def _allowed_host(host: str) -> bool:
    host = (host or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_REDIRECT_HOSTS)


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or not _allowed_host(parsed.hostname or ""):
            raise HTTPError(newurl, 403, "redirect to a host that is not allowed", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HostPacer:
    """Per-host start pacing and 429/503 back-off, shared by every artwork request."""

    def __init__(self, *, clock=time.monotonic, sleep=time.sleep, pace: float = PACE_SECONDS):
        self._clock, self._sleep, self._pace = clock, sleep, pace
        self._lock = threading.Lock()
        self._last: dict[str, float] = {}
        self._closed_until: dict[str, float] = {}
        self._backoff: dict[str, float] = {}

    def acquire(self, host: str) -> bool:
        """Wait for this host's turn. ``False`` (no wait) while the host is closed after a 429/503."""
        with self._lock:
            now = self._clock()
            if self._closed_until.get(host, 0.0) > now:
                return False
            wait = self._pace - (now - self._last.get(host, -self._pace))
            if wait > 0:
                self._sleep(wait)
            self._last[host] = self._clock()
            return True

    def throttled(self, host: str, retry_after: float | None) -> None:
        with self._lock:
            step = min(max(self._backoff.get(host, 0.0) * 2, BACKOFF_START), BACKOFF_MAX)
            self._backoff[host] = step
            delay = min(retry_after, BACKOFF_MAX) if retry_after and retry_after > 0 else step
            self._closed_until[host] = self._clock() + delay

    def succeeded(self, host: str) -> None:
        with self._lock:
            self._backoff.pop(host, None)


Opener = Callable[[Request], tuple[int, bytes, float | None]]


def _urllib_open(req: Request) -> tuple[int, bytes, float | None]:
    """(status, body, Retry-After seconds). Network errors and bad redirects give status 0 or the HTTP code."""
    try:
        with build_opener(_SafeRedirect).open(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(MAX_BYTES + 1), None
    except HTTPError as exc:
        retry = exc.headers.get("Retry-After") if exc.headers else None
        return exc.code, b"", float(retry) if retry and retry.strip().isdigit() else None
    except (URLError, TimeoutError, OSError):
        return 0, b"", None


ImageOpener = Callable[[Request, int], tuple[int, bytes, float | None]]


def _urllib_open_image(req: Request, limit: int) -> tuple[int, bytes, float | None]:
    """Like ``_urllib_open`` but reads at most ``limit + 1`` bytes, so an oversize body is detectable."""
    try:
        with build_opener(_SafeRedirect).open(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read(limit + 1), None
    except HTTPError as exc:
        retry = exc.headers.get("Retry-After") if exc.headers else None
        return exc.code, b"", float(retry) if retry and retry.strip().isdigit() else None
    except (URLError, TimeoutError, OSError):
        return 0, b"", None


def sniff_image(body: bytes) -> tuple[str, str] | None:
    """(content type, extension) from the file's own signature; ``None`` when it is not a supported image.

    PDF is kept (booklet scans are often PDFs); every other format is rejected. The upstream
    Content-Type is never trusted.
    """
    if body[:5] == b"%PDF-":
        return "application/pdf", "pdf"
    if body[:3] == b"\xff\xd8\xff":
        return "image/jpeg", "jpg"
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png", "png"
    if body[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", "gif"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp", "webp"
    return None


def image_url(release: str, image_id: int, size: str, ext: str = "jpg") -> str | None:
    if size not in SIZE_SUFFIX:
        return None
    suffix = SIZE_SUFFIX[size] or "." + (ext if ext in IMAGE_EXTENSIONS else "jpg")
    return f"{CAA_BASE}/release/{release}/{int(image_id)}{suffix}"


class ArtworkFetchers:
    def __init__(self, *, pacer: HostPacer | None = None, opener: Opener = _urllib_open,
                 image_opener: ImageOpener = _urllib_open_image):
        self.pacer = pacer or HostPacer()
        self._open = opener
        self._open_image = image_opener

    def fetch_image(self, release: str, image_id: int, size: str, ext: str = "jpg") -> tuple[str, bytes, str]:
        """(state, bytes, extension). State is ``ok``, ``missing`` (404 or not an image) or ``unavailable``.

        Only the CAA URL is built here and redirects may only go to the CAA and archive.org hosts. The body
        must be within the size's byte limit and must sniff as an image, otherwise it is ``missing`` (bad
        bytes) or ``unavailable`` (too large: not stored).
        """
        url = image_url(release, image_id, size, ext)
        if url is None:
            return "missing", b"", ""
        host = urlparse(url).hostname or ""
        if not self.pacer.acquire(host):
            return UNAVAILABLE, b"", ""
        limit = MAX_IMAGE_BYTES[size]
        status, body, retry = self._open_image(Request(url, headers={"User-Agent": USER_AGENT, "Accept": "image/*"}), limit)
        if status in (429, 503):
            self.pacer.throttled(host, retry)
            return UNAVAILABLE, b"", ""
        if status == 0 or status >= 500:
            return UNAVAILABLE, b"", ""
        self.pacer.succeeded(host)
        if status != 200:
            return "missing", b"", ""
        if len(body) > limit:
            return UNAVAILABLE, b"", ""
        kind = sniff_image(body)
        if kind is None or (kind[1] == "pdf" and size != "full"):     # a PDF is only ever the original file
            return "missing", b"", ""
        return OK, body, kind[1]

    def _json(self, url: str) -> tuple[int, dict | None]:
        host = urlparse(url).hostname or ""
        if not self.pacer.acquire(host):
            return 0, None
        status, body, retry = self._open(Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}))
        if status in (429, 503):
            self.pacer.throttled(host, retry)
            return status, None
        if status == 200 and len(body) <= MAX_BYTES:
            self.pacer.succeeded(host)
            try:
                data = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, ValueError):
                return 0, None
            return 200, data if isinstance(data, dict) else None
        if status == 200:
            return 0, None
        self.pacer.succeeded(host)
        return status, None

    def fetch_releases(self, rgid: str) -> list[dict] | None:
        """Every release of the group (paged), or ``None`` if any page failed."""
        out: list[dict] = []
        for page in range(MAX_PAGES):
            query = urlencode({"release-group": rgid, "inc": "media", "limit": PAGE, "offset": page * PAGE, "fmt": "json"})
            status, data = self._json(f"{MB_BASE}/release?{query}")
            if data is None or not isinstance(data.get("releases"), list):
                return None
            out += [r for r in data["releases"] if isinstance(r, dict)]
            if (page + 1) * PAGE >= int(data.get("release-count") or 0):
                break
        return out

    def fetch_release_index(self, release: str) -> ReleaseIndex:
        status, data = self._json(f"{CAA_BASE}/release/{release}")
        if status == 404:
            return ReleaseIndex(EMPTY)
        if status == 200 and data is not None and isinstance(data.get("images"), list):
            return ReleaseIndex(OK, tuple(i for i in data["images"] if isinstance(i, dict)))
        return ReleaseIndex(UNAVAILABLE)
