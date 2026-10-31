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

## Phase 1 state

Setup screen, Librarian sign-in, Navidrome connection test, encrypted credential and session storage, themed shell. Nothing beyond the connection check is implemented yet.
