import unittest

from discovery.mbid_popularity import MUSICBRAINZ_RELEASE_SEARCH_URL, fetch_release_mbids


class _Response:
    def __init__(self, payload):
        self.payload, self.status_code = payload, 200

    def json(self):
        return self.payload


class ReleaseYearTests(unittest.TestCase):
    def test_earliest_year_comes_from_the_same_search_without_an_extra_call(self):
        releases = [
            {"id": "r1", "status": "Official", "date": "1975-03-01", "release-group": {"id": "g"}},
            {"id": "r2", "status": "Official", "date": "1969", "release-group": {"id": "g"}},
            {"id": "r3", "status": "Official", "date": "", "release-group": {"id": "h"}},
        ]
        calls = []

        def get(url, params=None, headers=None, timeout=None):
            calls.append(url)
            return _Response({"count": len(releases), "releases": releases})

        years = {}
        found = fetch_release_mbids(get, ["g", "h"], headers={}, years=years)
        self.assertEqual(years, {"g": 1969})
        self.assertIn("g", found)
        self.assertEqual(calls, [MUSICBRAINZ_RELEASE_SEARCH_URL])


if __name__ == "__main__":
    unittest.main()
