"""Album review outlets shared by the route and the owned prefetch (efficiency K3, reviews).

No test reaches the network: outlets are replaced, or ``httpx.get`` is patched.
"""
import os
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import httpx

from app.api import metadata
from app.services import album_review_sources as ars
from app.services import owned_prefetch as op
from app.services import persistent_metadata
from app.services import prefetch_state as ps


def review(source):
    return {"source": source, "quote": f"{source} says a thing about this record, in a line.",
            "url": f"https://{source.lower().replace(' ', '')}.example/1"}


class _Store:
    """The metadata store as the worker sees it: ``read(key, ttl)`` and ``write(key, value)``."""

    def __init__(self):
        self.data = {}

    def read(self, key, ttl_seconds=None):
        return self.data.get(key)

    def write(self, key, value):
        self.data[key] = value


class _Case(unittest.TestCase):
    def setUp(self):
        self.store = _Store()
        env = mock.patch.dict(os.environ, {"GUARDIAN_API_KEY": ""})
        env.start()
        self.addCleanup(env.stop)

    def outlets(self, answers):
        """Replace the outlet fetchers: ``answers`` maps an outlet name to a review, None, or an exception."""
        asked = []

        def answer(name):
            asked.append(name)
            value = answers.get(name)
            if isinstance(value, BaseException):
                raise value
            return value

        patches = [mock.patch.object(ars, "pitchfork_review", lambda get, artist, album: answer("Pitchfork")),
                   mock.patch.object(ars, "wordpress_review", lambda get, name, site, artist, album: answer(name))]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        return asked

    def prefetch(self, refused=()):
        return ars.prefetch_reviews(self.store.read, self.store.write, mock.sentinel.get, "Opeth", "Watershed",
                                    refused=refused)


class PrefetchTests(_Case):
    def test_a_complete_list_is_stored_under_the_route_s_keys(self):
        asked = self.outlets({"Pitchfork": review("Pitchfork"), "Treble": review("Treble")})
        self.assertTrue(self.prefetch())
        self.assertEqual(len(asked), 1 + len(ars.WORDPRESS_REVIEW_SITES), "every outlet, one after another")
        self.assertEqual(self.store.data["album-reviews:v1:opeth:watershed"],
                         {"reviews": [review("Pitchfork"), review("Treble")]})
        self.assertEqual(self.store.data["album-review-source:v1:Treble:opeth:watershed"]["review"], review("Treble"))
        self.assertIsNone(self.store.data["album-review-source:v1:PopMatters:opeth:watershed"]["review"])

    def test_fresh_stored_answers_are_not_asked_again(self):
        self.outlets({"Pitchfork": review("Pitchfork")})
        self.prefetch()
        asked = self.outlets({})
        self.assertTrue(self.prefetch())
        self.assertEqual(asked, [])

    def test_a_failed_outlet_is_marked_and_a_partial_list_is_not_stored(self):
        self.outlets({"Pitchfork": review("Pitchfork"), "Treble": TimeoutError()})
        self.assertFalse(self.prefetch())
        self.assertNotIn("album-reviews:v1:opeth:watershed", self.store.data)
        self.assertNotIn("album-review-source:v1:Treble:opeth:watershed", self.store.data)
        self.assertTrue(self.store.data["album-review-source-failed:v1:Treble:opeth:watershed"]["negative"])
        asked = self.outlets({})
        self.assertFalse(self.prefetch(), "the resting outlet still makes the list partial")
        self.assertEqual(asked, [], "and is not asked within its hour")

    def test_a_refusal_ends_the_album_and_marks_nothing(self):
        asked = self.outlets({"Pitchfork": ps.BudgetExhausted("daily cap reached for reviews")})
        self.assertFalse(self.prefetch(refused=(ps.BudgetExhausted,)))
        self.assertEqual(asked, ["Pitchfork"], "the other outlets are left for the first view")
        self.assertEqual(self.store.data, {})

    def test_with_no_review_anywhere_nothing_is_stored_as_the_list(self):
        self.outlets({})
        self.assertTrue(self.prefetch())
        self.assertNotIn("album-reviews:v1:opeth:watershed", self.store.data)

    def test_the_guardian_is_asked_only_with_a_key(self):
        names = [name for name, _ in ars.outlet_asks(None, None, None, "A", "B")]
        self.assertNotIn("The Guardian", names)
        names = [name for name, _ in ars.outlet_asks(None, None, None, "A", "B", "key")]
        self.assertEqual(names[:2], ["Pitchfork", "The Guardian"])


