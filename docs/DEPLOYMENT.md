# Deployment runbook

Last updated: 2026-11-17

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

## Background worker

The `worker` service in `compose.yaml` (`python -m app.worker`, same image and `/data` volume as `discair`) runs all scheduled work: the automatic API fill, the insights refresh, the daily similar-artist precompute and, since efficiency W3, the scheduled refreshes of the recommendation lists (Personal, Classics, Artist Deep Dives, New releases, the listening profile and the daily lens lists). The web service starts no scheduler.

- **While the worker is down, recommendation lists do not refresh on schedule.** The app keeps serving the last stored lists; a manual refresh from the app still runs in the web service, and a stale Personal list read still starts its rebuild there. Check the worker with `docker compose ps worker` and `docker compose logs worker` when lists stop changing.
- Both services have `init: true` and a healthcheck (efficiency C3); `docker compose ps` shows `healthy` once they pass (up to 2 minutes after start). The web check requests `/api/auth/status` (public, no provider or store work). The worker check reads `DATA_DIR/worker.heartbeat`, a timestamp file the worker's heartbeat thread rewrites every 30 seconds only while both scheduler threads (`worker-schedule`, `worker-schedule-discovery`) are alive; it fails when the file is older than 5 minutes. A long similar-artist precompute therefore stays healthy, and a dead scheduler thread turns the worker `unhealthy`. `restart: unless-stopped` does not restart on `unhealthy`; use `docker compose restart worker`. No memory limits are set yet (waiting for measurements).
- **Owned prefetch (efficiency K3) is on by default** in `compose.yaml` (owner decision, 2026-11-17): the worker's `OWNED_PREFETCH_BUDGETS` defaults to the approved caps, and `.env` or the shell can override it. **To switch it off, set `OWNED_PREFETCH_BUDGETS=off`**: compose treats an empty value as unset and falls back to the default. Format: daily request caps per provider. The owner-approved default is `OWNED_PREFETCH_BUDGETS=musicbrainz=600,listenbrainz=300,lastfm=600,deezer=600,apple=400,wikipedia=300` (Discogs off). Name MusicBrainz and ListenBrainz (both page types use them); Last.fm and Discogs are used only when named. `deezer` fills the tracklist, artist photo and year fallback, `apple` and `wikipedia` (both needed) the album description, and `apple`, `deezer` and `musicbrainz` together the album links. `reviews` (the album review outlets together; not in the default, so off until the owner approves a cap) prefetches album reviews; the worker's compose service has no `GUARDIAN_API_KEY`, so the Guardian is left out there. A run stops when any one cap is reached. The coverage target (every owned artist and album handled within 21 days) is in `docs/plans/efficiency.md`, K3. A value with no valid cap (such as `off`) does nothing and makes no provider request. The job runs once a day for up to an hour, its spent counts survive a worker restart on the same local day, and its last coverage is under `prefetch` in `GET /api/diagnostics/runtime`. Any other caps need the owner's approval first (see `docs/plans/efficiency.md`, K3).
- Web and worker never refresh the same list at once: both record each list refresh as a job run in the knowledge store (`intelligence.sqlite3`, job `discovery_list_refresh`), and a refresh that finds its list running does nothing.
- Deploy both services from the same image version. An older web image still starts its own list scheduler, so during a mixed rollout lists can be refreshed twice.

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

## Sidebar Docker updates

A release image built with `APP_VERSION` shows its version in the desktop sidebar. Discair reads the public GHCR `latest` image configuration for its platform and offers an update when that image has a newer stable version. Source builds without a release version skip the registry check. The badge provides a release-tag link even on deployments that use manual updates.

Direct installation is optional. It requires a Compose project with the `discair` and `worker` services both using `ghcr.io/abucalip/navi-librarian:latest` and both configured with health checks. The Docker host needs Python with `httpx` and Docker Compose with `up --wait`. The example uses the repository's Compose files. For an existing stack, substitute its actual project directory and Compose files in both commands and keep its `.env`, service configuration, and volumes.

On the host, use a dedicated socket directory writable only by the updater account. The container runs as UID/GID 1000 by default. Give that group traversal and socket access, with the host account as the directory owner. Set the setgid bit so a new socket inherits the correct group. The following example assumes the host account is in GID 1000 and can already run Docker. Keep `DISCAIR_UPDATER_DIR` in the Compose project's environment for later commands.

```sh
export DISCAIR_UPDATER_DIR=/opt/discair-updater/socket
install -d -m 2750 -g 1000 "$DISCAIR_UPDATER_DIR"
python3 -m scripts.docker_updater \
  --socket "$DISCAIR_UPDATER_DIR/update.sock" \
  --project-directory "$PWD" \
  --compose-file compose.yaml --compose-file compose.updater.yaml
```

Run the host process under a supervisor for normal use, with the same working directory, account and environment. In another terminal on the host, with the same directory and environment, enable the socket mount for the first time.

