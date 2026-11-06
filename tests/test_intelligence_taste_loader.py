import unittest

from intelligence.store import repositories as repo
from intelligence.store.db import open_store
from intelligence.taste import ProfileConfig, build_profiles
from intelligence.taste.loader import load_listens

ART, REC, REL, LAB, AREA, GUEST = "a-1", "r-1", "rel-1", "l-1", "ar-1", "g-1"


def raw(ts, recording=REC, artists=(ART,)):
    return {"listened_at": ts, "track_metadata": {"mbid_mapping": {
        "recording_mbid": recording, "artist_mbids": list(artists)}}}


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.db = open_store(":memory:")
        db = self.db
        artist, _ = repo.upsert_entity(db, "artist", "Band", mbid=ART)
        guest, _ = repo.upsert_entity(db, "person", "Guest", mbid=GUEST)
        area, _ = repo.upsert_entity(db, "area", "Sweden", mbid=AREA)
        rec, _ = repo.upsert_entity(db, "recording", "Song", mbid=REC)
        rel, _ = repo.upsert_entity(db, "release", "Album", mbid=REL)
        lab, _ = repo.upsert_entity(db, "label", "Indie Co", mbid=LAB)
        kw = dict(evidence_class="source_explicit", match_quality="exact_mbid", source="test")
        repo.add_edge(db, artist, area, "area", **kw)
        repo.add_edge(db, rec, rel, "appears_on", **kw)
        repo.add_edge(db, rel, lab, "label", **kw)
        repo.add_edge(db, rec, guest, "performance", **kw)
        repo.add_edge(db, rec, artist, "performance", **kw)
        with db:
            db.execute("INSERT INTO release_facts (entity_id, date) VALUES (?, ?)", (rel, "1974-05-01"))

    def test_resolves_every_dimension_and_leaves_the_listened_artist_out_of_collaborators(self):
        result = load_listens(self.db, [raw(1000.0)], genres_by_recording={REC: ["prog", "prog", ""]})
        attrs = result.listens[0].attrs
        self.assertEqual(attrs["area"], ("Sweden",))
        self.assertEqual(attrs["era"], ("1970s",))
        self.assertEqual(attrs["label"], ("Indie Co",))
        self.assertEqual(attrs["collaborator"], ("Guest",))
        self.assertEqual(attrs["genre"], ("prog",))
        self.assertEqual(result.attributed["label"], 1)

    def test_unknown_recording_and_bad_timestamps_are_counted_not_guessed(self):
        result = load_listens(self.db, [raw(1000.0, recording="nope", artists=()), raw(0), {"listened_at": "x"}])
        self.assertEqual((result.total, result.unusable, result.unmatched), (3, 2, 1))
        self.assertEqual(result.listens[0].attrs, {})
        self.assertEqual(result.attributed["area"], 0)

    def test_additional_info_ids_are_used_when_there_is_no_mapping(self):
        item = {"listened_at": 5, "track_metadata": {"additional_info": {"artist_mbids": [ART]}}}
        self.assertEqual(load_listens(self.db, [item]).listens[0].attrs, {"area": ("Sweden",)})

    def test_output_feeds_build_profiles_and_missing_genre_reads_low_sample(self):
        result = load_listens(self.db, [raw(1000.0 + i) for i in range(5)])
        p = build_profiles(result.listens, ProfileConfig(now=2000.0, min_listens=3, min_attributed=3))
        self.assertTrue(p.windows["all_time"].dimension_low_sample["genre"])
        self.assertFalse(p.windows["all_time"].dimension_low_sample["area"])


if __name__ == "__main__":
    unittest.main()
