"""Artwork service: cached index per release group, background builds, and cached image bytes.

* ``index(rgid)``: ``not_loaded`` (and a background build is started or joined) until the group has been
  built; afterwards the merged index from the per-release cache. An expired group is still served and is
  refreshed in the background. Index builds never run inside a client request.
* ``image(image_id, size)``: served from disk; a miss is fetched once (one fetch per image and size at a
  time, one image download at a time overall), validated as an image, stored and returned.

Nothing here reads taste or play data. All traffic goes through the fetchers' shared per-host pacer.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .fetchers import ArtworkFetchers, sniff_image
from .index import (
    EMPTY, OK, UNAVAILABLE, GroupIndex, ReleaseIndex, best_front, build_group_index, to_response,
)
from .store import TTL_EMPTY, TTL_OK, TTL_PARTIAL, ArtworkStore

NOT_LOADED = "not_loaded"
IMAGE_WAIT_SECONDS = 60.0
REFS_TRIED = 3


class ArtworkService:
    def __init__(self, store: ArtworkStore, fetchers: ArtworkFetchers, *, executor: ThreadPoolExecutor | None = None):
        self.store, self.fetchers = store, fetchers
        self._pool = executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="artwork-index")
        self._building: set[str] = set()
        self._building_lock = threading.Lock()
        self._image_slot = threading.Semaphore(1)        # one image download at a time
        self._keyed: dict[tuple[int, str], threading.Lock] = {}
        self._keyed_lock = threading.Lock()

    # ---- index -------------------------------------------------------------------------------
    def index(self, rgid: str, owned_release: str | None = None) -> dict:
        group = self.store.get_group(rgid)
        owned = (owned_release or (group or {}).get("owned_release") or "").lower() or None
        if group is not None and owned and owned != group["owned_release"]:
            self.store.set_owned_release(rgid, owned)
        if group is None:
            self._start(rgid, owned)
            return {"status": NOT_LOADED, "rgid": rgid}
        if not group["fresh"]:
            self._start(rgid, owned)
        if group["status"] == UNAVAILABLE:
            return {"status": UNAVAILABLE, "rgid": rgid}
        return self._response(rgid, group["releases"], owned, group["status"])

    def _response(self, rgid: str, releases: list[dict], owned: str | None, status: str) -> dict:
        """The group view from the per-release cache only; no network."""
        def from_cache(release: str) -> ReleaseIndex:
            return self.store.get_release(release, fresh_only=False) or ReleaseIndex(UNAVAILABLE)
        built = build_group_index(rgid, lambda _r: releases, from_cache, owned_release=owned, time_bound=1e9)
        if status == "partial" and built.truncated_reason is None:
            built.truncated, built.truncated_reason = True, "partial"
        return to_response(built)

    def _start(self, rgid: str, owned: str | None) -> bool:
        with self._building_lock:
            if rgid in self._building:
                return False
            self._building.add(rgid)
        self._pool.submit(self._build, rgid, owned)
        return True

    def building(self, rgid: str) -> bool:
        with self._building_lock:
            return rgid in self._building

    def _build(self, rgid: str, owned: str | None) -> None:
        try:
            self.build_now(rgid, owned)
        except Exception:
            self.store.put_group(rgid, (self.store.get_group(rgid) or {}).get("releases", []), owned,
                                 UNAVAILABLE, self.store.error_ttl(rgid), failed=True)
        finally:
            with self._building_lock:
                self._building.discard(rgid)

    def build_now(self, rgid: str, owned: str | None = None) -> GroupIndex:
        """Build and store one group (runs in the background worker). Fresh per-release answers are reused."""
        docs_box: dict[str, list | None] = {}

        def fetch_releases(_rgid: str):
            docs = self.fetchers.fetch_releases(rgid)
            docs_box["docs"] = docs
            return docs

        def fetch_release(release: str) -> ReleaseIndex:
            res = self.fetchers.fetch_release_index(release)
            self.store.put_release(release, res)
            return res

        cached: dict[str, ReleaseIndex] = {}
        for doc in ((self.store.get_group(rgid) or {}).get("releases") or []):
            hit = self.store.get_release(str(doc.get("id") or "").lower())
            if hit is not None and hit.state in (OK, EMPTY):
                cached[str(doc["id"]).lower()] = hit
        built = build_group_index(rgid, fetch_releases, fetch_release, owned_release=owned, cached=cached)
        docs = docs_box.get("docs")
        if docs is None:
            old = self.store.get_group(rgid)
            if old and old["status"] != UNAVAILABLE:
                return built                       # keep the old good view; it stays expired and is retried later
            self.store.put_group(rgid, [], owned, UNAVAILABLE, self.store.error_ttl(rgid), failed=True)
            return built
        trimmed = [_trim_doc(d) for d in docs]
        if built.status == UNAVAILABLE:
            self.store.put_group(rgid, trimmed, owned, UNAVAILABLE, self.store.error_ttl(rgid), failed=True)
            return built
        if built.truncated_reason in ("time", "partial"):
            status, ttl = "partial", TTL_PARTIAL
        elif built.status == EMPTY:
            status, ttl = EMPTY, TTL_EMPTY
        else:
            status, ttl = OK, TTL_OK
        self.store.put_group(rgid, trimmed, owned, status, ttl)
        self._protect_front(built, owned)
        return built

    def _protect_front(self, built: GroupIndex, owned: str | None) -> None:
        if owned:
            front = best_front(built.images)
            if front is not None:
                self.store.protect([front.image_id])

    # ---- images ------------------------------------------------------------------------------
    def image(self, image_id: int, size: str) -> tuple[str, bytes | None, str]:
        """(state, bytes, content type). State: ``ok``, ``unknown`` (index never seen), ``missing``, ``unavailable``."""
        hit = self.store.get_file(image_id, size)
        if hit is not None:
            return OK, hit[0], _content_type(hit[0])
        refs = self.store.image_refs(image_id)
        if not refs:
            return "unknown", None, ""
        with self._key_lock(image_id, size):
            hit = self.store.get_file(image_id, size)         # another request may have just stored it
            if hit is not None:
                return OK, hit[0], _content_type(hit[0])
            if not self._image_slot.acquire(timeout=IMAGE_WAIT_SECONDS):
                return UNAVAILABLE, None, ""
            try:
                outcome = "missing"
                for release, ext in refs[:REFS_TRIED]:
                    state, body, got_ext = self.fetchers.fetch_image(release, image_id, size, ext)
                    if state == OK:
                        self.store.put_file(image_id, size, got_ext, body, protected=False)
                        return OK, body, _content_type(body)
                    if state == UNAVAILABLE:
                        outcome = UNAVAILABLE
                        break
                return outcome, None, ""
            finally:
                self._image_slot.release()

    def _key_lock(self, image_id: int, size: str) -> threading.Lock:
        with self._keyed_lock:
            return self._keyed.setdefault((image_id, size), threading.Lock())


def _trim_doc(doc: dict) -> dict:
    """Only what ``parse_release`` reads, so the stored release list stays small."""
    return {"id": doc.get("id"), "date": doc.get("date"), "country": doc.get("country"),
            "media": [{"format": m.get("format")} for m in (doc.get("media") or []) if isinstance(m, dict)]}


def _content_type(body: bytes) -> str:
    kind = sniff_image(body)
    return kind[0] if kind else "application/octet-stream"
