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
