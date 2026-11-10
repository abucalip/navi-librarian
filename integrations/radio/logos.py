"""Station logos. Order: owner override, Radio Browser favicon, homepage icon, generated tile.

Each station is resolved once. A found logo is cached as a file in the data directory; a miss is
remembered for NEGATIVE_TTL_SECONDS so a dead logo is not fetched on every list call. Failures in
any source fall through to the next one and never reach the client as an error.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urljoin, urlsplit

import httpx

from integrations.radio import safe_fetch
from integrations.radio.tile import tile_png

LOGO_SIZES = (128, 512)
MAX_UPLOAD_BYTES = safe_fetch.IMAGE_MAX_BYTES
NEGATIVE_TTL_SECONDS = 7 * 24 * 3600
RADIO_BROWSER_BASE = "https://all.api.radio-browser.info"
_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")
_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()
OVERRIDE = "override"
GENERATED = "generated"


@dataclass(frozen=True)
class Logo:
    """A cached image file, or None for the generated tile."""
    path: Path | None
    media_type: str | None


def logo_dir(data_dir: Path | str, station_id: str) -> Path:
    if not _ID_PATTERN.fullmatch(station_id or ""):
        raise ValueError("invalid station id")
    return Path(data_dir) / "radio-logos" / station_id


def _lock_for(station_id: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(station_id, threading.Lock())


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_bytes(data)
    os.replace(temp, path)


def _remove(data_dir: Path | str, station_id: str) -> None:
    folder = logo_dir(data_dir, station_id)
    for name in ("logo.bin", "logo.bin.tmp"):
        (folder / name).unlink(missing_ok=True)


def cached_logo(store, data_dir, station_id: str) -> Logo | None:
    """The cached file if one was resolved and is still on disk; None means resolve again."""
    state = store.get_logo_state(station_id)
    if state and state["status"] == "found":
        path = logo_dir(data_dir, station_id) / "logo.bin"
        if path.exists():
            return Logo(path, state["media_type"])
    return None


def resolve(station: dict, store, data_dir: Path | str, client: httpx.Client | None = None,
            now: float | None = None) -> Logo:
    """Resolve a station's logo once and cache it. `station` has id, name, stream_url (original
    address), and homepage_url. Never raises for a failed source."""
    now = time.time() if now is None else now
    station_id = station["id"]
    with _lock_for(station_id):
        cached = cached_logo(store, data_dir, station_id)
        if cached:
            return cached
        state = store.get_logo_state(station_id)
        if state and state["status"] == "none" and state["expires_at"] and state["expires_at"] > now:
            return Logo(None, None)
        found = _find_remote(station, client)
        if found is not None:
            body, media_type, source = found
            _write_atomic(logo_dir(data_dir, station_id) / "logo.bin", body)
            store.save_logo_state(station_id, source, "found", media_type, now, None)
            return Logo(logo_dir(data_dir, station_id) / "logo.bin", media_type)
        store.save_logo_state(station_id, GENERATED, "none", None, now, now + NEGATIVE_TTL_SECONDS)
        return Logo(None, None)


def image_bytes(station: dict, store, data_dir: Path | str, size: int,
                client: httpx.Client | None = None) -> tuple[bytes, str]:
    """The logo for a size in LOGO_SIZES: the cached image as stored, else a generated PNG tile."""
    logo = resolve(station, store, data_dir, client)
    if logo.path is not None:
        return logo.path.read_bytes(), logo.media_type
    return tile_png(station["name"], size), "image/png"


def set_override(store, data_dir: Path | str, station_id: str, body: bytes, now: float | None = None) -> str:
    """Save the owner's own image. Returns its media type. Raises ValueError for anything else."""
    media_type = safe_fetch.sniff_image(body)
    if media_type is None:
        raise ValueError("Upload a PNG, JPEG, GIF, WebP or ICO image.")
    if len(body) > MAX_UPLOAD_BYTES:
        raise ValueError("The image is too large.")
    now = time.time() if now is None else now
    with _lock_for(station_id):
        _write_atomic(logo_dir(data_dir, station_id) / "logo.bin", body)
        store.save_logo_state(station_id, OVERRIDE, "found", media_type, now, None)
    return media_type


def clear(store, data_dir: Path | str, station_id: str) -> None:
    """Forget the stored logo (the owner's or a fetched one). The next request resolves again."""
    with _lock_for(station_id):
        _remove(data_dir, station_id)
        store.delete_logo_state(station_id)


# ---- remote sources ---------------------------------------------------------------------

def _find_remote(station: dict, client: httpx.Client | None) -> tuple[bytes, str, str] | None:
    own = client is None
    if own:
        client = httpx.Client(timeout=safe_fetch.TIMEOUT, follow_redirects=False, trust_env=False)
    try:
        for source, finder in (("radio_browser", _radio_browser_images), ("homepage", _homepage_images)):
            for candidate in _candidates(finder, station, client):
                try:
                    body, media_type = safe_fetch.fetch_image(candidate, client)
                    return body, media_type, source
                except Exception:
                    continue
        return None
    finally:
        if own:
            client.close()


def _candidates(finder, station: dict, client: httpx.Client):
    try:
        yield from finder(station, client)
    except Exception:
        return


def _json(url: str, client: httpx.Client):
    body, _, _ = safe_fetch.fetch(url, accept=("application/json",), max_bytes=1024 * 1024, client=client)
    return json.loads(body.decode("utf-8"))


def _radio_browser_images(station: dict, client: httpx.Client):
    """Favicons from radio-browser.info: one search by stream address, then by name if that finds nothing."""
    seen = set()
    lookups = []
    if station.get("stream_url"):
        lookups.append(f"{RADIO_BROWSER_BASE}/json/stations/byurl/{quote(station['stream_url'], safe='')}")
    if station.get("name"):
        lookups.append(f"{RADIO_BROWSER_BASE}/json/stations/byname/{quote(station['name'], safe='')}")
    for url in lookups:
        try:
            entries = _json(url, client)
        except Exception:
            continue
        if not isinstance(entries, list):
            continue
        for entry in entries:
            favicon = str((entry or {}).get("favicon") or "").strip()
            if favicon.startswith(("http://", "https://")) and favicon not in seen:
                seen.add(favicon)
                yield favicon


class _HeadIcons(HTMLParser):
    """Collects apple-touch-icon links and og:image tags, in document order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.apple: list[str] = []
        self.og: list[str] = []

    def handle_starttag(self, tag, attrs):
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag == "link" and "apple-touch-icon" in values.get("rel", "").lower() and values.get("href"):
            self.apple.append(values["href"])
        if tag == "meta" and values.get("property", "").lower() == "og:image" and values.get("content"):
            self.og.append(values["content"])


def _homepage_images(station: dict, client: httpx.Client):
    """Homepage icons in the order apple-touch-icon, og:image, then /favicon.ico at the homepage's origin."""
    homepage = str(station.get("homepage_url") or "").strip()
    parts = urlsplit(homepage)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        return
    icons = _HeadIcons()
    base = homepage
    try:
        body, _, final = safe_fetch.fetch(homepage, accept=("text/html", "application/xhtml"),
                                          max_bytes=safe_fetch.PAGE_MAX_BYTES, client=client)
        base = final
        icons.feed(body.decode("utf-8", errors="replace"))
    except Exception:
        pass
    for href in icons.apple + icons.og:
        yield urljoin(base, href)
    yield urljoin(homepage, "/favicon.ico")
