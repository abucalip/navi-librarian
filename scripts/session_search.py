#!/usr/bin/env python3
"""Retrieve focused documentation and source snippets for an agent task.

Examples (run from the repository root):
    python scripts/session_search.py "recommendation replay metadata_lookup_errors"
    python scripts/session_search.py "path traversal symlink" --scope code
    python scripts/session_search.py "session workflow" --scope docs --limit 8
    python scripts/session_search.py "Last.fm scoring" --json

This is a lightweight lexical search aid, not a substitute for reading the
canonical docs, tracing callers, or validating current GitHub state.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path

TEXT_SUFFIXES = {
    ".md", ".rst", ".txt", ".py", ".sh", ".toml", ".yaml", ".yml",
    ".json", ".html", ".css", ".js", ".ts", ".tsx", ".ini", ".cfg",
    ".conf", ".xml", ".sql", ".dockerfile",
}
SKIP_DIRS = {
    ".git", ".venv", "venv", "__pycache__", "node_modules", "dist",
    "build", "coverage", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "site-packages", "data", "downloads",
}
DEFAULT_MAX_FILE_BYTES = 1_000_000


@dataclass
class Match:
    path: str
    score: float
    matched_terms: list[str]
    snippets: list[dict[str, object]]


def query_terms(query: str) -> list[str]:
    """Split a query into case-insensitive terms, preserving quoted phrases."""
    try:
        parts = shlex.split(query)
    except ValueError as exc:
        raise ValueError(f"invalid query quoting: {exc}") from exc
    terms: list[str] = []
    seen: set[str] = set()
    for part in parts:
        term = part.strip().casefold()
        if term and term not in seen:
            terms.append(term)
            seen.add(term)
    if not terms:
        raise ValueError("provide at least one search term")
    return terms


def classify_path(path: Path) -> str:
    parts = path.parts
    if "docs" in parts or path.name.lower() in {"agents.md", "project_log.md", "readme.md"}:
        return "docs"
    return "code"


def eligible(path: Path, scope: str, max_file_bytes: int, root: Path) -> bool:
    if not path.is_file() or any(part in SKIP_DIRS for part in path.relative_to(root).parts[:-1]):
        return False
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name.lower() not in {"dockerfile", "makefile"}:
        return False
    try:
        return path.stat().st_size <= max_file_bytes and (
            scope == "all" or classify_path(path.relative_to(root)) == scope
        )
    except OSError:
        return False


def snippets_for(lines: list[str], terms: list[str], context: int, max_snippets: int = 3) -> list[dict[str, object]]:
    hit_lines = [
        index for index, line in enumerate(lines)
        if any(term in line.casefold() for term in terms)
    ]
    groups: list[tuple[int, int]] = []
    for hit in hit_lines:
        start, end = max(0, hit - context), min(len(lines), hit + context + 1)
        if groups and start <= groups[-1][1]:
            groups[-1] = (groups[-1][0], max(groups[-1][1], end))
        else:
            groups.append((start, end))
    result = []
    for start, end in groups[:max_snippets]:
        result.append({
            "start_line": start + 1,
            "text": "\n".join(f"{i + 1}: {lines[i].rstrip()}" for i in range(start, end)),
        })
    return result


def search(root: Path, query: str, *, scope: str = "all", require_all: bool = True,
           limit: int = 12, context: int = 1,
           max_file_bytes: int = DEFAULT_MAX_FILE_BYTES) -> list[Match]:
    terms = query_terms(query)
    root = root.resolve()
    matches: list[Match] = []
    for path in root.rglob("*"):
        if not eligible(path, scope, max_file_bytes, root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        folded = text.casefold()
        present = [term for term in terms if term in folded]
        if (require_all and len(present) != len(terms)) or not present:
            continue

        relative = path.relative_to(root).as_posix()
        path_folded = relative.casefold()
        occurrence_score = sum(min(folded.count(term), 20) for term in present)
        path_score = sum(3 for term in present if term in path_folded)
        doc_score = 2 if classify_path(path.relative_to(root)) == "docs" else 0
        completeness_score = 4 if len(present) == len(terms) else 0
        score = float(occurrence_score + path_score + doc_score + completeness_score)
        lines = text.splitlines()
        snippets = snippets_for(lines, present, context)
        matches.append(Match(relative, score, present, snippets))

    matches.sort(key=lambda item: (-item.score, -len(item.matched_terms), item.path))
    return matches[:max(0, limit)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="keywords or quoted phrases to find")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    parser.add_argument("--scope", choices=("all", "docs", "code"), default="all")
    parser.add_argument("--any", dest="require_all", action="store_false",
                        help="return files matching any query term instead of all terms")
    parser.add_argument("--limit", type=int, default=12, help="maximum matching files to show (default: 12)")
    parser.add_argument("--context", type=int, default=1, help="context lines around each hit (default: 1)")
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES,
                        help="skip larger files (default: 1000000)")
    parser.add_argument("--json", action="store_true", help="emit structured JSON for agent pipelines")
    args = parser.parse_args()

    if args.limit < 0 or args.context < 0 or args.max_file_bytes < 1:
        parser.error("--limit and --context must be non-negative; --max-file-bytes must be positive")
    try:
        results = search(args.root, args.query, scope=args.scope, require_all=args.require_all,
                         limit=args.limit, context=args.context, max_file_bytes=args.max_file_bytes)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    if args.json:
        print(json.dumps([asdict(match) for match in results], indent=2, ensure_ascii=False))
    elif not results:
        print("No matches. Try fewer terms, --any, or a different --scope.")
    else:
        for match in results:
            print(f"\n## {match.path}  [score {match.score:g}; terms: {', '.join(match.matched_terms)}]")
            for snippet in match.snippets:
                print(f"--- line {snippet['start_line']} ---")
                print(snippet["text"])
        print(f"\n{len(results)} matching file(s). Search is a discovery aid; inspect the relevant source and callers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
