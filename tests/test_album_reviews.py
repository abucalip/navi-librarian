"""Review summary lines (deks) for the album page's Reviews tab: parsing and exact matching."""
import json
import unittest

from app.services import album_reviews as reviews


def pitchfork_page(*items, other=()):
    state = {"transformed": {"search": {"items": [{"items": list(other)}, {"items": list(items)}]}}}
    return "<html><script>window.__PRELOADED_STATE__ = " + json.dumps(state) + ";</script></html>"


def pitchfork_review(artist, album, dek, url="reviews/albums/11575-watershed"):
    return {"contentType": "review", "dangerousHed": f"<em>{album}</em>", "dangerousDek": dek,
            "subHed": {"name": artist, "url": url}, "url": "/" + url + "/"}


WATERSHED_DEK = "Swedish prog-metal greats unexpectedly fly their freak flag on their ninth full-length."


class DekTests(unittest.TestCase):
    def test_a_one_or_two_sentence_summary_is_kept_as_plain_text(self):
        self.assertEqual(reviews.clean_dek(f"<p>{WATERSHED_DEK}</p>"), WATERSHED_DEK)
        two = "A fine record. It rewards patience &amp; repeat plays."
        self.assertEqual(reviews.clean_dek(two), "A fine record. It rewards patience & repeat plays.")

    def test_inline_markup_does_not_leave_a_gap_before_punctuation(self):
        self.assertEqual(reviews.clean_dek("On <em>Mezzanine</em>, Massive Attack tried to escape trip-hop."),
                         "On Mezzanine, Massive Attack tried to escape trip-hop.")
        self.assertEqual(reviews.clean_dek("First line of text here.<br>Second line of text."),
                         "First line of text here. Second line of text.")

    def test_weekly_reissue_boilerplate_is_rejected(self):
        self.assertIsNone(reviews.clean_dek(
            "Each Sunday, Pitchfork takes an in-depth look at a significant album from the past, and an artist's best."))

    def test_a_removed_post_notice_is_rejected(self):
        self.assertIsNone(reviews.clean_dek(
            "This post has been removed because it promoted Nazi or Nazi-adjacent metal bands."))

    def test_the_opening_of_a_review_is_not_a_summary(self):
        self.assertIsNone(reviews.clean_dek(
            "It begins somewhere for everyone. There's the first song that grabs your attention. Then the album."))

    def test_cut_off_empty_and_oversized_text_is_rejected(self):
        self.assertIsNone(reviews.clean_dek("A page description that was cut off by the site before the end..."))
        self.assertIsNone(reviews.clean_dek("Too short."))
        self.assertIsNone(reviews.clean_dek(None))
        self.assertIsNone(reviews.clean_dek("x" * 301))

    def test_a_link_must_be_https(self):
        self.assertIsNone(reviews.review("Pitchfork", WATERSHED_DEK, "http://pitchfork.com/x/"))
        self.assertIsNone(reviews.review("Pitchfork", WATERSHED_DEK, "javascript:alert(1)"))


