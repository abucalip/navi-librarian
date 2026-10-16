"""Direct-import tests for slskd query polling and delayed peer payloads."""

import unittest
from types import SimpleNamespace

from slskd_search import response_items, search_queries
from acquisition_search_diagnostics import no_match_message
from slskd_search_polling import collect_search_responses


class FakeHTTPError(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.response = SimpleNamespace(status_code=status_code)


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise FakeHTTPError(self.status_code)


class FakeSlskdClient:
    HTTPStatusError = FakeHTTPError

    def __init__(self, mode):
        self.mode = mode
        self.posted = []
        self.state_calls = 0
        self.peer = {
            "username": "peer",
            "files": [{"filename": "Other Artist/Other Album/01 - Track.flac", "size": 1000}],
        }

    def post(self, _url, headers=None, json=None, timeout=None):
        self.posted.append({"payload": json, "timeout": timeout})
        return FakeResponse({})

    def get(self, url, params=None, headers=None, timeout=None):
        if url.endswith("/responses"):
            return FakeResponse([])
        if self.mode == "legacy":
            return FakeResponse([], 405) if url.endswith("/responses") else FakeResponse(None, 404)
        if self.mode == "error":
            return FakeResponse(None, 500)
        if self.mode == "wait":
            self.state_calls += 1
            if self.state_calls <= 26:
                return FakeResponse({
                    "isComplete": False,
                    "state": "InProgress",
                    "responseCount": 26,
                    "fileCount": 362,
                    "responses": [],
                })
            return FakeResponse({
                "isComplete": True,
                "state": "Completed, TimedOut",
                "responseCount": 26,
                "fileCount": 362,
                "responses": [self.peer],
            })
        query_index = len(self.posted) - 1
        if query_index == 0:
            return FakeResponse({"isComplete": True, "responseCount": 0, "fileCount": 0})
        return FakeResponse({
            "isComplete": True,
            "state": "Completed, TimedOut",
            "responseCount": 1,
            "fileCount": 1,
            "responses": [self.peer],
        })


class SlskdSearchPollingTests(unittest.TestCase):
    def run_search(self, client, queries):
        clock = [0.0]
        ids = iter(f"search-{index}" for index in range(1, 10))
        return collect_search_responses(
            queries,
            "http://slskd",
            {"X-API-KEY": "test"},
            http_client=client,
            monotonic=lambda: clock[0],
            sleep=lambda seconds: clock.__setitem__(0, clock[0] + seconds),
            new_search_id=lambda: next(ids),
            response_items=response_items,
        )

    def test_retries_broader_query_when_exact_query_has_no_payload(self):
        client = FakeSlskdClient("fallback")
        queries = search_queries("Tinariwen", "Idrache (Traces of the Past)")
        self.assertEqual(queries, [
            "Tinariwen Idrache (Traces of the Past)",
            "Tinariwen Idrache Traces of the Past",
        ])
        result = self.run_search(client, queries)

        self.assertEqual([item["payload"]["searchText"] for item in client.posted],
                         queries)
        self.assertEqual([item["payload"]["searchTimeout"] for item in client.posted],
                         [15000, 6000])
        self.assertEqual([item["query"] for item in result["search_attempts"]],
                         queries)
        self.assertEqual(result["search_attempts"][0]["collected_peer_response_count"], 0)
        self.assertEqual(result["search_attempts"][1]["collected_peer_response_count"], 1)
        self.assertEqual(result["reported_response_count"], 1)
        self.assertEqual(len(result["payload_by_peer"]), 1)
        message = no_match_message(
            response_count=1, audio_file_count=1,
            reported_response_count=result["reported_response_count"],
            reported_file_count=result["reported_file_count"],
            search_attempts=result["search_attempts"],
        )
        self.assertIn("Queries tried: " + " -> ".join(queries), message)

    def test_legacy_404_405_endpoints_are_tolerated(self):
        client = FakeSlskdClient("legacy")
        result = self.run_search(client, ["Exact Artist Album"])

        self.assertEqual(len(client.posted), 1)
        self.assertEqual(result["search_attempts"][0]["state"], "unknown")
        self.assertEqual(result["search_attempts"][0]["collected_peer_response_count"], 0)

    def test_unexpected_state_http_error_propagates(self):
        client = FakeSlskdClient("error")
        with self.assertRaises(FakeHTTPError):
            self.run_search(client, ["Exact Artist Album"])

    def test_waits_for_peer_payload_when_slskd_reports_responses(self):
        client = FakeSlskdClient("wait")
        result = self.run_search(client, ["Exact Artist Album", "Artist Album"])

        self.assertGreater(client.state_calls, 24)
        self.assertEqual(len(client.posted), 1)
        self.assertEqual(result["search_attempts"][0]["collected_peer_response_count"], 1)
        self.assertEqual(result["search_attempts"][0]["state"], "completed, timedout")
        self.assertEqual(result["reported_response_count"], 26)
        self.assertEqual(result["reported_file_count"], 362)


if __name__ == "__main__":
    unittest.main()
