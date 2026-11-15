"""Star Operation S2c: the web More menu and Blocklist page (source contract, not a browser check)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")


class BlocklistUiContract(unittest.TestCase):
    def test_page_is_a_labelled_section_reachable_from_the_header_menu(self):
        self.assertRegex(HTML, r'<section id="blocklist" class="page hidden" aria-labelledby="blocklistHeading">')
        self.assertIn('id="blocklistHeading"', HTML)
        self.assertIn('data-page="blocklist"', HTML)
        for list_id in ("blocklistGenres", "blocklistArtists", "blocklistLeans"):
            self.assertIn(f'id="{list_id}"', HTML)

    def test_menu_panel_and_toast_exist_once(self):
        self.assertEqual(HTML.count('id="feedbackMenu"'), 1)
        self.assertEqual(HTML.count('id="feedbackToast"'), 1)

    def test_every_endpoint_the_screen_uses_is_a_server_route(self):
        routes = (ROOT / "app" / "api" / "discovery.py").read_text(encoding="utf-8")
        for url in set(re.findall(r"'(/api/discovery/(?:blocked-genres|blocked-artists|artist-lean))", JS)):
            self.assertIn(f'"{url}"', routes, url)

    def test_menu_offers_the_four_actions_and_only_the_albums_own_genres(self):
        for text in ("More like this artist", "Less like this artist", "Not this artist", "'Block genre: '"):
            self.assertIn(text, JS)
        self.assertIn("['genres', 'tags']", JS)

    def test_menu_follows_not_for_me_so_saved_rows_have_none(self):
        body = JS.split("function createActionGroup", 1)[1].split("\n}\n", 1)[0]
        self.assertIn("if (options.onDismiss) {", body)
        self.assertLess(body.index("if (options.onDismiss) {"), body.index("createFeedbackMenuButton"))


if __name__ == "__main__":
    unittest.main()
