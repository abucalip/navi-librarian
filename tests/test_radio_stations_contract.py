"""Radio station fixtures (docs/RADIO_PLAYBACK_CONTRACT.md sections 3.1, 3.5, 7) must keep the agreed fields."""
import json
import unittest
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "android" / "contract-fixtures" / "librarian"
STATION_FIELDS = {"id", "name", "proxied", "stream_url", "playable_url", "homepage_url", "logo_url",
                  "favourite", "tags", "last_played_at"}


def body(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["response"]["body"]


class RadioStationFixtureTests(unittest.TestCase):
    def test_every_station_has_the_contract_fields_and_a_server_logo_path(self):
        items = body("radio_stations.json")["items"]
        self.assertGreaterEqual(len(items), 3)
        for item in items:
            with self.subTest(station=item["id"]):
                self.assertEqual(set(item), STATION_FIELDS)
                self.assertEqual(item["logo_url"], f"/api/radio/stations/{item['id']}/logo")
                self.assertNotIn("://", item["logo_url"])

    def test_fixture_shows_favourites_first_a_relayed_station_and_an_unplayed_one(self):
        items = body("radio_stations.json")["items"]
        self.assertTrue(items[0]["favourite"])
        self.assertTrue(items[0]["proxied"])
        self.assertIsNotNone(items[0]["homepage_url"])
        self.assertIsNone(items[-1]["last_played_at"])
        self.assertFalse(items[-1]["proxied"])
        self.assertEqual(items[-1]["playable_url"], items[-1]["stream_url"])

    def test_empty_list_fixture_has_no_items(self):
        self.assertEqual(body("radio_stations_empty.json"), {"items": []})

    def test_favourite_and_tags_fixtures_echo_the_saved_values(self):
        self.assertEqual(body("radio_station_favourite.json"), {"id": "11", "favourite": True})
        self.assertEqual(body("radio_station_tags.json"), {"id": "11", "tags": ["rock", "local"]})

    def test_logo_fixture_stores_only_the_type_and_size_of_the_image(self):
        self.assertEqual(body("radio_station_logo.json")["content_type"], "image/png")
        self.assertGreater(body("radio_station_logo.json")["bytes"], 0)


if __name__ == "__main__":
    unittest.main()
