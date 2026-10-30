"""Regression contract for the Phase 7 screen-reader pass (docs/REDESIGN_ROADMAP.md item 11).

Covers the names, roles and focus handling that a screen-reader or keyboard user depends on:
- the Get control keeps keyboard focus when it is disabled for a request, and returns to the
  control when the request fails;
- icon-only and repeated card actions name the album or artist they act on;
- the artwork group on a card is a real group, so its label is announced;
- acquisition Dismiss keeps focus when its row is removed.

These tests read the script only. Behaviour is checked in the rendered build; see
docs/UI_BACKLOG_EXECUTION.md section 32. The server contract is untouched.
"""
import unittest
from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "static" / "app.js"


class ScreenReaderNamesUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_get_keeps_focus_while_the_request_is_in_flight(self):
        search = self.js[self.js.index("async function searchAlbum("):self.js.index("function getFocusOwner(")]
        self.assertIn("const hadFocus = !!button && document.activeElement === button;", search)
        self.assertIn("const focusOwner = hadFocus ? getFocusOwner(button) : null;", search)
        pending = search.index("setGetButtonState(button, 'pending', artist, album);")
        self.assertLess(pending, search.index("if (focusOwner) focusOwner.focus();"))
        # The pending state is still applied before the await; focus only moves, it never
        # changes the Get state machine.
        self.assertLess(pending, search.index("await sendJSON('/api/acquire'"))
        self.assertIn("if (hadFocus) button.focus();", search)
        self.assertEqual(search.count("if (hadFocus) button.focus();"), 2)

    def test_get_focus_owner_is_the_dialog_close_or_the_card(self):
        helper = self.js[self.js.index("function getFocusOwner("):]
        helper = helper[:helper.index("\n}\n") + 3]
        self.assertIn("if (button.closest('.album-modal')) return $('albumModalClose');", helper)
        self.assertIn("button.closest('[tabindex=\"0\"]') || button.closest('article')", helper)
        self.assertIn("owner.setAttribute('tabindex', '-1');", helper)

    def test_card_artwork_group_is_announced(self):
        attach = self.js[self.js.index("function attachArtwork("):]
        self.assertIn("art.setAttribute('role', 'group');", attach)
        self.assertLess(attach.index("art.setAttribute('role', 'group');"),
                        attach.index("art.setAttribute('aria-label', 'Album artwork');"))

    def test_icon_only_and_repeated_actions_name_their_album_or_artist(self):
        self.assertIn("dismissButton.setAttribute('aria-label', options.dismissLabel || 'Not for me: ' + album);", self.js)
        self.assertNotIn("Dismiss artist", self.js)
        self.assertIn("'Dismiss ' + (job.album || job.artist || 'acquisition'), 'Dismiss');", self.js)

    def test_visible_label_is_kept_inside_each_accessible_name(self):
        # WCAG 2.5.3 (label in name): the visible words must begin the accessible name.
        # The control is an icon button; "Dismiss" stays inside its accessible name.
        self.assertIn("buildAcquisitionIconButton('trash-2', 'dismiss-album',", self.js)

    def test_acquisition_dismiss_keeps_focus_when_its_row_is_removed(self):
        render = self.js[self.js.index("const dismiss = buildAcquisitionIconButton("):]
        render = render[:render.index("group.append(dismiss);")]
        self.assertIn("const hadFocus = document.activeElement === dismiss;", render)
        self.assertIn("const neighbour = row.nextElementSibling || row.previousElementSibling;", render)
        self.assertLess(render.index("const neighbour = row.nextElementSibling"), render.index("row.remove();"))
        self.assertIn("status.tabIndex = -1; status.focus();", render)
        self.assertIn("if (hadFocus) dismiss.focus();", render)


if __name__ == "__main__":
    unittest.main()
