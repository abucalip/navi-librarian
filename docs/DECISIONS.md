# Architecture and workflow decisions

Last updated: 2026-11-02

Record decisions here when they constrain future implementation. Add new entries rather than silently rewriting history.

## D-001 — Keep existing discovery logic as the domain layer

**Decision:** The FastAPI web UI calls existing librarian functions in `navidrome_server.py` rather than maintaining a second copy of discovery/acquisition logic.

**Reason:** Avoid behavior drift between MCP and web access.

**Consequence:** Changes to shared functions require regression testing for both web and MCP behavior.

## D-002 — Web UI is a separate containerized service

**Decision:** Run the web app in Docker alongside, but separate from, Navidrome and slskd.

**Reason:** Keep service responsibilities isolated and make upgrades/rollback independent.

**Consequence:** Use reachable service URLs/network names and explicit bind mounts; do not bundle duplicate Navidrome or slskd instances into this image.

## D-003 — Persistent state lives outside the image

**Decision:** Mount a named volume at `/data` for the application database and authentication key.

**Reason:** Container replacement must not reset the account or saved state.

**Consequence:** Never delete this volume during routine upgrades or rollback. Back it up before migrations.

## D-004 — Separate implementation from verification status

**Decision:** Track Planned, In progress, Implemented, Tested, Merged, Deployed, and Verified as distinct states.

**Reason:** Code on a branch, code merged to `main`, and behavior running successfully on the VM are different facts.

**Consequence:** Every handoff must state the exact branch/commit, tests actually run, deployment evidence, and outstanding uncertainty.

## D-005 — Use narrow, reviewable changes

**Decision:** Prefer feature/fix branches and small diffs; use isolated worktrees for experiments. Do not reset, force-push, or overwrite unrelated local changes without explicit approval.

**Reason:** The development process has multiple active checkouts and in-progress work that must not be lost.

**Consequence:** Before editing, inspect branch, status, recent commits, and diff. Before handoff, inspect the final diff and tests.

## D-006 — Acquisition dismissal is a destructive operation

**Decision:** The requested dismiss behavior may delete the files associated with the acquisition's album folder.

**Reason:** The user explicitly requested cleanup when dismissing an acquisition card.

**Consequence:** Resolve the exact folder under an approved root; reject traversal, symlink escapes, ambiguous matches, and unrelated paths. Add positive and negative tests. Do not mark this behavior Verified without a controlled test.

## D-007 — Keep external metadata optional

**Decision:** Artwork, release-year, biography, and third-party music metadata enrich discovery but must not be required for the core recommendation flow.

**Reason:** External services can be unavailable, slow, ambiguous, or missing an album.

**Consequence:** Use exact/normalized matching where appropriate, bounded timeouts/caches, and graceful fallbacks.

## D-008 — Private registry errors are not tag errors

**Decision:** Treat GHCR `unauthorized` as an access/visibility/authentication issue until proven otherwise.

**Reason:** Choosing a commit tag or digest cannot grant registry access.

**Consequence:** Verify package visibility or authenticate before changing deployment tags.

## D-009 — GitHub is authoritative; assistant owns code changes and commits

**Decision:** GitHub is the sole source of truth for code, commits, pull requests, documentation, and release history. The assistant alone modifies project code and creates commits. The user's local checkout is for fetching and testing GitHub revisions, not for originating authoritative code changes.

**Reason:** Keep a single auditable history and avoid divergence between a local testing baseline and the shared repository.

**Consequence:** Base authoritative work on GitHub refs. Use focused GitHub branches and PRs; report exact commit SHAs and actual CI results. The user tests a specific GitHub branch/commit locally and reports results; the assistant makes any required fix on GitHub. Do not merge local-only commits back into GitHub or merge local `main` into a PR simply to reconcile histories. For testing against a divergent local baseline, use a temporary/disposable branch or worktree and never push that test-only combination. Local changes must be inspected and preserved, not reset or discarded without explicit authorization. Merge, image publication, deployment, and production verification remain separate states.


## D-010 — Separate album import filesystem mechanics from acquisition orchestration

**Decision:** Put staging, verified-track movement, storage-identity checks, no-overwrite behavior, rollback, and import-manifest handling in the directly importable `acquisition_import.py` module. Keep acquisition status transitions, dismissal synchronization, candidate selection, and retry/failover orchestration in `navidrome_server.py`.

