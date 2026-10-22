import unittest
from discovery.new_releases import fetch_artist_release_groups

from discovery.new_releases import new_release_window, build_new_release_lookup, build_new_release_response, merge_release_candidates, prepare_new_release_library_scope, select_artist_release_candidates
from discovery.recommendations import is_album_candidate, is_various_artists, music_key


def exact_credit(credit, artist):
    if not isinstance(credit, list):
        return False
    return any(
        isinstance(part, dict)
        and music_key((part.get("artist") or {}).get("name") or part.get("name") or "") == music_key(artist)
        for part in credit
    )


def group(title, date, *, artist="Björk", primary="Album", secondary=None, credit=None, mbid=None):
    return {
        "title": title,
        "first-release-date": date,
        "primary-type": primary,
        "secondary-types": secondary or [],
        "artist-credit": credit if credit is not None else [{"artist": {"name": artist}}],
        "id": mbid,
    }


class NewReleaseCandidateSelectionTests(unittest.TestCase):
    def select(self, groups, owned=None, artist="Björk"):
        return select_artist_release_candidates(
            groups,
            artist=artist,
            artist_record={"album_count": 4},
            owned=owned or set(),
            cutoff_date="2024-10-16",
            current_year=2026,
            music_key=music_key,
            is_album_candidate=is_album_candidate,
            exact_artist_credit_matches=exact_credit,
            is_various_artists=is_various_artists,
        )

    def test_selects_eligible_unowned_album_and_preserves_payload(self):
        result = self.select([group("Fossora", "2025-09-30", mbid="release-1")])
        self.assertEqual(list(result), [("bjork", "fossora")])
        candidate = result[("bjork", "fossora")]
        self.assertEqual(candidate["year"], 2025)
        self.assertEqual(candidate["mbid"], "release-1")
        self.assertEqual(candidate["discovery_type"], "new_release")
        self.assertEqual(candidate["artist_library_album_count"], 4)

    def test_excludes_releases_after_today_but_keeps_today_and_earlier(self):
        groups = [
            group("Tomorrow", "2026-10-23"),
            group("Later this year", "2026-12-01"),
            group("Later month only", "2026-11"),
            group("Today", "2026-10-22"),
            group("Earlier", "2026-10-01"),
        ]
        result = select_artist_release_candidates(
            groups, artist="Björk", artist_record={"album_count": 4}, owned=set(),
            cutoff_date="2024-10-16", current_year=2026, today="2026-10-22",
            music_key=music_key, is_album_candidate=is_album_candidate,
            exact_artist_credit_matches=exact_credit, is_various_artists=is_various_artists,
        )
        self.assertEqual({c["album"] for c in result.values()}, {"Today", "Earlier"})

    def test_rejects_non_album_bad_date_out_of_window_and_future_year(self):
        result = self.select([
            group("EP", "2025-01-01", primary="EP"),
            group("No date", ""),
            group("Too old", "2024-10-15"),
            group("Future", "2027-01-01"),
        ])
        self.assertEqual(result, {})

    def test_rejects_ineligible_release_and_similarly_named_artist(self):
        result = self.select([
            group("Greatest Hits", "2025-01-01"),
            group("Live Set", "2025-01-01"),
            group("Debut", "2025-01-01", credit=[{"artist": {"name": "Björk Tribute"}}]),
        ])
        self.assertEqual(result, {})

    def test_excludes_owned_and_various_artists_credit(self):
        owned_result = self.select(
            [group("Fossora", "2025-09-30")],
            owned={("bjork", "fossora")},
        )
        various_result = self.select(
            [group("Compilation", "2025-02-01", artist="Various Artists")],
            artist="Various Artists",
        )
        self.assertEqual(owned_result, {})
        self.assertEqual(various_result, {})

    def test_duplicate_identity_keeps_latest_release_date(self):
        result = self.select([
            group("New Record", "2025-01-01", mbid="older"),
            group("New Record", "2025-08-01", mbid="newer"),
        ])
        self.assertEqual(result[("bjork", "newrecord")]["mbid"], "newer")

    def test_library_scope_uses_full_album_threshold_and_excludes_various_artists(self):
        artists = [
            {"name": "Short Album Artist", "album_count": 9},
            {"name": "Björk", "album_count": 3},
            {"name": "Low Count", "album_count": 1},
            {"name": "Various Artists", "album_count": 50},
            {"name": "", "album_count": 100},
        ]
        albums = [
            {"artist": "Short Album Artist", "album": "EP", "song_count": 5},
            {"artist": "Björk", "album": "Full Album", "song_count": 6},
            {"artist": "Low Count", "album": "Long Album", "song_count": 12},
            {"artist": "Björk", "album": "Another Album", "song_count": 10},
            {"artist": "Various Artists", "album": "Compilation", "song_count": 20},
        ]
        owned, qualified = prepare_new_release_library_scope(
            artists, albums, music_key=music_key, is_various_artists=is_various_artists
        )
        self.assertEqual([item["name"] for item in qualified], ["Björk", "Low Count"])
        self.assertEqual(len(owned), 5)

    def test_library_scope_preserves_stable_order_for_equal_album_counts(self):
        artists = [
            {"name": "First", "album_count": 4},
            {"name": "Second", "album_count": 4},
            {"name": "Third", "album_count": 7},
        ]
        albums = [
            {"artist": name, "album": "Owned", "song_count": 6}
            for name in ("First", "Second", "Third")
        ]
        _, qualified = prepare_new_release_library_scope(
            artists, albums, music_key=music_key, is_various_artists=is_various_artists
        )
        self.assertEqual([item["name"] for item in qualified], ["Third", "First", "Second"])

    def test_library_scope_returns_owned_normalized_identities_even_without_qualified_artists(self):
        owned, qualified = prepare_new_release_library_scope(
            [{"name": "Unknown", "album_count": 1}],
            [{"artist": "Björk", "album": "Fossora", "song_count": 2}],
            music_key=music_key, is_various_artists=is_various_artists,
        )
        self.assertEqual(owned, {("bjork", "fossora")})
        self.assertEqual(qualified, [])