class ParityTests(_Case):
    """The route answers from what the prefetch stored, with its HTTP client failing on any request."""

    def setUp(self):
        super().setUp()
        persistent_metadata.attach(self.store.read, self.store.write)
        self.addCleanup(persistent_metadata.detach)
        metadata._review_cache.clear()
        self.addCleanup(metadata._review_cache.clear)

    def test_a_prefetched_list_is_the_route_s_answer_without_a_request(self):
        self.outlets({"Pitchfork": review("Pitchfork"), "Consequence": review("Consequence")})
        self.prefetch()
        failing = mock.Mock()
        failing.get.side_effect = AssertionError("the route sent a request")
        with mock.patch.object(metadata, "_EXTERNAL_HTTP", failing):
            answer = metadata.album_reviews_for("Opeth", "Watershed")
        self.assertEqual(answer, {"reviews": [review("Pitchfork"), review("Consequence")]})
        failing.get.assert_not_called()

    def test_prefetched_outlet_answers_serve_the_route_when_the_list_was_not_stored(self):
        self.outlets({})
        self.prefetch()
        asked = self.outlets({})
        self.assertEqual(metadata.album_reviews_for("Opeth", "Watershed"), {"reviews": []})
        self.assertEqual(asked, [], "every outlet answered from the stored \"nothing there\"")


class WorkerWiringTests(unittest.TestCase):
    def librarian(self, store):
        return SimpleNamespace(_metadata_cache_get=store.read, _metadata_cache_set=store.write)

    def test_reviews_are_prefetched_only_with_a_reviews_cap(self):
        store = _Store()
        without = op.entity_extras(self.librarian(store), ps.Spend({"musicbrainz": 5}))
        self.assertEqual(without["albums"], [])
        with_cap = op.entity_extras(self.librarian(store), ps.Spend({"reviews": 50}))
        self.assertEqual(len(with_cap["albums"]), 1)

    def test_outlet_requests_are_counted_under_the_reviews_cap_and_refused_past_it(self):
        store = _Store()
        spend = ps.Spend({"reviews": 3})
        extra = op.entity_extras(self.librarian(store), spend)["albums"][0]
        empty = httpx.Response(200, json=[], request=httpx.Request("GET", "https://pitchfork.com/search/"))
        with mock.patch.dict(os.environ, {"GUARDIAN_API_KEY": ""}), \
                mock.patch("httpx.get", return_value=empty) as get:
            extra({"artist": "Opeth", "name": "Watershed"})
        self.assertEqual(get.call_count, 3, "three outlets answered, the fourth was refused before it was sent")
        self.assertEqual(spend.snapshot()["reviews"], 3)
        self.assertEqual(spend.cap_reached, {"reviews"})
        self.assertFalse(any(key.startswith("album-review-source-failed:") for key in store.data),
                         "a refusal is not a failure mark")
        self.assertNotIn("album-reviews:v1:opeth:watershed", store.data)
        self.assertEqual(get.call_args_list[0].kwargs["timeout"], ars.REVIEW_PAGE_TIMEOUT)

    def test_every_outlet_host_is_counted_as_reviews(self):
        for url in ["https://pitchfork.com/search/", "https://content.guardianapis.com/search"] + [
                site + "/wp-json/wp/v2/search" for _, site in ars.WORDPRESS_REVIEW_SITES]:
            self.assertEqual(ps.provider_of(url), "reviews", url)


if __name__ == "__main__":
    unittest.main()
