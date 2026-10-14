# Product requirements

Last updated: 2026-10-14

This is the user-facing behavior ledger. If implementation and this document disagree, do not silently assume either is correct: clarify the intended behavior, update this ledger, and add a regression test.

## Product goals

- Help the user discover albums that are not already in their Navidrome library.
- Provide a web UI while preserving the existing MCP entry point and discovery logic.
- Support acquisition through an existing slskd service with explicit controls and safeguards.
- Make state and settings survive container restarts and upgrades.
- Prefer small, testable changes and preserve working behavior when extending the UI.

## Functional requirements

| ID | Requirement | Status |
|---|---|---|
| DISC-01 | Generate new-music recommendations using the existing discovery/recommendation logic. | Implemented; regression validation required |
| DISC-02 | Provide discovery lists for personal discoveries, classics / collection-building, and Artist Deep Dives. | Implemented; regression validation required |
| DISC-03 | Refresh discovery lists and preserve user feedback such as save/dismiss where supported. | Implemented; verify persistence and edge cases |
| DISC-04 | Avoid recommending albums already owned in Navidrome. | Core requirement; test with real and mocked library data |
| DISC-05 | Filter non-album releases and avoid false artist matches, including Various Artists and similarly named artists. | Implemented in development history; maintain regression coverage |
| DISC-06 | Show useful album metadata, including release year and artwork when reliable; missing external metadata must not break discovery. | Implemented in development history; visual/edge-case validation required |
| DISC-07 | Artist Deep Dives should show no more than one album by an artist in a genre row. | Implemented in development history; regression/UI validation required |
| DISC-08 | New Releases should focus on recent MusicBrainz release groups by artists represented in the library, subject to the eligibility rules documented in `PROJECT_LOG.md`. | Implemented in development history; validate metadata matching |
| ACQ-01 | The user can request an album without being navigated away from the current discovery page. | Verify on the target branch |
| ACQ-02 | After Get is clicked, the button should visibly change to a red `requested` state and prevent duplicate requests while the request is pending/successful. On a failed request, restore a usable state and show an error. | Acceptance criterion; verify regression behavior |
| ACQ-03 | Each acquisition card has a persistent Dismiss control regardless of acquisition state. | Acceptance criterion; verify regression behavior |
| ACQ-04 | Dismissing an acquisition removes its acquisition entry and deletes the files in that album's associated folder, as requested by the user. The implementation must resolve the correct folder, stay within configured roots, and reject ambiguous/unsafe paths. | Six cleanup safety cases passed all four required workflows on PR #51 exact head `58021141472c85c9fa33c431cba15cb66792bc1c`; merged at `790d690ca99866878ee6204f9d101dec5f099994`. Neighbor-preservation regression passed on earlier exact head `f220ce3b0296cf9429daa927d9c5bfaae9bea7a7`; all four workflows also passed on current PR head `6413d7cd94919a9983a381a398787b4301443d1b`: syntax `38594465611`, Docker packaging/full unit suite `38594465538`, runtime smoke `38594465673`, validation-only multi-architecture build `38594465580` (publishing paused). Live slskd/UI and production deletion remain unverified; HTTP 409 remains deferred because it was not reproduced. |
| ACQ-05 | slskd candidates are grouped by their actual remote folder/path; punctuation, edition suffixes, and Unicode normalization should be handled without merging unrelated candidates. | Implemented in development history; preserve regression tests |
| ACQ-06 | Acquisition/import must not overwrite or delete unrelated library content. Validate file completeness and paths before any destructive or import operation. | Import safety and six dismissal refusal/preservation cases passed exact-head CI on PR #51. The follow-up test proves neighboring files and album folders survive successful dismissal; all four required workflows passed on exact PR head `6413d7cd94919a9983a381a398787b4301443d1b`. No live production-folder deletion test performed. |
| ACQ-07 | If an exact slskd artist+album query returns no usable peer file payloads, try a small bounded set of broader query variants. Keep album/artist candidate checks unchanged and report each query plus slskd-reported and collected response counts. | Implemented on PR #21 branch; automated CI passed on prior code/test revision, latest diagnostic-message test pending CI, live regression retest pending |
| SET-01 | Provide configuration for Navidrome, slskd, Last.fm, and ListenBrainz as applicable to the current UI. | Implemented in development history; verify secrets are not returned to clients |
| SET-02 | A blank secret submitted while editing settings must not accidentally erase an existing secret unless the user explicitly requests clearing it. | Verify with tests |
| SET-03 | slskd audio-quality preferences contain MP3 320, MP3 193–319, MP3 192, FLAC CD/unverified, FLAC 16-bit/44.1 kHz, and FLAC Hi-Res (24-bit or above 44.1 kHz) exactly once; the user can reorder them by dragging, with move buttons as a non-drag alternative, and the order persists. Existing four- and five-tier settings append newly supported FLAC tiers without changing the saved order. | Implemented on fix branch; automated CI and UI smoke test pending |
| AUTH-01 | Protect the web UI with a first-run owner account and session-based authentication while allowing only required static assets before login. | Security primitives and route integration tests merged; frontend asset extraction must preserve public login assets and protected application/API routes. Auth routes were extracted in PR #39, squash-merged at `f08495088b28ca538f90b9ff9edf4410f5e55749` from exact head `9187a51380d2a7ed7d27276ce4505827becaed32`; all four required workflows passed on that exact head. Preserve setup, login/logout, throttling, cookies, session persistence, and public/protected path behavior. Preserve setup, login/logout, throttling, cookies, session persistence, and public/protected path behavior |
| DATA-01 | Persist app database and authentication key under the configured data directory, mounted as persistent storage in Docker. | Implemented; verify restart/upgrade |
| API-01 | Validate API input and return useful HTTP errors rather than exposing internal exceptions or credentials. | Ongoing quality requirement |
| OPS-01 | Validate reproducible Docker builds for `linux/amd64` and `linux/arm64`; publish to GHCR only after the modularization roadmap is complete and release is explicitly authorized. | Runtime/build validation automated; GHCR publication intentionally paused |
| OPS-02 | Keep Navidrome and slskd as external services; the web container must not start a second copy of either service or the MCP server. | Current deployment design |

## Safety rules for acquisition and deletion

- Treat every user-visible dismiss action as destructive because it can delete album files.
- Resolve and validate a canonical path under the configured downloads/acquisition root before deleting.
- Never allow traversal, symlink escapes, an empty path, a root directory, or an ambiguous folder match to result in deletion.
- If a folder cannot be identified uniquely, fail safely and explain the problem; do not guess.
- Tests must prove both that the intended files are removed and that files outside the target folder remain untouched.
- Do not broaden write/delete permissions merely to make a failing operation pass.

## Change process

For every requirement changed:
1. Update this ledger if user-visible behavior changes.
2. Add or update an automated regression test.
3. Run the full test suite, not only the new test.
4. Manually smoke-test affected UI behavior.
5. Mark status accurately in [PROJECT_STATUS.md](PROJECT_STATUS.md).
