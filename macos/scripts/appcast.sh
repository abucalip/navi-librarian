#!/usr/bin/env bash
# Signs the zip made by bundle.sh with Sparkle's EdDSA private key (kept in the login Keychain by generate_keys, never in
# this repository) and writes appcast.xml next to it. It publishes nothing.
#
#   scripts/appcast.sh [version]
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${1:-$(tr -d '[:space:]' < Packaging/VERSION)}"
OUT="${DISCAIR_OUT:-.build/bundle}"
TOOLS="$(find .build/artifacts -type d -path '*Sparkle/bin' | head -n 1)"
[ -x "$TOOLS/generate_appcast" ] || { echo "Sparkle tools not found; run swift package resolve" >&2; exit 1; }
[ -f "$OUT/Discair-$VERSION.zip" ] || { echo "run scripts/bundle.sh first" >&2; exit 1; }

STAGE="$OUT/appcast"
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp "$OUT/Discair-$VERSION.zip" "$STAGE/"
"$TOOLS/generate_appcast" --download-url-prefix "https://github.com/abucalip/navi-librarian/releases/download/macos-v$VERSION/" "$STAGE"
echo "appcast $STAGE/appcast.xml"
