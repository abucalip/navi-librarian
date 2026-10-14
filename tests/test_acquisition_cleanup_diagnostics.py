"""Focused regression tests for safe acquisition-dismiss cleanup diagnostics."""
import ast
import logging
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

SOURCE = Path(__file__).resolve().parents[1] / "navidrome_server.py"


def load_cleanup_helper():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    node = next(
        item for item in tree.body
        if isinstance(item, ast.FunctionDef)
        and item.name == "_discovery_cancel_and_clean_source"
    )
    node.decorator_list = []
    namespace = {
        "Path": Path,
        "httpx": SimpleNamespace(
            HTTPError=Exception,
            delete=Mock(return_value=SimpleNamespace(status_code=204)),
        ),
        "_slskd_download_transfer_files": lambda *_args, **_kwargs: [],
        "_discovery_safe_folder_name": lambda value: str(value or ""),
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
                 str(SOURCE), "exec"), namespace)
    return namespace["_discovery_cancel_and_clean_source"], namespace


class AcquisitionCleanupDiagnosticsTests(unittest.TestCase):
    def test_invalid_download_root_logs_safe_failure_stage(self):
        cleanup, _namespace = load_cleanup_helper()
        candidate = {
            "username": "peer",
            "folder": "release",
            "files": [{"filename": "release/track.mp3", "size": 3}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            missing_root = Path(temporary) / "does-not-exist"
            with self.assertLogs(level="WARNING") as captured:
                result = cleanup(str(missing_root), candidate, "http://slskd", {})
        self.assertFalse(result)
        self.assertIn("configured download root is missing, symlinked, or invalid",
                      " ".join(captured.output))

    def test_verified_album_files_are_removed_without_recursive_delete(self):
        cleanup, namespace = load_cleanup_helper()
        candidate = {
            "username": "peer",
            "folder": "release",
            "files": [{"filename": "release/track.mp3", "size": 3}],
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            album_folder = root / "release"
            album_folder.mkdir()
            track = album_folder / "track.mp3"
            track.write_bytes(b"abc")
            self.assertTrue(cleanup(str(root), candidate, "http://slskd", {}))
            self.assertFalse(track.exists())
            self.assertFalse(album_folder.exists())
        namespace["httpx"].delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
