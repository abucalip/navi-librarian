"""Source-contract regressions for the Discover music control composition.

These tests protect the two-phase structure of the Recommendations section — a request
group that builds a set, and a result toolbar that narrows it — plus the client wiring
that the reorder could silently break. They read the templates as source and never open a
browser, so they do not replace the documented manual browser checklist.
"""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "templates" / "index.html"
LOGIN_HTML = ROOT / "app" / "templates" / "login.html"
APP_JS = ROOT / "static" / "app.js"
APP_CSS = ROOT / "static" / "app.css"

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "order")

    def __init__(self, tag, attrs, parent, order):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []
        self.parent = parent
        self.order = order

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()


class TreeBuilder(HTMLParser):
    """Minimal element tree with document order, enough for structural assertions."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.roots = []
        self.stack = []
        self.counter = 0

    def _add(self, tag, attrs):
        parent = self.stack[-1] if self.stack else None
        node = Node(tag, attrs, parent, self.counter)
        self.counter += 1
        (parent.children if parent is not None else self.roots).append(node)
        return node

    def handle_starttag(self, tag, attrs):
        node = self._add(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._add(tag, attrs)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


def parse(html):
    builder = TreeBuilder()
    builder.feed(html)
    return builder.roots


def with_descendants(root):
    """``root`` plus every element inside it, in document order."""
    return [root] + list(root.descendants())


def find(nodes, **attrs):
    tag = attrs.pop("tag", None)
    for node in nodes:
        if tag is not None and node.tag != tag:
            continue
        if all(node.attrs.get(name) == value for name, value in attrs.items()):
            return node
    return None


def find_by_class(nodes, *classes):
    for node in nodes:
        if set(classes) <= node.classes:
            return node
    return None


def ids_in(nodes):
    return [node.attrs["id"] for node in nodes if "id" in node.attrs]


class RecommendationsUIContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")

        cls.all_nodes = []
        for root in parse(cls.html):
            cls.all_nodes.extend(with_descendants(root))

        cls.section = find(cls.all_nodes, id="recommendations")
        if cls.section is None:
            raise AssertionError("index.html has no #recommendations section")
        cls.section_nodes = with_descendants(cls.section)
        cls.panel = find(cls.section_nodes, tag="div", **{"class": "panel"})
        if cls.panel is None:
            raise AssertionError("#recommendations has no .panel wrapper")

    def test_section_opens_with_a_description_before_any_control(self):
        """Every neighbouring discovery section explains itself; this one now does too."""
        heading = find(self.panel.children, tag="h2", id="recommendationsHeading")
        self.assertIsNotNone(heading)

        following = [child for child in self.panel.children if child.order > heading.order]
        self.assertTrue(following, "the heading is the panel's last element")
        first = following[0]
        self.assertEqual(first.tag, "p", "the element after the heading is not a paragraph")
        self.assertNotIn(first.classes, [{"controls"}, {"discovery-controls"}])
        self.assertEqual(
            [node.tag for node in with_descendants(first) if node.tag in {"input", "select", "button"}],
            [],
            "the description paragraph contains a control",
        )

    def test_request_phase_keeps_the_primary_action_with_its_only_parameter(self):
        request = find_by_class(self.section_nodes, "controls", "request-controls")
        self.assertIsNotNone(request, "no .controls.request-controls group")
        self.assertEqual(ids_in(with_descendants(request)), ["count", "loadRecommendations"])

        toolbar = find_by_class(self.section_nodes, "results-toolbar")
        self.assertIsNotNone(toolbar, "no .results-toolbar block")
        self.assertLess(
            request.order, toolbar.order,
            "the request group must precede the result toolbar",
        )

    def test_result_toolbar_introduces_the_count_then_names_the_refinement(self):
        toolbar = find_by_class(self.section_nodes, "results-toolbar")
        self.assertIsNotNone(toolbar, "no .results-toolbar block")

        self.assertEqual(
            ids_in(with_descendants(toolbar))[:3],
            ["recommendationCount", "recommendationFiltersLabel", "recommendationSearch"],
            "the toolbar order is count -> label -> refinement controls",
        )

        cards = find(self.all_nodes, id="recommendationCards")
        self.assertIsNotNone(cards)
        self.assertNotIn(cards, with_descendants(toolbar), "the card grid must leave the toolbar")
        self.assertLess(toolbar.order, cards.order)

    def test_refinement_controls_are_a_named_group(self):
        toolbar = find_by_class(self.section_nodes, "results-toolbar")
        group = find_by_class(with_descendants(toolbar), "discovery-controls")
        self.assertIsNotNone(group, "no .discovery-controls inside the toolbar")
        self.assertEqual(group.attrs.get("role"), "group")

        labelledby = group.attrs.get("aria-labelledby")
        self.assertTrue(labelledby, "the refinement group has no accessible name")
        for token in labelledby.split():
            matches = [node for node in self.all_nodes if node.attrs.get("id") == token]
            self.assertEqual(len(matches), 1, f"aria-labelledby token {token!r} is not unique")
            self.assertEqual(matches[0].tag, "p")
            self.assertIn(matches[0], with_descendants(toolbar))

    def test_the_refinement_controls_appear_once_in_the_document(self):
        """The section-scoped CSS override only holds while this stays unique."""
        matches = [node for node in self.all_nodes if "discovery-controls" in node.classes]
        self.assertEqual(len(matches), 1)

    def test_document_ids_are_unique(self):
        found = re.findall(r'id="([^"]+)"', self.html)
        duplicates = sorted({value for value in found if found.count(value) > 1})
        self.assertEqual(duplicates, [])

    def test_every_client_wiring_id_still_resolves(self):
        """The reorder moved nodes; app.js still looks them up by id."""
        template_ids = set(re.findall(r'id="([^"]+)"', self.html))
        template_ids |= set(re.findall(r'id="([^"]+)"', LOGIN_HTML.read_text(encoding="utf-8")))
        # Elements the script creates itself (albumModalArtwork) carry their id from app.js.
        template_ids |= set(re.findall(r"\.id = '([^']+)'", self.js))
        referenced = set(re.findall(r"\$\('([A-Za-z0-9_\-]+)'\)", self.js))
        self.assertEqual(sorted(referenced - template_ids), [])

        for name in (
            "count", "loadRecommendations", "recommendationSearch", "categoryFilter",
            "recommendationSort", "recommendationCount", "recommendationCards",
            "recommendationDebug", "recommendationFiltersLabel",
        ):
            self.assertIn(f'id="{name}"', self.html, f"#{name} is missing from index.html")

    def test_rhythm_rules_are_section_scoped(self):
        # The two phases get a wider interval between them than inside either group.
        self.assertIn(".controls.request-controls { margin: 20px 0 30px; }", self.css)
        self.assertIn(".results-toolbar { margin: 0 0 18px; }", self.css)
        self.assertIn(".results-toolbar .discovery-controls { margin: 0; }", self.css)
        self.assertIn("#recommendationCount { margin: 0 0 12px;", self.css)
        # The shared rule the other discovery sections rely on is untouched.
        self.assertIn(
            ".controls { display: flex; align-items: center; gap: 9px; "
            "flex-wrap: wrap; margin: 18px 0 14px; }",
            self.css,
        )


class RankedRowContractTests(unittest.TestCase):
    """Discover music ranked rows (DESIGN_SYSTEM.md 9.4, 8). Source contracts only."""

    @classmethod
    def setUpClass(cls):
        cls.html = INDEX_HTML.read_text(encoding="utf-8")
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = APP_CSS.read_text(encoding="utf-8")

    def test_results_use_the_ranked_list_not_the_card_grid(self):
        self.assertIn('id="recommendationCards" class="ranked-list"', self.html)
        self.assertNotIn('id="recommendationCards" class="cards"', self.html)

    def test_numerals_only_when_the_sort_basis_is_a_real_order(self):
        self.assertIn("if (sort === 'artist') return {label: 'Sorted A–Z by artist', numbered: false};", self.js)
        self.assertIn("filtered.forEach((item, index) => {", self.js)
        self.assertIn("basis.numbered ? index + 1 : null", self.js)
        self.assertIn("numeral.setAttribute('aria-hidden', 'true');", self.js)

    def test_score_and_popularity_hide_numerals_when_values_are_missing(self):
        self.assertIn("complete('discovery_score')", self.js)
        self.assertIn("complete('lastfm_listeners')", self.js)

    def test_sort_basis_is_named_in_the_count_line(self):
        self.assertIn("· ${basis.label}`", self.js)

    def test_row_keeps_modal_open_and_separate_get_and_dismiss_stops(self):
        self.assertIn(".ranked-row[data-album-title]", self.js)
        start = self.js.index("function buildRecommendationRow(")
        builder = self.js[start:self.js.index("$('recommendationSearch').addEventListener", start)]
        self.assertIn("makeAlbumCardInteractive(row, artist, album, item);", builder)
        self.assertIn("actions.append(createGetButton(artist, album, item));", builder)
        self.assertIn("dismissButton.setAttribute('aria-label', 'Not for me: ' + album);", builder)
        self.assertNotIn("innerHTML", builder, "rows must be built with text APIs only")

    def test_failed_generation_is_reported_in_the_count_line(self):
        self.assertIn("'Recommendations could not be loaded: ' + error.message", self.js)

    def test_row_motion_is_transform_only(self):
        self.assertIn("transform: scaleY(0); transition: transform var(--dur) var(--ease-out);", self.css)


if __name__ == "__main__":
    unittest.main()
