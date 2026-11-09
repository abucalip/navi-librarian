"""Song peaks for the sound graph: folding, decoding with ffmpeg (skipped when absent), the cache and the route."""
import math
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.waveform as routes
from app.api.dependencies import get_librarian
from intelligence.waveform import BINS, PeakService, PeaksUnavailable, compute_peaks
from intelligence.waveform.peaks import fold


def write_wav(path, seconds=12, loud_from=6.0, rate=8000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        frames = b"".join(
            struct.pack("<h", int((20000 if i / rate >= loud_from else 4000) * math.sin(i * 0.3))) for i in range(seconds * rate))
        w.writeframes(frames)


class Fold(unittest.TestCase):
    def test_scales_to_loudest_and_bins(self):
        out = fold([100] * 1000 + [400] * 1000)
        self.assertEqual(len(out), BINS)
        self.assertEqual(max(out), 65535)
        self.assertEqual(out[0], round(100 / 400 * 65535))

    def test_silence_or_short_is_none(self):
        self.assertIsNone(fold([0] * 2000))
        self.assertIsNone(fold([5] * 10))


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class Decode(unittest.TestCase):
    def test_wav_peaks_follow_loudness(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.wav"
            write_wav(path)
            peaks = compute_peaks(path)
        self.assertEqual(len(peaks), BINS)
        self.assertGreater(peaks[900], peaks[100] * 3)


class Fake:
    def __init__(self, root, data):
        self.MUSIC_DIR, self.DATA_DIR, self.song = Path(root), Path(data), {"id": "s1", "path": "a/b.flac"}

    def api_call(self, method, **params):
        if params["id"] != "s1":
            raise RuntimeError("Navidrome API error 70: not found")
        return {"song": self.song}


class Route(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root, data = Path(self.tmp.name, "music"), Path(self.tmp.name, "data")
        (root / "a").mkdir(parents=True); data.mkdir()
        (root / "a" / "b.flac").write_bytes(b"x")
        self.lib = Fake(root, data)
        self.calls = 0
        def compute(path):
            self.calls += 1
            return [i * 60 for i in range(BINS)]
        routes._service = PeakService(data / "song_peaks.sqlite3", compute=compute, available=lambda: True)
        self.addCleanup(setattr, routes, "_service", None)
        api = FastAPI(); api.include_router(routes.router)
        api.dependency_overrides[get_librarian] = lambda: self.lib
        self.client = TestClient(api)

    def test_pending_then_ready_then_cached(self):
        r = self.client.get("/api/songs/s1/peaks")
        self.assertEqual((r.status_code, r.json()), (202, {"status": "pending"}))
        routes._service.wait_idle()
        r = self.client.get("/api/songs/s1/peaks")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["bins"], BINS)
        self.assertEqual(len(r.json()["peaks"]), BINS)
        self.client.get("/api/songs/s1/peaks")
        self.assertEqual(self.calls, 1)

    def test_changed_file_is_decoded_again(self):
        self.client.get("/api/songs/s1/peaks"); routes._service.wait_idle()
        (self.lib.MUSIC_DIR / "a" / "b.flac").write_bytes(b"longer file")
        self.assertEqual(self.client.get("/api/songs/s1/peaks").status_code, 202)

    def test_unknown_song_and_bad_id(self):
        self.assertEqual(self.client.get("/api/songs/zz/peaks").status_code, 404)
        self.assertEqual(self.client.get("/api/songs/a.b/peaks").status_code, 400)

    def test_path_outside_root_is_404(self):
        self.lib.song = {"id": "s1", "path": "../../etc/passwd"}
        self.assertEqual(self.client.get("/api/songs/s1/peaks").status_code, 404)

    def test_failed_decode_is_404_afterwards(self):
        routes._service._compute = lambda p: (_ for _ in ()).throw(RuntimeError("boom"))
        self.client.get("/api/songs/s1/peaks"); routes._service.wait_idle()
        self.assertEqual(self.client.get("/api/songs/s1/peaks").status_code, 404)

    def test_no_ffmpeg_is_404(self):
        routes._service._available = lambda: False
        self.assertEqual(self.client.get("/api/songs/s1/peaks").status_code, 404)


if __name__ == "__main__":
    unittest.main()
