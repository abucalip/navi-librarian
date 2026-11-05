"""The /api/insights body and the Phase 3 exit rules (docs/SERVER_V2_CONTRACT.md, ServerV2.md Phase 3)."""
import json
import re
import tempfile
import unittest
from pathlib import Path

from intelligence.api import INSIGHT_LISTERS, build_capabilities, build_insights_body
from intelligence.insights import (
    ComparisonSet, SeriesConfig, SetItem, find_series_progress, save_series,
)
from intelligence.insights import outcomes
from intelligence.insights import series_completion as sc
from intelligence.store import open_store

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "intelligence" / "contract-fixtures"


def seed(db, count):
    sets = [ComparisonSet(f"s{n}", "series", f"S{n}", tuple(SetItem(f"s{n}-{i}", f"T{i}", 2000 + i) for i in range(4)))
            for n in range(count)]
    save_series(db, find_series_progress(sets, [f"s{n}-0" for n in range(count)], SeriesConfig()), now=1.0)


class InsightsBodyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.db = open_store(Path(tmp.name) / "i.sqlite3")
        self.addCleanup(self.db.close)

    def test_every_lens_is_listed_and_off_by_default(self):
        seed(self.db, 2)
        body = build_insights_body(self.db)
        self.assertEqual(sorted(body["lenses"]), sorted(INSIGHT_LISTERS))
        for lens in body["lenses"].values():
            self.assertEqual(lens, {"enabled": False, "cards": []})

    def test_enabled_lens_returns_its_saved_cards_only(self):
        seed(self.db, 2)
        body = build_insights_body(self.db, enabled=[sc.CARD_KIND, "not_a_lens"])
        self.assertTrue(body["lenses"][sc.CARD_KIND]["enabled"])
        self.assertEqual(len(body["lenses"][sc.CARD_KIND]["cards"]), 2)
        self.assertNotIn("not_a_lens", body["lenses"])
        self.assertEqual(sum(l["enabled"] for l in body["lenses"].values()), 1)

    def test_limit_is_clamped(self):
        seed(self.db, 3)
        cards = lambda n: build_insights_body(self.db, enabled=[sc.CARD_KIND], limit=n)["lenses"][sc.CARD_KIND]["cards"]
        self.assertEqual(len(cards(2)), 2)
        self.assertEqual(len(cards(0)), 1)
        self.assertEqual(len(cards(10_000)), 3)

    def test_dismissed_and_accepted_rows_are_not_listed_as_cards(self):
        seed(self.db, 2)
        key = sc.dismiss_key("s0")
        outcomes.accept_card(self.db, sc.CARD_KIND, key)
        cards = build_insights_body(self.db, enabled=[sc.CARD_KIND])["lenses"][sc.CARD_KIND]["cards"]
        self.assertEqual(len(cards), 2)

    def test_capabilities_reports_insights_once_populated(self):
        self.assertFalse(build_capabilities(self.db)["features"]["insights"]["available"])
        seed(self.db, 1)
        self.assertTrue(build_capabilities(self.db)["features"]["insights"]["available"])

    def test_every_card_is_a_generic_card(self):
        doc = json.loads((FIXTURES / "insights_three_on.json").read_text())["response"]
        shown = 0
        for kind, lens in doc["lenses"].items():
            for card in lens["cards"]:
                shown += 1
                self.assertEqual(card["kind"], kind)
                for field in ("title", "body", "subject", "reasons", "actions", "dismissible", "score"):
                    self.assertIn(field, card)
                self.assertTrue(card["reasons"])
                self.assertTrue(card["subject"]["key"])
        self.assertEqual(shown, 3)


class PhaseThreeExitRuleTests(unittest.TestCase):
    """Recommendation weights and ownership flags are out of reach of every insight module."""

    FORBIDDEN = re.compile(r"^\s*(?:from|import)\s+[\w.]*(?:recommendation|navidrome_server)\b", re.M)

    def test_insight_modules_do_not_import_recommendation_or_the_server(self):
        files = list((ROOT / "intelligence" / "insights").glob("*.py")) + [ROOT / "intelligence" / "api" / "insights.py"]
        self.assertGreater(len(files), 10)
        for path in files:
            with self.subTest(module=path.name):
                self.assertIsNone(self.FORBIDDEN.search(path.read_text(encoding="utf-8")))

    def test_insight_modules_never_write_ownership_columns(self):
        for path in (ROOT / "intelligence" / "insights").glob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(module=path.name):
                self.assertNotRegex(text, r"(update|insert into|delete from)\s+(albums|owned|ownership)")


if __name__ == "__main__":
    unittest.main()
