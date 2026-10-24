"""Direct-import regression tests for acquisition persistence."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from acquisition.state import list_jobs, reactivate_dismissed_job, save_job


class AcquisitionStateStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "state.sqlite3"
        self.now = [100.0]

        def init():
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    CREATE TABLE IF NOT EXISTS discovery_acquisitions (
                        artist_key TEXT NOT NULL, album_key TEXT NOT NULL,
                        artist TEXT NOT NULL, album TEXT NOT NULL, status TEXT NOT NULL,
                        details_json TEXT NOT NULL, candidate_json TEXT NOT NULL,
                        settings_json TEXT NOT NULL, created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY (artist_key, album_key)
                    )
                """)

        self.services = {
            "init": init,
            "db_path": self.db_path,
            "music_key": lambda value: " ".join(value.casefold().split()),
            "clock": lambda: self.now[0],
        }

    def test_save_and_list_round_trip_with_normalized_identity(self):
        save_job(" Artist ", "ALBUM", "downloading", {"percent": 25},
                 candidate={"username": "peer"}, settings={"quality": ["flac"]},
                 services=self.services)
        jobs = list_jobs(services=self.services)
        self.assertEqual(len(jobs), 1)
        self.assertEqual((jobs[0]["artist_key"], jobs[0]["album_key"]), ("artist", "album"))
        self.assertEqual(jobs[0]["status"], "downloading")
        self.assertEqual(jobs[0]["details"]["percent"], 25)
        self.assertEqual(jobs[0]["candidate"]["username"], "peer")
        self.assertEqual(jobs[0]["settings"]["quality"], ["flac"])

    def test_write_without_metadata_keeps_request_metadata_and_metadata_replaces_it(self):
        lens = {"lens": "deep_cuts"}
        save_job("Artist", "Album", "downloading", {"metadata": lens}, services=self.services)
        self.now[0] = 200.0
        save_job("Artist", "Album", "monitor_error", {"message": "restart"}, services=self.services)
        self.assertEqual(list_jobs(services=self.services)[0]["details"]["metadata"], lens)
        self.now[0] = 300.0
        save_job("Artist", "Album", "no_matches", {"metadata": {}}, services=self.services)
        self.assertEqual(list_jobs(services=self.services)[0]["details"]["metadata"], {})

    def test_empty_candidate_and_settings_do_not_erase_existing_values(self):
        save_job("Artist", "Album", "downloading", {"quality_summary": ["mp3_320"]},
                 candidate={"username": "peer"}, settings={"downloads": "/safe"},
                 services=self.services)
        self.now[0] = 200.0
        save_job("Artist", "Album", "monitor_error", {"message": "restart"},
                 services=self.services)
        job = list_jobs(services=self.services)[0]
        self.assertEqual(job["candidate"], {"username": "peer"})
        self.assertEqual(job["settings"], {"downloads": "/safe"})
        self.assertEqual(job["details"]["quality_summary"], ["mp3_320"])
        self.assertEqual(job["updated_at"], 200.0)

    def test_reactivate_dismissed_job_clears_stale_source_and_persists_retry_metadata(self):
        save_job(
            "Artist", "Album", "dismissed", {"message": "cleaned"},
            candidate={"username": "old-peer", "files": [{"filename": "old/01.flac"}]},
            settings={"slskd_downloads_path": "/old"},
            services=self.services,
        )
        self.now[0] = 250.0

        result = reactivate_dismissed_job(
            " ARTIST ", "Album", {"mbid": "release-id"}, services=self.services,
        )

        self.assertTrue(result)
        job = list_jobs(services=self.services)[0]
        self.assertEqual(job["status"], "retry_requested")
        self.assertEqual(job["candidate"], {})
        self.assertEqual(job["settings"], {})
        self.assertEqual(job["updated_at"], 250.0)
        self.assertEqual(job["details"], {
            "status": "retry_requested",
            "message": "Retry requested; searching for available sources.",
            "retry_requested_at": 250.0,
            "metadata": {"mbid": "release-id"},
        })

    def test_reactivation_refuses_missing_or_non_dismissed_rows_without_mutation(self):
        self.assertFalse(reactivate_dismissed_job(
            "Artist", "Missing", {}, services=self.services,
        ))
        save_job(
            "Artist", "Album", "downloading", {"percent": 40},
            candidate={"username": "peer", "files": [{"filename": "Album/01.flac"}]},
            settings={"slskd_downloads_path": "/downloads"},
            services=self.services,
        )
        before = list_jobs(services=self.services)[0]

        self.assertFalse(reactivate_dismissed_job(
            "Artist", "Album", {"mbid": "new-id"}, services=self.services,
        ))

        after = list_jobs(services=self.services)[0]
        self.assertEqual(after, before)

    def test_invalid_identity_is_rejected_before_database_write(self):
        with self.assertRaises(ValueError):
            save_job(" ", "Album", "downloading", services=self.services)
        self.assertEqual(list_jobs(services=self.services), [])

    def test_malformed_json_is_decoded_conservatively(self):
        self.services["init"]()
        with sqlite3.connect(self.db_path) as db:
            db.execute(
                "INSERT INTO discovery_acquisitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("artist", "album", "Artist", "Album", "failed", "{", "[", "{", 1, 1),
            )
        job = list_jobs(services=self.services)[0]
        self.assertEqual(job["details"], {"status": "failed"})
        self.assertEqual(job["candidate"], {})
        self.assertEqual(job["settings"], {})
