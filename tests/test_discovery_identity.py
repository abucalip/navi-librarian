"""Background identity job: what is resolved, stored once, and skipped on later runs (contract section 12.9)."""

import threading
import time
import unittest

from discovery.identity import IdentityJob, identity_prefix, load_identities, resolve_identities
from discovery.search.index import build_owned_data
from discovery.search.providers import ProviderError


class FakeMusicBrainz:
    def __init__(self, artist_map=None, release_map=None, album_map=None, fail_artists=False, fail_albums=False):
        self.artist_map = artist_map or {}
        self.release_map = release_map or {}
        self.album_map = album_map or {}
        self.fail_artists = fail_artists
        self.fail_albums = fail_albums
        self.artist_calls = []
        self.release_calls = []
        self.album_calls = []

    def artist_identities(self, names, *, remaining, cancelled):
        self.artist_calls.append(list(names))
        if self.fail_artists:
            raise ProviderError("failed")
        return {k: v for k, v in self.artist_map.items() if k in {n.casefold() for n in names}}

    def release_groups_for_releases(self, ids, *, remaining, cancelled):
        self.release_calls.append(list(ids))
        return {i: self.release_map[i] for i in ids if i in self.release_map}

    def album_identities(self, albums, *, remaining, cancelled):
        self.album_calls.append(list(albums))
        if self.fail_albums:
            raise ProviderError("failed")
        return dict(self.album_map)


class Store:
    def __init__(self):
        self.data = {}

    def read_prefix(self, prefix):
        return {k: v for k, v in self.data.items() if k.startswith(prefix)}

    def write_many(self, lists):
        self.data.update(lists)


def library():
    return build_owned_data(
        generation=1, built_at=0,
        artists=[
            {"id": "ar1", "name": "Ash", "album_count": 1},
            {"id": "ar2", "name": "Radiohead", "album_count": 1},
            {"id": "ar3", "name": "Solo Nobody", "album_count": 1},
            {"id": "ar4", "name": "Twin", "album_count": 1},
            {"id": "ar5", "name": "Twin", "album_count": 1},
        ],
        albums=[
            {"id": "al1", "artist": "Radiohead", "artist_id": "ar2", "album": "OK Computer", "year": 1997,
             "song_count": 12, "release_mbid": "11111111-1111-1111-1111-111111111111"},
            {"id": "al2", "artist": "Radiohead", "artist_id": "ar2", "album": "Pablo Honey", "year": 1993,
             "song_count": 12, "release_mbid": None},
            {"id": "al3", "artist": "Various Artists", "artist_id": "ar9", "album": "Now 1", "year": 1995,
             "song_count": 40, "release_mbid": None},
        ],
        songs=[],
    )


def run(data, store, mb, tags=None, navidrome_fails=()):
    tags = tags or {}

    def navidrome_mbid(artist_id):
        if artist_id in navidrome_fails:
            raise RuntimeError("navidrome down")
        return tags.get(artist_id)

    return resolve_identities(
        data,
        navidrome_mbid=navidrome_mbid,
        musicbrainz=mb,
        read_prefix=store.read_prefix,
        write_many=store.write_many,
        remaining=lambda: 60.0,
        cancelled=threading.Event(),
    )


