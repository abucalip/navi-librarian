# AST-coupled test inventory

Audit baseline: GitHub `main` at `60cf07ffa05416355053660c1823f6af5b18716b` (2026-10-16); pure-helper test migration in progress on the current follow-up branch.

This inventory distinguishes tests that parse the legacy server source from tests that import it to verify a compatibility adapter. The latter are not AST-coupled and must not be indiscriminately rewritten.

## Tests that parse or execute functions extracted from navidrome_server.py

| Test | Coupling | Coverage currently provided | Recommended disposition |
|---|---|---|---|
| `tests/test_acquisition_safety.py` | Still parses `navidrome_server.py` with `ast` to execute acquisition orchestration/lifecycle functions. Pure slskd search and quality helper names are now supplied from direct imports of `slskd_search.py` and `slskd_quality.py`, not extracted from source. | Broader-query fallback plus duplicate-request concurrency, persistence-before-import, incomplete saved details, dismissed-job reactivation, and stale-download watcher recovery. | Keep high-risk lifecycle cases while tracing each remaining function to its real owner; remove the AST harness only when the production orchestration boundary can be tested directly without stubbing away its behavior. Do not delete or weaken the high-risk cases merely to remove the AST harness. |
| `tests/test_quality_priority.py` | **Migrated:** no longer reads or parses `navidrome_server.py`; imports `slskd_quality.quality_tier()` and exercises `SettingsPersistence` directly. | FLAC tier classification, filename fallback, legacy quality-priority migration/order, and settings/UI contract. | Complete. Keep UI contract assertions as source-level UI tests; they are not legacy-server coupling. |
| `tests/test_slskd_transfer_lookup.py` | **Migrated:** directly imports `slskd_transfers.download_transfer_files()`; no longer reads or parses `navidrome_server.py`. | Transfer-list 404/no-active-transfer behavior, propagation of other HTTP errors, URL encoding/timeout, and successful response parsing with remote-directory identity. | Complete. Legacy wrapper compatibility remains separately covered by `tests/test_slskd_transfers.py`. |

### Migration order

1. **Done on this branch, pending CI/merge:** quality classification and settings persistence tests use direct imports in `test_quality_priority.py`; pure slskd helper bindings in `test_acquisition_safety.py` now point to extracted modules.
2. Remaining source parsing is limited to acquisition orchestration/lifecycle cases in `test_acquisition_safety.py`. Migrate those only after mapping each case to the real owner; do not stub away safety coverage.

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

There are **two remaining direct AST/source-layout couplings** to `navidrome_server.py`: `tests/test_acquisition_safety.py` and `tests/test_quality_priority.py`. The transfer lookup migration is complete; its direct-import behavior tests and the separate legacy adapter contract in `tests/test_slskd_transfers.py` remain. The acquisition-safety test is the highest-risk migration and must be split incrementally, preserving the real concurrency, persistence, recovery, and acquisition lifecycle guarantees.

This inventory is based on a source search and full review of the identified test files at the stated main baseline. CI generated the dependency map from the audit branch, whose application source is unchanged from that baseline. It contains 159 local Python modules and a 71-module static closure from `app.main`; `navidrome_server` appears in that closure because `app/api/dependencies.py` imports it inside the lazy `get_librarian()` function. This static edge does not mean importing `app.main` eagerly loads the legacy server; `tests/test_auth_routes_integration.py::test_importing_app_does_not_initialize_legacy_server` checks that runtime boundary. The graph reports one direct `app/` import edge to the legacy server: `app/api/dependencies.py`.
