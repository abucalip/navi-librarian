"""Exercise the L3 renderer against the server's reason fixtures and the design tint reference."""

import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import unittest

from discovery.pick_why import build_pick_why


ROOT = Path(__file__).resolve().parents[1]
HOME_JS = ROOT / "static/listening-room/home.js"
REFERENCE = ROOT / "docs/design/listening-room/_src/check_contrast.py"

# Competing fields in the first fixtures exercise server precedence at the rendering boundary.
REASONS = (
    ({"bridge_label": "Discover more Broadcast", "because": {"kind": "tag", "names": ["jazz"]},
      "lens": "deep_cuts", "owned": True}, "Discover more Broadcast", "layers"),
    ({"because": {"kind": "tag", "names": ["jazz"]}, "similar_to": ["Low"],
      "lens": "deep_cuts"}, "Because you listen to jazz", "tag"),
    ({"because": {"kind": "similar_artists", "names": ["Low", "Grouper", "Codeine"]},
      "similar_to": ["Broadcast"]}, "Shares genres with Low, Grouper and 1 more", "people"),
    ({"similar_to": ["Grouper"], "lens": "deep_cuts"}, "Shares genres with Grouper", "people"),
    ({"lens": "deep_cuts", "seed_tag": "jazz", "album_listeners": 41234,
      "tags": ["modal jazz", "post-bop"]}, "A lesser-known record from the jazz you play", "layers"),
    ({"lens": "current_tastes", "owned": True}, "From your Current tastes lens", "spark"),
    ({"deep_dive_kind": "missing_album", "anchor_artist": "Low", "anchor_album_count": 2,
      "reason": "Internal reason"}, "You have 2 albums by Low. This one is not in your library yet.", "library"),
    ({"deep_dive_kind": "similar_artist", "artist": "Broadcast", "anchor_artist": "Low"},
     "Close to Low, who is well covered in your library. Nothing by this artist yet.", "people"),
    ({"discovery_type": "new_release", "year": 2026, "artist_library_album_count": 1},
     "New in 2026 from an artist with a full album in your library", "calendar"),
    ({"discovery_type": "classic", "artist_library_album_count": 2, "listeners": 850},
     "A well-known album; you have 2 albums by this artist", "disc"),
    ({"discovery_category": "adjacent"}, "Close to genres you already love", "discover"),
    ({"discovery_category": "cross_genre", "genre_families": ["jazz", "electronic"]},
     "A bridge between jazz and electronic, both in your listening", "compass-spread"),
    ({"discovery_category": "adventurous"}, "A step away from your usual genres", "spark"),
    ({"discovery_category": "unclassified"}, "Few genre tags, so the fit is a guess", "info"),
    ({"owned": True}, "In your library", "check"),
)

# Run the production render functions with a minimal DOM. Browser checks separate from this
# contract exercise sizing, focus, request wiring and actual canvas/CORS behavior.
JS_RUNNER = """
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.attrs = {};
    this.textContent = '';
    this.namespaceURI = 'http://www.w3.org/2000/svg';
  }
  append(...nodes) { this.children.push(...nodes); }
  setAttribute(name, value) { this.attrs[name] = value; }
  addEventListener() {}
}
const context = {
  $: () => new Element('div'),
  isListeningRoom: () => false,
  listeningRoomPhone: new Element('media'),
  window: new Element('window'),
  document: {
    addEventListener() {},
    createElement: tag => new Element(tag),
    createElementNS: (_, tag) => new Element(tag),
  },
  cachedJSONRequest: () => Promise.resolve(null),
  artistImageRequests: new Map(),
  foldKey: name => name.trim().toLowerCase(),
  namedArtistTarget: name => ({type: 'artist', name}),
  encodeLibraryHash: target => '#' + target.type + '/' + (target.tag || target.name),
  URLSearchParams,
};
const source = fs.readFileSync(process.argv[1], 'utf8');
const boot = source.indexOf('  window.listeningRoomHome = ');
if (boot === -1) throw Error('Listening Room Home bootstrap missing');
vm.runInNewContext(
  source.slice(0, boot) + 'globalThis.render = renderReason; globalThis.tint = clampTint; globalThis.group = groupDiveAlbums; globalThis.previewReason = previewReason;})();',
  context,
);
const reasons = input.items.map(item => ({
  hero: context.render(item, 'hero'),
  card: context.render(item, 'card'),
  line: context.render(item, 'line'),
  panel: context.render(item, 'card', true),
}));
const release = input.items.find(item => item.why?.kind === 'new_release');
const collection = input.items.find(item => item.why?.kind === 'collection');
const previews = [context.previewReason(release.why, release.year, true),
  context.previewReason(collection.why, collection.year, false)];
console.log(JSON.stringify({reasons, previews, groups: context.group(input.albums), tints: input.colors.map(context.tint)}));
"""