**Reason:** The filesystem transaction is safety-critical and benefits from deterministic temporary-directory tests independent of MCP/server initialization.

**Consequence:** Keep the legacy server helper as a compatibility wrapper that injects the existing strict completion matcher. Direct-import tests must exercise the module implementation; retain the broader lifecycle safety tests until orchestration is extracted separately. Do not change import semantics as part of this relocation.


## D-011 — Isolate cached discovery-list persistence

**Decision:** Put the SQLite read/write mechanics for cached discovery-list payloads in the directly importable `discovery_store.py`. Keep `_discovery_read_list` and `_discovery_write_list` as compatibility wrappers in `navidrome_server.py`, including the existing `_discovery_init()` call.

**Reason:** Discovery list storage can be regression-tested independently without importing the MCP server or initializing external services.

**Consequence:** The module owns only the `discovery_lists` table's read/write behavior. Feedback, acquisition state, settings, refresh locks, list building, and provider calls remain in the server for later focused extractions. Do not change payload shape, timestamp semantics, or cache/error behavior during relocation.


## D-012 — Separate discovery refresh coordination from list construction

**Decision:** Put the lock/dispatch/error/response coordination for cached discovery-list refreshes in directly importable `discovery_refresh.py`. Keep legacy `_discovery_refresh_personal` and `_discovery_refresh_other` entry points in `navidrome_server.py` as thin adapters.

**Reason:** Refresh control flow can be tested independently without importing MCP initialization or calling providers, while list-building and persistence remain distinct responsibilities.

**Consequence:** Inject existing locks, recommendation/list-builder callables, and the persistence wrapper. Preserve lock acquisition and release, list identifiers, response shapes, count fields, JSON-error handling, and error reporting. Do not move provider logic or alter list payload semantics in this extraction.


## D-013 — Split Claude front-end work from backend integration

**Decision:** Claude may implement UI-only changes in `static/app.css`, `static/app.js`, `static/login.css`, `static/login.js`, `app/templates/*.html`, and narrowly scoped UI tests/fixtures. Backend/domain/security, API contracts, application assembly, persistence, acquisition/import/filesystem safety, CI, packaging, release, and deployment remain outside that role. All work is proposed through GitHub PRs; the assistant owns cross-layer integration, release gates, and merge coordination.

**Reason:** The UI assets are now extracted into dedicated paths, enabling focused frontend iteration without allowing parallel agents to silently change server contracts or safety-critical behavior.

**Consequence:** Root `CLAUDE.md` is the operational instruction source for Claude. This decision supersedes only the single-agent ownership wording in D-009; it does not change GitHub authority, the local-testing-only rule, branch/PR requirements, or the distinction between merge, publication, deployment, and runtime verification.

## D-014 — Keep MCP registration outside the shared web service module

**Decision:** Keep the legacy MCP tool names and callables, but register them only in mcp_registry.py when the MCP entry point is explicitly run. The shared navidrome_server.py module must not import or initialize the MCP SDK merely because the web application needs its service functions.

**Reason:** The web application and MCP server share domain functions today, but importing the service should not itself load the MCP runtime. This is a safe incremental boundary before eventual MCP retirement.

**Consequence:** Keep an explicit ordered registry and regression tests for all existing tool names and callable references. Do not remove the MCP dependency, tool surface, or runtime entry point until web callers and release gates demonstrate that removal is safe.

**PR #138 verification record:** implementation/documentation head `fe71a9a19188a018a2ee65d5b313a99413d239f2` passed all four required workflows (syntax/acquisition safety `38783091362`, Docker packaging/full suite/build `38783091326`, runtime smoke `38783091309`, validation-only multi-architecture `38783091337`). The final documentation-updated PR head `05d0eaf9a2e1ca94f3f03251208059540d06772f` passed all four required workflows (syntax `38783296279`, Docker packaging/full suite/build `38783296173`, runtime smoke `38783296256`, validation-only multi-architecture `38783296249`) and PR #138 merged at `197863830471bbd63eed57a11cafd815aede7f00`.


## D-015 — Retire legacy source-patching and process-restart MCP tools

