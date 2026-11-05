## 2026-11-05 — Server V2 Phase 1 slice 1: store foundation merged

- **Owner decisions:** Phase 1 approved; D-7 option 1 (new dedicated SQLite file with its own migration runner), recorded as D-026 in `docs/DECISIONS.md`. D-8 and D-9 stay open.
- **Code merged via PR:** [#759](https://github.com/abucalip/navi-librarian/pull/759), squash `910d577385edf5655f06c8401e4f11e5cb4f5b16`: `intelligence/store/` (`migrations.py`, `db.py`), schema v1 (observations append-only, entities, entity_aliases, edges, unresolved, insights, snapshots, job_runs, meta), `tests/test_intelligence_store.py`, and `Dockerfile` now copies `intelligence/`.
- **Verification actually run:** `python3 -m unittest tests.test_intelligence_store` locally, 19 tests passing; `py_compile` on the new files. Full suite not run (owner rule). Required checks passed on head `f3fa43a6cf3fc3bf8935cd4a8c19c747efa898d6`: compile, test-and-build, container-smoke, validate-container, validate-release-workflow (publish-release skipped).
- **Documentation committed directly to main:** `docs/DECISIONS.md` (D-026), `docs/ServerV2.md` status and D-7 row, `docs/PROJECT_STATUS.md`, `docs/ACTIVE_WORK.md` and this log.
- **Not done / limitations:** nothing imports the store; no server wiring, endpoint, provider traffic, publication or deployment. The database file path and its backup handling are not decided yet. Concurrent-migration behavior and WAL on the real data directory were not exercised beyond unit tests.
- **Next action:** Phase 1 slice 2, repositories and the generation mechanism.