```sh
docker compose -f compose.yaml -f compose.updater.yaml config --quiet
docker compose -f compose.yaml -f compose.updater.yaml up -d --no-deps --no-build discair
```

The web container receives a read-only socket-directory mount. Docker access stays with the host process. When the signed-in owner confirms an update, the host independently checks the digest, pulls the immutable image, recreates both services with their existing volumes, and waits for health checks. The web UI polls the host for completion through the restart. A successful update also refreshes the local `latest` tag. Set up a backup before updating if a rollback might require restoring data after migrations. On failure, check the host updater log and `docker compose ps`. The log records the previous web image ID before attempting the restart.

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

## Backup and restore

`scripts/backup_stores.py` copies every SQLite store under the data directory while the app and worker keep running. It uses the SQLite online backup API (`sqlite3.Connection.backup`), never a file copy: the stores run in WAL mode, so the main file alone (or a copy taken between its `-wal` and `-shm` files) is not a consistent snapshot. The source is never written. The script lists the stores explicitly (no glob); `tests/test_backup_stores.py` checks the list against the code that owns each file name.

Stores covered (relative to the data directory): `navidrome_discovery.sqlite3` (settings and saved credentials, acquisitions, discovery lists), `intelligence.sqlite3` (knowledge store, rebuildable), `intelligence.state.sqlite3` (owner decisions, not rebuildable), `navidrome_metadata_cache.sqlite3`, `provider_gate.sqlite3`, `radio.sqlite3`, `artwork/artwork.sqlite3` (image index) and `song_peaks.sqlite3`. A store that does not exist yet is reported as `skipped`. Not covered: `app_auth.key` (the web-session signing key; copy it with its mode 0600, or lose only the current logins), the cached artwork image files, and the music library.

The settings file holds credentials. Each copy is created with mode `0600` inside a backup directory with mode `0700`; keep it off shared or world-readable locations. The summary prints file names, sizes and `ok` / `skipped` / `failed (ErrorType)` only, never contents. Exit code 0 means every present store was copied and passed `PRAGMA integrity_check`; 1 means a copy failed or no store was found (usually a wrong data directory).

Run on the host, from a source checkout and its virtual environment, with the data directory of the deployment (for a Docker named volume, the volume's path on the host, or use the container form):

```sh
DISCAIR_DATA_DIR=/path/to/data python scripts/backup_stores.py --dest /path/to/backups
```

Inside the running container (the image does not include `scripts/`, so copy the script in first; it needs only the modules already in `/app`):

```sh
docker cp scripts/backup_stores.py discair:/tmp/backup_stores.py
docker exec -e PYTHONPATH=/app discair python /tmp/backup_stores.py --dest /tmp/backups
docker cp discair:/tmp/backups ./discair-backups
```

Each run writes a new `stores-<UTC timestamp>` subdirectory under `--dest`. The script refuses a destination inside the data directory (a backup stored in the volume it protects is not a backup), so the container form writes to `/tmp` and copies out; delete the temporary copy afterwards (`docker exec discair rm -rf /tmp/backups`), since it holds credentials.

Restore (stops all writers; the backup copies are single files with no `-wal` or `-shm`):

1. `docker compose stop discair` (the web process and the worker both run in this service; make sure nothing else writes to the data directory).
2. Keep the current files aside, for example `mv /data /data.before-restore`, or copy the ones you will replace.
3. Copy the wanted files from the backup directory into the data directory under the same relative names, and delete any stale `<name>-wal` and `<name>-shm` beside each replaced file. A leftover WAL from the old file would be replayed onto the restored one.
4. Set the mode of every restored file to `0600` and make sure the container user owns them (`chown`).
5. `docker compose up -d discair`, then check `docker compose logs --tail=100 discair` and sign in.

Partial restore: to recover only owner decisions after a knowledge-store wipe, restore `intelligence.state.sqlite3` alone and let the knowledge store rebuild; it attaches the state file beside it and the decisions are read again (covered by `tests/test_backup_stores.py`).

Not verified here: a run against the live host and its production-size stores, and the time a copy takes on a large knowledge store.

## Rollback

- Keep the previous working image tag/digest recorded before an upgrade.
- Revert the service image to that exact known-good version, then run `docker compose up -d discair`.
- Do not delete `librarian_data` during rollback; it contains persistent application state and authentication material.
- If an upgrade changes the database schema, confirm backward compatibility before reverting the image.


## Container runtime gate and publishing pause

The PR CI smoke test exercises the built container against disposable storage and temporary read-only music/download mounts. It verifies readiness, authentication/setup boundaries, private auth-key permissions, and owner-account persistence across a container restart using the same persistent /data volume. It does not connect to production services and is not production runtime verification.

The GitHub Actions Docker workflow is validation-only: smoke first, then multi-architecture validation for linux/amd64 and linux/arm64 with push: false, provenance and SBOM enabled. No GHCR login, registry tags, image publication, or deployment occurs. Publication remains paused until the modularization roadmap is complete and the user separately authorizes release.
