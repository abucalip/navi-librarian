"""Direct-import regressions for slskd download-transfer lookup."""

import unittest

from integrations.slskd.transfers import download_transfer_files


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


class FakeHTTP:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


class SlskdTransferLookupTests(unittest.TestCase):
    def call_lookup(self, response, username="peer/name"):
        http = FakeHTTP(response)
        result = download_transfer_files(
            "http://slskd.example", {"X-API-Key": "test"}, username,
            http_client=http,
        )
        return result, http

    def test_missing_peer_transfer_entry_is_treated_as_no_active_transfers(self):
        response = FakeResponse(404)
        result, http = self.call_lookup(response)
        self.assertEqual(result, [])
        self.assertFalse(response.json_called)
        self.assertEqual(
            http.calls,
            [(("http://slskd.example/api/v0/transfers/downloads/peer%2Fname",),
              {"headers": {"X-API-Key": "test"}, "timeout": 8})],
        )

    def test_other_http_errors_still_raise(self):
        with self.assertRaisesRegex(FakeHTTPError, "HTTP 503"):
            self.call_lookup(FakeResponse(503))

    def test_successful_transfer_response_is_parsed_with_remote_directory(self):
        response = FakeResponse(200, [
            {"directory": "/Music/Album", "files": [
                {"filename": "01 - Song.flac", "state": "Succeeded"}
            ]}
        ])
        result, http = self.call_lookup(response)
        self.assertEqual(result, [{
            "filename": "01 - Song.flac",
            "state": "Succeeded",
            "_transfer_directory": "/Music/Album",
        }])
        self.assertTrue(response.json_called)
        self.assertEqual(len(http.calls), 1)


if __name__ == "__main__":
    unittest.main()
