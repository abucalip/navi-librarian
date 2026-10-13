"""Regression tests for acquisition path/import safety and lifecycle guards.

The tests compile selected real function definitions from navidrome_server.py into
a small stubbed namespace, avoiding import-time initialization of the full MCP app.
"""
import ast
import json
import tempfile
import threading
import unicodedata
import unittest
from pathlib import Path
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / "navidrome_server.py"


class FakeHTTPError(Exception):
    pass


def load_helpers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {
        "_discovery_filename_key",
        "_discovery_match_completed_album_files",
        "_discovery_is_album_candidate",
        "_discovery_exact_artist_credit_matches",
        "_discovery_is_various_artists",
        "_slskd_album_path_match",
        "_slskd_search_queries",
        "_slskd_search_response_items",
        "_slskd_path_match_diagnostics",
        "_slskd_queue_failure_action",
        "_slskd_quality_tier",
        "_slskd_track_identity",
        "_slskd_extract_candidates",
        "_discovery_reconcile_interrupted_import",
        "_discovery_import_matched_album_files",
        "_slskd_candidate_start_state",
        "_discovery_queue_candidate_unless_dismissed",
        "_discovery_switch_to_next_source_locked",
        "_discovery_import_completed_source",
        "_discovery_acquire_album_impl",
        "discovery_acquire_album",
    }
    selected = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    found = {node.name for node in selected}
    if found != wanted:
        raise AssertionError(f"Missing acquisition helpers: {sorted(wanted - found)}")
    # The public MCP decorator is an app-registration detail; exercise the actual
    # function body without importing/initializing MCPServer.
    for node in selected:
        node.decorator_list = []

    namespace = {
        "Path": Path,
        "unicodedata": unicodedata,
        "json": json,
        "threading": threading,
        "_DISCOVERY_IMPORT_TRANSITION_LOCK": threading.RLock(),
        "_DISCOVERY_IMPORT_LOCK": threading.Lock(),
        "_DISCOVERY_IMPORT_ACTIVE": set(),
        "_DISCOVERY_ACQUIRE_ACTIVE": set(),
        "jobs": [],
        "time": SimpleNamespace(monotonic=lambda: 0, sleep=lambda _seconds: None, time=lambda: 123.0),
        "MUSIC_DIR": Path("/music"),
        "httpx": SimpleNamespace(
            HTTPError=FakeHTTPError,
            delete=lambda *args, **kwargs: SimpleNamespace(status_code=204),
            post=lambda *args, **kwargs: SimpleNamespace(
                status_code=200, raise_for_status=lambda: None
            ),
        ),
        "_slskd_download_transfer_files": lambda *_args, **_kwargs: [],
        "_slskd_config": lambda: ("http://slskd", None, {}),
        "_DISCOVERY_SETTINGS_DEFAULTS": {"quality_priority": ["mp3_320", "flac_cd"]},
        "_discovery_expected_track_count": lambda _metadata: None,
        "_discovery_cancel_and_clean_source": lambda *_args, **_kwargs: True,
        "_discovery_reactivate_dismissed_acquisition": lambda *_args, **_kwargs: False,
        "_discovery_safe_folder_name": lambda value: str(value).replace("/", "_"),
        "_discovery_import_matched_album_files": lambda *_args, **_kwargs: None,
        "saved_jobs": [],
        "status_updates": [],
        "_discovery_save_acquisition_job": lambda *args, **kwargs: namespace["saved_jobs"].append((args, kwargs)),
        "_discovery_update_acquisition_status": lambda *args, **kwargs: (namespace["status_updates"].append((args, kwargs)) or True),
        "_slskd_candidate_start_state": lambda *args, **kwargs: True,
        "_music_key": lambda value: str(value or "").strip().casefold(),
    }
    namespace["_discovery_list_acquisition_jobs"] = lambda: namespace["jobs"]
    namespace["_discovery_is_dismissed"] = lambda artist, album: any(
        row.get("artist_key") == namespace["_music_key"](artist)
        and row.get("album_key") == namespace["_music_key"](album)
        and row.get("status") == "dismissed"
        for row in namespace["jobs"]
    )

    def start_watcher(artist, album, candidate, settings):
        identity = (namespace["_music_key"](artist), namespace["_music_key"](album))
        with namespace["_DISCOVERY_IMPORT_LOCK"]:
            namespace["_DISCOVERY_IMPORT_ACTIVE"].add(identity)

    namespace["_discovery_start_import_watcher"] = start_watcher
    namespace["_discovery_acquire_album_impl"] = lambda *args: json.dumps({
        "ok": True, "status": "implementation_called"
    })
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


