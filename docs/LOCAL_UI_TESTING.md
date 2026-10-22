# Local UI testing

Last updated: 2026-10-22

## Purpose and current workflow

Use the **current local test environment** for manual browser verification of UI-facing changes against an identified GitHub revision. This document defines the required browser checks and evidence; it is not the launcher or setup guide for that environment.

**Obsolete workflow:** `~/navi-librarian-test/test-pr.sh` is retired. Do not run it, rely on its generated reports, or assume its setup, ports, directories, credentials, or isolation behavior apply to the current environment. It has been replaced by the new local test environment.

Before testing, identify the exact GitHub commit SHA under test and confirm that the environment uses that revision. Keep test data isolated from production music/download paths and keep acquisition services disabled unless the owner explicitly authorizes a safe test. Record the environment used, tested SHA, checklist results, failures, and skipped checks in the current test record. A changed application SHA requires a new check or an explicit statement that the earlier report covers only its recorded SHA.

## When to run manual UI checks

Manual browser checks are a required gate for a UI-facing code change, after automated CI succeeds on the exact tested SHA. For non-UI changes, do not rerun the full browser checklist merely because the PR head changed. The remaining performance-observation and distinct error/recovery checks from the October 13 report are deferred to the next UI-facing change; record them against that exact application SHA. API-only refactors still require automated/API regression checks and any specifically relevant UI smoke, but do not by themselves trigger a full visual checklist.

## Browser checklist

Use the running test environment in a browser, then record each item as Pass, Fail, or Skip; skipped items are not passes.

1. App starts and first-run login/setup works, when applicable to the test state.
2. Dashboard layout, artwork, and primary navigation render correctly.
3. Discovery lists load and can be refreshed without a visible error.
4. Artist/album navigation and album details work.
5. Settings load, save, and survive a page reload without exposing credentials.
6. Get/request changes to the expected requested state and prevents duplicate requests; do not start a real download.
7. Acquisition cards/status render correctly for whatever safe fixture/state is available. Skip behaviors that require an unavailable test fixture rather than using live data.
8. Error/recovery states are understandable and leave the UI usable.
9. Verify representative desktop and narrow/mobile widths, long names, missing artwork, empty/loading/error states, and horizontal overflow where relevant.
10. Check keyboard navigation, visible focus, and accessible control labels.
11. Inspect browser console and network errors, plus server logs, during the tested flow.
12. Performance: dashboard and discovery content load without obvious stalls; record approximate timings and any slow interaction in the notes.

The automated regression/safety tests remain responsible for destructive filesystem guarantees such as path traversal rejection, symlink containment, no-overwrite behavior, rollback, and preservation of unrelated files. Do not use the browser smoke test as a substitute for those tests.

## Test record and publication

Use the current environment's supported reporting process. Include the exact application SHA, environment details sufficient to reproduce the check, each checklist result, notes, and failures. Do not publish credentials, secrets, private test data, or logs containing sensitive values.

A local UI check does not prove that a merge, image publication, deployment, or production runtime verification occurred.

## Completed run — PR #31

The user completed the manual checklist and published the report as [PR comment #6155071713](https://github.com/abucalip/navi-librarian/pull/31#issuecomment-6155071713).

- **Tested application source SHA:** `96b253c5f3ec2f858e02afc034365a22bac0773e` on `docs/testing-release-workflow-priority`.
- **Environment:** macOS 26.2 arm64; Python 3.12.14; port 8090.
- **Safety boundary:** music/download paths pointed to the test sandbox and slskd was disabled by default.
- **Result:** all eight checklist items recorded in the uploaded report passed; zero failures. The report specifically covers setup/login, dashboard/artwork, discovery, navigation/album details, settings, safe Get/request interaction, acquisition card/status display, and unexpected browser/server errors.
- **Scope:** the report's eight recorded checks passed, but performance observations and a distinct error/recovery exercise are not separately recorded. Do not treat unrecorded items in the full operator checklist or the broader integration/release checklist as passed. Do not infer merge, image publication, deployment, or production runtime verification. Keep the report associated with its recorded SHA; documentation-only follow-up commits do not change the tested application source.


## Credential/setup persistence requirement — follow-up

Repeated first-run owner setup on each rerun is a test-kit defect, not an expected app workflow. The installed helper must keep the same app-data directory for all source SHAs of one PR, while keeping separate PRs isolated. Reusing that directory must preserve the test account and settings across process restarts and source revisions. Do not delete/recreate app data during ordinary reruns. A first-run test must use a deliberate fresh-data run and disposable state, not an implicit per-SHA reset.

**Verification boundary:** a later local test confirmed that the test account survived a server restart. That establishes persistence for the tested local instance, but does not by itself prove that a rerun of the same PR at a different source SHA reuses the same app-data directory. The helper is installed at `~/navi-librarian-test/test-pr.sh`, outside this repository; record the repeated-same-PR/new-SHA test separately before claiming that exact scenario is verified.
