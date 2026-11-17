"""Tests for scripts/backup_stores.py (efficiency S2). unittest only."""
import importlib.util
import io
import re
import sqlite3
import stat
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("backup_stores", ROOT / "scripts" / "backup_stores.py")
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)

from intelligence.store.db import open_store  # noqa: E402


def _make(path: Path, rows: int = 5) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute("PRAGMA journal_mode = WAL")
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    db.executemany("INSERT INTO t (v) VALUES (?)", [(f"v{i}",) for i in range(rows)])
    db.commit()
    db.close()


def _source(rel: str) -> str:
    return (ROOT / rel).read_text()


class StoreTableTests(unittest.TestCase):
    def test_every_store_name_matches_its_owning_code(self):
        names = {s.name for s in backup.STORES}
        self.assertEqual(len(names), len(backup.STORES))
        expected = {
            "navidrome_discovery.sqlite3": ("navidrome_server.py", 'DISCOVERY_DB = DATA_DIR / "navidrome_discovery.sqlite3"'),
            "navidrome_metadata_cache.sqlite3": ("navidrome_server.py", 'METADATA_CACHE_DB = DATA_DIR / "navidrome_metadata_cache.sqlite3"'),
            "intelligence.sqlite3": ("app/api/insights.py", 'STORE_FILE = "intelligence.sqlite3"'),
            "radio.sqlite3": ("app/api/radio.py", 'librarian.DATA_DIR / "radio.sqlite3"'),
            "song_peaks.sqlite3": ("app/api/waveform.py", 'librarian.DATA_DIR / "song_peaks.sqlite3"'),
            "artwork/artwork.sqlite3": ("app/api/artwork.py", 'librarian.DATA_DIR / "artwork"'),
        }
        for name, (module, snippet) in expected.items():
            self.assertIn(name, names)
            self.assertIn(snippet, _source(module), name)
        self.assertIn('self.root / "artwork.sqlite3"', _source("intelligence/artwork/store.py"))
        # Names the script takes from code: the gate file and the state file beside the knowledge store.
        from integrations.provider_gate import GATE_FILE
        from intelligence.store.state import default_state_path

        self.assertIn(GATE_FILE, names)
        self.assertIn(Path(default_state_path("intelligence.sqlite3")).name, names)
        self.assertEqual(names, set(expected) | {GATE_FILE, "intelligence.state.sqlite3"})

    def test_every_knowledge_store_file_constant_is_covered(self):
        found = set()
        for path in (ROOT / "app" / "api").glob("*.py"):
            found.update(re.findall(r'^STORE_FILE = "([^"]+)"', path.read_text(), re.M))
        self.assertEqual(found, {backup.KNOWLEDGE_FILE})

    def test_no_unlisted_sqlite_file_name_in_server_code(self):
        # A new "<name>.sqlite3" literal in server code must be added to STORES (or this test).
        listed = {Path(s.name).name for s in backup.STORES}
        seen = set()
        files = [ROOT / "navidrome_server.py", ROOT / "metadata_cache.py"]
        for folder in ("app", "settings", "intelligence", "integrations", "acquisition", "discovery"):
            files.extend(p for p in (ROOT / folder).rglob("*.py") if p.name != "fixture_set.py")
        for path in files:
            seen.update(re.findall(r'"([A-Za-z_.]+\.sqlite3?)"', path.read_text()))
        self.assertEqual(seen - listed, set())


class BackupTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data = Path(tmp.name) / "data"
        self.data.mkdir()
        self.dest = Path(tmp.name) / "backups" / "one"

    def test_backup_while_a_writer_holds_a_transaction(self):
        store = self.data / "navidrome_discovery.sqlite3"
        _make(store, rows=50)
        writer = sqlite3.connect(store, timeout=5, isolation_level=None)
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("INSERT INTO t (v) VALUES ('uncommitted')")
        try:
            results = backup.run_backup(self.data, self.dest)
        finally:
            writer.execute("COMMIT")
            writer.close()
        self.assertEqual([r[1] for r in results if r[0] == store.name], ["ok"])
        copy = sqlite3.connect(self.dest / store.name)
        self.assertEqual(copy.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(copy.execute("SELECT COUNT(*) FROM t").fetchone()[0], 50)  # committed rows only
        copy.close()

    def test_backup_while_a_writer_is_active(self):
        store = self.data / "radio.sqlite3"
        _make(store, rows=10)
        stop = threading.Event()
        errors = []

        def write():
            db = sqlite3.connect(store, timeout=10)
            try:
                while not stop.is_set():
                    db.execute("INSERT INTO t (v) VALUES ('x')")
                    db.commit()
            except Exception as error:  # reported below
                errors.append(error)
            finally:
                db.close()

        thread = threading.Thread(target=write)
        thread.start()
        try:
            for i in range(5):
                target = self.dest.parent / f"run{i}"
                results = backup.run_backup(self.data, target)
                self.assertEqual([r[1] for r in results if r[0] == "radio.sqlite3"], ["ok"])
                copy = sqlite3.connect(target / "radio.sqlite3")
                self.assertEqual(copy.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertGreaterEqual(copy.execute("SELECT COUNT(*) FROM t").fetchone()[0], 10)
                copy.close()
        finally:
            stop.set()
            thread.join()
        self.assertEqual(errors, [])

    def test_copies_are_private_single_files(self):
        _make(self.data / "navidrome_discovery.sqlite3")
        _make(self.data / "artwork" / "artwork.sqlite3")
        backup.run_backup(self.data, self.dest)
        for rel in ("navidrome_discovery.sqlite3", "artwork/artwork.sqlite3"):
            self.assertEqual(stat.S_IMODE((self.dest / rel).stat().st_mode), 0o600, rel)
        self.assertEqual(stat.S_IMODE(self.dest.stat().st_mode), 0o700)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()), ["artwork", "navidrome_discovery.sqlite3"])
        self.assertEqual([p.name for p in (self.dest / "artwork").iterdir()], ["artwork.sqlite3"])

    def test_missing_store_is_skipped_and_not_created(self):
        _make(self.data / "radio.sqlite3")
        results = {name: status for name, status, _ in backup.run_backup(self.data, self.dest)}
        self.assertEqual(results["radio.sqlite3"], "ok")
        skipped = [n for n, s in results.items() if s == "skipped"]
        self.assertEqual(len(skipped), len(backup.STORES) - 1)
        self.assertFalse((self.data / "navidrome_discovery.sqlite3").exists())
        self.assertFalse((self.dest / "navidrome_discovery.sqlite3").exists())

    def test_corrupt_store_fails_and_leaves_no_partial_copy(self):
        (self.data / "radio.sqlite3").write_bytes(b"not a database" * 100)
        _make(self.data / "song_peaks.sqlite3")
        results = {name: status for name, status, _ in backup.run_backup(self.data, self.dest)}
        self.assertTrue(results["radio.sqlite3"].startswith("failed"))
        self.assertEqual(results["song_peaks.sqlite3"], "ok")
        self.assertFalse((self.dest / "radio.sqlite3").exists())

    def test_main_summary_has_no_row_contents_and_refuses_dest_inside_data(self):
        _make(self.data / "radio.sqlite3")
        db = sqlite3.connect(self.data / "radio.sqlite3")
        db.execute("INSERT INTO t (v) VALUES ('SECRET-VALUE')")
        db.commit()
        db.close()
        out = io.StringIO()
        with redirect_stdout(out):
            code = backup.main(["--data-dir", str(self.data), "--dest", str(self.dest.parent)])
        self.assertEqual(code, 0)
        self.assertIn("radio.sqlite3", out.getvalue())
        self.assertNotIn("SECRET-VALUE", out.getvalue())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(backup.main(["--data-dir", str(self.data), "--dest", str(self.data / "b")]), 1)

    def test_no_store_found_is_an_error(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(backup.main(["--data-dir", str(self.data), "--dest", str(self.dest.parent)]), 1)


class WipeAndRestoreTests(unittest.TestCase):
    def test_owner_decisions_survive_a_knowledge_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp) / "data"
            data.mkdir()
            knowledge = data / "intelligence.sqlite3"
            db = open_store(knowledge)
            db.execute(
                "INSERT INTO state.card_decisions (kind, key, state, payload, decided_at) VALUES ('k', 'card-1', 'dismissed', '{}', 1.0)"
            )
            db.commit()
            db.close()

            dest = Path(tmp) / "bk"
            results = {n: s for n, s, _ in backup.run_backup(data, dest)}
            self.assertEqual(results["intelligence.sqlite3"], "ok")
            self.assertEqual(results["intelligence.state.sqlite3"], "ok")

            # Disaster: both files and their WAL side files are gone; restore only the state file.
            for path in data.glob("intelligence*"):
                path.unlink()
            (data / "intelligence.state.sqlite3").write_bytes((dest / "intelligence.state.sqlite3").read_bytes())

            # The knowledge store is rebuilt from nothing and attaches the restored state file.
            db = open_store(knowledge)
            try:
                rows = db.execute("SELECT kind, key, state FROM state.card_decisions").fetchall()
                self.assertEqual([tuple(r) for r in rows], [("k", "card-1", "dismissed")])
                self.assertEqual(db.execute("SELECT COUNT(*) FROM entities").fetchone()[0], 0)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
