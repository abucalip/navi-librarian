import unittest

from integrations.navidrome import client


class FakeResponse:
    def __init__(self, status_code=200, content_type="image/jpeg", body=b"\xff\xd8img"):
        self.status_code = status_code
        self.headers = {"content-type": content_type} if content_type else {}
        self.content = body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeHttp:
    def __init__(self, response):
        self.response = response
        self.requests = []

    def factory(self, **_options):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def get(self, url, *, params):
        self.requests.append((url, params))
        return self.response


def config():
    return "http://navidrome:4533", "owner", "stub-secret"


class CoverArtTests(unittest.TestCase):
    def fetch(self, response, **kwargs):
        http = FakeHttp(response)
        result = client.cover_art(
            config, "al-1", size=300,
            client_factory=http.factory, salt_factory=lambda: "salt", **kwargs,
        )
        return result, http

    def test_returns_image_bytes_with_signed_getCoverArt_request(self):
        (content_type, body), http = self.fetch(FakeResponse())
        self.assertEqual(content_type, "image/jpeg")
        self.assertEqual(body, b"\xff\xd8img")
        url, params = http.requests[0]
        self.assertEqual(url, "http://navidrome:4533/rest/getCoverArt.view")
        self.assertEqual(params["id"], "al-1")
        self.assertEqual(params["size"], 300)
        self.assertEqual(params["u"], "owner")
        self.assertEqual(params["s"], "salt")
        self.assertEqual(len(params["t"]), 32)

    def test_content_type_parameters_are_dropped(self):
        (content_type, _), _ = self.fetch(FakeResponse(content_type="image/png; charset=binary"))
        self.assertEqual(content_type, "image/png")

    def test_missing_cover_is_unavailable(self):
        with self.assertRaises(client.CoverArtUnavailable):
            self.fetch(FakeResponse(status_code=404))

    def test_json_error_body_is_never_returned_as_an_image(self):
        with self.assertRaises(client.CoverArtUnavailable):
            self.fetch(FakeResponse(content_type="application/json", body=b'{"error": "x"}'))

    def test_missing_content_type_is_unavailable(self):
        with self.assertRaises(client.CoverArtUnavailable):
            self.fetch(FakeResponse(content_type=None))

    def test_oversized_body_is_refused(self):
        big = b"0" * (client.MAX_COVER_BYTES + 1)
        with self.assertRaises(client.CoverArtUnavailable):
            self.fetch(FakeResponse(body=big))

    def test_server_error_propagates_for_the_route_to_map_to_502(self):
        with self.assertRaises(RuntimeError):
            self.fetch(FakeResponse(status_code=500))


if __name__ == "__main__":
    unittest.main()
