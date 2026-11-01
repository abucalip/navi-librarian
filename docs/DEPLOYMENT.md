# Deployment runbook

Last updated: 2026-10-12

## Target environment

The intended host is a Debian media VM (`<host-ip>` below), alongside the existing Docker media stack (for example `/opt/media-stack/compose.yml`).

Expected existing service endpoints:
- Navidrome: `http://navidrome:4533` from containers on the same Compose network, or `http://<host-ip>:4533` from outside that network.
- slskd: `http://slskd:5030` from containers on the same Compose network, or `http://<host-ip>:5030` from outside that network.
- Music library host path: `/media/library/music` (verify against the live host before deployment).
- Completed slskd downloads host path: `/media/downloads/slskd/complete` (verify against the live host before deployment).
- Proposed host UI port: `8689` for the media-stack deployment; container port is `8080`.

These are environment-specific examples. Confirm live paths, Compose network membership, and permissions before changing or restarting services.

## Registry prerequisite

**Current release gate (2026-10-14): image publication is paused by project decision.** PR #32 is merged and the default-branch workflow validates only, with push disabled. Do not manually trigger image publication or push release tags until the modularization roadmap is complete and the user explicitly authorizes release.

**Current status (2026-10-12):** the user reports the Docker package has been made public and Librarian has been installed on the server and tested successfully. This supersedes the earlier `unauthorized` report as an active blocker. The exact deployed tag/digest and host-side pull/log evidence were not captured in this documentation update.

1. Package page: [GHCR package](https://github.com/abucalip/navi-librarian/pkgs/container/navi-librarian).
2. Confirm the publish workflow completed successfully for the intended commit/tag when preparing a future update.
3. Pull the intended tag. For reproducible deployment, record and use the resolved image digest where practical.
4. If a future pull returns `unauthorized`, re-check package visibility and host authentication rather than trying different tags as a workaround.

A Git commit SHA tag (for example, `sha-<commit>`) is a tag convention. An immutable registry digest is written as `ghcr.io/abucalip/navi-librarian@sha256:<full-digest>`.

## Add the service safely

Do not replace the existing Compose file. Add only the `discair` service and its top-level named volume if they are not already present. The named volume must be at the top level, not nested under `services`.

Illustrative service block (adapt network, paths, and settings to the actual file):

```yaml
  discair:
    image: ghcr.io/abucalip/navi-librarian:latest
    container_name: discair
    restart: unless-stopped
    pull_policy: always
    ports:
      - "8689:8080"
    environment:
      DISCAIR_DATA_DIR: /data
      NAVIDROME_MUSIC_DIR: /music
      SLSKD_DOWNLOADS_DIR: /downloads
      NAVIDROME_URL: http://navidrome:4533
      SLSKD_URL: http://slskd:5030
    volumes:
      - librarian_data:/data
      - /media/library/music:/music
      - /media/downloads/slskd/complete:/downloads

volumes:
  librarian_data:
```

The ListenBrainz user token is optional and is entered in Settings, under ListenBrainz, not in Compose. When saved, ListenBrainz requests also send `Authorization: Token <token>` alongside the app's honest `User-Agent`; when blank, behavior is unchanged. It is stored in the app's settings database (mode 0600, like the other saved credentials), never returned by the API and never sent to MusicBrainz. A `LISTENBRAINZ_TOKEN` environment variable is still read as a fallback but is no longer in the Compose file.

Preserve all existing service definitions and secret values. Do not copy redacted placeholders such as `******` into a live Compose file. Confirm whether the app actually needs write access to each bind mount before granting it; follow the current acquisition safety requirements.

## Preflight and deploy

Run from the directory containing the real Compose file:

```sh
docker compose config --quiet
docker compose pull discair
docker compose up -d discair
docker compose ps discair
docker compose logs --tail=100 discair
```

If using a source checkout instead of a registry image, follow [DOCKER.md](../DOCKER.md); do not mix source-build and registry-image procedures without checking the Compose configuration.

## Post-deployment verification

The user reports the current server installation was tested successfully, including first-run account creation, entering service credentials through Settings, downloads, and imports. Treat these as manually verified baseline workflows; this document update did not independently access the host or repeat the tests.

For a future deployment/update:

1. Confirm the container is running and logs contain no startup/configuration errors.
2. Open `http://<media-host>:8689` from the LAN.
3. Verify login and that the account/data survive a container restart.
4. Verify Navidrome connectivity and slskd settings/connection test.
5. Smoke-test recommendations, discovery lists, release years/artwork, Get/requested state, acquisition status, and dismiss behavior.
6. For destructive dismissal, use a known test album/folder and verify only the intended files are removed.
7. Record deployed image tag **and digest**, date/time, host, smoke-test result, and any deviations in `PROJECT_LOG.md`.

## Rollback

- Keep the previous working image tag/digest recorded before an upgrade.
- Revert the service image to that exact known-good version, then run `docker compose up -d discair`.
- Do not delete `librarian_data` during rollback; it contains persistent application state and authentication material.
- If an upgrade changes the database schema, confirm backward compatibility before reverting the image.


## Container runtime gate and publishing pause

The PR CI smoke test exercises the built container against disposable storage and temporary read-only music/download mounts. It verifies readiness, authentication/setup boundaries, private auth-key permissions, and owner-account persistence across a container restart using the same persistent /data volume. It does not connect to production services and is not production runtime verification.

The GitHub Actions Docker workflow is validation-only: smoke first, then multi-architecture validation for linux/amd64 and linux/arm64 with push: false, provenance and SBOM enabled. No GHCR login, registry tags, image publication, or deployment occurs. Publication remains paused until the modularization roadmap is complete and the user separately authorizes release.
