"""Offline tests: ListenBrainz calls carry the honest identity; MusicBrainz never gets the token."""
import os
import unittest
from unittest import mock

from discovery_candidate_gathering import RecommendationProviders, gather_recommendation_candidates
from integrations.listenbrainz.client import USER_AGENT

TOKEN = "fixture-token-not-real"


class _Response:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"payload": {"mbids": [{"recording_mbid": "rec-0", "score": 9}]}}


class _Client:
    def __init__(self, mb_headers, mb_urls):
        self.mb_headers = mb_headers
        self.mb_urls = mb_urls

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        self.mb_headers.append(dict(headers or {}))
        self.mb_urls.append(url)
        response = _Response()
        response.json = lambda: {"genres": [], "release-groups": []}
        return response


def _raise_status():
    raise RuntimeError("502")


class ListenBrainzHeaderTests(unittest.TestCase):
    def _run(self, env):
        lb, mb, self.mb_urls = [], [], []

        def http_get(url, params=None, headers=None, **kwargs):
            lb.append((url, dict(headers or {})))
            response = _Response()
            if "metadata" in url:
                response.json = lambda: []
            return response

        def http_post(url, json=None, headers=None, **kwargs):
            lb.append((url, dict(headers or {})))
            response = _Response()
            response.status_code = 502
            response.raise_for_status = _raise_status
            return response

        providers = RecommendationProviders(
            listenbrainz_recent=lambda days: [{"track_metadata": {
                "artist_name": "a", "additional_info": {"artist_mbid": "a-mbid"}}}],
            listenbrainz_username=lambda: "fixture-user",
            music_key=lambda value: "".join(str(value).casefold().split()),
            metadata_cache_get=lambda key, **kw: None,
            metadata_cache_set=lambda key, value, **kw: None,
            is_album_candidate=lambda candidate: True,
            api_call=lambda *args, **kwargs: {},
            items=lambda response: [],
            http_get=http_get,
            http_post=http_post,
            http_client=lambda *args, **kwargs: _Client(mb, self.mb_urls),
            sleep=lambda seconds: None,
        )
        with mock.patch.dict(os.environ, env, clear=False):
            gather_recommendation_candidates(providers)
        return lb, mb

    def test_listenbrainz_calls_send_identity_and_token(self):
        lb, _ = self._run({"LISTENBRAINZ_TOKEN": TOKEN})
        self.assertTrue(lb, "guard: no ListenBrainz request was captured")
        urls = " ".join(url for url, _ in lb)
        self.assertIn("/cf/recommendation/", urls)
        self.assertIn("/metadata/artist/", urls)
        for url, headers in lb:
            self.assertEqual(headers.get("User-Agent"), USER_AGENT, url)
            self.assertEqual(headers.get("Authorization"), f"Token {TOKEN}", url)

    def test_musicbrainz_never_receives_the_token(self):
        _, mb = self._run({"LISTENBRAINZ_TOKEN": TOKEN})
        self.assertTrue(mb, "guard: no MusicBrainz request was captured")
        self.assertTrue(
            any("/ws/2/recording/" in url for url in self.mb_urls),
            "guard: the failed batch must fall back to a per-recording MusicBrainz request",
        )
        for headers in mb:
            self.assertNotIn("Authorization", headers)

    def test_without_a_token_only_the_identity_is_sent(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LISTENBRAINZ_TOKEN", None)
            lb, _ = self._run({})
        self.assertTrue(lb)
        for _url, headers in lb:
            self.assertEqual(headers, {"User-Agent": USER_AGENT})


if __name__ == "__main__":
    unittest.main()
