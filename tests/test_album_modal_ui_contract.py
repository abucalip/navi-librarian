"""Phase 6 item 3 contract: the album modal uses the Chart Rundown layout, motion and tokens.

DESIGN_SYSTEM.md sections 6, 7, 8, 9.8, 10, 11 and 12; REDESIGN_ROADMAP.md Phase 6. These are
source-contract checks. Rendered behaviour was checked in the browser (docs/UI_BACKLOG_EXECUTION.md
section 22); the dialog's focus trap, Escape and focus return are covered in
test_ui_keyboard_and_feedback_contract.py and are not weakened here.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
TEMPLATE = ROOT / "app" / "templates" / "index.html"
APP_CSS = STATIC / "app.css"
APP_JS = STATIC / "app.js"


def album_modal_css(css):
    start = css.index(".album-modal-backdrop {")
    end = css.index("@media (max-width: 650px) { .album-modal-backdrop", start)
    return css[start:end]


class AlbumModalMarkupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = TEMPLATE.read_text(encoding="utf-8")

    def test_dialog_keeps_its_semantics_and_name(self):
        self.assertIn('<section class="album-modal" role="dialog" aria-modal="true" aria-labelledby="albumModalTitle">', self.html)
        self.assertIn('<h2 id="albumModalTitle">', self.html)

    def test_close_control_is_a_named_icon_button_from_the_sprite(self):
        close = re.search(r'<button id="albumModalClose"[^>]*>.*?</button>', self.html, re.S).group(0)
        self.assertIn('aria-label="Close album details"', close)
        self.assertIn('<use href="/static/icons.svg#x"></use>', close)
        self.assertIn('aria-hidden="true"', close)
        self.assertNotIn("×", close)

    def test_artwork_column_precedes_the_copy_column(self):
        layout = self.html.index('class="album-modal-layout"')
        self.assertLess(self.html.index('class="album-modal-art-column"', layout), self.html.index('class="album-modal-copy"', layout))


class AlbumModalStyleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = APP_CSS.read_text(encoding="utf-8")
        cls.block = album_modal_css(cls.css)

    def test_scrim_is_solid_and_panel_is_raised_without_blur_or_shadow(self):
        self.assertNotIn("backdrop-filter", self.block)
        self.assertNotRegex(self.block, r"box-shadow: (?!none)")
        self.assertIn("background: rgb(20 18 17 / .8);", self.block)
        self.assertIn("background: var(--surface-raised);", self.block)
        self.assertIn("border-radius: var(--radius-panel);", self.block)

    def test_no_literal_colours_in_the_modal_block(self):
        self.assertIsNone(re.search(r"#[0-9a-fA-F]{3,6}\b", self.block))
        self.assertIsNone(re.search(r"rgba?\(", self.block.replace("rgb(20 18 17 / .8)", "")))

    def test_year_is_metadata_not_the_accent(self):
        year = re.search(r"\.album-modal-year \{[^}]*\}", self.block).group(0)
        self.assertNotIn("var(--accent)", year)

    def test_motion_is_opacity_and_an_eight_pixel_translate_only(self):
        self.assertIn("@keyframes album-modal-rise { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }", self.block)
        self.assertIn("@keyframes album-modal-fade { from { opacity: 0; } to { opacity: 1; } }", self.block)
        self.assertRegex(self.block, r"\.album-modal \{[^}]*animation: album-modal-rise var\(--dur-slow\)")

    def test_reduced_motion_removes_the_modal_animation(self):
        self.assertIn("@media (prefers-reduced-motion: reduce) { .album-modal-backdrop, .album-modal { animation: none; } }", self.block)

    def test_touch_targets_are_44_pixels(self):
        self.assertRegex(self.block, r"\.album-modal-close \{[^}]*width: 44px; height: 44px;")
        # Platform links are text chips now (PR for DESIGN_SYSTEM.md 16.2 row 12): min-width, not a fixed width, so the name fits.
        self.assertRegex(self.block, r"\.album-modal-art-column \.album-platform-links a \{[^}]*min-width: 44px; height: 44px;")
        self.assertNotIn("inset: -7px", self.block)

    def test_tracklist_rows_are_compact_48_pixels(self):
        self.assertIn("min-height: 48px;", self.block)
        self.assertIn("font-variant-numeric: tabular-nums;", self.block)

    def test_dialog_contains_scroll_chaining_and_balances_the_title(self):
        self.assertIn("overscroll-behavior: contain;", self.block)
        self.assertIn("text-wrap: balance;", self.block)

    def test_modal_title_stays_at_the_page_head_maximum(self):
        self.assertIn("font: 600 var(--text-2xl)/1.05 var(--display);", self.block)


class AlbumModalBehaviourGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_get_state_machine_and_data_calls_are_unchanged(self):
        self.assertIn("requestJSON('/api/album-details?' + query.toString())", self.js)
        self.assertIn("requestJSON('/api/artwork?' + query.toString())", self.js)
        self.assertIn("get.onclick = () => searchAlbum(artist, album, metadata, get);", self.js)

    def test_close_returns_focus_to_the_opener_when_still_attached(self):
        self.assertIn("if (returnTo && returnTo.isConnected) returnTo.focus();", self.js)

    def test_platform_links_make_no_third_party_requests(self):
        # AGENTS.md: no runtime third-party assets. Every image the platform links load is a local
        # vendored file under /static/vendor/simple-icons/, and the script names none of the hosts
        # the old logo images came from. The visible platform name is set as text on every link.
        start = self.js.index("function setAlbumPlatformLinks(")
        end = self.js.index("\n}\n", start)
        body = self.js[start:end]
        for host in ("raw.githubusercontent.com", "simpleicons.org", "community.qobuz.com"):
            self.assertNotIn(host, self.js)
        for src in re.findall(r"'(/static/vendor/[^']+)'", body):
            self.assertTrue((ROOT / src.lstrip("/")).is_file(), src)
        self.assertIn("icon.alt = '';", body)
        self.assertIn("link.append(label);", body)
        self.assertIn("link.setAttribute('aria-label',", body)
        # Qobuz and ListenBrainz have no vendored mark, so they are text-only links.
        self.assertIn("['Qobuz', 'https://www.qobuz.com/us-en/search/albums/' + encoded, null]", body)
        self.assertIn("['ListenBrainz', 'https://listenbrainz.org/search/?query=' + encoded, null]", body)


if __name__ == "__main__":
    unittest.main()
