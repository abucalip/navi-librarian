"""Source contract for the artist bio in the album details dialog.

The dialog reuses the existing /api/artist-bio endpoint and artistBioRequests cache that ranked
rows use. These tests read the template, script and stylesheet as source; they never open a
browser, so they do not replace the manual checklist.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
JS = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8")


class AlbumModalArtistBioContractTests(unittest.TestCase):
    def test_dialog_has_a_bio_paragraph_hidden_until_a_bio_arrives(self):
        self.assertRegex(HTML, r'<p id="albumModalBio" class="album-modal-bio" hidden></p>')
        self.assertIn(".album-modal-bio[hidden] { display: none; }", CSS)

    def test_open_requests_the_bio_through_the_shared_cache_and_endpoint(self):
        body = re.search(r"function loadAlbumModalBio\(.*?\n\}\n", JS, re.S).group(0)
        self.assertIn("cachedBioRequest(bioKey, artist, true)", body)
        self.assertIn("bio.textContent = result.bio;", body)
        self.assertNotIn("innerHTML", body)
        self.assertIn("activeAlbumModal.card !== card", body)
        self.assertIn("loadAlbumModalBio(card, artist);", JS)

    def test_bio_resets_on_each_open_and_is_skipped_for_unknown_artist(self):
        body = re.search(r"function loadAlbumModalBio\(.*?\n\}\n", JS, re.S).group(0)
        self.assertLess(body.index("bio.hidden = true;"), body.index("cachedBioRequest"))
        self.assertIn("'Unknown artist'", body)


if __name__ == "__main__":
    unittest.main()
