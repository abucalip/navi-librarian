"""Synthetic tests: a fresh save seeds supplementary tag-query selection."""
import time
import unittest

from discovery_candidate_gathering import RecommendationProviders, gather_recommendation_candidates
from recommendation_feedback import POSITIVE_EXPIRY_SECONDS, saved_artist_seed_weights

PROFILE_MBID = "p-jazz"
PROFILE_GENRES = ["jazz", "modal jazz", "hard bop", "cool jazz", "bebop"]
CANDIDATE_GENRES = {"c-1": ["dub"], "c-2": ["folk", "ambient"], "c-3": ["dub"]}


def _music_key(value):
    return "".join(str(value).casefold().split())


class _Response:
    def __init__(self, payload, status_code=200):
        self._payload, self.status_code = payload, status_code

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _Client:
    def __init__(self, log):
        self._log = log

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, params=None, headers=None):
        if "/artist/" in url:
            self._log["artist"].append(url.rsplit("/", 1)[1])
            return _Response({"genres": []})
        if "/release-group/" in url:
            self._log["queries"].append(params["query"])
            return _Response({"release-groups": []})
        return _Response({}, status_code=404)


def _save_row(artist, *, age_days, scope="album", status="for_me", metadata=None):
    return {
        "metadata": metadata or {},
        "scope": scope, "artist_key": _music_key(artist), "album_key": "x",
        "status": status, "created_at": time.time() - age_days * 86400,
        "updated_at": time.time(),
    }


def _run(feedback, *, many_artists=False):
    now = int(time.time())
    listens = [{
        "listened_at": now - i * 3600,
        "track_metadata": {"artist_name": "Profile Jazz", "additional_info": {"artist_mbid": PROFILE_MBID}},
    } for i in range(12)]
    cache = {f"mb:artist-genres:{PROFILE_MBID}": list(PROFILE_GENRES)}
    if many_artists:
        # 16 profile artists with fewer listens each, so the lowest-weighted one falls
        # outside the 15 whose genres the profile pass reads. Only that one has cached
        # genres, so the unseeded plan has no profile queries and a free quota.
        cache = {}
        listens = [{
            "listened_at": now - j * 60,
            "track_metadata": {"artist_name": f"Art {n}", "additional_info": {"artist_mbid": f"a-{n}"}},
        } for n in range(16) for j in range(1 + (16 - n))]
        cache["mb:artist-genres:a-15"] = ["shoegaze"]
    for index, (artist_id, genres) in enumerate(CANDIDATE_GENRES.items(), start=1):
        cache[f"mb:artist-genres:{artist_id}"] = list(genres)
        cache[f"mb:recording:rec-{index}"] = {
            "title": f"Track {index}",
            "artist-credit": [{"name": f"Cand {index}", "artist": {"id": artist_id}}],
            "releases": [{"release-group": {
                "id": f"rg-{index}", "title": f"Album {index}",
                "primary-type": "Album", "secondary-types": [],
            }}],
        }
    recordings = [{"recording_mbid": f"rec-{i}", "score": 300 - i} for i in range(1, 4)]
    log = {"queries": [], "artist": []}
    providers = RecommendationProviders(
        listenbrainz_recent=lambda days: listens,
        listenbrainz_username=lambda: "fixture-user",
        music_key=_music_key,
        metadata_cache_get=lambda key, **kw: cache.get(key),
        metadata_cache_set=lambda key, value, *a, **kw: cache.__setitem__(key, value),
        is_album_candidate=lambda candidate: True,
        api_call=lambda *a, **kw: {"albumList2": {"album": []}},
        items=lambda root: list(root or []),
        http_get=lambda url, params=None, **kw: _Response({"payload": {
            "mbids": recordings if params["offset"] == 0 else [],
        }}),
        http_client=lambda *a, **kw: _Client(log),
        sleep=lambda _s: None,
        feedback_rows=feedback if callable(feedback) or feedback is None else (lambda: feedback),
    )
    result = gather_recommendation_candidates(providers, shortlist_target=10)
    assert not isinstance(result, str), result
    return log


