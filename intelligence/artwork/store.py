"""Disk cache for the artwork index and image files (docs/artwork.md, slice 1: cache).

One SQLite file plus an ``images/`` folder under the artwork directory:

* ``release_index``: the per-release CAA answer (``ok`` with its raw image list, ``empty``, ``unavailable``),
  with an expiry. The unit cached is the release, so a group rebuild re-fetches only what is stale.
* ``group``: one row per release group: the MusicBrainz release list, the owned release, and an expiry.
* ``image_ref``: which release(s) an image id lives on and its original file extension.
* ``image_file``: one row per stored file (image id and size), with byte count, last access and a
  ``protected`` flag for the best front of an owned album.

The byte budget is shared by every size. Eviction order when over budget: unprotected full-resolution files,
then other unprotected files by least recent use, then protected files by least recent use (only when nothing
else is left). A file bigger than the whole budget is not stored.
"""
from __future__ import annotations

import json
import os
import random
import sqlite3
import threading
import time
from pathlib import Path
from typing import Callable

from .index import EMPTY, OK, UNAVAILABLE, ReleaseIndex

BUDGET_BYTES = 1_500_000_000
DAY = 86400.0
TTL_OK, TTL_EMPTY, TTL_PARTIAL = 30 * DAY, 7 * DAY, 1 * DAY
TTL_ERROR_FIRST, TTL_ERROR_REPEAT = 15 * 60.0, 3600.0
JITTER = 0.10
SIZES = ("thumb", "display", "full")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS release_index (
    release TEXT PRIMARY KEY, state TEXT NOT NULL, images TEXT NOT NULL,
    fetched_at REAL NOT NULL, expires_at REAL NOT NULL, failures INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS grp (
    rgid TEXT PRIMARY KEY, releases TEXT NOT NULL, owned_release TEXT,
    status TEXT NOT NULL, fetched_at REAL NOT NULL, expires_at REAL NOT NULL, failures INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS image_ref (
    image_id INTEGER NOT NULL, release TEXT NOT NULL, ext TEXT NOT NULL, seq INTEGER NOT NULL,
    PRIMARY KEY (image_id, release));
CREATE TABLE IF NOT EXISTS protected_image (image_id INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS image_file (
    image_id INTEGER NOT NULL, size TEXT NOT NULL, ext TEXT NOT NULL, bytes INTEGER NOT NULL,
    last_access REAL NOT NULL, protected INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (image_id, size));
"""


def jittered(ttl: float, rng: Callable[[], float] = random.random) -> float:
    """``ttl`` plus up to 10% so a first fill does not expire all at once."""
    return ttl * (1.0 + JITTER * rng())


class ArtworkStore:
    def __init__(self, root: Path, *, budget: int = BUDGET_BYTES, clock: Callable[[], float] = time.time,
                 rng: Callable[[], float] = random.random):
        self.root = Path(root)
        self.files = self.root / "images"
        self.files.mkdir(parents=True, exist_ok=True)
        self.budget, self._clock, self._rng = budget, clock, rng
        self._lock = threading.RLock()
        self._db = sqlite3.connect(str(self.root / "artwork.sqlite3"), check_same_thread=False)
        self._db.executescript(_SCHEMA)
        self._db.commit()

    def close(self) -> None:
        with self._lock:
            self._db.close()

    # ---- per-release index -------------------------------------------------------------------
    def put_release(self, release: str, res: ReleaseIndex) -> None:
        now = self._clock()
        with self._lock:
            row = self._db.execute("SELECT failures FROM release_index WHERE release=?", (release,)).fetchone()
            failures = 0
            if res.state == OK:
                ttl = TTL_OK
            elif res.state == EMPTY:
                ttl = TTL_EMPTY
            else:
                failures = (row[0] if row else 0) + 1
                ttl = TTL_ERROR_FIRST if failures < 2 else TTL_ERROR_REPEAT
            self._db.execute(
                "INSERT OR REPLACE INTO release_index VALUES (?,?,?,?,?,?)",
                (release, res.state, json.dumps(list(res.images)) if res.state == OK else "[]",
                 now, now + jittered(ttl, self._rng), failures))
            if res.state == OK:
                for seq, raw in enumerate(res.images):
                    try:
                        image_id = int(raw["id"])
                    except (KeyError, TypeError, ValueError):
                        continue
                    self._db.execute("INSERT OR REPLACE INTO image_ref VALUES (?,?,?,?)",
                                     (image_id, release, _ext_of(raw), seq))
            self._db.commit()

    def get_release(self, release: str, *, fresh_only: bool = True) -> ReleaseIndex | None:
        with self._lock:
            row = self._db.execute(
                "SELECT state, images, expires_at FROM release_index WHERE release=?", (release,)).fetchone()
        if row is None or (fresh_only and row[2] <= self._clock()):
            return None
        return ReleaseIndex(row[0], tuple(json.loads(row[1])) if row[0] == OK else ())

    # ---- group -------------------------------------------------------------------------------
    def put_group(self, rgid: str, releases: list[dict], owned_release: str | None, status: str, ttl: float,
                  *, failed: bool = False) -> None:
        now = self._clock()
        with self._lock:
            row = self._db.execute("SELECT failures FROM grp WHERE rgid=?", (rgid,)).fetchone()
            failures = ((row[0] if row else 0) + 1) if failed else 0
            self._db.execute("INSERT OR REPLACE INTO grp VALUES (?,?,?,?,?,?,?)",
                             (rgid, json.dumps(releases), owned_release, status, now,
                              now + jittered(ttl, self._rng), failures))
            self._db.commit()

    def get_group(self, rgid: str) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT releases, owned_release, status, expires_at, failures FROM grp WHERE rgid=?", (rgid,)).fetchone()
        if row is None:
            return None
        return {"releases": json.loads(row[0]), "owned_release": row[1], "status": row[2],
                "fresh": row[3] > self._clock(), "failures": row[4]}

    def error_ttl(self, rgid: str) -> float:
        g = self.get_group(rgid)
        return TTL_ERROR_REPEAT if g and g["failures"] >= 1 else TTL_ERROR_FIRST

    def set_owned_release(self, rgid: str, owned_release: str) -> None:
        with self._lock:
            self._db.execute("UPDATE grp SET owned_release=? WHERE rgid=?", (owned_release, rgid))
            self._db.commit()

    def image_refs(self, image_id: int) -> list[tuple[str, str]]:
        """(release, extension) for each release the image is on, in the order they were seen."""
        with self._lock:
            rows = self._db.execute(
                "SELECT release, ext FROM image_ref WHERE image_id=? ORDER BY seq, release", (image_id,)).fetchall()
        return [(r[0], r[1]) for r in rows]

    # ---- image files -------------------------------------------------------------------------
    def _path(self, image_id: int, size: str, ext: str) -> Path:
        return self.files / f"{int(image_id)}-{size}.{ext}"

    def get_file(self, image_id: int, size: str) -> tuple[bytes, str] | None:
        """(bytes, extension) of a stored file, marking it as used; ``None`` on a miss."""
        with self._lock:
            row = self._db.execute(
                "SELECT ext FROM image_file WHERE image_id=? AND size=?", (image_id, size)).fetchone()
            if row is None:
                return None
            try:
                body = self._path(image_id, size, row[0]).read_bytes()
            except OSError:
                self._db.execute("DELETE FROM image_file WHERE image_id=? AND size=?", (image_id, size))
                self._db.commit()
                return None
            self._db.execute("UPDATE image_file SET last_access=? WHERE image_id=? AND size=?",
                             (self._clock(), image_id, size))
            self._db.commit()
        return body, row[0]

    def put_file(self, image_id: int, size: str, ext: str, body: bytes, *, protected: bool = False) -> bool:
        """Store a file and evict to stay within the budget. ``False`` when it can never fit."""
        if size not in SIZES or len(body) > self.budget:
            return False
        path = self._path(image_id, size, ext)
        tmp = path.with_name(path.name + ".tmp")
        with self._lock:
            tmp.write_bytes(body)
            os.replace(tmp, path)
            protected = protected or self._db.execute(
                "SELECT 1 FROM protected_image WHERE image_id=?", (image_id,)).fetchone() is not None
            self._db.execute("INSERT OR REPLACE INTO image_file VALUES (?,?,?,?,?,?)",
                             (image_id, size, ext, len(body), self._clock(), 1 if protected else 0))
            self._db.commit()
            self._evict(keep=(image_id, size))
        return True

    def protect(self, image_ids: list[int]) -> None:
        """Protect these images (an owned album's best front), now and for sizes stored later."""
        with self._lock:
            self._db.executemany("INSERT OR IGNORE INTO protected_image VALUES (?)", [(i,) for i in image_ids])
            self._db.executemany("UPDATE image_file SET protected=1 WHERE image_id=?", [(i,) for i in image_ids])
            self._db.commit()

    def total_bytes(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COALESCE(SUM(bytes),0) FROM image_file").fetchone()[0]

    def _evict(self, *, keep: tuple[int, str]) -> None:
        total = self.total_bytes()
        if total <= self.budget:
            return
        rows = self._db.execute(
            "SELECT image_id, size, ext, bytes FROM image_file WHERE NOT (image_id=? AND size=?) "
            "ORDER BY protected, (size='full') DESC, last_access, image_id, size", keep).fetchall()
        for image_id, size, ext, nbytes in rows:
            if total <= self.budget:
                break
            try:
                self._path(image_id, size, ext).unlink()
            except FileNotFoundError:
                pass
            except OSError:
                continue
            self._db.execute("DELETE FROM image_file WHERE image_id=? AND size=?", (image_id, size))
            total -= nbytes
        self._db.commit()


def _ext_of(raw: dict) -> str:
    """File extension of the original, from the CAA ``image`` URL; ``jpg`` when it is missing or odd."""
    url = str(raw.get("image") or "")
    ext = url.rsplit(".", 1)[-1].lower() if "." in url.rsplit("/", 1)[-1] else ""
    return ext if ext in ("jpg", "png", "gif", "webp", "pdf") else "jpg"
