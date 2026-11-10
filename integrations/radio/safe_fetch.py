"""Outbound fetches for station logos: http(s) only, no private, loopback or link-local targets
(checked again after every redirect), a size cap, a timeout, and no credentials or proxies."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlsplit

import httpx

USER_AGENT = "Discair-radio/1.0"
MAX_REDIRECTS = 3
TIMEOUT = httpx.Timeout(5.0)
IMAGE_MAX_BYTES = 2 * 1024 * 1024
PAGE_MAX_BYTES = 512 * 1024
REDIRECT_STATUSES = {301, 302, 303, 307, 308}

# Image types accepted for a logo, by magic bytes. SVG is refused: it can carry script.
_SIGNATURES = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"\x00\x00\x01\x00", "image/x-icon"),
)


class UnsafeURL(ValueError):
    """The address is not an http(s) public address; never fetched."""


class FetchFailed(Exception):
    """The fetch did not produce usable content. Callers fall through to the next source."""


def resolve_host(host: str) -> list[str]:
    """Every address a host name resolves to. Replaced in tests so no network is needed."""
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


def check_url(url: str) -> None:
    parts = urlsplit(url or "")
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise UnsafeURL("only public http(s) addresses are fetched")
    if parts.username or parts.password:
        raise UnsafeURL("addresses with credentials are not fetched")
    try:
        addresses = resolve_host(parts.hostname)
    except OSError as exc:
        raise FetchFailed("host did not resolve") from exc
    if not addresses:
        raise FetchFailed("host did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%", 1)[0])
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
            ip = ip.ipv4_mapped
        if not ip.is_global:
            raise UnsafeURL("the address points at a private or local network")


def fetch(url: str, *, accept: tuple[str, ...], max_bytes: int, client: httpx.Client | None = None,
          headers: dict[str, str] | None = None) -> tuple[bytes, str, str]:
    """Return (body, media type, final URL). Raises FetchFailed for anything unusable."""
    own_client = client is None
    if own_client:
        client = httpx.Client(timeout=TIMEOUT, follow_redirects=False, trust_env=False)
    request_headers = {"User-Agent": USER_AGENT, "Accept": ", ".join(accept) + ", */*;q=0.1"}
    request_headers.update(headers or {})
    current = url
    try:
        for _ in range(MAX_REDIRECTS + 1):
            check_url(current)
            try:
                with client.stream("GET", current, headers=request_headers) as response:
                    if response.status_code in REDIRECT_STATUSES and response.headers.get("location"):
                        current = urljoin(current, response.headers["location"])
                        continue
                    if response.status_code != 200:
                        raise FetchFailed(f"status {response.status_code}")
                    media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if not any(media_type.startswith(prefix) for prefix in accept):
                        raise FetchFailed("unexpected content type")
                    declared = response.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > max_bytes:
                        raise FetchFailed("too large")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > max_bytes:
                            raise FetchFailed("too large")
                    return bytes(body), media_type, current
            except httpx.HTTPError as exc:
                raise FetchFailed("request failed") from exc
        raise FetchFailed("too many redirects")
    finally:
        if own_client:
            client.close()


def fetch_image(url: str, client: httpx.Client | None = None) -> tuple[bytes, str]:
    """A public image URL as (bytes, media type), with the type taken from the file's own bytes."""
    body, _, _ = fetch(url, accept=("image/",), max_bytes=IMAGE_MAX_BYTES, client=client)
    media_type = sniff_image(body)
    if media_type is None:
        raise FetchFailed("not a supported image")
    return body, media_type


def sniff_image(data: bytes) -> str | None:
    for signature, media_type in _SIGNATURES:
        if data.startswith(signature):
            return media_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None
