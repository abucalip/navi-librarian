"""Regression contract for status-pair contrast (DESIGN_SYSTEM.md sections 4.1 and 16.2 row 13).

WCAG 2.1 AA: text under 24px needs 4.5:1; a control boundary needs 3:1 against its surface. The
pending Get control's boundary used --accent-dim, which measured 1.66 to 2.15:1 on the rendered
build. It now uses --accent, the idle control's ring (9.8:1 or better on every card ground). These
tests read the stylesheet only; the measured ratios are recorded in docs/UI_BACKLOG_EXECUTION.md
section 30.
"""
import re
import unittest
from pathlib import Path


APP_CSS = Path(__file__).resolve().parents[1] / "static" / "app.css"


def rule_bodies(css, selector):
    pattern = r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}"
    return [match.group(1) for match in re.finditer(pattern, css)]


class StatusContrastUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_pending_get_boundary_is_not_the_dim_accent(self):
        bodies = rule_bodies(self.css, ".get-album.is-pending")
        self.assertEqual(len(bodies), 1)
        self.assertIn("border-color: var(--accent);", bodies[0])
        self.assertNotIn("--accent-dim", bodies[0])

    def test_pending_get_keeps_its_muted_label_and_progress_cursor(self):
        body = rule_bodies(self.css, ".get-album.is-pending")[0]
        self.assertIn("color: var(--text-muted);", body)
        self.assertIn("cursor: progress;", body)


if __name__ == "__main__":
    unittest.main()
