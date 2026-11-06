import tempfile
import unittest
from pathlib import Path
from unittest import mock

from intelligence.musicbrainz import dump, scan
from intelligence.musicbrainz.scan import RowFilter
from intelligence.musicbrainz.schema import TABLES

COLUMNS = TABLES["l_artist_artist"]


def line(i, e0, e1):
    row = {c: "\\N" for c in COLUMNS}
    row.update(id=str(i), link=str(i % 7), entity0=str(e0), entity1=str(e1), last_updated="2020")
    return "\t".join(row[c] for c in COLUMNS) + "\n"


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "l_artist_artist"
        self.rows = [(i, i % 50, (i * 7) % 50) for i in range(1, 3001)]
        self.path.write_text("".join(line(*r) for r in self.rows))
        self.size = self.path.stat().st_size

    def expected(self, keep):
        return [(str(e0), str(e1)) for _, e0, e1 in self.rows if keep(e0, e1)]

    def run_scan(self, flt, workers=3):
        with mock.patch.object(scan, "MIN_CHUNK_BYTES", 1000), mock.patch.object(scan, "INLINE_BYTES", 0):
            return scan.scan_files({"l_artist_artist": (str(self.path), flt)}, workers=workers)["l_artist_artist"]

    def test_chunks_cover_every_line_exactly_once_in_order(self):
        flt = RowFilter(("id",))
        got = self.run_scan(flt)
        self.assertEqual([int(r[0]) for r in got], [r[0] for r in self.rows])

    def test_all_conditions(self):
        flt = RowFilter(("entity0", "entity1"), ints=(("entity0", frozenset({3, 4})), ("entity1", frozenset(range(10)))))
        self.assertEqual(self.run_scan(flt), self.expected(lambda a, b: a in (3, 4) and b < 10))

    def test_any_condition(self):
        flt = RowFilter(("entity0", "entity1"), ints=(("entity0", frozenset({3})), ("entity1", frozenset({5}))), any_=True)
        self.assertEqual(self.run_scan(flt), self.expected(lambda a, b: a == 3 or b == 5))

    def test_no_conditions_returns_everything(self):
        self.assertEqual(len(self.run_scan(RowFilter(("id",)))), len(self.rows))

    def test_inline_path_matches_pool_path(self):
        flt = RowFilter(("entity0",), ints=(("entity1", frozenset({1, 2})),))
        pooled = self.run_scan(flt)
        inline = scan.scan_files({"l_artist_artist": (str(self.path), flt)}, workers=1)["l_artist_artist"]
        self.assertEqual(pooled, inline)

    def test_fallback_for_a_plain_reader_gives_the_same_rows(self):
        flt = RowFilter(("entity0", "entity1"), ints=(("entity0", frozenset({3, 4})),))
        reader = dump.extracted_reader(self.tmp.name)  # a real reader's __call__ is the sequential path
        plain = lambda tables: reader(tables)  # no .scan attribute
        self.assertEqual(scan.scan_rows(plain, {"l_artist_artist": flt})["l_artist_artist"],
                         self.run_scan(flt))

    def test_strings_match_case_insensitively(self):
        path = Path(self.tmp.name) / "artist"
        fields = {c: "\\N" for c in TABLES["artist"]}
        fields.update(id="5", gid="AbC-1", name="X")
        path.write_text("\t".join(fields[c] for c in TABLES["artist"]) + "\n")
        got = scan.scan_files({"artist": (str(path), RowFilter(("id", "gid"), strs=(("gid", frozenset({"abc-1"})),)))})
        self.assertEqual(got["artist"], [("5", "AbC-1")])

    def test_progress_comes_from_the_calling_thread(self):
        import threading
        threads = set()
        with mock.patch.object(scan, "MIN_CHUNK_BYTES", 1000), mock.patch.object(scan, "INLINE_BYTES", 0):
            scan.scan_files({"l_artist_artist": (str(self.path), RowFilter(("id",)))}, workers=2,
                            on_progress=lambda f: threads.add(threading.current_thread()))
        self.assertEqual(threads, {threading.current_thread()})

    def test_optional_column_missing_from_a_table_is_none(self):
        path = Path(self.tmp.name) / "work"
        fields = {c: "\\N" for c in TABLES["work"]}
        fields.update(id="9", gid="g", name="W")
        path.write_text("\t".join(fields[c] for c in TABLES["work"]) + "\n")
        flt = RowFilter(("id", "sort_name"), optional=("sort_name",))
        self.assertEqual(scan.scan_files({"work": (str(path), flt)})["work"], [("9", None)])

    def test_progress_reaches_one(self):
        seen = []
        with mock.patch.object(scan, "MIN_CHUNK_BYTES", 1000), mock.patch.object(scan, "INLINE_BYTES", 0):
            scan.scan_files({"l_artist_artist": (str(self.path), RowFilter(("id",)))}, workers=2, on_progress=seen.append)
        self.assertEqual(seen[-1], 1.0)
        self.assertTrue(all(0 <= f <= 1 for f in seen))

    def test_wrong_column_count_is_an_error(self):
        bad = Path(self.tmp.name) / "work"
        bad.write_text("1\t2\n")
        with self.assertRaises(dump.DumpError):
            scan.scan_files({"work": (str(bad), RowFilter(("id",)))}, workers=1)

    def test_plan_chunks_tile_the_file(self):
        chunks = scan.plan_chunks(1_000_003, 4)
        self.assertEqual(chunks[0][0], 0)
        self.assertEqual(chunks[-1][1], 1_000_003)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(chunks, chunks[1:])))


if __name__ == "__main__":
    unittest.main()
