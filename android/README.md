# Discair (Android client)

Native Android client for Librarian and Navidrome. Contract: [`docs/ANDROID_CLIENT_CONTRACT.md`](../docs/ANDROID_CLIENT_CONTRACT.md). Design decisions: [`DESIGN.md`](DESIGN.md). Recorded payloads: [`contract-fixtures/`](contract-fixtures/README.md).

## Build and test

Needs JDK 17 and the Android SDK (platform 36). Put `sdk.dir=<path>` in `android/local.properties` (not committed).

```
cd android
./gradlew testDebugUnitTest      # unit tests, including parsing of the recorded fixtures
./gradlew assembleDebug lintDebug
```

Fonts in `app/src/main/res/font` are converted from `static/fonts` (woff2 to ttf, unchanged glyphs); licences are in `licenses/`.

## Release build

`./gradlew assembleRelease` builds a minified, resource-shrunk APK. It is **unsigned** (and cannot be installed) until the owner supplies a signing key:

1. Create a keystore once and keep it and its passwords somewhere safe; losing it means a new app identity: `keytool -genkeypair -v -keystore discair-release.jks -alias discair -keyalg RSA -keysize 4096 -validity 10000`.
2. Create `android/keystore.properties` with `storeFile`, `storePassword`, `keyAlias` and `keyPassword`. The file and `*.jks` are git-ignored; never commit either.
3. `./gradlew assembleRelease` then writes a signed `app/build/outputs/apk/release/app-release.apk`.

## Phase 1 state

Setup screen, Librarian sign-in, Navidrome connection test, encrypted credential and session storage, themed shell. Nothing beyond the connection check is implemented yet.
