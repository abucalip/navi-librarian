"""Source-contract regressions for the Artist Deep Dive card and row controls.

These tests protect the branch's conditional rendering and lifecycle behavior without
claiming to replace the documented manual browser checklist.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"


class ArtistDeepDiveUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_artist_hierarchy_and_category_change_are_scoped_to_deep_dive(self):
        self.assertIn("const isDeepDive = name === 'artist_deep_dive';", self.js)
        self.assertIn("if (!isDeepDive) {", self.js)
        self.assertIn("title.append(document.createTextNode(isDeepDive ? artist : album));", self.js)
        self.assertIn("if (year !== null && !isDeepDive) addTextElement(title, 'span', 'album-year', String(year));", self.js)
        self.assertIn("const supportingLine = addTextElement(card, 'p', 'card-artist', isDeepDive ? album : artist);", self.js)
        self.assertIn("if (year !== null && isDeepDive) addTextElement(supportingLine, 'span', 'album-year', String(year));", self.js)

    def test_arrows_are_hidden_and_removed_from_tab_order_when_track_fits(self):
        self.assertIn("const overflows = track.scrollWidth > track.clientWidth + 1;", self.js)
        self.assertIn("arrows.hidden = !overflows;", self.js)
        self.assertIn("else arrow.setAttribute('tabindex', '-1');", self.js)
        self.assertIn("if (overflows) arrow.removeAttribute('tabindex');", self.js)
        # The arrows container has an author display:flex rule, so [hidden] needs an
        # explicit author rule rather than relying only on the user-agent hidden style.
        self.assertIn(".genre-row-arrows[hidden] { display: none; }", self.css)

    def test_overflow_rechecks_and_observers_are_cleaned_up_on_rerender(self):
        self.assertIn("track.addEventListener('scroll', syncArrows, {passive: true});", self.js)
        self.assertIn("const observer = new ResizeObserver(syncArrows);", self.js)
        self.assertIn("requestAnimationFrame(syncArrows);", self.js)
        cleanup_start = self.js.index("function disconnectGenreRowObservers()")
        cleanup_end = self.js.index("async function loadDiscovery(", cleanup_start)
        cleanup = self.js[cleanup_start:cleanup_end]
        self.assertIn("genreRowObservers.pop().disconnect()", cleanup)
        self.assertIn("window.removeEventListener('resize', genreRowResizeHandlers.pop())", cleanup)
        load_start = self.js.index("async function loadDiscovery(")
        self.assertLess(
            self.js.index("disconnectGenreRowObservers();", load_start),
            self.js.index("target.replaceChildren();", load_start),
        )


if __name__ == "__main__":
    unittest.main()
