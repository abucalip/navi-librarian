# Deployment runbook

Last updated: 2026-10-12

## Target environment

Current intended host is the Debian media VM at `192.168.1.12`, alongside the existing Docker media stack in `/opt/media-stack/compose.yml`.

Expected existing service endpoints:
- Navidrome: `http://navidrome:4533` from containers on the same Compose network, or `http://192.168.1.12:4533` from outside that network.
- slskd: `http://slskd:5030` from containers on the same Compose network, or `http://192.168.1.12:5030` from outside that network.
- Music library host path: `/media/library/music` (verify against the live host before deployment).
- Completed slskd downloads host path: `/media/downloads/slskd/complete` (verify against the live host before deployment).
- Proposed host UI port: `8689` for the media-stack deployment; container port is `8080`.

These are environment-specific examples. Confirm live paths, Compose network membership, and permissions before changing or restarting services.

## Registry prerequisite

The image name is `ghcr.io/abucalip/navi-librarian`. The GitHub Actions workflow is intended to publish `linux/amd64` and `linux/arm64` images on pushes to `main` and version tags.

**Current status (2026-10-12):** the user reports the Docker package has been made public and Librarian has been installed on the server and tested successfully. This supersedes the earlier `unauthorized` report as an active blocker. The exact deployed tag/digest and host-side pull/log evidence were not captured in this documentation update.

1. Package page: [GHCR package](https://github.com/abucalip/navi-librarian/pkgs/container/navi-librarian).
2. Confirm the publish workflow completed successfully for the intended commit/tag when preparing a future update.
3. Pull the intended tag. For reproducible deployment, record and use the resolved image digest where practical.
4. If a future pull returns `unauthorized`, re-check package visibility and host authentication rather than trying different tags as a workaround.

A Git commit SHA tag (for example, `sha-<commit>`) is a tag convention. An immutable registry digest is written as `ghcr.io/abucalip/navi-librarian@sha256:<full-digest>`.

## Add the service safely

Do not replace the existing Compose file. Add only the `navidrome-librarian` service and its top-level named volume if they are not already present. The named volume must be at the top level, not nested under `services`.

Illustrative service block (adapt network, paths, and settings to the actual file):

```yaml
  navidrome-librarian:
    image: ghcr.io/abucalip/navi-librarian:latest
    container_name: navidrome-librarian
    restart: unless-stopped
    pull_policy: always
    ports:
      - "8689:8080"
    environment:
      NAVIDROME_LIBRARIAN_DATA_DIR: /data
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

Preserve all existing service definitions and secret values. Do not copy redacted placeholders such as `******` into a live Compose file. Confirm whether the app actually needs write access to each bind mount before granting it; follow the current acquisition safety requirements.

## Preflight and deploy

Run from the directory containing the real Compose file:

```sh
docker compose config --quiet
docker compose pull navidrome-librarian
docker compose up -d navidrome-librarian
docker compose ps navidrome-librarian
docker compose logs --tail=100 navidrome-librarian
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
- Revert the service image to that exact known-good version, then run `docker compose up -d navidrome-librarian`.
- Do not delete `librarian_data` during rollback; it contains persistent application state and authentication material.
- If an upgrade changes the database schema, confirm backward compatibility before reverting the image.

## Artifact identity and container-runtime gate

The PR CI container smoke workflow starts the built image against disposable storage and checks HTTP readiness, authentication boundaries, first-run setup, private auth-key permissions, and persistence of the owner account across a container restart. It does not connect to live Navidrome/slskd services and is not a production deployment check.

For an image publication, use the GitHub Actions run summary from Build and publish Docker image to record:

- source commit SHA and trigger ref;
- immutable reference ghcr.io/abucalip/navi-librarian@sha256:<digest>;
- published tags and supported architectures (linux/amd64, linux/arm64);
- build provenance and SBOM status.

Before deploying, confirm the digest belongs to the intended commit and keep the previous known-good digest as the rollback reference. After deployment, independently confirm the running container's resolved image digest, persistent /data volume, service connectivity, logs, and required smoke tests. CI and a published image alone do not mark a release deployed or verified.
