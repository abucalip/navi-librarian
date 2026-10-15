import unittest
from unittest.mock import patch

from listenbrainz_client import recent_listens


class FakeResponse:
    def __init__(self, listens):
        self._listens = listens
        self.raised = False

    def raise_for_status(self):
        self.raised = True

    def json(self):
        return {"payload": {"listens": self._listens}}


class FakeClient:
    def __init__(self, pages):
        self.pages = list(pages)
        self.requests = []
        self.responses = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def get(self, url, *, params, headers):
        self.requests.append((url, params, headers))
        response = FakeResponse(self.pages.pop(0))
        self.responses.append(response)
        return response


class ListenBrainzClientTests(unittest.TestCase):
    def test_fetches_bounded_pages_and_uses_oldest_timestamp_cursor(self):
        first_page = [{"listened_at": 1_700_000_000 - index} for index in range(100)]
        second_page = [{"listened_at": 1_699_999_899}]
        client = FakeClient([first_page, second_page])
        pauses = []

        result = recent_listens(
            "test-user",
            days=7,
            page_limit=3,
            client_factory=lambda **kwargs: client,
            clock=lambda: 1_700_000_100,
            sleep=pauses.append,
        )

        self.assertEqual(result, first_page + second_page)
        self.assertEqual(len(client.requests), 2)
        first_url, first_params, first_headers = client.requests[0]
        self.assertEqual(first_url, "https://api.listenbrainz.org/1/user/test-user/listens")
        self.assertEqual(first_params, {"min_ts": 1_699_395_300, "count": 100})
        self.assertEqual(first_headers, {"User-Agent": "NavidromeLibrarian/1.0"})
        self.assertEqual(client.requests[1][1], {
            "min_ts": 1_699_395_700,
            "count": 100,
            "max_ts": 1_699_999_900,
        })
        self.assertEqual(pauses, [0.2])
        self.assertTrue(all(response.raised for response in client.responses))

    def test_stops_on_empty_page(self):
        client = FakeClient([[]])
        result = recent_listens(
            "test-user",
            page_limit=2,
            client_factory=lambda **kwargs: client,
            clock=lambda: 100_000,
            sleep=lambda _seconds: self.fail("sleep should not be called"),
        )
        self.assertEqual(result, [])
        self.assertEqual(len(client.requests), 1)

    def test_stops_when_a_page_is_short(self):
        client = FakeClient([[{"listened_at": 99}]])
        result = recent_listens(
            "test-user",
            client_factory=lambda **kwargs: client,
            clock=lambda: 100_000,
            sleep=lambda _seconds: self.fail("sleep should not be called"),
        )
        self.assertEqual(result, [{"listened_at": 99}])
        self.assertEqual(len(client.requests), 1)

    def test_legacy_server_adapter_preserves_signature_and_username_lookup(self):
        import navidrome_server

        expected = [{"listened_at": 123}]
        with patch.object(navidrome_server, "_listenbrainz_username", return_value="configured-user"), patch.object(
            navidrome_server._listenbrainz_client,
            "recent_listens",
            return_value=expected,
        ) as recent:
            self.assertIs(navidrome_server._listenbrainz_recent(days=12, page_limit=4), expected)

        recent.assert_called_once_with("configured-user", days=12, page_limit=4)


if __name__ == "__main__":
    unittest.main()
