#!/bin/bash
# Runs discair-audio-spike with the Navidrome login taken from a local env file (default ~/Desktop/disqair/config.env).
# Nothing is printed or stored: the three values are only handed to the tool for this one run.
set -euo pipefail
ENV_FILE="${DISCAIR_ENV_FILE:-$HOME/Desktop/disqair/config.env}"
[ -f "$ENV_FILE" ] || { echo "env file not found: $ENV_FILE (set DISCAIR_ENV_FILE)"; exit 2; }
cd "$(dirname "$0")/.."
BIN=.build/release/discair-audio-spike
[ -x "$BIN" ] || swift build -c release --product discair-audio-spike >/dev/null
set -a; . "$ENV_FILE"; set +a
export DISCAIR_NAVIDROME_URL="$NAVIDROME_URL" DISCAIR_NAVIDROME_USER="$NAVIDROME_USER" DISCAIR_NAVIDROME_PASSWORD="$NAVIDROME_PASSWORD"
exec "$BIN" "$@"
