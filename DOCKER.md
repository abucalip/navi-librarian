# Docker deployment

Navidrome Librarian runs as a standalone web app. Navidrome and slskd remain external services; this container does not bundle or start either service, and it does not start the separate MCP server.

## Requirements

- Docker Engine with the Compose plugin, on the machine that can access Navidrome, slskd, the music library, and slskd's completed-download directory.
- The host paths for the music library and completed downloads must be mounted into the container. The app may need write access to both when importing acquired albums.
- The music library and download paths below are examples. Verify the real paths on your host before starting the service.

## Configure

1. Copy `.env.example` to `.env`.
2. Edit `.env`: set Navidrome/slskd credentials and API key if required, and confirm both host directory paths.
3. Keep `.env` private; it contains credentials and is excluded from the Docker build context.
4. Ensure the configured directories exist and that container UID/GID 1000 can perform the required file operations.

## Run from a source checkout

```sh
docker compose config
docker compose build
docker compose up -d
docker compose logs -f navidrome-librarian
```

Open `http://<docker-host>:8080` (or the port set with `WEB_PORT`). Complete the first-run owner account setup in the web UI.

## Persistent data and upgrades

The named volume `librarian_data` stores the app's database and authentication key. Keep this volume when upgrading; deleting it resets the app's persistent state and authentication.

To upgrade a source-based deployment after pulling changes:

```sh
git pull
docker compose build
docker compose up -d
```

## GitHub Container Registry

Images are published by `.github/workflows/docker-release.yml` only when the owner authorizes a release tag (`vMAJOR.MINOR` or `vMAJOR.MINOR.PATCH`) that points at the exact current `main` commit. It builds `linux/amd64` and `linux/arm64` images and publishes `ghcr.io/abucalip/navi-librarian:<version>` and `:sha-<commit>`. The `latest` tag is **not** moved by releases, and pushes to `main` do not publish; `docker-publish.yml` is validation-only. The release build passes the tag as the `APP_VERSION` build argument, which the page rail shows; a local or untagged build shows `git describe` output or `dev`.

To deploy a published release, replace `build: context: .` in `compose.yaml` with `image: ghcr.io/abucalip/navi-librarian:<version>` (for example `v0.2.2`), remove the `build` section, then run `docker compose pull && docker compose up -d`. Keep the `librarian_data` volume and note the previous image tag or digest as a rollback reference. If the repository/package is private, authenticate to GHCR on the deployment host before pulling.

## Troubleshooting

- If Compose reports a missing bind-mount path, correct the corresponding `*_HOST_PATH` in `.env`; do not create an empty directory over an existing library mount by mistake.
- If imports fail with permission errors, check ownership and permissions on both host directories. The container runs as UID/GID 1000.
- If Navidrome or slskd is unreachable, verify the service URL from the Docker host and ensure its firewall/network permits connections.
