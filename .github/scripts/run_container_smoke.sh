#!/usr/bin/env bash
set -euo pipefail

IMAGE_TAG="${1:-navi-librarian:ci-smoke}"
CONTAINER_NAME="${2:-librarian-smoke}"
VOLUME_NAME="${CONTAINER_NAME}-data"
TEMP_ROOT="$(mktemp -d)"

cleanup() {
  status=$?
  trap - EXIT
  if [ "$status" -ne 0 ]; then
    docker logs "$CONTAINER_NAME" 2>&1 || true
  fi
  docker rm --force "$CONTAINER_NAME" >/dev/null 2>&1 || true
  docker volume rm "$VOLUME_NAME" >/dev/null 2>&1 || true
  rm -rf "$TEMP_ROOT"
  exit "$status"
}
trap cleanup EXIT

mkdir -p "$TEMP_ROOT/music" "$TEMP_ROOT/downloads"
docker build --tag "$IMAGE_TAG" .
docker volume create "$VOLUME_NAME" >/dev/null
docker run --detach \
  --name "$CONTAINER_NAME" \
  --publish 127.0.0.1:18080:8080 \
  --mount "type=volume,src=$VOLUME_NAME,dst=/data" \
  --mount "type=bind,src=$TEMP_ROOT/music,dst=/music,readonly" \
  --mount "type=bind,src=$TEMP_ROOT/downloads,dst=/downloads,readonly" \
  --env DISCAIR_DATA_DIR=/data \
  --env NAVIDROME_MUSIC_DIR=/music \
  --env SLSKD_DOWNLOADS_DIR=/downloads \
  "$IMAGE_TAG" >/dev/null

SMOKE_BASE_URL=http://127.0.0.1:18080 \
SMOKE_CONTAINER="$CONTAINER_NAME" \
  python .github/scripts/container_smoke.py
