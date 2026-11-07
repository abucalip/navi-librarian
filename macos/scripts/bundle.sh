#!/usr/bin/env bash
# Builds Discair.app (release), embeds Sparkle, signs it (no Developer account, contract section 10: a local self-signed
# identity if one exists, else ad hoc) and zips it.
#
#   scripts/bundle.sh                      # app without an update key: runs, but never accepts updates
#   DISCAIR_SU_PUBLIC_KEY=<base64> scripts/bundle.sh
#
# Environment (all optional):
#   DISCAIR_SU_PUBLIC_KEY  Sparkle EdDSA public key (default: Packaging/SU_PUBLIC_KEY, the owner's public key; not secret).
#   DISCAIR_FEED_URL       appcast address, https only (default: the macos-appcast release of this repository)
#   DISCAIR_SIGN_IDENTITY  signing identity name (default: "Discair Local Signing" if scripts/make-signing-identity.sh made it, else ad hoc)
#   DISCAIR_VERSION        shown version (default: Packaging/VERSION)
#   DISCAIR_BUILD          build number Sparkle compares (default: number of commits)
#   DISCAIR_OUT            output folder (default: .build/bundle)
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION="${DISCAIR_VERSION:-$(tr -d '[:space:]' < Packaging/VERSION)}"
BUILD="${DISCAIR_BUILD:-$(git rev-list --count HEAD 2>/dev/null || echo 1)}"
FEED="${DISCAIR_FEED_URL:-https://github.com/abucalip/navi-librarian/releases/download/macos-appcast/appcast.xml}"
KEY="${DISCAIR_SU_PUBLIC_KEY:-$(tr -d '[:space:]' < Packaging/SU_PUBLIC_KEY 2>/dev/null || true)}"
OUT="${DISCAIR_OUT:-.build/bundle}"
case "$FEED" in https://*) ;; *) echo "DISCAIR_FEED_URL must be https" >&2; exit 1 ;; esac
[ -n "$KEY" ] || echo "note: DISCAIR_SU_PUBLIC_KEY is empty, so this app will not accept updates" >&2

swift build -c release --product Discair
swift build -c release --product DiscairWidget
BIN="$(swift build -c release --show-bin-path)"
SPARKLE="$(find .build/artifacts -type d -name Sparkle.framework -path '*macos-arm64_x86_64*' | head -n 1)"
[ -d "$SPARKLE" ] || { echo "Sparkle.framework not found; run swift package resolve" >&2; exit 1; }

APP="$OUT/Discair.app"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Frameworks" "$APP/Contents/Resources"
cp "$BIN/Discair" "$APP/Contents/MacOS/Discair"
for b in "$BIN"/*.bundle; do [ -e "$b" ] && cp -R "$b" "$APP/Contents/Resources/"; done
# App icons: Finder uses Discair.icns (Cupertino); the app swaps the Dock icon with the theme from the per-theme files.
cp Packaging/Icons/Discair-Cupertino.icns "$APP/Contents/Resources/Discair.icns"
cp Packaging/Icons/Discair-*.icns "$APP/Contents/Resources/"
ditto "$SPARKLE" "$APP/Contents/Frameworks/Sparkle.framework"

sed -e "s|@VERSION@|$VERSION|" -e "s|@BUILD@|$BUILD|" -e "s|@FEED_URL@|$FEED|" -e "s|@PUBLIC_KEY@|$KEY|" \
    Packaging/Info.plist.template > "$APP/Contents/Info.plist"
plutil -lint "$APP/Contents/Info.plist" >/dev/null

# The Notification Center widget: an app extension (contract section 10). Sandboxed, as WidgetKit requires.
APPEX="$APP/Contents/PlugIns/DiscairWidget.appex"
mkdir -p "$APPEX/Contents/MacOS"
cp "$BIN/DiscairWidget" "$APPEX/Contents/MacOS/DiscairWidget"
sed -e "s|@VERSION@|$VERSION|" -e "s|@BUILD@|$BUILD|" Packaging/DiscairWidget-Info.plist.template > "$APPEX/Contents/Info.plist"
plutil -lint "$APPEX/Contents/Info.plist" >/dev/null

# The executable finds Sparkle through @rpath.
if ! otool -l "$APP/Contents/MacOS/Discair" | grep -q "@executable_path/../Frameworks"; then
    install_name_tool -add_rpath "@executable_path/../Frameworks" "$APP/Contents/MacOS/Discair"
fi

# Signing identity: a stable self-signed one keeps the Keychain item's trusted-app entry valid across rebuilds; it does not remove the
# per-build cdhash prompt (no team ID), so expect one Always Allow per build. Ad hoc also changes the trusted-app entry every build.
IDENTITY="${DISCAIR_SIGN_IDENTITY:-Discair Local Signing}"
if ! security find-identity -p codesigning 2>/dev/null | grep -q "\"$IDENTITY\""; then
    echo "note: no \"$IDENTITY\" identity (run scripts/make-signing-identity.sh); signing ad hoc, so the Keychain will ask after each update" >&2
    IDENTITY="-"
fi

# Signing, inside out. No hardened runtime: an ad-hoc app has no team, so library validation would refuse Sparkle.
FW="$APP/Contents/Frameworks/Sparkle.framework/Versions/B"
for item in "$FW/XPCServices/"*.xpc "$FW/Autoupdate" "$FW/Updater.app"; do
    [ -e "$item" ] && codesign --force --sign "$IDENTITY" "$item"
done
codesign --force --sign "$IDENTITY" "$APP/Contents/Frameworks/Sparkle.framework"
codesign --force --sign "$IDENTITY" --entitlements Packaging/DiscairWidget.entitlements "$APPEX"
codesign --force --sign "$IDENTITY" "$APP"
codesign --verify --deep --strict "$APP"

ZIP="$OUT/Discair-$VERSION.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
echo "built $APP (version $VERSION, build $BUILD)"
echo "zip   $ZIP"
