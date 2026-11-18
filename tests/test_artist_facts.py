"""Index theme I0: artist page plays, active years and owned-of-total album counts."""

import tempfile
import unittest
from pathlib import Path

from app.api.insights import STORE_FILE
from discovery.search.artist_facts import active_years, album_counts
from discovery.search.artist_page import artist_page
from discovery.search.artist_sections import network_sections
from discovery.search.index import STATE_FRESH, IndexView, build_owned_data
from discovery.search.providers import album_candidate, artist_candidate
from intelligence.knowledge.artist_years import read_life_span
from intelligence.store import open_store
from intelligence.store import repositories as repo
from tests.test_discovery_search_artist_sections import ALBUMS, FakeMusicBrainz, network


def view():
    data = build_owned_data(
        generation=1, built_at=0,
        artists=[{"id": "ar1", "name": "Radiohead", "album_count": 1}],
        albums=[{"id": "al1", "artist": "Radiohead", "artist_id": "ar1", "album": "OK Computer",
                 "year": 1997, "song_count": 1}],
        identities={"artist:ar1": {"mbid": "a-gid"}},
        songs=[{"id": "s1", "title": "Karma Police", "albumId": "al1", "artistId": "ar1", "playCount": 7}],
    )
    return IndexView(STATE_FRESH, data, None)


class ActiveYearsTests(unittest.TestCase):
    def test_years_from_a_span(self):
        self.assertEqual(active_years({"begin": "1967-03", "end": "2007", "ended": True}),
                         {"begin": 1967, "end": 2007, "ended": True})
        self.assertEqual(active_years({"begin": "1985", "end": None, "ended": False}),
                         {"begin": 1985, "end": None, "ended": False})

    def test_no_begin_year_gives_none(self):
        self.assertIsNone(active_years(None))
        self.assertIsNone(active_years({"begin": None, "end": "2000", "ended": True}))
        self.assertIsNone(active_years({"begin": "?", "end": None, "ended": False}))


class AlbumCountsTests(unittest.TestCase):
    def test_counts_provider_listed_albums_only(self):
        catalog = [
            {"sources": ["musicbrainz"], "owned": True},
            {"sources": ["musicbrainz", "lastfm"], "owned": False},
            {"sources": ["navidrome"], "owned": True},  # a live album the providers do not list
        ]
        self.assertEqual(album_counts(catalog), (1, 2))

    def test_none_when_no_provider_listed_any(self):
        self.assertIsNone(album_counts([]))
        self.assertIsNone(album_counts([{"sources": ["navidrome"], "owned": True}]))

    def test_albums_section_carries_the_counts(self):
        net = network(FakeMusicBrainz(artists=[artist_candidate("musicbrainz", "Radiohead", "a-gid")], albums=ALBUMS))
        albums = network_sections(net, "Radiohead", None, view().data, known_mbid="a-gid")["albums"]
        self.assertEqual((albums["owned_count"], albums["album_count"]), (1, 3))

    def test_albums_section_omits_counts_without_a_provider_list(self):
        albums = network_sections(network(FakeMusicBrainz()), "Radiohead", None, view().data)["albums"]
        self.assertNotIn("album_count", albums)


class ArtistSectionTests(unittest.TestCase):
    def test_plays_and_years_on_the_artist_section(self):
        page = artist_page(view(), "radiohead", None, life_span=lambda m: {"begin": "1985", "end": None, "ended": False})
        artist = page.sections["artist"]["artist"]
        self.assertEqual(artist["play_count"], 7)
        self.assertEqual(artist["active_years"], {"begin": 1985, "end": None, "ended": False})

    def test_years_are_null_without_a_reader_or_when_it_fails(self):
        self.assertIsNone(artist_page(view(), "radiohead", None).sections["artist"]["artist"]["active_years"])

        def boom(mbid):
            raise RuntimeError("store")

        self.assertIsNone(artist_page(view(), "radiohead", None, life_span=boom).sections["artist"]["artist"]["active_years"])


class ReadLifeSpanTests(unittest.TestCase):
    def test_reads_a_stored_span_and_tolerates_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / STORE_FILE
            db = open_store(path)
            artist = repo.upsert_entity(db, "artist", "Alpha", mbid="a-gid")[0]
            repo.upsert_entity(db, "artist", "Beta", mbid="b-gid")
            with db:
                db.execute("INSERT INTO artist_life_span (entity_id, begin_date, end_date, ended) VALUES (?, '1967', '2007', 1)", (artist,))
            db.close()
            self.assertEqual(read_life_span(path, "A-GID"), {"begin": "1967", "end": "2007", "ended": True})
            self.assertIsNone(read_life_span(path, "b-gid"))
            self.assertIsNone(read_life_span(path, "unknown"))
            self.assertIsNone(read_life_span(Path(tmp) / "missing" / "x.sqlite3", "a-gid"))


if __name__ == "__main__":
    unittest.main()