class ResolveIdentitiesTests(unittest.TestCase):
    def test_tagged_artists_use_navidrome_and_untagged_use_one_name_batch(self):
        store, mb = Store(), FakeMusicBrainz(artist_map={"radiohead": "mb-rh"})
        counts = run(library(), store, mb, tags={"ar1": "mb-ash"})
        self.assertEqual(store.data[f"{identity_prefix(1)}artist:ar1"]["mbid"], "mb-ash")
        self.assertEqual(store.data[f"{identity_prefix(1)}artist:ar1"]["source"], "navidrome")
        self.assertEqual(store.data[f"{identity_prefix(1)}artist:ar2"]["mbid"], "mb-rh")
        self.assertEqual(len(mb.artist_calls), 1)
        self.assertNotIn("Ash", mb.artist_calls[0])  # Ash was tagged, so it was not looked up by name
        self.assertGreater(counts["artists"], 0)

    def test_a_name_with_no_exact_match_is_stored_unresolved_so_it_is_not_asked_again(self):
        store, mb = Store(), FakeMusicBrainz(artist_map={})
        run(library(), store, mb, tags={"ar1": "x", "ar2": "y"})
        self.assertEqual(store.data[f"{identity_prefix(1)}artist:ar3"]["source"], "unresolved")
        second = FakeMusicBrainz()
        run(library(), store, second, tags={"ar1": "x", "ar2": "y"})
        self.assertEqual(second.artist_calls, [])

    def test_homonyms_are_not_guessed_and_make_no_name_lookup(self):
        store, mb = Store(), FakeMusicBrainz(artist_map={"twin": "mb-twin"})
        run(library(), store, mb, tags={"ar1": "a", "ar2": "b"})
        self.assertEqual(store.data[f"{identity_prefix(1)}artist:ar4"]["source"], "unresolved")
        self.assertEqual(store.data[f"{identity_prefix(1)}artist:ar5"]["source"], "unresolved")
        self.assertFalse(any("Twin" in call for call in mb.artist_calls))

    def test_a_failed_navidrome_read_writes_nothing_so_the_next_run_retries(self):
        store, mb = Store(), FakeMusicBrainz()
        run(library(), store, mb, navidrome_fails=("ar1",))
        self.assertNotIn(f"{identity_prefix(1)}artist:ar1", store.data)

    def test_a_failed_name_batch_writes_nothing_for_that_chunk(self):
        store, mb = Store(), FakeMusicBrainz(fail_artists=True)
        run(library(), store, mb, tags={"ar1": "a", "ar2": "b"})
        self.assertNotIn(f"{identity_prefix(1)}artist:ar3", store.data)

    def test_a_transport_error_in_one_batch_skips_only_that_batch(self):
        class FlakyMusicBrainz(FakeMusicBrainz):
            def artist_identities(self, names, *, remaining, cancelled):
                self.artist_calls.append(list(names))
                if len(self.artist_calls) == 1:
                    raise TimeoutError("read timed out")  # what a timed-out request raises
                return {"radiohead": "mb-rh"}

        store, mb = Store(), FlakyMusicBrainz()
        counts = run(library(), store, mb, tags={"ar1": "a", "ar2": "b"})
        # The timeout leaves no record behind; the pass still reaches the album step.
        self.assertNotIn(f"{identity_prefix(1)}artist:ar3", store.data)
        self.assertGreater(len(mb.album_calls), 0)
        self.assertIsInstance(counts, dict)

    def test_albums_use_the_release_mbid_then_the_title_lookup_and_compilations_are_skipped(self):
        store = Store()
        mb = FakeMusicBrainz(
            release_map={"11111111-1111-1111-1111-111111111111": "rg-ok"},
            album_map={("radiohead", "pablo honey"): "rg-ph"},
        )
        run(library(), store, mb, tags={"ar1": "a", "ar2": "b"})
        self.assertEqual(store.data[f"{identity_prefix(1)}album:al1"]["release_group_mbid"], "rg-ok")
        self.assertEqual(store.data[f"{identity_prefix(1)}album:al2"]["release_group_mbid"], "rg-ph")
        self.assertEqual(store.data[f"{identity_prefix(1)}album:al3"]["source"], "unresolved")
        self.assertEqual(mb.album_calls and [a[0] for a in mb.album_calls[0]], ["Radiohead"])

    def test_second_run_makes_no_calls_once_everything_is_stored(self):
        store = Store()
        run(library(), store, FakeMusicBrainz(artist_map={"radiohead": "mb-rh"},
                                              album_map={("radiohead", "pablo honey"): "rg-ph"}),
            tags={"ar1": "a", "ar2": "b"})
        again = FakeMusicBrainz()
        counts = run(library(), store, again, tags={"ar1": "a", "ar2": "b"})
        self.assertEqual(again.artist_calls + again.release_calls + again.album_calls, [])
        self.assertEqual(counts, {"artists": 0, "albums": 0, "unresolved": 0})

    def test_load_identities_returns_the_shape_build_owned_data_expects(self):
        stored = {
            f"{identity_prefix(1)}artist:ar1": {"mbid": "mb-ash", "source": "navidrome"},
            f"{identity_prefix(1)}album:al1": {"release_group_mbid": None, "source": "unresolved"},
        }
        loaded = load_identities(lambda prefix: {k: v for k, v in stored.items() if k.startswith(prefix)}, 1)
        self.assertEqual(loaded, {"artist:ar1": {"mbid": "mb-ash"}, "album:al1": {"release_group_mbid": None}})