HELPERS = load_helpers()


class RecommendationEligibilityTests(unittest.TestCase):
    def test_rejects_compilations_remixes_and_non_album_types(self):
        is_album = HELPERS["_discovery_is_album_candidate"]
        for item in (
            {"album": "Greatest Hits"},
            {"album": "The Remixes"},
            {"album": "Live at Wembley"},
            {"album": "An Ordinary Title", "primary_type": "EP"},
            {"album": "An Ordinary Title", "secondary_types": ["Compilation"]},
        ):
            with self.subTest(item=item):
                self.assertFalse(is_album(item))

    def test_accepts_regular_full_album(self):
        self.assertTrue(HELPERS["_discovery_is_album_candidate"]({
            "album": "Back to Black", "primary_type": "Album",
        }))


class NewReleasesArtistCreditTests(unittest.TestCase):
    def test_requires_exact_artist_credit_name(self):
        matches = HELPERS["_discovery_exact_artist_credit_matches"]
        self.assertTrue(matches([{"artist": {"name": "Queen"}}], "Queen"))
        self.assertFalse(matches([{"artist": {"name": "Queen Tribute"}}], "Queen"))
        self.assertFalse(matches([{"artist": {"name": "The Queens"}}], "Queen"))
        self.assertFalse(matches([], "Queen"))


class VariousArtistsNewReleasesTests(unittest.TestCase):
    def test_rejects_various_artists_aliases(self):
        is_various = HELPERS["_discovery_is_various_artists"]
        for value in ("Various Artists", "VARIOUS ARTISTS", "Various Artist", "Various", "V.A."):
            with self.subTest(value=value):
                self.assertTrue(is_various(value))

    def test_keeps_named_artists(self):
        is_various = HELPERS["_discovery_is_various_artists"]
        self.assertFalse(is_various("Queen"))
        self.assertFalse(is_various("The Various"))


