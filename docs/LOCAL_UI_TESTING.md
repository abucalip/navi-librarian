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
- Each PR/SHA has a separate source directory, virtual environment, server log, and app-data directory under `~/navi-librarian-test/runs/`.
- Music and download paths point to `~/navi-librarian-test/sandbox/`, not the real library or download folder.
- Keep slskd disabled at `http://127.0.0.1:9` with an empty API key for ordinary UI checks. Do not point the app at live download paths or run destructive dismissal/acquisition checks against real data without explicit authorization.
- Prefer a read-only Navidrome account if live library browsing is configured.
- The helper's source is currently installed as a local utility outside the repository. Do not treat local edits to it as project changes; GitHub remains authoritative for application code and documentation.

## Browser checklist

Use the UI while the server is running, then return to Terminal and press Enter. Record each item as Pass, Fail, or Skip; skipped items are not passes.

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
