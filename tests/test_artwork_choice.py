"""Edition picker and grid fallback (docs/artwork.md, slice 4)."""
import struct
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.api.artwork as artwork_routes
import app.api.owned_artwork as owned
from app.api.dependencies import get_librarian
from integrations.navidrome import client as navidrome_client
from intelligence.artwork import ArtworkService, ArtworkStore, cover
from tests.test_intelligence_artwork_cache import JPEG, R1, RG, FakeFetchers


def jpeg(side: int) -> bytes:
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, side, side, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + sof + b"\xff\xd9"


class FakeLibrarian:
    def __init__(self, data_dir):
        self.DATA_DIR = Path(data_dir)

    def _navidrome_config(self):
        return "http://navidrome:4533", "owner", "stub-secret"


class ChoiceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.fetch = FakeFetchers()
        self.service = ArtworkService(ArtworkStore(Path(tmp.name)), self.fetch)
        self.addCleanup(self.service._pool.shutdown)
        api = FastAPI()
        api.include_router(artwork_routes.router)
        api.include_router(owned.router)
        api.dependency_overrides[get_librarian] = lambda: FakeLibrarian(tmp.name)
        api.dependency_overrides[artwork_routes.get_service] = lambda: self.service
        self.client = TestClient(api)

    def pick(self, image_id=10, album="al-1"):
        return self.client.put(f"/api/artwork/choice/{album}", json={"rgid": RG, "image_id": image_id})

    def test_long_side_reads_jpeg_and_png_headers_only(self):
        png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 120, 340)
        self.assertEqual((cover.long_side(jpeg(180)), cover.long_side(png)), (180, 340))
        self.assertIsNone(cover.long_side(b"not an image"))
        self.assertIsNone(cover.long_side(b"\xff\xd8\xff"))

    def test_pick_needs_a_built_index_then_a_front_of_the_group(self):
        self.assertEqual(self.pick().status_code, 409)                    # not built: queued, nothing stored
        self.service._pool.submit(lambda: None).result(5)
        self.assertEqual(self.pick(11).status_code, 404)                  # 11 is a Back
        self.assertEqual(self.pick(999).status_code, 404)                 # not in the group
        self.assertIsNone(self.service.store.get_choice("al-1"))
        self.assertEqual(self.pick(10).json(), {"album_id": "al-1", "image_id": 10})
        self.assertEqual(self.service.store.get_choice("al-1"), 10)
        bad = self.client.put("/api/artwork/choice/al-1", json={"rgid": "nope", "image_id": 10})
        self.assertEqual(bad.status_code, 400)

    def test_choices_lists_every_pick(self):
        self.assertEqual(self.client.get("/api/artwork/choices").json(), {"choices": {}})
        self.service.build_now(RG)
        self.pick()
        self.assertEqual(self.client.get("/api/artwork/choices").json(), {"choices": {"al-1": 10}})

    def test_clear_removes_the_pick(self):
        self.service.build_now(RG)
        self.pick()
        self.assertEqual(self.client.delete("/api/artwork/choice/al-1").json()["image_id"], None)
        self.assertIsNone(self.service.store.get_choice("al-1"))

    def test_the_pick_is_served_for_the_album_cover_and_never_asks_navidrome(self):
        self.service.build_now(RG)
        self.pick()
        with mock.patch.object(navidrome_client, "cover_art") as nav:
            r = self.client.get("/api/owned/artwork/al-1", params={"size": "300"})
        nav.assert_not_called()
        self.assertEqual((r.status_code, r.content), (200, JPEG))
        self.assertEqual(r.headers["cache-control"], "private, max-age=300")

    def test_other_albums_are_untouched_by_a_pick(self):
        self.service.build_now(RG)
        self.pick()
        with mock.patch.object(navidrome_client, "cover_art", return_value=("image/jpeg", b"lib")):
            r = self.client.get("/api/owned/artwork/al-2")
        self.assertEqual(r.content, b"lib")

    def _group(self, rgid=RG):
        return mock.patch.object(owned, "_album_group", return_value=(rgid, None))

    def test_grid_falls_back_to_best_front_when_the_library_has_no_cover(self):
        self.service.build_now(RG)
        with self._group(), mock.patch.object(
                navidrome_client, "cover_art", side_effect=navidrome_client.CoverArtUnavailable("none")):
            r = self.client.get("/api/owned/artwork/al-1")
        self.assertEqual((r.status_code, r.content), (200, JPEG))

    def test_missing_cover_and_unbuilt_group_stays_404_and_queues_the_build(self):
        with self._group(), mock.patch.object(
                navidrome_client, "cover_art", side_effect=navidrome_client.CoverArtUnavailable("none")):
            r = self.client.get("/api/owned/artwork/al-1")
        self.assertEqual(r.status_code, 404)
        self.service._pool.submit(lambda: None).result(5)
        self.assertEqual(self.fetch.release_calls, 1)

    def test_small_library_cover_is_replaced_only_by_a_larger_front(self):
        self.service.build_now(RG)
        small, big = jpeg(120), jpeg(900)
        self.fetch.release_index[R1] = self.fetch.release_index[R1]
        with self._group(), mock.patch.object(navidrome_client, "cover_art", return_value=("image/jpeg", small)):
            self.assertEqual(self.client.get("/api/owned/artwork/al-1").content, small)   # sizes unknown: keep
        view = self.service.index(RG)
        for entry in view["images"]:
            entry["width"] = entry["height"] = 1200
        with mock.patch.object(self.service, "index", return_value=view), self._group(), \
                mock.patch.object(navidrome_client, "cover_art", return_value=("image/jpeg", small)):
            self.assertEqual(self.client.get("/api/owned/artwork/al-1").content, JPEG)
        with mock.patch.object(self.service, "index", return_value=view), self._group(), \
                mock.patch.object(navidrome_client, "cover_art", return_value=("image/jpeg", big)):
            self.assertEqual(self.client.get("/api/owned/artwork/al-1").content, big)       # big enough: keep

    def test_album_payload_carries_the_pick(self):
        from discovery.search.album_page import album_sections
        album = {"id": "al-1", "name": "A", "artist": "B", "artist_id": "ar", "key": "b/a", "year": 1999,
                 "song_count": 3, "release_group_mbid": RG}
        sections = album_sections(SimpleNamespace(clock=lambda: 0.0, deadline_seconds=1), None, album=album,
                                  artist="B", artist_key="b", name="A", year=1999, release_group_mbid=RG,
                                  artwork_choice=10)
        first = next(sections)
        self.assertEqual(first["album"]["artwork_choice"], 10)


if __name__ == "__main__":
    unittest.main()
