"""Peaks of one song for the sound graph (read-only).

``ffmpeg`` decodes the file to 8 kHz mono 16-bit samples on a pipe; the loudest sample of every 10 ms window is kept and
those windows are folded into :data:`BINS` bins, each 0..65535 (the loudest bin is scaled to full height, so quiet songs
still draw). Files are opened only under the music root (``resolve_under_root``), the audio never leaves the server and the
error text never carries a path. Results are kept in a small SQLite file keyed by song id and checked against the file's
size and modification time, so a replaced file is decoded again.
"""
from __future__ import annotations

import array
import sqlite3
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from intelligence.health.audio import AudioCheckError, ffmpeg_available, resolve_under_root

BINS = 1000
RATE = 8000
WINDOW = RATE // 100  # 10 ms
CHUNK = WINDOW * 2 * 512  # bytes per read
TIMEOUT = 600.0


class PeaksUnavailable(Exception):
    """The song has no readable file or ffmpeg is missing."""


def _command(path: Path, binary: str = "ffmpeg") -> list[str]:
    return [binary, "-nostdin", "-v", "error", "-i", f"file:{path}", "-vn", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"]


def fold(windows: list[int], bins: int = BINS) -> list[int] | None:
    """Windows of 0..32768 folded to ``bins`` values of 0..65535, scaled to the loudest; None for silence or too little audio."""
    if len(windows) < bins or max(windows, default=0) <= 0:
        return None
    top = max(windows)
    out = []
    for i in range(bins):
        lo, hi = i * len(windows) // bins, (i + 1) * len(windows) // bins
        out.append(round(max(windows[lo:hi]) / top * 65535))
    return out


def compute_peaks(path: Path, *, binary: str = "ffmpeg", timeout: float = TIMEOUT) -> list[int] | None:
    """Decode ``path`` and return the peaks, or None when the file is silent or shorter than 10 s."""
    try:
        proc = subprocess.Popen(_command(path, binary), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except OSError as exc:
        raise AudioCheckError(f"ffmpeg could not start: {exc.__class__.__name__}") from exc
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    windows: list[int] = []
    carry = b""
    try:
        while True:
            data = proc.stdout.read(CHUNK)
            if not data:
                break
            data = carry + data
            usable = len(data) - len(data) % (WINDOW * 2)
            carry = data[usable:]
            samples = array.array("h")
            samples.frombytes(data[:usable])
            for i in range(0, len(samples), WINDOW):
                block = samples[i:i + WINDOW]
                windows.append(max(max(block), -min(block)))
        if proc.wait() != 0:
            raise AudioCheckError("ffmpeg could not decode the file")
    finally:
        timer.cancel()
        if proc.poll() is None:
            proc.kill()
        proc.stdout.close()
    return fold(windows)


class PeakService:
    """Cache plus a small background pool. ``get`` never blocks on a decode: it answers ready peaks or 'pending'."""

    def __init__(self, db_path: Path, *, compute: Callable[[Path], list[int] | None] = compute_peaks, workers: int = 2,
                 available: Callable[[], bool] = ffmpeg_available):
        self.db_path = Path(db_path)
        self._compute = compute
        self._available = available
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="peaks")
        self._lock = threading.Lock()
        self._running: set[str] = set()
        self._failed: dict[str, tuple] = {}
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS peaks (song_id TEXT PRIMARY KEY, size INTEGER, mtime_ns INTEGER, data BLOB)")

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def _stored(self, song_id: str, sig: tuple) -> list[int] | None:
        with self._connect() as db:
            row = db.execute("SELECT size, mtime_ns, data FROM peaks WHERE song_id=?", (song_id,)).fetchone()
        if not row or (row[0], row[1]) != sig:
            return None
        a = array.array("H")
        a.frombytes(row[2])
        return list(a)

    def _store(self, song_id: str, sig: tuple, peaks: list[int]) -> None:
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO peaks VALUES (?,?,?,?)", (song_id, sig[0], sig[1], array.array("H", peaks).tobytes()))

    def _work(self, song_id: str, path: Path, sig: tuple) -> None:
        try:
            peaks = self._compute(path)
            if peaks:
                self._store(song_id, sig, peaks)
            else:
                self._failed[song_id] = sig
        except Exception:
            self._failed[song_id] = sig
        finally:
            with self._lock:
                self._running.discard(song_id)

    def get(self, song_id: str, root, relative_path: str | None) -> list[int] | None:
        """Peaks when ready, None while a decode runs; PeaksUnavailable when there is nothing to show (no file, no ffmpeg, silent or failed)."""
        try:
            path = resolve_under_root(root, relative_path)
            st = path.stat()
        except (AudioCheckError, OSError) as exc:
            raise PeaksUnavailable("no readable file") from exc
        sig = (st.st_size, st.st_mtime_ns)
        ready = self._stored(song_id, sig)
        if ready:
            return ready
        if self._failed.get(song_id) == sig:
            raise PeaksUnavailable("no peaks for this file")
        if not self._available():
            raise PeaksUnavailable("ffmpeg is not installed")
        with self._lock:
            if song_id not in self._running:
                self._running.add(song_id)
                self._pool.submit(self._work, song_id, path, sig)
        return None

    def wait_idle(self, timeout: float = 5.0) -> None:
        """Test helper: wait until no decode is running."""
        import time
        end = time.monotonic() + timeout
        while self._running and time.monotonic() < end:
            time.sleep(0.01)