class HeadlineTests(unittest.TestCase):
    def test_real_headline_shapes_match(self):
        for title, artist, album in (
            ("Album Review: Opeth &#8211; Watershed", "Opeth", "Watershed"),
            ("Opeth: Watershed", "Opeth", "Watershed"),
            ("Opeth : In cauda venenum", "Opeth", "In Cauda Venenum"),
            ("Tony Allen and Hugh Masekela: Rejoice review – a joyous farewell", "Tony Allen & Hugh Masekela", "Rejoice"),
            ("Watershed – Opeth", "Opeth", "Watershed"),
            ("Radiohead: The King of Limbs review – eight new tracks", "Radiohead", "The King of Limbs"),
            ("Muse: The Wow! Signal review | Alexis Petridis's album of the week", "Muse", "The Wow! Signal"),
            ("The Smile: Cutouts review – as intricately crafted", "Smile", "Cutouts"),
            ("The Doors: Morrison Hotel Review", "Doors", "Morrison Hotel [Remastered]"),
        ):
            self.assertTrue(reviews.title_matches(title, artist, album), title)

    def test_a_reissue_review_is_a_review_of_the_album(self):
        self.assertEqual(reviews.match_key("Kind of Blue: 50th Anniversary Edition"), reviews.match_key("Kind of Blue"))
        self.assertEqual(reviews.match_key("Abbey Road - Super Deluxe Edition"), reviews.match_key("Abbey Road"))
        self.assertEqual(reviews.match_key("A Love Supreme [2002 Deluxe Edition] Disc 2"), reviews.match_key("A Love Supreme"))
        # A live album or a box set of the same name is a different release.
        self.assertNotEqual(reviews.match_key("A Love Supreme: Live in Seattle"), reviews.match_key("A Love Supreme"))
        self.assertNotEqual(reviews.match_key("The Wall: Live"), reviews.match_key("The Wall"))

    def test_a_catchphrase_before_the_title_is_ignored(self):
        self.assertTrue(reviews.title_matches("AAHHH! John Coltrane: Afro Blue Impressions", "John Coltrane", "Afro Blue Impressions"))
        self.assertTrue(reviews.title_matches("A CLASSIC IN MONO…John Coltrane: A Love Supreme", "John Coltrane", "A Love Supreme"))
        self.assertFalse(reviews.title_matches("Why I love Kind of Blue", "Miles Davis", "Kind of Blue"))
        self.assertFalse(reviews.title_matches("Best Jazz of 2020!", "Miles Davis", "Kind of Blue"))

    def test_news_lists_and_other_albums_do_not_match(self):
        for title, artist, album in (
            ("Opeth share new song &#8220;Sorceress&#8221;", "Opeth", "Sorceress"),
            ("Opeth from Worst to Best: 8-4", "Opeth", "Watershed"),
            ("Top 100 Songs of 2020", "Tony Allen", "Rejoice"),
            ("Rejoice", "Tony Allen", "Rejoice"),
            ("Opeth: Deliverance", "Opeth", "Watershed"),
            ("Anything", "", "Watershed"),
        ):
            self.assertFalse(reviews.title_matches(title, artist, album), title)

    def test_search_text_drops_trailing_editions_only(self):
        self.assertEqual(reviews.search_text("Pink Floyd", "The Dark Side Of The Moon[ Remastered]"),
                         "Pink Floyd The Dark Side Of The Moon")
        self.assertEqual(reviews.search_text("Khaled", "1,2,3 Soleils Disc 2"), "Khaled 1,2,3 Soleils")
        self.assertEqual(reviews.search_text("Oasis", "(What's the Story) Morning Glory?"),
                         "Oasis (What's the Story) Morning Glory?")


class PitchforkTests(unittest.TestCase):
    def test_a_reissue_review_is_used_for_the_original_album(self):
        page = pitchfork_page(pitchfork_review("Miles Davis", "Kind of Blue: 50th Anniversary Edition",
                                               "It's arguably the greatest jazz recording of all time, and this edition adds more.",
                                               "reviews/albums/13159-kind-of-blue-50th-anniversary-edition"))
        found = reviews.pick_pitchfork(reviews.parse_pitchfork_search(page), "Miles Davis", "Kind of Blue")
        self.assertEqual(found["url"], "https://pitchfork.com/reviews/albums/13159-kind-of-blue-50th-anniversary-edition/")

    def test_the_exact_review_comes_with_its_dek_and_full_link(self):
        page = pitchfork_page(pitchfork_review("Opeth", "Watershed", WATERSHED_DEK))
        found = reviews.pick_pitchfork(reviews.parse_pitchfork_search(page), "Opeth", "Watershed")
        self.assertEqual(found, {"source": "Pitchfork", "quote": WATERSHED_DEK,
                                 "url": "https://pitchfork.com/reviews/albums/11575-watershed/"})

    def test_a_different_album_or_artist_is_not_used(self):
        page = pitchfork_page(pitchfork_review("Opeth", "Deliverance", WATERSHED_DEK))
        results = reviews.parse_pitchfork_search(page)
        self.assertIsNone(reviews.pick_pitchfork(results, "Opeth", "Watershed"))
        self.assertIsNone(reviews.pick_pitchfork(results, "Mastodon", "Deliverance"))

    def test_only_reviews_count(self):
        news = {"contentType": "article", "dangerousHed": "Watershed", "dangerousDek": WATERSHED_DEK,
                "subHed": {"name": "Opeth", "url": "news/x"}}
        results = reviews.parse_pitchfork_search(pitchfork_page(other=[news]))
        self.assertEqual(results, [])

    def test_a_review_with_an_unusable_dek_gives_nothing(self):
        boiler = "Each Sunday, Pitchfork takes an in-depth look at a significant album from the past."
        page = pitchfork_page(pitchfork_review("Pink Floyd", "The Dark Side of the Moon", boiler, "reviews/albums/1-x"))
        self.assertIsNone(reviews.pick_pitchfork(reviews.parse_pitchfork_search(page), "Pink Floyd", "The Dark Side Of The Moon"))

    def test_pages_without_the_data_give_no_results(self):
        for page in ("", "<html></html>", "<script>window.__PRELOADED_STATE__ = {bad};</script>",
                     "<script>window.__PRELOADED_STATE__ = {\"transformed\": 1};</script>"):
            self.assertEqual(reviews.parse_pitchfork_search(page), [])


