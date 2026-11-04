#!/usr/bin/env bash
# Makes a self-signed code-signing certificate named "Discair Local Signing" in the login Keychain, once.
# Signing every build with it (scripts/bundle.sh does when it exists) keeps the app's identity the same across rebuilds and
# updates, so the Keychain stops asking about the app again after each update. No Apple Developer account is involved, and the
# certificate is only ever used on this Mac; it does not make the app trusted by Gatekeeper.
set -euo pipefail
NAME="${DISCAIR_SIGN_IDENTITY:-Discair Local Signing}"
if security find-identity -p codesigning 2>/dev/null | grep -q "\"$NAME\""; then
    echo "\"$NAME\" already exists; nothing to do."; exit 0
fi
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/cert.conf" <<CONF
[req]
distinguished_name = dn
x509_extensions = ext
prompt = no
[dn]
CN = $NAME
[ext]
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,codeSigning
CONF
PASS="$(uuidgen)"
/usr/bin/openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -keyout "$TMP/key.pem" -out "$TMP/cert.pem" -config "$TMP/cert.conf" 2>/dev/null
/usr/bin/openssl pkcs12 -export -inkey "$TMP/key.pem" -in "$TMP/cert.pem" -out "$TMP/id.p12" -passout "pass:$PASS" 2>/dev/null
security import "$TMP/id.p12" -k "$HOME/Library/Keychains/login.keychain-db" -P "$PASS" -T /usr/bin/codesign >/dev/null
echo "Created \"$NAME\" in the login Keychain. Back it up (Keychain Access > export) if you want future builds to keep the same identity after a reinstall."