class IdentityJobTests(unittest.TestCase):
    def test_a_pass_requested_while_one_runs_is_queued_and_runs_after_it(self):
        job = IdentityJob()
        release = threading.Event()
        started = []

        def slow():
            started.append(1)
            release.wait(2)
            return {"artists": 0, "albums": 0}

        self.assertTrue(job.start(slow, on_changed=lambda: None))
        time.sleep(0.05)
        self.assertFalse(job.start(slow, on_changed=lambda: None))
        release.set()
        time.sleep(0.2)
        self.assertEqual(len(started), 2)

    def test_on_changed_runs_only_when_something_was_stored(self):
        changed = []
        job = IdentityJob()
        job.start(lambda: {"artists": 0, "albums": 0}, on_changed=lambda: changed.append("no"))
        time.sleep(0.1)
        job.start(lambda: {"artists": 0, "albums": 2}, on_changed=lambda: changed.append("yes"))
        time.sleep(0.1)
        self.assertEqual(changed, ["yes"])

    def test_a_failing_pass_changes_nothing_and_releases_the_job(self):
        job = IdentityJob()

        def broken():
            raise RuntimeError("boom")

        job.start(broken, on_changed=lambda: None)
        time.sleep(0.1)
        self.assertTrue(job.start(lambda: {"artists": 0, "albums": 0}, on_changed=lambda: None))


class StoredMbidsInIndexTests(unittest.TestCase):
    def test_stored_identities_reach_the_index_entries(self):
        data = build_owned_data(
            generation=1, built_at=0,
            artists=[{"id": "ar1", "name": "Ash", "album_count": 1}],
            albums=[{"id": "al1", "artist": "Ash", "artist_id": "ar1", "album": "1977", "year": 1977, "song_count": 1}],
            songs=[],
            identities={"artist:ar1": {"mbid": "mb-ash"}, "album:al1": {"release_group_mbid": "rg-1977"}},
        )
        self.assertEqual(data.artists[0]["mbid"], "mb-ash")
        self.assertEqual(data.albums[0]["release_group_mbid"], "rg-1977")


class GenerationRaceTests(unittest.TestCase):
    def test_a_late_identity_callback_cannot_roll_the_index_back_to_an_old_generation(self):
        from discovery.search.index import STATE_FRESH, OwnedIndex

        index = OwnedIndex(
            load_library=lambda: ([{"id": "ar1", "name": "Ash", "album_count": 1}], []),
            load_songs=lambda: [],
            background=False,
        )
        index.ensure(1)
        release = threading.Event()
        job = IdentityJob()
        # The pass started under generation 1 and finishes after the Navidrome generation has changed.
        job.start(
            lambda: (release.wait(2), {"artists": 1, "albums": 0})[1],
            on_changed=lambda: index.refresh(1),
        )
        time.sleep(0.05)
        index.ensure(2)
        self.assertEqual(index.view().data.generation, 2)

        release.set()
        time.sleep(0.2)
        view = index.view()
        self.assertEqual(view.data.generation, 2)
        self.assertEqual(view.state, STATE_FRESH)

    def test_identities_stored_while_a_build_is_in_flight_reach_the_next_published_index(self):
        from discovery.search.index import OwnedIndex, STATE_FRESH

        store = {}
        read_done = threading.Event()
        release_build = threading.Event()
        first_read = []

        def identities(generation):
            # The first build reads the store, then waits. Later builds never wait.
            snapshot = dict(store)
            if not first_read:
                first_read.append(1)
                read_done.set()
                release_build.wait(5)
            return {k: v for k, v in snapshot.items()}

        index = OwnedIndex(
            load_library=lambda: ([{"id": "ar1", "name": "Ash", "album_count": 1}], []),
            load_songs=lambda: [],
            load_identities=lambda generation: load_identities(
                lambda prefix: {k: v for k, v in identities(generation).items() if k.startswith(prefix)},
                generation,
            ),
        )
        index.ensure(1)
        self.assertTrue(read_done.wait(5))
        # An identity pass stores an MBID while that build is in flight, then asks for a refresh.
        store[f"{identity_prefix(1)}artist:ar1"] = {"mbid": "mb-ash", "source": "navidrome"}
        index.refresh(1)
        release_build.set()

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            view = index.view()
            if view.state == STATE_FRESH and view.data and view.data.artists[0]["mbid"] == "mb-ash":
                break
            time.sleep(0.02)
        view = index.view()
        self.assertEqual(view.state, STATE_FRESH)
        self.assertEqual(view.data.artists[0]["mbid"], "mb-ash")

    def test_refresh_for_the_current_generation_rebuilds_it(self):
        from discovery.search.index import OwnedIndex

        builds = []
        index = OwnedIndex(
            load_library=lambda: (builds.append(1) or [{"id": "ar1", "name": "Ash", "album_count": 1}], []),
            load_songs=lambda: [],
            background=False,
        )
        index.ensure(1)
        index.refresh(1)
        self.assertEqual(len(builds), 2)


if __name__ == "__main__":
    unittest.main()
