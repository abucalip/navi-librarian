"""Apple Music editorial notes, read from an album page's embedded data."""
import json
import unittest

from app.services.apple_description import paragraphs_from_markup, parse_editorial_notes


def page(notes):
    data = {"data": [{"data": {"sections": [{"items": [{"modalPresentationDescriptor": {"paragraphText": notes}}]}]}}]}
    return '<html><script type="application/json" id="serialized-server-data">' + json.dumps(data) + "</script></html>"


class ParserTests(unittest.TestCase):
    def test_notes_become_plain_paragraphs(self):
        markup = "First <i>paragraph</i> &amp; more.<br />\nSecond paragraph.<br /><br />Third."
        self.assertEqual(paragraphs_from_markup(markup), ["First paragraph & more.", "Second paragraph.", "Third."])

    def test_a_leading_bold_badge_is_not_part_of_the_text(self):
        self.assertEqual(paragraphs_from_markup("<b>100 Best Albums</b> In three albums, <b>bold</b> later."),
                         ["In three albums, bold later."])

    def test_notes_are_found_inside_the_page_data(self):
        self.assertEqual(parse_editorial_notes(page("One.<br />Two.")), ["One.", "Two."])

    def test_a_page_without_notes_gives_none(self):
        self.assertIsNone(parse_editorial_notes("<html>no data</html>"))
        self.assertIsNone(parse_editorial_notes('<script type="application/json" id="serialized-server-data">{"data": []}</script>'))
        self.assertIsNone(parse_editorial_notes('<script type="application/json" id="serialized-server-data">not json</script>'))


if __name__ == "__main__":
    unittest.main()
