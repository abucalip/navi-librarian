import importlib.util
import tempfile
import unittest
from pathlib import Path

from intelligence.musicbrainz.schema import TABLES
from intelligence.store import open_store
from intelligence.store import repositories as repo

SPEC = importlib.util.spec_from_file_location("album_slice_audit", Path(__file__).resolve().parent.parent / "scripts" / "album_slice_audit.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def row(table, **values):
    return "\t".join(str(values.get(c, "\\N")) for c in TABLES[table]) + "\n"


class AlbumSliceAuditTest(unittest.TestCase):
    def test_counts_match_and_missing_is_reported(self):
        db = open_store(":memory:")
        rec = repo.upsert_entity(db, "recording", "So What", mbid="rec-gid", owned=True)[0]
        place = repo.upsert_entity(db, "place", "Studio", mbid="pl-gid")[0]
        repo.add_edge(db, place, rec, "recorded at", evidence_class="source_explicit", match_quality="exact_mbid",
                      source="musicbrainz_dump")
        self.assertEqual(audit.store_counts(db), {("place", "recorded at"): 1})
        self.assertEqual(audit.owned_recording_gids(db), {"rec-gid"})
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            files = {
                "recording": row("recording", id=7, gid="rec-gid", name="So What"),
                "link_type": row("link_type", id=1, name="recorded at") + row("link_type", id=2, name="mixed at"),
                "link": row("link", id=10, link_type=1) + row("link", id=11, link_type=2),
                "l_place_recording": row("l_place_recording", id=1, link=10, entity0=5, entity1=7)
                + row("l_place_recording", id=2, link=11, entity0=5, entity1=7)
                + row("l_place_recording", id=3, link=10, entity0=5, entity1=99),  # another recording: ignored
            }
            for table in audit.TABLES:
                (folder / table).write_text(files.get(table, ""))
            theirs = audit.dump_counts(folder, {"rec-gid"}, workers=1)
        self.assertEqual(theirs, {("place", "recorded at"): 1, ("place", "mixed at"): 1})
