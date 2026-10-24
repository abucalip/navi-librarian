## 2026-10-24 — Lens storage test isolation fix (PR #604)

- **Merged:** PR #604, squash commit `102a2d9e842d9887b15c7ce7fe266a63c5c0d056`, from CI-green head `6b0db0b5feabec357dbf864caab632e8173fd90f`.
- **Cause:** the routes test called `POST /api/discovery/all/refresh`, which starts a real lens refresh thread; that thread could still hold the module-level refresh lock when the lens storage tests ran, so they reported `already_running`.
- **Change:** the routes test patches `lens_service.start_refresh` and asserts the call. No production code changed.
- **Verification:** the lock was free before the routes tests and held after them; the lens test modules passed together in three consecutive runs. CI passed on the head: compile, container smoke, full unit suite and image build, validate-container.
- **Not done:** no publication, deployment or runtime verification.

## 2026-10-24 — Engine 2 Phase 5 closed (PRs #600 to #603)

- **Merged:** PR #600 (`bb6cb97`), #601 (`f60268b`), #602 (`46d8cb2`), #603 (`b1454b8`), each squash-merged from a CI-green head.
- **Delivered:** lens-tagged albums and per-lens saves/dismissals; a read-only `GET /api/discovery/lens-feedback`; acquisition request metadata kept on success statuses; per-lens acquisition request and status counts.
- **Closed by owner decision:** play/download attribution dropped; no UI display of the summary. The read API is the only consumer.
- **Limits:** counts are current stored state, not history; pre-#602 jobs are not attributed; no quality claim.
- **Known issue (not fixed here):** `tests/test_discovery_lens_storage.py` fails in some unittest orderings with `already_running` from the refresh lock. CI's full suite passes; the issue predates Phase 5.
- **Not done:** no publication, deployment or runtime verification.

## 2026-10-24 — Engine 2 Phase 5 feedback read API (PR #601)