class NewReleaseProviderLookupTests(unittest.TestCase):
    def test_cache_hit_skips_network_and_delay(self):
        calls = []
        payload = [{"id": "cached"}]
        result, error = fetch_artist_release_groups(
            "key", "query", cache_get=lambda key, **kw: payload,
            cache_set=lambda *a: calls.append(("set", a)),
            http_get=lambda *a, **kw: calls.append(("http", kw)),
            sleep=lambda seconds: calls.append(("sleep", seconds)),
            headers={"User-Agent": "test"}, pause_before_request=True,
        )
        self.assertEqual(result, payload)
        self.assertIsNone(error)
        self.assertEqual(calls, [])

    def test_cache_miss_fetches_with_existing_request_contract_and_caches(self):
        calls = []
        response = type("Response", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"release-groups": [{"id": "fresh"}]},
        })()
        result, error = fetch_artist_release_groups(
            "key", "artist-query", cache_get=lambda key, **kw: None,
            cache_set=lambda key, value: calls.append(("set", key, value)),
            http_get=lambda url, **kw: (calls.append(("http", url, kw)) or response),
            sleep=lambda seconds: calls.append(("sleep", seconds)),
            headers={"User-Agent": "test"}, pause_before_request=True,
        )
        self.assertEqual(result, [{"id": "fresh"}])
        self.assertIsNone(error)
        self.assertEqual(calls[0], ("sleep", 1.1))
        self.assertEqual(calls[1][2]["params"], {"query": "artist-query", "fmt": "json", "limit": 100})
        self.assertEqual(calls[1][2]["timeout"], 20)
        self.assertEqual(calls[2], ("set", "key", [{"id": "fresh"}]))

    def test_malformed_payload_is_normalized_and_cached_as_empty(self):
        cached = []
        response = type("Response", (), {
            "raise_for_status": lambda self: None,
            "json": lambda self: {"release-groups": "wrong-shape"},
        })()
        result, error = fetch_artist_release_groups(
            "key", "query", cache_get=lambda *a, **kw: None,
            cache_set=lambda key, value: cached.append(value),
            http_get=lambda *a, **kw: response, sleep=lambda _: None,
            headers={}, pause_before_request=False,
        )
        self.assertEqual(result, [])
        self.assertIsNone(error)
        self.assertEqual(cached, [[]])

    def test_expected_provider_errors_return_type_without_leaking_message(self):
        result, error = fetch_artist_release_groups(
            "key", "query", cache_get=lambda *a, **kw: None,
            cache_set=lambda *a: self.fail("must not cache failures"),
            http_get=lambda *a, **kw: (_ for _ in ()).throw(ValueError("secret detail")),
            sleep=lambda _: None, headers={}, pause_before_request=False,
        )
        self.assertIsNone(result)
        self.assertEqual(error, "ValueError")


if __name__ == "__main__":
    unittest.main()


