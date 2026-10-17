"""Tests for the focused agent-session search utility."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.session_search import query_terms, search


class SessionSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        (self.root / "app").mkdir()
        (self.root / ".venv" / "lib").mkdir(parents=True)
        (self.root / "docs" / "workflow.md").write_text(
            "# Session workflow\nSearch documentation and code for relevant context.\n", encoding="utf-8"
        )
        (self.root / "PROJECT_STATUS.md").write_text("Session workflow summary.\\n", encoding="utf-8")\n        (self.root / "app" / "service.py").write_text(
            "# service\ndef replay_metadata():\n    return 'session context'\n", encoding="utf-8"
        )
        (self.root / ".venv" / "lib" / "ignored.py").write_text(
            "session workflow replay metadata\n", encoding="utf-8"
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_query_terms_preserve_quoted_phrases_and_deduplicate(self):
        self.assertEqual(query_terms('Replay "metadata lookup" replay'), ["replay", "metadata lookup"])

    def test_all_terms_is_default_and_returns_matching_snippets(self):
        results = search(self.root, "replay session")
        self.assertEqual([result.path for result in results], ["app/service.py"])
        self.assertIn("session context", results[0].snippets[0]["text"])

    def test_any_mode_returns_partial_matches(self):
        results = search(self.root, "workflow metadata", require_all=False)
        self.assertEqual({result.path for result in results}, {"docs/workflow.md", "app/service.py"})

    def test_scope_separates_documentation_from_code(self):
        self.assertEqual([m.path for m in search(self.root, "session workflow", scope="docs")],
                         ["docs/workflow.md"])
        self.assertEqual([m.path for m in search(self.root, "session context", scope="code")],
                         ["app/service.py"])

    def test_skips_virtual_environments_and_large_files(self):
        (self.root / "app" / "large.py").write_text("needle " * 100, encoding="utf-8")
        results = search(self.root, "needle", max_file_bytes=10)
        self.assertEqual(results, [])

    def test_rejects_empty_query(self):
        with self.assertRaises(ValueError):
            query_terms("   ")


if __name__ == "__main__":
    unittest.main()
