"""Contract for the ranked-row artist bio: rows stay one height, a clipped bio opens on click."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")


class RowBioExpandTests(unittest.TestCase):
    def test_rows_have_one_height_and_the_bio_is_clamped_with_an_ellipsis(self):
        self.assertIn("--row-art: 136px;", CSS)
        self.assertRegex(CSS, r"\.ranked-row \.row-main \{[^}]*height: var\(--row-art\);")
        rule = re.search(r"\.ranked-row \.artist-bio \{([^}]*)\}", CSS).group(1)
        self.assertIn("-webkit-line-clamp: 2", rule)
        self.assertIn("overflow: hidden", rule)

    def test_opening_a_row_removes_the_clamp_and_grows_only_that_row(self):
        self.assertIn(".ranked-row.is-bio-open .row-main { height: auto;", CSS)
        self.assertIn(".ranked-row.is-bio-open .artist-bio { display: block; -webkit-line-clamp: none;", CSS)

    def test_only_a_clipped_bio_becomes_a_keyboard_operable_toggle(self):
        body = JS[JS.index("function makeBioExpandable("):JS.index("// Discover music metadata lines.")]
        self.assertIn("if (bio.scrollHeight <= bio.clientHeight + 1) return;", body)
        self.assertIn("setAttribute('role', 'button')", body)
        self.assertIn("setAttribute('tabindex', '0')", body)
        self.assertIn("aria-expanded", body)
        self.assertIn("event.stopPropagation()", body)
        self.assertIn("event.key !== 'Enter' && event.key !== ' '", body)
        self.assertNotIn("innerHTML", body)


if __name__ == "__main__":
    unittest.main()
