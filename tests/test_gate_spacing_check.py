import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gate_spacing_check", ROOT / "scripts" / "gate_spacing_check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class AnalyzeTests(unittest.TestCase):
    def test_spaced_requests_from_two_processes(self):
        stats = check.analyze([(0.0, "web"), (1.1, "worker"), (2.2, "web"), (3.4, "web")])
        self.assertEqual((stats["count"], stats["gaps"], stats["below_interval"]), (4, 3, 0))
        self.assertAlmostEqual(stats["min_gap"], 1.1)
        self.assertAlmostEqual(stats["median_gap"], 1.1)
        self.assertEqual(stats["per_role"], {"web": 3, "worker": 1})
        self.assertEqual(stats["share"]["worker"], 0.25)
        self.assertEqual(stats["cross_pairs"], 2)

    def test_too_close_pair_is_counted_and_input_order_is_irrelevant(self):
        stats = check.analyze([(2.0, "web"), (0.0, "worker"), (1.0, "web")])
        self.assertEqual(stats["below_interval"], 2)
        self.assertEqual(stats["min_gap"], 1.0)

    def test_empty_and_single_record(self):
        self.assertEqual(check.analyze([])["count"], 0)
        one = check.analyze([(5.0, "web")])
        self.assertIsNone(one["min_gap"])
        self.assertEqual(one["below_interval"], 0)


if __name__ == "__main__":
    unittest.main()
