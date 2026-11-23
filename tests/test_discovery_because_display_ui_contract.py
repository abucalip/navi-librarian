"""Source-contract regressions for the personal-pick reason line (Star Operation S1c, DISC-09).

The browser formats `because` in `reasonLine`. These tests keep the owner's wording, the
tag-over-overlap order, and the routing of every personal-pick display through that one
formatter from being removed. They read the source only; the formatter's behaviour was
checked separately with Node (see the PR).
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "app.js"


def _function_body(source: str, header: str) -> str:
    start = source.index(header)
    depth = 0
    for index in range(source.index("{", start), len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"no body for {header}")


class DiscoveryBecauseDisplayUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_listening_room_reads_the_server_reason(self):
        home = (ROOT / "static" / "listening-room" / "home.js").read_text(encoding="utf-8")
        body = _function_body(home, "function renderReason(")
        self.assertIn("const why = item.why;", body)
        self.assertIn("why.sentence", body)
        self.assertNotIn("reasonLine(item)", body)

    def test_owner_wording_is_used_for_each_kind(self):
        self.assertIn("['tag', names => 'Because you listen to ' + names.join(', ')]", self.js)
        self.assertIn("['similar_artists', names => 'Shares genres with ' + names.join(', ')]", self.js)

    def test_because_one_is_never_worded_as_a_confirmed_seed(self):
        self.assertNotIn("Because you play", self.js)

    def test_reason_line_prefers_because_then_older_similar_to_on_adjacent(self):
        body = _function_body(self.js, "function reasonLine(item)")
        self.assertLess(body.index("BECAUSE_WORDING.get(because.kind)"), body.index("item.similar_to"))
        self.assertIn("item.discovery_category === 'adjacent' && similar.length", body)
        self.assertIn("'Shares genres with ' + similar.join(', ')", body)

    def test_category_line_falls_back_to_the_category_label(self):
        body = _function_body(self.js, "function categoryLine(item)")
        self.assertIn("reasonLine(item) || categoryLabel(item.discovery_category)", body)

    def test_every_personal_pick_display_uses_the_formatter(self):
        self.assertIn("meta: [reasonLine(item)],", self.js)
        self.assertIn("meta: [reasonLine(item), item.discovery_category === 'unclassified'", self.js)
        card = _function_body(self.js, "function buildRecommendationCard(item)")
        self.assertIn("reasonLine(item)", card)
        # Classics keep their own anchor-artist line; no personal or recommendation path draws similar_to by hand.
        self.assertNotIn("'Similar to: ' + item.similar_to", self.js)
        self.assertNotIn("'Similar to: ' + similar", self.js)


if __name__ == "__main__":
    unittest.main()
