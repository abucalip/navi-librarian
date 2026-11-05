import subprocess
import tempfile
import unittest
from pathlib import Path

from intelligence.health import build_report
from intelligence.health.audio import (
    AudioCheckError, AudioMeasurement, HF_SILENT_DBFS, build_command, ffmpeg_available,
    findings_for, hf_cutoff_for, measure_file, parse_output, resolve_under_root,
)
from intelligence.health.audio_job import findings_from_progress, make_job, with_audio
from intelligence.ingest.navidrome import NormalizedTrack
from intelligence.jobs import run_job, status
from intelligence.store import open_store

LOG = """\
[astats@hf @ 0x1] Overall
[astats@hf @ 0x1] RMS level dB: -inf
[ebur128@lufs @ 0x2] Summary:

  Integrated loudness:
    I:         -9.5 LUFS
  Loudness range:
    LRA:         4.0 LU
  True peak:
    Peak:       0.3 dBFS
[astats@full @ 0x3] Channel: 1
[astats@full @ 0x3] Peak level dB: -3.00
[astats@full @ 0x3] Peak count: 1
[astats@full @ 0x3] Overall
[astats@full @ 0x3] Peak level dB: 0.00
[astats@full @ 0x3] RMS level dB: -12.0
[astats@full @ 0x3] Peak count: 120.000000
"""


class ParseTests(unittest.TestCase):
    def test_parse_reads_overall_not_channel_values(self):
        m = parse_output(LOG, "t1", 16000)
        self.assertEqual((m.peak_dbfs, m.peak_count), (0.0, 120))
        self.assertEqual((m.integrated_lufs, m.loudness_range_lu, m.true_peak_dbfs), (-9.5, 4.0, 0.3))
        self.assertEqual(m.hf_rms_dbfs, float("-inf"))

    def test_garbage_gives_all_none(self):
        m = parse_output("nothing useful", "t1", 16000)
        self.assertIsNone(m.peak_dbfs)
        self.assertIsNone(m.hf_rms_dbfs)
        self.assertEqual(findings_for(m, "flac"), [])

    def test_as_dict_round_trips_infinity(self):
        m = parse_output(LOG, "t1", 16000)
        again = AudioMeasurement.from_dict(m.as_dict())
        self.assertEqual(again, m)


class FindingTests(unittest.TestCase):
    def m(self, **over):
        base = dict(track_id="t", peak_dbfs=-1.0, peak_count=1, hf_cutoff_hz=16000, hf_rms_dbfs=-60.0)
        base.update(over)
        return AudioMeasurement(**base)

    def test_clean_track_has_no_findings(self):
        self.assertEqual(findings_for(self.m(), "flac"), [])

    def test_clipping_needs_many_peaks(self):
        self.assertEqual(findings_for(self.m(peak_dbfs=0.0, peak_count=3), "flac"), [])
        found = findings_for(self.m(peak_dbfs=0.0, peak_count=500), "flac")
        self.assertEqual([f.check for f in found], ["clipping"])

    def test_transcode_flag_only_for_lossless(self):
        silent = self.m(hf_rms_dbfs=HF_SILENT_DBFS - 5)
        self.assertEqual([f.check for f in findings_for(silent, "flac")], ["suspected_upsampled_or_transcoded"])
        self.assertEqual(findings_for(silent, "mp3"), [])
        self.assertEqual(findings_for(self.m(hf_rms_dbfs=-70.0), "flac"), [])

    def test_digital_silence_is_flagged_and_json_safe(self):
        f = findings_for(self.m(hf_rms_dbfs=float("-inf")), "FLAC")[0]
        self.assertTrue(f.detail["hf_silent"])
        self.assertIsNone(f.detail["hf_rms_dbfs"])

    def test_hires_wording(self):
        f = findings_for(self.m(hf_cutoff_hz=22500, hf_rms_dbfs=-100.0), "flac")[0]
        self.assertIn("upsampled", f.message)

    def test_cutoff_by_rate(self):
        self.assertIsNone(hf_cutoff_for(22050))
        self.assertEqual(hf_cutoff_for(44100), 16000)
        self.assertEqual(hf_cutoff_for(96000), 22500)


class PathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "music"
        (self.root / "a").mkdir(parents=True)
        (self.root / "a" / "t.flac").write_bytes(b"x")
        self.outside = Path(self.tmp.name) / "secret.flac"
        self.outside.write_bytes(b"x")

    def test_relative_path_resolves(self):
        self.assertEqual(resolve_under_root(self.root, "a/t.flac"), (self.root / "a" / "t.flac").resolve())

    def test_refuses_traversal_symlink_absolute_outside_and_missing(self):
        (self.root / "link.flac").symlink_to(self.outside)
        for bad in ("../secret.flac", "link.flac", str(self.outside), "a/none.flac", "", "a", None):
            with self.assertRaises(AudioCheckError, msg=repr(bad)):
                resolve_under_root(self.root, bad)

    def test_measure_file_uses_runner_and_hides_path(self):
        seen = {}

        def runner(cmd, timeout):
            seen["cmd"] = cmd
            return LOG

        m = measure_file(self.root, "a/t.flac", "t1", 44100, runner=runner)
        self.assertEqual(m.peak_count, 120)
        self.assertEqual(seen["cmd"][0], "ffmpeg")
        self.assertIn("-f", seen["cmd"])
        self.assertEqual(seen["cmd"][-3:], ["-f", "null", "-"])
        try:
            measure_file(self.root, "a/none.flac", "t1", runner=runner)
        except AudioCheckError as exc:
            self.assertNotIn("none.flac", str(exc))

    def test_command_has_no_output_file(self):
        cmd = build_command(Path("/m/x.flac"), None)
        self.assertIn("file:/m/x.flac", cmd)
        self.assertNotIn("-y", cmd)


class JobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = open_store(Path(self.tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)
        self.tracks = [
            NormalizedTrack(navidrome_id=f"t{i}", path=f"{i}.flac", suffix="flac", sampling_rate=44100)
            for i in (1, 2, 3)
        ]
        self.calls = []

    def measure(self, root, path, tid, rate):
        self.calls.append(tid)
        if tid == "t2":
            raise AudioCheckError("file not found")
        return AudioMeasurement(tid, peak_dbfs=0.0, peak_count=900, hf_cutoff_hz=16000, hf_rms_dbfs=-120.0)

    def test_resumes_after_budget_and_records_errors(self):
        job = make_job(self.tracks, "/m", measure=self.measure)
        first = run_job(self.db, "health_audio", job, max_items=1, resource="health")
        self.assertEqual(first.state, "queued")
        second = run_job(self.db, "health_audio", job, resource="health")
        self.assertEqual(second.state, "succeeded")
        self.assertEqual(self.calls, ["t1", "t2", "t3"])
        progress = status(self.db, "health_audio")["progress"]
        self.assertEqual(sorted(progress["measured"]), ["t1", "t3"])
        self.assertEqual(progress["errors"], {"t2": "file not found"})

    def test_findings_merge_into_report(self):
        run_job(self.db, "health_audio", make_job(self.tracks, "/m", measure=self.measure))
        progress = status(self.db, "health_audio")["progress"]
        findings = findings_from_progress(progress, self.tracks)
        self.assertEqual(len(findings), 4)
        report = with_audio(build_report([]), findings)
        self.assertEqual(report.counts["clipping"], 2)
        self.assertEqual(report.not_checked, ("measured_loudness",))
        self.assertEqual(build_report([]).counts.get("clipping"), None)


@unittest.skipUnless(ffmpeg_available(), "ffmpeg not installed")
class RealFfmpegTests(unittest.TestCase):
    def test_lowpassed_flac_is_flagged_and_full_band_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, src in (("low", "sine=f=1000:d=2:r=44100"), ("full", "anoisesrc=d=2:r=44100:a=0.2")):
                subprocess.run(
                    ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", src, "-af", "lowpass=f=12000" if name == "low" else "volume=1",
                     f"{tmp}/{name}.flac"], check=True)
            low = measure_file(tmp, "low.flac", "low", 44100)
            full = measure_file(tmp, "full.flac", "full", 44100)
        self.assertEqual([f.check for f in findings_for(low, "flac")], ["suspected_upsampled_or_transcoded"])
        self.assertEqual(findings_for(full, "flac"), [])
        self.assertIsNotNone(low.integrated_lufs)


if __name__ == "__main__":
    unittest.main()