class SlskdSearchQueryTests(unittest.TestCase):
    def test_zero_response_fallback_queries_broaden_without_dropping_artist_immediately(self):
        build = HELPERS["_slskd_search_queries"]
        queries = build("Tinariwen", "Idrache (Traces of the Past)")
        self.assertEqual(queries[0], "Tinariwen Idrache (Traces of the Past)")
        self.assertEqual(queries[1], "Tinariwen Idrache Traces of the Past")
        self.assertEqual(queries[2], "Tinariwen Idrache")
        self.assertEqual(len({query.casefold() for query in queries}), len(queries))

    def test_acquisition_retries_broader_query_when_exact_search_has_no_payload(self):
        posted_queries = []
        posted_timeouts = []
        other_peer = {
            "username": "peer",
            "files": [{"filename": "Other Artist/Other Album/01 - Track.flac", "size": 1000}],
        }

        def fake_response(payload=None, status_code=200):
            return SimpleNamespace(
                status_code=status_code,
                json=lambda: payload,
                raise_for_status=lambda: None,
            )

        def fake_post(_url, headers=None, json=None, timeout=None):
            posted_queries.append(json["searchText"])
            posted_timeouts.append(json["searchTimeout"])
            return fake_response({})

        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith("/responses"):
                return fake_response([])
            search_id = url.rsplit("/", 1)[-1]
            query_index = len(posted_queries) - 1
            state = {"isComplete": True, "responseCount": 0, "fileCount": 0}
            if query_index == 1:
                state = {
                    "isComplete": True,
                    "responseCount": 1,
                    "fileCount": 1,
                    "responses": [other_peer],
                }
            return fake_response(state)

        client = HELPERS["httpx"]
        original_post = client.post
        original_get = getattr(client, "get", None)
        original_status_error = getattr(client, "HTTPStatusError", None)
        client.post = fake_post
        client.get = fake_get
        client.HTTPStatusError = FakeHTTPError
        try:
            result = json.loads(HELPERS["_discovery_acquire_album_impl"](
                "Tinariwen", "Idrache (Traces of the Past)"
            ))
        finally:
            client.post = original_post
            if original_get is None:
                delattr(client, "get")
            else:
                client.get = original_get
            if original_status_error is None:
                delattr(client, "HTTPStatusError")
            else:
                client.HTTPStatusError = original_status_error

        self.assertEqual(posted_queries, [
            "Tinariwen Idrache (Traces of the Past)",
            "Tinariwen Idrache Traces of the Past",
        ])
        self.assertEqual(posted_timeouts, [15000, 6000])
        self.assertEqual(
            [item["query"] for item in result["search_queries_attempted"]],
            posted_queries,
        )
        self.assertEqual(result["search_queries_attempted"][0]["collected_peer_response_count"], 0)
        self.assertEqual(result["search_queries_attempted"][1]["collected_peer_response_count"], 1)
        self.assertIn("Queries tried: Tinariwen Idrache (Traces of the Past)", result["message"])
        self.assertIn("Tinariwen Idrache Traces of the Past", result["message"])

    def test_waits_for_peer_payload_when_slskd_reports_responses(self):
        posted_queries = []
        state_calls = [0]
        clock = [0.0]
        peer = {
            "username": "peer",
            "files": [{
                "filename": "Other Artist/Other Album/01 - Track.flac",
                "size": 1000,
            }],
        }

        def fake_response(payload=None, status_code=200):
            return SimpleNamespace(
                status_code=status_code,
                json=lambda: payload,
                raise_for_status=lambda: None,
            )

        def fake_post(_url, headers=None, json=None, timeout=None):
            posted_queries.append(json["searchText"])
            return fake_response({})

        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith("/responses"):
                return fake_response([])
            state_calls[0] += 1
            if state_calls[0] <= 26:
                return fake_response({
                    "isComplete": False,
                    "state": "InProgress",
                    "responseCount": 26,
                    "fileCount": 362,
                    "responses": [],
                })
            return fake_response({
                "isComplete": True,
                "state": "Completed, TimedOut",
                "responseCount": 26,
                "fileCount": 362,
                "responses": [peer],
            })

        client = HELPERS["httpx"]
        original_post = client.post
        original_get = getattr(client, "get", None)
        original_time = HELPERS["time"]
        client.post = fake_post
        client.get = fake_get
        HELPERS["time"] = SimpleNamespace(
            monotonic=lambda: clock[0],
            sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
            time=lambda: 123.0,
        )
        try:
            result = json.loads(HELPERS["_discovery_acquire_album_impl"](
                "Tinariwen", "Idrache (Traces of the Past)"
            ))
        finally:
            client.post = original_post
            if original_get is None:
                delattr(client, "get")
            else:
                client.get = original_get
            HELPERS["time"] = original_time

        self.assertGreater(state_calls[0], 24)
        self.assertEqual(len(posted_queries), 1)
        self.assertEqual(result["search_queries_attempted"][0]["collected_peer_response_count"], 1)
        self.assertEqual(result["search_queries_attempted"][0]["state"], "completed, timedout")

    def test_search_queries_reject_blank_artist_or_album(self):
        build = HELPERS["_slskd_search_queries"]
        self.assertEqual(build("", "Album"), [])
        self.assertEqual(build("Artist", "  "), [])


