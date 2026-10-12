"""Regression tests for retryable artwork-provider failures."""
import ast
import unittest
from pathlib import Path
from time import monotonic
from urllib.parse import urlencode

class HTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code


SOURCE = Path(__file__).resolve().parents[1] / "app" / "main.py"


class FailingArtworkProvider:
    def get(self, _url):
        raise TimeoutError("simulated Deezer timeout")


def load_artwork_route(provider, cache):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    route = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "album_artwork"
    )
    route.decorator_list = []
    namespace = {
        "HTTPException": HTTPException,
        "urlencode": urlencode,
        "monotonic": monotonic,
        "_artwork_cache": cache,
        "_ARTWORK_CACHE_TTL": 6 * 60 * 60,
        "_ARTWORK_NEGATIVE_CACHE_TTL": 5 * 60,
        "_EXTERNAL_HTTP": provider,
    }
    exec(compile(ast.Module(body=[route], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["album_artwork"]


class ArtworkRetryTests(unittest.TestCase):
    def test_provider_timeout_is_retryable_and_not_negative_cached(self):
        cache = {}
        route = load_artwork_route(FailingArtworkProvider(), cache)

        result = route(artist="Example Artist", album="Example Album")

        self.assertIsNone(result["artwork_url"])
        self.assertTrue(result["retryable"])
        self.assertEqual(cache, {})


if __name__ == "__main__":
    unittest.main()
