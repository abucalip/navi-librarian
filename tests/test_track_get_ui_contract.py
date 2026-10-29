"""Source-contract regressions for the per-track Get on the album page and its acquisition card.

Server behavior is covered in test_acquisition_track.py. These keep the button states, the
album-level Get/check rule and the song card from being removed. The state function is also
run in Node when it is available, so the rule itself is exercised and not only its source.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"


def block(source, start, end):
    first = source.index(start)
    return source[first:source.index(end, first)]


class TrackGetUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_unowned_tracks_get_their_own_button_and_owned_tracks_keep_the_check(self):
        row = block(self.js, "function buildTrackRow(", "// \"17 songs")
        self.assertIn("track.owned ? buildOwnedCheck()", row)
        self.assertIn("createTrackGetButton({", row)
        self.assertIn("title: track.title", row)
        self.assertIn("album: album.name", row)

    def test_top_songs_get_a_button_when_they_name_an_album(self):
        row = block(self.js, "function buildTopSongRow(", "function paintTopSongs(")
        self.assertIn("item.owned ? buildOwnedCheck()", row)
        self.assertIn("item.album && item.artist ? createTrackGetButton(", row)
        self.assertIn("artist: ctx.name", block(self.js, "function paintTopSongs(", "function hideTopSongs("))
        self.assertIn(".top-song .get-track", self.css)

    def test_song_get_posts_to_the_track_endpoint_and_never_claims_success_early(self):
        request = block(self.js, "async function searchTrack(", "function createTrackGetButton(")
        self.assertIn("'/api/acquire/track'", request)
        self.assertLess(request.index("'pending'"), request.index("sendJSON("))
        self.assertLess(request.index("sendJSON("), request.index("'requested'"))
        self.assertIn("data.ok === false", request)
        self.assertIn("'no_matches'", request)  # nothing found leaves Get usable again
        self.assertNotIn("setTimeout", request)
        self.assertNotIn("'idle'", request)
        button = block(self.js, "function createTrackGetButton(", "async function loadNavidromeSettings")
        self.assertIn("button.dataset.noun = 'song'", button)

    def test_idle_label_names_the_noun(self):
        state = block(self.js, "function setGetButtonState(", "// Transient acquisition feedback")
        self.assertIn("button.dataset.noun || 'album'", state)
        self.assertIn("'Get this ' + noun", state)

    def test_album_get_becomes_the_check_only_when_every_track_is_owned(self):
        action = block(self.js, "function setAlbumAction(", "// A track: number")
        self.assertIn("tracks.every(track => track.owned)", action)
        self.assertIn("Boolean(album.owned)", action)
        sections = block(self.js, "function applyAlbumSection(", "// ---- Genre view")
        self.assertIn("albumPage.album = album;", sections)
        self.assertIn("setAlbumAction(albumPage.album, section.items)", sections)

    def test_rule_in_node(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node is not available")
        source = block(self.js, "function setAlbumAction(", "// A track: number")
        script = (
            "const made = [];\n"
            "const $ = () => ({replaceChildren: x => made.push(x)});\n"
            "const buildAlbumState = item => item;\n" + source +
            "const album = {artist: 'A', name: 'B', year: 1999, release_group_mbid: null, owned: true};\n"
            "const out = [];\n"
            "setAlbumAction(album); out.push(made.pop().owned);\n"
            "setAlbumAction({...album, owned: false}); out.push(made.pop().owned);\n"
            "setAlbumAction(album, [{owned: true}, {owned: true}]); out.push(made.pop().owned);\n"
            "setAlbumAction(album, [{owned: true}, {owned: false}]); out.push(made.pop().owned);\n"
            "setAlbumAction({...album, owned: false}, [{owned: true}, {owned: true}]); out.push(made.pop().owned);\n"
            "console.log(JSON.stringify(out));\n"
        )
        result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        # Before the tracklist: the album's own state. After: owned only when no track is missing.
        self.assertEqual(json.loads(result.stdout), [True, False, True, False, True])

    def test_song_cards_are_named_after_the_song_and_retry_through_the_song_endpoint(self):
        cards = block(self.js, "function renderAcquisitions(", "const ACTIVE_DOWNLOAD_STATUSES")
        self.assertIn("details.kind === 'track'", cards)
        self.assertIn("details.track_title", cards)
        self.assertIn("'Song on '", cards)
        self.assertIn("isSong ? '/api/acquire/track' : '/api/acquire'", cards)
        # Dismiss keeps the row's own identity, which the server maps to the song.
        dismiss = block(cards, "'/api/acquisitions/dismiss'", "const stored")
        self.assertIn("artist: job.artist, album: job.album", dismiss)

    def test_the_fourth_track_column_fits_the_button_and_the_button_is_a_pill(self):
        self.assertIn("minmax(28px, auto)", block(self.css, ".track {", "}"))
        self.assertIn(".track .get-track, .top-song .get-track {", self.css)


if __name__ == "__main__":
    unittest.main()