class SlskdAlbumPathMatchingTests(unittest.TestCase):
    def test_matches_edition_suffix_and_partial_album_wording(self):
        matcher = HELPERS["_slskd_album_path_match"]
        self.assertTrue(matcher("A Moon Shaped Pool", "Radiohead/A Moon Shaped Pool (FLAC Deluxe Edition)"))
        self.assertTrue(matcher("A Moon Shaped Pool", "Radiohead/Moon Shaped Pool"))

    def test_rejects_unrelated_album_folder(self):
        matcher = HELPERS["_slskd_album_path_match"]
        self.assertFalse(matcher("Moon River", "Radiohead/Moonlight River"))
        self.assertFalse(matcher("AM", "Sam"))

    def test_explicit_source_queue_rejections_allow_failover(self):
        classify = HELPERS["_slskd_queue_failure_action"]
        for status in (400, 404, 422):
            with self.subTest(status=status):
                exc = SimpleNamespace(response=SimpleNamespace(status_code=status))
                self.assertEqual(classify(exc), "retry_source")

    def test_queue_auth_errors_are_fatal_but_ambiguous_errors_remain_uncertain(self):
        classify = HELPERS["_slskd_queue_failure_action"]
        for status in (401, 403):
            with self.subTest(status=status):
                exc = SimpleNamespace(response=SimpleNamespace(status_code=status))
                self.assertEqual(classify(exc), "fatal")
        self.assertEqual(classify(FakeHTTPError("timeout")), "uncertain")
        self.assertEqual(
            classify(SimpleNamespace(response=SimpleNamespace(status_code=503))),
            "uncertain",
        )

    def test_slskd_search_response_payload_normalization(self):
        normalize = HELPERS["_slskd_search_response_items"]
        peer = {"username": "peer", "files": [{"filename": "Bombino/Agamgam/01.flac"}]}
        self.assertEqual(normalize([peer]), [peer])
        self.assertEqual(normalize({"responses": [peer]}), [peer])
        self.assertEqual(normalize({"items": [peer]}), [peer])
        self.assertEqual(normalize({"responses": "not-a-list"}), [])
        self.assertEqual(normalize(None), [])

    def test_path_diagnostics_explain_album_and_artist_match_signals(self):
        diagnose = HELPERS["_slskd_path_match_diagnostics"]
        result = diagnose([{
            "username": "peer",
            "files": [{
                "filename": r"Music\Tinariwen\Tinariwen - Idrache (Traces Of The Past) - 2024\01 - Soixante Trois.flac"
            }],
        }], "Tinariwen", "Idrache (Traces of the past)")
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["album_path_match"])
        self.assertTrue(result[0]["artist_path_match"])
        self.assertFalse(result[0]["album_filename_match"])


    def test_tinariwen_idrache_source_folder_variants_are_clear_candidates(self):
        extract = HELPERS["_slskd_extract_candidates"]
        priority = ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"]
        tracks = [
            "Soixante Trois", "Assuf Ag Assuf", "Amoss Idjraw", "Azaman Amikankanen",
            "Adounia Nissan", "Amidinin War Hi Toyed", "Imidiwan Ma Tennam",
            "Alkhar Dessouf", "Tenere Maloulat", "Tenhert", "Adounia Ti Chidjret",
            "Tenere Dafeo Nikchan",
        ]
        folders = [
            r"Tinariwen\2024 - Idrache Traces of the Past",
            r"Music\Tinariwen\Tinariwen - Idrache (Traces Of The Past) - 2024",
            r"Tinariwen\2024 - Idrache (Traces Of The Past) [24-44.1]",
            r"Tinariwen\2024 - Idrache (Traces Of The Past)",
        ]
        responses = []
        for index, folder in enumerate(folders):
            files = []
            for track_number, title in enumerate(tracks, 1):
                item = {"filename": f"{folder}\\{track_number:02d} - {title}.flac", "size": 5000000}
                if index == 0:
                    item.update({"sampleRate": 44100, "bitDepth": 16})
                files.append(item)
            responses.append({"username": f"peer-{index}", "files": files})

        candidates = extract(
            responses, "Tinariwen", "Idrache (Traces of the past)", priority,
            expected_track_count=12,
        )
        self.assertEqual(len(candidates), 4)
        self.assertTrue(all(item["clear_match"] for item in candidates))
        self.assertTrue(all(item["unique_track_count"] == 12 for item in candidates))
        all_tiers = [tier for item in candidates for tier in item["quality_summary"]]
        self.assertIn("flac_16_44", all_tiers)
        self.assertIn("flac_hires", all_tiers)


class CompletedAlbumMatchingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "downloads"
        self.source.mkdir()
        self.destination_parent = self.root / "music"
        self.destination_parent.mkdir()
        self.destination = self.destination_parent / "Artist - Album"
        self.candidate = {
            "files": [
                {"filename": "Artist - Album/01 - Track.flac", "size": 4},
                {"filename": "Artist - Album/02 - Track.flac", "size": 3},
            ]
        }
        (self.source / "01 - Track.flac").write_bytes(b"1234")
        (self.source / "02 - Track.flac").write_bytes(b"567")

    def test_import_moves_only_expected_tracks_and_leaves_unrelated_files(self):
        unrelated = self.source / "cover.jpg"
        unrelated.write_bytes(b"cover")
        HELPERS["_discovery_import_matched_album_files"](
            self.source, self.destination, self.candidate
        )
        self.assertEqual((self.destination / "01 - Track.flac").read_bytes(), b"1234")
        self.assertEqual((self.destination / "02 - Track.flac").read_bytes(), b"567")
        self.assertTrue(unrelated.exists())
        self.assertFalse((self.destination / ".navidrome-import.json").exists())
        self.assertFalse(self.source.joinpath("01 - Track.flac").exists())

    def test_unknown_or_zero_advertised_track_size_is_rejected(self):
        candidate = {
            "files": [{"filename": "Album/01 - Track.flac", "size": 0}]
        }
        self.assertIsNone(
            HELPERS["_discovery_match_completed_album_files"](self.source, candidate)
        )
        with self.assertRaisesRegex(OSError, "Expected tracks no longer match"):
            HELPERS["_discovery_import_matched_album_files"](
                self.source, self.destination, candidate
            )
        self.assertTrue((self.source / "01 - Track.flac").exists())
        self.assertFalse(self.destination.exists())

    def test_existing_destination_is_never_overwritten(self):
        self.destination.mkdir()
        marker = self.destination / "keep.txt"
        marker.write_text("preserve", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            HELPERS["_discovery_import_matched_album_files"](
                self.source, self.destination, self.candidate
            )
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
        self.assertTrue((self.source / "01 - Track.flac").exists())

    def test_broken_destination_symlink_is_never_overwritten(self):
        self.destination.symlink_to(self.root / "missing-target")
        with self.assertRaises(FileExistsError):
            HELPERS["_discovery_import_matched_album_files"](
                self.source, self.destination, self.candidate
            )
        self.assertTrue(self.destination.is_symlink())
        self.assertTrue((self.source / "01 - Track.flac").exists())

    def test_symlinked_destination_parent_is_rejected(self):
        real_parent = self.root / "real-music"
        real_parent.mkdir()
        link_parent = self.root / "linked-music"
        link_parent.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaises(OSError):
            HELPERS["_discovery_import_matched_album_files"](
                self.source, link_parent / "Artist - Album", self.candidate
            )
        self.assertFalse((real_parent / "Artist - Album").exists())


    def test_failed_staged_move_rolls_tracks_back_to_source(self):
        import shutil
        original_move = shutil.move
        calls = {"count": 0}

        def fail_on_second_move(src, dst, *args, **kwargs):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("simulated second-track move failure")
            return original_move(src, dst, *args, **kwargs)

        from unittest.mock import patch
        with patch("shutil.move", side_effect=fail_on_second_move):
            with self.assertRaises(OSError):
                HELPERS["_discovery_import_matched_album_files"](
                    self.source, self.destination, self.candidate
                )

        self.assertFalse(self.destination.exists())
        self.assertTrue((self.source / "01 - Track.flac").exists())
        self.assertTrue((self.source / "02 - Track.flac").exists())
        self.assertEqual((self.source / "01 - Track.flac").read_bytes(), b"1234")
        self.assertEqual((self.source / "02 - Track.flac").read_bytes(), b"567")
        self.assertEqual(list(self.destination_parent.glob(".navidrome-import-*")), [])

    def test_import_aborts_before_writing_if_music_filesystem_identity_changed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "downloads"
            source.mkdir()
            (source / "01 - Track.flac").write_bytes(b"1234")
            (source / "02 - Track.flac").write_bytes(b"567")
            music = root / "music"
            music.mkdir()
            destination = music / "Artist - Album"

            with self.assertRaisesRegex(OSError, "filesystem changed"):
                HELPERS["_discovery_import_matched_album_files"](
                    source, destination, self.candidate,
                    expected_music_root=music, expected_device=music.stat().st_dev + 1,
                )

            self.assertTrue((source / "01 - Track.flac").exists())
            self.assertTrue((source / "02 - Track.flac").exists())
            self.assertFalse(destination.exists())
            self.assertEqual(list(music.iterdir()), [])

    def test_conflicting_duplicate_remote_basenames_are_ambiguous(self):
        candidate = {"files": [
            {"filename": "A/01.flac", "size": 4},
            {"filename": "B/01.flac", "size": 8},
        ]}
        self.assertIsNone(
            HELPERS["_discovery_match_completed_album_files"](self.source, candidate)
        )

    def test_unique_collision_suffixed_file_can_be_matched_by_size(self):
        (self.source / "01 - Track_1.flac").write_bytes(b"1234")
        (self.source / "01 - Track.flac").unlink()
        candidate = {"files": [{"filename": "Album/01 - Track.flac", "size": 4}]}
        matched = HELPERS["_discovery_match_completed_album_files"](self.source, candidate)
        self.assertEqual(matched["01 - Track.flac"].name, "01 - Track_1.flac")


class AcquisitionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.ns = load_helpers()

    def test_parent_traversal_is_rejected_before_transfer_lookup(self):
        calls = []
        self.ns["_slskd_download_transfer_files"] = lambda *args: calls.append(args) or []
        candidate = {"username": "peer", "files": [
            {"filename": "Album/../Other/01.flac"}
        ]}
        result = self.ns["_slskd_candidate_start_state"](
            "http://slskd", {}, candidate, timeout=1
        )
        self.assertIsNone(result)
        self.assertEqual(calls, [])

    def test_files_from_multiple_remote_directories_are_rejected(self):
        calls = []
        self.ns["_slskd_download_transfer_files"] = lambda *args: calls.append(args) or []
        candidate = {"username": "peer", "files": [
            {"filename": "Album/01.flac"},
            {"filename": "Other/02.flac"},
        ]}
        result = self.ns["_slskd_candidate_start_state"](
            "http://slskd", {}, candidate, timeout=1
        )
        self.assertIsNone(result)
        self.assertEqual(calls, [])

    def test_dismissed_acquisition_is_not_queued(self):
        posts = []
        self.ns["httpx"].post = lambda *args, **kwargs: posts.append(args)
        self.ns["jobs"].append({
            "artist_key": "artist", "album_key": "album", "status": "dismissed"
        })
        result = self.ns["_discovery_queue_candidate_unless_dismissed"](
            "Artist", "Album", "http://slskd", {}, "peer", ["Album/01.flac"]
        )
        self.assertIsNone(result)
        self.assertEqual(posts, [])

    def test_simultaneous_requests_do_not_run_two_acquisition_searches(self):
        entered_impl = threading.Event()
        release_impl = threading.Event()
        calls = []

        def slow_impl(*args):
            calls.append(args)
            entered_impl.set()
            if not release_impl.wait(timeout=3):
                raise AssertionError("test did not release first acquisition")
            return json.dumps({"ok": True, "status": "queued"})

        self.ns["_discovery_acquire_album_impl"] = slow_impl
        first_result = []
        first = threading.Thread(target=lambda: first_result.append(
            self.ns["discovery_acquire_album"]("Artist", "Album")
        ))
        first.start()
        self.assertTrue(entered_impl.wait(timeout=2))
        second_result = self.ns["discovery_acquire_album"]("Artist", "Album")
        release_impl.set()
        first.join(timeout=3)

        self.assertFalse(first.is_alive())
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(second_result)["status"], "already_in_progress")
        self.assertEqual(json.loads(first_result[0])["status"], "queued")




    def test_interrupted_import_is_reconciled_when_destination_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            music = Path(temp)
            destination = music / "Artist" / "Album"
            destination.mkdir(parents=True)
            (destination / "01.flac").write_bytes(b"1234")
            (destination / ".navidrome-import.json").write_text(json.dumps({
                "source": str(Path("/downloads/Album").resolve()),
                "destination": str(destination),
                "tracks": {"01.flac": 4},
            }), encoding="utf-8")
            self.ns["MUSIC_DIR"] = music
            self.ns["jobs"].append({
                "artist_key": "artist",
                "album_key": "album",
                "status": "importing",
                "details": {
                    "source_folder": "/downloads/Album",
                    "destination": str(destination),
                    "music_root_device": music.stat().st_dev,
                },
            })
            candidate = {
                "username": "peer",
                "files": [{"filename": "Album/01.flac", "size": 4}],
            }

            recovered = self.ns["_discovery_reconcile_interrupted_import"](
                "Artist", "Album", candidate
            )

        self.assertTrue(recovered)
        self.assertEqual(self.ns["status_updates"][-1][0][2], "imported")
        self.assertTrue(self.ns["status_updates"][-1][0][3]["recovered_after_restart"])
        self.assertFalse((destination / ".navidrome-import.json").exists())

    def test_restart_reconciliation_refuses_changed_library_filesystem(self):
        with tempfile.TemporaryDirectory() as temp:
            music = Path(temp)
            destination = music / "Artist" / "Album"
            destination.mkdir(parents=True)
            (destination / "01.flac").write_bytes(b"1234")
            self.ns["MUSIC_DIR"] = music
            self.ns["jobs"].append({
                "artist_key": "artist",
                "album_key": "album",
                "status": "importing",
                "details": {
                    "source_folder": "/downloads/Album",
                    "destination": str(destination),
                    "music_root_device": music.stat().st_dev + 1,
                },
            })
            candidate = {
                "username": "peer",
                "files": [{"filename": "Album/01.flac", "size": 4}],
            }

            recovered = self.ns["_discovery_reconcile_interrupted_import"](
                "Artist", "Album", candidate
            )
            self.assertTrue((destination / "01.flac").exists())

        self.assertFalse(recovered)
        self.assertEqual(self.ns["status_updates"], [])

    def test_partial_staging_is_rolled_back_to_download_folder_after_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            music = root / "music"
            artist_dir = music / "Artist"
            artist_dir.mkdir(parents=True)
            source = root / "downloads" / "Album"
            source.mkdir(parents=True)
            (source / "02.flac").write_bytes(b"567")
            staging = artist_dir / ".navidrome-import-interrupted"
            staging.mkdir()
            (staging / "01.flac").write_bytes(b"1234")
            destination = artist_dir / "Album"
            (staging / ".navidrome-import.json").write_text(json.dumps({
                "source": str(source.resolve()),
                "destination": str(destination),
                "tracks": {"01.flac": 4, "02.flac": 3},
            }), encoding="utf-8")
            self.ns["MUSIC_DIR"] = music
            self.ns["jobs"].append({
                "artist_key": "artist",
                "album_key": "album",
                "status": "importing",
                "details": {
                    "source_folder": str(source),
                    "destination": str(destination),
                    "music_root_device": music.stat().st_dev,
                },
            })
            candidate = {
                "username": "peer",
                "files": [
                    {"filename": "Album/01.flac", "size": 4},
                    {"filename": "Album/02.flac", "size": 3},
                ],
            }

            recovered = self.ns["_discovery_reconcile_interrupted_import"](
                "Artist", "Album", candidate
            )

            self.assertFalse(recovered)
            self.assertEqual((source / "01.flac").read_bytes(), b"1234")
            self.assertEqual((source / "02.flac").read_bytes(), b"567")
            self.assertFalse(staging.exists())
            self.assertFalse(destination.exists())
            self.assertEqual(self.ns["status_updates"], [])

    def test_interrupted_import_does_not_reconcile_wrong_or_incomplete_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            music = Path(temp)
            destination = music / "Artist" / "Album"
            destination.mkdir(parents=True)
            (destination / "01.flac").write_bytes(b"bad")
            self.ns["MUSIC_DIR"] = music
            self.ns["jobs"].append({
                "artist_key": "artist",
                "album_key": "album",
                "status": "importing",
                "details": {
                    "source_folder": "/downloads/Album",
                    "destination": str(destination),
                    "music_root_device": music.stat().st_dev,
                },
            })
            candidate = {
                "username": "peer",
                "files": [{"filename": "Album/01.flac", "size": 4}],
            }

            recovered = self.ns["_discovery_reconcile_interrupted_import"](
                "Artist", "Album", candidate
            )

        self.assertFalse(recovered)
        self.assertEqual(self.ns["status_updates"], [])

    def test_import_does_not_move_files_if_importing_status_cannot_be_persisted(self):
        status_calls = []
        import_calls = []
        self.ns["_discovery_is_dismissed"] = lambda artist, album: False
        self.ns["_discovery_update_acquisition_status"] = lambda *args, **kwargs: (
            status_calls.append(args) or False
        )
        self.ns["_discovery_import_matched_album_files"] = lambda *args, **kwargs: import_calls.append(args)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            music = root / "music"
            music.mkdir()
            source = root / "downloaded-album"
            source.mkdir()
            result = self.ns["_discovery_import_completed_source"](
                "Artist", "Album", source, music,
                {"username": "peer", "files": [{"filename": "Album/01.flac", "size": 4}]},
            )

        self.assertEqual(result, "failed")
        self.assertEqual(import_calls, [])
        self.assertEqual(status_calls[0][2], "importing")

    def test_dismissed_job_never_enters_import_transition(self):
        self.ns["_discovery_is_dismissed"] = lambda artist, album: True
        status_calls = []
        import_calls = []
        self.ns["_discovery_update_acquisition_status"] = lambda *args, **kwargs: status_calls.append(args)
        self.ns["_discovery_import_matched_album_files"] = lambda *args, **kwargs: import_calls.append(args)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = self.ns["_discovery_import_completed_source"](
                "Artist", "Album", root / "downloaded-album", root,
                {"username": "peer", "files": [{"filename": "Album/01.flac"}]},
            )

        self.assertEqual(result, "dismissed")
        self.assertEqual(status_calls, [])
        self.assertEqual(import_calls, [])

    def test_incomplete_saved_download_details_do_not_start_or_requeue(self):
        self.ns["jobs"].append({
            "artist": "Artist",
            "album": "Album",
            "artist_key": "artist",
            "album_key": "album",
            "status": "downloading",
            "candidate": {"username": "peer", "files": []},
            "settings": {},
        })
        impl_calls = []
        watcher_calls = []
        self.ns["_discovery_acquire_album_impl"] = lambda *args: impl_calls.append(args)
        self.ns["_discovery_start_import_watcher"] = lambda *args: watcher_calls.append(args)

        result = json.loads(self.ns["discovery_acquire_album"]("Artist", "Album"))

        self.assertEqual(result["status"], "recovery_unavailable")
        self.assertEqual(impl_calls, [])
        self.assertEqual(watcher_calls, [])

    def test_ambiguous_fallback_queue_is_monitored_without_trying_another_peer(self):
        posts = []

        def uncertain_post(*args, **kwargs):
            posts.append((args, kwargs))
            raise FakeHTTPError("connection dropped after request")

        self.ns["httpx"].post = uncertain_post
        self.ns["_slskd_candidate_start_state"] = lambda *args, **kwargs: None
        first_fallback = {
            "username": "peer-one",
            "folder": "Album",
            "files": [{"filename": "Album/01.flac", "size": 4}],
            "quality_summary": ["FLAC"],
        }
        second_fallback = {
            "username": "peer-two",
            "folder": "Album",
            "files": [{"filename": "Album/01.flac", "size": 4}],
        }
        current = {
            "username": "original-peer",
            "files": [{"filename": "Album/01.flac", "size": 4}],
            "fallback_candidates": [first_fallback, second_fallback],
        }

        result = self.ns["_discovery_switch_to_next_source_locked"](
            "Artist", "Album", current, {}, Path("/downloads"), {}, "stalled"
        )

        self.assertEqual(result["username"], "peer-one")
        self.assertEqual(len(posts), 1, "must not queue peer-two after an ambiguous response")
        self.assertEqual(len(self.ns["saved_jobs"]), 1)
        args, kwargs = self.ns["saved_jobs"][0]
        self.assertEqual(args[2], "downloading")
        self.assertEqual(kwargs["candidate"]["username"], "peer-one")
        self.assertEqual(args[3]["queue_error"], "FakeHTTPError")
        self.assertEqual(kwargs["candidate"]["fallback_candidates"], [second_fallback])

    def test_explicit_get_reactivates_safely_dismissed_job(self):
        job = {
            "artist": "Artist",
            "album": "Album",
            "artist_key": "artist",
            "album_key": "album",
            "status": "dismissed",
            "candidate": {"username": "old-peer", "files": [{"filename": "old/01.flac"}]},
            "settings": {"slskd_downloads_path": "/old"},
        }
        self.ns["jobs"].append(job)
        calls = []

        def reactivate(artist, album, metadata):
            calls.append((artist, album, metadata))
            job.update(status="retry_requested", candidate={}, settings={})
            return True

        self.ns["_discovery_reactivate_dismissed_acquisition"] = reactivate
        self.ns["_discovery_acquire_album_impl"] = lambda *args: json.dumps({
            "ok": True, "status": "implementation_called"
        })
        result = json.loads(self.ns["discovery_acquire_album"](
            "Artist", "Album", json.dumps({"mbid": "release-id"})
        ))

        self.assertEqual(result["status"], "implementation_called")
        self.assertEqual(calls, [("Artist", "Album", {"mbid": "release-id"})])
        self.assertEqual(job["status"], "retry_requested")
        self.assertEqual(job["candidate"], {})
        self.assertEqual(job["settings"], {})

    def test_dismissed_job_stays_blocked_if_reactivation_fails(self):
        self.ns["jobs"].append({
            "artist": "Artist", "album": "Album",
            "artist_key": "artist", "album_key": "album",
            "status": "dismissed",
        })
        self.ns["_discovery_reactivate_dismissed_acquisition"] = lambda *_args, **_kwargs: False
        result = json.loads(self.ns["discovery_acquire_album"]("Artist", "Album"))

        self.assertEqual(result["status"], "dismissed")
        self.assertEqual(result["ok"], False)

    def test_stale_downloading_job_recovers_watcher_without_requeueing(self):
        self.ns["jobs"].append({
            "artist": "Artist",
            "album": "Album",
            "artist_key": "artist",
            "album_key": "album",
            "status": "downloading",
            "candidate": {"username": "peer", "files": [{"filename": "Album/01.flac"}]},
            "settings": {"slskd_downloads_path": "/downloads"},
        })
        impl_calls = []
        self.ns["_discovery_acquire_album_impl"] = lambda *args: impl_calls.append(args)

        result = json.loads(self.ns["discovery_acquire_album"]("Artist", "Album"))

        self.assertEqual(result["status"], "recovery_started")
        self.assertEqual(impl_calls, [])
        self.assertIn(("artist", "album"), self.ns["_DISCOVERY_IMPORT_ACTIVE"])


if __name__ == "__main__":
    unittest.main()
