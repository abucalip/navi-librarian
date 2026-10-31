"""Direct-import regression tests for persistent data-directory resolution."""
import tempfile
import unittest
from pathlib import Path

from settings.data_directory import resolve_data_dir


class ResolveDataDirTests(unittest.TestCase):
    def test_configured_path_is_expanded(self):
        result = resolve_data_dir(
            {"DISCAIR_DATA_DIR": "~/librarian-data"},
            "/opt/librarian/navidrome_server.py",
        )
        self.assertEqual(result, Path("~/librarian-data").expanduser())

    def test_legacy_variable_is_used_when_new_one_is_absent(self):
        result = resolve_data_dir(
            {"NAVIDROME_LIBRARIAN_DATA_DIR": "/legacy/data"},
            "/opt/librarian/navidrome_server.py",
        )
        self.assertEqual(result, Path("/legacy/data"))

    def test_new_variable_wins_over_legacy_one(self):
        result = resolve_data_dir(
            {"DISCAIR_DATA_DIR": "/new/data", "NAVIDROME_LIBRARIAN_DATA_DIR": "/legacy/data"},
            "/opt/librarian/navidrome_server.py",
        )
        self.assertEqual(result, Path("/new/data"))

    def test_empty_configuration_uses_source_directory(self):
        result = resolve_data_dir(
            {"DISCAIR_DATA_DIR": ""},
            "/opt/librarian/navidrome_server.py",
        )
        self.assertEqual(result, Path("/opt/librarian"))

    def test_missing_configuration_uses_resolved_source_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "nested" / "navidrome_server.py"
            source.parent.mkdir()
            source.touch()
            result = resolve_data_dir({}, source)
            self.assertEqual(result, source.parent.resolve())


if __name__ == "__main__":
    unittest.main()
