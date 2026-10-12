"""Regression tests for slskd transfer-list lifecycle responses."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote

SOURCE = Path(__file__).resolve().parents[1] / "navidrome_server.py"


class FakeHTTPError(RuntimeError):
    pass


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload
        self.json_called = False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise FakeHTTPError(f"HTTP {self.status_code}")

    def json(self):
        self.json_called = True
        return self.payload


def load_transfer_helper():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    helper = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_slskd_download_transfer_files"
    )
    namespace = {"httpx": None}
    module = ast.Module(body=[helper], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(SOURCE), "exec"), namespace)
    return namespace


class SlskdTransferLookupTests(unittest.TestCase):
    def call_helper(self, response):
        namespace = load_transfer_helper()
        calls = []
        namespace["httpx"] = SimpleNamespace(
            get=lambda *args, **kwargs: (calls.append((args, kwargs)) or response)
        )
        result = namespace["_slskd_download_transfer_files"](
            "http://slskd.example", {"X-API-Key": "test"}, "peer/name"
        )
        return result, calls

    def test_missing_peer_transfer_entry_is_treated_as_no_active_transfers(self):
        response = FakeResponse(404)
        result, calls = self.call_helper(response)
        self.assertEqual(result, [])
        self.assertFalse(response.json_called)
        self.assertEqual(
            calls[0][0][0],
            "http://slskd.example/api/v0/transfers/downloads/peer%2Fname",
        )

    def test_other_http_errors_still_raise(self):
        response = FakeResponse(503)
        with self.assertRaises(FakeHTTPError):
            self.call_helper(response)

    def test_successful_transfer_response_is_parsed(self):
        response = FakeResponse(200, [
            {"directory": "/Music/Album", "files": [
                {"filename": "01 - Song.flac", "state": "Succeeded"}
            ]}
        ])
        result, _ = self.call_helper(response)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["filename"], "01 - Song.flac")
        self.assertEqual(result[0]["_transfer_directory"], "/Music/Album")


if __name__ == "__main__":
    unittest.main()
