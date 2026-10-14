## 2026-10-14 — PR #50 acquisition orchestration merged

- **PR:** https://github.com/abucalip/navi-librarian/pull/50
- **Branch:** `refactor/acquisition-orchestration-reconstructed`
- **Verified PR head:** `c8610fdc44ea93bcfb55a654598792aee78e7ecb`
- **Merge commit:** `a37d29cf11657dce6d5cbc6cb928ca840fe5b206`
- **Diff reviewed:** nine files; extracted persisted source-skip transition into `acquisition_orchestration.py`, preserved the MCP adapter, shared transition lock and conditional `status='downloading'` write, added direct regression tests, included the module in Docker packaging, and updated focused docs.
- **Exact-head CI:** Python syntax run `38589006636`, Docker packaging/full unit suite `38589006609`, container runtime smoke `38589006569`, and validation-only multi-architecture image validation `38589006620` all succeeded on the exact final PR head.
- **Review gate:** GitHub reported the PR open, ready, and mergeable; no review submissions or inline review threads were present. Squash merge completed successfully.
- **Verification boundaries:** no separate local test run is claimed. The multi-architecture image was validated with publishing paused. No image publication, deployment, or production runtime verification occurred.
- **Remaining work:** watcher orchestration, source switching, cleanup execution, interrupted-import recovery, and top-level acquisition coordination remain on the roadmap. Next, inspect the roadmap priorities and select the highest-priority unresolved requirement.


## 2026-10-14 — Safety-first acquisition dismissal verification

- Started branch `test/acquisition-dismissal-safety` from current GitHub `main` (`95fbce1654209368af82989efe87bc38fa3f02e2`).
- Added six regression cases around `_discovery_cancel_and_clean_source` for verified cleanup, unrelated files, traversal, ambiguous duplicate folders, symlink targets, and cancellation failure. The change is test-only; no cleanup safeguards were relaxed.
- Exact test commits: `6f35761504ca86702ec3863cc44d9fd8699d347b`, then `d8bffdf0989c530994a4ac9e01a8ab6a0a46dcdc` to correct the ambiguous-folder fixture.
- Initial exact-head CI on `b8e1c9a398853851e1a8140a9724600800f42c3b` exposed a test harness collision: loading the real cleanup helper replaced a stub expected by an existing source-switch test. The helper now has a distinct AST namespace name, preserving isolation; corrected-head CI and review remain pending. The reported HTTP 409 remains deferred because it was not reproduced. No merge, publication, deployment, or production runtime verification.


## 2026-10-14 — PR #51 merged: acquisition dismissal safety

- PR #51 (`test: cover acquisition dismissal cleanup safety`) was squash-merged to `main` at `790d690ca99866878ee6204f9d101dec5f099994`; tested PR head was `58021141472c85c9fa33c431cba15cb66792bc1c`.
- Added six regression cases for safe dismissal cleanup and refusal/preservation on unrelated files, traversal, ambiguous folders, symlinked targets, and failed transfer cancellation. Test-only change; no production behavior or safety checks altered.
- All four required workflows passed on the exact final PR head: syntax/acquisition safety `38590192829`, Docker packaging/full unit suite `38590192830`, container runtime smoke `38590192905`, validation-only multi-architecture image build `38590192858` (publishing paused).
- The first CI attempt failed due to a test-harness namespace collision; the helper was renamed in the AST test namespace and corrected-head CI passed. No separate local test run is claimed.
- The reported HTTP 409 was not reproduced and remains deferred. No live slskd test, real download-folder deletion, publication, deployment, or production runtime verification was performed.


## 2026-10-14 — Acquisition dismissal neighbor-preservation regression

- Branch `test/acquisition-dismissal-neighbor-preservation` starts from main commit `7f05363c3b9abec29ef7c7d516bad2796813b11e` after PR #52's exact-head CI passed and merge completed.
- Added a regression proving successful cleanup removes only the selected album folder and preserves a neighboring artwork file plus a different album folder. Existing tests cover refusal before deletion when the selected folder contains an unexpected file.
- Test-only change; no production cleanup logic altered. Exact-head CI is pending and no test pass is claimed. HTTP 409 remains deferred. No local test execution, live slskd, real production-folder deletion, publication, deployment, or runtime verification.

- CI follow-up: the initial assertion expected one transfer lookup, but the implementation performs two preflight checks. Corrected the test to expect both; exact head `f68ae4bd46523b9a41f298950ce397023a8f19b4` is awaiting CI.