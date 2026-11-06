import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from intelligence.musicbrainz import dump
from intelligence.musicbrainz.schema import TABLES


def _archive(directory, members, schema="31"):
    path = Path(directory) / "mbdump.tar.bz2"
    with tarfile.open(path, "w:bz2") as tar:
        for name, text in [("TIMESTAMP", "2026-11-04 00:22:23+00\n"), ("SCHEMA_SEQUENCE", schema + "\n"), *members]:
            data = text.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return path


def _label_line(**over):
    row = {c: "\\N" for c in TABLES["label"]}
    row.update(id="7", gid="g-7", name="Blue\\tNote", comment="")
    row.update(over)
    return "\t".join(row[c] for c in TABLES["label"]) + "\n"


class DecodeTests(unittest.TestCase):
    def test_null_and_escapes(self):
        self.assertIsNone(dump.decode_field("\\N"))
        self.assertEqual(dump.decode_field("a\\tb\\\\c\\nd"), "a\tb\\c\nd")
        self.assertEqual(dump.decode_field(""), "")

    def test_literal_backslash_n_text_is_not_null(self):
        self.assertEqual(dump.decode_field("\\\\N"), "\\N")

    def test_wrong_column_count_is_an_error(self):
        with self.assertRaises(dump.DumpError):
            dump.decode_row("1\t2\n", ("a", "b", "c"))


class ExtractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = _archive(self.tmp.name, [
            ("mbdump/area", "ignored\n"),
            ("mbdump/label", _label_line() + _label_line(id="8", gid="g-8")),
            ("mbdump/work", ""),
        ])
        self.dest = Path(self.tmp.name) / "out"

    def read_labels(self):
        return [r["gid"] for _, rows in dump.extracted_reader(self.dest)(["label"]) for r in rows]

    def test_extracts_only_wanted_tables_and_reads_them_back(self):
        written = dump.extract_tables(self.path, {"label", "work"}, self.dest, parallel=False)
        self.assertEqual(set(written), {"label", "work"})
        self.assertFalse((self.dest / "area").exists())
        self.assertEqual(self.read_labels(), ["g-7", "g-8"])

    def test_second_call_reuses_the_folder_without_opening_the_archive(self):
        dump.extract_tables(self.path, {"label"}, self.dest, parallel=False)
        self.path.write_bytes(self.path.read_bytes())  # same size, same content
        again = dump.extract_tables(self.path, {"label"}, self.dest, parallel=False)
        self.assertEqual(set(again), {"label"})
        (self.dest / "label").unlink()
        self.assertEqual(set(dump.extract_tables(self.path, {"label"}, self.dest, parallel=False)), {"label"})

    def test_missing_table_is_an_error_and_leaves_no_marker(self):
        with self.assertRaises(dump.DumpError):
            dump.extract_tables(self.path, {"label", "recording"}, self.dest, parallel=False)
        self.assertFalse((self.dest / dump.COMPLETE_MARKER).exists())

    def test_wrong_schema_is_refused_before_writing(self):
        bad = _archive(self.tmp.name, [("mbdump/label", _label_line())], schema="99")
        with self.assertRaises(dump.DumpError):
            dump.extract_tables(bad, {"label"}, self.dest, parallel=False)
        self.assertFalse(self.dest.exists())

    @unittest.skipUnless(dump.parallel_available(), "indexed_bzip2 not installed")
    def test_parallel_decoder_gives_the_same_tables_and_progress(self):
        seen = []
        dump.extract_tables(self.path, {"label"}, self.dest, parallel=True, on_progress=seen.append)
        self.assertEqual(self.read_labels(), ["g-7", "g-8"])
        self.assertEqual(seen[-1], 1.0)

    def test_unknown_table_rejected(self):
        with self.assertRaises(KeyError):
            dump.extract_tables(self.path, {"nope"}, self.dest, parallel=False)


class ArchiveTests(unittest.TestCase):
    def test_reads_only_wanted_tables_in_order_with_named_columns(self):
        with tempfile.TemporaryDirectory() as d:
            path = _archive(d, [
                ("mbdump/area", ""),
                ("mbdump/label", _label_line() + _label_line(id="8", gid="g-8")),
                ("mbdump/work", ""),
            ])
            info = dump.read_info(path)
            self.assertEqual((info.schema_sequence, info.timestamp), (31, "2026-11-04 00:22:23+00"))
            seen = [(t, list(rows)) for t, rows in dump.iter_tables(path, {"label", "work"})]
        self.assertEqual([t for t, _ in seen], ["label", "work"])
        labels = seen[0][1]
        self.assertEqual([r["gid"] for r in labels], ["g-7", "g-8"])
        self.assertEqual(labels[0]["name"], "Blue\tNote")
        self.assertIsNone(labels[0]["begin_date_year"])
        self.assertEqual(labels[0]["comment"], "")

    def test_unknown_schema_sequence_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = _archive(d, [("mbdump/label", _label_line())], schema="32")
            with self.assertRaises(dump.DumpError):
                list(dump.iter_tables(path, {"label"}))

    def test_unknown_table_name_is_rejected_before_reading(self):
        with tempfile.TemporaryDirectory() as d:
            path = _archive(d, [])
            with self.assertRaises(KeyError):
                list(dump.iter_tables(path, {"nonsense"}))

    def test_archive_without_schema_sequence_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.tar.bz2"
            with tarfile.open(path, "w:bz2") as tar:
                data = b"x"
                info = tarfile.TarInfo("mbdump/label")
                info.size = 1
                tar.addfile(info, io.BytesIO(data))
            with self.assertRaises(dump.DumpError):
                dump.read_info(path)

    def test_not_an_archive(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.tar.bz2"
            path.write_bytes(b"not an archive")
            with self.assertRaises(dump.DumpError):
                dump.read_info(path)

    def test_checksum(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "f"
            path.write_bytes(b"abc")
            good = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            dump.verify_checksum(path, good.upper())
            with self.assertRaises(dump.DumpError):
                dump.verify_checksum(path, "0" * 64)


if __name__ == "__main__":
    unittest.main()
