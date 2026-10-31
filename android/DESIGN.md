# Discair design decisions

Status: proposal, Phase 0. Produced with the `/mobile-design` skill (platform Android, Kotlin + Jetpack Compose, phone only, online first). Every screen type re-runs the skill and appends its decisions here. Visual identity comes from `static/app.css`; this file records only the Android-specific choices.

## Navigation
- Bottom navigation bar, icon plus visible label, 4 destinations: Home, Library, Search, Acquisitions (with active-count badge). Discovery lists beyond Home sit under Home as a tab row, not in a drawer. Settings opens from a top-bar action on Home.
- Artist, Album, Genre and list pages are stack destinations. System back and predictive back behave as expected; a destination never traps back.
- Each tab keeps its own back stack and scroll position. Deep links are planned from the start: `discair://artist/{key}`, `discair://album/{artist_key}/{album_key}`, `discair://genre/{tag}`, `discair://acquisitions`, mapped to the same routes as the web address hash.
- Persist: last tab, per-list scroll, search text. Do not persist server data except through the cache (Phase 5).

## Touch and thumb zone
- Minimum 48dp targets with 8dp gaps; icon-only buttons get a content description.
- Primary actions (Get, Save) sit in the lower half of cards and in a bottom action area on detail pages. Top bar holds navigation only.
- **Dismiss** (deletes files) is never adjacent to Get, is behind a confirmation dialog naming the album and stating that files are deleted, and its confirm button is not the default focus.
- No gesture is the only route to an action: swipe lists have a visible button alternative.
- Pull to refresh on lists, with a visible refresh action for TalkBack.

## Lists and performance
- `LazyColumn` / `LazyRow` with stable keys (server `key` or `id`, never the index) and fixed row height for ranked rows so scrolling stays predictable.
- Coil with downsampled artwork sized to the cell; placeholder is a flat surface colour, so a missing cover never shifts layout.
- Server order is rendered as received; no sort or filter is applied on the device.
- The SSE connection exists only while the Acquisitions or a pending-Get screen is visible and the app is resumed.

## State and honesty
- Every screen has loading, empty, error-with-retry and offline-with-stale-data states. Error text distinguishes no network, server unreachable (Tailscale hint), unauthorised, and server error, using the server's `detail` when given.
- Action buttons have four distinct states shown by icon and text, not colour alone: idle, pending, confirmed, failed. Success is shown only after the server responds.

## Colour and type
- Dark theme only, built from the web tokens (ink `#141211`, surface `#1c1a18`, raised `#252220`, text `#f4efe6`, accent `#f5d33f` on-accent `#141211`, chart red `#ff5a3c`, ok `#86d39b`, caution `#f0a640`). Material 3 colour roles are mapped to these; **dynamic colour is off** because the identity is fixed and artwork tints are applied per page.
- Background is the warm near-black from the web UI rather than pure black; accepted trade for identity over maximum OLED saving.
- Fonts bundled from `static/fonts`: Big Shoulders Display (headings), Schibsted Grotesk (body), JetBrains Mono (numbers). All text in `sp`, and layouts must hold at 200% font scale; headings may wrap, ranked-row titles clamp to two lines.
- Contrast: text on surfaces at least 4.5:1; `--text-subtle` is used only for large or supplementary text and is checked in Phase 1.

## Security
- Credentials only in EncryptedSharedPreferences; the cookie jar is stored encrypted; nothing sensitive is logged; release builds strip logging; backup of the credential store is disabled.
- Cleartext traffic disabled. System trust store only, as the contract states.

## Testing
- Compose screenshot tests per screen state at default and 200% font scale; TalkBack manual pass in Phase 5; low-end device check before the signed build.
