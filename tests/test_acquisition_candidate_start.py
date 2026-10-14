"""Direct regression tests for queued slskd candidate-start validation."""
import unittest
from types import SimpleNamespace

from acquisition_candidate_start import candidate_start_state


class FakeHTTPError(Exception):
    pass


class FakeClock:
    def __init__(self):
        self.value = 0.0

    def monotonic(self):
        return self.value

    def sleep(self, seconds):
        self.value += seconds


class FakeHTTP:
    def __init__(self, status_code=204, error=None):
        self.status_code = status_code
        self.error = error
        self.calls = []

    def delete(self, url, **kwargs):
        self.calls.append((url, kwargs))
        if self.error:
            raise self.error
        return SimpleNamespace(status_code=self.status_code)


class CandidateStartValidationTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.http = FakeHTTP()
        self.transfer_calls = []
        self.transfers = []

    def lookup(self, *_args):
        self.transfer_calls.append(_args)
        return self.transfers

    def run_check(self, candidate, timeout=1):
        return candidate_start_state(
            "http://slskd", {"X-API-KEY": "test"}, candidate, timeout,
            download_transfer_files=self.lookup,
            http_client=self.http,
            http_error_types=(FakeHTTPError,),
            monotonic=self.clock.monotonic,
            sleep=self.clock.sleep,
        )

    def test_rejects_parent_traversal_before_transfer_lookup(self):
        result = self.run_check({
            "username": "peer",
            "files": [{"filename": "Album/../Other/01.flac"}],
        })
        self.assertIsNone(result)
        self.assertEqual(self.transfer_calls, [])

    def test_rejects_files_from_multiple_remote_directories(self):
        result = self.run_check({
            "username": "peer",
            "files": [
                {"filename": "Album/01.flac"},
                {"filename": "Other/02.flac"},
            ],
        })
        self.assertIsNone(result)
        self.assertEqual(self.transfer_calls, [])

    def test_accepts_matching_active_transfer(self):
        self.transfers = [{
            "filename": "album/01.FLAC",
            "state": "in_progress",
            "_transfer_directory": "Album",
        }]
        self.assertIs(self.run_check({
            "username": "peer", "files": [{"filename": "Album/01.flac"}],
        }), True)
        self.assertEqual(len(self.transfer_calls), 1)

    def test_cancels_queued_transfer_before_reporting_safe_fallback(self):
        self.transfers = [{
            "id": "queued-id",
            "filename": "Album/01.flac",
            "state": "queued",
            "_transfer_directory": "Album",
        }]
        self.assertIs(self.run_check({
            "username": "peer", "files": [{"filename": "Album/01.flac"}],
        }, timeout=0.5), False)
        self.assertEqual(len(self.http.calls), 1)
        self.assertIn("/peer/queued-id", self.http.calls[0][0])

    def test_uncertain_cancellation_refuses_fallback(self):
        self.transfers = [{
            "id": "queued-id",
            "filename": "Album/01.flac",
            "state": "queued",
            "_transfer_directory": "Album",
        }]
        self.http.status_code = 500
        self.assertIsNone(self.run_check({
            "username": "peer", "files": [{"filename": "Album/01.flac"}],
        }, timeout=0.5))

    def test_cancellation_transport_error_refuses_fallback(self):
        self.transfers = [{
            "id": "queued-id",
            "filename": "Album/01.flac",
            "state": "queued",
            "_transfer_directory": "Album",
        }]
        self.http.error = FakeHTTPError("unknown cancellation outcome")
        self.assertIsNone(self.run_check({
            "username": "peer", "files": [{"filename": "Album/01.flac"}],
        }, timeout=0.5))

    def test_transfer_lookup_error_is_uncertain(self):
        def broken_lookup(*_args):
            raise FakeHTTPError("transfer lookup failed")

        self.assertIsNone(candidate_start_state(
            "http://slskd", {}, {
                "username": "peer", "files": [{"filename": "Album/01.flac"}],
            }, 1,
            download_transfer_files=broken_lookup,
            http_client=self.http,
            http_error_types=(FakeHTTPError,),
            monotonic=self.clock.monotonic,
            sleep=self.clock.sleep,
        ))


if __name__ == "__main__":
    unittest.main()
