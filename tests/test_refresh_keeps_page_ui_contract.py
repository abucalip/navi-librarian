"""Regressions for ACTIVE_WORK 2e: a browser refresh returns to the page the owner was on.

The hash helpers are pure, so the round-trip tests run them in Node when it is installed and
skip otherwise. The source-contract tests keep the hash read and write wired in.
"""
import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "static" / "app.js"
LOGIN_JS = ROOT / "static" / "login.js"
NODE = shutil.which("node")


def _function_source(js, name):
    start = js.index("function " + name + "(")
    depth = 0
    for index in range(js.index(") {", start) + 2, len(js)):
        depth += js[index] == "{"
        depth -= js[index] == "}"
        if depth == 0:
            return js[start:index + 1]
    raise AssertionError(name)


class RefreshKeepsPageSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")

    def test_show_page_and_library_navigation_write_the_hash(self):
        self.assertIn("syncLocationHash();", _function_source(self.js, "showPage"))
        for name in ("libraryReset", "libraryOpen"):
            self.assertIn("syncLocationHash();", _function_source(self.js, name), name)
        self.assertIn("syncLocationHash(", _function_source(self.js, "libraryBack"))

    def test_page_changes_push_history_and_popstate_reapplies_without_writing(self):
        sync = _function_source(self.js, "syncLocationHash")
        self.assertIn("history.pushState", sync)
        self.assertIn("history.replaceState", sync)
        self.assertIn("if (applyingHash) return;", sync)
        self.assertIn("addEventListener('popstate', () => applyHash(window.location.hash))", self.js)
        self.assertIn("syncLocationHash({replace: true});", _function_source(self.js, "libraryBack"))

    def test_hash_carries_no_secret(self):
        fields = self.js[self.js.index("const HASH_FIELDS"):self.js.index("const HASH_FIELD_MAX")]
        for forbidden in ("token", "password", "secret", "artworkUrl", "api_key"):
            self.assertNotIn(forbidden, fields)

    def test_startup_applies_the_hash_after_everything_is_defined(self):
        self.assertTrue(self.js.rstrip().endswith("if (window.location.hash) applyHash(window.location.hash);"))
        apply_hash = _function_source(self.js, "applyHash")
        self.assertIn("classList.contains('page')", apply_hash)
        self.assertIn("decodeLibraryHash(hash)", apply_hash)
        self.assertIn("'dashboard'", apply_hash)

    def test_restoring_from_the_address_does_not_focus_the_heading(self):
        for name in ("renderArtist", "renderAlbum", "renderGenre"):
            source = _function_source(self.js, name)
            self.assertIn("if (!applyingHash) heading.focus();", source, name)
            self.assertNotIn("\n  heading.focus();", source, name)

    def test_login_keeps_the_hash(self):
        login = LOGIN_JS.read_text(encoding="utf-8")
        self.assertIn("window.location.replace('/'+window.location.hash)", login)


@unittest.skipUnless(NODE, "node is not installed")
class RefreshKeepsPageHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        js = APP_JS.read_text(encoding="utf-8")
        cls.helpers = js[js.index("const HASH_FIELDS"):js.index("function currentLocationHash")]

    def run_js(self, body):
        script = self.helpers + "\nconsole.log(JSON.stringify((() => {" + body + "})()));"
        result = subprocess.run([NODE, "-e", script], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_round_trip_with_awkward_names(self):
        names = ['AC/DC', 'Guns N\' Roses "Live"', 'Sigur Rós', 'a&b=c?d#e', '日本語 100%']
        out = self.run_js(
            "const names = %s; const back = [];"
            "for (const n of names) {"
            " const a = {type:'artist', key:n.toLowerCase(), id:'ar 1', name:n, mbid:null, artworkUrl:'/x'};"
            " const b = {type:'album', key:'x/'+n.toLowerCase(), id:null, artist:n, name:n, year:1999, mbid:'m'};"
            " const g = {type:'genre', tag:n};"
            " const h = [a, b, g].map(t => encodeLibraryHash(t));"
            " back.push(h.every(x => x.indexOf(' ') < 0 && x.indexOf('#', 1) < 0),"
            "  decodeLibraryHash(h[0]).name, decodeLibraryHash(h[1]).artist, decodeLibraryHash(h[1]).year,"
            "  decodeLibraryHash(h[2]).tag, decodeLibraryHash(h[1]).owned, decodeLibraryHash(h[0]).artworkUrl);"
            "} return back;" % json.dumps(names)
        )
        for position, name in enumerate(names):
            chunk = out[position * 7:position * 7 + 7]
            self.assertEqual(chunk, [True, name, name, "1999", name, False, None], name)

    def test_unknown_or_malformed_hashes_decode_to_null(self):
        out = self.run_js(
            "return ['', '#', '#library', '#library/', '#library/bogus?key=a', '#library/artist',"
            " '#library/artist?name=x', '#library/album?key=nokey&name=x', '#library/album?key=a/b',"
            " '#library/genre?tag=', '#library/artist?key=' + 'a'.repeat(400), '#settings']"
            ".map(h => decodeLibraryHash(h));"
        )
        self.assertEqual(out, [None] * 12)

    def test_non_library_target_encodes_as_the_library_list(self):
        self.assertEqual(self.run_js("return [encodeLibraryHash(null), encodeLibraryHash({type:'x'})];"),
                         ["#library", "#library"])


if __name__ == "__main__":
    unittest.main()
