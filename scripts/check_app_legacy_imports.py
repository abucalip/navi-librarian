#!/usr/bin/env python3
"""Enforce the reviewed app-to-legacy-server import boundary.

The sole compatibility edge is the lazy import in
app/api/dependencies.py:get_librarian. Domain and route modules must not
import navidrome_server directly.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path

ALLOWED_PATH = Path("app/api/dependencies.py")
ALLOWED_FUNCTION = "get_librarian"


def _legacy_import_nodes(tree: ast.AST) -> list[tuple[ast.AST, tuple[str, ...]]]:
    found: list[tuple[ast.AST, tuple[str, ...]]] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.functions: list[str] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Import(self, node: ast.Import) -> None:
            if any(alias.name == "navidrome_server" or alias.name.startswith("navidrome_server.") for alias in node.names):
                found.append((node, tuple(self.functions)))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if node.module == "navidrome_server" or (node.module or "").startswith("navidrome_server."):
                found.append((node, tuple(self.functions)))

    Visitor().visit(tree)
    return found


def check_app_imports(root: Path) -> list[str]:
    app_dir = root / "app"
    if not app_dir.is_dir():
        return [f"{app_dir}: app directory not found"]

    errors: list[str] = []
    for path in sorted(app_dir.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            errors.append(f"{path.relative_to(root)}: unable to parse Python source: {exc}")
            continue

        relative = path.relative_to(root)
        for node, functions in _legacy_import_nodes(tree):
            allowed = (\n                relative == ALLOWED_PATH\n                and functions == (ALLOWED_FUNCTION,)\n                and isinstance(node, ast.Import)\n                and len(node.names) == 1\n                and node.names[0].name == "navidrome_server"\n            )
            if not allowed:
                errors.append(
                    f"{relative}:{node.lineno}: unapproved import of navidrome_server"
                    + (f" inside {' -> '.join(functions)}" if functions else "")
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    errors = check_app_imports(args.root.resolve())
    if errors:
        print("\n".join(errors))
        return 1
    print("App-to-legacy-server import boundary: OK")
    print("Allowlisted edge: app/api/dependencies.py:get_librarian (lazy compatibility adapter)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
