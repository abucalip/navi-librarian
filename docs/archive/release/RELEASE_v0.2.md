# v0.2 release preparation

Status: **prepared for review; not released or published**.

## Candidate snapshot

- Preparation started from GitHub `main` at `36a23b5b3b3fe6e0118af8e192462fb7cfd5fa6f` (2026-10-21).
- All four required GitHub Actions workflows passed on that exact commit:
  - Python syntax check: run 2229, https://github.com/abucalip/navi-librarian/actions/runs/39632904845
  - Docker packaging, full unit suite, and image build: run 2137, https://github.com/abucalip/navi-librarian/actions/runs/39632905042
  - Container runtime smoke: run 1946, https://github.com/abucalip/navi-librarian/actions/runs/39632905086
  - Multi-architecture image validation: run 1990, https://github.com/abucalip/navi-librarian/actions/runs/39632904996
- The multi-architecture workflow is validation-only (`push: false`); it did not publish an image.
- The repository had no GitHub Releases at preparation time. No existing tag was confirmed by this audit.
- The app has no discovered central package/version file; do not claim an in-app version string has been set.
- The open documentation PRs #358 and #368 are not included in this candidate because they are unmerged.

**Important:** this is the preparation baseline, not the final release SHA. After this document is merged, refresh `main`, verify all four workflows against the exact resulting SHA, and use that SHA for the release/tag and image provenance.

## Draft release notes — Navidrome Librarian v0.2

Navidrome Librarian is a self-hosted web interface for discovering albums missing from a Navidrome library and tracking acquisition through an existing slskd service.

### Highlights

- Music discovery surfaces for personalized recommendations, new releases from library artists, collection-building classics, and Artist Deep Dives.
- Saved albums view with save/remove and undo flows, ownership-aware rows, and loading, empty, and error states.
- Acquisition request and status workflows designed to keep request state visible without navigating away from discovery.
- Persistent Settings for Navidrome, slskd, Last.fm, ListenBrainz, and acquisition quality preferences.
- Optional ListenBrainz user token can be saved in Settings. The API exposes only whether a token is configured; the token is not returned to the browser and is not sent to MusicBrainz.
- More neutral connection URL defaults and stricter validation: missing/blank slskd URLs no longer silently fall back to a private LAN address.
- Container packaging targets `linux/amd64` and `linux/arm64`, with isolated runtime smoke testing and persistent application data.

### Deployment notes

- Navidrome and slskd remain external services; this application does not launch replacement instances.
- Existing deployments must provide valid Navidrome and slskd URLs in Settings/environment configuration. The application no longer silently supplies a private LAN IP for a missing slskd URL.
- ListenBrainz token entry is available in Settings. A previously configured `LISTENBRAINZ_TOKEN` Compose value was removed from the example Compose configuration; users relying on that old Compose entry should enter the token in Settings. The environment-variable fallback remains available if configured separately.
- Preserve the existing persistent `librarian_data` volume during upgrade or rollback.

### Known limitations and release cautions

- The Settings UI currently has no explicit way to clear a saved ListenBrainz token; submitting a blank value preserves it.
- The existing ListenBrainz “Test connection” action remains unauthenticated.
- Browser verification for the Settings changes in PRs #503 and #504 was waived by the owner and was not performed. Automated CI passed, but this is not evidence of rendered UI behavior.
- No release image, tag, deployment, or production-runtime verification has been performed.

## Release gate checklist

Do not mark v0.2 released until each applicable item has evidence:

- [x] Modularization roadmap is closed on GitHub main (completion audit recorded in `docs/MODULARIZATION_ROADMAP.md`).
- [x] Current preparation-baseline CI passed on exact SHA `36a23b5b3b3fe6e0118af8e192462fb7cfd5fa6f`.
- [ ] Merge this preparation document, refresh main, and verify all four workflows on the exact post-merge SHA.
- [ ] Review the final release diff and release notes; confirm no open, relevant blocker was overlooked.
- [ ] Obtain explicit go-ahead to perform the actual publication/deployment steps. “Prepare” does not create a release or publish an image.
- [ ] Review and merge PR #506, which adds `.github/workflows/docker-release.yml`: pull requests validate only (`push: false`); pushing a `vMAJOR.MINOR` or `vMAJOR.MINOR.PATCH` tag publishes `v*` and `sha-<commit>` image tags for `linux/amd64` and `linux/arm64`, with provenance/SBOM. The workflow requires the tag to point at the exact current `main` SHA and deliberately does not move `latest`.
- [ ] Create the GitHub release for tag `v0.2` only after the exact source commit is verified.
- [ ] Verify GHCR tag and immutable digest after publication; record both.
- [ ] Before deployment, record the existing image tag/digest as rollback reference and validate Compose configuration and persistent-volume mappings.
- [ ] After authorized deployment, verify container status/logs, service connectivity, persistence across restart, and the key discovery/acquisition workflows. Record deployed tag, digest, and evidence in `PROJECT_LOG.md`.

## Current state

Implemented: existing code and Docker packaging on main.  
Tested: four required workflows passed on the preparation-baseline SHA.  
Published: **no**.  
Deployed: **not verified by this preparation task**.  
Runtime verified: **not verified by this preparation task**.

The existing `.github/workflows/docker-publish.yml` remains validation-only. PR #506 prepares a separate tag-triggered publishing path, but until that PR is reviewed/merged and an authorized release tag is pushed, no registry image is published. This document does not create a tag, GitHub release, registry image, or deployment.
