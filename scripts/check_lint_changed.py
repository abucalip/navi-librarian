#!/usr/bin/env python3
"""Lint ratchet: pylint findings in files a PR touches must not exceed the base.

Only a small set of simplification checks runs, only on Python files changed
between the merge base and HEAD, and a file fails only when a finding appears
more often than it did in the base version of that file. Existing findings in
touched files are therefore never the author's job (see "Opportunistic
simplification" in docs/DEVELOPMENT_WORKFLOW.md).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

CHECKS = (
    "unused-import",
    "unused-variable",
    "unreachable",
    "no-else-return",
    "no-else-raise",
    "no-else-continue",
    "no-else-break",
    "simplifiable-if-statement",
    "simplifiable-if-expression",
    "singleton-comparison",
    "use-implicit-booleaness-not-len",
    "consider-using-in",
    "consider-using-generator",
)

Finding = tuple[str, str, str]  # (path, symbol, message)


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed_python_files(base: str) -> dict[str, str | None]:
    """Map each added/modified/renamed .py path on HEAD to its base path (None if new)."""
    out = git("diff", "--name-status", "-M", "--diff-filter=AMR", f"{base}...HEAD")
    files: dict[str, str | None] = {}
    for line in out.splitlines():
        parts = line.split("\t")
        status, paths = parts[0], parts[1:]
        new_path = paths[-1]
        if not new_path.endswith(".py"):
            continue
        files[new_path] = paths[0] if status.startswith("R") else (None if status == "A" else new_path)
    return files


def run_pylint(paths: list[str], cwd: Path) -> list[dict]:
    if not paths:
        return []
    result = subprocess.run(
        [
            sys.executable, "-m", "pylint", "--rcfile=", "--persistent=n", "--disable=all",
            f"--enable={','.join(CHECKS)}", "--output-format=json", *paths,
        ],
        cwd=cwd, capture_output=True, text=True, check=False,
    )
    if result.returncode & (1 | 32):  # fatal or usage error: the run itself is not trustworthy
        raise SystemExit(f"pylint failed ({result.returncode}):\n{result.stdout}\n{result.stderr}")
    return json.loads(result.stdout or "[]")


def findings_by_key(messages: list[dict], rename: dict[str, str] | None = None) -> dict[Finding, list[int]]:
    rename = rename or {}
    grouped: dict[Finding, list[int]] = {}
    for message in messages:
        path = rename.get(message["path"], message["path"])
        grouped.setdefault((path, message["symbol"], message["message"]), []).append(message["line"])
    return grouped


def new_findings(head: dict[Finding, list[int]], base: dict[Finding, list[int]]) -> dict[Finding, list[int]]:
    """Findings whose count on HEAD is higher than in the base version."""
    return {
        key: lines
        for key, lines in head.items()
        if len(lines) > len(base.get(key, []))
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="base ref, for example origin/main")
    args = parser.parse_args()

    files = changed_python_files(args.base)
    if not files:
        print("LINT_CHANGED: no Python files changed")
        return 0

    head = findings_by_key(run_pylint(sorted(files), Path.cwd()))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        rename = {}
        for new_path, old_path in files.items():
            if old_path is None:
                continue
            target = root / old_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(git("show", f"{args.base}:{old_path}"), encoding="utf-8")
            rename[old_path] = new_path
        base = findings_by_key(run_pylint(sorted(rename), root), rename)

    added = new_findings(head, base)
    print(f"LINT_CHANGED: {len(files)} file(s) checked, {len(added)} new finding group(s)")
    for (path, symbol, message), lines in sorted(added.items()):
        where = ", ".join(str(line) for line in lines)
        print(f"{path}:{where}: {symbol}: {message}")
    if added:
        print("Fix these in the touched code, or move the change out of the PR. Do not add suppressions.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
