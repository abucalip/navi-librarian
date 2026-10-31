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

## Phase 2 decisions (Dashboard, Library, Artist, Album and Genre pages)

Reviewed with `/mobile-design` while building, then re-checked on an emulator against real library data.

**Structure**
- **Bottom bar has two tabs now, Home and Library.** Search and Acquisitions join it in the phases that build them. The bar shows only on top-level destinations; artist, album, genre and settings pages are stack destinations with a 48dp Back button and system back. Tab state (stack and scroll) is saved and restored.
- **Settings moved off the first screen** to a gear button at the top of Home. It holds connection status, Check again, Edit servers and the confirmed Sign out.
- **Every name opens its page (LIB-01).** Artist, album and genre names are 48dp-tall links. Albums the server gave no key for (recommendations, shelves) are opened with `artist/album` lower-cased; the server normalises it, as the web app does.

**Dashboard** (ported from the mobile web CSS, `static/app.css` under the phone breakpoint)
- Order: Recommended, Genres, Newly added, Recently played, Most played. "New releases" is the discovery list and arrives with Phase 3.
- **Recommended is the web's phone strip:** swipeable cards, one per page, full width and centred, with the artwork at 60% of the width, the tag (`dashboard_category`, shortened to "discovery" or "deep dive"), the title, then artist, year and listeners on one line, and **a dot for each card with no arrows and no count**. Each dot is a button, so the strip never depends on swiping alone; dots are 32dp wide and 48dp tall so ten fit a 360dp phone. Not yet ported: the cover-tinted background, the "i" bio over the artwork, and the Get/dismiss buttons (Phase 4).
- **Genres follow the web phone tiles:** one label, a left bar whose hue comes from the same hash as the web (`genreTileHue`, tested), four to a line, "View more" at the right of the heading (12 shown, up to 60). No album count is printed; it is in the spoken label. Long names are cut with an ellipsis ("Progressive…"), as on the web; the full name and count are spoken and shown on the genre page. Text is 12sp and tiles are 48dp tall, which is slightly larger than the web's 11px and 40px.
- Shelves are horizontal rows of 144dp album cards with a check for owned albums. Each section loads on its own, so one failure shows a message and a Try again button without blanking the rest.

**Library**
- Artists and Albums are chips; search is the server's `q` filter with a 300 ms debounce, not a client filter. Sort field and direction are sent to the server. Direction is named in words that fit the field ("A to Z", "Newest first", "Most first"), never "asc" or "desc", and the total is labelled ("733 artists").
- Paging is by the server's cursor, loading the next page when six rows from the end. The first page uses the server's own starting direction. A failed next page keeps the rows already loaded and offers Try again.
- Not built: grid mode and the tile-size slider from LIB-06, and the all-sources streaming search (Phase 3).

**Artist and album pages**
- Artist: photo hero with the name over a scrim, genre links, "N albums in your library", Top songs (first 5, then "All songs"), About with Read more, owned albums as a two-column card grid (first 6, then "All albums"), albums not in the library ranked by listens, and similar artists. No Get buttons yet (Phase 4).
- Album: centred cover (at most 320dp), title, artist link, genre and year, "Not in your library" when unowned, About with Read more, tracklist with an owned check per track and a summary line, similar albums, similar artists. Service links are not shown yet.
- Similar artists are one row that swipes sideways, with 112dp-wide circles and names that wrap, as in the web phone layout (`static/app.css`, max-width 620px); five are picked at random on each page load. This is display variety only; the server's list and scores are the source.

**Data and images**
- The Library, Artist, Album and Genre pages use Librarian's routes, not Navidrome directly. They are the only source of the artist and album keys the page routes need, and owned covers come through Librarian's artwork route. Navidrome's direct calls (contract section 5.1) are therefore unused so far; the app still checks the Navidrome connection.
- Images load with one shared HTTP client, so they carry the session cookie. Owned covers use the server-relative path; other covers and artist photos are looked up by name once per session and cached in memory. A cover that is not found stays a flat placeholder so the layout never shifts.

**Fidelity to the web UI (rule 10).** The first Phase 2 build took the Recommended strip's arrows and "n of 10" from the desktop slider and built the other pages from the written requirements. It was then compared side by side with the running mobile web UI (Chrome at 360 x 780, the same library) and with the reference screenshots, and these were aligned:
- A global bar with the app name in the display face and the Settings button on top-level pages; headings in the display face with the short red rule.
- Recommended, Genres, shelves and similar artists as described above. Shelf cards are raised rounded cards with the cover edge to edge, a check badge on the cover, the title in the display face, the year in yellow mono, then the artist.
- **Cover-tinted backgrounds** on the Recommended card and on the artist and album pages: the cover's colour, capped dark, fading to the page ground and scrolling away with the page. The colour is a saturation-weighted average, not the web's exact algorithm.
- **Artist page:** photo hero with the Back button laid over it, name, muted genre links and "N albums in your library"; Top songs in a raised panel with display-face rank numerals, album under the title, abbreviated listens (18.3K) and a check; the bio with Read more and no "About" heading; owned albums with a check badge on the cover; "Missing albums" as ranked rows with a thumbnail; similar artists.
- **Album page:** Back button beside the cover, cover 240dp, display-face title, plain artist name, muted "genre · year", a tracklist with dividers, mono durations and a check per track, the summary line ("27 songs, 1 hour 19 minutes · 10 in your library"), four logo-only service links (Apple Music, Deezer, MusicBrainz, Qobuz; the marks are the web's vendored files converted to vector drawables, with their licences in `android/licenses/simple-icons`), similar albums as ranked rows with thumbnails, then similar artists.
- **Library:** heading with the red rule, the description line, a pill search field, an Artists/Albums segmented control, "Sort by" with a dropdown and a direction button, the "Showing 60 of 733 artists" caption, and square 48dp thumbnails.

Still different from the web, on purpose or because it is not built yet:
- No Get, dismiss, save or "i" bio buttons (Phase 4 and later), no search icon in the bar (Phase 3), and only two of the web's bottom tabs until their screens exist.
- Library grid mode and tile-size slider are not built.
- The genre page is a light port of the web's plain page (heading, item count, underlined names with "In your library").
- Touch targets are 48dp where the web uses 44px or less; genre tile text is 12sp where the web uses 11px.
- An album whose title leaves no letters or digits for the key (for example one titled only in non-Latin script) has an empty album key, so the server answers Not Found. The web page has the same limit.

**Accessibility and states**
- Section titles are headings. Owned checks have a spoken label. Pager and sort buttons have descriptions that say what they do and their current state. Loading, empty, "index still building" and error-with-retry states exist for every list.
- Number columns use a fixed width, not a fixed size, so they align with the first line of text.
- Not yet checked on a device: TalkBack reading order across these pages, 200% font scale on the new screens, and landscape.
