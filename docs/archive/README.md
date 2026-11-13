# Documentation archive

These files preserve completed roadmaps, redesign specifications, measurements, and parked proposals. They are historical evidence, not active instructions. For current work, start at [`../ACTIVE_WORK.md`](../ACTIVE_WORK.md), then follow the permanent rules in [`../DEVELOPMENT_WORKFLOW.md`](../DEVELOPMENT_WORKFLOW.md).

## Redesign — completed

- `redesign/AGENTS.md`: redesign-specific agent permissions and phased workflow, now superseded.
- `redesign/DESIGN.md`, `redesign/DESIGN_SYSTEM.md`, `redesign/app-templates-index-html.md`: shipped visual identity and its design contract.
- `redesign/REDESIGN_ROADMAP.md`, `redesign/UI_BACKLOG_EXECUTION.md`: phase history and implementation evidence.
- `redesign/FRONTEND_DESIGN_GUIDE.md`, `redesign/STATUS_ICON_DEV.md`: prior interaction/design guidance and specific UI task notes. Permanent UI safety, accessibility, and testing rules now live in the development workflow and test plan.

## Recently completed proposals and plans

The following documents were moved here after their implementation/build plans closed. The original paths contain short pointers for source-comment and contract compatibility:

- `completed/ALBUM_PAGE_REDESIGN_PROPOSAL.md` and `completed/ARTIST_PAGE_REDESIGN_PROPOSAL.md`: page layouts and API additions merged in PRs #634–#636; contract sections are authoritative. Browser verification was not claimed.
- `completed/ALBUM_PATHS_PROPOSAL.md`: all seven album path kinds, routes, fixtures and client screens built; owner checks after deployment remain.
- `completed/ANDROID_ART_THEMES_PROPOSAL.md`: Soft Brut and Flow build slices merged; owner phone review remains.
- `completed/palettes.md`: P1–P5 merged; owner phone comparison with palette mockups remains.
- `completed/BRUT_LAYOUTS_PLAN.md`: P1–P6 merged; the remaining owner phone/accessibility checks are still tracked in the active queue.
- `completed/HARDCODE_REPLACEMENT.md`: derived taste behavior replaced the hard-coded mode (PRs #561–#571).
- `completed/artwork.md`: all planned artwork slices merged; owner device/window checks and any open decisions remain outstanding.

## Completed engineering plans

- `completed/MODULARIZATION_ROADMAP.md`: completed domain modularization.
- `completed/PYTHON_PACKAGE_LAYOUT_ROADMAP.md`: root-module package-layout migration.
- `completed/MCP_RETIREMENT_PLAN.md`: repository-level MCP retirement. External-client migration remains unverified.

## Recommendation research and parked work

- `recommendations/RECOMMENDATION_ENGINE_IMPROVEMENTS_HISTORY.md`: full measurement log, experiments, and earlier task sequencing. The short active gates remain in `../RECOMMENDATION_ENGINE_IMPROVEMENTS.md`.
- `research/CF_PAGES_PROPOSAL_2026-10-20.md` and `research/REPEAT_RATE_MEASUREMENT_2026-10-20.md`: historical CF/repeat-rate findings; current interpretation belongs in the recommendation history.
- `parked/DIVERSITY_SETTING_ROADMAP.md`: diversity UI/calibration is paused.
- `parked/V0.2_DROPPEDNEEDLE_LESSONS.md`: optional ideas, not commitments.

## Release

- `release/RELEASE_v0.2.md`: preparation record only; it does not mean the release was published.