**Decision:** Remove `restart_server` and `apply_server_patch` from `navidrome_server.py` and the ordered MCP registry. Preserve the MCP runtime and all other registered tools.

**Reason:** The owner identified these as early-development legacy functions and requested removal if safe. Current-source inspection found no internal callers; they were exposed only as MCP tools. `restart_server` kills/relaunches a process on hardcoded port 8000, and `apply_server_patch` rewrites the running service's source file. Their risk outweighs the value of preserving these two legacy operations.

**Consequence:** Regression tests pin the registry at 25 unique tools and verify both retired functions are absent from the service module and registry. This does not retire MCP or authorize removal of other MCP capabilities. Reintroducing either tool requires a new explicit owner decision and security review.

## D-016 — `navidrome_server.py` takes no new code; new code goes in new modules

**Decision:** `navidrome_server.py` must not receive any additions: no new functions, constants, imports, routes or other lines. Every new feature is written in a new, directly importable module under `discovery/`, `settings/`, `integrations/` or another existing package, with its own tests. The server may only shrink (moving or deleting code) or keep existing call sites that cannot be avoided, and a change that must touch it has to remove or move lines, not add them.

**Reason:** The server is the compatibility boundary (D-001) and already exceeds the size ceiling checked by `scripts/check_server_size.py`. Growing it makes the decoupling work (D-002 to D-015) harder to finish.

**Consequence:** PR #592 (Engine 2 Phase 4 slice 3, merged as `0a8f9090fbb218f6508b33d9e72ebedbcdc64fd1`) added the lens adapters to `navidrome_server.py`, which broke this rule. The follow-up (PR #593, merged as `8ef9eb6e1f6e7099ae0369f0bd2471872fab816b`) moved them to `discovery/lens_service.py`, wired from `app/api/discovery.py` (lens names and the manual "all" refresh) and `app/main.py` (daily refresh), and returned `navidrome_server.py` to its pre-PR-592 content. The size guard does not yet enforce this rule; enforcing it (a ceiling at the current line count) is a separate, owner-approved change.

## D-017 — Owned search state is an in-process index keyed by a Navidrome generation

**Decision:** Global search and library browsing read an in-process owned index in `discovery/search/`, built in the background from the library snapshot and a paged song inventory. Each build is keyed by a non-secret Navidrome generation counter in the settings store. The counter increments whenever the Navidrome URL, user or password changes, so a changed server's data is never served. A completed build replaces the previous index atomically; a failed or suspicious build keeps the last known-good index and reports `stale`.

**Reason:** Owned results must not wait on the network (SEARCH_CONTRACT section 2), and the library is large enough (12,097 songs) that a request-time scan would be too slow. A counter, rather than a hash of the password, keeps credential-derived values out of keys, logs and responses.

**Consequence:** The recommendation path still reads the unscoped library snapshot, so the generation rule covers search only. The owner accepted that gap as a deferred follow-up (SEARCH_CONTRACT section 11.4). Index state is per process; a restart rebuilds it from the snapshot.


## D-018 — Android playback streams directly from Navidrome

**Decision:** The Android app may play owned songs. Audio is streamed directly from Navidrome with the Subsonic credentials already stored on the device. The queue is kept on the device. Playback scrobbles to Navidrome through a per-device toggle that is on by default. The web UI stays without a player, and Librarian gets no stream or scrobble routes.

**Reason:** The owner chose direct access for the Android app (contract section 9, decision 3), so a proxy would add backend code and doubled bandwidth without a new security boundary. The review findings on PR #645 (ownership, stream lifecycle, scrobble duplicates, format allowlist) are carried into the Android contract in their Android form.

