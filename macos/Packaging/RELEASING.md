# Releasing Discair for Mac

Nothing here publishes by itself. Publication stays paused until the owner authorises it (`docs/DEVELOPMENT_WORKFLOW.md`).

## One-time setup (the owner, on the owner's Mac)

1. Build once so Sparkle's tools exist: `swift package resolve`.
2. Make the update signing key: `generate_keys` from inside the `macos` folder: `./.build/artifacts/sparkle/Sparkle/bin/generate_keys`. The private key goes into the login Keychain
   (back it up with `generate_keys -x <file>` and keep that file out of the repository). It prints the **public** key; that one is not secret.
3. Put the public key in `Packaging/SU_PUBLIC_KEY` (done 2026-11-04; `bundle.sh` reads it, or `DISCAIR_SU_PUBLIC_KEY` overrides it).

An app built without the key runs normally but refuses every update (`UpdateConfiguration`, "no update signing key").

4. Make the local signing identity: `scripts/make-signing-identity.sh` (once; self-signed, stays in the login Keychain, no Apple account).
   `bundle.sh` then signs with it, so the app's trusted-app entry on the Keychain item stays valid across rebuilds and updates.
   It does **not** stop the prompt after an update: an app with no team ID is also checked by its per-build `cdhash` (the item's
   partition list, the "XARA" check in the `securityd` log), and every build has a new one. Expect one Keychain prompt after each
   update or rebuild and click **Always Allow** (plain Allow is not remembered, so it asks again on every launch). Ending the
   prompt needs an Apple Developer ID (a stable team ID) or keeping logins outside the Keychain; neither is decided.

## Each release

1. Raise `Packaging/VERSION` (shown version). The build number Sparkle compares is the commit count, so it always goes up.
2. `scripts/bundle.sh` makes `.build/bundle/Discair.app` (ad-hoc signed, Sparkle inside) and `Discair-<version>.zip`.
3. `scripts/appcast.sh` signs the zip with the private key and writes `.build/bundle/appcast/appcast.xml`.
4. Publish (only when authorised): a GitHub release `macos-v<version>` holding the zip, and the same `appcast.xml` uploaded to the
   fixed release `macos-appcast` (replace the asset each time). The app reads
   `https://github.com/abucalip/navi-librarian/releases/download/macos-appcast/appcast.xml`; a fixed tag is used because the
   repository's "latest release" belongs to the web and Android builds.

## Gatekeeper

No Developer account, so the app is not notarized. The first launch of a downloaded copy needs right-click > Open. Updates that Sparkle
downloads itself are not quarantined, so they open without that step; their authenticity comes from the EdDSA signature, not from Apple.