class ListeningRoomReasonUiContractTests(unittest.TestCase):
    def test_server_fixtures_choose_the_expected_sentence(self):
        for fields, sentence, _ in REASONS:
            with self.subTest(fields=fields):
                self.assertEqual(build_pick_why(fields)["sentence"], sentence)
        self.assertIsNone(build_pick_why({"reason": "Internal reason"}))

    @unittest.skipUnless(shutil.which("node"), "Node is needed to exercise the browser renderer")
    def test_browser_uses_server_sentences_links_and_design_tint(self):
        colors = [(r / 10, g / 10, b / 10) for r in range(11) for g in range(11) for b in range(11)]
        items = [{**fields, "why": build_pick_why(fields)} for fields, _, _ in REASONS]
        items.append({"reason": "Internal reason"})
        result = subprocess.run(
            ["node", "-e", JS_RUNNER, str(HOME_JS)],
            input=json.dumps({
                "items": items,
                "colors": colors,
                "albums": [
                    {"artist": artist, "album": album}
                    for artist, album in (
                        ("Low", "I"), ("Broadcast", "Tender Buttons"), ("low", "I"),
                        ("Low", "II"), ("Low", "III"), ("Low", "IV"), ("Low", "V"),
                    )
                ],
            }),
            text=True, capture_output=True, check=False, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["previews"], [
            "New in 2026 · 1 album in your library",
            "A well-known album; you have 2 albums by this artist",
        ])
        for drawn, (_, sentence, icon) in zip(output["reasons"], REASONS):
            with self.subTest(sentence=sentence):
                self.assertEqual(drawn["line"]["textContent"], sentence)
                for size, cls in (("hero", "lr-reason-hero"), ("card", "lr-reason-text")):
                    label, heading, *_ = drawn[size]["children"]
                    self.assertEqual(label["children"][0]["children"][0]["attrs"]["href"], "#lr-" + icon)
                    self.assertEqual(heading["children"][0]["className"], cls)
                    self.assertEqual(heading["children"][0]["textContent"], sentence)
        self.assertEqual(output["reasons"][-1], dict(hero=None, card=None, line=None, panel=None))
        evidence = output["reasons"][4]["hero"]["children"][2]
        self.assertEqual(evidence["attrs"]["aria-label"], "Why this pick")
        seed, count, *extra = [row["children"][0] for row in evidence["children"]]
        self.assertEqual(seed["href"], "#genre/jazz")
        self.assertEqual(count["attrs"]["aria-label"], "41,234 listeners")
        self.assertEqual(len(extra), 2)
        artist = output["reasons"][2]["hero"]["children"][2]["children"][0]["children"][0]
        self.assertEqual(artist["href"], "#artist/Low")
        self.assertEqual(artist["children"][0]["textContent"], "L")
        self.assertEqual(output["reasons"][6]["hero"]["children"][0]["children"][1], "Why this artist")

        panel = output["reasons"][6]["panel"]["children"]
        self.assertEqual(panel[1]["children"][0]["textContent"],
                         "You have 2 albums by Low. These are the ones not in your library yet.")
        count = panel[2]["children"][0]["children"][0]
        self.assertEqual(count["children"][0]["children"][0]["attrs"]["href"], "#lr-disc")
        self.assertEqual(output["reasons"][7]["card"], output["reasons"][7]["panel"])
        self.assertEqual([[item["album"] for item in group] for group in output["groups"]],
                         [["I", "II", "III", "IV"], ["Tender Buttons"]])

        reference = runpy.run_path(str(REFERENCE))
        for sample, tint in zip(colors, output["tints"], strict=True):
            channels = [float(value) / 255 for value in re.findall(r"[\d.]+", tint)]
            self.assertEqual(len(channels), 3)
            for got, expected in zip(channels, reference["hero_tint"](sample), strict=True):
                self.assertAlmostEqual(got, expected, places=6)
            self.assertLessEqual(reference["luminance"](channels), 0.040001)
