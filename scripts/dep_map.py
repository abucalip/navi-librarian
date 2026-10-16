#!/usr/bin/env python3
"""Emit a deterministic AST-based import map for application assembly audits.

Run from the repository root:
    python scripts/dep_map.py --output docs/architecture/dependency-map.json

This is a static import map, not a substitute for tracing dynamic imports,
dependency injection, entry points, or runtime compatibility calls.
"""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path

ROOT = Path.cwd()

def module_name(path: Path, root: Path) -> str:
    relative = path.relative_to(root).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)

def imports_of(path: Path) -> list[dict[str, object]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "module": alias.name, "line": node.lineno, "kind": "import"
                })
        elif isinstance(node, ast.ImportFrom):
            imports.append({
                "module": node.module or "", "level": node.level,
                "line": node.lineno, "kind": "from",
                "names": [alias.name for alias in node.names],
            })
    return sorted(imports, key=lambda item: (int(item["line"]), str(item["module"])))

def resolve_local_imports(source: Path, imports: list[dict[str, object]], modules: dict[str, Path]) -> list[str]:
    resolved: set[str] = set()
    for item in imports:
        raw_module = str(item["module"])
        level = int(item.get("level", 0))
        if level:
            package = module_name(source, ROOT).split('.')[:-1]
            package = package[:max(0, len(package) - max(level - 1, 0))]
            candidate = ".".join(package + ([raw_module] if raw_module else []))
        else:
            candidate = raw_module
        if candidate in modules:
            resolved.add(candidate)
        for name in item.get("names", []):
            child = f"{candidate}.{name}" if candidate else str(name)
            if child in modules:
                resolved.add(child)
    return sorted(resolved)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, help="write JSON here instead of stdout")
    args = parser.parse_args()
    global ROOT
    ROOT = args.root.resolve()
    python_files = sorted(
        path for path in ROOT.rglob("*.py")
        if not any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts)
    )
    modules = {module_name(path, ROOT): path for path in python_files}
    api_dir = ROOT / 'app' / 'api'
    targets = [
        path for path in python_files
        if path == ROOT / 'app' / 'main.py'
        or api_dir in path.parents
        or path == ROOT / 'navidrome_server.py'
    ]
    graph: dict[str, dict[str, object]] = {}
    # Include every repository-local module so the app.main closure is transitive.
    for path in python_files:
        name = module_name(path, ROOT)
        imports = imports_of(path)
        graph[name] = {"path": path.relative_to(ROOT).as_posix(),
                       "imports": imports,
                       "local_imports": resolve_local_imports(path, imports, modules)}
    start = 'app.main'
    closure: set[str] = set()
    pending = [start] if start in graph else []
    while pending:
        current = pending.pop()
        if current in closure:
            continue
        closure.add(current)
        pending.extend(child for child in graph.get(current, {}).get('local_imports', []) if child not in closure)
    result = {
        "schema_version": 1,
        "scope": "all repository Python modules; audit targets are app/main.py, app/api/**/*.py, navidrome_server.py",
        "audit_targets": sorted(module_name(path, ROOT) for path in targets),
        "notes": ["AST import edges only; dynamic imports and dependency injection require manual review.",
                  "Closure traverses repository-local modules discovered by the AST scan."],
        "modules": graph,
        "app_main_import_closure": sorted(closure),
        "legacy_server_in_app_main_closure": "navidrome_server" in closure,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = args.output if args.output.is_absolute() else ROOT / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
