"""Every button on the pages below sits in an action group (icon-only, sprite icon, named by aria-label).

The owner asked for one button style: the joined Get / Save / Not for me frame. Buttons next to each
other share one group; a lone button gets a one-button group. `.btn-primary` is gone.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
SPRITE_IDS = set(re.findall(r'<symbol id="([^"]+)"', (ROOT / "static" / "icons.svg").read_text(encoding="utf-8")))

# button id (or data attribute) -> (accessible name, sprite icon)
BUTTONS = {
    'id="loadRecommendations"': ("Generate recommendations", "sparkles"),
    'id="saveNavidrome"': ("Save settings", "save"),
    'id="checkConnection"': ("Test connection", "plug-zap"),
    'id="saveSlskd"': ("Save settings", "save"),
    'id="testSlskd"': ("Test connection", "plug-zap"),
    'id="saveLastfm"': ("Save settings", "save"),
    'id="testLastfm"': ("Test connection", "plug-zap"),
    'id="saveListenbrainz"': ("Save settings", "save"),
    'id="testListenbrainz"': ("Test connection", "plug-zap"),
    'id="saveDiscogs"': ("Save token", "save"),
    'id="removeDiscogs"': ("Remove saved token", "trash-2"),
    'id="testDiscogs"': ("Test connection", "plug-zap"),
    'id="saveRadioAddress"': ("Save", "save"),
    'id="refreshRadio"': ("Refresh", "rotate-cw"),
    'data-refresh-saved': ("Refresh", "rotate-cw"),
    'id="libraryMore"': ("Load more", "plus"),
    'id="dashboardPrev"': ("Previous album", "chevron-left"),
    'id="dashboardNext"': ("Next album", "chevron-right"),
    'data-load-discovery="new_releases"': ("Load new releases", "list-plus"),
    'data-refresh-discovery="new_releases"': ("Refresh in background", "rotate-cw"),
    'data-load-discovery="personal"': ("Load discoveries", "list-plus"),
    'data-refresh-discovery="personal"': ("Refresh", "rotate-cw"),
    'data-load-discovery="classics"': ("Load albums", "list-plus"),
    'data-refresh-discovery="classics"': ("Refresh", "rotate-cw"),
    'data-load-discovery="artist_deep_dive"': ("Load albums", "list-plus"),
    'data-refresh-discovery="artist_deep_dive"': ("Refresh", "rotate-cw"),
}


class ButtonGroupContractTests(unittest.TestCase):
    def button(self, marker):
        match = re.search(r"<button [^>]*" + re.escape(marker) + r"[^>]*>.*?</button>", HTML)
        self.assertIsNotNone(match, marker)
        return match.group(0)

    def test_each_listed_button_is_an_icon_with_a_name(self):
        for marker, (name, icon) in BUTTONS.items():
            with self.subTest(marker):
                markup = self.button(marker)
                self.assertIn(f'title="{name}" aria-label="{name}"', markup)
                self.assertIn(f'icons.svg#{icon}"', markup)
                self.assertIn(icon, SPRITE_IDS)
                self.assertNotRegex(markup, r">\s*[A-Za-z]")

    def test_each_listed_button_is_inside_an_action_group(self):
        for marker in BUTTONS:
            with self.subTest(marker):
                pattern = r'<div [^>]*class="action-group"[^>]*>(?:(?!</div>).)*' + re.escape(marker)
                self.assertRegex(HTML, re.compile(pattern, re.S))

    def test_primary_button_class_is_retired(self):
        self.assertNotIn("btn-primary", HTML)
        self.assertNotIn(".btn-primary", CSS)

    def test_dynamic_groups_use_sprite_icons(self):
        self.assertIn("moves.className = 'quality-priority-moves action-group';", JS)
        self.assertIn("spriteIcon(direction === 'up' ? 'chevron-up' : 'chevron-down')", JS)
        self.assertIn("arrows.className = 'genre-row-arrows action-group';", JS)
        self.assertIn("$('libraryMoreGroup').hidden = !visible;", JS)

    def test_selects_use_the_chevron_down_instead_of_the_native_arrow(self):
        self.assertRegex(CSS, r"\.controls select, \.discovery-controls select \{ -webkit-appearance: none; appearance: none;")
        self.assertIn("%3Cpath d='m6 9 6 6 6-6'/%3E", CSS)


if __name__ == "__main__":
    unittest.main()
