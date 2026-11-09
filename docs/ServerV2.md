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

### Remaining slices

5. macOS: decode the taste body, call refresh on launch, Cupertino taste cards (lately-vs-always, window card with dimension picker, decades), low-sample and empty states. Filtered tests only.
6. macOS: the other Insights themes (Zine and the rest) draw their own versions, one follow-up PR per theme.
7. macOS actions: smart-playlist rule prefill and library filter.
8. Android: decode, refresh on launch, compact card and bottom sheet, `InsightsTest` cases.
9. Close-out: confirm profiles change no ranking output, visual and runtime checks, docs and log.

**Order:** 5; then 8 and 7; then 6; then 9.

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
