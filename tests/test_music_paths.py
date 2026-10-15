"""Direct-import regressions for music library path selection."""
import unittest
from pathlib import Path
from music_paths import default_music_dir


class DefaultMusicDirTests(unittest.TestCase):
    def test_explicit_override_wins_and_expands_home(self):
        result = default_music_dir({"NAVIDROME_MUSIC_DIR": "~/music-library"},
                                   lambda path: self.fail("unexpected mount lookup"))
        self.assertEqual(result, Path("~/music-library").expanduser())

    def test_server_mount_is_preferred(self):
        checked = []
        result = default_music_dir({}, lambda path: checked.append(path) or True)
        self.assertEqual(result, Path("/media/library/music"))
        self.assertEqual(checked, [Path("/media/library/music")])

    def test_mac_mount_is_fallback(self):
        checked = []
        result = default_music_dir({}, lambda path: checked.append(path) or path == Path("/Volumes/media/library/music"))
        self.assertEqual(result, Path("/Volumes/media/library/music"))
        self.assertEqual(checked, [Path("/media/library/music"), Path("/Volumes/media/library/music")])

    def test_server_path_is_final_fallback(self):
        checked = []
        result = default_music_dir({}, lambda path: checked.append(path) or False)
        self.assertEqual(result, Path("/media/library/music"))
        self.assertEqual(checked, [Path("/media/library/music"), Path("/Volumes/media/library/music")])


if __name__ == "__main__":
    unittest.main()
