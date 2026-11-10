"""Live "now" fixtures (docs/RADIO_PLAYBACK_CONTRACT.md sections 3.2, 3.3 and 7) must keep the agreed shape,
and the Download rule (state ok and a play id) must hold in every fixture."""
import json
import unittest
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "android" / "contract-fixtures" / "librarian"
NOW_FIELDS = {"state", "raw_title", "artist", "title", "play_id", "in_library", "cover_url"}
NOW_STATES = {"ok", "no_metadata", "unparsed", "not_proxied", "unavailable", "idle"}


def body(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))["response"]["body"]


class RadioNowFixtureTests(unittest.TestCase):
    def test_every_single_station_fixture_has_the_contract_fields_and_a_known_state(self):
        for name in ("radio_now_ok.json", "radio_now_ok_waiting.json", "radio_now_no_metadata.json",
                     "radio_now_unparsed.json", "radio_now_not_proxied.json", "radio_now_unavailable.json",
                     "radio_now_idle.json"):
            with self.subTest(fixture=name):
                data = body(name)
                self.assertEqual(set(data), NOW_FIELDS)
                self.assertIn(data["state"], NOW_STATES)

    def test_ok_with_play_id_and_cover_is_the_download_case(self):
        data = body("radio_now_ok.json")
        self.assertEqual((data["state"], data["artist"], data["title"]), ("ok", "Pink Floyd", "Time"))
        self.assertIsNotNone(data["play_id"])
        self.assertTrue(data["in_library"])
        self.assertTrue(data["cover_url"].startswith("/api/owned/artwork/"))

    def test_ok_before_thirty_seconds_has_no_play_id_yet(self):
        data = body("radio_now_ok_waiting.json")
        self.assertEqual(data["state"], "ok")
        self.assertIsNone(data["play_id"])

    def test_states_without_a_parsed_song_carry_no_artist_title_or_download(self):
        for name in ("radio_now_no_metadata.json", "radio_now_unparsed.json", "radio_now_not_proxied.json",
                     "radio_now_unavailable.json", "radio_now_idle.json"):
            with self.subTest(fixture=name):
                data = body(name)
                self.assertIsNone(data["artist"])
                self.assertIsNone(data["title"])
                self.assertFalse(data["in_library"])

    def test_unparsed_keeps_the_raw_title_and_is_not_downloadable(self):
        data = body("radio_now_unparsed.json")
        self.assertEqual(data["raw_title"], "Station jingle")
        self.assertNotEqual(data["state"], "ok")

    def test_all_stations_fixture_lists_a_listening_station_and_an_idle_one(self):
        items = body("radio_now_all.json")["items"]
        by_id = {item["id"]: item for item in items}
        self.assertEqual(by_id["11"]["state"], "ok")
        self.assertIsNotNone(by_id["11"]["play_id"])
        self.assertEqual(by_id["12"]["state"], "idle")
        for item in items:
            self.assertEqual(set(item), NOW_FIELDS | {"id"})


if __name__ == "__main__":
    unittest.main()
