# Server V2 — remaining work

**Updated:** 2026-11-09  
**Current state:** Server-side Phases 0–6 are closed. Phase 7 implementation is merged. Remaining work is client integration and explicitly listed runtime/visual verification; no Server V2 work is currently published or deployed. See [Project Status](PROJECT_STATUS.md), the [API contract](SERVER_V2_CONTRACT.md), and the [historical plan archive](archive/ServerV2_HISTORY_2026-11-09.md).

## Phase 6 — Taste presentation

### Contract context

- `GET /api/insights/taste` returns saved `profiles` and `context`; each is `null` until refresh has saved it.
- Clients call `POST /api/insights/taste/refresh` on launch, then render the saved response. There is no scheduler or server-startup hook. The one-hour minimum interval, overlap protection, and fail-closed ListenBrainz history reader are implemented.
- `profiles` includes the server-authored `headline`, recent/mid/all-time windows, dimensions, shifts and sample/attribution flags. Clients display the supplied headline and never invent a shift or compose replacement prose.
- `context` includes time-of-day and weekday/weekend lenses plus morning-vs-night contrast. Contrast is stated only when both contexts have at least 100 listens, attribution is sufficient, and the configured shift threshold is met; otherwise show the supplied low-sample/no-difference state.
- Sparse and empty data must remain honest. Taste profiles and context do not affect recommendation ranking.
- Design references: [macOS mockups](design/macos-taste/mockups.html) · [Android mockups](design/android-taste/mockups.html).

### Completed slices

7. **macOS taste card actions (PR [#909](https://github.com/abucalip/navi-librarian/pull/909), merged 2026-11-09):** adds genre/decade actions to the Cupertino shift and window cards. The owner can create a prefilled smart playlist and edit it, or open the Library Songs tab with a clearable taste filter. Area, label and collaborator deliberately have no action because they do not map to a Library song field. No playlist is saved to Navidrome until the owner saves it; recommendation ranking is unchanged. Seven filtered Swift tests were reported passing (`TasteActionTests`, `TasteModelTests`); all four required GitHub workflows passed on exact PR head `e0ae1c3d6b8bd1519e11900b6e336d314032f0af`. Squash commit: `872ad8c8ae9a1c5412f92c54484eba5efa3be874`. No manual visual Mac or live-server check; not published or deployed.

5. **macOS taste cards (PR [#907](https://github.com/abucalip/navi-librarian/pull/907), merged 2026-11-09):** decodes the taste response, refreshes once per app launch in the background, and presents the Cupertino Insights cards for lately-vs-always, selectable windows and dimensions, decades, low-sample progress and empty states. The server-authored headline and shifts are displayed without client-invented claims. Sixteen filtered Swift tests were reported passing; all four required GitHub workflows passed on the exact PR head. No live-server or visual/manual Mac check; not published or deployed.

8. **Android taste card and sheet (PR [#908](https://github.com/abucalip/navi-librarian/pull/908), merged 2026-11-09):** adds the taste response decoder and repository calls, once-per-app-launch background refresh, compact Insights card, and bottom sheet with recent, past-year (`mid`) and all-time windows, dimensions, listed movers, and honest low-sample/empty states. The app displays the server-authored headline and does not invent shifts or affect recommendation ranking. Seventeen focused Android tests were reported passing (`TasteTest`, `InsightsTest`); all four required GitHub workflows passed on exact PR head `598ac7c2f8e73b14ad63f4645e568b621b5c0927`. No device/emulator, accessibility or live-server check; the shared HTTP client's 30-second read timeout may expire before a long refresh completes (saved profiles remain). Not published or deployed.

### Remaining slices

6. macOS: the other Insights themes (Zine and the rest) draw their own versions, one follow-up PR per theme.
9. Close-out: confirm profiles change no ranking output, complete visual and runtime checks, and reconcile docs/log.

**Order:** 6; then 9.

**Acceptance:** both clients render the same server-authored headline; thin/empty data is represented honestly; launch refresh is safe and idempotent; no recommendation output changes.

## Phase 7 — Remaining verification

Implementation is merged. The following checks remain:

- **Path-cache warm-up:** run the bounded manual warm-up against a copy of the real store; record completion, duration and resource impact. The endpoint is resumable and local-store-only; it has no scheduler or startup hook.
- **Sonic API integration:** exercise the similar-track and song-to-song path routes end to end through the live Librarian server.
- **Sonic path UI:** visually verify the path preview on macOS and Android, including ordered steps and queue/play actions.

The owner waived the macOS Connections/Atlas/Timeline screen review, the discovery-path quality spot-check, and the sonic re-listen after the per-artist radio cap (2026-11-07). These are recorded waivers, not completed tests. The sonic path preview visual checks and live route checks above remain outstanding.

## Working constraints

- Keep provider/analysis work out of page requests; jobs and refreshes must remain bounded, resumable and fail safely.
- Preserve evidence and sample-state semantics; never turn missing data into a positive claim.
- Keep read-only intelligence separate from media mutation, acquisition and recommendation ranking.
- Follow `docs/TEST_PLAN.md`: focused tests for the change, required CI on the exact PR head, and manual UI verification after CI for UI changes. The owner runs the full local suite.
- Track implemented, tested, CI-passed, merged, published, deployed and runtime-verified as separate states.

## History

Completed phase plans, slice implementation details, PR/commit history, probes, measurements, decisions and earlier verification notes are preserved in [Server V2 historical snapshot](archive/ServerV2_HISTORY_2026-11-09.md). Do not use that snapshot as the active work queue.