- **Merged:** PR [#601](https://github.com/abucalip/navi-librarian/pull/601), squash commit `f60268b17d2e28f47e08fbcbc57f3667ec5d6694`, from reviewed head `171efc4a7a074c093ccb6da4cc92964abd4bd44c`.
- **Changes:** Added read-only `GET /api/discovery/lens-feedback` and `lens_service.feedback_summary()`, reusing the Phase 5 summary helper from PR #600. The route is registered before `/api/discovery/{list_name}` so the catch-all cannot shadow it. When `engine2_lens_lists_enabled` is off, the service returns `{"disabled": true, "lenses": {}}` without reading feedback rows; enabled mode reports current per-lens save/dismiss counts and save rate.
- **Review/regressions:** Reviewed all four changed files, route ordering, service setting gate, existing API contracts, and error path. Regression coverage verifies disabled mode performs no feedback read, enabled mode counts correctly, the route resolves rather than hitting the list catch-all, and the route inventory is updated.
- **Verification:** All required CI workflows passed on exact PR head: Python syntax/acquisition-safety (`40122515028`), Docker packaging including the full unit suite and image build (`40122515044`), container runtime smoke (`40122514974`), and non-publishing multi-architecture validation (`40122514971`). Release-workflow validation succeeded (`40122514987`) with publishing skipped. PR author reports 33 focused tests passed; no separate local full-suite run was performed. Backend-only; no browser test required.
- **Limits/status:** Read-only API only; no UI, provider call, publication, deployment, or independent runtime verification. Counts reflect current feedback state rather than historical event totals. No quality claim is made. Next action: determine whether and how to consume the summary in the UI, while keeping any quality evaluation separate from raw counts.

## 2026-10-24 — Engine 2 Phase 5 groundwork (PR #600)

- **Merged:** PR [#600](https://github.com/abucalip/navi-librarian/pull/600), squash commit `bb6cb97062fece9236f964802f9ef705c99809ea`, from reviewed head `2a9b856d0f23b4edbe87fa8a89a088f86cedd22e`.
- **Changes:** `discovery/lens_lists.py` includes each album's lens name; new pure `discovery/lens_feedback.py` counts current album-scope `for_me` saves and `not_for_me` dismissals per known lens and reports a save rate when actions exist. Unknown lens metadata, non-album scopes, and other statuses are ignored.
- **Review and regression coverage:** reviewed all four changed files and existing feedback API/payload contracts. New tests cover per-lens counts/rates, empty lenses, invalid/missing lens metadata, non-album scope, and unsupported statuses; list payload regression verifies the `lens` field.
- **Verification:** GitHub CI on exact PR head passed all four required workflows: Python syntax and acquisition-safety checks (`40121772726`), Docker packaging including the full unit suite and image build (`40121772668`), container runtime smoke (`40121772704`), and non-publishing multi-architecture image validation (`40121772683`). The PR author reports 147 focused tests passed; I did not run a separate local full suite. No browser test was needed for this backend/payload-only change.
- **Limits/status:** the summary helper is intentionally not wired into a route or UI yet; Get/play/download attribution and any quality claim remain out of scope. No publication, deployment, or runtime verification. Next action: implement the read/API integration for the summary with tests, then evaluate what feedback events can be reliably attributed to a lens.

## 2026-10-24 — Phase 4 live run, browser checks, and Last.fm username control

- **Last.fm username control (PR #599, branch `feat/lastfm-username-setting`, head `2fad9b2`):** the Settings Last.fm panel has a username field, saved with the API key; blank clears the stored value so `LASTFM_USERNAME` applies again; invalid usernames are refused before any write. `navidrome_server.py` keeps 2457 lines (adapter signature only). Focused tests: `tests.test_service_settings`, `tests.test_settings_ui_contract`, `tests.test_settings_routes`, `tests.test_discovery_history_fetch`, `tests.test_lens_lists_ui_contract`, `tests.test_discovery_lens_pool_gatherer` (95 tests, pass). CI green on `2fad9b2`: compile `40118706314`, test-and-build `40118706315`, container-smoke `40118706301`, validate-container `40118706294`, validate-release-workflow `40118706303` (publish skipped).
- **Merge not done:** `gh pr merge 599 --squash` was refused by the permission check ("Merge Without Review"). The PR is open and clean; the merge is for the owner or a permitted action.
- **Setting:** `engine2_lens_lists_enabled` is `true` in the owner's `local-test/data` and in the isolated run copy. The code default stays `false`. The setting has no Settings control; it was written to `discovery_settings` directly.
- **Live run (isolated copy, port 8092, scratch data directory, throwaway account, slskd disabled, Navidrome and providers live):** a manual "all" refresh stored Repeated tracks 8, Deep cuts 10, Obsessions 9. A reload kept the Last.fm username.
- **Artwork (`/api/artwork`, 27 albums):** 26 with an image, no provider errors or retry flags. The one miss, "(sic)monic" by "Somnambulist", is a name mismatch: Deezer lists the artist as "Sicmonic", and that query returns the cover. The earlier "empty artwork on every row" note did not reproduce; its cause is unknown.
- **Browser (desktop 1280 px, phone 390 px):** 0 console errors, 0 failed responses, no horizontal overflow. Keyboard: 14 focus stops reached the row actions, each with a visible 2 px outline. Save worked; Not for me removed one album server-side (8 to 7, `dismissed: 1`). Not run: Get (it starts an acquisition request), screen-reader output, and a reduced-motion check beyond loading the page.
- **Note:** the browser run used Chrome through Playwright from a scratch virtualenv outside the repository. Port 8091 was already held by another uvicorn process (started 2026-10-22); it was not touched.
- No publication or deployment.

## 2026-10-24 — Lens artwork investigation (Phase 4 item 3): no code defect found

- Path traced: lens rows call `buildRecommendationRow` → `attachArtwork` with the stored `artist` and `album` (`static/app.js`), then `/api/artwork` (`app/api/metadata.py`), which runs a Deezer album search with an artist-photo fallback. Lens rows use the same loader as the other rows; no lens-specific skip was found.
- Handler check (local, no list data): `album_artwork(artist='Miles Davis', album='Kind of Blue')` returns a Deezer cover; a nonsense name returns `artwork_url: None` with no `retryable` flag. Deezer's album search answered from this environment.
- Failure handling: a provider exception sets `retryable` and is not cached, so an outage cannot leave a row blank for five minutes.
- Conclusion: the empty rows are most likely "no Deezer match with score 9 or more, and no exact artist photo" for these albums. This is not confirmed: the local database has no lens rows (the live run used an isolated copy), and no lens album names were available to query. Confirming needs the artist and album pairs from one stored lens list, run through the handler.
- No code or test change. Nothing published or deployed.

## 2026-10-24 — Phase 4 closeout: what is left

- Built and merged: Phase 4 slices 1 to 4 (PRs #590 to #595), the dismissal read filter and Daily picks rename (#596), the dynamic history walk with its Last.fm error fix (#597), and the ListenBrainz recent-listens paging fix (#598).
- Left: the owner's decision on `engine2_lens_lists_enabled`; the Last.fm account Settings control (parked); browser checks for keyboard, focus, actions, reduced motion and screen readers; empty artwork on lens rows; a quality measurement of the lists; Phase 5. No publication or deployment in this entry.

## 2026-10-24 — Deeper lens history (PR #597); correction to the live-run entry; PR #596 review fixes

- Correction: the live-run entry below says the history was capped at 100 listens by the ListenBrainz page limit. That was wrong. A `min_ts` query returns the oldest page after the bound in ascending order, and the client paged backwards from there and stopped, so the one-year read kept only the oldest two days of the year. `recent_listens` (Discover, `days=30`) has the same behaviour and is not changed; it needs an owner decision.
- PR #597 (`feat/engine2-dynamic-history`): dynamic 365-day walk back from now, to a 13-year floor, until 2000 usable listens (starting value). Windows alternate between ListenBrainz and Last.fm, a failing source is answered by the other, duplicates counted once, windows at the 5,000-listen page cap flagged. Tests: `tests/test_discovery_history_fetch.py` (14). Live: 6,866 listens over 13 windows; all three lenses built; the 2014 window reached.
- PR #596 review (`d6261439`): malformed cache entries no longer make an unchecked read fail; two regression tests. Browser check on that head: pass at 1280 and 390 px.
- Not merged, both PRs open. No publication or deployment.

## 2026-10-24 — Daily picks dismissal filtering (PR #596)

- Re-reviewed PR [#596](https://github.com/abucalip/navi-librarian/pull/596) after the robustness fix. The unchecked-cache response now drops malformed non-mapping entries safely and handles a non-list `albums` field; regression tests cover both-checks-unavailable and malformed-cache cases.
- Final PR head: `d62614393244c4ee33726d9401704c339edd5440`. Required workflows passed on that exact head: Python syntax (`40111186933`), Docker packaging/full unit suite/image build (`40111186947`), container runtime smoke (`40111186946`), and validation-only multi-architecture image validation (`40111186939`). Release workflow run `40111186943` reported success; publication/deployment status is not inferred from this.
- Manual UI/browser testing was explicitly waived by the owner and was not performed. Squash-merged as `3e2e8bc2c3e3882596fc1a398706e1b9f3f72f5e`. No deployment or runtime verification claimed.

---

## 2026-10-24 — Daily picks: live run, browser check, dismissals (PR #596)

- Opened PR #596 (`feat/daily-picks-dismissals`): lens lists drop "Not for me" albums and artists at read time (`discovery/list_payload.py` `dismissed_predicate`, `discovery/lens_storage.py` `serve_lens_list`), and the read filter counts them as `dismissed`. Ranks restart at 01 after a removal (follow-up commit `f3f88bdb`). The page and copy are renamed "Daily picks". Focused tests: the lens storage tests (33), list payload, lens list, pool, lens, and metric tests, and all UI contract tests; full suite left to CI. Open; not merged.
- Live run on an isolated copy of the local data directory, port 8192, with live providers. The owner's running instances (other ports) were not used or changed. One lens build selected 10 Deep cuts albums from a pool of 60. Repeated tracks and Obsessions stored nothing: the ListenBrainz history fetch returned 100 listens for the 365-day window, too few to produce seeds. Details and aggregates in `docs/engine2.md`, Phase 4.
- Browser check (Chrome via Playwright, scratch virtualenv, not in the repository) at 1280 px and 390 px: navigation, the Daily picks page, toggle state, list semantics, and rows rendered; no console or page errors, no failed responses, no horizontal overflow. Not covered: keyboard and focus, the action controls in the browser, reduced motion, screen readers. Lens artwork was empty and was not investigated.
- Owner decisions recorded: 10-minute library cache stays; no daily acquisition cap; the name Daily picks.
- No publication, deployment, or merge of PR #596 in this entry.

## 2026-10-24 — PR #595 merged; Engine 2 Phase 4 Daily lists UI

- Re-reviewed exact PR head `01ca4428c7c07dda111086ea4942124f2ef24172`. The SVG sprite now has valid attribute spacing, and `tests/test_lens_lists_ui_contract.py` parses the sprite as XML. The Daily lists UI uses the shared recommendation row, ignores stale lens responses, reports disabled/empty states as status text, and routes dismiss feedback back to the active lens.
- The diff also removes the ranked-row hover stripe and creates the album artwork image in JavaScript rather than shipping an `<img>` without a source; contract tests explicitly cover these choices.
- All required workflows passed on the exact head: Python syntax (`40108409642`), Docker packaging/full unit suite/image build (`40108409602`, including `Run unit tests`), container runtime smoke (`40108409585`), and validation-only multi-architecture image validation (`40108409651`, publishing paused). Release workflow validation (`40108409597`) passed with the `publish-release` job skipped.
- Squash-merged PR #595 as `9ac74da768e93b592ac070814b69a6a7ffa4f964`. The owner waived manual browser testing; no browser check was performed. No live provider run, publication, deployment, or runtime verification. `engine2_lens_lists_enabled` remains off by default.
- Next: perform the waived browser checks against a pinned deployed/test environment when appropriate; otherwise continue the planned Engine 2 Phase 4 follow-up.

## 2026-10-24 — Re-review, full CI suite, and merge PR #594

- Reviewed exact PR head `b79ff64cf65e51bfa38e8203b722961ff0be077c`. The manual `all` discovery refresh now starts a lens-list build through `discovery/lens_service.py:start_refresh` in a daemon thread; other list refreshes do not trigger it. The refresh shares the daily loop's lock, and the existing setting gate means the feature remains inert while `engine2_lens_lists_enabled` is off. Regression tests cover the `all` trigger, non-`all` behavior, and execution on a separate thread. No blocker found in the changed code.
- All required workflows passed on the exact PR head: Python syntax/acquisition safety (`40106635627`), Docker packaging/full unit suite/image build (`40106635948`, including successful `Run unit tests` and `Build Docker image` steps), container runtime smoke (`40106635598`), and validation-only multi-architecture image validation (`40106635703`, non-publishing). Release workflow validation (`40106635611`) succeeded; its `publish-release` job was skipped. Per repository workflow policy, the full unit suite ran in CI, not manually.
- Squash-merged PR #594 as `5299ac03f04c8718a64adc1c557c09b367f7d266`; GitHub confirms the PR is closed and merged. Updated `docs/PROJECT_STATUS.md` to record the merge and set the next action to define the bounded Phase 4 slice 4 (UI) scope.
- Lens lists remain behind the default-off setting. No live provider run, publication, deployment, browser check, or runtime verification was performed.

## 2026-10-24 — PR #593 merged; manual lens trigger in the app layer

- PR #593 (move the lens adapters out of `navidrome_server.py`) squash-merged as `8ef9eb6e1f6e7099ae0369f0bd2471872fab816b`. Its review fixes: the read path checks `engine2_lens_lists_enabled` before any store or library access, with regression tests for the disabled path (service and route) and the enabled path.
- Owner decisions: the daily loop's hourly retries while a lens list is missing or not from today are acceptable; the manual trigger goes in the app layer.
- Manual trigger: `POST /api/discovery/all/refresh` also starts a background lens build (`discovery/lens_service.py:start_refresh`), which returns at once and shares the daily loop's lock. Other list refreshes do not start it. Tests cover the trigger, the other refreshes, and background execution.
- `navidrome_server.py` is unchanged by this work (zero diff against its pre-PR-592 content, D-016).
- Next: define the bounded slice 4 (UI) scope before implementation.

## 2026-10-24 — Engine 2 Phase 4 slice 3 merged; server module rule

- PR #592 (storage and serving for the daily lens lists) squash-merged as `0a8f9090fbb218f6508b33d9e72ebedbcdc64fd1` from exact head `09fb6e8d907d49fdefad4925a6b91c2e394abe5d`. All four required workflows passed on that head. Feature stays off by default (`engine2_lens_lists_enabled`); no live provider run, publication or deployment.
- Owner rule recorded as D-016 (`docs/DECISIONS.md`) and in `docs/DEVELOPMENT_WORKFLOW.md`: `navidrome_server.py` takes no additions; new code goes in new modules.
- Debt: PR #592 added the lens build and read adapters to `navidrome_server.py` before the rule existed. They must move to a new module before slice 4. The size guard does not enforce the rule yet.
- Docs updated: `docs/engine2.md` (slice 3 status and debt), `docs/ACTIVE_WORK.md`, `docs/PROJECT_STATUS.md`.
- Next: move the adapters out of `navidrome_server.py`, then slice 4 (UI).

## 2026-10-24 — Engine 2 Phase 4: owner decisions on the slice 2 review

- The owner approved: the setting name `engine2_lens_lists_enabled`; about three MusicBrainz release searches per lens (25 release groups per query) in place of the planned one; the per-run history-artist genre prefetch (cached 90 days) and the one-time MusicBrainz genre vocabulary load (about 25 requests when its cache is empty); the missing attribution trailers on the PR #591 feature-branch commit (the squash-merge body carries them).
- Day boundary decided: the day rolls over at 4am local time. Slice 3 must derive the lens-list `day` (and the radio scope) from the local time minus four hours; slice 2 currently takes `day` from the caller.
- Still open: how often the Navidrome library artists are refreshed for the known-artist check (the 10-minute snapshot cache stays for now).
- Documentation only; no code, tests, provider calls, publication or deployment.
- Next: slice 3, storage and serving, in a new session.

## 2026-10-24 — PR #591: Engine 2 Phase 4 slice 2, the pool gatherer

- PR #591 squash-merged as `cca42e3cfde534571d319206eff8ab4fa0c461ff` from exact head `3a7ab611c5cdca432a4ebf3769f1e756de719cb5`. All four required workflows succeeded on that head: Python syntax check (`40104361233`), Docker packaging (`40104361217`; `test-and-build`, including `Run unit tests` and `Build Docker image`, passed in CI), container runtime smoke (`40104361193`), and validation-only image validation (`40104361177`, publishing paused). Unwired; no publication or deployment.
- Added `discovery/lens_pool_gatherer.py`: `gather_lens_pools(listens, *, day, providers, headers, lastfm_api_key, settings_read)`. For each lens in `LENS_LIST_ORDER` it runs `run_deep_cuts_tag_supply` with the lens name and the ISO day as the radio scope, then gathers album listeners (MusicBrainz release search and Last.fm `album.getInfo`, capped at 60 Last.fm lookups per lens, artist lookups skipped), artist genres (one ListenBrainz artist batch per lens, cached), and fallback tags for pool artists with fewer than two genre tags. The output keys match the inputs of `build_lens_lists`.
- Setting `engine2_lens_lists_enabled` (`settings/service.py`, `engine2_lens_lists_enabled_value`), default off, boolean only. When off the gatherer returns `{"status": "disabled"}` before any provider call. No route, recommendation path, personal list, or history/cooldown reads or writes it.
- Starting-note fixes: `fetch_release_mbids` retries a release-search page that is rate-limited (429), 5xx, or dropped, after an 8 s pause, up to three tries (`RELEASE_SEARCH_ATTEMPTS`); other client errors are not retried, and successful pages make the same calls as before. `usable_listens` (`discovery/lens_lists.py`) drops listens stamped before 1971, and the gatherer applies it before building any profile or history-artist set. `resolve_popularity` gains `with_artist_listeners` (default `True`, unchanged).
- Tests (stubbed providers, placeholder data, no network): focused runs only, all passing locally: `test_discovery_lens_pool_gatherer` (10 new), `test_discovery_mbid_popularity` (25, including 5 new retry and album-only tests), `test_discovery_lens_lists` (29), `test_service_settings` (20, including the new setting test), `test_discovery_deep_cuts_supply` (11), `test_discovery_lenses` (27). `scripts/check_server_size.py` and `scripts/check_app_legacy_imports.py` passed. The full unit suite was not run locally; CI ran it on the exact head. No live provider calls.
- Budget notes, to confirm with the owner: `fetch_release_mbids` batches 25 release groups per query, so a 60-album pool costs about three release searches per lens, not the one in the approved plan. History artists are prefetched for genres on each run (cached 90 days, so this costs calls on first run or after expiry). The fallback vocabulary (MusicBrainz genre list, about 25 requests) loads once per run when its 90-day cache is empty.
- Open: the setting name is a draft choice for the owner to confirm; the day boundary (local or UTC) and the library-refresh rate are still open; slices 3 (storage and serving) and 4 (UI) are not started.
- Next: slice 3, storage and serving, in a new session.

## 2026-10-24 — PR #590: Engine 2 Phase 4 slice 1, the pure lens-list builder

- PR #590 squash-merged as `eadbd8a1f7b3515ffbed6ec65d4b34e95adaedf2` from exact final head `29659aea4c6b0a159db72a6b546a8b428e4746d0`. The builder was written by a delegated agent from the approved plan; the owner's follow-up decision (below) was added as a second commit on the same branch. All four required workflows succeeded on the final head: compile (`120898813524`), test-and-build (`120898813251`), container-smoke (`120898813582`), validate-container (`120898813244`). Local checks were focused tests only: the agent ran 151 lens-related tests and a 609-test keyword-filtered subset on the first head; the follow-up ran 84 and a 612-test subset. The full suite ran in CI. Unwired; no publication or deployment.
- Added `discovery/lens_lists.py`: `build_lens_lists(pools, *, day, popularity, artist_tags, library_by_title, fallback_tags, known_artist_mbids, library_artist_mbids, seeds, lenses, count)` takes precomputed pools per lens, merges the fallback tags after the genre tags, builds candidates with `build_allocation_inputs`, runs each lens's own gates through `run_lens`, and returns one JSON-serialisable payload per lens (lens, label, day, requested, albums, seed tags, pool size, skipped entries, checked count, decisions by status). It reads no clock and makes no provider calls; an entry without an album title or primary artist is skipped and counted. Helpers: `lens_seed_queries` (seeds for all three lenses; Deep cuts from the densest 30-day window with flat weights, or all recent activity when the history is shorter, after dropping listens stamped before 1971), `history_artist_mbids`, `merge_artist_tags`.
- `discovery/lenses.py`: `partition_lens_pools` partitions separately gathered pools so one lens cannot pick from another lens's supply; `partition_lenses` delegates to it with unchanged behaviour. Owner decisions on review: lens order Repeated tracks, Deep cuts, Obsessions; the Deep cuts seed window above; known artists do not count against the 60-candidate check limit. The selection now rejects an unowned album by a known artist as `artist_already_known` without using a check (owned albums still count), so `checked_count` is lower than before for pools with known artists.
- Tests: new `tests/test_discovery_lens_lists.py` (29 tests, placeholder data only: partitioning across lenses, known-artist exclusion by library name, library artist MBID and history MBID including a same-name-different-MBID case, fallback tags rescuing a candidate, empty pools, determinism, serialisability, bad input) and additions to `tests/test_discovery_lenses.py`.
- Limits: a local run of the builder on saved real-history pools (aggregates only) produced 6 seeds per lens and about 16 to 17 known artists excluded per lens but no finished list, because those saved files carry no album listeners or genre tags; end-to-end behaviour on real data is unchecked until slice 2 gathers full pools. Where the history is read from at runtime, the day boundary, the setting name, the library refresh rate and the UI wording remain open.
- Next: slice 2, the pool gatherer, with the MusicBrainz release-search retry and the 1970-timestamp fix noted in `docs/engine2.md`.

## 2026-10-24 — Engine 2 Phase 4 plan approved

- The owner approved the Phase 4 plan (precompute and serve the lens lists) with these decisions: the first lenses are Deep cuts, Repeated tracks and Obsessions; the daily provider budget is approved (about 25 s and roughly 6 radio calls, 1 batch POST, 1 release search and 40 to 60 Last.fm lookups per lens); one list of 10 per lens per day, no "next list"; lens lists keep their cooldown apart from the existing recommendation history and cooldown; everything sits behind a setting that defaults to off.
- The plan, its four slices (pure list builder, pool gatherer, storage and serving, UI), the open questions and the starting notes for the next session are in `docs/engine2.md`, Phase 4. No code was written; nothing is wired into runtime; no publication or deployment.
- Next: slice 1, the pure list builder, in a new session.

## 2026-10-24 — Engine 2 Phase 3 closeout: tier fall-through, albums per seed, merges

- Merges: PR #588 (Last.fm fallback genre tags, `discovery/artist_tag_fallback.py`) merged as `c2c346da406df79803405824929b99cf55bff332` from head `d0778412367e21a4652425c2c9bf74ce601c2966`, on which all four required workflows (compile, test-and-build, container-smoke, validate-container) were successful before the merge; PR #589 (10 albums per seed in the Deep cuts radio tiers) merged as `972912f`. This corrects the entry above, which was written before the #588 merge and says it was unmerged and that the merge was blocked. Both are unwired; no publication or deployment.
- Tier fall-through, measured (owner-approved live runs, one listener, aggregates only): fetching the 75 to 100% band for every seed in addition to the 50 to 75% band doubled the pool (30 to 59 albums for Repeated tracks, 30 to 55 for Obsessions) but added only one selected album per lens (7 to 8 and 4 to 5), because the deeper band mostly returned known artists and albums outside 300 to 50,000 listeners. Fall-through is unchanged: the second band is tried only when the first returns no album for a seed.
- Albums kept per seed, one radio draw each (the radio is redrawn per run, so about 2 of noise): 5 gave 7 (Repeated tracks) and 8 (Obsessions) selected of 10; 10 gave 9 and 9; 15 gave 5 and 7, because a pool over 60 exceeds the selection's limit of 60 checked candidates (29 candidates not considered in one run). The radio returns 20 recordings per call, so keeping more costs no extra radio or batch calls. After #589 (unpatched supply, 60 albums per lens, none from the tail): Repeated tracks selected 8 of 10 without the fallback tags and 10 with them; Obsessions selected 10 of 10 either way.
- Fallback tags: the Last.fm tags restricted to MusicBrainz genre names brought 41 of 95 untagged history artists to two or more tags (raw Last.fm tags reach 71 but include non-genres); in the lens runs the fallback extended 3 to 5 artists per lens. Tag quality for ranking and list quality were not judged.
- Limits: one listener; single radio draws; fallback tags merged by the harness, not by pipeline code; the radio band that supplied each album is not recorded per candidate (not needed while the radio supplies everything); all of it is unwired.
- Phase 3 is complete. Not Phase 3: wiring the lenses, the known-artist inputs and the fallback tags into a precomputed, daily-served pipeline is Phase 4. Next: a Phase 4 plan for the owner's approval.

## 2026-10-24 — Engine 2 Phase 3: live runs of Repeated tracks and Obsessions with the radio working and the tag fallback

- Owner-approved, read-only live runs on one listener's history, from the branch of PR #588 (the fallback was not yet merged; the owner's merge instruction could not be carried out by the agent because the merge command was blocked). Throwaway harness and data outside the repository; aggregates only. Each lens: seeds, `run_deep_cuts_tag_supply` (lens name and day as the radio scope), album listeners by one MusicBrainz release search plus Last.fm lookups, genres by one ListenBrainz artist batch, the Last.fm fallback tags (vocabulary: the MusicBrainz genre list, count 10 or more), the Navidrome library (1,739 albums) and the listening-history artists as known artists, then the lens selection for a list of 10.
- First run in this series where the radio worked: every seed returned 5 albums from the 50 to 75% band, 30 albums per lens, none from the tail, no failures. The whole run took 22 s (Repeated tracks) and 21 s (Obsessions), against 100 s or more in the earlier runs that fell back to the tail.
- Repeated tracks: without the fallback tags 4 were selected; with them 6 (8 artists had fewer than 2 genre tags, the fallback extended 3, leaving 5; candidates rejected for too few tags fell from 5 to 3). Of the 30 albums: 9 by known artists, 4 already owned, 7 outside 300 to 50,000 listeners, 1 per-seed cap, 3 too few tags. The raï and desert blues seeds produced no selection: their radio candidates were all artists already in the library or the history, or had too few tags.
- Obsessions: 5 selected without the fallback and 6 with it (5 artists extended, artists with fewer than 2 tags 5 to 1). Of the 30 albums: 13 by known artists, 10 outside 300 to 50,000 listeners (broad tags return well-known albums), 1 with unknown listeners.
- Reading: with a working radio both lenses fill 6 of 10, not 10. The limits are the known-artist exclusion (a third to a half of the radio's candidates are artists the listener already has), the audience ceiling for broad tags, and a pool of only 30 albums. Tier fall-through to the 75 to 100% band happens only when the 50 to 75% band returns no album for a seed, not when every returned album is rejected downstream, so a seed whose candidates are all known artists never reaches the less popular band.
- Limits: one listener and one day's radio draw (answers are fixed per lens and day); the fallback tags were merged by the harness, not by pipeline code; tag quality and list quality were not judged.
- Next: the owner merges PR #588; decide whether tier fall-through should consider downstream rejections or whether the pool needs more albums per seed; wiring is Phase 4.

## 2026-10-24 — Engine 2 Phase 3: Obsessions definition approved

- The owner approved the Obsessions lens definition after PR #587 merged: seeds from artists with at least 20 listens, 70% or more of them inside one 30-day span; the broad seed tags are kept as they come (no dominant-tag or generic-tag filter); the Deep cuts gates apply (album listeners 300 to 50,000, at least 2 artist tags, one album per artist, at most 2 per seed, owned albums and known artists excluded). The approval reached `main` as a separate docs commit because it was made after the PR's squash merge; the draft wording in `docs/engine2.md`, `ACTIVE_WORK.md` and `PROJECT_STATUS.md` is replaced.
- The lens remains unwired and outside the default lens order. No code, provider calls, publication or deployment.
- Open: a tag source or an exception for artists with no genre tags; a live run of Repeated tracks and Obsessions with the radio path working (needs owner approval).

## 2026-10-24 — Engine 2 Phase 3: Repeated tracks lens, live runs and owner decisions

- Owner-approved, read-only live runs of the Repeated tracks lens on one listener's history, with throwaway harnesses and data outside the repository; aggregates only. Seeds: the six tags in the lens catalog. Supply: `run_deep_cuts_tag_supply` with lens `repeated_tracks`; album listeners by one MusicBrainz release search plus four parallel Last.fm lookups; genres by one ListenBrainz artist batch.
- Run 1 (before PR #585): the lens returned 23 albums in 96 s, all from the MusicBrainz tail: five radio calls were dropped as stragglers or failed on the connection, so the radio tiers added nothing, and the most distinctive seed tag returned nothing after a connection error. Album listeners were found for 21 of 22. Selection reached 5 of 10: 8 rejected for fewer than 2 artist tags, 7 for album listeners outside 300 to 50,000, 2 for unknown listeners, 1 for the per-seed cap. One selected album was by an artist in the listening history, which showed that the Deep cuts selection checked album ownership only and did not exclude known artists.
- Navidrome check (PR #585): the library has 1,739 albums by 694 artists, fetched in 0.4 s. `getArtists` returns a MusicBrainz ID for 311 of 730 artists; albums carry `artistId`. With the known-artist exclusion and a tag minimum of 1, the same pool reached 5 of 10 again: 2 candidates rejected as known artists, 2 as already owned, 1 held for ownership review. Five candidates had no genre tags at all, so lowering the minimum to 1 rescued only 2 of the 8 that the minimum of 2 had rejected. After the MBID-aware match (same name with different artist MBIDs is not the same artist) the exclusion decisions were unchanged; the Last.fm lookups failed on every attempt in that last rerun, so its final list was not compared.
- Limits: one listener; two runs on one pool (the radio path was never exercised for this lens); no library ownership check in run 1; the 5 selected albums were not judged for quality and one title looked like possible junk the gates cannot catch.
- Owner decisions (2026-10-24): the Repeated tracks gates are approved (album listeners 300 to 50,000, one album per artist, at most 2 per seed, known artists excluded); the tag minimum of 1 is dropped, so the lens returns to the Deep cuts minimum of 2 (code revert to follow); Obsessions becomes a lens, definition to be written; the radio-path secondary-type fix is skipped; another tag source or an exception for artists with no genre tags is to be explored.
- Tail follow-up: the owner confirmed on 2026-10-24 that the MusicBrainz tail runs daily, so no separate repeat-run test of the tail is planned. The code revert of the tag minimum is PR #586.
- Next: revert the tag minimum for Repeated tracks, write the Obsessions definition, explore the no-tag candidates, and rerun the lens live with the radio path working (needs owner approval).

## 2026-10-24 — PR #587: Obsessions lens and seed builder

- Reviewed the complete five-file diff at `fedd943ee214354ab75b6e880bdde1851860113e`; no blocking correctness or compatibility issues found. `obsession_seed_queries` reuses `burst_artist_weights` and the established supplementary-tag query shape. Tests cover burst qualification, thresholds/limit, empty and untagged inputs, and invalid arguments. `OBSESSIONS` reuses the Deep cuts selection gates, including known-artist exclusion, is registered under its own name, and remains outside `DEFAULT_LENS_ORDER` so default partitions/runtime behavior are unchanged.
- All four required CI workflows passed on the exact PR head: syntax (`40094978423`), Docker packaging/full unit suite/image build (`40094978481`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40094978473`), and validation-only multi-architecture image validation (`40094978442`, publishing paused). No separate agent-run full suite per workflow policy.
- Squash-merged PR #587 as `a97cdc0363cb324f9005aa21fa3c691843eadf17`. The Obsessions definition is still a draft pending owner approval; the lens is not in the default order and is not wired into runtime. No publication, deployment, or runtime verification.

## 2026-10-24 — Engine 2 Phase 3: history profiles through the real seed selection

- Offline check, no provider calls: the merged-branch profile helpers (PR #583) and the existing `select_supplementary_tag_queries` over one listener's full ListenBrainz history (40,798 listens, 36,231 with an artist MBID through the `mbid_mapping` fallback) and cached genre tags for 504 of 599 artists. Aggregates only; the data and harness stay outside the repository.
- Profiles and the six seed tags each produced: Now (30 days): jazz, pop, rock, alternative rock, hip hop, indie rock. Long-term: progressive rock, metal, progressive metal, rock, art rock, acoustic rock. Rediscovery (dormant 365 days): metal, progressive metal, progressive rock, acoustic rock, death metal, rock. Repeated tracks outside the dominant tags (54 artists): raï, folk, traditional pop, desert blues, jazz fusion, folk rock. Obsessions (67 artists): rock, rock and roll, blues rock, progressive rock, blues, alternative rock. New since 2018 (88 artists): jazz, hip hop, pop, raï, rock, r&b.
- Shared seed tags (of 6): Long-term and Rediscovery 5; Now and New since 2018 4; Obsessions 2 with each of Now, Long-term and Rediscovery; Repeated tracks 0 with Now, Long-term, Rediscovery and Obsessions, and 1 with New since 2018.
- Reading: the repeated-track profile is the only clearly separate one; New since 2018 is largely redundant with Now; Long-term and Rediscovery are near-duplicates; Obsessions gives broad, popular tags, so obscurity would rest on the Deep cuts gates. As earlier, a profile changes the seed tags, not which albums a tag returns.
- Limits: one listener; 95 of 599 artists have no genre tags and add nothing to the seeds; thresholds (5 plays, 20 listens, 70% in 30 days) are untuned; seed tags only, no albums were fetched; no quality judgment. Nothing is wired into runtime.
- Next: the owner decides which profiles become lenses and their gates.

## 2026-10-24 — Engine 2 Phase 3: title-marker check, size of the known radio-path gap

- The title-marker check itself was done and logged on 2026-10-23: the radio path applies `batch_title_marker_rejection`, the MusicBrainz path uses release-group secondary types, and an unmarked live or compilation album still passes the radio path. The Christmas album noted in the first 2026-10-24 live-run entry is not a filter failure, since "Christmas" was never a marker. This entry measures how often the known gap lets an excluded type through.
- Owner-approved, read-only, throwaway harness outside the repository, aggregates only. A radio-led Deep cuts pool from the same five seed tags (krautrock returned nothing after a connection error) gave 20 albums. One MusicBrainz release-group search per 25 groups, unauthenticated with the app `User-Agent` (two connection retries), returned secondary types for all 20.
- Result: 18 of 20 had no secondary type; 1 was a Soundtrack and 1 a Compilation (a discography), 2 of 20 (10%). Neither title carried a batch marker, so both passed the radio-path title filter and would have been excluded on the MusicBrainz path.
- Limits: one run, one listener, five hand-picked tags, a small pool; the 10% is an observation, not an estimate. The radio band that supplied each album was not recorded.
- Possible fix, not started and needing an owner decision: a bounded secondary-type check on radio candidates before the Deep cuts gates, about one MusicBrainz call per 25 albums, applying the existing excluded secondary types. Nothing is wired into runtime; no publication or deployment.

## 2026-10-24 — Engine 2 Phase 3: MusicBrainz tail of the Deep cuts supply, measured alone

- The tail was added in PR #581 and is covered by unit tests (including radio unavailable and no `http_post`). This entry adds a live measurement of the tail on its own: owner-approved, read-only, throwaway harness outside the repository, aggregates only. Same five seed tags as the entry above, `run_deep_cuts_tag_supply` with `http_post` unset so the radio tiers are skipped and the MusicBrainz tag search serves every query, then the fast album-listener path (one MusicBrainz release search, Last.fm album lookups on four threads).
- Supply: 20 albums in 26 s (post-rock lost to a `No route to host` error; the other four tags returned 5 each), against 74 s for the radio tiers in the previous entry. Album listeners were found for 20 of 20 in 3.4 s (median 1,360): 13 inside the 300 to 50,000 gate, 5 under 300 (as low as 19), 2 over 50,000. The radio-led run had median 810 and 14 of 25 in the gate.
- Overlap: 12 of the 20 tail albums also appeared in the earlier radio-led run's 25. The harness recorded neither the radio band nor whether the tail served each album there, so the cause is unknown. A possible explanation, not tested, is that the MusicBrainz tag search returns the same top results each time, while radio answers are redrawn daily (PR #582); the tail would then give a nearly fixed list.
- Limits: one listener, five hand-picked tags, one run each, a flaky network (one tag lost), album-listener gates only, no quality judgment. Nothing is wired into runtime; no publication or deployment.
- Next (not started): repeat the tail on two days or two runs to test whether it is stable; record the radio band per candidate.

## 2026-10-24 — Engine 2 Phase 3: live run of the Deep cuts tiered supply, with batch lookups

- Owner-approved live run of `run_deep_cuts_tag_supply` (radio 50–75%, then 75–100%, then the MusicBrainz tail) with real providers, five seed tags (post-rock, shoegaze, doom metal, jazz fusion, krautrock), lens `deep_cuts`, today's scope. ListenBrainz calls carried the configured token and `User-Agent`; Last.fm used the configured key; MusicBrainz was unauthenticated. Read-only; throwaway harness outside the repository; aggregates only.
- The first two attempts lost tags to connection errors (`No route to host`, `ConnectError`); a connectivity check passed in between, so the drops looked transient. Later runs completed: every tag returned 5 albums (25 total), all with release-group and artist MBIDs.
- Album listeners (Last.fm, by release MBID): 21 of 25 found with the existing `resolve_popularity` (median 810); 25 of 25 with the faster path below (median 810; 14 in the 300–50,000 gate, 8 under 300, 3 over 50,000). One album with a "Christmas" title passed the batch title-marker filter, which is a concrete case for the deferred title-marker check.
- Speed: 129 s end to end with `resolve_popularity` (supply 78 s, popularity 52 s). With album-only lookups, one MusicBrainz release search for all 25 groups, and four parallel Last.fm threads, popularity took about 4 s (0.4 s plus 3.8 s) and the run 78 s. Pre-gating (title marker, one album per artist) removed nothing here.
- The remaining time is ListenBrainz latency: 10 radio GETs summed to 282 s (slowest 40 s) and 2 recording-batch POSTs to 60 s (one at its 30 s timeout). A tag that misses the 4 s straggler window in the 50–75 band falls to the 75–100 band and waits again. Recording batches already carry 100 recordings per call (larger sizes are unverified). The release-group endpoint fails above 80 IDs and was not needed. A batch endpoint for the tag radio is not known; passing several tags in one call would lose per-seed attribution and was not tested.
- Limits: one listener, five hand-picked tags (not derived from a window), one day's radio samples, a flaky network, album-listener gates only; the lists were not judged for quality. The tier that supplied each album was not recorded. A same-day repeat run, which should hit the radio and batch caches, was not measured. Nothing is wired into runtime; no publication or deployment.

## 2026-10-24 — Engine 2 Phase 3 gate: repeated tag-radio samples, replayed through the production lane

- Owner-approved live run, cheaper design than the previous repeat: 8 unique seed tags across five windows (four dense 30-day windows and all time), 6 independent tag-radio samples per tag (50–75 band, 20 recordings each), one batch resolution of 943 recordings (780 usable), then the production `run_lb_tag_queries` replayed offline for each window and repetition. 48 radio calls, no failures; no MusicBrainz tail (radio tier only).
- The first attempt failed at batch resolution (no route to host) after its radio samples had been lost; the rerun checkpointed samples to disk and reused them. Raw output is outside the repository.
- Every pool has 30 albums (6 seeds × the 5-per-query cap).
- Same window, different repetitions: 1.1 shared albums on average (of 30); top-10 overlap 0.3. Radio samples are redrawn on each call.
- Different windows, same repetition: 25 shared albums on average. This is explained by shared seed tags, not by the window: each shared tag contributes exactly 5 albums at that repetition (for example, 5 shared tags gave 25 shared albums, 6 gave 30, 4 gave 20).
- Conclusion: a window changes the pool only through its seed set (which tags are queried). The albums contributed by a given tag are a fresh random sample each time, so run-to-run variation of a list is larger than the window-to-window difference in seed sets. The Phase 3 gate ("a window changes the candidate pool, not only ranks") is met only at the seed level; the album-level effect is dominated by radio sampling noise. A stable window list would need a fixed sample per tag (or a deterministic candidate source), which is a design decision for the owner.
- No change to code, defaults, or runtime. No publication or deployment.

## 2026-10-24 — Re-review, CI verification, and merge PR #582

- Re-reviewed exact PR head `48532b774af01e895de1a7ef41c823b07b94edd1`. Daily cache scope is passed through the radio lane and included in cache keys; the original unscoped 0–100 key and existing band-specific key remain unchanged. New tests cover same-day reuse, next-day refresh, separate lens samples, and invalid lens/day input. The feature remains unwired into runtime.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety (`40041573624`), Docker packaging/full unit suite/image build (`40041573588`), container runtime smoke (`40041573555`), and validation-only multi-architecture image validation (`40041573534`; publishing paused). Full unit suite ran in CI; it was not run manually, consistent with the repository workflow.
- Squash-merged PR #582 as `5018446c45c000fefcde6a4955a6bcb6e1943f77`. No live provider calls, publication, deployment, or runtime verification.

## 2026-10-24 — Daily radio scope for Deep cuts (unwired)

- Radio answers can now be keyed by a scope (`lens:date`). `run_deep_cuts_tag_supply` requires `lens` and an ISO `day`, so each tag gives one fixed sample per lens per day, a fresh draw the next day, and a separate draw for each lens that shares the tag. The default key (no scope, default band) is unchanged, so existing cache entries stay valid.
- Old daily entries are not deleted; they expire with the existing 30-day TTL.
- The MusicBrainz tail is deterministic per query and is not scoped.
- Focused tests: 123 passed (new `tests/test_discovery_daily_radio_scope.py`, plus updated Deep cuts, tag-lane, gathering, lens and size-guard tests). The full suite is left to CI.
- Not wired into runtime; no live calls in this change; defaults unchanged.
## 2026-10-23 — Engine 2 Phase 3 gate: repeat live run of the Deep cuts tiered supply (gate not met)

- Owner-approved live run: `run_deep_cuts_tag_supply` (radio 50–75, radio 75–100, MusicBrainz tail) over five history windows (four dense 30-day windows and all time), twice. Each run started from a fresh copy of the metadata cache, so tag radio and MusicBrainz calls were live. Raw output stays outside the repository.
- Within a run, the windows' album pools overlap heavily: 20–25 shared of 30–40 (run 1) and 10–30 shared of 30–45 (run 2). These overlaps are inflated by the run's shared cache: all windows reuse the same tags (4–6 of 6 seeds are shared), and a repeated tag returns its cached answer. The same-window timings in run 2 (0.0–4.3 s after the first windows) are cache hits, not provider latency.
- Across runs, the same window shares almost nothing: 0–2 of about 30 albums, and 0–2 of the top 10. The seeds were identical, so the tag radio answers differed between runs. A single-tag repeat to isolate sampling from drift was attempted but the network dropped (no route to host) before it could run.
- Consequence: the 2026-10-23 entry above that says a window "changes the candidate pool in most pairs" is not supported once run-to-run variation is counted. Lists built from one window's radio sample do not differ from another window's by more than the sample noise can explain. The Phase 3 gate (a window changes the candidate pool, not only ranks) is not met by this evidence.
- Operational findings: tag-radio stragglers were dropped after the 4 s window (1 in run 1, 5 in run 2, first window only). The MusicBrainz tail ran once (run 2, first window: 5 albums). One MusicBrainz search failed with no route to host (run 1, first window). One radio query per run in the first window ended in a connection error, leaving 5 of 6 queries filled.
- No change to code, defaults, or runtime. No publication or deployment.
- Next action (needs owner decision): either measure window effects with repeated radio samples per tag (more live calls, owner approval), or treat window-driven seeds as unproven and stop Phase 3 at the seed level.

## 2026-10-23 — Engine 2 Phase 3: Deep cuts tiered supply with MusicBrainz tail (unwired)

- Added `discovery/deep_cuts_supply.py`: `run_deep_cuts_tag_supply` runs the ListenBrainz tag radio at the owner-approved 50–75% band, then the 75–100% band for queries still empty, then the MusicBrainz tag search for queries still empty. A query no tier reached is marked `not_attempted`.
- A radio tier that marks the lane unavailable (retryable HTTP failure) skips the remaining radio tiers, but not the MusicBrainz tail; the flag is cleared before the tail, which is a different provider. Regression test added (PR #581 review). Without `http_post` the radio tiers are skipped.
- `discovery/candidate_gathering.py`: the radio branch of `_run_tag_lane` moved into `run_radio_lane(..., pop_begin, pop_end)`; default behaviour and cache keys are unchanged.
- Focused tests: 158 passed across gathering, tag lane, replenishment, supply, lenses, title filter, packaging and the size guard. The full unit suite was not run here (CI runs it on the PR head).
- Title-marker check (Phase 2 deferral): the radio path applies `batch_title_marker_rejection` in `synthesize_recording`; the MusicBrainz path relies on the release-group secondary types (`CF_EXCLUDED_SECONDARY_TYPES`). Known gap: an unmarked live album still passes the radio path. Minor: "unplugged" and "bootleg" are batch markers but not in the MusicBrainz title phrases.
- Not wired into runtime; defaults unchanged. No live provider calls, publication or deployment.

## 2026-10-23 — Engine 2 Phase 3 slices 1–2: window helpers merged; live window-pool check (partial gate)

- PR #579 squash-merged as `aea328c`: pure `windowed_listen_weights` (bounded window anchored to the newest listen, optional half-life, flat all-time default) and a tag-radio popularity band parameter. The default 0–100 band keeps the original request and cache key. Focused tests: 69 passed. Not wired into runtime.
- PR #580 (above) added `window_artist_weights` and `densest_window_listens`. The dense-window choice follows the owner's direction: the history ends in 2019, so a last-N-days window is empty.
- Offline, no provider calls by the code: the local history (about 22k rows; about 19k with valid timestamps, 2010–2019) had cached artist tags for 35 of 447 all-time artists. Batch-filling the rest through the existing ListenBrainz artist prefetch reached 447 of 447 in a scratch copy of the metadata cache. Network "No route to host" errors were retried. The source cache was not modified.
- Seed probe (cached tags only): four non-overlapping dense 30-day windows and the all-time window each produce 6 profile seeds, and each pair shares 4–6 of them. Windows reorder seeds and swap one or two genres.
- Live tag-radio run (owner-approved; ListenBrainz tag radio, batch recording lookups, release-group metadata; cache writes to the scratch copy only): five windows, six seeds each, 30 albums each (the 5-per-query cap). No provider failures were recorded. Album-level overlap: dense1 and all-time share 30 of 30; dense3 and dense4 share 30 of 30; other pairs share 20–25 of 35–40. The window changes the candidate pool in most pairs, but only modestly.
- Gate status: partly met. One live run, one profile, profile seeds only (no CF or exploration pool). The Phase 3 gate needs repeat runs and an evaluation of whether the changed pools change any list.
- Probe scripts, raw results and the scratch cache live outside the repository because they derive from the owner's private listening history. Only these aggregates are recorded here.
- Limitation found during the run: a first attempt returned zero albums because the probe skipped the production batch-to-recording conversion. The fixed probe uses the production resolver shape; the earlier results were discarded.
- No publication, deployment, or runtime verification. The CI status of PR #579 was not recorded in this session.

## 2026-10-23 — Re-review, CI verification, and merge PR #580

- Re-reviewed final PR head `f2ca7a9822af0dac592c0e36cd81a7bcee8c25f8`. The earlier findings were addressed: `listen_artist_mbid()` now validates nested metadata as mappings and rejects malformed MBID values safely; `densest_window_listens()` normalizes non-numeric/boolean window widths to `ValueError`. Regression tests cover malformed nesting and invalid widths. The helper remains pure and is not wired into runtime.
- All four required workflows passed on that exact head: Python syntax/acquisition safety (`40029108109`), Docker packaging/full unit suite/image build (`40029108024`; the unit-test step and image build succeeded), container runtime smoke (`40029108017`), and validation-only multi-architecture image validation (`40029108075`; publishing paused). The full unit suite ran in CI; it was not run manually, in accordance with the repository workflow.
- Squash-merged PR #580 as `ede38e969956d1907ba25e579203c6d4b5805c3b`. The feature remains unwired; defaults unchanged. No publication, deployment, or runtime verification. Phase 3 continues with time-range profiles/window-driven tag-lane seeds and the previously deferred Deep cuts items.

## 2026-10-23 — Engine 2 Phase 2 closeout: Deep cuts band, filter check and tail deferred to Phase 3

- Phase 2 is complete: lens framework and Deep cuts adapter (PRs #575, #577) and evaluation metrics (PR #578). Nothing is wired into runtime.
- The owner decided to leave the 50 to 75% radio band request (it needs a band-keyed radio cache and a decision on live provider use), the check that the title-marker filter covers both candidate sources (`lb_tag_lane.py` states the filter applies to radio candidates; not verified for the MusicBrainz tail), and the MusicBrainz tail for Phase 3. Defaults are unchanged.
- Next action: Phase 3, time-range profiles and window-driven seeds.

## 2026-10-23 — Engine 2 Phase 2 (part 1): lens framework and Deep cuts pool adapter merged

- PR #575 (squash-merged as `85efa95b32ecd1ce42d7afd5293a60cbfcf9f391`): `lens` name on `AllocationRequest` and `AllocationResult` (default `now`); new pure `discovery/lenses.py` with the Now (quota), Genre spread (family coverage) and Deep cuts lenses and `partition_lenses`, which removes the artists and album titles an earlier lens selected before the next lens runs. Deep cuts follows the approved definition (album audience 300 to 50,000, at least 2 tags, one album per artist, at most 2 per seed, ranked by tag strength, unknown audience never selected). After review, partitioning also excludes by album title, and Deep cuts validates `count`, `max_checks` and candidate IDs, enforces the 60-check bound and reports the real checked count.
- PR #577 (squash-merged as `513a4589387a7667569b854c37ace1bf028ab012`): `build_allocation_inputs` takes an optional `popularity` map and fills `audience`, `seed` and `tag_strength` through `deep_cuts_fields`. After review: audience is the album-level listener count only (an artist-level count never passes the album gate), and the tag lane now keeps the radio's per-recording `tag_count` as `tag_strength`. Radio cache entries are now `[recording MBID, tag_count]` pairs; older plain-MBID entries still load with a count of 0.
- Tests actually run by the agent: focused suites only (lenses, allocation contract, allocator, selection inputs, characterization, tag lane, candidate gathering and supply, tag-lane early stop); server-size ratchet. The full suite was not run by the agent. Review reports stated CI was green on earlier heads (`2ebaf61`, `5a8a063`); the final reconciled heads (`1d7c729`, `c1556b0`) were not confirmed by the agent because the GitHub API was unreachable, so confirm required workflows on `main`.
- Not done: nothing is wired into `recommend_new_music` or any route; the lane still requests the full popularity range (0 to 100%), not the approved 50 to 75% band; the title-marker filter and the MusicBrainz tail are not part of the lens; window-profile seeds are Phase 3; per-lens and set evaluation metrics were still open when this entry was written (merged afterwards in PR #578); the lens is not stored on recommendations (Phase 4/5). Not published or deployed; no live-runtime verification.
- Next action: Phase 2 evaluation metrics per lens and across the set.

## 2026-10-23 — Engine 2 Phase 1 closeout; Deep cuts lens approved

- The owner approved the Deep cuts lens as proposed: dense-month or recent window; ListenBrainz tag radio at the 50 to 75% popularity band as the main source, with the 75 to 100% band and the MusicBrainz tag search as the tail; title-marker filter; album listeners about 300 to 50,000; one album per artist; at most 2 per seed. The definition is recorded in `docs/engine2.md`.
- Phase 1 outputs: merged popularity module (PR #574, unwired); measurements and prototype results in the 2026-10-23 entries above; no ranking weight, default or provider budget changed; no code beyond PR #574. Throwaway harnesses and private data files stay outside the repository.
- Not claimed: list quality beyond aggregates and spot checks; behavior for other listeners; any publication or deployment.
- Next action: Phase 2, the lens framework (a design of how lenses enter the allocator request and result, and how lists are partitioned, before code).

## 2026-10-23 — Engine 2: fast end-to-end Deep cuts test across five windows (50-75% radio band plus tails)

Prompted by the owner: the earlier five-window runs took too long. This run was tuned to about 35 s per window (about 3 minutes for all five, sequentially). Read-only; private files outside the repository (mode 600); aggregates only; throwaway harness not committed.

- **Tuning that made it fast:** the recording-batch response already carries the release MBID (`release.mbid`), so no MusicBrainz release search is needed; album listeners only (no artist-level lookup); a pre-gated shortlist (title-marker filter, tag count at least 2, one candidate per artist, 6 from the 50-75% band and 3 from the 75-100% band per seed) of about 30 candidates per window; four parallel Last.fm threads under a 4-per-second limit; one retry with short timeouts; the MusicBrainz tail reused from the earlier harvest (no new MusicBrainz calls). The first two attempts failed for two avoidable reasons: a wrong field name dropped every radio candidate, and swallowed batch errors hid a dropped connection. Both were fixed in the harness.
- **Result (gates: 300 to 50,000 album listeners, one album per artist, at most 2 per seed, tag count at least 2; radio 50-75% first, then radio 75-100%, then the MusicBrainz tail):** four windows reached lists of 10 (2012-04: 9 from the 50-75% band, 1 from the tail, 5 seeds, median 21,534 listeners, 1 album under 1,000; 2012-06: 9 and 1, 5 seeds, median 19,911, none under 1,000; 2014-02: 6 from 50-75%, 2 from 75-100%, 2 tail, 5 seeds, median 12,118; 2011-02: 6 and 4 from 75-100%, 5 seeds, median 6,890, 2 under 1,000). The current profile reached 7 (4 from 50-75%, 2 from 75-100%, 1 tail; 4 seeds; median 1,825). Artist overlap between the first four windows is 0 for all six pairs.
- **Conclusion:** with the 50-75% band as the main source and the title-marker filter and listener gates, the window mechanism produces full, distinct, mostly mid-obscure lists quickly. The first-pass cost is one radio GET per seed per band, one recording batch POST per window and about one Last.fm album lookup per shortlisted candidate (about 30 per window, 150 for five windows); with the windows run in parallel under the same Last.fm limit this is about 40 s.
- **Limits:** one listener; four windows from the same metal and world-music period plus one current profile (which gave a shorter list); the network dropped repeatedly and the harness retried or skipped; tag assignments in the radio are noisy and were only spot-checked; thresholds are untuned; the lists were not judged for quality beyond aggregates and spot checks.
- **Next:** the owner decides the Deep cuts lens definition (window, band, gates); then Phase 2 (lens framework and partitioning).

## 2026-10-23 — Engine 2: ListenBrainz tag-radio popularity band is inverted; 50-75% is the sweet spot (corrects the previous entry)

Read-only; private files outside the repository (mode 600); aggregates only; throwaway harness not committed. Network intermittent again (one radio request failed in the 0-10% run and was skipped; the 2012-06 window was rerun after a total failure).

- **Correction:** the previous entry suggested a lower band (0 to 10%) for more obscure results. That was wrong. In `GET /1/lb-radio/tags` a low `pop_begin`/`pop_end` returns the MOST popular recordings of the tag. Run over the five windows, the 0-10% band returned 310 candidates with median album listeners 539,928 and 232 at 200k or more, against median 224,104 and 177 for 0-25%. Title-marker rejects were 0 of 310.
- **Probe (3 tags, 4 bands, 15 recordings each, album listeners by release MBID):** progressive rock median album listeners 259,203 / 43,474 / 26,934 / 28,813 for bands 0-10 / 25-50 / 50-75 / 75-100; jazz 537,015 / 31,577 / 23,791 / 2,569; metal 280,826 / 75,561 / 17,940 / 1,958. Albums under 50k listeners: 0-10% band 0, 2, 2 of 9 to 13; 50-75% band 10, 12, 10 of 13 to 15; 75-100% band 7, 13, 8 of 12 to 15. Albums under 1,000 listeners: none in the 50-75% band except 1 in jazz; 4, 6 and 5 in the 75-100% band. The upper band gets obscure but also reaches the junk-risk range.
- **Combined lists (0-10% radio plus the MusicBrainz tail, gates 300 to 50,000 listeners, one album per artist, 2 per seed, title-marker filter):** list lengths 8, 10, 8, 8, 7 across the five windows; the radio contributed 1 to 6 per list (it was mostly outside the listener ceiling), the MusicBrainz tail the rest; artist overlap between windows 0 to 2 per pair. The band, not the combination, was the problem, so these lists say little about a final design.
- **Conclusion:** for a Deep cuts lens use the radio with a band around 50 to 75% as the main source (obscure, few junk-range albums), the title-marker filter, a listener floor of about 300 and a ceiling of about 50k; the 75-100% band and the MusicBrainz tag search are the tail for obscure artists, with the floor guarding against junk. This is not yet tested end to end across the windows.
- **Limits:** three tags and 15 recordings per cell in the probe; one listener; the `percent` field's exact meaning is inferred from results (low is popular), not from documentation; the endpoint is undocumented; thresholds are descriptive and untuned.
- **Next:** rerun the five windows with the 50 to 75% band plus the MusicBrainz tail, then decide the lens definition.

## 2026-10-23 — Engine 2 Phase 1 step 4: deep-cuts prototype across listening windows (offline plus read-only calls; no code)

The owner clarified the criterion: the application suggests music to acquire, so predicting later listening is not the goal; what matters is that a dense window changes the tag-lane seeds and that the resulting deep-cuts list is obscure, varied and not junk. The earlier prediction check (previous entry) is therefore informational only. Read-only; private files outside the repository (mode 600); aggregates only; throwaway harness not committed; network intermittent (11 of 30 MusicBrainz searches and 1 radio request failed and were skipped).

- **Windows:** four months from the scrobble export (2012-04, 2012-06, 2014-02, 2011-02) plus the current 15-artist profile. Seeds come from the repo's `select_supplementary_tag_queries`; candidates exclude every artist already in the history or the current pool. Album listeners by release MBID come from the merged `discovery/mbid_popularity.py`.
- **Candidate source A, MusicBrainz tag search (about 8 new artists per seed, secondary types excluded):** 152 candidates; album listeners median 444; 39 of 142 known under 100 and 83 under 1,000 (junk risk: tribute and cover albums appear); 2 of 142 over 200k. After gates (300 to 50,000 listeners, at most 2 per seed, one per artist) lists reach only 4 to 9 of 10. MusicBrainz ratings were absent from search results, so the rating signal was not testable without extra lookups.
- **Candidate source B, ListenBrainz tag radio, popularity band 0 to 25% (30 recordings per seed, resolved through the batch recording endpoint):** 339 candidates; album listeners median 224,104; only 2 under 100 and 10 under 1,000; 177 of 327 known at 200k or more. After the same gates, lists of 6 to 10 reach 4 to 6 seeds. The band is relative within the tag, so for large tags it is still well-known music; the gated survivors are deep cuts by moderately known artists rather than obscure artists. The radio's tag assignment is noisy (a pop album under hip hop, a hard-rock album under metal), and live or greatest-hits albums appear, since the batch endpoints carry no secondary types (the repo's batch title-marker filter exists for this).
- **Windows differ, which was the question:** artist overlap between the window lists is 0 for 9 of 10 pairs and 1 for the tenth (tag-radio lists); with the MusicBrainz source the pairs share 0 to 2 artists, through a few recurring albums for overlapping seeds such as progressive rock.
- **Signals compared for ranking the gated pool:** tag strength (radio `tag_count`), plays per listener, and their product. They select nearly the same lists (overlap 4 to 9 of 6 to 10, identical in five of the ten comparisons made), so the ranking signal matters less than the gates. Plays per listener has median about 11 (quartiles 8 and 17) and separates devoted small audiences from drive-by ones; it is unvalidated.
- **Conclusion:** the window mechanism works; a usable deep-cuts list needs (1) the batch title-marker and secondary-type filter, (2) a listener floor (about 300) and ceiling (about 50k), (3) one album per artist and a per-seed cap, (4) a lower popularity band than 0 to 25% or a combination of both sources to reach obscure artists with enough supply, and (5) seed-tag quality control (tag count minimum) to avoid mislabelled albums. List length of 10 was reached for only one window (current profile), so supply per seed needs to grow before lists of 10 are reliable.
- **Limits:** one listener; four windows from a metal and world-music period plus one current profile; MusicBrainz searches partly failed; no quality judgement beyond aggregates and spot checks; thresholds are descriptive and untuned; the album listener count is a Last.fm audience measure, not a quality measure.
- **Next:** decide the lens definition for Deep cuts (window, source, band, gates), then Phase 2 (lens framework and partitioning).

## 2026-10-23 — Engine 2 Phase 1: taste fit checked against the listening history across four months (offline plus read-only calls)

Prompted by the owner: a dense listening period should give better results whatever the genre, so four months with different tastes were tested against the scrobble export (2010-10 to 2019-05 after dropping 3,031 rows stamped January 1970). Read-only; private files outside the repository (mode 600); aggregates only; throwaway harness not committed. No code, ranking weight or default changed. The network was intermittent during the run (see limits).

- **Method:** profile = flat play counts by artist MBID in one month; fit = the same tag/family cosine as before. Ground truth from the history: positives are artists whose first scrobble falls in the three months after the window; negatives are artists first scrobbled at least 12 months after it; AUC of fit, positives against negatives. Tags for 406 artists came from the ListenBrainz artist batch (95 s).
- **Fit against what was played next (AUC; 0.5 is chance):** 2012-04 progressive metal 0.60 (52 positives, 87 negatives); 2012-06 Maghreb and Tuareg 0.43 (31, 78); 2014-02 progressive and classic rock 0.44 (5, 26); 2011-02 metal with folk and world 0.55 (45, 256). Tag-only and family-only variants fall between 0.41 and 0.60 the same way.
- **Conclusion:** the tag/family fit does not predict the next new artists reliably. It is slightly above chance for two months and below chance for two. It is not validated for ranking and should not be used as a ranking score. The below-chance months may partly reflect the negatives (artists first heard a year or more later, when taste had moved), and 2014-02 has only 5 positives, so the test is crude; the result is "no evidence it works", not proof that it cannot.
- **Seeds do change with the window and follow the taste:** 2012-04 gives progressive rock, progressive metal, metal, ambient, art rock, post-metal; 2012-06 gives rock, progressive rock, raï, gnawa, punk, reggae; 2014-02 gives progressive rock, progressive metal, metal, rock, psychedelic rock, space rock; 2011-02 gives metal, progressive rock, rock, art rock, progressive metal, acoustic rock. The top root families come out as rock and metal in almost every month, so the family labels are too coarse to tell these months apart.
- **Lane stage incomplete:** 13 of the 24 MusicBrainz seed searches failed on the network, leaving 5 to 15 candidates per month; of those, the artists with known audiences were mostly obscure (medians 8k to 153k Last.fm artist listeners) and 1 to 4 per month were both fit >= 0.45 and under 200k. Too few and too uneven to count as a result; to be rerun with a stable connection.
- **Limits:** one listener; four windows; tiny positive set for 2014-02; negatives confounded with later taste; family labels coarse; fit formula untuned; lane stage partial.
- **Next:** rerun the lane stage when the network is stable, then try a signal other than tag cosine (similar-artist links, or co-listening within the history itself) against the same ground truth before building a deep-cuts list.

## 2026-10-23 — Engine 2 Phase 1: dense-month window (2012-04) drives the tag lane (offline plus small read-only calls)

Prompted by the owner: the last 30 days are only about two weeks of listening, so a dense month from the scrobble export was used. Aggregates only; private files outside the repository (mode 600). Small, throwaway harness (not committed): 6 MusicBrainz release-group searches, 2 ListenBrainz artist-tag batch GETs, about 20 Last.fm `artist.getInfo` calls by artist MBID. No code, ranking weight or default changed.

- **Export check:** 22,185 scrobbles, 2010 to 2019; 3,031 rows carry a January 1970 timestamp (bad data, excluded). Densest months: 2012-04 (1,743 scrobbles, 98 artists, 84% with an artist MBID), 2012-05 (1,505), 2012-03 (1,322). That period is progressive metal and rock (Pain of Salvation, Devin Townsend, Opeth, Pink Floyd), unlike the current hip-hop, jazz and pop profile.
- **Window profile:** flat play counts by artist MBID for 2012-04 (75 artists with MBIDs, 67 tagged). The repo's own `select_supplementary_tag_queries` on the top 15 artists gave six seeds: progressive rock, progressive metal, metal, ambient, art rock, post-metal. The current profile's seeds were hip hop, pop, jazz, east coast hip hop, art pop, pop rock. No seed is shared, so **a window changes the tag-lane seeds completely.** This is the Phase 3 gate for the tag lane; the CF pool is still not windowed.
- **Resulting candidates (crude lane: first 5 albums per query, 25 candidates, 18 distinct artists):** only 3 of the 18 artists appear in the current 274-candidate pool. Artist listeners by artist MBID: median 9,889; 21 of 24 known are under 200k and 18 under 50k, against a median of 4.2M for the current CF pool. The lane under a window is where obscure supply is.
- **Fit under the window profile (same tag/family cosine as before):** 17 of 18 artists tagged; quintile cuts 0.00, 0.36, 0.53, 0.64; 6 candidates are both well fit (>= 0.45) and under 200k artist listeners. The current CF pool has a median fit of 0.51 under this profile against 0.41 for the windowed lane. Fit remains an unvalidated, weak taste signal (see the earlier entry).
- **Limits and open issues:** one window, one profile; the harness is not the app's lane (no owned or duplicate filtering; one query returned five albums by a single artist; the ambient seed returned five albums by one artist with fit 0.00); the progressive metal seed produced no candidates and was not investigated; fit is not validated; two-week and one-month windows were not compared for stability; the 1970 rows mean any window code must drop timestamps before 2000.
- **Next:** a deep-cuts prototype that joins fit, obscurity and artist de-duplication under both profiles, then a decision on whether the tag lane alone is enough.

## 2026-10-23 — Engine 2 Phase 1 steps 2 and 3: tag-lane taste fit and seeding (offline, docs only)

Offline analysis of the 8-page / 120-tag capture plus one read-only ListenBrainz artist-tag batch GET for the 38 tag-lane artists (the only new provider call). One profile, one capture. No code, ranking weight or default changed.

- **Step 3, seeding (read from `discovery/candidate_gathering.py`, `discovery/tag_queries.py`):** tag-lane queries come from the 15 highest-weight artists in `recent_artist_mbid_counts`; their cached genre tags are weighted by that artist weight and the top 6 become `profile:` queries, plus 2 `explore:` tags from the CF pool, 5 candidates kept per query (40 in total here). So a history window can drive the seeds: replace the weight map and the profile tags change. Saved-album feedback can already reorder or replace a seed. The CF pool is not affected by a window (ListenBrainz builds it from the whole history).
- **The tag-lane candidates carry no tags in the capture:** 2 of 40 have genres, because the 120-lookup tag budget goes to the CF pool. Their `genre_families` is only the seed's family, so candidates from the same seed are indistinguishable until their artists are tagged. After the batch GET, 25 of 38 artists (66%) have genre tags; the untagged third are the data-poor ones.
- **Fit score tried:** cosine similarity between the candidate's tags and the recent-listening tag vector (weights from the 19 recent artists), at tag level, at root-family level (`fallback_family`), and a mix.
- **It is a weak signal.** On 233 tagged CF candidates the fit has Spearman 0.09 with the engine score (the engine score is mostly collaborative filtering and popularity). As a taste check, owned against unowned CF candidates: AUC 0.59 for tag-level fit, 0.53 for family-level, 0.58 for the mix, against 0.71 for the engine score. Owned albums are only a rough proxy for taste.
- **Tag-lane fit values** (25 tagged artists) range 0.21 to 0.50 with quintile cut points 0.36 to 0.48, similar to the CF candidates (0.35 to 0.52). Within one seed the score orders candidates (for example jazz 0.21 to 0.40), but several seeds give near-identical values (east-coast hip hop: four candidates at 0.48), and `explore:` seeds score lower than `profile:` seeds as expected.
- **Conclusion:** tag overlap with the recent profile can break ties and gate out clear mismatches, but it is not enough alone to rank the tag lane; its discrimination of taste is weak on this profile. Candidates without tags cannot be scored, and they are the obscure ones. A second signal is needed before a deep-cuts list: candidates would need tags (about one ListenBrainz batch call per 75 artists, cacheable) and possibly similar-artist links to the profile artists (not yet tested).
- **Limits:** one profile; the profile vector uses 19 recent artists; owned-versus-unowned is a proxy; the tag-lane sample is 38 artists; the fit formula and the 0.5 mix were not tuned; similar-artist links, MusicBrainz tag counts and the full listening history were not tried.

## 2026-10-23 — Engine 2 Phase 1 step 1: MBID-keyed popularity measured (PR #574, merged)

Owner-approved read-only provider calls on the 203 unowned candidates of the 8-page / 120-tag capture (artist MBIDs 143 distinct). Private results outside the repository (mode 600); aggregates only. One profile, one capture.

- **Last.fm artist listeners by artist MBID:** 203 of 203. Median 4.2M; 17 candidates under 10k, 23 under 50k, 32 under 200k (matches the earlier name-based run).
- **Last.fm album listeners by release-group MBID:** 0 of 203 (error 6, not found). Last.fm's `mbid` wants a release MBID.
- **Release MBIDs:** MusicBrainz release search used as a batch (`rgid:(a OR b ...)`, 25 groups per query, 100 releases per page, so paginated) worked; the ListenBrainz release-group batch (`inc=release`) returns one `caa_release_mbid` per group. On a 25-candidate sample Last.fm resolved 23 via the MusicBrainz release (official first, then earliest) and 19 via the ListenBrainz release.
- **Full run (MusicBrainz search, up to 5 releases tried per group):** 57 MusicBrainz calls covered 175 of 203 groups; 228 Last.fm calls found 166 albums (82%). Median album listeners 1.2M; 32 under 10k, 41 under 50k, 45 under 200k. Tag-lane candidates: 36 of 40 matched, 31 under 50k; ListenBrainz candidates: 130 of 163 matched, 10 under 50k. Ten albums have under 50k listeners though their artist has over 1M. The 37 unmatched are mostly popular (median artist audience 5.1M; 5 under 200k). The 28 groups the paginated search did not cover were not filled in that run.
- **Deezer (name search, no batch endpoint; 8 parallel threads under a 40-per-5-seconds limiter, 52 s):** album fans for 198 of 203. 46 of 163 ListenBrainz candidates show under 1,000 fans though only 4 have a small artist audience, so fan counts mislead for popular artists.
- **Discogs (consumer key and secret, master search, 60 requests a minute, 4 minutes):** `have` counts for 188 of 203.
- **Agreement (Spearman, on candidates both sides matched):** album listeners vs artist listeners 0.62; vs Discogs 0.50; vs Deezer 0.38. Artist vs Deezer 0.38; artist vs Discogs 0.42; Deezer vs Discogs 0.30.
- **Conclusion:** use album listeners by MBID as the obscurity signal with artist listeners by artist MBID as fallback; Deezer and Discogs are optional cross-checks only.
- **Code:** `discovery/mbid_popularity.py` with 20 offline tests after the review fix (PR #574, merged as `eb4cb16`, not wired into any runtime path; no ranking weight, default or provider budget changed). Tests run: `tests.test_discovery_mbid_popularity` plus `test_discovery_artist_genre_batch`, `test_discovery_batch_lookup`, `test_metadata_cache` (50 total, repo venv); size ratchet and legacy-import checks pass. Full suite not run by the agent; CI on the merged head is recorded in the PR #574 review entry below.
- **Module run live on the same 203 candidates (fresh cache, 307 s):** 186 albums found (92%) against 166 above, 17 candidates on artist-level fallback, none without a signal. Calls: 143 Last.fm artist, 233 Last.fm album, 19 MusicBrainz release searches, 2 ListenBrainz release-group batches. The MusicBrainz call count differs from the 57 above (different script); the cause was not investigated.
- **Limits:** one profile; 25-candidate release-resolution sample; correlations only on mutually matched candidates; Last.fm's matched edition not verified; album and obscurity thresholds are descriptive, not tuned.

## 2026-10-23 — PR #573 merged: opt-in family-coverage policy

- Squash-merged as `9b1dab53f2fc480fd74f4e24560ebb6dd7ed14e1` from exact tested PR head `1c67f61add223274a898aeb3061d95a1664139f8`.
- The final review fix moved ownership classification and allocation-input construction to `discovery/allocation_inputs.py`, and quota/coverage request options and diagnostics to `discovery/selection_policy.py`; `recommend_new_music()` is 418 lines. The enforced limit was not raised.
- Regression coverage checks ownership classification and stable allocation inputs, legacy quota targets/default response shape, opt-in family-coverage options/diagnostics, and fallback for unknown setting values.
- Required CI passed on the exact PR head: Python syntax/acquisition safety run `39944738730`; Docker packaging, full unit suite and image build `39944738753`; container runtime smoke `39944738722`; non-publishing multi-architecture validation `39944738756`. Release workflow validation `39944738733` passed with the publishing job skipped. The full unit suite was run by CI, not locally. No browser check was performed.
- Remaining evidence limits: one profile and individual captures; no listening-quality claim; replay captures do not freeze the selection-policy setting; the per-artist MusicBrainz fallback path was not exercised. No publication or deployment.

## 2026-10-23 — PR #573 review fix: legacy-server size ratchet

- The reviewer found `recommend_new_music()` at 474 lines against the 450-line exception (the Python syntax workflow failed at the size ratchet). `main` was exactly at 450, so any addition inside the function failed. The limit was not raised.
- Fix: ownership classification and `AllocationCandidate` construction moved to `discovery/allocation_inputs.py`; quota targets, the family-coverage request options and the opt-in response diagnostics moved to `discovery/selection_policy.py`. `recommend_new_music()` is now 418 lines. Behavior is unchanged for both policies.
- Tests added: `tests/test_discovery_selection_inputs.py` (ownership statuses, input building and genre family, quota split, policy options and report) and three server-level cases (default policy keeps quotas and the response shape; opt-in policy sets the allocator options and reports genre families; unknown value falls back to quota).
- Run locally: the steps of the Python syntax workflow (py_compile list, size ratchet, app import boundary, dependency map) and the focused test modules touching the change. The full suite was not run locally; CI results for the updated head are recorded in the PR.

## 2026-10-23 — Obscurity measurements and Engine 2 roadmap (docs only)

Owner-approved read-only provider calls (Last.fm `album.getInfo` for 203 unowned candidates, `artist.getInfo` for 144 artists, about 20 Deezer lookups); private result files outside the repository (mode 600); aggregates only. One capture (8 CF pages, 120 tag lookups), one profile. No code or default changed by this entry.

- **Popularity data is nearly absent from captures.** The engine looks up Last.fm popularity for about 40 candidates per run; 12 unowned candidates carried listener counts and the smallest was 9,382.
- **Album-level Last.fm lookups mismatch** on titles with brackets, curly quotes or edition suffixes, making well-known albums look obscure. Artist-level lookups are better but mismatch on "feat." credits and non-ASCII hyphens. MBID lookups are needed.
- **Artist listeners, 203 candidates:** median 4.2M; 33 (16%) under 200k; 22 under 50k; 17 under 10k.
- **Obscure candidates come from the MusicBrainz tag lane:** 29 of 40 (73%), against 4 of 163 (2%) from ListenBrainz CF. All tag-lane candidates share the base score 0.035 (no taste bonus), so they never rank.
- **Score tracks popularity:** median album listeners 2.7M for the top 20 by score, 75k for ranks 120 and below.
- **Deezer (no key):** 15 of 20 sampled albums matched; 0 to 132 fans for albums with 1 to 554 Last.fm listeners, 54 to 348,362 for 4.0M to 5.3M. Separates extremes, noisy mid-range.
- **Roadmap:** `docs/engine2.md` (lenses, other data sources, phases, evaluation metrics, open decisions). `ACTIVE_WORK.md` section 2c lists Phase 1 as the next priority.
- **Limits:** one profile and one capture; album-level counts unreliable; the tag-lane seeding code was not read; Deezer/Discogs/others unverified beyond the Deezer sample; no listener-quality measurement.

## 2026-10-23 — Family-coverage selection policy and genre-tag budget (PR #573, merged)

Owner-approved live captures (read-only, slskd off, aggregates only, private captures outside the repo, mode 600). Single profile, one capture per arm; no recommendation-quality claim.

- **Finding.** With the quota policy the wider CF pool barely reaches the final list: genre-tag lookups were capped at 60 (+15 recent) artists whatever the pool size, so extra candidates arrived untagged, scored low, and never ranked. Untagged unowned candidates at 4 / 8 / 12 CF pages: 40 / 97 / 128 (60 lookups), 15 / 39 / 61 (120), 15 / 13 / 15 (220). 220 gained nothing over 120.
- **Label correction.** The first experiments labelled families by the alphabetically first tag through the rules table ("alternative rock" -> "alternative"), which inflated family counts. The final label is `primary_genre_family`: plurality of `fallback_family` (trailing root word, then the Wikidata ancestry table) across all tags.
- **Offline (real allocator, 9 captures, count 10).** Cap 2 alone is about level with 4/3/3 on spread and higher on engine score (0.158 vs 0.14 to 0.145). The coverage phase is what uses the wider pool: with 8+ CF pages and 120 tags, coverage at floor 0.4 reached 9 families (entropy 3.12, mean score 0.147 vs 0.145 for 4/3/3, 6 families). At 4 pages the pool cannot exceed 7.
- **Live end to end (new code, tag budget 120).** quota @4 pages: 7 families, 4 rock; family_coverage @4: 7 families, max 2 per family; family_coverage @8: 9 families, max 2. 10 recommendations and 10 artists in each, no provider failures.
- **Change.** Commit 1: tag budget 60/75 -> 120/135 (named constants). Commit 2: opt-in `recommendation_selection_policy = family_coverage` (default `quota`, legacy path unchanged): genre-family cap 2 (unknown 1), adventurous floor `count // 5`, coverage phase above 0.4 x top score, score fill, relaxed final fallback; owned candidates do not use the 60-check budget under this policy. `CF_MAX_PAGES` left at 4.
- **Limits.** Replay captures do not freeze the policy setting, so family_coverage captures do not reproduce under default settings. Coverage lists lean toward higher-scoring, better-known albums than the quota list in the one live comparison (the quota list had a jazz and two lesser-known picks the coverage list lacked); whether that is better or worse is not measured. No setting UI, no browser check, not published or deployed. Engine score is not a listening-quality measure.

## 2026-10-23 — CF freshness repeat, deeper CF pages, and recent-vs-all-time profile comparison (docs only)

All live runs were approved by the owner; slskd off; aggregate only; harnesses were one-off scripts and are not committed; temporary data dirs deleted. No code, default, or ranking weight changed. Single samples throughout; none supports a recommendation-quality claim.

- **P0h repeat (CF freshness).** 4 CF pages, 3 recent-listen pages, 1 `stats/.../recordings` GET (200). CF pool 400 of 1,000; recent 30 days 100 listens / 89 distinct mapped recordings; all-time top 1,000 items / 902 with a recording MBID. CF in recent: 2 (0.5%). CF in all-time: 44 (11.0%), all of it all-time-only (X = 11.0%). All-time matches per CF page 10, 11, 13, 10 (baseline of 2026-10-21: 23, 10, 1, 3 on page 1). Decision-table outcome: **mixed; keep defaults.** The even spread across pages, against the page-1 concentration of the baseline, is consistent with ListenBrainz having recomputed CF; this was not independently verified (the baseline CF recordings were not retained).
- **P1a repeat (deeper CF pages), `CF_MAX_PAGES` 4 / 6 / 8.** Test-only override, fresh data dir per arm, one cold and one warm run per arm, 10-minute pause between arms (the 2026-10-21 run had none).

| Pages | Cold | Warm | CF recordings resolved | LB candidate albums | Final list overlap with 4-page (cold / warm) |
| --- | --- | --- | --- | --- | --- |
| 4 | 27.7 s | 11.4 s | 400 | 117 | n/a |
| 6 | 38.9 s | 9.9 s | 600 | 180 | 9/10, 9/10 |
| 8 | 34.0 s | 10.2 s | 800 | 234 | 9/10, 9/10 |

  Final list 10 albums / 10 artists in every run; no ListenBrainz 429 or 502; one MusicBrainz 503 (6-page cold run). The 6-page cold run missed the +10 s threshold by 1.2 s; the 8-page cold run passed (+6.3 s). Eligible unowned albums were **not** captured, so candidate albums stand in for them. Each extra 2 pages cost 2 CF GETs and 2 recording-batch GETs, with no fallback to per-recording lookups. The 2026-10-21 cold-run failure (429s, fallback, 183.6 s) did not recur. **Decision: keep `CF_MAX_PAGES = 4`.** The larger pool changes the final list by one album; 8 pages is the candidate if more supply is wanted later.
- **Recent 30 days vs all-time profile (full-engine responsiveness; offline replay of one live capture).** One live capture (cold, 22.1 s, 10 recommendations, 152 ranked candidates), then `recommendation.profile_comparison` building blocks with a one-off driver. History: the owner's 22,185-scrobble export (2002-10-01 to 2019-05-26; artist MBIDs on 18,023 rows; 3,031 rows carry a 1970 timestamp in the raw export, so dates came from the cleaned export, which aligns row for row). Profiles: recent 30 days (100 listens, 24 artists, 76 genre-classified listens, 8 families) vs all-time (22,285 listens, 721 artists, 18,112 with an artist MBID, 3,060 genre-classified, 8 families).
  - All-time with **flat** weights vs recent: 9/10 final overlap (Jaccard 0.82), 5 positions changed, 143 of 152 shared candidates changed rank, maximum displacement 55; category split unchanged (4 adjacent / 3 adventurous / 3 cross-genre); 10 distinct artists in both.
  - All-time with the **production** 14-day half-life vs recent: identical (10/10, 0 rank changes), because decay is anchored to the newest listen and the older history weighs about zero. The app today effectively ignores history older than a few weeks.
  - Allocator: about 90 of 152 candidates are blocked by the recent-genre cap in both profiles (88 and 90); only 1 to 2 of the 10 selections come from the top 10 by score.
  - Limits: one frozen pool and one capture; candidate generation not varied (the CF pool is built by ListenBrainz from the whole history); genre data exists only for artists already looked up in the snapshot, so the all-time family profile is partial; 11 popularity lookups had no captured data in the all-time arm and were treated as no bonus (no live request).
  - Reading: ranking responds to listening habits; the final list barely does. Same shape as the 2026-10-18 result (PR #361 harness). No weight change is justified by this.
- The private capture contains listening history and stays outside the repository (owner-only directory).
- Next: optional, owner's decision. Investigate why the recent-genre cap removes about 60% of candidates in both profiles, or request approval for 8 CF pages if more candidate supply is wanted. Neither is started.

## 2026-10-23 — Genre ancestry table extended to 398 tags (PR #572)

- PR #572 squash-merged as `133a510627d42fecf86241a3f4f04a189950a65c` from exact head `344b8775863ba55a13bca3951b45e9f62080ccaa`; all four required workflows passed, including the full unit suite (test-and-build run `39873873438`). CI was not re-checked on the merge commit.
- `settings/genre_ancestry.json` grew from 205 to 398 tags, built with `scripts/build_genre_ancestry.py` from a broad seed list plus all tags seen in the owner's captures (263 of 284 new tags resolved on Wikidata). New roots: gospel, latin, and ska (mapped to reggae). Wikidata's wrong placements were corrected with curated `OVERRIDES` (metalcore/deathcore/grindcore/mathcore/djent/post-metal to metal; amapiano/gqom/kwaito/kuduro/afrobeats to african; choro/forro to brazilian; lovers rock to reggae; and others). No existing entry changed. The build script now backs off when Wikidata throttles.
- A frozen-capture check on the owner's latest capture is unchanged (28 adventurous / 88 adjacent / 32 cross-genre / 12 unclassified; targets met) because the owner's tags were already covered. Known soft spots: darkwave/coldwave map to rock and bare `minimal` to electronic. Focused tests only run locally; not published or deployed.

## 2026-10-23 — Derived taste profile follow-ups: labels, ancestry fixes, fixed tables removed (PRs #570, #571)

- **#570** squash-merged as `b0a0132578e729edfaeec2303f68e67366c78fda` from head `c143451f891cb541d66aca0133d9f50a4f755c0d` (all four required workflows passed). Deep Dives rows and tag-query family labels now use the derived family vocabulary; the Deep Dives rule table is gone. A row's key is the family of the artist's first tag that yields one. The Wikidata ancestry table was corrected (metal subgenres wrongly under rock, punk rock, soul-adjacent entries under pop, unresolved baroque/dub/dance/k-pop and others) and `scripts/build_genre_ancestry.py` now applies trailing-root-word normalization and a curated `OVERRIDES` map on every build.
- **#571** squash-merged as `ba2f235a4f9e82fdb98139c50b5c512c83438824` from head `2fcce6759e5d8071f66a35781dd834192f66b403`; all four required workflows passed, including the full unit suite (test-and-build run `39872383954`). CI was not re-checked on the merge commits. It removes the default core/exploration family sets, the regional artist-name list, the adventurous-tag list, the diversity-style artist and region lists, the `taste_profile_mode` setting and the fixed-vs-derived comparison tooling. `classify_diversity_style` now returns the candidate's primary derived family. Sparse listening history derives the core from the candidate pool (`candidate_pool_sparse_history`); no history and no pool gives an empty profile (`no_profile`).
- **Kept, deliberately:** the tag-to-family grouping rules, recent-style terms and display labels in `settings/taste_defaults.json`; they group and name genres rather than decide taste. Removing them would lose regional families such as African and Brazilian.
- **Category rule (owner chose "option 2"):** two or more core taste clusters = cross_genre; otherwise any exploration-family overlap = adventurous (still receiving the x1.10 bonus), even when the candidate also touches a core family; otherwise core overlap = adjacent; no overlap = adventurous. Reason: after #570 the old adventurous candidates were revealed as vocabulary-miss artifacts (labelled family `other`), leaving the category empty with its target unmet.
- **Exploration bonus review:** on the owner's capture the exploration set is only `electronic`; disabling the bonus changed 1 of the top 10. No weight change.
- **Replay:** captures now record taste clusters (a derived capture could not otherwise reproduce); a live capture on the #571 branch replayed with `reproduced: true`. Captures taken before this change no longer reproduce. Frozen-capture check of the final rule (160 candidates): adjacent 88, cross_genre 32, adventurous 28, unclassified 12; selected top 10 = 4/3/3 with all targets met and 7 of 10 picks unchanged. Two additional read-only live captures of the owner's profile were taken during this work (private, outside the repository, mode 600).
- **Limitations:** one real, jazz-leaning profile; no browser check of the new Deep Dives rows or the "Style:" label; no publication or deployment; focused tests only run locally.

## 2026-10-23 — Derived taste profile made the default (PR #569)

- The owner decided that derived mode becomes the default. PR #569 squash-merged as `b5c77c0b9f88782cc16d3971b5ab56d6f5e2f9aa` from exact head `5a38d1a4e8f658347c05703cebbef56db5573de6`; all four required workflows passed on that head (test-and-build, including the full unit suite, run `39870109947`). CI was not re-checked on the merge commit.
- `DEFAULT_TASTE_PROFILE_MODE` is now `derived`; absent or unknown stored values mean `derived`, and `taste_profile_mode=fixed` restores the shipped tables. Sparse listening history still falls back to the complete fixed behavior.
- **Kept, not removed:** the fixed tables, regional artist list and adventurous tags (they back the `fixed` option and the sparse fallback). Deep Dives rows and tag-query labels still use the fixed vocabulary. Removing the fixed tables remains a separate owner decision.
- Expected effect for a user with no stored setting, from the owner's capture: adventurous candidates 47 to 15, 44 candidates receive the x1.10 exploration bonus where none did, 8 of the top 10 unchanged. Focused tests only were run locally; not published or deployed; no live-runtime or browser verification.

## 2026-10-23 — Derived taste profile: Phases 2-4 evidence merged (PRs #565-#568)

- Squash-merged to `main` in order, each brought up to date with `main` and merged only after the four required workflows passed on its exact head (compile, container-smoke, test-and-build with the full unit suite, validate-container; publishing skipped): #565 `218ce4cdfc6b152ef1cbe614e4fb661894bf8603` (head `603541dca892540474520c4a995ff9731b07b6b8`, test-and-build run `39868468298`), #566 `f81443bfe4ce8b26cce818bfa8ef7055523b3640` (head `55b13d9ee3809002351536cf7349cd8e84b45df8`, run `39868728929`), #567 `9d7a0e7e6459738af61ee7fa1d18251f7a511760` (head `83be06b4e97050ba6e4096a4cd8c3ad7bb3ee1ca`, run `39868997784`), #568 `4c2a95e19cc8c4e83ad34fce9f6e2e4f3aab3748` (head `85ab821a11d3b4d3b744abef1f3950f5e4f1560b`, run `39869256200`). CI was not re-checked on the merge commits. Phase 2 (defaults in `settings/taste_defaults.json`) was #563; the opt-in mode was #564.
- **What changed (derived mode only; `taste_profile_mode` stays `fixed` by default):** #565 adds `recommendation/taste_profile_evaluation.py` (synthetic fixed-vs-derived comparison). #566 groups unmatched tags by trailing root word, then a static Wikidata ancestry table (`settings/genre_ancestry.json`, rebuilt with `scripts/build_genre_ancestry.py`), then the head-noun fallback. #567 merges core families whose listens overlap (Jaccard >= 0.5) into taste clusters, so cross-genre needs two clusters. #568 adds `python -m recommendation.replay <capture> --compare-profile-modes`.
- **Live captures:** two captures of the owner's profile were taken with the owner's approval (read-only provider calls, isolated data directory, slskd disabled). The files are private, outside the repository, mode 600, and were not committed. The second capture replays to identical output.
- **Evidence on the owner's profile (155 candidates, aggregates only):** fixed vs derived with ancestry and clusters: adjacent 65 vs 101, cross_genre 36 vs 32, adventurous 47 vs 15, unclassified 12 vs 12; exploration-bonus candidates 0 vs 44. Frozen-capture ranking comparison of the top 10: the fixed run reproduces the capture; 8 of 10 recommendations are shared, mean rank shift 1.0, identical selected category mix, 7 vs 14 distinct families. The derived run had 8 Last.fm lookups absent from the capture (no popularity adjustment), so the 2 differing picks may partly reflect that.
- **Synthetic profiles (hand-written, not real listeners), adventurous share fixed to derived:** metal 0.9 to 0.3, classical 0.9 to 0.3, k-pop 0.5 to 0.2, mixed 0.5 to 0.4, jazz 0.4 to 0.5.
- **Limitations:** only one real profile (jazz-leaning) exists; no non-jazz capture. The ancestry table has errors (some metal subgenres map to rock) and 36 searched tags did not resolve. Deep Dives and tag-query labels still use the fixed vocabulary. Manual browser checks: none performed. No publication or deployment.
- **Next action:** the owner decides whether derived mode should ever become the default. Open levers if so: the exploration bonus (44 candidates vs 0) and the jazz-profile adventurous increase.

## 2026-10-22 — PR #560 merged: artist bios for instrumentalists

- PR #560 squash-merged as `ffff550c2336ca3dcd56a301c9ae7fffe9f0104b` from exact head `0f2ae27562a175e237a7c7364d380dae7b49f5a0`. Root cause of the missing album-panel bio: `_ARTIST_DESCRIPTION_RE` in `app/services/artist_bio.py` had no instrument terms, so Wikidata descriptions such as "American jazz saxophonist" were rejected and the bio came back empty. Added instrumentalist and ensemble terms.
- Tests actually run: `tests/test_artist_bio_service.py` (7 pass), plus a direct endpoint call returning bios for John Coltrane, Bill Evans, and Art Blakey. Required CI (compile, container-smoke, test-and-build, validate-container, validate-release-workflow) passed on that exact head; publishing skipped. No browser check; not published or deployed.
- The owner confirmed the section-label size and Deep Dives card spacing items are done, which closes the 2a list.

## 2026-10-22 — Published image v0.2.2

- Owner explicitly authorized publication. Annotated tag `v0.2.2` was pushed at `0b1111114e0e751928312e76a287123061640343`, the then-current `main` head. All four required workflows had passed on that exact commit.
- Release workflow "Publish Docker release" run [39835121956](https://github.com/abucalip/navi-librarian/actions/runs/39835121956) succeeded (`publish-release`; the validation job was skipped for a tag push). It enforces tag == current `main`, runs the container smoke test, and builds `linux/amd64` and `linux/arm64` with provenance and SBOM.
- **Published:** `ghcr.io/abucalip/navi-librarian:v0.2.2` and `ghcr.io/abucalip/navi-librarian:sha-0b1111114e0e751928312e76a287123061640343`; package version digest `sha256:8ec36eaea585292f73ff7ec3546d96e4c5bc135b08fb3ccbcee789675f3f3ea2` (from the GitHub Packages API). `latest` was not moved.
- **Not verified:** per-platform manifests were not inspected, the image was not pulled or run, and no GitHub Release was created. Not deployed; no live-runtime verification. Manual browser checks for the included UI changes remain waived/not performed; PR #526/#527 runtime checks remain outstanding.

## 2026-10-22 — PR #558 merged: Deep Dives artwork loading improvements

- PR [#558](https://github.com/abucalip/navi-librarian/pull/558) squash-merged to `main` as `d44c01669611bd11acfaa4f1197905afed7f9f08`, from exact tested PR head `976c86e77034322e53cc7aea9691fa840c2d6146`.
- Review blockers were resolved before merge: capped MusicBrainz result sets are recursively split so a truncated response cannot cause a missing album year to be negatively cached, and regression coverage exercises that case. The PR was aligned to current `main`.
- **Automated verification on the exact PR head:** full unit suite and Docker build passed in workflow `39827794898`; Python syntax passed in `39827794888`; container runtime smoke passed in `39827794833`; validation-only multi-architecture image check passed in `39827794825`; release-workflow validation passed in `39827794824`. The publishing job was skipped as intended.
- **Manual browser verification:** explicitly waived by the owner and not performed. Deep Dives artwork performance was not re-measured in a browser, so UI behavior/performance is not claimed as verified.
- No image was published, no deployment occurred, and live runtime was not verified. Publishing/deployment remain paused.
- Documentation closeout commits: `docs/PROJECT_STATUS.md` `05cd398b17055cf8724c44f9fdf5fd3892a704eb`; `docs/ACTIVE_WORK.md` `64fd0b6f9b29dab956ef14656dbf8a84e14b8a7c`; `PROJECT_LOG.md` `1ecf065b69384711de24cba31c71e7bd89f272a5`.

## 2026-10-22 — PR #557 merged: similar-to discovery labels

- Merged PR [#557](https://github.com/abucalip/navi-librarian/pull/557) by squash. Merge commit on `main`: `45cf5abe0257e70fe0d0573365259c2d0c7c2c10`; exact tested PR head: `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`.
- Adds `discovery/similar_artists.py` and tests for similar-artist matching; the server includes `similar_to` in recommendation payloads, and Recommendations/Personal discovery rows show “Similar to: …” when related listening-profile artists are available.
- Required workflows passed on the exact PR head: Python syntax/acquisition safety run 39807842253; container runtime smoke 39807842257; Docker packaging, full unit suite and image build 39807842282; release workflow validation 39807842267 (the `publish-release` job was skipped); validation-only multi-architecture image check 39807842351. No claim that the suite was rerun on the merge commit.
- The owner explicitly waived manual browser verification; it was not performed. No image was published, no deployment occurred, and production runtime was not verified.
- Also retired the old `~/navi-librarian-test/test-pr.sh` workflow in `docs/LOCAL_UI_TESTING.md`; the guide now refers to the replacement local test environment without relying on the obsolete helper.
- Documentation closeout commits: `docs/PROJECT_STATUS.md` bfd8a25d06f7475a88f2e1bfc8c8fa10570ff653; `docs/ACTIVE_WORK.md` 8cbed8f810792d713be9cb30b843c79c484099ec; `PROJECT_LOG.md` pending this entry.

## 2026-10-22 — Retire obsolete local UI test helper instructions

- Updated `docs/LOCAL_UI_TESTING.md` in commit `a8a63764036c265a30e322adccf134b5485f8f6d`: explicitly marked `~/navi-librarian-test/test-pr.sh` obsolete, removed its commands and helper-specific setup/report assumptions, and retained a current browser checklist requiring exact-SHA identification, isolated test data, disabled acquisition services unless authorized, and recording pass/fail/skip results. The document points to the replacement local test environment without inventing an unverified launcher command.
- Updated `docs/PROJECT_STATUS.md` in commit `ee15bacdac965442c85fd4999faf15343024b581` to reflect the documentation change and PR #557's outstanding manual browser gate.
- PR #557 head remains `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`; automated full-suite and required CI evidence previously passed on that head. Manual browser testing has not been performed. The instruction to merge did not explicitly waive the documented manual UI gate, so the PR remains unmerged pending the browser check or an explicit waiver. No publishing or deployment occurred.

## 2026-10-22 — PR #556 review; reconciled replacement PR #557

- Reviewed PR #556, “Add ‘Similar to’ labels to Recommendations and Personal rows.” Its base was the feature branch from merged PR #555, so retargeting it to `main` would include duplicated/conflicting stacked changes. Closed #556 as superseded and created replacement PR [#557](https://github.com/abucalip/navi-librarian/pull/557) directly from current `main`, preserving only the intended four-file change.
- Replacement PR head: `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`. It adds a directly tested `build_similar_to_lookup` helper, attaches `similar_to` to normal and ownership-review payloads, and updates the UI labels. No provider calls or recommendation ranking budgets were added.
- The first syntax/guard run failed because `recommend_new_music()` reached 461 lines, above its 450-line ceiling. The lookup construction was moved into the reusable helper, with a regression test. The next run showed 452 lines, so redundant blank lines were removed; the final exact-head syntax/size guard passed. No guard thresholds were changed.
- **Full unit suite:** passed on the exact final head in Docker packaging workflow run `39807842282`, job `test-and-build`; Docker image build also passed.
- **Required workflows on exact final head:** Python syntax/acquisition-safety run `39807842253` passed; container runtime smoke `39807842257` passed; Docker packaging/full unit suite/build `39807842282` passed; validation-only multi-architecture image check `39807842351` passed. Release workflow validation `39807842267` passed with its publishing job skipped.
- **Manual UI verification:** not performed in this session. `docs/LOCAL_UI_TESTING.md` requires browser checks against the exact tested SHA for UI-facing changes. PR #557 remains open and unmerged pending that gate. The owner may test with `~/navi-librarian-test/test-pr.sh 557` or explicitly waive the manual gate.
- No image publication, deployment, or live-runtime verification.
- **Next action:** complete or explicitly waive manual browser testing for exact head `8bd57c5a977a33f4772ffe47e3a2c35d166f89f4`; then recheck PR state and merge only if the gate is satisfied.

## 2026-10-22 — PR #555: artist bios and dashboard discovery UI refinements

- **PR #555** squash-merged as `f80254550369ed56b66e114faebb2b9fb72ed6bf` from exact head `58bbe0e4ef7320c14146a6fa4ea5a3ef0d266953`.
- Changes include the Wikidata `Accept: application/json` header and avoiding a 24-hour empty-bio cache when the Wikidata search request fails; artist bios on dashboard and discovery cards; removal of New Releases source/reason text; more specific low-confidence genre messaging; consistent “Adventurous discovery” labels; responsive row artwork sizing; Deep Dives album-year placement; smaller one-line category tags; and yellow year styling. Three artist-bio regression tests were added.
- **Full unit suite:** passed in GitHub Actions on the exact PR head, run `39806088731`, job `test-and-build` (“Run unit tests” succeeded). Docker image build succeeded in the same job.
- **Required workflows on exact head:** Python syntax check `39806088756` passed; container runtime smoke test `39806088730` passed; Docker packaging/full unit suite/build `39806088731` passed; validation-only multi-architecture image check `39806088814` passed. Release workflow validation `39806088786` passed with the publishing job skipped.
- **Manual UI verification:** the owner reported the PR was manually tested in the browser and all is working well. No separate browser test was run in this session.
- No image publication, deployment, or live-runtime verification. The existing publication/deployment pause remains in effect.
- **Next action:** retain the runtime-verification priority in `docs/ACTIVE_WORK.md`; do not publish or deploy.

## 2026-10-22 — PR #554: larger row artwork and artist bio on discovery rows

- **PR #554** squash-merged as `c9fcf3289f37984258aca5b62891d700c569d5c1` from exact head `8c8d473f3b9576fbf0dc278c702b9843b422d991` (branch `feat/dashboard-row-bios`, two feature commits plus one review fix). Ranked-row artwork is 96px (80px up to 1200px wide, 64px up to 620px wide). The artist bio now shows in the middle of every row on Recommendations, New releases, and Personal discoveries (previously only genre-connected Personal rows). "Add to your collection" and Saved rows are unchanged.
- Rows keep one height (the artwork size). The bio is clamped to two lines with an ellipsis; a bio that does not fit becomes a keyboard-operable toggle (`role="button"`, `aria-expanded`, Enter/Space) that grows only its own row and does not open the album panel. A review pass caught that the first CSS edit had also enlarged acquisition-row artwork; this was reverted before merge.
- **Tests run (focused only):** all `tests/*ui_contract.py` (251 passed) and `node --check static/app.js`. New contract file `tests/test_row_bio_expand_ui_contract.py`; the title-clamp count test now allows the bio clamp. The full unit suite was not run locally.
- **CI on the exact head:** Python syntax check, container runtime smoke test, and release-workflow validation passed. Docker packaging (`Validate Docker packaging`, run `39796796155`, which runs the full unit suite) and `Validate Docker image (publishing paused)` (run `39796795957`) had **not completed** when this entry was written, and the PR was merged before they finished. Their results are not recorded here; check them on `main`.
- **Manual browser check (`LOCAL_UI_TESTING.md`, `test-pr.sh 554`):** performed by the owner against this head, reported as "tested and working". Specific checklist items were not itemized, and performance was not measured.
- No image publication, deployment, or live-runtime verification.
- **Next action:** confirm the remaining CI runs for `c9fcf3289f37984258aca5b62891d700c569d5c1` finished green, then continue with the next item in `docs/ACTIVE_WORK.md` section 2a ("Similar to:" labels).

## 2026-10-22 — Live-runtime verification attempt for PRs #526 and #527 blocked by access

- Re-read current project status, requirements, development workflow, test plan, active work, and the merged PRs. Current `main` before this documentation update was `fbc806badd9006853d2ccab45af19101809cb15a`.
- Confirmed PR #526 is merged as `4fcd5ff78dc7cfebe99d289a49cd8505c6ca9138`; it retries only failed tracks from the same source, at most three times 30 seconds apart, and keeps a 15-minute recovery grace. Its automated regression tests and CI do not establish behavior against real slskd state strings or queue operations.
- Confirmed PR #527 is merged as `e03f4b35c66745f71b45f01481dbed5547c7a45e`; masked artist variants are inserted after the unmasked query. Its automated tests do not establish live search behavior or real no-match diagnostics.
- **Runtime verification not performed:** this session has no connection to the running Librarian host or slskd API. These changes have not been published/deployed. No live search was issued, no transfer was queued, and no production data was changed. Publishing/deployment remain paused.
- **Next action:** arrange authorized access to an isolated Librarian test instance connected to the real slskd service. Test failed-track retry/recovery using an isolated test acquisition, then test masked queries and no-match diagnostics. Do not claim completion until results are captured; do not use a production transfer as a test substitute.

## 2026-10-22 — Reconciled and merged PRs #530–#535

- **PR #530 — imported-album filtering:** squash-merged as `0b2bda011b86d2c08a0179e5df801c7891c10f9a` from exact tested head `c52af5d8f660500074e799c77ada9ded61d73ec3`. Required workflow runs passed: syntax/acquisition safety `39780311719`, Docker packaging/full unit suite/build `39780311736`, container smoke `39780311752`, validation-only multi-architecture `39780311800`, and release validation `39780311809` (publishing skipped).
- **PR #531 — mobile navigation:** original stacked PR closed as superseded. Reconciled replacement PR #546 merged as `f884f004de83a6c373c16699b560e25312b41a3d`, tested head `53026bcbff794c04b6f901aefeb4fa939403cd7e`. Required workflows passed on that exact head: syntax `39782554896`, Docker packaging/full unit suite/build `39782554899`, container smoke `39782554893`, validation-only multi-architecture `39782554867`, release validation `39782554862` (publishing skipped).
- **PR #532 — artist bio in album panel:** original stacked PR closed as superseded. Reconciled replacement PR #547 merged as `4e11053ae5d203a4287a27abb162b4a9d093bf60`, tested head `c20bb6d0ac00067f2e00dab41fa899183ccf1f0a`. Required workflows passed on that exact head: syntax `39782630505`, Docker packaging/full unit suite/build `39782630071`, container smoke `39782630499`, validation-only multi-architecture `39782630190`, release validation `39782630442` (publishing skipped).
- **PR #533 — equal-width ranked rows:** reconciled original branch without force-pushing and merged as `8beb5baac431e6916d434efd111d96d98c4b8d9b` from exact final head `2948e56185608c8c3d798f38690f022253831940`. Required workflows passed on that exact head: syntax `39783301040`, Docker packaging/full unit suite/build `39783300845`, container smoke `39783300851`, validation-only multi-architecture `39783300775`, release validation `39783301000` (publishing skipped).
- **PR #534 — stable acquisition rendering:** reconciled original branch without force-pushing and merged as `871d3dd4401e493315e38f021bcdeec7918e0900` from exact final head `aea6b57045f2de06cf2eba89d99663d58b6dc699`. Required workflows passed on that exact head: syntax `39783571973`, Docker packaging/full unit suite/build `39783572017`, container smoke `39783571955`, validation-only multi-architecture `39783572002`, release validation `39783571972` (publishing skipped).
- **PR #535 — card artwork loading:** reconciled original branch without force-pushing and merged as `785715320c45b0e79d5f93873953b85859d4891f` from exact final head `15a2195685af26eaab69246a4069e928336692a6`. Required workflows passed on that exact head: syntax `39783827113`, Docker packaging/full unit suite/build `39783827065`, container smoke `39783827116`, validation-only multi-architecture `39783827092`, release validation `39783827150` (publishing skipped).
- The owner explicitly waived manual browser checks for this merge batch; none were performed. No artwork before/after performance measurement was made. No image publication, deployment, or live-runtime verification occurred. All temporary validation PRs were closed. The original #531/#532 PRs were closed as superseded; #530 and #533–#535 were merged directly.
- **Next action:** verify the already-merged #526 and #527 behavior against the live slskd runtime only with appropriate authorization; do not publish or deploy.

## 2026-10-22 — Open PR review and full-suite validation for PRs #530–#535

- Reviewed all six open product PRs. PR #530 (imported-album cache filtering) has no code-review blocker identified and its exact final head `df3dd651051826f483831b5a868dd16483f75fa4` passed all required CI, including the full unit suite: syntax/acquisition-safety run 39772679218; Docker packaging/full suite/build 39772679339; container smoke 39772679292; validation-only multi-architecture image 39772679145; release workflow 39772679160 (publishing job skipped; validation-only job passed).
- Reviewed UI stack PRs #531–#535. Main findings: all five are stacked on branches rather than `main`, starting from closed stale PR #529; required workflows filter pull requests to `main`, so there were no CI runs on their original head SHAs. Manual browser checks required by `docs/LOCAL_UI_TESTING.md` have not been performed. Do not merge these original PR heads until the stack is rebased/reconciled and final-head CI plus browser checks are complete.
- To exercise the cumulative UI changes against current `main` without altering original PR branches, created temporary validation-only commits by overlaying the changed-file state through each PR onto current main, then closed the temporary validation PRs after testing. These commits are integration test candidates, not the original PR heads:
  - Through #531: `53026bcbff794c04b6f901aefeb4fa939403cd7e`; all four workflows passed (syntax 39779026542; full suite/build 39779026314; smoke 39779026388; non-publishing multi-arch 39779026309; release validation 39779026400).
  - Through #532: `c20bb6d0ac00067f2e00dab41fa899183ccf1f0a`; all four passed (syntax 39779175672; full suite/build 39779175738; smoke 39779175835; non-publishing multi-arch 39779175783; release validation 39779175705).
  - Through #533: `da4a3e72146ec60c8c0c700f4ed5f387bf864723`; all four passed (syntax 39779276986; full suite/build 39779276674; smoke 39779276863; non-publishing multi-arch 39779276675; release validation 39779276967).
  - Through #534: `d319d8c5cc5f661a834035dabf99a26a1431655a`; all four passed (syntax 39779388308; full suite/build 39779388280; smoke 39779388596; non-publishing multi-arch 39779388383; release validation 39779388204).
  - Through #535: `1d803c6f1daf198d3c77741cbbb5c51eb5c490e0`; all four passed (syntax 39779671933; full suite/build 39779672016; smoke 39779672162; non-publishing multi-arch 39779671942; release validation 39779672201).
- Release workflow publishing jobs were skipped; validation-only multi-architecture builds passed. No image was published, no deployment occurred, and no manual browser or live-runtime verification is claimed. The local checkout attempt failed because the environment could not resolve github.com; full-suite evidence above comes from GitHub Actions.
- No product PR was merged. Next action: review/merge #530 if desired, then reconcile #531–#535 onto current main and run required checks on the actual final PR heads plus manual browser checks.

## 2026-10-22 — PR #529 reconciled; full CI suite passed on replacement PR #530

- Closed stale PR #529 because its branch predated the current `main` and its `discovery/list_payload.py` version omitted PR #528's cached future-release filter. Replacement PR #530 is based on current `main` and retains both behaviors.
- Exact tested PR #530 head: `34b926249a6e71aeab4e2243500fa91eb47e226b`; compare reported 3 commits ahead, 0 behind at review time. Changed files: `discovery/list_payload.py`, `navidrome_server.py`, `tests/test_discovery_list_payload.py`.
- Regression coverage hides imported acquisition identities across lists, excludes library-owned items from non-personal lists, preserves the future-date filter, and keeps imported items hidden when the library snapshot fails.
- Exact-head CI: Python syntax/acquisition safety run 39772357314 passed; Docker packaging/full unit suite/image build run 39772357012 passed (the full unit-test step succeeded); container runtime smoke run 39772356995 passed; validation-only multi-architecture image run 39772356972 passed. Release workflow run 39772357053 skipped the publishing job; its validation-only build completed successfully. No image was published.
- PR #530 remains open and unmerged. No manual browser or live-library/runtime check was performed; not published or deployed. Next action: review final PR state and merge #530 if all gates remain green, then continue live-runtime verification of #526/#527.

## 2026-10-22 — PR #528 merged: hide future-dated New Releases

- Squash merge commit on `main`: `1e55da1b7b25fe59d4f905a1c9d8985e8c8c7750`; exact tested PR head: `295148dcf817479f4098195200ada4c4173733fe`.
- Candidate selection now excludes release groups dated after today, including partial dates using their earliest possible day. Cached New Releases responses also hide stored future-dated items, so stale cached lists are corrected on read.
- Regression coverage: `tests/test_discovery_new_releases.py` and `tests/test_discovery_list_payload.py`; PR report records 46 focused tests passing and `py_compile` on `navidrome_server.py`.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety run 39770936745; Docker packaging/full unit suite/build 39770936858 (unit tests and image build passed); container runtime smoke 39770936556; validation-only multi-architecture image validation 39770936564. The release workflow's publishing job was skipped; its validation job passed.
- Full unit suite was run by CI on the exact PR head, not separately in the agent environment. No manual browser check or live-library verification was performed. Not published, deployed, or runtime-verified.
- Removed the resolved future-release bug from `docs/ACTIVE_WORK.md`; `docs/PROJECT_STATUS.md` records the merge. Next action remains live-runtime verification of PRs #526 and #527.

## 2026-10-22 — Exclusive “the owner” reference convention

- Added a permanent rule requiring all repository documentation, source comments, commit/PR text, reviews, issues, and other project communications to refer to the person directing the project exclusively as “the owner”; personal names and account usernames/handles must not be used for that person.
- Recorded the rule in `docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`, and `handoff.md`. Documentation-only changes committed directly to `main` as required. No application code changed; no application tests or CI were run.

## 2026-10-22 — Wildcard-masked artist queries for blocked slskd searches (PR #527 merged)

- PR #527 squash-merged as `e03f4b3` from head `8f51626677473aa069c81e34eaa9007f18cd6623`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Why: slskd blocks some artist names (e.g. "Gorillaz Plastic Beach" returns zero) although the music is on the network; replacing a first letter with `*` ("*orillaz Plastic Beach") bypasses it.
- Change: `integrations/slskd/search.py` adds `masked_artist_variants()`; `search_queries()` inserts the first-word-masked and every-word-masked artist queries right after the unmasked one, before the existing punctuation/parenthetical fallbacks. Words under 3 characters are not masked. No change to `search_polling.py`, candidate extraction or diagnostics.
- Tests: new cases in `tests/test_slskd_search.py` (single word, multi-word, short words); old query-list expectations updated in `test_slskd_search`, `test_slskd_search_modules` and `test_slskd_search_polling` (the latter two were missed on the first head and failed CI). Focused run of five slskd/acquisition modules with `.venv`: 32 OK. Live slskd behavior not verified.

## 2026-10-22 — Failed-track retry in the acquisition watcher (PR #526 merged)

- PR #526 squash-merged as `4fcd5ff78dc7cfebe99d289a49cd8505c6ca9138` from head `360e84287c01622fc19ba844954f55594a218ea9`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Bug: one errored slskd track stopped byte progress, so the watcher ended in `download_failed` or, after 120s, switched to a fallback source and re-downloaded the whole album. `acquisition/watcher.py` now re-queues failed tracks alone from the same source (3 tries, 30s apart) through the injected `queue_files` service, suppresses the stall switch meanwhile, keeps watching 15 minutes before `download_failed` so a manual slskd retry can recover, and ranks completed > live > failed records per file. Without `queue_files` the old immediate-failure behavior is kept.
- Tests: three regression tests in `tests/test_acquisition_watcher.py`; focused run only (13 OK). Not verified against a live slskd; real failure state strings are assumed (`Errored`, `Failed`, `Cancelled`, `TimedOut`, including slskd's `Completed, Errored` form).

## 2026-10-21 — Discovery package PR 4: gathering core (PR #524 merged); layout roadmap complete

- PR #524 squash-merged as `a5b14191c02007db376b0642ecceeef0426bdbd5` from head `69c9359e80aa4ff192a073f69b39bf6ffcdc02f1`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `candidate_gathering`, `batch_metadata`, `lb_tag_lane`, `tag_queries`, `library_snapshot`, `recommendations` into `discovery/`; `mock.patch` string targets rewritten. Root Python modules 9. Focused tests and `py_compile` only.

## 2026-10-21 — Discovery package PR 3: store, refresh and cooldown (PR #523 merged)

- PR #523 squash-merged as `04c0798ea528e53ce5485ea0410b4620b00b3098` from head `279eeee39559dd469238c60be84faef95e8fdbe4`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `store`, `snapshot`, `refresh`, `list_payload`, `candidate_supply` and `recommendation_cooldown` (as `discovery/cooldown.py`) into `discovery/`; root Python modules 15. `navidrome_server.py` keeps the `discovery_store` and `discovery_refresh` names via `from discovery import ... as`. Focused tests and `py_compile` only.

## 2026-10-21 — Discovery package PR 2: allocator (PR #522 merged)

- PR #522 squash-merged as `bcd34c956e177ae43fcb895cb79dbfb095ec6463` from head `d989557adb9d78f83cfc73bb50b212faef4ad984`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.
- Moved `allocation_contract`, `personal_allocator`, `mmr` into `discovery/`; root Python modules 21. Focused tests and `py_compile` only (104 tests OK locally).

## 2026-10-21 — Discovery package PR 1: leaf cluster (PR #521 merged)

- PR #521 squash-merged as `7fbea3a22d65cb5e3406981803392e91b7c15288` from head `2cf623a6ad24e4a8014eef9f4dae3ec8e7960d1d`; compile, test-and-build, container-smoke and validate-container passed. Not published or deployed.

- Moved `classics_candidates`, `classics_genres`, `classics_ratings`, `deep_dive_candidates`, `new_releases`, `recommendation_payload` from `discovery_*.py` into the new `discovery/` package (no re-export shims; the only callers were `navidrome_server.py` and five test modules, all updated). Dockerfile gains `discovery/ ./discovery/` and drops the six root names. Root Python modules 24. Packaging test `test_discovery_leaf_modules_live_in_discovery_package` added.
- Local: `py_compile`, `scripts/check_server_size.py` and the focused modules (`test_docker_packaging` plus the five moved-module tests) pass except 4 `test_discovery_new_releases` provider tests that need `httpx`, which the local python3 lacks (same 4 errors on clean `main`). Full suite not run. CI, merge, publish and deploy not done.

## 2026-10-21 — Acquisition PR 3 merged (PR #519); music_key inversion (PR #520 merged)

- PR #519 squash-merged as `6e12466` after compile, test-and-build, container-smoke and validate-container passed on head `c2f584b4f09e9e264268fb644f7f4b4900a7a27f`. Not published or deployed.
- PR #520 squash-merged as `b5e0622043737c89ccd4d4bfacb9881c366594f9` from head `886fb03c3a354738b1b51ced393783fe1aac80d5`; four checks passed; not published or deployed.
- `music_key` moved to stdlib-only `recommendation/music_key.py`; `integrations/lastfm/client.py`, `recommendation_feedback.py` and `recommendation/profile_comparison.py` import it from there. `discovery_recommendations` re-exports the same function (other callers and tests use it). `tests/test_music_key.py` proves output identical to the previous implementation. Behavior unchanged; focused tests only; `httpx` missing locally so the Last.fm client was checked by AST, not import.

## 2026-10-21 — Acquisition package PR 3 (open, not merged)

- Moved the five import/cleanup modules into `acquisition/`: `completion`, `import_files` (was `acquisition_import`; `import` is a Python keyword, so `acquisition/import.py` is not importable), `import_service`, `cleanup`, `recovery`. Callers, tests, Dockerfile COPY line and the `python-syntax.yml` compile entry updated; packaging test added. Behavior unchanged. Focused tests and `py_compile` only; the one failure is the known macOS `/var` case. Root Python modules 30. Not merged, published or deployed.

## 2026-10-21 — Acquisition package PR 2 (PR #518 merged)

- Moved five monitor modules into `acquisition/`; details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `32b23176e1c22317ad1ce662b8ca22cb8970409d` from head `29e7879beb162098cc612e27e4781e1ba40bf6e4`; four required checks passed. Not published or deployed.

## 2026-10-21 — Acquisition package PR 1 (PR #517 merged)

- Moved eight request/queue modules into `acquisition/`; owner approved this order and the `music_key` fix, and `recommendation_cooldown` moving with the store modules. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `2411740dc74d57b1a4fddbd33eeef80a461b40dd`, exact head `cd39e83ee7abe50378c015d4486b6306d4690270`, four required workflows passed. Root modules 40. Publication, deployment and runtime verification not performed. Next steps in `CLAUDE_CLI.md`.

## 2026-10-21 — Package layout design note (docs-only)

- Audited `main` `f84dfce` with an AST import graph plus grep. slskd: nothing left to move. `acquisition_*` (18): no outward dependencies, only `navidrome_server.py` calls them; proposed `acquisition/` in three PRs. `discovery_*` (20): six server-only leaves and the 3-module allocator are safe; store/refresh and the gathering core are blocked by the `integrations/lastfm` -> `discovery_recommendations.music_key` inversion (needs an owner decision). `navidrome_server` stays. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. No code changed, no tests run. Next: owner picks the first move (recommended: `acquisition/` PR 1).

## 2026-10-21 — Listening profile move (PR #516 merged)

- Moved `listening_profile` into `recommendation/listening_profile.py` (no shim). Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only. Squash merge `adc66e88d522b0240ffc1c271643d7ba0a90e403`, exact head `462ffcb28456ff734522266c7f5fc4f8cae7ff93`, all four required workflows passed. Root modules 48. Next: design note for slskd leftovers, acquisition, discovery and the legacy server. See `CLAUDE_CLI.md`.


## 2026-10-21 — Settings package move (PR #515 merged)

- Moved `service_settings`, `settings_persistence`, `music_paths`, `data_directory` into `settings/` (no shims). Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Focused tests and `py_compile` only; Also archived `diagnose_categories.py` to `docs/archive/`; `read_only_command_policy` stays in root. Squash merge `766ffe487baa28f23f3880e42f6aa4689a9284ad`, exact head `1e5020dfcd7bd6551bf705588f9bb34f1b3c17d8`, all four required workflows passed. Root modules 49. Next: `listening_profile` -> `recommendation/`. See `CLAUDE_CLI.md`.
## 2026-10-21 — Recommendation replay/diagnostics package move (PR #514 merged)

- Moved `recommendation_replay`, `recommendation_diagnostics`, `recommendation_mmr_evaluate`, `recommendation_profile_comparison` into `recommendation/` (no shims). `replay._REPOSITORY_ROOT` adjusted to the repo root. Merge `431c152642809e2aad1a36a556ac47610d0ddaa2`, exact final head `b636fcf2298f27b76befc3285034fe03285a32a0`, four required workflows passed. Root Python modules 54. `run_metrics`, `cooldown`, `feedback` stay in root. Focused tests and `py_compile` run locally; full suite not run. Publishing, deployment and runtime verification not performed.
- Next task: audit settings/paths group. See `CLAUDE_CLI.md`.

## 2026-10-21 — ListenBrainz integration package move (PR #513 merged)

- Moved `listenbrainz_client.py` and `listenbrainz_popularity.py` into `integrations/listenbrainz/` with canonical imports, no shims. Behavior unchanged. Details in `docs/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`. Merge `4e392e6660706191d080a5a2e9c66739377a5c33` from head `935d8984002bc6d690a2a6c09c315816dea9e16e` (owner named PR 513). Not published, deployed or runtime-verified.

## 2026-10-21 — PR #512 merged: Last.fm integration package

- Squash merge commit on `main`: `7282cbb740dba6e27fa79aecfe0de5519c18d859`; exact final PR head `84b4f04b27025f35d1f8f353b152a78ee886ef59`, all four required workflows passed on it (syntax 39653199481, Docker packaging/full unit suite/build 39653199482, container smoke 39653199327, validation-only multi-architecture 39653199280). Merged on the owner's instruction naming PR 512.
- Owner rules added to `CLAUDE_CLI.md` (2026-10-21): agents never run the full test suite; documentation-only updates are pushed directly to `main`.
- Main also contains owner-merged PR #506 (`8e29044`, tag-triggered release workflow); out of scope here. Publishing, deployment and production-runtime verification remain unperformed.
- Next task: audit the ListenBrainz modules as their own boundary. See `CLAUDE_CLI.md`.

## Last.fm integration package move details (before merge)

- Base: `main` `13790f8` (all four workflows green on it). Moved `lastfm_client.py` to `integrations/lastfm/client.py` (new `integrations/lastfm/__init__.py`); `navidrome_server.py` now imports the canonical module and keeps its `_lastfm_*` adapters unchanged. No root shim: AST/grep audit found exactly one production importer (`navidrome_server.py`) and one direct test module (`tests/test_lastfm_client.py`, switched to the canonical path); no dynamic/string imports, no `__file__` or path assumptions, no workflow or script references besides the syntax compile list.
- Dependencies: the client imports `recommendation_run_metrics` and `discovery_recommendations.music_key` from the root. Both are stdlib-only leaf modules (no cycle) and resolve from `/app` in the image. `music_key` is only the default for the injectable `key_normalizer`; left as is to keep behavior unchanged. Decoupling it is a possible later cleanup, not part of this move.
- ListenBrainz modules (`listenbrainz_client`, `listenbrainz_popularity`) were inspected separately and not moved: three production call sites across `navidrome_server.py` and `discovery_candidate_gathering.py`, plus lazy imports, so they need their own audit.
- Docker: root `COPY` list drops `lastfm_client.py`; `integrations/` is already copied. Added a packaging regression test. Root-level Python modules: 61 to 60.
- Agent-side checks (macOS, venv from `requirements.txt`): `py_compile` on changed Python files; focused `tests.test_lastfm_client`, `tests.test_docker_packaging`, `tests.test_lastfm_recommendation_scoring` (26 tests OK); `scripts/check_server_size.py` OK. Full suite not run. CI on code head `76e5979d` (before this docs-only evidence commit): syntax [39652945862](https://github.com/abucalip/navi-librarian/actions/runs/39652945862), Docker packaging/full unit suite/build [39652945820](https://github.com/abucalip/navi-librarian/actions/runs/39652945820), container smoke [39652945713](https://github.com/abucalip/navi-librarian/actions/runs/39652945713), validation-only multi-architecture [39652945728](https://github.com/abucalip/navi-librarian/actions/runs/39652945728): all passed. PR is #512; the final head after this commit is re-verified in the PR checks.
- Not merged, published, deployed, or runtime-verified.

## 2026-10-21 — PR #511 merged: slskd integration package

- Squash merge commit on `main`: `84fbb68afa7929a0bedae4e178d37ad2b6255c5a`; exact final PR head: `00712197ea7ba48b4ae07735fb9a9a1100e1eab9`.
- Moved `slskd_client.py`, `slskd_quality.py`, `slskd_search.py`, `slskd_search_polling.py`, and `slskd_transfers.py` to `integrations/slskd/{client,quality,search,search_polling,transfers}.py`. Updated production imports in `navidrome_server.py`, preserving its adapters; updated direct-import tests, Docker packaging regression coverage, and the syntax workflow compile list. No old root-level shims were retained because the caller audit found no remaining direct imports requiring them.
- Root-level Python module count: 61 after the move, down from 66 before it.
- Four required workflows passed on exact PR head `00712197ea7ba48b4ae07735fb9a9a1100e1eab9`: syntax/acquisition safety [39649756998](https://github.com/abucalip/navi-librarian/actions/runs/39649756998); Docker packaging/full unit suite/build [39649757098](https://github.com/abucalip/navi-librarian/actions/runs/39649757098); container runtime smoke [39649756971](https://github.com/abucalip/navi-librarian/actions/runs/39649756971); validation-only multi-architecture image [39649757030](https://github.com/abucalip/navi-librarian/actions/runs/39649757030).
- The Docker packaging workflow's full unit suite passed. Agent-side focused tests and `py_compile` were not run because no fresh isolated checkout was available. Do not infer tests on the merge commit beyond the verified PR-head evidence.
- Published, deployed, and production-runtime verified: no. Publishing/deployment remain paused.
- Next task: refresh the dependency map on post-merge `main` and audit `lastfm_client.py` plus its callers, direct tests, dynamic imports, path assumptions, and Docker/CI references before deciding whether to move it to `integrations/lastfm/`. See `CLAUDE_CLI.md`.

## 2026-10-21 — Python package-layout PR #509 merged

- Squash merge commit on `main`: `8fe825a41c0122bd3fd6d3260ca8978cdbf0d27f`; tested PR head `c045865fea13e8944512fc5c987e609cbc41e443`.
- Moved the canonical MusicBrainz album-year and rating helpers into `integrations/musicbrainz/`; retained `musicbrainz_rating_client.py` as a compatibility shim for the legacy server; updated the album-year caller, focused tests, and Docker COPY list.
- Four required workflows passed on the exact PR head: syntax 39646429894, Docker packaging/full unit suite/build 39646429876, container smoke 39646429872, and non-publishing multi-architecture image validation 39646429885. Agent-side focused tests and `py_compile` were not run because a fresh checkout was unavailable.
- Root-level Python module count decreased from 67 to 66. Publishing/deployment remain paused; no release or production runtime verification was performed.
- Next action: audit the five `slskd_*` modules and all callers/tests before deciding whether a cohesive package move is safe; see `CLAUDE_CLI.md`.

## 2026-10-21 — v0.2 release preparation (PR #505)

- PR #505 merged by squash as `99c0b88ed885de8b3c36686d63736b19a9235392`, exact PR head `fb34440b4893cc7f65678c90ba6e333616c0479d`. Added `docs/RELEASE_v0.2.md`: draft user-facing notes, configuration migration cautions, and a release/deployment checklist. No application code changed.
- All four required workflows passed on exact merge SHA `99c0b88ed885de8b3c36686d63736b19a9235392`: Python syntax `39634236552`; Docker packaging/full unit suite/build `39634236630`; container runtime smoke `39634236733`; validation-only multi-architecture image validation `39634236750` (`push: false`).
- Modularization roadmap is closed. No GitHub Release was present at preparation time; an existing tag was not confirmed. The current workflow remains validation-only; no tag, release, image publication, deployment, or runtime verification was performed.
- Release state is prepared, not released. The release notes disclose that the PR #503/#504 Settings browser checks were waived. After this closeout commit, the exact final main SHA still needs all four required workflows checked before tagging. A deliberate publishing workflow path and explicit authorization are still required before publication/deployment.

## 2026-10-21 — PRs #504 and #503 merged

- **PR #504 — neutral LAN defaults:** squash merge `af78c9e9796c27c65f9503a64d61ca9c58357dba`; exact tested PR head `4263f9c5bf3400cf6a5846c0f81a253a177e9543`. Removes the private LAN IP default and uses neutral placeholders/docs; blank slskd URLs fail validation. All four required workflows passed on the exact head: Python syntax `39631742346`, Docker packaging/full unit suite/build `39631742366`, runtime smoke `39631742152`, and validation-only multi-architecture validation `39631742470`.
- **PR #503 — ListenBrainz token setting:** reconciled after #504, then squash merged as `c3d5e02a4e5f113bb2914b12986cdef41e5863b5` from exact final PR head `cd0d53cb9f962b361f7ea84abba12b32b7efb17a`. Reconciliation commits `f1b136669dc790842d86aa9e16a56abd28fc5aee` and `cd0d53cb9f962b361f7ea84abba12b32b7efb17a` carried the token API/service changes onto current main while preserving #504's blank-URL validation. Token is optional, validated against `[A-Za-z0-9_-]{1,200}`, stored in the existing settings DB, never returned by the API, and not sent to MusicBrainz; blank input preserves a saved token and the environment fallback remains. All four required workflows passed on the exact final head: Python syntax `39632632729`, Docker packaging/full unit suite/build `39632632823`, runtime smoke `39632632791`, and validation-only multi-architecture validation `39632633039`.
- The Docker packaging workflow ran the full unit suite for each tested head. No separate agent-side full-suite run was performed (standing workflow rule). Manual UI checks were waived by the owner and not performed. Publishing remains paused; no image publication, deployment, or production-runtime verification is claimed.

## 2026-10-21 — P1a deeper CF pool measured (PR #502, docs only)

- Owner waived P0h and approved one cold plus one warm run for `CF_MAX_PAGES` 4 vs 6 (test-only harness, not committed, fresh data dirs, slskd off, aggregate only).
- 4 pages: cold 25.2 s, warm 5.1 s, 117 candidate albums / 85 artists, 0 uncached recording lookups. 6 pages: cold 183.6 s (2 ListenBrainz 429s, batch fallback, 100 lookups, 47 albums), warm 10.0 s (162 albums / 109 artists). Final list 10 in all runs; overlap 4 of 10.
- Decision: keep `CF_MAX_PAGES = 4`. Single samples, order effect not excluded. No code change. PR #502 merged by squash as `6e0718699740ce96539321e6b82ce15c0f632c06` from exact final PR head `ba29be2429484620415232db91ef97471470826a`.

## 2026-10-21 — PRs #500 and #501 merged

- **PR #500** (`ui/deepdive-save-render-check`) merged by squash as `e911a26b87cf8d9c11bb2502d8f1c074190b7a4c`, from exact final head `97e0bbbffbf3efb7c47860d980e49b023323bd0c`. Docs-only rendered verification record: Playwright/Chromium observed four 44 px Save controls, unobstructed hit targets, `save`/`remove_for_me` behavior without acquire or list reload, retry state on HTTP 500, and no overflow at 375 px. Screen-reader/live-data checks not done. All four required workflows passed on exact head: Python syntax/acquisition safety `39622877712`, Docker packaging `39622877775`, runtime smoke `39622877823`, validation-only multi-architecture image `39622877814` (publishing paused).
- **PR #501** (`ui/saved-page`) merged by squash as `990c83d3c0fdee816d7b511a7c6bd347bc715532`, from exact final head `10d0defec37479606ebb9bca143a21eb9d5cfd7c`. Adds the Saved page to the header menu, reading existing `/api/discovery/for_me`; supports refresh/revisit, saved dates, owned-album indication, remove/undo, loading/empty/error states, and hides Get for owned albums. Also removes the footer copy per owner request. PR report says 5 focused UI-contract tests and all UI-contract modules passed, `node --check static/app.js` passed, and Playwright/Chromium checks covered menu/navigation, rows, save/remove without acquisition/reload, refresh/revisit, empty/failure states, and 375 px layout. Live Navidrome data and screen-reader checks not done. All four required workflows passed on exact head: Python syntax `39626079394`, Docker packaging/full unit suite/build `39626079244`, runtime smoke `39626079346`, validation-only multi-architecture image `39626079497` (publishing paused).
- Publishing, deployment, and production-runtime verification remain unperformed. Exact PR heads were CI-verified before merge; no separate local full-suite run was performed.

## 2026-10-21 — PR #499 merged: P0i stale-flag audit (documentation only)

- PR #499 (`docs/p0i-stale-flag-audit`) merged by squash from exact final head `b5404cfcb80f65d36d61f309bb8c90b54d40b091`; merge commit `90d127eb46b0528a12ea0255ba81f25e1617ac4a`.
- Updated active status wording to reflect the current genre circuit-breaker and batch/title-filter defaults after PRs #495–#498. Corrected the tag-lane early-stop test docstring. No application code or defaults changed; dated historical experiment records were retained.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `39621883615`; Docker packaging/full unit suite/build `39621883770` (`test-and-build`, unit tests and image build succeeded); container runtime smoke `39621883534`; validation-only multi-architecture image validation `39621883758` (non-publishing).
- No separate local full-suite run (owner rule); CI ran the full suite. Publishing, deployment, and production-runtime verification remain unperformed.
- Next action: continue the active recommendation-engine roadmap from its top item; do not infer recommendation-quality or stable performance improvements from single samples.

## 2026-10-21 — Handoff: next task P0i (stale-flag audit, read-only then docs PR) (docs only)

- Pushed straight to `main` at the owner's instruction. `CLAUDE_CLI.md` hands off P0i: audit docs and comments against the post-#495 to #498 code defaults (known suspect: `docs/PROJECT_STATUS.md` still says the batch/breaker PRs are off by default), fix contradictions in a docs PR, no code or default changes, no network. P0h stays parked until ListenBrainz recomputes CF. No tests run (docs only).


## 2026-10-21 — Python package layout, first slice (PR #508 open)

- Branch: `refactor/package-navidrome-client`, based on main `86ad8de2bc1f08b86c4821969e017c15c3ef97bd`. PR: https://github.com/abucalip/navi-librarian/pull/508.
- Moved the Navidrome client implementation to `integrations/navidrome/client.py`, added package initializers, updated production imports, retained `navidrome_client.py` as a compatibility shim, updated direct-import tests, and added the package to Docker COPY.
- Regression coverage added for identity of the legacy re-export and canonical callable. Agent-side focused tests and `py_compile` were not run: the execution environment could not resolve github.com for a fresh checkout. No stale local checkout was used.
- All four required workflows passed on exact head `cffb5486d6fedb091979e397ff545a22fd0502cf`: Python syntax/acquisition safety `39639446692`; Docker packaging/full unit suite/build `39639446681` (unit tests and image build succeeded); container runtime smoke `39639446683`; validation-only multi-architecture image validation `39639446720` (non-publishing). This documentation closeout advances the PR head, so the four workflows must be checked again on the new exact head. Not merged, published, deployed, or runtime-verified.


## 2026-10-21 — Python package-layout first move merged (PR #508)

- Squash merge: `f171a4e73915222292642ba17d6dcb568b8c929a`; exact tested PR head: `a6fe1bd656f77ae4fbd65cb94c067949d14cf140`.
- Moved the Navidrome/Subsonic client implementation to `integrations/navidrome/client.py`; added package initializers, switched production imports, retained and tested `navidrome_client.py` as a compatibility shim, updated direct-import tests, and added `integrations/` to Docker packaging. ASGI entry point unchanged.
- Required CI passed on exact PR head: syntax/acquisition safety run 39639612889; Docker packaging/full unit suite/build 39639612870; container runtime smoke 39639612822; non-publishing multi-architecture validation 39639612866.
- Agent-side focused tests and `py_compile` not run because the execution environment could not obtain a fresh GitHub checkout. No stale local checkout used. No publishing, deployment, or production runtime verification.
- Next: regenerate/review the dependency map against post-merge main, finish the remaining module/caller/path/test inventory, and choose the next cohesive move only after checking dynamic imports, compatibility, and Docker assumptions.


## 2026-10-21 — slskd integration package move opened as PR #511

- Code commit: `2530192b703cdc023406ad8415008a5aa37fcbd5`, based on current main `ea4d50e2384617ba365d11b93f5f4f789af6e019`. Moved the five slskd modules into `integrations/slskd/`, updated lazy/top-level legacy-server imports and direct-import test paths, removed the root module copies, added a Docker package-presence regression test, and updated the syntax workflow compile list.
- Refreshed dependency-map artifact ID `12368421891` from the audit workflow confirms independent module imports; exact artifact SHA-256 is `22440f9cabed53f77f21abbdeb0593a9553fbdcc5bc0791d0ff46498d5185ca5`. The artifact source SHA is audit head `8ba095c17040ea5dd40ab19ad36e132acb4ab2ee`, whose application source matches the main baseline.
- All four required workflows passed on code head `664639724ef9d1cbf5edd1603a41ccb14a372ce3`: syntax/acquisition safety `39649449299`, Docker packaging/full unit suite/build `39649449147`, container smoke `39649449405`, and validation-only multi-architecture `39649449373`. A docs-only follow-up changes the PR head, so exact-final-head CI must be rechecked. Agent-side focused tests and `py_compile` were not run due lack of a fresh checkout. Not merged; publishing/deployment/runtime verification not performed.


## 2026-10-22 — Documentation consolidation and redesign archive

- Documentation-only commits on `main`: `96e2c0d445e6b63523700dbb209849fef69ab14a` (archive and active-doc rewrite) and `04d5be51aa6d54e17499517a31ad731c09c6771a` (remove stale redesign/modularization references). This log closeout is a follow-up commit.
- Created `docs/ACTIVE_WORK.md` as the short current task queue; reduced `CLAUDE_CLI.md` to a pointer; shortened `docs/PROJECT_STATUS.md` to a current snapshot; reduced `docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md` to remaining gates; moved permanent process and UI safety/accessibility rules into `docs/DEVELOPMENT_WORKFLOW.md` and `docs/TEST_PLAN.md`.
- Archived redesign-specific files, including root `AGENTS.md`, `DESIGN.md`, the Impeccable surface brief, design system, front-end guide, roadmap, UI backlog, and status-icon task notes. Archived completed modularization/package-layout/MCP-retirement plans, historical recommendation research, parked diversity/backlog proposals, CF/repeat-rate reports, and v0.2 release preparation under `docs/archive/`. Original file blobs were preserved.
- Updated `PRODUCT.md`, `docs/ARCHITECTURE.md`, and `docs/TEST_PLAN.md` to remove stale references to active redesign and modularization roadmaps.
- Closed superseded documentation PRs [#358](https://github.com/abucalip/navi-librarian/pull/358) and [#368](https://github.com/abucalip/navi-librarian/pull/368) with explanatory comments; their proposed status corrections are retained in the archive.
- Verification: re-read the resulting GitHub tree and active work/handoff/workflow files; confirmed archived files exist at their new paths and active handoff no longer points to redesign roadmaps. No automated link checker or application tests were run because this was documentation-only. No CI, publication, deployment, or runtime verification is claimed.
- Next action remains live-runtime verification of merged PRs #526 and #527; see `docs/ACTIVE_WORK.md`. Image publication/deployment remain paused.


## 2026-10-22 — Rename agent entry point

- Renamed the root `CLAUDE_CLI.md` handoff pointer to `handoff.md` in two documentation-only commits: `c2df9e820fff4ee3610eeb88988af51c0706a8ca` (add new path) and `b931899cca0b02cf27fb728865ce6d62b17a3fc0` (remove old path). The handoff content is unchanged; current queue and permanent rules remain in `docs/ACTIVE_WORK.md` and `docs/DEVELOPMENT_WORKFLOW.md`.
- No application tests or CI run; this was a documentation-only rename. No publication, deployment, or runtime verification performed.


## 2026-10-22 — Full test suite requires owner approval

- Updated `docs/TEST_PLAN.md` to state that manually running `python -m unittest discover -s tests -v` requires explicit owner approval. Without approval, agents run focused tests only; CI's `test-and-build` workflow continues to run the full suite on the PR head. Updated the stale handoff reference to `handoff.md`.
- Documentation-only commit: `841c8b2d912eac7032473558601bd7ec7ee87138`. No tests or CI run for this documentation-only change; no publication, deployment, or runtime verification performed.

## 2026-10-22 — Reconcile and merge PR #562

- Reconciled stacked branch `taste-families-server-labels` with the then-current `main` after PR #561 merged, preserving the PR branch as a parent and avoiding a force-push. Final tested PR head: `76142e1d0f2d48b59a1355e36c7372c4ed6f7123`.
- Reviewed the final diff: server API adds `genre_row` and `genre_row_label`; the UI consumes those fields rather than maintaining duplicate classification rules. The fallback behavior change for a small set of tags is described in the PR.
- Required workflows on the exact final head all passed: Python syntax (`39860454090`), Docker packaging/full unit suite (`39860454167`), container runtime smoke (`39860454213`), and validation-only Docker image validation (`39860454082`). Release-workflow validation (`39860454120`) passed; the publishing job was skipped. Manual browser verification was explicitly waived by the owner and was not performed.
- PR #562 squash-merged as `650a72718bfcd40a63ce67c5f869e71fd3a18d85`. Documentation closeout commit: `82f9be0c41455c035a1abf729d7a290483e1fdce`. No image publication, deployment, or live-runtime verification.



## 2026-10-23 — Review, test, and merge PR #574

- Re-reviewed the reconciled PR head `cc23a8005e554713f31eb0ab8594d2efa70b8d1e`. The cache correction now reads misses with the 7-day TTL first and only falls back to the 30-day TTL for positive values; Last.fm error 6 is treated as definitive not-found, while other errors, non-200 responses, malformed payloads, and exceptions remain uncached. Regression tests cover miss expiry, positive-value expiry, and transient failures.
- All four required workflows passed on that exact PR head: Python syntax/acquisition safety (`39954186109`), Docker packaging/full unit suite/image build (`39954186084`), container runtime smoke (`39954186218`), and validation-only multi-architecture image validation (`39954186167`, publishing paused). The full unit suite therefore ran in CI on the exact reviewed revision; no separate local full-suite run was performed.
- Squash-merged PR #574 as `eb4cb16ec5b932b4dc21a8978149f200931b1334`. The module remains unwired into runtime recommendation paths. No publication, deployment, or runtime behavior verification was performed.
- Review caveat: cache and provider behavior is covered offline with stubs; live provider behavior was measured in the prior capture but not re-run as part of this PR review.

## 2026-10-22 — Close approved runtime verification tasks

- The owner confirmed that failed-track retry/recovery and masked slskd artist-query behavior have been tested and approved. These are removed from the active work queue; no further verification task remains for those behaviors.
- Updated `docs/ACTIVE_WORK.md` in `22c54d99e118eb89ba9fff143c26419b78fbf8b6` and `docs/PROJECT_STATUS.md` in `6157b273155264db880dbecc78b53239465e29c5` to reflect the confirmation and remove stale outstanding-verification references.
- The v0.2.2 image remains published and not deployed. Approval of the behavior tests does not itself authorize deployment.
- Next eligible repository task: begin the behavior-preserving taste-family vocabulary consolidation described in `docs/HARDCODE_REPLACEMENT.md`; document current mapping differences and do not change canonical behavior without the owner's decision.


## 2026-10-22 — Merge PR #563 and review PR #564

- PR #563 externalized the existing taste-family defaults to `settings/taste_defaults.json`; squash-merged as `9a659f6e9da175e475aa22f86c69492f40206869` from exact PR head `0de6a16c6058c053f0948c6b46c74f50092b7bf9`. All four required workflows passed on that head: Python syntax `39861151203`, Docker packaging/full unit suite/build `39861151000`, container runtime smoke `39861150857`, and validation-only multi-architecture image validation `39861150831`. The Docker packaging workflow's full unit suite passed on the exact head. No publication or deployment.
- Retargeted PR #564 to `main` after #563 merged. Review of head `9cae06937a4dc65e9a3f12be484f008a0a49d839` found that sparse-history fallback returns fixed core/exploration sets but retains `profile_mode="derived"`, so fixed-mode classification exceptions remain disabled. Posted a review comment requesting an effective-mode fix and regression coverage. GitHub rejected a formal REQUEST_CHANGES review because the PR was authored by the connected account; the finding was posted as a COMMENT review instead.
- No workflow runs are visible for PR #564's current head after retargeting, so the requested full suite and four required CI workflows are **not verified** on that head. The repository workflow says agents do not run the full suite manually; it must run in CI. PR #564 remains open and unmerged. Derived mode remains off by default; multi-profile replay evidence and owner approval are still required before enabling it.
- No manual UI checks, publication, deployment, or runtime verification were performed.


## 2026-10-22 — PR #564 merged: opt-in derived taste profile

- PR #564 squash-merged to `main` as `508269f1177e35075330c903775f74e23c2f14af`, from exact tested PR head `6c08e385dccb21a28dd3b1e54531cb554ef26db8`.
- The sparse-history fallback issue was corrected: when derived profiling falls back to shipped defaults, the effective mode is now `fixed`, preserving fixed adventurous-tag and regional artist fallback behavior. Regression coverage checks effective mode, classification, and exploration bonus.
- All four required workflows passed on the exact PR head: Python syntax/acquisition safety `39862938840`; Docker packaging, full unit suite and image build `39862938736`; container runtime smoke `39862938685`; validation-only multi-architecture image build `39862938695` (`push: false`). The full unit-test and Docker-build steps succeeded. These runs are associated with the PR head, not the squash merge commit.
- The stacked branch's review diff included already-merged #563 changes, but comparison of the squash merge commit against pre-merge `main` shows only the seven derived-profile files changed; #563 defaults are not duplicated in the net merge diff. No separate branch reconciliation commit was created before merge.
- Derived mode remains off by default. Multi-profile replay evidence is not supplied and enabling the mode requires a separate owner decision. No image publication, deployment, or runtime verification was performed.


## 2026-10-23 — Re-review, full CI suite, and merge PR #578

- Re-reviewed final PR head `f15dbde3fe78ddb4974178b84f863de85de0fd69`. The earlier album-identity correction uses normalized `album_key` for album overlap, union, and reference overlap; the latest fix calculates `total_picks` from selected candidate IDs rather than unique album keys. Regression coverage includes duplicate album identity within one list and across lists/reference.
- All four required workflows passed on that exact head: Python syntax/acquisition safety (`40007720479`), Docker packaging/full unit suite/image build (`40007720478`; unit tests and image build succeeded), container runtime smoke (`40007720476`), and validation-only multi-architecture image validation (`40007720523`; publishing paused). The full unit suite ran in CI; no separate local run was performed.
- Squash-merged PR #578 as `3aebacbd40d80386199e0e5cb9b1b0ca94ca430d`. The metrics are pure evaluation code, not wired into runtime; they describe list composition and do not measure listening quality. No image publication, deployment, or runtime verification.
- Phase 2 evaluation metrics are complete. Next action: Phase 3 time-range profiles and window-driven tag-lane seeds. Any live capture or provider-budget increase still requires owner approval.

## 2026-10-24 — PR #583: Engine 2 Phase 3 history profiles

- PR #583 squash-merged from exact reviewed head `e4635b5b06e7dc04c6c6a9c3613c6bef531f2a69` as merge commit `09a958dfb39411f5b31f4ca9a79899e27221e6ef`.
- Added pure, unwired helpers for repeated-track artist weights, dominant-tag selection, tag-filtered artists, listening bursts, newly heard artists, dormant artists, and ListenBrainz artist-MBID mapping fallback. No runtime wiring, publication, or deployment.
- All four required workflows passed on the exact PR head: syntax/acquisition safety (`40087423103`), Docker packaging/full unit suite/image build (`40087423092`), container runtime smoke (`40087423107`), and non-publishing multi-architecture image validation (`40087423108`). Focused tests were reported as 35 tests plus a filtered 551-test subset; not rerun locally. The PR notes one existing unrelated test-collection error in `tests/test_service_settings.py::test_listenbrainz_connection` when running locally; CI's full suite passed.
- Post-merge container smoke workflow is running; publishing/deployment and runtime verification are not complete.

## 2026-10-24 — Re-review and merge PR #584: repeated-tracks lens

- Re-reviewed final PR head `2e59968bf1e78abe37ea75a8c0ee80023eb400fd` against `main` `d5107bda20f400fe46914ec67ad492fc403a9b6e`. The earlier concern about colliding normalized tag style identifiers was addressed: `select_supplementary_tag_queries` assigns deterministic unique suffixes to distinct selected tags, with regressions for `raï`/`rai` and `hip hop`/`hip-hop` plus separate profile/exploration namespaces.
- The repeated-track seed builder uses cached artist tags and listening history only, applies the configurable play threshold and dominant-tag exclusion, and performs no I/O. `REPEATED_TRACKS` reuses the Deep cuts gates but is not in `DEFAULT_LENS_ORDER`; runtime recommendation paths and default partitions remain unchanged. The proposed gates are still pending owner approval, and no provider/live-album evaluation was performed for this lens.
- All four required workflows passed on the exact final PR head: Python syntax/acquisition safety (`40089767320`), Docker packaging/full unit suite/image build (`40089767317`; `Run unit tests` and `Build Docker image` both succeeded), container runtime smoke (`40089767356`), and validation-only multi-architecture image validation (`40089767293`, non-publishing). No separate manual full-suite run was performed; repository workflow says CI runs the full suite and agents do not run it manually. No manual UI check was applicable.
- Squash-merged PR #584 as `82e06c6321107d3803761b65cab9a985bb686e42`. No publication, deployment, or runtime verification; image publication remains paused.
- Next action: owner decision on the proposed repeated-tracks lens gates before any runtime wiring; keep this lens unwired until that decision.


## 2026-10-24 — Re-review, full CI suite, and merge PR #585

- Re-reviewed the updated PR head `34ec1a962a809cac86f735dfcf32422dc92f8646`. The prior same-name artist concern is addressed by comparing MusicBrainz IDs when both candidate and library artist IDs are available, with a name fallback when either identity is unresolved. Regression tests cover distinct same-name MBIDs, shared library identity, missing IDs, unresolved same-name library records, and history-MBID matching. Known artists are rejected before consuming seed/artist slots. Repeated tracks accepts one tag while Deep cuts retains the two-tag minimum. No runtime wiring was added.
- All four required workflows passed on that exact head: Python syntax/acquisition safety (`40092120752`), Docker packaging/full unit suite/image build (`40092120821`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40092120755`), and validation-only multi-architecture image validation (`40092120772`, non-publishing). CI ran the full unit suite on the exact reviewed head. No separate agent-run full suite was performed, per repository workflow rules.
- Squash-merged PR #585 as `2706dda68c594a6d683cd6c6bc00feb2d9869d00`. The new lens remains unwired; no provider calls, publication, deployment, or runtime verification were performed.
- Next action remains owner decision on the proposed Repeated tracks selection gates before any runtime wiring.


## 2026-10-24 — Re-review, full CI suite, and merge PR #586

- Re-reviewed PR #586 at exact head `3007590f0214c94b3694ad6a4ff8da089fb11f80`. The diff cleanly removes `Lens.min_tags`, restores Repeated tracks to the shared Deep cuts two-tag minimum, and updates the regression test to cover zero, one, and two tags for both lenses. The known-artist exclusion from PR #585 is untouched; the repeated-tracks lens remains outside `DEFAULT_LENS_ORDER`, so no runtime/default recommendation behavior changes.
- All four required workflows passed on that exact head: Python syntax/acquisition safety (`40093298924`), Docker packaging/full unit suite/image build (`40093299008`; unit tests and image build succeeded), container runtime smoke (`40093299033`), and validation-only multi-architecture image validation (`40093299077`, non-publishing). CI ran the full unit suite on the exact reviewed head. No separate agent-run full suite was performed, per repository workflow rules.
- Squash-merged PR #586 as `f53a2cf2d3c1a1ce65703ded66c421ae2434d274`. No provider calls, publication, deployment, or runtime verification were performed.
- Next action: write the owner-approved Obsessions lens definition; separately explore another tag source or an exception for artists with no genre tags. Any new live run still requires owner approval.


## 2026-10-24 — Re-review, full CI suite, and merge PR #592

- Re-reviewed the updated PR head `09fb6e8d907d49fdefad4925a6b91c2e394abe5d`. Both findings from the previous review were fixed: `refresh_lens_lists` now calls the build/gate before ownership or storage access, and a non-gathered result reports `failed` rather than `disabled`. Regression tests assert the setting-off path touches no library, ListenBrainz, gatherer, or store, and that failed gathering preserves stored lists and reports failure. Diff review covered all five changed files; storage keys are namespaced as `lens:<name>`, read-time ownership filtering preserves ranks, and the replacement policy keeps previous usable lists when candidates are invalid/partial.
- All four required workflows passed on exact PR head `09fb6e8d907d49fdefad4925a6b91c2e394abe5d`: Python syntax (`40105619986`), Docker packaging/full unit suite/image build (`40105619974`, with `Run unit tests` and `Build Docker image` successful), container runtime smoke (`40105620007`), and validation-only multi-architecture image validation (`40105619975`, publishing paused). Release workflow `40105620017` succeeded with its publish job skipped. Per workflow policy, the full unit suite was run by CI, not manually by the agent.
- Squash-merged PR #592 as `0a8f9090fbb218f6508b33d9e72ebedbcdc64fd1`. Lens lists are now refresh/serve-wired but remain behind `engine2_lens_lists_enabled`, default off. No live provider run, publication, deployment, or runtime verification was performed.
- Next action: inspect the Phase 4 roadmap and define the next bounded slice before implementation.


## 2026-10-24 — Re-review, full CI suite, and merge PR #593

- Re-reviewed final PR head `1004251872937e3d6eef8cbcd2db033fbe5c0da3`. The previous blocker was fixed: `discovery.lens_service.list_response()` now checks `engine2_lens_lists_enabled` before reading the store or checking library ownership. Regression tests cover all three lens names through both the service and API route, asserting the disabled response without store/library access.
- All required checks passed on the exact final head: Python syntax (`40106383183`), Docker packaging/full unit suite/image build (`40106383162`, including successful `Run unit tests` and `Build Docker image` steps), container runtime smoke (`40106383137`), and validation-only multi-architecture image validation (`40106383191`). Release-workflow validation (`40106383120`) succeeded with publication skipped. Per repository workflow policy, the full unit suite ran in CI, not manually.
- Squash-merged PR #593 as `8ef9eb6e1f6e7099ae0369f0bd2471872fab816b` from exact reviewed head `1004251872937e3d6eef8cbcd2db033fbe5c0da3`. The lens service is now outside `navidrome_server.py`; lens lists remain gated by the default-off setting and are not wired into the recommendation path. No live provider run, image publication, deployment, or runtime verification was performed.
- Next action: define the bounded Phase 4 slice 4 (UI) scope before implementation.


## 2026-10-24 — Re-review, full CI suite, and merge PR #597

- Re-reviewed final PR head `017b4a81b7c5e8ba21d490584e2d2044cd3ef6b7`. The prior blocker was fixed: Last.fm API error payloads (including HTTP 200 errors) and unexpected response shapes now raise, allowing the window walk to fall back to ListenBrainz. Added regression tests cover API errors, malformed shape, valid empty history, single-track object responses, and fallback to ListenBrainz. The rest of the history-fetch tests cover pagination, source alternation, deduplication, floor/threshold behavior, and the page-cap diagnostic.
- All four required workflows passed on the exact PR head: Python syntax (`40113690376`), Docker packaging/full unit suite/image build (`40113690375`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40113690363`), and validation-only multi-architecture image validation (`40113690367`, publishing paused). CI ran the full unit suite on the exact head; no separate manual full-suite run was performed.
- Squash-merged PR #597 as `c653aab4526c450b84a2071bf8d0e0ea701891ed`. The actual starting threshold is 2000 usable listens, not the stale 500 mentioned in the PR description; the owner decision remains open. Discover's separate `recent_listens` paging bug remains tracked in PR #598. No publication, deployment, or runtime verification.


## 2026-10-24 — Re-review, full CI suite, and merge PR #598

- Re-reviewed exact PR head `96582e1a87d9908ed4ad1e23a68eb6d8d8fe5e3c`. The Discover `recent_listens` path no longer sends `min_ts` on every page, which returned the oldest page within the bound; it pages newest-first using `max_ts` and filters each page to the requested window. Regression coverage verifies request parameters and dropping out-of-window records.
- All four required workflows passed on that exact head: Docker packaging/full unit suite/image build (`40113450803`; unit tests and image build succeeded), container runtime smoke (`40113450800`), validation-only multi-architecture image validation (`40113450804`, publishing paused), and Python syntax/acquisition-safety/modularization checks (`40113450816`). CI ran the full unit suite on the exact head; no separate manual full-suite run was performed.
- Squash-merged PR #598 as `80e1ea2164ab4c3329a80d8c8947b88336bf5e4d`. Main was verified at that SHA after merge. No post-merge workflow run was visible at closeout; no publication, deployment, or runtime verification was performed. The PR description includes a live API check by the author; it was not independently repeated.

## 2026-10-24 — Review, full CI suite, and merge PR #602

- Reviewed exact PR head `7276e04a6fe7f1dde31496de46e7f5779be3da3c` across all five changed files. Request metadata (including the lens for Get requests) is passed to all three import-watcher success/uncertain paths; watcher startup persists it at initial acquisition state. Later status writes that omit metadata preserve the stored value, while a write with `metadata: {}` explicitly clears it to prevent stale lens attribution on a later personal-list request. Existing quality-summary preservation, candidate/settings retention, locking, reservation and file-handling behavior remain intact.
- Regression coverage added for omitted-versus-empty metadata and watcher persistence/defaulting. All four required workflows passed on the exact PR head: Docker packaging/full unit suite/image build (`40123851108`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40123851049`), non-publishing multi-architecture validation (`40123851089`), and Python syntax/acquisition-safety/modularization checks (`40123851118`; acquisition safety regressions passed). The full unit suite ran in CI, not separately locally. PR description reports one macOS-only temp-path assertion failure in local focused tests, also failing on untouched code; Linux CI passed.
- Squash-merged PR #602 as `46d8cb20c50bb89858cb62d727651e18da15ad17`. Backend-only; no manual UI test applicable. No image publication, deployment, or runtime verification.
- Phase 5 Get-to-lens acquisition attribution is implemented. Next: define/implement play and download attribution only after inspecting the available Navidrome/slskd events and choosing a reliable identity/attribution contract; do not infer listening-quality gains from save/dismiss counts.

## 2026-10-24 — Review, full CI suite, and merge PR #603

- Reviewed exact PR head `dccc555e565d4431affa5396e32d129c57fd6785` across all four changed files. The pure acquisition summary counts only jobs whose `details.metadata.lens` matches a known lens, handles malformed/non-mapping job data conservatively, and reports current persisted status counts. The service adds this object without changing save/dismiss counts or rates, and retains the default-off setting gate before feedback or acquisition-store reads.
- Regression tests cover known/unknown/missing lens metadata, malformed jobs, per-status counts, service output, and the API route. All four required workflows passed on the exact head: Docker packaging/full unit suite/image build (`40124369022`; `Run unit tests` and `Build Docker image` succeeded), container runtime smoke (`40124369071`), non-publishing multi-architecture validation (`40124369042`), and Python syntax/acquisition-safety checks (`40124369145`; acquisition safety regressions passed). Per repository policy, the full unit suite ran in CI, not manually by the agent. PR notes a combined focused-test ordering failure in `test_discovery_lens_storage`; the same failure was reported on unchanged code, and the full CI suite passed.
- Squash-merged PR #603 as `b1454b8697016bd2217ffbf15e50c03f074d3d08`. Counts are lower bounds because pre-PR #602 success rows lack lens metadata; counts represent current stored job state, not historical request events. Backend-only; no manual browser test applicable. No publication, deployment, or runtime verification.
- Phase 5 feedback API now includes acquisition status breakdowns. Next: decide UI consumption and inspect available Navidrome/slskd events before defining play/download attribution. Do not interpret these counts as complete request history or as evidence of recommendation quality.

## 2026-10-24 — Daily lens lists enabled by default (PR #605)

- **Merged:** PR #605, squash commit `b0d309a04cf84a5aa7f223998dd6b40c675d9dfd`, from reviewed head `f75fc061d6fc0ceba0aee35b892864699ff4bb36`; owner explicitly approved merge.
- **Change:** `engine2_lens_lists_enabled` now defaults to `True`; explicit `False` continues to exit before provider, library, and storage work.
- **Verification:** Required CI on exact PR head was green, including full unit suite and Docker build (run `40127475063`) and Python syntax/acquisition-safety checks (run `40127475121`). PR reports 135 focused tests passed. Three test-collection errors in `test_service_settings.py` were reported as pre-existing and also present on main; full CI suite passed.
- **UI gate:** Owner approved merge and deferred remaining browser checks (keyboard/focus, Get using a safe fixture, Save/dismiss, reduced motion, screen readers). Those checks were not performed against this exact PR head.
- **Release state:** Merged only. No image publication, deployment, or post-merge runtime verification.
