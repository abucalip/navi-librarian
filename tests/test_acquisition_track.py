"""Single-song Get: search choice, destination, safe import, watcher, dismissal and status."""
import os
import re
import tempfile
import threading
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch

from acquisition import completion, track_search, track_service
from acquisition.track_destination import DestinationError, plan_destination
from acquisition.track_import import import_track_file
from integrations.slskd.quality import quality_tier
from integrations.slskd.search import album_path_match

PRIORITY = ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"]


def music_key(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").casefold())


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeLibrarian:
    """The helpers track_service reads from the server, with an in-memory acquisition table."""

    def __init__(self, root):
        self.root = Path(root)
        self.MUSIC_DIR = self.root / "music"
        self.downloads = self.root / "downloads"
        self.MUSIC_DIR.mkdir()
        self.downloads.mkdir()
        self.jobs = {}
        self._DISCOVERY_IMPORT_TRANSITION_LOCK = threading.RLock()
        self._DISCOVERY_ACQUIRE_ACTIVE = set()
        self._DISCOVERY_SETTINGS_DEFAULTS = {"quality_priority": PRIORITY, "slskd_downloads_path": str(self.downloads)}
        self._DISCOVERY_PROGRESS_SNAPSHOTS = type("S", (), {"estimate": lambda *a: None})()
        self._music_key = music_key
        self._slskd_album_path_match = album_path_match
        self._slskd_quality_tier = quality_tier
        self._discovery_safe_folder_name = completion.safe_folder_name
        self.queued, self.cleaned, self.transfers = [], [], []
        self.queue_error = None
        self.start_state = True
        self.clean_result = True

    def _slskd_config(self):
        return "http://slskd", "key", {"quality_priority": PRIORITY, "slskd_downloads_path": str(self.downloads),
                                       "slskd_api_key": "secret"}

    def _identity(self, artist, album):
        return music_key(artist), music_key(album)

    def _discovery_list_acquisition_jobs(self):
        return [dict(job) for job in self.jobs.values()]

    def _discovery_save_acquisition_job(self, artist, album, status, details=None, candidate=None, settings=None):
        key = self._identity(artist, album)
        previous = self.jobs.get(key, {})
        self.jobs[key] = {
            "artist_key": key[0], "album_key": key[1], "artist": artist, "album": album, "status": status,
            "details": {"status": status, **(details or {})},
            "candidate": candidate if candidate else previous.get("candidate", {}),
            "settings": settings if settings else previous.get("settings", {}),
        }

    def _discovery_is_dismissed(self, artist, album):
        return self.jobs.get(self._identity(artist, album), {}).get("status") == "dismissed"

    def _discovery_update_acquisition_status(self, artist, album, status, details=None):
        if status != "dismissed" and self._discovery_is_dismissed(artist, album):
            return False
        self._discovery_save_acquisition_job(artist, album, status, details)
        return True

    def _discovery_reactivate_dismissed_acquisition(self, artist, album, metadata=None):
        key = self._identity(artist, album)
        self.jobs[key].update(status="retry_requested", candidate={}, details={"metadata": metadata or {}})
        return True

    def _discovery_queue_candidate_unless_dismissed(self, artist, album, base_url, headers, username, files):
        if self.queue_error:
            raise self.queue_error
        self.queued.append((username, files))
        return object()

    def _slskd_queue_failure_action(self, exc):
        return {400: "retry_source", 401: "fatal"}.get(getattr(getattr(exc, "response", None), "status_code", None), "uncertain")

    def _slskd_candidate_start_state(self, base_url, headers, candidate, timeout=8):
        return self.start_state

    def _discovery_cancel_and_clean_source(self, download_root, candidate, base_url, headers):
        self.cleaned.append(candidate)
        return self.clean_result

    def _slskd_download_transfer_files(self, base_url, headers, username):
        return list(self.transfers)

    def _discovery_match_completed_album_files(self, folder, candidate):
        return completion.match_completed_album_files(folder, candidate)

    def _discovery_inspect_completed_album(self, download_root, candidate):
        return completion.inspect_completed_album(
            download_root, candidate, safe_folder_name=completion.safe_folder_name,
            filename_key=completion.filename_key, match_files=completion.match_completed_album_files)


def peer(user, *files, speed=100):
    return {"username": user, "uploadSpeed": speed, "files": [{"filename": f, "size": s} for f, s in files]}


class TrackSearchTests(unittest.TestCase):
    def test_queries_are_bounded_and_include_masked_artist(self):
        queries = track_search.track_search_queries("Pink Floyd", "Time (2011 Remaster)")
        self.assertEqual(queries[0], "Pink Floyd Time")
        self.assertIn("*ink Floyd Time", queries)
        self.assertLessEqual(len(queries), 5)
        self.assertEqual(track_search.track_search_queries("", "x"), [])

    def test_file_is_song_accepts_only_the_requested_recording(self):
        ok = partial(track_search.file_is_song, artist="Pink Floyd", album="The Dark Side of the Moon", title="Time")
        for name in ("Pink Floyd/Dark Side/04 - Time.flac", "x\\Pink Floyd - Time.mp3", "x/04. Pink Floyd - Time (Remastered).flac",
                     "x/Time.mp3", "x/04 Time [320kbps].mp3"):
            with self.subTest(name=name):
                self.assertTrue(ok(name))
        for name in ("x/04 - Time (Live).flac", "x/Time (Radio Edit).mp3", "x/Time Remix.mp3", "x/Time After Time.mp3",
                     "x/Another Time.mp3", "Pink Floyd/Live at Pompeii/04 - Time.flac", "x/Timeless.mp3", "x/Sometime.mp3"):
            with self.subTest(name=name):
                self.assertFalse(ok(name))

    def test_edition_notes_in_the_title_do_not_block_a_match(self):
        for title in ("Time (2011 Remaster)", "Time - 2011 Remaster", "Time [Mono]", "Time (Deluxe Edition)"):
            with self.subTest(title=title):
                self.assertTrue(track_search.file_is_song("x/04 - Time.flac", "Pink Floyd", "Dark Side", title))
        self.assertFalse(track_search.file_is_song("x/04 - Time (Live).flac", "Pink Floyd", "Dark Side", "Time (2011 Remaster)"))
        self.assertEqual(track_search.core_title("Song (feat. Someone)"), "Song (feat. Someone)")

    def test_a_requested_version_word_is_allowed(self):
        self.assertTrue(track_search.file_is_song("x/01 - Song (Live).mp3", "A", "Album", "Song (Live)"))
        self.assertTrue(track_search.file_is_song("x/Live/01 - Song.mp3", "A", "Live at Wembley", "Song"))
        self.assertFalse(track_search.file_is_song("x/01 - Song.mp3", "A", "Album", "Song (Live)"))

    def extract(self, payload, title="Time"):
        return track_search.extract_track_candidates(
            payload, "Pink Floyd", "The Dark Side of the Moon", title, PRIORITY,
            music_key=music_key, album_path_match=album_path_match, quality_tier=quality_tier)

    def test_candidates_are_ordered_by_tier_then_album_then_speed(self):
        payload = [
            peer("flacuser", ("Music/Pink Floyd/Dark Side of the Moon/04 Time.flac", 30)),
            peer("mp3user", ("Music/Pink Floyd/Greatest Hits/Time 320kbps.mp3", 9), speed=50),
            peer("mp3album", ("Music/Pink Floyd/The Dark Side of the Moon/Time 320kbps.mp3", 9), speed=10),
            peer("other", ("Music/Someone Else/Time.mp3", 9)),
            peer("empty", ("Music/Pink Floyd/Time.mp3", 0)),
            peer("wrongsong", ("Music/Pink Floyd/Money.mp3", 9)),
        ]
        names = [item["username"] for item in self.extract(payload)]
        self.assertEqual(names, ["mp3album", "mp3user", "flacuser"])

    def test_tiers_outside_the_priority_are_dropped(self):
        payload = [peer("low", ("Pink Floyd/Time 128kbps.mp3", 9)), peer("wav", ("Pink Floyd/Time.wav", 9))]
        self.assertEqual(self.extract(payload), [])

    def test_a_file_without_a_folder_or_repeated_listing_is_handled(self):
        payload = [peer("a", ("Pink Floyd - Time.mp3 320kbps", 9)),
                   peer("b", ("Pink Floyd/Time 320kbps.mp3", 9), ("pink floyd/time 320kbps.mp3", 9))]
        self.assertEqual([c["username"] for c in self.extract(payload)], ["b"])


class DestinationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.plan = partial(plan_destination, self.root, safe_folder_name=completion.safe_folder_name, music_key=music_key)

    def test_a_missing_artist_gets_the_usual_new_folders(self):
        self.assertEqual(self.plan("Artist", "Album"), self.root / "Artist" / "Album")

    def test_an_existing_album_folder_is_used(self):
        (self.root / "Artist" / "Album").mkdir(parents=True)
        self.assertEqual(self.plan("Artist", "Album"), self.root / "Artist" / "Album")

    def test_a_year_suffixed_folder_is_reused_not_duplicated(self):
        for name in ("Album (1999)", "Other Album"):
            (self.root / "Artist" / name).mkdir(parents=True)
        self.assertEqual(self.plan("Artist", "Album"), self.root / "Artist" / "Album (1999)")
        (self.root / "Artist" / "Album (1999)").rmdir()
        (self.root / "Artist" / "1999 - Album").mkdir()
        self.assertEqual(self.plan("Artist", "Album"), self.root / "Artist" / "1999 - Album")

    def test_the_artist_folder_may_differ_in_case_or_punctuation(self):
        (self.root / "ARTIST!" / "Album").mkdir(parents=True)
        self.assertEqual(self.plan("artist", "Album"), self.root / "ARTIST!" / "Album")

    def test_two_matching_folders_refuse(self):
        for name in ("Album (1999)", "Album [2005]"):
            (self.root / "Artist" / name).mkdir(parents=True)
        with self.assertRaises(DestinationError):
            self.plan("Artist", "Album")

    def test_symlinked_artist_or_album_refuses(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "Artist").symlink_to(outside)
        with self.assertRaises(DestinationError):
            self.plan("Artist", "Album")
        (self.root / "Artist").unlink()
        (self.root / "Artist").mkdir()
        (self.root / "Artist" / "Album").symlink_to(outside)
        with self.assertRaises(DestinationError):
            self.plan("Artist", "Album")


class TrackImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.root, self.downloads = base / "music", base / "downloads" / "Release"
        self.root.mkdir()
        self.downloads.mkdir(parents=True)
        self.source = self.downloads / "04 Time.flac"
        self.source.write_bytes(b"audio")
        self.album = self.root / "Artist" / "Album"

    def run_import(self, **overrides):
        args = {"source_file": self.source, "album_dir": self.album, "music_root": self.root,
                "remote_filename": "Music\\Release\\04 Time.flac", "expected_size": 5, **overrides}
        return import_track_file(**args)

    def test_success_creates_folders_moves_the_file_and_removes_the_empty_source_folder(self):
        destination = self.run_import()
        self.assertEqual(destination, self.album / "04 Time.flac")
        self.assertEqual(destination.read_bytes(), b"audio")
        self.assertFalse(self.source.exists())
        self.assertFalse(self.downloads.exists())

    def test_the_existing_album_keeps_its_other_files(self):
        self.album.mkdir(parents=True)
        (self.album / "01 Speak.flac").write_bytes(b"keep")
        self.run_import()
        self.assertEqual((self.album / "01 Speak.flac").read_bytes(), b"keep")
        self.assertEqual(len(list(self.album.iterdir())), 2)

    def test_an_existing_file_is_never_overwritten(self):
        self.album.mkdir(parents=True)
        (self.album / "04 Time.flac").write_bytes(b"original")
        with self.assertRaises(FileExistsError):
            self.run_import()
        self.assertEqual((self.album / "04 Time.flac").read_bytes(), b"original")
        self.assertTrue(self.source.exists())

    def test_other_files_in_the_source_folder_survive(self):
        (self.downloads / "cover.jpg").write_bytes(b"c")
        self.run_import()
        self.assertTrue((self.downloads / "cover.jpg").exists())

    def test_a_size_mismatch_refuses_and_leaves_no_new_folders(self):
        with self.assertRaises(OSError):
            self.run_import(expected_size=6)
        self.assertTrue(self.source.exists())
        self.assertFalse((self.root / "Artist").exists())

    def test_a_symlinked_source_refuses(self):
        real = self.downloads / "real.flac"
        real.write_bytes(b"audio")
        link = self.downloads / "link.flac"
        link.symlink_to(real)
        with self.assertRaises(OSError):
            self.run_import(source_file=link)
        self.assertFalse((self.root / "Artist").exists())

    def test_a_destination_not_two_levels_under_the_root_refuses(self):
        for album_dir in (self.root / "Album", self.root / "A" / "B" / "C", self.root.parent / "Artist" / "Album"):
            with self.subTest(album_dir=album_dir), self.assertRaises(OSError):
                self.run_import(album_dir=album_dir)
        self.assertTrue(self.source.exists())

    def test_a_symlinked_artist_folder_refuses(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        (self.root / "Artist").symlink_to(outside)
        with self.assertRaises(OSError):
            self.run_import()
        self.assertEqual(list(outside.iterdir()), [])
        self.assertTrue(self.source.exists())

    def test_remote_names_cannot_escape_the_album_folder(self):
        destination = self.run_import(remote_filename="x/../../evil/../04 Time.flac")
        self.assertEqual(destination.parent, self.album)
        with self.assertRaises(OSError):
            self.run_import(remote_filename="x/..")

    def test_a_failed_copy_rolls_back_the_folders_it_created(self):
        with patch("acquisition.track_import._copy_fd_to_directory", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.run_import()
        self.assertFalse((self.root / "Artist").exists())
        self.assertTrue(self.source.exists())

    def test_an_unknown_size_refuses(self):
        with self.assertRaises(OSError):
            self.run_import(expected_size=0)


class TrackServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lib = FakeLibrarian(Path(self.temp.name).resolve())
        spawn = patch.object(track_service, "_spawn", return_value=True)
        self.spawn = spawn.start()
        self.addCleanup(spawn.stop)
        self.job_album = track_service.track_job_album("Dark Side", "Time")

    def search(self, *peers):
        payload = {"search_id": "s", "search_attempts": ["q"], "payload_by_peer": {p["username"]: p for p in peers}}
        return patch.object(track_service, "collect_search_responses", return_value=payload)

    def request(self):
        return track_service.request_track(self.lib, "Pink Floyd", "Dark Side", "Time", 4, 1973, {"lens": "now"})

    def job(self):
        return self.lib.jobs[self.lib._identity("Pink Floyd", self.job_album)]

    def test_no_clear_file_is_recorded_as_no_matches(self):
        with self.search(peer("u", ("Pink Floyd/Money.mp3 320kbps", 9))):
            result = self.request()
        self.assertEqual(result["status"], "no_matches")
        self.assertEqual(self.job()["details"]["kind"], "track")
        self.assertEqual(self.job()["details"]["album_name"], "Dark Side")
        self.assertEqual(self.lib.queued, [])

    def test_the_best_file_is_queued_alone_and_saved_without_album_files(self):
        with self.search(peer("low", ("Pink Floyd/Time.flac", 40)), peer("best", ("Pink Floyd/Dark Side/Time 320kbps.mp3", 9))):
            result = self.request()
        self.assertEqual(result["status"], "queued")
        self.assertEqual(self.lib.queued, [("best", [{"filename": "Pink Floyd/Dark Side/Time 320kbps.mp3", "size": 9}])])
        job = self.job()
        self.assertEqual(job["status"], "downloading")
        self.assertEqual(job["candidate"]["track_file"]["size"], 9)
        self.assertNotIn("files", job["candidate"])  # the album watcher must never recover a song
        self.assertEqual(job["candidate"]["fallback_candidates"][0]["username"], "low")
        self.assertNotIn("slskd_api_key", job["settings"])
        self.assertEqual(job["details"]["metadata"], {"lens": "now"})
        self.assertEqual(job["details"]["file_count"], 1)
        self.spawn.assert_called_once()

    def test_a_rejected_source_falls_back_to_the_next(self):
        import httpx

        calls = []
        original = self.lib._discovery_queue_candidate_unless_dismissed

        def queue(artist, album, base, headers, username, files):
            calls.append(username)
            if username == "first":
                raise httpx.HTTPStatusError("rejected", request=httpx.Request("POST", "http://x"),
                                            response=httpx.Response(400))
            return original(artist, album, base, headers, username, files)

        self.lib._discovery_queue_candidate_unless_dismissed = queue
        with self.search(peer("first", ("Pink Floyd/Time 320kbps.mp3", 9), speed=9),
                         peer("second", ("Pink Floyd/Time 320kbps.mp3", 9), speed=1)):
            result = self.request()
        self.assertEqual((result["status"], calls), ("queued", ["first", "second"]))
        self.assertEqual(self.job()["candidate"]["username"], "second")

    def test_a_source_that_does_not_start_is_cleaned_before_the_next(self):
        states = iter([False, True])
        self.lib._slskd_candidate_start_state = lambda *a, **k: next(states)
        with self.search(peer("first", ("Pink Floyd/Time 320kbps.mp3", 9), speed=9),
                         peer("second", ("Pink Floyd/Time 320kbps.mp3", 9), speed=1)):
            result = self.request()
        self.assertEqual(result["status"], "queued")
        self.assertEqual(len(self.lib.cleaned), 1)
        self.assertEqual(self.lib.cleaned[0]["files"], [{"filename": "Pink Floyd/Time 320kbps.mp3", "size": 9}])

    def test_unconfirmed_cleanup_stops_without_queueing_another(self):
        self.lib.start_state, self.lib.clean_result = False, False
        with self.search(peer("first", ("Pink Floyd/Time 320kbps.mp3", 9), speed=9),
                         peer("second", ("Pink Floyd/Time 320kbps.mp3", 9), speed=1)):
            result = self.request()
        self.assertEqual(result["status"], "source_switch_failed")
        self.assertEqual(len(self.lib.queued), 1)

    def test_an_active_or_imported_song_is_not_requested_again(self):
        self.lib._discovery_save_acquisition_job("Pink Floyd", self.job_album, "imported", {"kind": "track"})
        with self.search(peer("u", ("Pink Floyd/Time 320kbps.mp3", 9))) as search:
            self.assertEqual(self.request()["status"], "imported")
        search.assert_not_called()
        self.lib._discovery_save_acquisition_job("Pink Floyd", self.job_album, "no_matches", {"kind": "track"})
        self.lib._DISCOVERY_ACQUIRE_ACTIVE.add(self.lib._identity("Pink Floyd", self.job_album))
        with self.search() as search:
            self.assertEqual(self.request()["status"], "already_in_progress")
        search.assert_not_called()

    def test_a_downloading_song_without_a_watcher_is_resumed_not_requeued(self):
        candidate = {"username": "u", "folder": "f", "track_file": {"filename": "f/Time.mp3", "size": 9}}
        self.lib._discovery_save_acquisition_job("Pink Floyd", self.job_album, "downloading", {"kind": "track"}, candidate=candidate)
        with self.search() as search:
            self.assertEqual(self.request()["status"], "recovery_started")
        search.assert_not_called()
        self.assertEqual(self.lib.queued, [])
        self.spawn.assert_called_once()

    def test_a_dismissed_song_can_be_requested_again(self):
        self.lib._discovery_save_acquisition_job("Pink Floyd", self.job_album, "dismissed", {"kind": "track"})
        with self.search(peer("u", ("Pink Floyd/Time 320kbps.mp3", 9))):
            self.assertEqual(self.request()["status"], "queued")

    def test_missing_slskd_settings_are_reported(self):
        def broken():
            raise ValueError("Set the slskd URL and API key.")
        self.lib._slskd_config = broken
        result = self.request()
        self.assertEqual((result["ok"], result["status"]), (False, "settings_required"))
        self.assertEqual(self.job()["status"], "settings_required")

    def test_title_artist_and_album_are_required(self):
        self.assertFalse(track_service.request_track(self.lib, "A", "", "T")["ok"])


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lib = FakeLibrarian(Path(self.temp.name).resolve())
        self.clock = FakeClock()
        self.ctx = {"artist": "Pink Floyd", "job_album": track_service.track_job_album("Dark Side", "Time"),
                    "album": "Dark Side", "title": "Time", "track_number": 4, "year": 1973}
        self.candidate = {"username": "u", "folder": "Release", "quality_summary": ["flac_cd"],
                          "track_file": {"filename": "Music\\Release\\04 Time.flac", "size": 5}}
        self.folder = self.lib.downloads / "Release"
        self.folder.mkdir()
        (self.folder / "04 Time.flac").write_bytes(b"audio")
        self.lib._discovery_save_acquisition_job("Pink Floyd", self.ctx["job_album"], "downloading", {"kind": "track"},
                                                 candidate=self.candidate)
        self.settings = {"slskd_downloads_path": str(self.lib.downloads)}

    def job(self):
        return self.lib.jobs[self.lib._identity("Pink Floyd", self.ctx["job_album"])]

    def watch(self, candidate=None):
        track_service.watch_track(self.lib, self.ctx, candidate or self.candidate, self.settings,
                                  clock=self.clock, poll_seconds=2)

    def done_record(self, state="Completed, Succeeded", sent=5):
        return {"filename": "Music\\Release\\04 Time.flac", "state": state, "bytesTransferred": sent}

    def test_a_completed_download_is_imported_into_a_new_album_folder(self):
        self.lib.transfers = [self.done_record()]
        self.watch()
        self.assertEqual(self.job()["status"], "imported")
        self.assertEqual((self.lib.MUSIC_DIR / "Pink Floyd" / "Dark Side" / "04 Time.flac").read_bytes(), b"audio")
        self.assertEqual(self.job()["details"]["kind"], "track")

    def test_the_song_joins_a_year_suffixed_album_folder(self):
        existing = self.lib.MUSIC_DIR / "Pink Floyd" / "Dark Side (1973)"
        existing.mkdir(parents=True)
        (existing / "01 Speak.flac").write_bytes(b"keep")
        self.lib.transfers = [self.done_record()]
        self.watch()
        self.assertTrue((existing / "04 Time.flac").exists())
        self.assertTrue((existing / "01 Speak.flac").exists())
        self.assertFalse((self.lib.MUSIC_DIR / "Pink Floyd" / "Dark Side").exists())

    def test_an_existing_file_in_the_album_is_reported_not_replaced(self):
        album = self.lib.MUSIC_DIR / "Pink Floyd" / "Dark Side"
        album.mkdir(parents=True)
        (album / "04 Time.flac").write_bytes(b"original")
        self.lib.transfers = [self.done_record()]
        self.watch()
        self.assertEqual(self.job()["status"], "destination_exists")
        self.assertEqual((album / "04 Time.flac").read_bytes(), b"original")
        self.assertTrue((self.folder / "04 Time.flac").exists())

    def test_a_dismissed_song_is_never_imported(self):
        self.lib.transfers = [self.done_record()]
        self.lib._discovery_save_acquisition_job("Pink Floyd", self.ctx["job_album"], "dismissed", {"kind": "track"})
        self.watch()
        self.assertFalse((self.lib.MUSIC_DIR / "Pink Floyd").exists())
        self.assertTrue((self.folder / "04 Time.flac").exists())
        self.assertEqual(self.job()["status"], "dismissed")

    def test_dismissal_wins_over_a_completed_import_check(self):
        self.lib.transfers = [self.done_record()]
        with patch.object(self.lib, "_discovery_is_dismissed", side_effect=[False, True]):
            self.watch()
        self.assertFalse((self.lib.MUSIC_DIR / "Pink Floyd").exists())

    def test_a_missing_downloaded_folder_waits_without_importing(self):
        (self.folder / "04 Time.flac").unlink()
        self.folder.rmdir()
        self.lib.transfers = [self.done_record()]
        with patch.object(track_service, "WATCH_SECONDS", 6):
            self.watch()
        self.assertEqual(self.job()["status"], "monitor_timeout")
        self.assertFalse((self.lib.MUSIC_DIR / "Pink Floyd").exists())

    def test_a_wrong_size_on_disk_is_not_imported(self):
        (self.folder / "04 Time.flac").write_bytes(b"audio!")
        self.lib.transfers = [self.done_record()]
        with patch.object(track_service, "WATCH_SECONDS", 6):
            self.watch()
        self.assertFalse((self.lib.MUSIC_DIR / "Pink Floyd").exists())
        self.assertEqual((self.folder / "04 Time.flac").read_bytes(), b"audio!")

    def test_a_failed_transfer_retries_then_reports_failure_after_the_grace(self):
        self.lib.transfers = [self.done_record(state="Completed, Errored", sent=0)]
        with patch.object(track_service.transfers, "queue_download_files") as queue:
            self.watch()
        self.assertEqual(queue.call_count, track_service.RETRY_LIMIT)
        self.assertEqual(self.job()["status"], "download_failed")
        self.assertGreaterEqual(self.clock.now - 1000, track_service.FAILED_GRACE_SECONDS)

    def test_a_failed_source_switches_to_the_fallback(self):
        fallback = {"username": "v", "folder": "Other", "quality_summary": ["mp3_320"],
                    "track_file": {"filename": "x\\Other\\Time.mp3", "size": 7}}
        candidate = {**self.candidate, "fallback_candidates": [fallback]}
        self.lib.transfers = [self.done_record(state="Completed, Errored", sent=0)]
        with patch.object(track_service.transfers, "queue_download_files") as queue, \
                patch.object(self.lib, "_discovery_is_dismissed", side_effect=[False] * 80 + [True] * 1000):
            self.watch(candidate)
        queued_users = [call.args[2] for call in queue.call_args_list]
        self.assertIn("v", queued_users)
        self.assertEqual(self.lib.cleaned[0]["username"], "u")
        self.assertEqual(self.job()["candidate"]["username"], "v")
        self.assertEqual(self.job()["candidate"]["fallback_candidates"], [])

    def test_an_uncleanable_source_stops_the_switch(self):
        self.lib.clean_result = False
        fallback = {"username": "v", "folder": "Other", "track_file": {"filename": "Other\\Time.mp3", "size": 7}}
        self.lib.transfers = [self.done_record(state="Completed, Errored", sent=0)]
        with patch.object(track_service.transfers, "queue_download_files") as queue:
            self.watch({**self.candidate, "fallback_candidates": [fallback]})
        self.assertEqual(self.job()["status"], "source_switch_failed")
        self.assertNotIn("v", [call.args[2] for call in queue.call_args_list])


class DismissAndStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.lib = FakeLibrarian(Path(self.temp.name).resolve())
        self.job_album = track_service.track_job_album("Dark Side", "Time")
        self.candidate = {"username": "u", "folder": "Release",
                          "track_file": {"filename": "Music\\Release\\04 Time.flac", "size": 5}}

    def save(self, status, candidate=None, kind="track"):
        self.lib._discovery_save_acquisition_job(
            "Pink Floyd", self.job_album, status,
            {"kind": kind, "album_name": "Dark Side", "track_title": "Time"} if kind else {},
            candidate=self.candidate if candidate is None else candidate)

    def job(self):
        return self.lib.jobs[self.lib._identity("Pink Floyd", self.job_album)]

    def test_dismissing_a_song_cleans_only_its_own_file(self):
        self.save("downloading")
        result = track_service.dismiss_track(self.lib, "Pink Floyd", self.job_album)
        self.assertTrue(result["ok"])
        self.assertEqual(self.lib.cleaned[0]["files"], [{"filename": "Music\\Release\\04 Time.flac", "size": 5}])
        self.assertEqual(self.job()["status"], "dismissed")

    def test_a_cleanup_that_cannot_be_confirmed_refuses_to_dismiss(self):
        self.save("downloading")
        self.lib.clean_result = False
        result = track_service.dismiss_track(self.lib, "Pink Floyd", self.job_album)
        self.assertFalse(result["ok"])
        self.assertEqual(self.job()["status"], "downloading")

    def test_missing_source_inventory_refuses_when_files_may_exist(self):
        self.save("downloading", candidate={"username": "u"})
        self.assertFalse(track_service.dismiss_track(self.lib, "Pink Floyd", self.job_album)["ok"])
        self.assertEqual(self.job()["status"], "downloading")
        self.assertEqual(self.lib.cleaned, [])

    def test_fileless_states_dismiss_without_touching_any_files(self):
        for status in ("no_matches", "imported", "queue_failed"):
            with self.subTest(status=status):
                self.save(status)
                self.assertTrue(track_service.dismiss_track(self.lib, "Pink Floyd", self.job_album)["ok"])
                self.assertEqual(self.job()["status"], "dismissed")
        self.assertEqual(self.lib.cleaned, [])

    def test_a_failed_download_is_cleaned_before_it_is_dismissed(self):
        self.save("download_failed")
        track_service.dismiss_track(self.lib, "Pink Floyd", self.job_album)
        self.assertEqual(len(self.lib.cleaned), 1)

    def test_album_rows_and_unknown_rows_are_left_to_the_album_dismissal(self):
        self.save("downloading", kind=None)
        self.assertIsNone(track_service.dismiss_track(self.lib, "Pink Floyd", self.job_album))
        self.assertIsNone(track_service.dismiss_track(self.lib, "Nobody", "Nothing"))
        self.assertIsNone(track_service.dismiss_track(object(), "A", "B"))
        self.assertEqual(self.lib.cleaned, [])

    def test_status_resumes_interrupted_songs_and_adds_progress(self):
        self.save("downloading")
        self.lib.transfers = [{"filename": "Music\\Release\\04 Time.flac", "state": "InProgress",
                               "bytesTransferred": 2, "size": 5}]
        payload = {"ok": True, "acquisitions": [
            {"artist": "Pink Floyd", "album": self.job_album, "status": "downloading", "details": {"kind": "track"}},
            {"artist": "Other", "album": "Album", "status": "downloading", "details": {}},
        ]}
        with patch.object(track_service, "_spawn", return_value=True) as spawn:
            result = track_service.augment_status(self.lib, payload)
        spawn.assert_called_once()
        progress = result["acquisitions"][0]["details"]["live_progress"]
        self.assertEqual((progress["available"], progress["total_tracks"], progress["percent"]), (True, 1, 40.0))
        self.assertNotIn("live_progress", result["acquisitions"][1]["details"])

    def test_status_is_returned_unchanged_when_nothing_applies_or_anything_fails(self):
        payload = {"ok": True, "acquisitions": []}
        self.assertIs(track_service.augment_status(self.lib, payload), payload)
        self.assertIs(track_service.augment_status(object(), payload), payload)
        self.assertEqual(track_service.augment_status(self.lib, "text"), "text")


if __name__ == "__main__":
    unittest.main()
