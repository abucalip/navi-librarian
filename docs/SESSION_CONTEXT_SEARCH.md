# Agent session context search

Use `scripts/session_search.py` at the repository root to retrieve a small, relevant slice of documentation and code before opening full files. It is intended for any coding agent, including the assistant, and uses only Python's standard library.

## Quick start

```sh
python scripts/session_search.py "recommendation replay metadata_lookup_errors"
python scripts/session_search.py "path traversal symlink" --scope code
python scripts/session_search.py "session workflow" --scope docs --limit 8
python scripts/session_search.py '"Last.fm" scoring' --json
```

The default behavior requires every query term to occur in a file. Use `--any` for broader recall. Quoted phrases are treated as a single term. Results are ranked by term coverage, occurrences, path matches, and a small documentation preference; each result includes a few matching line snippets.

## Standard agent workflow

1. Inspect current GitHub `main`, recent commits, open PRs, and relevant CI. GitHub remains authoritative; do not use a local checkout as the source of truth.
2. Read `docs/PROJECT_STATUS.md` for the current state and next action.
3. Run `python scripts/session_search.py "<task-specific concepts>"` to find the relevant requirements, decisions, architecture, tests, callers, and implementation.
4. Read the full relevant canonical docs and source ranges returned by search. Search `PROJECT_LOG.md` by module, PR, behavior, or error when historical evidence matters; do not ingest the whole log by default.
5. Trace production callers, tests, configuration, packaging, and safety boundaries before editing. Search is an index, not proof that every relevant reference was found.
6. Define one concrete objective and acceptance criteria, then follow `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`.

## Options

- `--scope all|docs|code`: search the full repository, documentation, or code/config respectively.
- `--any`: match at least one query term instead of all terms.
- `--limit N`: maximum number of matching files (default 12).
- `--context N`: context lines around each hit (default 1).
- `--max-file-bytes N`: skip larger files (default 1,000,000 bytes).
- `--root PATH`: repository root (defaults to the current working directory).
- `--json`: emit structured results for agent pipelines.

The tool skips common generated, virtual-environment, dependency, and data directories. It reads bounded text files and ignores undecodable files. If results are empty, use fewer terms, `--any`, or a different scope.

## Limitations

This is lexical search, not semantic search. It does not prove absence, resolve symbols, trace dynamic imports, or replace GitHub/CI inspection. Treat matches as navigation hints. Read canonical docs and verify code, callers, tests, and current GitHub state before making claims or changes.
