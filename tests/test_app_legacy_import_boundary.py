"""Regression tests for the app-to-legacy-server import boundary guard."""
import tempfile
import unittest
from pathlib import Path

from scripts.check_app_legacy_imports import check_app_imports


class AppLegacyImportBoundaryTests(unittest.TestCase):
    def write(self, root: Path, relative: str, content: str) -> None:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_allows_only_the_lazy_compatibility_adapter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "app/api/dependencies.py", """
def get_librarian():
    import navidrome_server as librarian
    return librarian
""")
            self.assertEqual(check_app_imports(root), [])

    def test_rejects_module_level_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "app/api/routes.py", "import navidrome_server\n")
            errors = check_app_imports(root)
            self.assertEqual(len(errors), 1)
            self.assertIn("app/api/routes.py:1", errors[0])

    def test_rejects_import_in_wrong_function_or_path(self):
        cases = [
            ("app/api/dependencies.py", "def another():\n    import navidrome_server\n"),
            ("app/services/domain.py", "def get_librarian():\n    import navidrome_server\n"),
            ("app/api/dependencies.py", "from navidrome_server import api_call\n"),
            ("app/api/dependencies.py", "def get_librarian():\n    from navidrome_server import api_call\n"),
            ("app/api/dependencies.py", "def get_librarian():\n    import navidrome_server.submodule\n"),
        ]
        for relative, content in cases:
            with self.subTest(relative=relative, content=content):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    self.write(root, relative, content)
                    self.assertTrue(check_app_imports(root))

    def test_reports_unparseable_python(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write(root, "app/broken.py", "def broken(:\n")
            errors = check_app_imports(root)
            self.assertEqual(len(errors), 1)
            self.assertIn("unable to parse Python source", errors[0])


if __name__ == "__main__":
    unittest.main()