class GuardianTests(unittest.TestCase):
    def payload(self, title, trail="<strong>Cautious, joyful</strong> and wonderfully loose, the late drummer's last session."):
        return {"response": {"results": [{
            "webTitle": title, "webUrl": "https://www.theguardian.com/music/2020/mar/26/rejoice",
            "fields": {"trailText": trail}}]}}

    def test_the_review_headline_must_name_the_album(self):
        found = reviews.pick_guardian(
            self.payload("Tony Allen and Hugh Masekela: Rejoice review – joyous"), "Tony Allen & Hugh Masekela", "Rejoice")
        self.assertEqual(found["source"], "The Guardian")
        self.assertTrue(found["quote"].startswith("Cautious, joyful and wonderfully loose"))
        self.assertEqual(found["url"], "https://www.theguardian.com/music/2020/mar/26/rejoice")
        self.assertIsNone(reviews.pick_guardian(self.payload("Hugh Masekela: Another review"), "Tony Allen", "Rejoice"))

    def test_odd_payloads_are_ignored(self):
        for payload in (None, {}, {"response": {}}, {"response": {"results": [None, 3]}}, "text"):
            self.assertIsNone(reviews.pick_guardian(payload, "Tony Allen", "Rejoice"))
            self.assertIsNone(reviews.pick_guardian_tag(payload, "Tony Allen"))

    def test_a_useless_standfirst_falls_back_to_the_headline_tagline(self):
        # The standfirst of Kamasi Washington's review is only the label name.
        found = reviews.pick_guardian(
            self.payload("Kamasi Washington: Heaven and Earth review – a second album that sprawls and soars", "(Young Turks)"),
            "Kamasi Washington", "Heaven and Earth")
        self.assertEqual(found["quote"], "A second album that sprawls and soars.")
        # No usable standfirst and no tagline: nothing to quote.
        self.assertIsNone(reviews.pick_guardian(
            self.payload("Muse: The Wow! Signal review | Alexis Petridis's album of the week", "Short."), "Muse", "The Wow! Signal"))

    def test_the_artist_tag_must_name_the_artist_exactly(self):
        tags = {"response": {"results": [
            {"id": "world/acid-attack", "webTitle": "Acid attacks"},
            {"id": "music/massive-attack", "webTitle": "Massive Attack"}]}}
        self.assertEqual(reviews.pick_guardian_tag(tags, "Massive Attack"), "music/massive-attack")
        self.assertIsNone(reviews.pick_guardian_tag(tags, "Attack"))
        self.assertIsNone(reviews.pick_guardian_tag({"response": {"results": [{"id": "music/the-smile", "webTitle": "The Smile"}]}}, "Smile Smile"))


class WordPressTests(unittest.TestCase):
    def test_the_first_exact_headline_gives_its_address(self):
        results = [
            {"title": "Opeth from Worst to Best", "url": "https://www.angrymetalguy.com/worst-to-best/"},
            {"title": "Album Review: Opeth &#8211; Watershed", "url": "https://consequence.net/2008/06/album-review-watershed/"},
        ]
        self.assertEqual(reviews.pick_wordpress_post(results, "Opeth", "Watershed"),
                         "https://consequence.net/2008/06/album-review-watershed/")
        self.assertIsNone(reviews.pick_wordpress_post(results, "Opeth", "Ghost Reveries"))
        self.assertIsNone(reviews.pick_wordpress_post({"code": "rest_cannot_access"}, "Opeth", "Watershed"))

    def test_an_insecure_address_is_not_used(self):
        self.assertIsNone(reviews.pick_wordpress_post(
            [{"title": "Opeth: Watershed", "url": "http://example.com/x"}], "Opeth", "Watershed"))

    def test_the_dek_comes_from_the_page_description_in_either_attribute_order(self):
        for tag in (f'<meta property="og:description" content="{WATERSHED_DEK}"/>',
                    f'<meta content="{WATERSHED_DEK}" name="description">'):
            self.assertEqual(reviews.page_dek("<head>" + tag + "</head>"), WATERSHED_DEK)

    def test_an_unusable_description_falls_through_to_the_next_tag(self):
        page = ('<meta property="og:description" content="Cut off by the site..."/>'
                f'<meta name="description" content="{WATERSHED_DEK}"/>')
        self.assertEqual(reviews.page_dek(page), WATERSHED_DEK)
        self.assertIsNone(reviews.page_dek("<html></html>"))


class PickTests(unittest.TestCase):
    def item(self, source, url):
        return {"source": source, "quote": WATERSHED_DEK, "url": url}

    def test_three_at_most_one_per_outlet_in_source_order(self):
        found = [None, self.item("A", "https://a/1"), self.item("A", "https://a/2"), self.item("B", "https://b/1"),
                 self.item("C", "https://c/1"), self.item("D", "https://d/1")]
        self.assertEqual([r["source"] for r in reviews.pick_reviews(found)], ["A", "B", "C"])

    def test_nothing_found_gives_an_empty_list(self):
        self.assertEqual(reviews.pick_reviews([None, None]), [])


if __name__ == "__main__":
    unittest.main()
