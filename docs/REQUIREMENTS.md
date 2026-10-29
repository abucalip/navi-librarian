# Product requirements

Last updated: 2026-10-17 (MCP retirement)

This is the user-facing behavior ledger. If implementation and this document disagree, do not silently assume either is correct: clarify the intended behavior, update this ledger, and add a regression test.

## Product goals

- Help the user discover albums that are not already in their Navidrome library.
- Provide a supported web UI and preserve the shared discovery logic; MCP is not a supported interface.
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
| ACQ-01 | The user can request an album without being navigated away from the current discovery page. | Browser-source regression added; CI and manual verification pending |
| ACQ-02 | After Get is clicked, the button should visibly change to a red `requested` state and prevent duplicate requests while the request is pending/successful. On a failed request, restore a usable state and show an error. | Browser-source regression added; CI and manual verification pending |
| ACQ-03 | Each acquisition card has a persistent Dismiss control regardless of acquisition state. | Browser-source regression and API success/validation tests added; CI and manual verification pending |
| ACQ-04 | Dismissing an acquisition removes its acquisition entry and deletes the files in that album's associated folder, as requested by the user. The implementation must resolve the correct folder, stay within configured roots, and reject ambiguous/unsafe paths. | Cleanup logic is extracted to `acquisition_cleanup.py`; web API callers use the shared cleanup implementation. Six refusal/success cases and neighbor preservation are now direct-import tests in `tests/test_acquisition_cleanup.py`. PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed all four required workflows and merged at `982e39122a401b8b68d75e38423dbb93711b4abd`; no live slskd or production deletion test is claimed. HTTP 409 remains deferred because it was not reproduced. |
| ACQ-05 | slskd candidates are grouped by their actual remote folder/path; punctuation, edition suffixes, and Unicode normalization should be handled without merging unrelated candidates. | Implemented in development history; preserve regression tests |
| ACQ-06 | Acquisition/import must not overwrite or delete unrelated library content. Validate file completeness and paths before any destructive or import operation. | Import safety and dismissal refusal/preservation cases are retained; cleanup tests now directly import the extracted production implementation. PR #54 exact head `79bb2854e362786661264eb55fe1697aa0ac6596` passed all four required workflows and merged at `982e39122a401b8b68d75e38423dbb93711b4abd`. No live production-folder deletion test performed. |
| ACQ-07 | If an exact slskd artist+album query returns no usable peer file payloads, try a small bounded set of broader query variants, including wildcard-masked artist names (`*ink *loyd`) for names slskd blocks outright. Keep album/artist candidate checks unchanged and report each query plus slskd-reported and collected response counts. | Implemented on PR #21 branch; automated CI passed on prior code/test revision, latest diagnostic-message test pending CI, live regression retest pending |
| LIB-01 | Every artist, album and genre name in the app opens its library page (search results, library rows, cards, rows, the album panel, tags, similar artists). A song result opens its album. Song names are not links. | Implemented in PR #630; browser verification pending |
| LIB-02 | The artist page shows the name, a larger picture, a bio (Navidrome for owned artists), tag buttons that open genre pages, the top 20 albums by listens (owned ticked, others with Get), and similar artists. Unowned artists have the same page. | Implemented in PR #630; browser verification pending |
| LIB-03 | The album page shows title, year, artwork, artist link, a Get button or an owned tick, service links, Apple Music notes (first paragraph, Read more for the rest), the tracklist, similar artists and similar unowned albums. | Implemented in PR #630; browser verification pending |
| LIB-04 | A browser refresh returns to the page the owner was on. The address hash is `#<page>` for a top-level page and `#library/artist?key=&id=&name=&mbid=`, `#library/album?key=&id=&artist=&name=&year=&mbid=` or `#library/genre?tag=` for a library page, every value URI-encoded. An unknown or malformed hash shows the dashboard. The hash holds names, keys and catalog IDs only, never a token. Each page change pushes a history entry, so browser Back and Forward step through the in-app pages. The in-app library stack is not stored, so after a refresh the in-app Back button returns to the library list. Login returns to the same hash. | Implemented in PR #631 (v0.2.5); browser verification pending |
| DASH-01 | Under the Recommended row the dashboard shows a Genres grid (Navidrome genres with albums, largest first, 12 shown and "View more" up to 60; a tile opens the genre page). | Implemented in PR #632 (v0.2.6); owner browser checks done |
| DASH-02 | The dashboard then shows card shelves for New releases (the discovery list), Newly added, Recently played and Most played (Navidrome newest, recent and frequent). Each card shows a check when the library has the album and the Get button when not. Navidrome failures show an error line and leave the rest of the dashboard usable. | Implemented in PR #632 (v0.2.6); owner browser checks done |
| DASH-03 | The Recommended row is a slider: one feature slide with the cover, category, title, artist and bio, and the next three albums as blurred thumbnails. Previous, Next, Left and Right keys and a click on a thumbnail move through the ten. Only the feature slide is a tab stop. It uses plain CSS and JS (works in Firefox), animates only opacity and transform, and the fade-in is off under reduced motion. | Implemented in PR #632 (v0.2.6); owner browser checks done |
| LIB-05 | Artist and album pages show five similar artists chosen at random from the server's list on each page load, as circular photos filling the page width (three per row on narrow screens), with a name and, for owned artists, "In your library". Similar albums (album page) and albums (artist page) show seven, with an "All albums" button when there are more. An unowned album page shows "Not in your library" under the year. This refines LIB-02 and LIB-03. | Implemented in PR #632 (v0.2.6); owner browser checks done |
| SET-01 | Provide configuration for Navidrome, slskd, Last.fm, and ListenBrainz as applicable to the current UI. | Implemented in development history; verify secrets are not returned to clients |
| SET-02 | A blank secret submitted while editing settings must not accidentally erase an existing secret unless the user explicitly requests clearing it. | Verify with tests |
| SET-03 | slskd audio-quality preferences contain MP3 320, MP3 193–319, MP3 192, FLAC CD/unverified, FLAC 16-bit/44.1 kHz, and FLAC Hi-Res (24-bit or above 44.1 kHz) exactly once; the user can reorder them by dragging, with move buttons as a non-drag alternative, and the order persists. Existing four- and five-tier settings append newly supported FLAC tiers without changing the saved order. | Implemented on fix branch; automated CI and UI smoke test pending |
| AUTH-01 | Protect the web UI with a first-run owner account and session-based authentication while allowing only required static assets before login. | Security primitives and route integration tests merged; frontend asset extraction must preserve public login assets and protected application/API routes. Auth routes were extracted in PR #39, squash-merged at `f08495088b28ca538f90b9ff9edf4410f5e55749` from exact head `9187a51380d2a7ed7d27276ce4505827becaed32`; all four required workflows passed on that exact head. Preserve setup, login/logout, throttling, cookies, session persistence, and public/protected path behavior. Preserve setup, login/logout, throttling, cookies, session persistence, and public/protected path behavior |
| DATA-01 | Persist app database and authentication key under the configured data directory, mounted as persistent storage in Docker. | Implemented; verify restart/upgrade |
| API-01 | Validate API input and return useful HTTP errors rather than exposing internal exceptions or credentials. | Ongoing quality requirement; `/api/acquire` rejects non-boolean `auto_queue` values with HTTP 400 rather than truthiness-coercing strings or numbers. |
| OPS-01 | Validate reproducible Docker builds for `linux/amd64` and `linux/arm64`; publish to GHCR only after the modularization roadmap is complete and release is explicitly authorized. | Runtime/build validation automated; GHCR publication intentionally paused |
| OPS-02 | Keep Navidrome and slskd as external services; the web container must not start a second copy of either service. | Current deployment design |

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