class NewReleaseGlobalMergeTests(unittest.TestCase):
    def test_newer_candidate_wins_and_inputs_are_not_mutated(self):
        old = {("bjork", "album"): {"first_release_date": "2025-01-01"}}
        incoming = {("bjork", "album"): {"first_release_date": "2025-09-01"}, ("radiohead", "album"): {"first_release_date": "2025-06-01"}}
        merged = merge_release_candidates(old, incoming)
        self.assertEqual(merged[("bjork", "album")]["first_release_date"], "2025-09-01")
        self.assertNotIn(("radiohead", "album"), old)
        self.assertEqual(old[("bjork", "album")]["first_release_date"], "2025-01-01")

    def test_existing_candidate_wins_equal_date_tie(self):
        old = {("artist", "album"): {"first_release_date": "2025-03-01", "winner": "old"}}
        incoming = {("artist", "album"): {"first_release_date": "2025-03-01", "winner": "new"}}
        self.assertEqual(merge_release_candidates(old, incoming)[("artist", "album")]["winner"], "old")

    def test_empty_and_missing_dates(self):
        self.assertEqual(merge_release_candidates({}, {}), {})
        old = {("artist", "album"): {"first_release_date": ""}}
        new = {("artist", "album"): {"first_release_date": "2024-01-01"}}
        self.assertEqual(merge_release_candidates(old, new)[("artist", "album")]["first_release_date"], "2024-01-01")


class NewReleaseResponseTests(unittest.TestCase):
    def test_response_sorts_newest_first_caps_items_and_preserves_contract(self):
        candidates = {
            ("a", "old"): {"artist": "Artist A", "album": "Old", "first_release_date": "2025-01-01"},
            ("b", "new"): {"artist": "Artist B", "album": "New", "first_release_date": "2026-06-01"},
            ("c", "tie-z"): {"artist": "Zed", "album": "Same", "first_release_date": "2026-06-01"},
            ("d", "tie-a"): {"artist": "Alpha", "album": "Same", "first_release_date": "2026-06-01"},
        }
        errors = [{"artist": str(i), "error": "HTTPError"} for i in range(25)]
        result = build_new_release_response(
            candidates,
            qualified_library_artists=140,
            artists_scanned=120,
            lookup_errors=errors,
            earliest_year=2024,
            cutoff_date="2024-10-16",
            generated_at=123.5,
        )
        self.assertEqual(
            [(item["artist"], item["album"]) for item in result["items"]],
            [("Zed", "Same"), ("Artist B", "New"), ("Alpha", "Same"), ("Artist A", "Old")],
        )
        self.assertEqual(result["generated_at"], 123.5)
        self.assertEqual(result["year_from"], 2024)
        self.assertEqual(result["date_from"], "2024-10-16")
        self.assertEqual(result["qualified_library_artists"], 140)
        self.assertEqual(result["artists_scanned"], 120)
        self.assertEqual(len(result["lookup_errors"]), 20)
        self.assertEqual(result["source"], "MusicBrainz release groups matched against the Navidrome library")
        self.assertEqual(len(result["limitations"]), 4)

    def test_response_caps_visible_items_at_200_without_mutating_candidates(self):
        candidates = {
            (str(i), str(i)): {"artist": f"Artist {i}", "album": f"Album {i}", "first_release_date": f"2025-{(i % 12) + 1:02d}-01"}
            for i in range(205)
        }
        before = dict(candidates)
        result = build_new_release_response(
            candidates,
            qualified_library_artists=205,
            artists_scanned=120,
            lookup_errors=[],
            earliest_year=2024,
            cutoff_date="2024-10-16",
            generated_at=1.0,
        )
        self.assertEqual(len(result["items"]), 200)
        self.assertEqual(candidates, before)


class NewReleaseLookupConstructionTests(unittest.TestCase):
    def test_builds_stable_cache_key_and_date_bounded_query(self):
        cache_key, query = build_new_release_lookup(
            "Björk", artist_key="bjork", earliest_year=2024, current_year=2026
        )
        self.assertEqual(cache_key, "mb:new-releases:v1:2024:bjork")
        self.assertEqual(
            query,
            'artist:"Björk" AND primarytype:album AND firstreleasedate:[2024 TO 2026]',
        )

    def test_escapes_quotes_and_backslashes_in_artist_name(self):
        cache_key, query = build_new_release_lookup(
            'The \\ "Band"',
            artist_key="theband",
            earliest_year=2025,
            current_year=2026,
        )
        self.assertEqual(cache_key, "mb:new-releases:v1:2025:theband")
        self.assertIn('artist:"The \\\\ \\"Band\\""', query)

    def test_same_normalized_artist_and_window_share_cache_key(self):
        first, _ = build_new_release_lookup(
            "Björk", artist_key="bjork", earliest_year=2024, current_year=2026
        )
        second, _ = build_new_release_lookup(
            "BJÖRK", artist_key="bjork", earliest_year=2024, current_year=2026
        )
        self.assertEqual(first, second)


class NewReleaseWindowPolicyTests(unittest.TestCase):
    def test_uses_exactly_730_days_and_returns_query_year_bounds(self):
        from datetime import date
        self.assertEqual(new_release_window(date(2026, 10, 16)), ("2024-10-16", 2024, 2026))

    def test_leap_day_boundary_is_calendar_correct(self):
        from datetime import date
        self.assertEqual(new_release_window(date(2024, 2, 29)), ("2022-03-01", 2022, 2024))
