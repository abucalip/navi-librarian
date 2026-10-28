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
        # The heading is the artist in a deep dive and the album elsewhere; either name opens its library page.
        self.assertIn("if (isDeepDive) linkArtistName(title, artist);", self.js)
        self.assertIn("else linkAlbumName(title, artist, album, item);", self.js)
        self.assertIn("if (year !== null && !isDeepDive) addTextElement(title, 'span', 'album-year', String(year));", self.js)
        self.assertIn("const supportingLine = addTextElement(card, 'p', 'card-artist', '');", self.js)
        self.assertIn("if (isDeepDive) linkAlbumName(supportingLine, artist, album, item);", self.js)
        self.assertIn("else linkArtistName(supportingLine, artist);", self.js)
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


    def test_arrows_and_not_for_me_use_sprite_icons_with_names_kept(self):
        # Phase 4 (DESIGN_SYSTEM.md 9.1, 10): text glyphs were replaced with sprite icons.
        # The accessible names and the Not for me action are unchanged.
        self.assertIn("function spriteIcon(name)", self.js)
        self.assertIn("arrow.append(spriteIcon(icon));", self.js)
        self.assertIn("[['chevron-left', -1], ['chevron-right', 1]]", self.js)
        self.assertIn("notForMe.append(spriteIcon('x'));", self.js)
        self.assertNotIn("arrow.textContent = symbol;", self.js)
        self.assertNotIn("notForMe.textContent = '×';", self.js)
        self.assertIn("arrow.setAttribute('aria-label', direction < 0 ? 'Scroll albums left' : 'Scroll albums right');", self.js)
        self.assertIn("notForMe.setAttribute('aria-label', 'Not for me: ' + album);", self.js)
        self.assertIn("notForMe.title = 'Not for me';", self.js)

    def test_sprite_icon_helper_builds_nodes_without_innerhtml(self):
        start = self.js.index("function spriteIcon(name)")
        helper = self.js[start:self.js.index("\n}\n", start)]
        self.assertIn("document.createElementNS(svgNs, 'use')", helper)
        self.assertIn("'/static/icons.svg#' + name", helper)
        self.assertNotIn("innerHTML", helper)

    def test_deep_dive_controls_have_no_text_shadow_and_meet_44px(self):
        def rule(selector):
            start = self.css.index(selector + " {")
            return self.css[start:self.css.index("}", start)]
        arrow = rule(".genre-row-arrow")
        dismiss = rule(".card .card-art .deep-dive-dismiss")
        self.assertNotIn("text-shadow", arrow)
        self.assertNotIn("text-shadow", dismiss)
        self.assertIn("width: 44px; height: 44px;", arrow)
        self.assertIn("width: 44px; height: 44px;", dismiss)

    def test_genre_count_uses_body_face_not_mono(self):
        rule_start = self.css.index(".genre-row-count {")
        rule = self.css[rule_start:self.css.index("}", rule_start)]
        self.assertIn("var(--body)", rule)
        self.assertNotIn("var(--mono)", rule)
        self.assertIn("var(--text-sm)", rule)


    def test_genre_count_pluralizes_correctly(self):
        # "1 album", not "1 albums"; the count is a real count of the rendered row.
        self.assertIn("pluralize(genreItems.length, 'album', 'albums')", self.js)
        self.assertNotIn("`${genreItems.length} albums`", self.js)


if __name__ == "__main__":
    unittest.main()
