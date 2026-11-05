import unittest

from intelligence.health import CHECKS, NOT_CHECKED, build_report
from intelligence.ingest.navidrome import normalize_album

MB = "11111111-1111-1111-1111-111111111111"


def album(aid="al-1", **over):
    base = {
        "id": aid, "name": "Rumours", "artist": "Fleetwood Mac", "artistId": "ar-1",
        "artists": [{"id": "ar-1", "musicBrainzId": MB}], "musicBrainzId": MB,
        "songCount": 2, "genres": [{"name": "Rock"}],
        "song": [
            {"id": f"{aid}-1", "track": 1, "discNumber": 1, "year": 1977, "musicBrainzId": MB,
             "replayGain": {"trackGain": -6.0}},
            {"id": f"{aid}-2", "track": 2, "discNumber": 1, "year": 1977, "musicBrainzId": MB,
             "replayGain": {"trackGain": -7.0}},
        ],
    }
    base.update(over)
    return normalize_album(base)


def checks(*albums):
    return [f.check for f in build_report(albums).findings]


class HealthReportTests(unittest.TestCase):
    def test_clean_album_has_no_findings(self):
        report = build_report([album()])
        self.assertEqual(report.findings, ())
        self.assertEqual(report.albums_checked, 1)
        self.assertEqual(report.not_checked, NOT_CHECKED)
        self.assertEqual(set(report.counts), set(CHECKS))

    def test_missing_ids_and_genre(self):
        a = album(musicBrainzId=None, artists=[], genres=[])
        self.assertEqual(checks(a), ["missing_album_mbid", "missing_artist_mbid", "missing_genre"])

    def test_track_genre_satisfies_genre_check(self):
        a = album(genres=[], song=[{"id": "s", "track": 1, "genre": "Rock", "musicBrainzId": MB, "replayGain": {"trackGain": 1}}], songCount=1)
        self.assertNotIn("missing_genre", checks(a))

    def test_missing_track_mbid_and_replaygain_list_tracks(self):
        a = album(song=[{"id": "s1", "track": 1}, {"id": "s2", "track": 2, "musicBrainzId": MB, "replayGain": {"trackGain": 1}}])
        found = {f.check: f for f in build_report([a]).findings}
        self.assertEqual(found["missing_track_mbid"].detail["track_ids"], ["s1"])
        self.assertEqual(found["replaygain_missing"].detail["track_ids"], ["s1"])

    def test_track_count_mismatch_only_when_both_known(self):
        self.assertIn("track_count_mismatch", checks(album(songCount=5)))
        self.assertNotIn("track_count_mismatch", checks(album(songCount=None)))

    def test_numbering_gap_duplicate_and_unnumbered(self):
        a = album(songCount=4, song=[
            {"id": "a", "track": 1, "musicBrainzId": MB, "replayGain": {"trackGain": 1}},
            {"id": "b", "track": 1, "musicBrainzId": MB, "replayGain": {"trackGain": 1}},
            {"id": "c", "track": 4, "musicBrainzId": MB, "replayGain": {"trackGain": 1}},
            {"id": "d", "musicBrainzId": MB, "replayGain": {"trackGain": 1}},
        ])
        finding = next(f for f in build_report([a]).findings if f.check == "track_number_problem")
        self.assertEqual(finding.detail["discs"]["1"], {"unnumbered": 1, "duplicates": [1], "missing": [2, 3]})

    def test_disc_gap(self):
        a = album(songCount=2, song=[
            {"id": "a", "track": 1, "discNumber": 1, "musicBrainzId": MB, "replayGain": {"trackGain": 1}},
            {"id": "b", "track": 1, "discNumber": 3, "musicBrainzId": MB, "replayGain": {"trackGain": 1}},
        ])
        finding = next(f for f in build_report([a]).findings if f.check == "disc_gap")
        self.assertEqual(finding.detail["missing"], [2])

    def test_mixed_years_skips_compilations(self):
        songs = [
            {"id": "a", "track": 1, "year": 1977, "musicBrainzId": MB, "replayGain": {"trackGain": 1}},
            {"id": "b", "track": 2, "year": 2004, "musicBrainzId": MB, "replayGain": {"trackGain": 1}},
        ]
        self.assertIn("mixed_years", checks(album(song=songs)))
        self.assertNotIn("mixed_years", checks(album(song=songs, isCompilation=True)))

    def test_inconsistent_album_artist_spelling(self):
        report = build_report([album("a1", artist="The Beatles"), album("a2", artist="Beatles"), album("a3", artist="Beatles")])
        finding = next(f for f in report.findings if f.check == "inconsistent_album_artist")
        self.assertEqual(finding.album_ids, ("a1", "a2", "a3"))
        self.assertEqual(set(finding.detail["spellings"]), {"The Beatles", "Beatles"})
        self.assertEqual(checks(album("a1"), album("a2")), [])

    def test_deterministic_and_dedupes(self):
        albums = [album("b", musicBrainzId=None), album("a", musicBrainzId=None), album("a", musicBrainzId=None)]
        first = build_report(albums)
        self.assertEqual(first.albums_checked, 2)
        self.assertEqual(first.as_dict(), build_report(list(reversed(albums))).as_dict())
        self.assertEqual([f.album_ids for f in first.findings], [("a",), ("b",)])


if __name__ == "__main__":
    unittest.main()