**Consequence:** `docs/ANDROID_PLAYER_CONTRACT.md` is the governing contract. `PRODUCT.md` and `ANDROID_CLIENT_CONTRACT.md` are amended. Playback needs a media foreground service, an exception to the earlier no-background rule that covers playback only. D-016 is unaffected. `docs/PLAYER_PROPOSAL.md` (PR #645) remains the web proposal and is not approved. Enabling scrobbling feeds the history that discovery reads.

## D-019 — Android lyrics come only from the owner's Navidrome

**Decision:** The Android app shows lyrics for the playing song inside the Now Playing sheet, read directly from Navidrome with the login already saved on the device (`getLyricsBySongId`, after a `getOpenSubsonicExtensions` check for `songLyrics`). Timed lyrics follow the music; plain lyrics are text. Lines are not tappable. Fetching happens only when the Lyrics view is opened, with a prefetch of the next song while it stays open. A small on-device cache (300 songs or 5 MB, refreshed at most daily, "none" kept 24 hours) is cleared at sign-out.

**Reason:** Lyrics text is copyrighted, so no outside service is used and nothing is logged, committed or sent anywhere except from Navidrome to the screen. A survey on the owner's server (2026-11-01) showed Navidrome 0.64.2 supports `songLyrics`, that lookups are slow (4.1 s average, 12.5 s worst on the local network) and that about one song in eight has none, so the design needs a loading state, a cache and "none" as a normal answer.

**Consequence:** `docs/ANDROID_LYRICS_CONTRACT.md` is the governing contract (approved by the owner on 2026-11-01). The web UI and Librarian are unchanged (D-016 untouched). `ANDROID_PLAYER_CONTRACT.md` points to it. Work runs in phases L0 to L4, each one PR except L0 (documentation, direct to `main`).

## D-020 — Android equalizer is the app's own audio processor

**Decision:** The Android app gets a 10-band graphic equalizer (31 Hz to 16 kHz, ±12 dB in 0.5 dB steps) implemented as a Media3 `AudioProcessor` in the ExoPlayer audio sink, not the platform `android.media.audiofx.Equalizer`. It has nine built-in presets and a Custom slot, automatic pre-gain with a soft limiter, and a true bypass. It is off by default, one curve applies to every output, and the setting is stored per device and kept at sign-out. No permission, third-party SDK or Librarian change is added.

**Reason:** The same sound on every phone and output, and a filter that is unit-testable in plain Kotlin like the rest of the player. The platform effect varies by maker, cannot be checked for clipping, and needs session tracking. The platform effect remains the fallback if the owner's phone shows a CPU or battery problem.

**Consequence:** `docs/ANDROID_EQ_CONTRACT.md` is the governing contract (approved by the owner on 2026-11-01, all defaults accepted). The web UI and Librarian are unchanged (D-016 untouched). Gapless playback and scrobbling must not change. Work runs in phases E0 to E4, each one PR except E0 (documentation). Crossfade, bass boost, normalisation, per-output profiles and curve import stay out of scope.

## D-021 — Android crossfade is a service-level overlap, chosen by a spike

**Decision:** The Android app gets an optional crossfade between songs, off by default, 1 to 12 seconds (default 5), equal-power, applied only to automatic song changes (manual skips stay instant). Consecutive tracks of one album stay gapless by default. The overlap uses two ExoPlayers with identical playlists, kept identical by a mirror wrapper, with the session's player swapped to the incoming one at the fade start (decided after the X1 spike on the owner's phone, 2026-11-01; the owner reported it sounds clean). A helper player that takes over the outgoing song was rejected because two players cannot be aligned on one song (position noise about 250 ms). Settings are per device and kept at sign-out. No permission, third-party SDK or Librarian change is added.

**Reason:** ExoPlayer plays one song at a time on one audio track, so a true overlap cannot be done inside the current single player, and Media3 1.11.0 is not known to offer one (to be confirmed in X1). The owner confirmed that gapless playback is seamless today, so the design must leave it untouched with crossfade off and for same-album joins, and must keep scrobbling, the equalizer and the notification honest.

**Consequence:** `docs/ANDROID_CROSSFADE_CONTRACT.md` is the governing contract (X0 started by the owner on 2026-11-01; its proposed defaults stand until overridden). The web UI and Librarian are unchanged (D-016 untouched). Work runs in phases X0 to X5, each one PR except X0 (documentation, direct to `main`); X1 is a spike that is not merged. Crossfade on manual skips, normalisation and automatic mix points stay out of scope.

## D-022 — The web UI offers nine themes and six Brut font pairs; Neobrut is an opt-in exception to the flat-depth rule

