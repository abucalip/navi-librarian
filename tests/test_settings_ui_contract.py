"""Source-contract regressions for the Settings page restyle (Redesign Phase 6, item 1).

These read the shipped template, stylesheet and script as source and never open a browser.
They guard the points most likely to regress silently: the quality-tier move buttons losing
keyboard focus after a move, the ARIA tab pattern and its roving tabindex, the two-column
layout collapsing to one column on narrow screens, the 44px target floor, and secret fields
never being rendered into markup. Browser checks in docs/LOCAL_UI_TESTING.md still apply.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"


class SettingsKeyboardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_move_buttons_pass_direction_so_focus_can_follow_the_row(self):
        self.assertIn("moveQualityPriority(item, current + (direction === 'up' ? -1 : 1), direction);", self.js)

    def test_focus_returns_to_the_moved_row_and_skips_a_disabled_button(self):
        self.assertIn("function focusQualityMove(item, direction)", self.js)
        self.assertIn("(pressed.disabled ? other : pressed).focus();", self.js)

    def test_move_announcement_is_still_polite_live_region(self):
        self.assertIn("announceQualityPriority(item, destination);", self.js)
        html = INDEX_HTML.read_text(encoding="utf-8")
        self.assertRegex(html, r'id="qualityPriorityAnnouncement" class="sr-only" aria-live="polite"')

    def test_settings_tabs_keep_roving_tabindex_and_arrow_keys(self):
        self.assertIn("tab.setAttribute('tabindex', active ? '0' : '-1');", self.js)
        self.assertIn("event.key === 'ArrowRight' || event.key === 'ArrowDown'", self.js)
        self.assertIn("event.key === 'Home'", self.js)
        self.assertIn("event.key === 'End'", self.js)


class SettingsLayoutContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_fields_flow_in_two_columns_only_at_900px_and_up(self):
        self.assertRegex(
            self.css,
            r"@media \(min-width: 900px\) \{\s*\.settings-tab-panel \{ display: grid; grid-template-columns: repeat\(2, minmax\(0, 1fr\)\);",
        )

    def test_full_width_blocks_span_both_columns(self):
        self.assertIn(
            ".settings-tab-panel > h3, .settings-tab-panel > p, .settings-tab-panel > .quality-priority-list { grid-column: 1 / -1; }",
            self.css,
        )

    def test_hidden_panels_stay_hidden_inside_the_grid(self):
        self.assertIn(".settings-tab-panel[hidden] { display: none; }", self.css)

    def test_settings_tabs_and_buttons_meet_the_44px_floor(self):
        self.assertRegex(self.css, r"\.settings-tabs \.settings-tab \{[^}]*min-height: 44px;")
        self.assertRegex(self.css, r"#settings button \{ min-height: 44px; \}")
        self.assertRegex(self.css, r"\.quality-priority-moves button \{ min-width: 44px; min-height: 44px;")

    def test_selected_tab_is_marked_by_more_than_color_alone(self):
        self.assertRegex(self.css, r"\.settings-tabs \.settings-tab\.active \{[^}]*border-bottom-color: var\(--accent\);")

    def test_settings_text_uses_tokens_not_hardcoded_greys(self):
        self.assertNotIn("#c8c8bd", self.css)

    def test_no_new_motion_so_reduced_motion_needs_no_override(self):
        block = re.search(r"/\* Settings tabs.*?(?=\n/\* |\n\.quality-priority-list)", self.css, re.S)
        self.assertIsNotNone(block)
        self.assertNotIn("transition", block.group(0))
        self.assertNotIn("animation", block.group(0))


class SettingsSecretContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_secret_inputs_are_never_rendered_with_a_value(self):
        for field_id in ("navidromePassword", "slskdApiKey", "lastfmApiKey"):
            with self.subTest(field=field_id):
                match = re.search(rf'<input id="{field_id}"[^>]*>', self.html)
                self.assertIsNotNone(match)
                self.assertNotIn(" value=", match.group(0))
                self.assertIn('type="password"', match.group(0))

    def test_secret_fields_are_cleared_after_load_and_save(self):
        self.assertIn("$('navidromePassword').value = '';", self.js)
        self.assertIn("if ($('slskdApiKey').value) payload.api_key = $('slskdApiKey').value;", self.js)


if __name__ == "__main__":
    unittest.main()
