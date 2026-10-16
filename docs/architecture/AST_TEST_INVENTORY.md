# AST-coupled test inventory

Audit baseline: GitHub `main` at `93519c403ac2c301c46acddf6a64d59059d3f683` (2026-10-16).

This inventory distinguishes tests that parse the legacy server source from tests that import it to verify a compatibility adapter. The latter are not AST-coupled and must not be indiscriminately rewritten.

## Source-layout coupling audit

| Test | Coupling | Coverage currently provided | Recommended disposition |
|---|---|---|---|
| `tests/test_acquisition_safety.py` | **Migrated:** no longer reads or parses `navidrome_server.py`; fixture now supplies isolated state only. | Duplicate-request concurrency, incomplete saved-download recovery refusal, dismissed-job reactivation/refusal, stale watcher recovery, and importing-status persistence failure are exercised through direct imports of `acquisition_request_coordinator`, `acquisition_orchestration`, and `acquisition_import_service`. Query generation/polling/diagnostics and filesystem move/rollback/symlink protections remain covered by their own direct-import suites. The importing-status regression verifies no import callback or destination mutation occurs when persistence fails. | Complete. Keep behavior tests on production modules and retain independent compatibility tests for public adapters/MCP. |
| `tests/test_quality_priority.py` | **Migrated:** no longer reads or parses `navidrome_server.py`; imports `slskd_quality.quality_tier()` and exercises `SettingsPersistence` directly. | FLAC tier classification, filename fallback, legacy quality-priority migration/order, and settings/UI contract. | Complete. Keep UI contract assertions as source-level UI tests; they are not legacy-server coupling. |
| `tests/test_slskd_transfer_lookup.py` | **Migrated:** directly imports `slskd_transfers.download_transfer_files()`; no longer reads or parses `navidrome_server.py`. | Transfer-list 404/no-active-transfer behavior, propagation of other HTTP errors, URL encoding/timeout, and successful response parsing with remote-directory identity. | Complete. Legacy wrapper compatibility remains separately covered by `tests/test_slskd_transfers.py`. |

### Migration order

1. **Complete:** quality classification/settings persistence use direct imports in `test_quality_priority.py`; `test_acquisition_safety.py` no longer parses `navidrome_server.py`.
2. **Complete:** the final AST/source-layout coupling in `test_acquisition_safety.py` was removed. Its fixture no longer compiles functions from the legacy server. Import persistence failure is covered by the production import service and the dismissal/transition lock is covered by direct orchestration tests. Filesystem safety remains covered in `tests/test_acquisition_import.py`; request concurrency/recovery remain covered through the real request coordinator. No production code changed.

## Related legacy-server references that are not AST source coupling

These tests import or patch `navidrome_server` to check compatibility adapters, lazy imports, or MCP-facing behavior. They should be reviewed only when their relevant adapter changes; they are not blockers caused by reading the file as source.

- `tests/test_acquisition_routes.py`: patches `sys.modules["navidrome_server"]` to verify the API's lazy legacy-service adapter.
- `tests/test_auth_routes_integration.py`: asserts importing the web app does not load `navidrome_server`; this is an important application-assembly boundary regression.
- `tests/test_lastfm_client.py`: legacy wrappers delegate to the extracted Last.fm client and preserve filtering/error state.
- `tests/test_listenbrainz_client.py`: legacy recent-listens wrapper preserves username lookup and signature.
- `tests/test_music_tag_audit.py`: legacy JSON/tool adapter preserves its response contract.
- `tests/test_musicbrainz_rating_client.py`: legacy rating wrapper delegates while passing cache dependencies.
- `tests/test_slskd_search.py`: legacy expected-track-count adapter compatibility; the remaining search helper tests already use direct imports.
- `tests/test_slskd_transfers.py`: legacy queue/download-transfer adapter contracts alongside direct tests of `slskd_transfers.py`.
- `tests/test_mcp_registry.py`: subprocess import test ensures importing the legacy server does not load the MCP SDK; retain for the current compatibility surface.

Other text-reading tests found in the test suite inspect frontend assets/templates, not `navidrome_server.py`, and are outside this inventory. `tests/test_data_directory.py` uses a synthetic path named `navidrome_server.py` to test data-directory resolution; it does not read the real server source.

## Audit conclusion

There are **no remaining direct AST/source-layout couplings** to `navidrome_server.py` in the audited inventory. PR #274 removed the `ast.parse()` harness from `tests/test_acquisition_safety.py`; it now uses injected fixture state and directly exercises production coordinator/orchestration/import-service modules. This removes source-layout coupling without deleting lifecycle assertions or weakening filesystem/persistence safety. Keep separate compatibility tests for the public adapters/MCP surface and rerun this source search after future test changes.

This inventory is based on a source search and full review of the identified test files at the stated main baseline. CI generated the dependency map from the audit branch, whose application source is unchanged from that baseline. It contains 159 local Python modules and a 71-module static closure from `app.main`; `navidrome_server` appears in that closure because `app/api/dependencies.py` imports it inside the lazy `get_librarian()` function. This static edge does not mean importing `app.main` eagerly loads the legacy server; `tests/test_auth_routes_integration.py::test_importing_app_does_not_initialize_legacy_server` checks that runtime boundary. The graph reports one direct `app/` import edge to the legacy server: `app/api/dependencies.py`.
