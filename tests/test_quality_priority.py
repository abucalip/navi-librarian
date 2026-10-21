"""Regression tests for six-tier acquisition quality priorities and reordering UI."""
import json
import tempfile
from service_settings import set_slskd_settings
from settings_persistence import SettingsPersistence
from integrations.slskd.quality import quality_tier
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "static" / "app.js"


def load_quality_helpers(db_path, music_dir):
    defaults = {
        "navidrome_url": "http://localhost:4533",
        "navidrome_user": "",
        "navidrome_password": "",
        "lastfm_api_key": "",
        "listenbrainz_username": "",
        "music_library_path": str(music_dir),
        "slskd_url": "http://localhost:5030",
        "quality_priority": [
            "mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"
        ],
        "slskd_downloads_path": str(Path(music_dir) / "downloads" / "slskd" / "complete"),
    }
    music_dir_state = {"path": Path(music_dir)}
    persistence = SettingsPersistence(
        db_path,
        defaults,
        lambda: music_dir_state["path"],
        lambda path: music_dir_state.update({"path": path}),
        clock=lambda: 123.0,
    )
    return {
        "_slskd_quality_tier": quality_tier,
        "_discovery_settings_read": persistence.read,
        "_discovery_settings_write": persistence.write,
        "_DISCOVERY_SETTINGS_DEFAULTS": defaults,
        "MUSIC_DIR": music_dir_state["path"],
        "music_dir_state": music_dir_state,
    }

class QualityPriorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.music = self.root / "music"
        self.music.mkdir()
        self.ns = load_quality_helpers(self.root / "settings.sqlite3", self.music)

    def tearDown(self):
        self.temp.cleanup()

    def test_flac_with_explicit_16_bit_44100_hz_metadata_gets_new_tier(self):
        rank, tier = self.ns["_slskd_quality_tier"](
            {"sampleRate": 44100, "bitDepth": 16},
            "Album/01 - Track.flac",
            ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"],
        )
        self.assertEqual(tier, "flac_16_44")
        self.assertEqual(rank, 4)

    def test_flac_filename_can_identify_16_44_when_peer_omits_metadata(self):
        _, tier = self.ns["_slskd_quality_tier"](
            {}, "Album/01 Track [16-bit 44.1 kHz].flac",
            ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"],
        )
        self.assertEqual(tier, "flac_16_44")

    def test_filename_resolution_label_24_44_1_is_recognized_as_hires(self):
        _, tier = self.ns["_slskd_quality_tier"](
            {}, r"Tinariwen\\2024 - Idrache (Traces Of The Past) [24-44.1]\\01.flac",
            ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"],
        )
        self.assertEqual(tier, "flac_hires")

    def test_high_resolution_metadata_is_recognized(self):
        rank, tier = self.ns["_slskd_quality_tier"](
            {"sampleRate": 44100, "bitDepth": 24}, "Album/01.flac",
            ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"],
        )
        self.assertEqual(tier, "flac_hires")
        self.assertEqual(rank, 5)

    def test_unverified_flac_keeps_existing_fallback_tier(self):
        _, tier = self.ns["_slskd_quality_tier"](
            {}, "Album/01 - Track.flac",
            ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"],
        )
        self.assertEqual(tier, "flac_cd")

    def test_legacy_four_tier_settings_append_new_flac_tiers_without_reordering(self):
        old_order = ["mp3_192", "mp3_320", "flac_cd", "mp3_193_319"]
        self.ns["_discovery_settings_write"]({"quality_priority": old_order})
        settings = self.ns["_discovery_settings_read"]()
        self.assertEqual(settings["quality_priority"], old_order + ["flac_16_44", "flac_hires"])

    def test_legacy_five_tier_settings_append_hires_without_reordering(self):
        old_order = ["flac_16_44", "mp3_192", "flac_cd", "mp3_320", "mp3_193_319"]
        self.ns["_discovery_settings_write"]({"quality_priority": old_order})
        settings = self.ns["_discovery_settings_read"]()
        self.assertEqual(settings["quality_priority"], old_order + ["flac_hires"])

    def save_settings(self, **overrides):
        args = {
            "settings_read": self.ns["_discovery_settings_read"],
            "settings_write": self.ns["_discovery_settings_write"],
            "get_music_dir": lambda: self.music,
            "set_music_dir": lambda path: self.ns.update({"MUSIC_DIR": path}),
            "defaults": self.ns["_DISCOVERY_SETTINGS_DEFAULTS"],
        }
        args.update(overrides)
        return json.loads(set_slskd_settings(**args))

    def test_saving_six_tiers_preserves_user_order(self):
        order = ["flac_hires", "flac_16_44", "mp3_192", "flac_cd", "mp3_320", "mp3_193_319"]
        result = self.save_settings(
            slskd_url="http://localhost:5030",
            quality_priority_json=json.dumps(order),
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["quality_priority"], order)
        self.assertEqual(self.ns["_discovery_settings_read"]()["quality_priority"], order)

    def test_saving_old_four_tier_or_duplicate_priority_is_rejected(self):
        invalid_orders = [
            ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd"],
            ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_cd"],
            ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44"],
        ]
        for order in invalid_orders:
            with self.subTest(order=order):
                result = self.save_settings(
                    slskd_url="http://localhost:5030",
                    quality_priority_json=json.dumps(order),
                )
                self.assertFalse(result["ok"])

    def test_settings_ui_uses_sortable_rows_and_has_non_drag_controls(self):
        source = APP_SOURCE.read_text(encoding="utf-8")
        source += (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="qualityPriorityList"', source)
        self.assertIn("item.draggable = true", source)
        self.assertIn("data-quality-move", source)
        self.assertIn("dragover", source)
        self.assertIn("Move up / Move down buttons", source)
        self.assertNotIn('class="quality-priority"></select>', source)
        self.assertIn("FLAC 16-bit / 44.1 kHz", source)
        self.assertIn("FLAC Hi-Res (24-bit or above 44.1 kHz)", source)


if __name__ == "__main__":
    unittest.main()
