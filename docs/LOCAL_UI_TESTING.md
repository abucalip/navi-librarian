# Local PR UI smoke testing

Last updated: 2026-10-13

## Purpose

Use the local helper to verify the real browser UI against an exact GitHub pull-request head. This is a manual smoke-test layer on top of automated CI, not a replacement for unit tests or release/deployment verification.

## Run a PR

The helper is installed outside the application checkout at `~/navi-librarian-test/test-pr.sh`. With GitHub CLI authenticated (`gh auth status`), run:

```sh
~/navi-librarian-test/test-pr.sh <PR-number>
```

The default app URL is `http://127.0.0.1:8089`. If that port is occupied, choose another port:

```sh
~/navi-librarian-test/test-pr.sh <PR-number> 8090
```

If the helper says it created `~/navi-librarian-test/config.env`, edit that private file only if you need optional Navidrome/discovery access, then rerun. Keep secrets out of test notes and PR comments.

## Isolation and safety

- The helper reads the open PR's current head SHA from GitHub and downloads that exact source archive. It does not check out, reset, clean, or push a Git branch.
- Each PR/SHA has a separate source directory and server log under `~/navi-librarian-test/runs/`. The virtual environment should be reused when the selected Python version and dependency lock/input set have not changed. **Application data must persist per PR, not per SHA**, so changing to a new commit of the same PR does not force first-run account creation again. Different PRs must remain isolated from one another. Only an explicitly requested fresh-data test should reset setup/account state.
- Music and download paths point to `~/navi-librarian-test/sandbox/`, not the real library or download folder.
- Keep slskd disabled at `http://127.0.0.1:9` with an empty API key for ordinary UI checks. Do not point the app at live download paths or run destructive dismissal/acquisition checks against real data without explicit authorization.
- Prefer a read-only Navidrome account if live library browsing is configured.
- The helper's source is currently installed as a local utility outside the repository. Do not treat local edits to it as project changes; GitHub remains authoritative for application code and documentation. Because the helper is external to this repository, a documentation change alone does not change its behavior: verify that the installed `test-pr.sh` uses a stable per-PR app-data path before considering credential/setup persistence fixed.

## When to run manual UI checks

Manual browser checks are a required gate for a UI-facing code change, after automated CI succeeds on the exact tested SHA. For non-UI changes, do not rerun the full browser checklist merely because the PR head changed. The remaining performance-observation and distinct error/recovery checks from the October 13 report are deferred to the **next UI-facing change**; record them against that exact application SHA. API-only refactors still require automated/API regression checks and any specifically relevant UI smoke, but do not by themselves trigger a full visual checklist.

## Browser checklist

When a UI-facing change is ready for manual verification, use the UI while the server is running, then return to Terminal and press Enter. Record each item as Pass, Fail, or Skip; skipped items are not passes.

1. App starts and first-run login/setup works.
2. Dashboard layout, artwork, and primary navigation render correctly.
3. Discovery lists load and can be refreshed without a visible error.
4. Artist/album navigation and album details work.
5. Settings load, save, and survive a page reload without exposing credentials.
6. Get/request changes to the expected requested state and prevents duplicate requests; do not start a real download.
7. Acquisition cards/status render correctly for whatever safe fixture/state is available. Skip behaviors that require an unavailable test fixture rather than using live data.
8. Error/recovery states are understandable and leave the UI usable.
9. Performance: dashboard and discovery content load without obvious stalls; record approximate timings and any slow interaction in the notes.
10. No unexpected browser-console or server-log errors occur during the tested flow.

The automated regression/safety tests remain responsible for destructive filesystem guarantees such as path traversal rejection, symlink containment, no-overwrite behavior, rollback, and preservation of unrelated files. Do not use the browser smoke test as a substitute for those tests.

## Report and publication

The helper writes a Markdown report to `~/navi-librarian-test/reports/PR-<number>-<sha>.md`. It records the exact tested SHA, machine/Python information, CI state it could retrieve, checklist results, notes, and failures. Review the report and choose whether to publish it as a PR comment when prompted.

If the PR head changes after testing, rerun against the new head or state explicitly that the prior report covers only its recorded SHA. UI startup alone does not mean the entire checklist passed. Passing a local UI check does not prove that a merge, image publication, deployment, or production runtime verification occurred.


## Completed run — PR #31

The user completed the manual checklist and published the report as [PR comment #6155071713](https://github.com/abucalip/navi-librarian/pull/31#issuecomment-6155071713).

- **Tested application source SHA:** `96b253c5f3ec2f858e02afc034365a22bac0773e` on `docs/testing-release-workflow-priority`.
- **Environment:** macOS 26.2 arm64; Python 3.12.14; port 8090.
- **Safety boundary:** music/download paths pointed to the test sandbox and slskd was disabled by default.
- **Result:** all eight checklist items recorded in the uploaded report passed; zero failures. The report specifically covers setup/login, dashboard/artwork, discovery, navigation/album details, settings, safe Get/request interaction, acquisition card/status display, and unexpected browser/server errors.
- **Scope:** the report's eight recorded checks passed, but performance observations and a distinct error/recovery exercise are not separately recorded. Do not treat unrecorded items in the full operator checklist or the broader integration/release checklist as passed. Do not infer merge, image publication, deployment, or production runtime verification. Keep the report associated with its recorded SHA; documentation-only follow-up commits do not change the tested application source.


## Credential/setup persistence requirement — follow-up

Repeated first-run owner setup on each rerun is a test-kit defect, not an expected app workflow. The installed helper must keep the same app-data directory for all source SHAs of one PR, while keeping separate PRs isolated. Reusing that directory must preserve the test account and settings across process restarts and source revisions. Do not delete/recreate app data during ordinary reruns. A first-run test must use a deliberate fresh-data run and disposable state, not an implicit per-SHA reset.

**Current limitation at this closeout:** the helper is installed at `~/navi-librarian-test/test-pr.sh`, outside the GitHub repository. This session updated the authoritative policy but did not directly modify that file on the user's Mac. Until the installed helper's path selection is patched and rerun, the recurring-credential issue remains unverified and must not be marked fixed.
