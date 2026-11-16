import multiprocessing
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from integrations.provider_gate import GATE_FILE, ProviderGate, default_gate


class FakeTime:
    def __init__(self, now=1_000_000.0):
        self.now = now
        self.slept = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


class _Recorder:
    """Real clock and sleep that remember the granted slot start (clock read + wait)."""

    def __init__(self):
        self.read = 0.0
        self.waited = 0.0

    def clock(self):
        self.read = time.time()
        return self.read

    def sleep(self, seconds):
        self.waited = seconds
        time.sleep(seconds)


def _worker(path, out):
    rec = _Recorder()
    gate = ProviderGate(path, clock=rec.clock, sleep=rec.sleep)
    starts = []
    for _ in range(10):
        rec.waited = 0.0
        gate.reserve("musicbrainz", 60)
        starts.append(rec.read + rec.waited)  # the slot the gate granted, free of wake-up jitter
    out.put(starts)


class ProviderGateTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / GATE_FILE
        self.t = FakeTime()
        self.gate = ProviderGate(self.path, clock=self.t.clock, sleep=self.t.sleep)
        self.addCleanup(self.gate.close)

    def test_first_slot_is_immediate_then_spaced(self):
        self.assertTrue(self.gate.reserve("musicbrainz", 5))
        self.assertEqual(self.t.slept, [])
        self.assertTrue(self.gate.reserve("musicbrainz", 5))
        self.assertAlmostEqual(self.t.slept[0], 1.1)

    def test_refusal_past_max_wait_writes_nothing(self):
        self.gate.reserve("musicbrainz", 5)
        before = self.gate.snapshot()["musicbrainz"]
        self.assertFalse(self.gate.reserve("musicbrainz", 0.5))
        self.assertEqual(self.gate.snapshot()["musicbrainz"], before)
        self.assertEqual(self.t.slept, [])

    def test_penalize_blocks_and_does_not_shrink(self):
        self.gate.penalize("musicbrainz", 30)
        self.assertFalse(self.gate.reserve("musicbrainz", 10))
        self.assertTrue(self.gate.reserve("musicbrainz", 40))
        self.assertAlmostEqual(self.t.slept[0], 30)
        self.gate.penalize("musicbrainz", 5)  # shorter penalty must not shorten the block
        self.assertGreaterEqual(self.gate.snapshot()["musicbrainz"]["blocked_until"], self.t.now)

    def test_long_penalty_is_not_mistaken_for_clock_step(self):
        self.gate.penalize("musicbrainz", 300)
        self.assertTrue(self.gate.reserve("musicbrainz", 400))
        self.assertAlmostEqual(self.t.slept[0], 300)
        self.assertTrue(self.gate.reserve("musicbrainz", 5))
        self.assertAlmostEqual(self.t.slept[1], 1.1)

    def test_clock_step_back_does_not_freeze_provider(self):
        self.gate.reserve("musicbrainz", 5)
        self.t.now -= 3600  # clock stepped back an hour
        self.assertTrue(self.gate.reserve("musicbrainz", 5))
        self.assertEqual(self.t.slept, [])

    def test_clock_step_back_after_penalty_does_not_freeze_provider(self):
        self.gate.penalize("musicbrainz", 30)
        self.t.now -= 3600
        self.assertTrue(self.gate.reserve("musicbrainz", 60))
        self.assertEqual(self.t.slept, [])

    def test_penalty_after_clock_step_back_still_blocks(self):
        self.gate.penalize("musicbrainz", 30)
        self.t.now -= 3600
        self.gate.penalize("musicbrainz", 30)  # a fresh 429 must not vanish into the stale block
        self.assertFalse(self.gate.reserve("musicbrainz", 10))
        self.assertTrue(self.gate.reserve("musicbrainz", 40))
        self.assertAlmostEqual(self.t.slept[0], 30)

    def test_fallback_clock_step_back_does_not_freeze_provider(self):
        bad = ProviderGate(self.path, clock=self.t.clock, sleep=self.t.sleep)
        with mock.patch("integrations.provider_gate.sqlite3.connect",
                        side_effect=__import__("sqlite3").OperationalError("nope")):
            with self.assertLogs("integrations.provider_gate", "WARNING"):
                bad.penalize("musicbrainz", 30)
                bad.reserve("musicbrainz", 60)
                self.t.now -= 7200
                self.assertTrue(bad.reserve("musicbrainz", 1))
                bad.penalize("musicbrainz", 30)
                self.assertFalse(bad.reserve("musicbrainz", 10))
        self.assertEqual(self.t.slept, [30])

    def test_day_counter_rolls_over(self):
        for _ in range(3):
            self.gate.reserve("musicbrainz", 5)
        self.assertEqual(self.gate.snapshot()["musicbrainz"]["day_count"], 3)
        self.t.now += 86400 * 2
        self.gate.reserve("musicbrainz", 5)
        self.assertEqual(self.gate.snapshot()["musicbrainz"]["day_count"], 1)

    def test_unknown_provider_is_counted_not_spaced(self):
        self.gate.reserve("other", 1)
        self.gate.reserve("other", 1)
        self.assertEqual(self.t.slept, [])
        self.assertEqual(self.gate.snapshot()["other"]["day_count"], 2)

    def test_unwritable_file_falls_back_to_double_interval(self):
        bad = ProviderGate(Path(self.path.parent) / "missing" / "x" / GATE_FILE,
                           clock=self.t.clock, sleep=self.t.sleep)
        with mock.patch("integrations.provider_gate.sqlite3.connect",
                        side_effect=__import__("sqlite3").OperationalError("nope")):
            with self.assertLogs("integrations.provider_gate", "WARNING") as logs:
                self.assertTrue(bad.reserve("musicbrainz", 5))
                self.assertTrue(bad.reserve("musicbrainz", 5))
                self.assertTrue(bad.reserve("musicbrainz", 5))
                self.assertFalse(bad.reserve("musicbrainz", 0.1))
        self.assertEqual(len(logs.records), 1)  # warned once
        self.assertAlmostEqual(self.t.slept[0], 2.2)

    def test_default_gate_is_shared_per_directory(self):
        a = default_gate(self.path.parent)
        self.assertIs(a, default_gate(self.path.parent))
        a.close()


class MultiProcessTests(unittest.TestCase):
    def test_two_processes_never_get_slots_closer_than_the_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / GATE_FILE
            ctx = multiprocessing.get_context("spawn")
            out = ctx.Queue()
            procs = [ctx.Process(target=_worker, args=(path, out)) for _ in range(2)]
            for p in procs:
                p.start()
            stamps = sorted(s for _ in procs for s in out.get(timeout=60))
            for p in procs:
                p.join(10)
            self.assertEqual(len(stamps), 20)
            gaps = [b - a for a, b in zip(stamps, stamps[1:])]
            self.assertGreaterEqual(min(gaps), 1.1 - 1e-6)  # granted slots, so no jitter allowance


if __name__ == "__main__":
    unittest.main()
