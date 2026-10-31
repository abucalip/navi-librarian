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

## Phase 1 review decisions (setup, connection and home shell)

Reviewed with `/mobile-design` against the built screens. Each item was fixed in Phase 1.

1. **Nothing encrypted is opened on the main thread.** The settings and cookie stores open lazily on the IO dispatcher; the view model starts on a Checking screen and loads the saved settings from there. Keystore setup can take hundreds of milliseconds.
2. **Sign out is destructive, rare and confirmed.** It is a text button set 32dp apart from the routine actions, and opens a dialog that says what is erased (both addresses, user names and passwords). The dialog's default dismiss is "Keep me signed in".
3. **A failed check of saved servers is not first-time setup.** A separate Unavailable screen ("Can't connect", nothing was changed) offers Try again, Open Tailscale (only if the Tailscale app is installed) and Edit servers. The setup form appears only for first-time setup, for editing, or when the Connect attempt itself fails. A failed edit never replaces working saved settings.
4. **Editing can be abandoned.** Cancel and system or predictive back (opted in with `enableOnBackInvokedCallback`) drop the edits and re-check the saved servers. First-time setup has no Cancel and back leaves the app.
5. **Typing on a phone is minimised.** Each field has an IME action: Next moves down, Done on the last field submits. User name and password fields carry autofill content types so a password manager can fill them. Passwords have a Show/Hide toggle with a 48dp target and a spoken label.
6. **The Connect button never goes dead.** It stays enabled while idle; pressing it with blanks marks each empty field "Required." in text and colour. It is disabled only while a check is running.
7. **Headings are exposed.** The app title and the Librarian and Navidrome section titles carry heading semantics for TalkBack heading navigation.

Smaller decisions from the same review:
- Server status rows are hidden until a check has run, so the first screen is only the form.
- Forms are capped at 480dp wide and centred, so tablets and landscape stay readable.
- The launcher icon is adaptive with a monochrome layer for themed icons.
- Verified on an emulator at 200% font scale: nothing clipped, fields still at least 56dp, Show toggle intact.

Not yet checked on a device: TalkBack reading order, the real Open Tailscale intent, and password-manager autofill.

Library note: the `ContentType` autofill API is public only from Compose UI 1.8, so the Compose BOM is 2025.04.01.
