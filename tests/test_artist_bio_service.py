"""Direct-import regressions for artist biography entity matching."""

import unittest

from app.services.artist_bio import resolve_artist_bio


class ArtistBioResolutionTests(unittest.TestCase):
    def test_uses_extract_only_when_page_qid_matches_music_entity(self):
        entities = [{
            "id": "Q42", "label": "Artist", "description": "British musician and singer",
        }]
        self.assertEqual(
            resolve_artist_bio(
                "Artist", entities,
                {"wikibase_item": "Q42", "type": "standard", "extract": "  Artist  is a musician.\nMore details."},
            ),
            "Artist is a musician.",
        )

    def test_mismatched_wikipedia_identity_uses_music_description(self):
        entities = [
            {"id": "Q1", "label": "Rainbow", "description": "English rock band"},
            {"id": "Q2", "label": "Rainbow", "description": "A colorful optical phenomenon"},
        ]
        result = resolve_artist_bio(
            "Rainbow", entities,
            {"wikibase_item": "Q2", "type": "standard", "extract": "Light refracted by water droplets."},
        )
        self.assertEqual(result, "English rock band")

    def test_disambiguation_page_does_not_supply_extract(self):
        entities = [{
            "id": "Q7", "label": "The Artist", "description": "French jazz musician",
        }]
        result = resolve_artist_bio(
            "The Artist", entities,
            {"wikibase_item": "Q7", "type": "disambiguation", "extract": "Wrong summary."},
        )
        self.assertEqual(result, "French jazz musician")

    def test_prefers_exact_label_and_ignores_non_music_entities(self):
        entities = [
            {"id": "Q1", "label": "Artist Tribute", "description": "A tribute event"},
            {"id": "Q2", "label": "The Artist", "description": "A rock band"},
            {"id": "Q3", "label": "Artist", "description": "American singer"},
        ]
        result = resolve_artist_bio("Artist", entities, {})
        self.assertEqual(result, "American singer")

    def test_empty_payload_returns_empty_bio(self):
        self.assertEqual(resolve_artist_bio("Unknown", [], {}), "")

    def test_long_extract_is_bounded_without_truncating_mid_word(self):
        entities = [{"id": "Q8", "label": "Artist", "description": "A musician"}]
        extract = "Artist is a musician. " + ("longword " * 60)
        result = resolve_artist_bio(
            "Artist", entities,
            {"wikibase_item": "Q8", "type": "standard", "extract": extract},
        )
        self.assertLessEqual(len(result), 280)
        self.assertTrue(result.endswith("…"))
        self.assertFalse(result.endswith("longw…"))


if __name__ == "__main__":
    unittest.main()
