"""Source contract for the Save bookmark control on recommendation rows and cards.

Like the other ``*_ui_contract`` modules these read the shipped assets and never start a
browser, a server or an acquisition request. Rendered behaviour is recorded in the PR report.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")


def between(source, start, end):
    begin = source.index(start)
    return source[begin:source.index(end, begin)]


class SaveBookmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.button = between(JS, "function createSaveButton(", "async function refreshDiscovery(")
        cls.state = between(JS, "function setSaveButtonState(", "function createSaveButton(")

    def test_save_posts_feedback_with_the_whole_item_and_starts_no_acquisition(self):
        self.assertIn("'/api/discovery/feedback'", self.button)
        self.assertIn("{action: wasSaved ? 'remove_for_me' : 'save', artist, album, metadata}", self.button)
        self.assertNotIn("/api/acquire", self.button)
        self.assertNotIn("searchAlbum", self.button)

    def test_save_updates_in_place_and_does_not_reload_the_list(self):
        # The list endpoints hide saved albums, so a reload would drop the card and its Undo.
        self.assertNotIn("loadDiscovery", self.button)
        self.assertNotIn("sendFeedback", self.button)

    def test_accessible_name_includes_the_album_and_state_is_aria_pressed(self):
        self.assertIn("button.setAttribute('aria-label', 'Save ' + album)", self.button)
        self.assertIn("'aria-pressed'", self.state)
        self.assertIn("'aria-busy'", self.state)

    def test_failure_restores_the_confirmed_state_and_reports_the_error(self):
        self.assertIn("setSaveButtonState(button, wasSaved, album, false, true)", self.button)
        self.assertIn("discoveryStatus(listName,", self.button)
        self.assertIn("data.ok === false", self.button)

    def test_repeat_clicks_are_ignored_while_a_request_is_in_flight(self):
        self.assertIn("if (button.getAttribute('aria-busy') === 'true') return;", self.button)

    def test_state_is_not_colour_alone(self):
        self.assertIn("'bookmark-check' : 'bookmark'", self.state)
        self.assertIn("'Saved'", self.state)

    def test_control_is_wired_to_every_recommendation_list(self):
        self.assertIn("listName: options.listName,", JS)
        self.assertIn("listName: name,", JS)
        self.assertIn("group.append(createSaveButton(artist, album, metadata, options.listName));", JS)
        for name in ("new_releases", "personal", "classics"):
            self.assertIn("listName: '%s'," % name, JS)

    def test_touch_target_and_focus_ring(self):
        rule = between(CSS, ".action-group > button {", "}")
        self.assertIn("height: var(--group-h)", rule)
        self.assertIn("width: 44px", rule)
        self.assertIn(".action-group > button:focus-visible", CSS)


if __name__ == "__main__":
    unittest.main()
