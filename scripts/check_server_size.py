#!/usr/bin/env python3
"""Enforce a reviewed size ceiling for the legacy server and its top-level functions."""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

SERVER_LINE_LIMIT = 3032
TOP_LEVEL_FUNCTION_LINE_LIMIT = 280
FUNCTION_EXCEPTIONS = {
    "recommend_new_music": {
        "max_lines": 575,
        "reason": "Large live recommendation adapter; provider gathering was extracted first.",
        "follow_up": "Reduce this limit as recommendation policy and payload responsibilities are separated.",
    },
}


def top_level_function_sizes(source: str) -> list[tuple[str, int]]:
    """Return AST-measured sizes for module-level functions, including decorators."""
    tree = ast.parse(source)
    sizes = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        starts = [node.lineno, *(decorator.lineno for decorator in node.decorator_list)]
        sizes.append((node.name, node.end_lineno - min(starts) + 1))
    return sizes


def check_source(
    source: str,
    *,
    server_line_limit: int = SERVER_LINE_LIMIT,
    top_level_function_line_limit: int = TOP_LEVEL_FUNCTION_LINE_LIMIT,
    function_exceptions: dict[str, dict[str, object]] | None = None,
) -> list[str]:
    """Return all size violations with measured sizes and explicit exception context."""
    errors = []
    line_count = len(source.splitlines())
    if line_count > server_line_limit:
        errors.append(
            f"navidrome_server.py is {line_count} lines (limit {server_line_limit})"
        )

    try:
        functions = top_level_function_sizes(source)
    except SyntaxError as exc:
        return [f"navidrome_server.py cannot be parsed for size checks: {exc}"]

    exceptions = FUNCTION_EXCEPTIONS if function_exceptions is None else function_exceptions
    for name, size in functions:
        exception = exceptions.get(name)
        limit = (
            int(exception["max_lines"])
            if exception is not None
            else top_level_function_line_limit
        )
        if size > limit:
            message = f"top-level function {name} is {size} lines (limit {limit})"
            if exception is not None:
                message += (
                    f"; exception reason: {exception.get('reason', 'unspecified')};"
                    f" follow-up: {exception.get('follow_up', 'unspecified')}"
                )
            errors.append(message)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    source_path = args.root / "navidrome_server.py"
    try:
        source = source_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{source_path}: unable to read source: {exc}")
        return 1

    errors = check_source(source)
    line_count = len(source.splitlines())
    print(f"navidrome_server.py: {line_count} lines (limit {SERVER_LINE_LIMIT})")
    sizes = sorted(top_level_function_sizes(source), key=lambda item: item[1], reverse=True)
    print("Largest top-level functions:")
    for name, size in sizes[:10]:
        exception = FUNCTION_EXCEPTIONS.get(name)
        limit = int(exception["max_lines"]) if exception else TOP_LEVEL_FUNCTION_LINE_LIMIT
        print(f"  {name}: {size} lines (limit {limit})")
    if errors:
        print("\n".join(errors))
        return 1
    print("Legacy server size ratchet: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
