"""Direct-import tests for the sonic proxy (Server V2 Phase 7): filtering, scores, graceful errors."""
import unittest

from intelligence.sonic import MAX_COUNT, similar_tracks, sonic_path
from intelligence.sonic.proxy import normalize_title


def song(i, title="Song", artist="A", mbid=None, **kw):
    return {"id": i, "title": title, "artist": artist, "artistId": f"ar-{artist}", "album": "LP", "albumId": "al",
            "musicBrainzId": mbid, **kw}


def match(entry, sim=0.9):
    return {"entry": entry, "similarity": sim}


class FakeNavidrome:
    def __init__(self, songs=(), matches=(), error=None):
        self.songs, self.matches, self.error, self.calls = {s["id"]: s for s in songs}, list(matches), error, []

    def __call__(self, method, **params):
        self.calls.append((method, params))
        if self.error and method in self.error:
            raise RuntimeError(self.error[method])
        if method == "getSong":
            if params["id"] not in self.songs:
                raise RuntimeError("Navidrome API error 70: data not found")
            return {"song": self.songs[params["id"]]}
        return {"sonicMatch": self.matches}


class SimilarTracks(unittest.TestCase):
    def test_keeps_order_and_marks_owned(self):
        nav = FakeNavidrome([song("s", "Seed")], [match(song("1", "One", "B"), 0.97), match(song("2", "Two", "C"), 0.93)])
        result = similar_tracks(nav, "s", count=2)
        self.assertEqual(result.status, "ok")
        self.assertEqual([t["navidrome_id"] for t in result.tracks], ["1", "2"])
        self.assertTrue(all(t["owned"] for t in result.tracks))
        self.assertEqual(result.tracks[0]["similarity"], 0.97)

    def test_drops_same_recording_edition_and_repeats(self):
        seed = song("s", "Seed Song (Remastered 2011)", "A", mbid="m1")
        matches = [match(song("e", "Seed Song - 2011 Remaster", "A")),
                   match(song("m", "Different Name", "Z", mbid="m1")),
                   match(song("k", "Seed Song", "Q"), 0.99),
                   match(song("x", "Other", "B")), match(song("y", "other!", "B"))]
        result = similar_tracks(FakeNavidrome([seed], matches), "s", count=10)
        self.assertEqual([t["navidrome_id"] for t in result.tracks], ["k", "x"])
        self.assertEqual(result.dropped, {"same_recording": 2, "repeat": 1, "artist_cap": 0})

    def test_asks_for_extra_and_trims_to_count(self):
        nav = FakeNavidrome([song("s")], [match(song(str(n), f"T{n}", f"X{n}")) for n in range(8)])
        result = similar_tracks(nav, "s", count=3)
        self.assertEqual(len(result.tracks), 3)
        self.assertEqual(nav.calls[1][1]["count"], 9)

    def test_caps_matches_by_the_seed_artist(self):
        own = [match(song(f"a{n}", f"Own{n}", "A")) for n in range(4)]
        other = [match(song(f"b{n}", f"Other{n}", "B")) for n in range(4)]
        result = similar_tracks(FakeNavidrome([song("s")], own + other), "s", count=6)
        self.assertEqual([t["navidrome_id"] for t in result.tracks], ["a0", "a1", "b0", "b1", "b2", "b3"])
        self.assertEqual(result.dropped["artist_cap"], 2)

    def test_cap_can_be_turned_off(self):
        own = [match(song(f"a{n}", f"Own{n}", "A")) for n in range(4)]
        result = similar_tracks(FakeNavidrome([song("s")], own), "s", count=4, max_same_artist=None)
        self.assertEqual(len(result.tracks), 4)

    def test_count_is_clamped(self):
        nav = FakeNavidrome([song("s")], [])
        similar_tracks(nav, "s", count=9999)
        self.assertEqual(nav.calls[1][1]["count"], MAX_COUNT)

    def test_unknown_song_is_not_found_without_a_sonic_call(self):
        nav = FakeNavidrome()
        self.assertEqual(similar_tracks(nav, "nope").status, "not_found")
        self.assertEqual([c[0] for c in nav.calls], ["getSong"])

    def test_sonic_404_and_plugin_failure_are_statuses(self):
        seed = song("s")
        r = similar_tracks(FakeNavidrome([seed], error={"getSonicSimilarTracks": "Navidrome API error 70: data not found"}), "s")
        self.assertEqual((r.status, r.tracks), ("not_found", []))
        r = similar_tracks(FakeNavidrome([seed], error={"getSonicSimilarTracks": "Navidrome API error 0: plugin call failed"}), "s")
        self.assertEqual(r.status, "unavailable")

    def test_unanalysed_song_is_empty_not_unavailable(self):
        err = "Navidrome API error 0: Internal Server Error: plugin call failed: AudioMuse-AI returned status 404"
        r = similar_tracks(FakeNavidrome([song("s")], error={"getSonicSimilarTracks": err}), "s")
        self.assertEqual((r.status, r.tracks, r.seed["navidrome_id"]), ("empty", [], "s"))

    def test_refused_login_is_not_hidden(self):
        nav = FakeNavidrome([song("s")], error={"getSong": "Navidrome API error 40: Wrong username or password"})
        with self.assertRaises(RuntimeError):
            similar_tracks(nav, "s")

    def test_no_matches_is_empty(self):
        self.assertEqual(similar_tracks(FakeNavidrome([song("s")], []), "s").status, "empty")


class SonicPath(unittest.TestCase):
    def test_minus_one_scores_become_none(self):
        nav = FakeNavidrome(matches=[match(song("a"), -1), match(song("b", "B", "B"), 0.9), match(song("c", "C", "C"), 0.8)])
        result = sonic_path(nav, "a", "c", count=3)
        self.assertEqual(result.status, "ok")
        self.assertIsNone(result.tracks[0]["similarity"])
        self.assertEqual(result.seed["navidrome_id"], "a")
        self.assertEqual(nav.calls[0], ("findSonicPath", {"startSongId": "a", "endSongId": "c", "count": 3}))

    def test_same_start_and_end_is_refused(self):
        with self.assertRaises(ValueError):
            sonic_path(FakeNavidrome(), "a", "a")

    def test_unknown_song_is_not_found(self):
        nav = FakeNavidrome(error={"findSonicPath": "Navidrome API error 70: data not found"})
        self.assertEqual(sonic_path(nav, "a", "b").status, "not_found")


class Titles(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(normalize_title("Hello, World! (Live) [2011 Remaster]"), "hello world")
        self.assertEqual(normalize_title("Track - Remastered"), "track")


if __name__ == "__main__":
    unittest.main()