class SaveTagSeedTests(unittest.TestCase):
    def test_fresh_save_plans_a_tag_from_the_saved_artists_genres(self):
        # The first six queries are the profile quota; without a save the saved
        # artist's tags only reach the exploration quota or the replenishment pass.
        ambient = "primarytype:album AND tag:ambient"
        self.assertNotIn(ambient, _run([])["queries"][:6])  # guard: not vacuous

        log = _run([_save_row("Cand 2", age_days=1)])

        self.assertIn(ambient, log["queries"][:6])

    def test_save_of_unknown_artist_seeds_from_stored_genres(self):
        tag = "primarytype:album AND tag:shoegaze"
        unseeded = _run([_save_row("Never Heard", age_days=1)])
        self.assertNotIn(tag, unseeded["queries"])  # guard: no metadata, no seed

        seeded = _run([_save_row("Never Heard", age_days=1, metadata={"genres": ["shoegaze"]})])
        self.assertIn(tag, seeded["queries"][:6])
        self.assertEqual(len(seeded["artist"]), len(unseeded["artist"]))
        self.assertLessEqual(len(seeded["queries"]), len(unseeded["queries"]))

    def test_seed_for_artist_outside_top_15_profile_reads_adds_no_queries(self):
        # Review P2: the cap must compare against the plan made before seed cache
        # entries were added, not one rebuilt from the seeded profile-tag map.
        base = _run([], many_artists=True)
        seeded = _run([_save_row("Art 15", age_days=1)], many_artists=True)

        self.assertNotIn("primarytype:album AND tag:shoegaze", base["queries"])  # guard
        self.assertLessEqual(len(seeded["queries"]), len(base["queries"]))
        self.assertEqual(len(seeded["artist"]), len(base["artist"]))

    def test_expired_save_with_stored_genres_plans_nothing_extra(self):
        old = _save_row("Never Heard", age_days=POSITIVE_EXPIRY_SECONDS / 86400 + 1,
                        metadata={"genres": ["shoegaze"]})
        self.assertEqual(_run([old])["queries"], _run([])["queries"])

    def test_expired_save_plan_matches_no_save(self):
        expired = _run([_save_row("Cand 2", age_days=POSITIVE_EXPIRY_SECONDS / 86400 + 1)])
        self.assertEqual(expired["queries"], _run([])["queries"])
        self.assertEqual(expired["queries"], _run(None)["queries"])

    def test_seed_adds_no_queries_or_lookups(self):
        base, seeded = _run([]), _run([_save_row("Cand 2", age_days=1)])

        self.assertLessEqual(len(seeded["queries"]), len(base["queries"]))
        self.assertEqual(len(seeded["artist"]), len(base["artist"]))

    def test_dismissals_and_unknown_artists_do_not_seed(self):
        base = _run([])["queries"]
        rows = [
            _save_row("Cand 2", age_days=1, scope="artist", status="not_for_me_artist"),
            _save_row("Cand 2", age_days=1, status="not_for_me"),
            _save_row("Nobody Known", age_days=1),
        ]
        self.assertEqual(_run(rows)["queries"], base)

    def test_failing_feedback_provider_falls_back_to_unseeded(self):
        def boom():
            raise RuntimeError("store down")

        self.assertEqual(_run(boom)["queries"], _run([])["queries"])
        malformed = [{"scope": "album", "status": "for_me", "artist_key": "cand2", "created_at": "bad"}]
        self.assertEqual(_run(malformed)["queries"], _run([])["queries"])

    def test_seed_weight_decays_and_expires(self):
        now = time.time()
        fresh = saved_artist_seed_weights([_save_row("A", age_days=1)], now=now)
        old = saved_artist_seed_weights([_save_row("A", age_days=31)], now=now)
        gone = saved_artist_seed_weights([_save_row("A", age_days=91)], now=now)
        self.assertAlmostEqual(old["a"], fresh["a"] / 2, places=2)
        self.assertEqual(gone, {})


if __name__ == "__main__":
    unittest.main()
