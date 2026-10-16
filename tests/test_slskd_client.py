"""Direct-import regressions for the slskd connectivity probe."""
import json
import unittest
from unittest.mock import Mock

import httpx

from slskd_client import test_connection


class SlskdConnectionTests(unittest.TestCase):
    def setUp(self):
        self.response = Mock(status_code=200)
        self.response.raise_for_status.return_value = None
        self.http_get = Mock(return_value=self.response)
        self.config = Mock(return_value=("http://slskd.test", "secret-key", "/downloads"))

    def payload(self):
        return json.loads(test_connection(self.config, http_get=self.http_get))

    def test_success_preserves_request_and_response_contract(self):
        result = self.payload()
        self.assertEqual(result, {
            "ok": True,
            "status": "connected",
            "http_status": 200,
            "message": "slskd API connection succeeded.",
        })
        self.http_get.assert_called_once_with(
            "http://slskd.test/api/v0/server",
            headers={"X-API-KEY": "secret-key"},
            timeout=8,
        )

    def test_authentication_failures_are_distinguished_without_exposing_key(self):
        for status in (401, 403):
            with self.subTest(status=status):
                self.response.status_code = status
                self.response.raise_for_status.reset_mock()
                result = self.payload()
                self.assertEqual(result["status"], "authentication_failed")
                self.assertFalse(result["ok"])
                self.assertNotIn("secret-key", json.dumps(result))
                self.response.raise_for_status.assert_not_called()

    def test_http_error_is_mapped_to_connection_failed(self):
        self.response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "server unavailable", request=Mock(), response=Mock(status_code=503)
        )
        result = self.payload()
        self.assertEqual(result["status"], "connection_failed")
        self.assertEqual(result["message"], "server unavailable")

    def test_missing_configuration_is_mapped_to_connection_failed(self):
        self.config.side_effect = ValueError("slskd URL is not configured")
        result = self.payload()
        self.assertEqual(result["status"], "connection_failed")
        self.assertEqual(result["message"], "slskd URL is not configured")
        self.http_get.assert_not_called()

    def test_api_key_is_not_returned_on_success(self):
        result = self.payload()
        self.assertNotIn("secret-key", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
