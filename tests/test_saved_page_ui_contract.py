"""Source contract for the Saved page (header menu entry, list read, row behaviour).

Reads the shipped assets only; it starts no browser, server or acquisition request.
Rendered behaviour is recorded in the PR report.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")


def between(source, start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


class SavedPageTests(unittest.TestCase):
    def test_header_menu_lists_saved_before_settings(self):
        panel = between(HTML, 'id="appMenu"', 'id="logoutButton"')
        self.assertLess(panel.index('data-page="saved"'), panel.index('data-page="settings"'))

    def test_page_section_has_list_and_live_status(self):
        section = between(HTML, '<section id="saved"', "</section>")
        self.assertIn('id="savedCards"', section)
        self.assertIn('id="savedStatus"', section)
        self.assertIn('aria-live="polite"', section)

    def test_page_reads_the_for_me_list_on_every_visit(self):
        self.assertIn("/api/discovery/for_me", between(JS, "async function loadSaved", "[data-refresh-saved]"))
        self.assertIn("if (name === 'saved') loadSaved();", between(JS, "function navigateTo", "}\n\n"))

    def test_gear_carries_the_current_cue_for_saved(self):
        self.assertIn("name === 'settings' || name === 'saved'", JS)

    def test_saved_rows_start_saved_and_have_no_dismiss_or_acquire_on_owned(self):
        row = between(JS, "function buildSavedRow", "async function loadSaved")
        self.assertIn("saved: true", row)
        self.assertIn("owned", row)
        build = between(JS, "function buildRecommendationRow", "const monthAbbreviations")
        self.assertIn("if (!options.owned) group.append(createGetButton", JS)
        self.assertIn("const onDismiss = options.saved ? null :", build)
        self.assertIn("if (options.saved) setSaveButtonState(group.querySelector('.save-album'), true, album);", build)


if __name__ == "__main__":
    unittest.main()
