"""Source contract: ranked rows keep the same column widths whatever their tag count.

Each row is its own grid, so a content-sized metadata column made a row with many tags lay out
differently from one with two or three. These tests read the script and stylesheet as source;
they never open a browser, so they do not replace the manual checklist.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")


class RankedRowEqualWidthContractTests(unittest.TestCase):
    def test_metadata_column_has_a_fixed_width_at_every_desktop_breakpoint(self):
        self.assertIn("grid-template-columns: 72px var(--row-art) minmax(0, 1fr) 220px auto;", CSS)
        self.assertIn("grid-template-columns: 64px var(--row-art) minmax(0, 1fr) 180px auto;", CSS)
        self.assertNotRegex(CSS, r"\.ranked-row \{[^}]*minmax\(0, \d+px\)")

    def test_genre_line_is_clamped_and_keeps_the_full_list_in_a_title(self):
        self.assertRegex(CSS, r"\.row-genres \{[^}]*-webkit-line-clamp: 2;[^}]*overflow: hidden;")
        self.assertIn("'row-meta-line row-genres'", JS)
        self.assertIn("genreLine.title = genres.join(' · ');", JS)


if __name__ == "__main__":
    unittest.main()
