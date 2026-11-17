"""Tests for scripts/store_size_report.py (efficiency S1, report part). unittest only."""
import contextlib
import hashlib
import importlib.util
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("store_size_report", ROOT / "scripts" / "store_size_report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

from backup_stores import STORES, Store  # noqa: E402

ONE_STORE = (Store("a.sqlite3", "test fixture"),)


def _make_wal_store(path: Path, rows: int = 5) -> None:
    """A WAL-mode store closed cleanly: no -wal or -shm left beside it."""
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    db.execute("CREATE INDEX t_v ON t (v)")
    db.execute("CREATE TABLE u (id INTEGER PRIMARY KEY)")
    db.executemany("INSERT INTO t (v) VALUES (?)", [(f"v{i}",) for i in range(rows)])
    db.commit()
    db.close()


def _listing(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.iterdir())


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _by_name(entry: dict) -> dict:
    return {obj["name"]: obj for obj in entry["objects"]}


class CountsTests(unittest.TestCase):
    def test_counts_rows_and_reports_objects(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            _make_wal_store(data / "a.sqlite3", rows=5)
            result = report.build_report(data, ONE_STORE)
            entry = result["stores"][0]
            self.assertEqual(entry["status"], "ok")
            objects = _by_name(entry)
            self.assertEqual(objects["t"]["rows"], 5)
            self.assertEqual(objects["t"]["kind"], "table")
            self.assertEqual(objects["u"]["rows"], 0)
            self.assertEqual(objects["t_v"]["kind"], "index")
            self.assertIsNone(objects["t_v"]["rows"])
            self.assertEqual(entry["allocated_bytes"], entry["page_count"] * entry["page_size"])

    def test_dbstat_bytes_per_object_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            _make_wal_store(data / "a.sqlite3", rows=200)
            result = report.build_report(data, ONE_STORE)
            if not result["dbstat"]:
                self.skipTest("this SQLite build has no dbstat")
            objects = _by_name(result["stores"][0])
            self.assertGreater(objects["t"]["bytes"], 0)
            self.assertGreaterEqual(objects["t"]["bytes"], objects["u"]["bytes"])
            # Sorted by bytes, largest first.
            sizes = [obj["bytes"] for obj in result["stores"][0]["objects"]]
            self.assertEqual(sizes, sorted(sizes, reverse=True))

    def test_live_wal_content_is_counted_without_changing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            path = data / "a.sqlite3"
            _make_wal_store(path, rows=5)
            writer = sqlite3.connect(path)
            writer.execute("PRAGMA wal_autocheckpoint = 0")
            writer.execute("INSERT INTO t (v) VALUES ('pending')")
            writer.commit()  # the new row lives in the -wal file, not yet in the main file
            wal = Path(str(path) + "-wal")
            try:
                self.assertTrue(wal.is_file())
                before = (_listing(data), _digest(path), _digest(wal))
                result = report.build_report(data, ONE_STORE)
                self.assertEqual(_by_name(result["stores"][0])["t"]["rows"], 6)
                self.assertEqual((_listing(data), _digest(path), _digest(wal)), before)
            finally:
                writer.close()


class ReadOnlyTests(unittest.TestCase):
    def test_source_is_byte_identical_and_no_sidecar_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            path = data / "a.sqlite3"
            _make_wal_store(path)
            before_listing, before_digest, before_mtime = _listing(data), _digest(path), path.stat().st_mtime_ns
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(report.main(["--data-dir", str(data)]), 0)
            report.build_report(data, ONE_STORE)
            self.assertEqual(_listing(data), before_listing)
            self.assertEqual(_digest(path), before_digest)
            self.assertEqual(path.stat().st_mtime_ns, before_mtime)

    def test_wal_without_shm_is_skipped_not_opened(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            path = data / "a.sqlite3"
            _make_wal_store(path)
            wal = Path(str(path) + "-wal")
            wal.write_bytes(b"not a real wal")
            before = _listing(data)
            entry = report.build_report(data, ONE_STORE)["stores"][0]
            self.assertTrue(entry["status"].startswith("skipped"))
            self.assertEqual(entry["objects"], [])
            self.assertEqual(_listing(data), before)
            self.assertEqual(entry["wal_bytes"], len(b"not a real wal"))

    def test_missing_store_is_reported_and_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            before = _listing(data)
            result = report.build_report(data, ONE_STORE)
            entry = result["stores"][0]
            self.assertEqual(entry["status"], "missing")
            self.assertEqual(entry["objects"], [])
            self.assertEqual(_listing(data), before)

    def test_unreadable_file_reported_as_error_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "a.sqlite3").write_bytes(b"this is not sqlite" * 100)
            entry = report.build_report(data, ONE_STORE)["stores"][0]
            self.assertTrue(entry["status"].startswith("error"), entry["status"])


class FallbackTests(unittest.TestCase):
    def test_dbstat_unavailable_reports_n_a_and_still_counts_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            _make_wal_store(data / "a.sqlite3", rows=5)
            failing = mock.Mock(side_effect=sqlite3.OperationalError("no such table: dbstat"))
            with mock.patch.object(report, "query_dbstat", failing):
                result = report.build_report(data, ONE_STORE)
                markdown = report.render_markdown(result)
            self.assertFalse(result["dbstat"])
            entry = result["stores"][0]
            self.assertEqual(entry["status"], "ok")
            self.assertGreater(entry["allocated_bytes"], 0)
            objects = _by_name(entry)
            self.assertEqual(objects["t"]["rows"], 5)
            self.assertIsNone(objects["t"]["bytes"])
            self.assertIn("dbstat: unavailable", markdown)
            self.assertIn("| a.sqlite3 | t | 5 | n/a |", markdown)


class OutputTests(unittest.TestCase):
    def test_json_output_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            _make_wal_store(data / "radio.sqlite3")
            out = Path(tmp) / "report.json"
            with contextlib.redirect_stdout(io.StringIO()):
                code = report.main(["--data-dir", str(data), "--json", str(out)])
            self.assertEqual(code, 0)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(set(payload), {"data_dir", "generated_at", "dbstat", "stores"})
            self.assertIsInstance(payload["dbstat"], bool)
            self.assertEqual([s["name"] for s in payload["stores"]], [s.name for s in STORES])
            for store in payload["stores"]:
                self.assertTrue({"name", "owner", "status", "objects", "file_bytes", "wal_bytes"} <= set(store) or store["status"] == "missing")
            radio = next(s for s in payload["stores"] if s["name"] == "radio.sqlite3")
            self.assertEqual(radio["status"], "ok")
            for obj in radio["objects"]:
                self.assertEqual(set(obj), {"name", "kind", "rows", "bytes"} | ({"error"} if "error" in obj else set()))
            self.assertTrue(all(s["status"] == "missing" for s in payload["stores"] if s["name"] != "radio.sqlite3"))

    def test_markdown_lists_store_table_rows_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            _make_wal_store(data / "a.sqlite3", rows=3)
            markdown = report.render_markdown(report.build_report(data, ONE_STORE))
            self.assertIn("| store | table | rows | bytes |", markdown)
            self.assertIn("| a.sqlite3 | t | 3 |", markdown)
            self.assertIn("| a.sqlite3 | index: t_v | - |", markdown)

    def test_missing_data_dir_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope"
            with contextlib.redirect_stderr(io.StringIO()):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(report.main(["--data-dir", str(missing)]), 1)
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
