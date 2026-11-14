import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import check_lint_changed as lint


def msg(path, symbol, text, line):
    return {"path": path, "symbol": symbol, "message": text, "line": line}


class LintRatchetTests(unittest.TestCase):
    def test_existing_findings_are_not_new(self):
        head = lint.findings_by_key([msg("a.py", "unused-import", "Unused import os", 3)])
        base = lint.findings_by_key([msg("a.py", "unused-import", "Unused import os", 9)])
        self.assertEqual(lint.new_findings(head, base), {})

    def test_extra_occurrence_is_new(self):
        head = lint.findings_by_key([
            msg("a.py", "unused-import", "Unused import os", 1),
            msg("a.py", "unused-import", "Unused import os", 2),
        ])
        base = lint.findings_by_key([msg("a.py", "unused-import", "Unused import os", 1)])
        self.assertEqual(len(lint.new_findings(head, base)), 1)

    def test_new_file_has_no_base(self):
        head = lint.findings_by_key([msg("b.py", "no-else-return", "Unnecessary else", 4)])
        self.assertEqual(len(lint.new_findings(head, {})), 1)

    def test_renamed_file_compares_against_old_path(self):
        base = lint.findings_by_key([msg("old.py", "unreachable", "Unreachable code", 5)], {"old.py": "new.py"})
        head = lint.findings_by_key([msg("new.py", "unreachable", "Unreachable code", 7)])
        self.assertEqual(lint.new_findings(head, base), {})

    def test_fixed_finding_is_not_reported(self):
        base = lint.findings_by_key([msg("a.py", "unused-variable", "Unused variable x", 2)])
        self.assertEqual(lint.new_findings({}, base), {})


if __name__ == "__main__":
    unittest.main()
