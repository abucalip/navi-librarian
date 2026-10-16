import unittest

from discovery_new_releases import select_artist_release_candidates
from discovery_recommendations import is_album_candidate, is_various_artists, music_key


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
        result = self.select([
            group("Fossora", "2025-09-30"),
            group("Compilation", "2025-02-01", artist="Various Artists"),
        ], owned={("bjork", "fossora")})
        self.assertEqual(result, {})

    def test_duplicate_identity_keeps_latest_release_date(self):
        result = self.select([
            group("New Record", "2025-01-01", mbid="older"),
            group("New Record", "2025-08-01", mbid="newer"),
        ])
        self.assertEqual(result[("bjork", "newrecord")]["mbid"], "newer")


if __name__ == "__main__":
    unittest.main()
