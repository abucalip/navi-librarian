"""Wikipedia as the album description when Apple Music has none: article choice and lead text."""
import unittest

from app.services import album_wikipedia as wiki


def page(key, title, description, excerpt=""):
    return {"key": key, "title": title, "description": description, "excerpt": excerpt}


class PickTests(unittest.TestCase):
    def test_the_disambiguated_album_article_is_found(self):
        pages = [page("Tony_Allen_(musician)", "Tony Allen (musician)", "Nigerian drummer"),
                 page("Rejoice_(Tony_Allen_and_Hugh_Masekela_album)", "Rejoice (Tony Allen and Hugh Masekela album)",
                      "2020 studio album by Tony Allen and Hugh Masekela")]
        self.assertEqual(wiki.pick_album_article(pages, "Tony Allen & Hugh Masekela", "Rejoice"),
                         "Rejoice_(Tony_Allen_and_Hugh_Masekela_album)")

    def test_a_plain_title_needs_the_artist_in_the_description(self):
        pages = [page("Morrison_Hotel", "Morrison Hotel", "1970 studio album by the Doors")]
        self.assertEqual(wiki.pick_album_article(pages, "The Doors", "Morrison Hotel [Remastered]"), "Morrison_Hotel")
        self.assertIsNone(wiki.pick_album_article(pages, "Another Band", "Morrison Hotel"))

    def test_same_titled_things_that_are_not_this_album_are_skipped(self):
        pages = [page("Animals", "Animals", "Kingdom of animals"),
                 page("Animals_(Pink_Floyd_album)", "Animals (Pink Floyd album)", "1977 studio album by Pink Floyd"),
                 page("Animals_(Maroon_5_song)", "Animals (Maroon 5 song)", "2014 song by Maroon 5")]
        self.assertEqual(wiki.pick_album_article(pages, "Pink Floyd", "Animals"), "Animals_(Pink_Floyd_album)")
        self.assertIsNone(wiki.pick_album_article(pages[:1] + pages[2:], "Pink Floyd", "Animals"))

    def test_no_pages_or_bad_data_gives_none(self):
        for pages in (None, [], [None, {}], [{"title": "X"}]):
            self.assertIsNone(wiki.pick_album_article(pages, "Artist", "X"))
        self.assertIsNone(wiki.pick_album_article([page("X", "X", "album by Artist")], "", "X"))


class SummaryTests(unittest.TestCase):
    def test_the_lead_becomes_paragraphs_with_source_link_and_licence(self):
        summary = {"extract": "Rejoice is an album.\nIt was recorded in 2010.",
                   "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Rejoice"}}}
        self.assertEqual(wiki.description_from_summary(summary), {
            "paragraphs": ["Rejoice is an album.", "It was recorded in 2010."], "source": "Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Rejoice", "license": "CC BY-SA 4.0"})

    def test_disambiguation_empty_or_unlinked_answers_give_none(self):
        link = {"desktop": {"page": "https://en.wikipedia.org/wiki/X"}}
        for summary in (None, {}, {"type": "disambiguation", "extract": "X may refer to", "content_urls": link},
                        {"extract": "  ", "content_urls": link}, {"extract": "Text."},
                        {"extract": "Text.", "content_urls": {"desktop": {"page": "http://x"}}}):
            self.assertIsNone(wiki.description_from_summary(summary))


if __name__ == "__main__":
    unittest.main()
