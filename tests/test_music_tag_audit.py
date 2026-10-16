import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from music_tag_audit import scan_missing_mbids


class MusicTagAuditTests(unittest.TestCase):
    def test_reports_missing_ids_in_sorted_bounded_batch_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "b.mp3").write_bytes(b"")
            (root / "a.flac").write_bytes(b"")
            (root / "ignore.txt").write_text("untouched")
            calls = []

            def reader(path, **kwargs):
                calls.append((path.name, kwargs))
                if path.name == "a.flac":
                    return SimpleNamespace(tags={
                        "MusicBrainz Track Id": ["track-id"],
                        "MusicBrainz Album Id": ["album-id"],
                        "MusicBrainz Artist Id": ["artist-id"],
                        "MusicBrainz Album Artist Id": ["albumartist-id"],
                    })
                return SimpleNamespace(tags={})

            result = scan_missing_mbids(root, max_files=1, audio_file_reader=reader)
            self.assertEqual(result["total_audio_files_found"], 2)
            self.assertEqual(result["results"], [])
            self.assertEqual(result["files_in_batch"], 1)
            self.assertTrue(result["more_files_remaining"])
            self.assertEqual(calls, [("a.flac", {"easy": False})])
            self.assertEqual((root / "ignore.txt").read_text(), "untouched")

    def test_missing_empty_and_unreadable_tags_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "empty.mp3").write_bytes(b"")
            (root / "bad.flac").write_bytes(b"")

            def reader(path, **_kwargs):
                if path.name == "bad.flac":
                    raise ValueError("bad tags")
                return SimpleNamespace(tags={
                    "MUSICBRAINZ_TRACKID": [""],
                    "musicbrainz_albumid": ["album-id"],
                })

            result = scan_missing_mbids(root, audio_file_reader=reader)
            self.assertEqual(result["files_with_missing_ids"], 1)
            self.assertEqual(result["unreadable_files"], 1)
            self.assertEqual(result["results"][0]["file"], "empty.mp3")
            self.assertEqual(result["results"][0]["missing_ids"], [
                "track_mbid", "artist_mbid", "albumartist_mbid"
            ])

    def test_validation_and_unavailable_directory_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reader = lambda *_a, **_k: None
            self.assertEqual(
                scan_missing_mbids(root, 0, audio_file_reader=reader),
                "max_files must be between 1 and 5000.",
            )
            self.assertEqual(
                scan_missing_mbids(root, 1, -1, audio_file_reader=reader),
                "offset must be non-negative.",
            )
            self.assertIn(
                "Music directory is unavailable",
                scan_missing_mbids(root / "missing", audio_file_reader=reader),
            )


if __name__ == "__main__":
    unittest.main()
