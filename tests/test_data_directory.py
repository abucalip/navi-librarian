"""Direct-import regression tests for persistent data-directory resolution."""
import tempfile
import unittest
from pathlib import Path

from data_directory import resolve_data_dir


class ResolveDataDirTests(unittest.TestCase):
    def test_configured_path_is_expanded(self):
        result = resolve_data_dir(
            {"NAVIDROME_LIBRARIAN_DATA_DIR": "~/librarian-data"},
            "/opt/librarian/navidrome_server.py",
        )
        self.assertEqual(result, Path("~/librarian-data").expanduser())

    def test_empty_configuration_uses_source_directory(self):
        result = resolve_data_dir(
            {"NAVIDROME_LIBRARIAN_DATA_DIR": ""},
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