**Decision:** Settings > Appearance (web) offers nine colour themes and seven font pairs, chosen per browser and kept in `localStorage`. Themes: Dark (Ink, the default and unchanged; Vinyl; Nocturne), Light (Parchment, Gallery, Sleeve) and Neobrut (Brut · Cassette, Brut · Mint Desk, Brut · Night Shift). "Follow system" uses a Day theme (a light one) and a Night theme (a dark one). Fonts, independent of the theme: the Discair pair (Peace Sans / Open Sans, the default) and six Brut pairs: Baseline, Technical, Editorial, Modern, Poster shout, Swiss brut (each a title face, a body face and a mono face; the title face also sets rank numerals). The wordmark's i-dots take the theme's accent. The Android app has the same six Brut font pairs and, separately, its own twenty themes (D-022 does not port the app's themes to the web, and the web's themes are not the app's).

**Reason:** the owner asked for more personality and a light option. Themes and fonts only override the existing custom properties in `static/app.css` (`static/themes.css`), so components are not forked.

**Consequence:** (1) The Neobrut themes add outlines (`--bw`), hard offset shadows (`--brut-sh`) and a hover nudge. This is an **explicit, opt-in exception** to the flat-depth rule in `docs/archive/redesign/DESIGN_SYSTEM.md` section 4.1 (depth from ground steps, not shadows or borders); the rule still holds on every other theme. (2) Accent used as a text colour goes through `--accent-text`, which equals `--accent` on Ink and is a deeper shade where the accent is pale, so text stays at 4.5:1. (3) The Brut font files (`static/fonts/brut-fonts.css`, 22 woff2, about 440 KB) have their own 520 KB ceiling in `tests/test_fonts_and_icons_ui_contract.py` and are never preloaded; a browser fetches a face only when its pair is chosen, so a default install downloads none of them. The 180 KB ceiling on the default faces is unchanged. (4) `static/appearance.js` is a small synchronous script in `<head>` that applies the saved choice before first paint; there is no inline script. (5) The server is not involved: no endpoint, field or setting was added (D-016 untouched).

**Review fixes (2026-11-02, impeccable critique and mobile-design pass), same decision:** (1) Keyboard focus uses a `--focus` token: the accent, except black on the two pale Neobrut themes (Cassette and Mint Desk), whose accents were under 3:1; current-page marks and active underlines use `--accent-text`. (2) Album, artist and song names are never re-cased: a font pair that sets titles in capitals (Technical, Editorial, Poster shout) points the `--name-*` tokens at its body face (semibold), so "dEUS" stays "dEUS"; only section headings take the capitals. Technical's body is IBM Plex Sans (its numbers stay IBM Plex Mono) and its title scale is 0.8. (3) Vinyl's accent is cyan and Sleeve's teal, so the working accent is never the signature red; the muted text level is always stronger than the subtle one on every theme (a unit test). (4) The Neobrut hover nudge applies only on devices that can hover, so a tap on a phone does not leave a card lifted; Neobrut also outlines the artist hero and the search field and caps row rules at 2px. (5) Appearance pills: theme pills carry four colour dots, groups (Dark, Light, Neobrut) are spaced apart, and each font pill is set in its own face; on a phone the label sits above its pills. (6) `<meta name="theme-color">` follows the theme's top-bar colour. **Not done:** the hard shadow is still applied through an exclusion list of link-like buttons (`themes.css`), not an opt-in class, because an opt-in class needs a class on about 20 JavaScript-built buttons; the unit test pins the main link-like classes. The "Brut ·" prefix and the separate Baseline and Modern pairs stay, as the owner chose them.

**Neobrut component layer (2026-11-03, `neobrut.md`), same decision:** the Neobrut themes restyle their components after neobrutalism.com: a `--bw` outline, a small radius and a hard shadow (shadow-sm, half the offset, for small controls; the full `--brut-sh` for cards, groups and menus); a control lifts on hover (hover-capable devices only) and presses down into its shadow. On the web (`themes.css`, generated) the layer covers: input field (outline, shadow-sm, red border when `aria-invalid`), search field (one framed group with a ghost submit), button group (one frame, `--bw` seams, accent-tinted hover, the frame presses as one), button (including the Get control), toggle (`aria-pressed` fills with the accent), dropdown menu (the header menu and the phone More panel; items fill with the nav colour), tags (category and count badges primary, genre tags secondary), dialog (scrim is the text colour at 28%), carousel dots, navigation (the phone bar takes a top rule), progress bar (bordered track, solid fill), slider (the tile-size range: bordered track, square thumb), skeleton (bordered pulsing blocks), toast (notifications and the undo bar, whose action is a real button), switch (`.radio-switch`: accent track, square outlined thumb) and tabs (a bordered list, the active tab filled). Not applicable on the web, which has none of them: pagination, radio group (the Appearance pills are the owner's own design), sheet. **Android:** `ui/common/BrutalComponents.kt` holds composables with the names and parameters of Material's (`Button`, `OutlinedButton`, `FilledTonalButton`, `FilledIconButton`, `OutlinedIconButton`, `OutlinedTextField`, `DropdownMenu`, `AlertDialog`, `Slider`, `LinearProgressIndicator`, `SnackbarHost`, `ModalBottomSheet`, `FilterChip`) plus `BrutalTag`; call sites import them from `app.discair.ui.common` instead of Material (new code must do the same), and on a Classic theme each passes straight through to Material. Also restyled: the Home tag chip, the album quality tag, the library badge, the navigation island and the equalizer sliders. Not applicable in the app: skeleton (it has none), pagination, radio group and checkbox (it has none), carousel arrows (it swipes). Not done: the shadow of a dropdown or dialog is drawn inside its popup window, so it is clipped to the window; the mini-player's 2dp progress line stays Material (it is decorative).

**Review fixes (2026-11-03), same decision:** on the web the dashboard carousel's tinted panel fades to Ink's dark on every theme (`--slider-fade`, set on the light themes) and its featured slide keeps Ink's light text colours, so the bio, the artist name and the listener count stay readable on a light theme; under a Neobrut theme the carousel panel is a card (outline and shadow) and the dashboard genre tiles are filled with their hue, outlined and shadowed with black text. On Android see `android/DESIGN.md`, "Neobrut player, Home and notification".

**Web review fixes (2026-11-03, second pass), same decision:** (1) a very long carousel title (wide layout) runs on over the first, blurred thumbnail, capped at three lines, so the bio and info keep to their column with room left for the navigation buttons; the featured slide ignores the pointer except on its artwork and text, so the thumbnails stay usable; (2) the carousel's light text applies to its text column only, not the artwork side, so the action-group icons are no longer pale; (3) every icon takes its stroke width from `--icon-stroke` (default 1.75, unchanged; `icons.svg` was edited once by hand for this) and a Neobrut theme sets 2.3, with button icons in the text colour; (4) the artist back button, the quality tag (a white badge) and the Info/Reviews tabs (centred again) are Neobrut, and every select is as square as the other fields so its shadow is too.


## D-023 — Round 2 Neobrut: layouts that change composition, six layouts and sixteen themes

**Decision:** The owner approved six layouts, each in a limited set of palettes: on the web Tape Deck (Lime, Cobalt Reel, Tangerine Reel), Ledger Room (Ink Slate, Plum Archive, Paper Mono) and Crate Wall (Kraft, Mint Sleeve, Night Press); on Android Cassette Deck (Lime, Cobalt Reel, Tangerine Reel), Sheet Stack (Violet-orange, Acid Night, Daylight Sheet) and Sticker Wall (Peach-teal). The web gets nine new themes and Android seven. A layout rearranges the shell and the main pages (ruled playlists, tables, a mosaic wall with a drawer; a player card, a bottom sheet, a tile wall) while the pages, content and functions stay the same. Existing themes and the Ink default are unchanged.

**Reason:** round 1 (D-022) only changed colours and component skins, and the owner wanted themes that differ in composition. The layouts borrow from neobrutalism.com and stream/ui (Track List, Audio Player, Equalizer).

**Consequence:** (1) Web: a `layout` field on theme entries, `data-layout` on `<html>`, layout rules only in `static/layouts.css` under `:root[data-layout="…"]`, palettes as token sets in `static/themes.css`; layouts apply from 900 px up and the phone shell keeps its current structure. (2) Android: a layout field on a theme and a composition chosen per screen, with `Standard` for every existing theme. (3) The web UI still has no playback (PRODUCT.md): player-style pieces there show acquisition progress only. Android playback behaviour (D-018, D-020, D-021) is unchanged. (4) The Neobrut exception to the flat-depth rule (D-022) extends to these themes. (5) The governing document is `docs/BRUT_LAYOUTS_PLAN.md` (phases P0 to P7, palettes, acceptance, risks); reference mockups are in `docs/design/brut-layouts/`. Server code and the API are untouched (D-016). Rejected: Comic Issue, Comic Burst and the other palettes listed in the plan.

**Tape Deck (P1, 2026-11-03), same decision:** merged in PR #701 (`a4961c9`). The web gets `data-layout` (set by `static/appearance.js` from a `layout` field), `static/layouts.css` (loaded after `themes.css` on the main page only, every selector scoped, 901 px and up) and three light Neobrut themes, Tape · Lime, Tape · Cobalt and Tape · Tangerine, in the Appearance theme row. Tape Deck is a ruled tab strip, ruled playlist rows and shelves, rectangular search fields and a three-bar meter on downloading requests. Cobalt's accent was darkened to `#3d68f0` to pass AA with white text. The plan's dashboard deck column and `Ctrl K` hint were not built (see the plan, section 5).

**Ledger Room (P2, 2026-11-03), same decision:** merged in PR #702 (`d94667d`). Three light Neobrut themes (Ledger · Slate, Plum, Mono) and the `ledger` layout: an ink sidebar, ruled table-style rows with Owned/Missing/Queued status cells and an All/Missing/Queued switch (hides rows, never reorders), a breadcrumb, a summary strip counted from the acquisition list already loaded, genre folds on Artist Deep Dives, and Ctrl/Cmd+K to search in this layout only. Pagination, sort changes and real table header cells were not built (see the plan, section 5).

**Crate Wall (P3, 2026-11-03), same decision:** merged in PR #703 (`c6dbc43`). Three Neobrut themes (Crate · Kraft, Mint, Night; Night is dark) and the `crate` layout: a stamped label strip, a mosaic wall with a 2x2 hero and Owned/Missing/Queued stamps, shelf arrows, and the album window as a right-hand drawer with Get and a Not for me button (the row's own dismiss control) at its foot. This completes the web layouts (Tape Deck, Ledger Room, Crate Wall); the Android layouts follow.

**Owner rule on behaviour (2026-11-03), same decision:** a layout may change UI behaviour, not only appearance, where that serves the layout (for example the Cassette Deck's mini player and lyrics button), for its own themes only. The contracts underneath (API, playback, accessibility, no web playback) do not change. Recorded in the plan, section 2.

**Cassette Deck (P4, 2026-11-03), same decision:** merged in PR #704 (`95e7da3`). The Android plumbing is a `Layout` field on a theme (`Standard` for every earlier theme). The Cassette Deck themes (Tape · Lime, Cobalt, Tangerine) get a ruled navigation bar (Search, Home, Settings), a mini player, a ruled Home list with a live meter, and Now Playing as a player card with the queue under it and a lyrics button, applying the owner's behaviour rule.

**Sheet Stack (P5, 2026-11-03), same decision:** merged in PR #705 (`43159c7`). Three Sheet themes (Violet-orange, Acid Night, Daylight) and the Sheet Stack layout: a joined four-segment navigation group, "Today" plus a Requests list with status words on Home, and Now Playing as a bottom sheet with a vertical volume slider, a joined transport, a lyrics strip and the queue under it.

**Sticker Wall (P6, 2026-11-03), same decision:** merged in PR #706 (`ee9ff84`). One theme (Sticker · Peach-teal) and the Sticker Wall layout: a floating pill, Home walls of tilted tiles with New and Missing stickers, and Now Playing as a poster whose equalizer summary opens the real Equalizer and whose crossfade switch is the real setting. All six layouts are now built; the items skipped before the behaviour rule are being revisited.

**Revisit (2026-11-03), same decision:** merged in PRs #707 and #708 (`fff47de`). Under the behaviour rule the Tape Deck got its deck, the Ledger Room its ruler, pagination, Library table and dashboard genre accordion, all web layouts Ctrl+K, and the Android Cassette Deck its four-cell bar and ruled seek bar. Real `th` cells, the Crate Wall 2-column step and the hover card's owned count stay unbuilt, with reasons in the plan.
