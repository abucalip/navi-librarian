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
- Fonts bundled from `static/fonts`: Peace Sans (page and section titles, -0.085em tracking, 1.05 line height, matching the wordmark), Open Sans (body), Big Shoulders Display (rank numerals), JetBrains Mono (numbers). The Discair wordmark (`ic_wordmark`, traced from `static/discair-logo.svg`) replaces the text title in the top bar and setup screens. All text in `sp`, and layouts must hold at 200% font scale; headings may wrap, ranked-row titles clamp to two lines.
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

## Phase 3 decisions (Discover, Search, shared row, feedback)

Decided with `/mobile-design` while building; the built screens still need the rule 9 re-review.

- **Bottom bar has four tabs:** Home, Discover, Search, Library. Search is a tab because it is used from anywhere, one tap from the thumb zone; Discover holds the six lists as 48dp chips in one scrolling row instead of the web's More menu, so no list is hidden behind a second tap.
- **Shared ranked row:** lead column 36dp (position, or release date on New releases), artwork 72dp, title (display face, two lines), artist link (48dp tall), meta lines, bio of three lines that expands on tap (with a spoken Expanded/Collapsed state). Actions are two 48dp icon buttons stacked at the right: Save and a menu. Fixed height is not forced; long titles clamp to two lines.
- **Save is not colour alone:** outline heart (not saved), spinner (pending), filled heart (saved), warning triangle (failed, tap to retry), each with a spoken state. It turns to Saved only on the server's `ok`.
- **"Not for me" is a menu, not a swipe:** "Not this album" or "Never suggest <artist>". Both hide the row and show Undo for 6 s before anything is sent. A second dismissal sends the first at once, as on the web. Neither deletes files, so no confirmation dialog; the dialog stays reserved for acquisition Dismiss (Phase 4).
- **Search:** live search after 400 ms of typing, a Clear button, status text announced politely ("Searching…", "No matches.", "Some sources did not answer"). "No matches." appears only after the stream's `done`. Results keep the server's order, owned first.
- **Honest empty states:** a list the server says is disabled or not yet built shows the server's message; a Build this list button is offered only for lists that can be built.
- Remaining differences from the web phone UI: lists render as vertical rows rather than card tracks; Classics is not capped at three per artist or shuffled; no recent-searches panel.
- Bottom bar text is capped at 130% (the rest of the app follows the system setting to 200%): four labelled tabs split mid-word at 200% on a 360dp-class screen.

## Phase 4 decisions (Get, Downloads)

Checked against the `/mobile-design` checklist (touch targets and spacing, thumb zone, loading and error states with a way out, destructive-action confirmation, no gesture-only controls, cleanup, accessibility labels). The built screens have not been reviewed on a device.

- **Get is the web's cloud button as a 48dp icon control.** Idle is the cloud, pending a spinner, requested a green check, failed a warning triangle; each has a spoken state, and failed speaks the server's reason. Requested and pending ignore taps, so a request cannot be sent twice (ACQ-02). Failures and acceptances are also announced in a shell-level snackbar.
- **Song Get only where the server can file it:** on the album page for tracks the library lacks, and on Top songs that name an album.
- **Downloads is a header button, not a tab.** It carries a badge with the active count and a spoken "Downloads, N active". Trade-off: the header is outside the thumb zone; a fifth tab would have split labels at large text. It is reached rarely and the badge shows when to look.
- **Actions are labelled buttons, not icons or swipes,** wrapped in a flow row with 8dp gaps: "Use next source (12s)", "Try again", "Dismiss". Dismiss is the only destructive one; it opens a dialog that says files are deleted and that the server refuses unsafe cases, and Cancel is the dialog's other button. The dialog does not name the files, which only the server can identify.
- **Status is icon plus words,** colour only adds emphasis. Progress is a bar plus the percentage in text; the bar is announced as "Download progress N percent".
- **No dead ends:** loading spinner, an error line with Try again if the first read fails, and an empty message. Rows already shown stay if a later read fails.
- **Known gaps:** Get, Save and the menu are three stacked 48dp targets with no gap on ranked rows (Save and the menu were already adjacent); the stream is stopped on app stop and screen leave but battery use has not been measured.

## Phase 5 decisions (offline, session expiry, release)

Decided without a device run; the owner then ran the signed build on their phone (2026-10-31): banner, offline cold start on saved pages and the Downloads page behaved as designed, no crash. The `/mobile-design` review of these screens on a device is still owed (rule 9); the owner deferred it to a later UI polish pass (2026-10-31). Known items for that pass: Get, Save and the overflow menu are stacked 48dp targets with no gap; a ranked row's cover and title both open the same page; TalkBack, landscape and 200% text are unchecked.

- **Offline is a banner, not a mode.** One line under the header with an info icon and words: "Can't reach Librarian. Showing a copy saved 2 hours ago." It is a polite live region and appears only while a saved copy is being shown; the next live read clears it. Pages keep their normal layout, so nothing is hidden or greyed. Actions that need the server (Get, Save, Dismiss) fail with the server-unreachable message rather than queueing, so the app never shows a request as made that was not.
- **A dead end becomes the last known state.** Starting with no connection used to stop on the Unavailable screen; with saved copies it opens Home. A server that answers with a refusal still stops there.
- **Session expiry returns to setup with a reason** in red text (announced politely) and the saved values filled in, instead of every page showing "Not authorised".
- **Accessibility:** clickable rows, covers and names now announce as buttons. Known open: a ranked row's cover and title both open the same page (two TalkBack stops).

## UI and speed pass (2026-10-31, owner's requests)

- **Tabs swipe, stacked pages swipe back.** A drag no child used (carousels, rows and pagers take theirs first) moves to the neighbouring top-level tab, or pops a stacked page. A pager at its first or last tab keeps the drag, so Daily picks and Artist deep dives are left with the bottom bar.
- **Discover is cards, two to a row.** Controls sit on the cover over a dark round backing so they read on any art. Cards are a fixed height: the title reserves two lines, the year line one, the bio three, and the bio does not expand in a card. The server's "reason" text is never shown.
- **Artist names are white; the year is the accent colour and the listener count grey.** Categories use the dark pill with a lighter border and a glow while pressed; the selected one has the accent border and is announced as selected.
- **Pages show what they have.** First paint comes from the saved copy, then the server replaces it; an album or artist page shows each section as the server finishes it. A failure after something is on screen keeps it. Cosmetic lookups (covers, bios, years) run on a few threads so they never delay page data.
- **Open:** the Sort by pill and its direction button are 32 dp tall, below the 48 dp touch target used elsewhere; the owner asked for them small. Thumb reach of the on-cover buttons belongs to the deferred device review.

## Album Info and Reviews tabs
Mirrors PR #652. The description area is two tabs. Info shows the description with its source link and licence (Wikipedia is CC BY-SA 4.0). Reviews calls `GET /api/album-reviews` only when first opened, shows up to three outlet lines with links, and offers Try again when the answer is partial (`retryable`) or fails. With no description, Reviews opens by itself unless the reader already chose a tab.

## Player UI decisions (Phase 3 of the player, 2026-11-01)

Reviewed with the `/mobile-design` principles (touch targets, thumb zone, platform conventions, state honesty) against the code. **No screen has been run on an emulator or a phone**, so this is a code-level review only (rule 9 is only partly met).

1. **Mini-player above the bottom navigation, on every page.** It sits in the thumb zone, 64dp high, and shows on stacked pages too (clearing the system bar itself). It is absent from the layout when the queue is empty.
2. **Controls are 48dp, text is the control.** Play or pause and next are 48dp buttons; the title and artist area is one 48dp-high button labelled "Open now playing". The progress line is decorative and hidden from TalkBack because Now Playing has the seek bar.
3. **Now Playing is a modal bottom sheet** (Android convention), closable by back, the down button or a drag. Transport sits in the lower half of the sheet. Play or pause is the one large (64dp) control.
4. **State in words, not colour.** Loading, buffering, lost connection, unavailable song, queue full and "Sign in again" are written under the title. Queue rows say "Now playing", "Paused here" or "Unavailable". Shuffle and repeat carry spoken state ("On", "Repeat one").
5. **The seek bar speaks its value** ("1:23 of 4:10"). The track title is a polite live region so a track change is announced once, not on every position update.
6. **No gesture-only action.** Queue reorder is Move up, Move down and Remove in a per-row menu, not drag. Skipping is buttons.
7. **Destructive action kept apart and confirmed.** "Clear queue and stop" is 32dp below the transport controls and opens a dialog that says the library is not changed.
8. **Volume is the phone's volume.** No in-app slider; a one-line note says so.
9. **Sign-in problem pauses once.** The Sign in again button reuses the existing session-expired flow (back to the setup screen with the saved values); it does not erase the saved login.
10. **Notification permission** is asked once, when playback first starts, because the media notification needs it on Android 13.

Known gaps:
- Not checked on a device: layout at default and 200% font, landscape, TalkBack reading order, thumb reach, contrast of the status line, the sheet's open and close animation (it is not switched off for the reduced-motion setting yet).
- The notification and lock screen show title, artist and album but no cover (the cover needs a signed Navidrome address; left for a later pass). In the app, the cover is loaded from Librarian when a queue item carries one.
- No Compose screenshot tests.

## Player entry points (Phase 4 of the player, 2026-11-01)

Code-level review with the `/mobile-design` principles; **not run on an emulator or a phone**.

1. **Play controls exist only for albums and artists in the library.** Album page: Play and Shuffle buttons (48dp, thumb-reachable under the header) and a More menu with Play next and Add to queue. An unowned album shows none of them, and recommendation and Get cards never do.
2. **Tapping an owned track plays the album from that track**, with the rest of the album after it. The row says "Play <title>" to TalkBack. A track that is not in the library keeps its Get button and does nothing on tap.
3. **Artist page:** Play and Shuffle for the artist's library albums, and a play button on an owned Top song whose album is in the library. A Top song whose album cannot be found keeps its owned mark.
4. **Library and Search rows:** a 48dp play button on each album and artist row, and Play and Add to queue buttons on each song result. The row text still opens the page.
5. **Honest feedback in words.** Loading, success of the queue actions ("2 songs will play next.") and every failure (can't reach Navidrome, login rejected, no songs found, song not in the library) appear in the snackbar. A second tap while songs are loading is ignored with "Still loading songs.".
6. **Where the ids come from.** The web album page carries no song ids, so the app asks Navidrome (`getAlbum`, `getArtist`) with the login saved on the device; search results already carry the song id.

Known gaps: per-track Play next and Add to queue, a Shuffle button on library rows and play controls on Discover or Home cards are not built. Not checked on a device: layout at 200% font and in landscape, TalkBack order on the track rows, thumb reach of the buttons, the time to load a large artist.

## Player settings and hardening (Phase 5 of the player, 2026-11-01)

Code-level review with the `/mobile-design` principles; **not run on an emulator or a phone**.

1. **Playback section in Settings.** Streaming quality is a radio list (Original, then 320 down to 64 kbps), each row at least 48dp and selectable as a whole row, with a note that a change applies to songs started afterwards. "Record plays" is a switch row (the whole row toggles) whose supporting text changes with the state in words: On says plays shape the listening history and recommendations; Off says they will not.
2. **The Settings page scrolls.** With the new section it is taller than a phone in landscape or at large text, so the fixed layout with a flexible spacer became a scrolling column.
3. **Reduced motion.** The mini-player and sheet use standard Compose animations, which follow the system animator scale, so the system "Remove animations" setting switches them off. This is from the framework's behaviour, not checked on a device.
4. **Not covered:** TalkBack order and spoken state on the new rows, 200% text and landscape on Settings, and thumb reach have not been checked on a device.

## Playback gaps and gapless (2026-11-01)

Code-level review; **not run on a device**.

1. **Per-track queue actions.** Each owned track on the album page has a 48dp More button (Play next, Add to queue) beside the owned mark.
2. **Library rows** keep the Play button and gain a More menu: Shuffle, Play next, Add to queue (albums and artists).
3. **Home shelf cards** (Newest, Recently played, Most played) show a 48dp play button on the cover of albums in the library. Discover and Recommended cards still offer none: they are not in Navidrome.
4. **Quality note.** The Settings text now says converted streams can leave a short gap between songs.

## Lyrics view (Phase L3 of the lyrics contract, 2026-11-01)

Code-level review with the `/mobile-design` principles; **not run on an emulator or a phone**. The owner's polish pass on a device is still deferred (see the Phase 5 decision of 2026-10-31).

1. **Three labelled views in the Now Playing sheet: Player, Lyrics, Queue.** The old queue icon is gone; the segmented text tabs (each at least 48dp, selected tab announced as selected and drawn raised, so not colour alone) sit in the middle of the header with Close on the left. The last view used is remembered while the app process lives, not across restarts. Back returns to Player from the other two views.
2. **Every state is written out.** "Loading lyrics…" with a progress ring; the lines; "These lyrics are not timed." above plain lyrics; "No lyrics for this song." with no retry button; a failure sentence with **Try again**; "Saved copy" above lyrics shown from the cache when a refresh failed; "Your Navidrome doesn't provide lyrics."
3. **Following the music.** The current line is larger and bold and carries the spoken state "Current line"; it is kept about a third of the way down the list. The current line is not announced as it changes (it would talk over the music). A hand scroll stops following and shows **Back to the current line** (48dp, bottom centre); following resumes when the song changes. With the system animation scale at 0 the list jumps instead of scrolling.
4. **Lines do nothing when tapped** (owner decision). Empty lines are drawn as space and hidden from TalkBack.
5. **Size.** The list is at most half the screen height, so it fits landscape and large text and scrolls inside the sheet. Text uses the system font size and wraps.
6. **Fetching.** Only while the Lyrics view is open, for the song that is playing; the next song is prefetched while it stays open; closing the view or the sheet cancels everything. The cache is cleared at sign-out.

Seen on the owner's phone (2026-11-01, screenshots over adb): plain lyrics with their note; 200% text keeps the tabs on one line ("Queue" near the right edge) and wraps lines; landscape at 200% fits but shows only about three lines at a time; the "not timed" note has no space above it (cosmetic, not fixed). Not checked on a device: TalkBack order across the three tabs and the lines, thumb reach of the tabs, whether the 4 s average lookup feels acceptable over Tailscale, scroll behaviour on very long lyrics.

## Polish pass on built screens (2026-11-01)

Run with the `/mobile-design` checklist against the release build on the owner's phone (SM-G781B, 1080x2400 at 480 dpi), over adb. Method: every tappable element on Home, Discover, Search, Library, Downloads, Settings and Now Playing was measured from the accessibility tree (`uiautomator dump`, bounds converted to dp) and each screen was screenshotted at default text size. Landscape is dismissed by the owner. TalkBack and thumb reach were not re-run (TalkBack was confirmed by the owner for lyrics).

**Measured:** no tappable element under 48dp on any screen once items clipped by the mini-player or the sheet edge are excluded. Two apparent misses were checked and are not defects: the mini-player's Play and Next report 27dp tall on pages without the bottom bar, but a tap 63px below the icon centre (inside 48dp, outside 27dp) still toggled playback and a tap 77px above did not; "Clear queue and stop" reports 43dp only because the sheet edge clips it.

**Changed:**
1. **Header buttons 44dp to 48dp wide** (Downloads and Settings). They measured 45 wide, so their touch areas overlapped by 3dp.
2. **Discover card menu (the three dots) now sits on a dark round backing** (34dp, 55% black). The old soft halo vanished on white and yellow covers.
3. **12dp of space under the Player / Lyrics / Queue tabs in every view.** The tabs sat 5px above the cover on Player and touched the "These lyrics are not timed." note. Verified on the phone for the Player and Lyrics views; the plain-lyrics note itself was not on screen after the change (the playing song has no lyrics).

**Seen, not changed:**
- Discover cards cut the listener count to "39,904 listene…" at default text size. The line is one row on purpose so cards stay level; the number is intact.
- Search shows an empty page under the field before typing (the field label already says what to type). Recent searches or a hint would be an owner decision.
- Failed downloads show the server's long diagnostic text in full ("No matching album folders were found among 0 collected peer responses…"). Wording is the server's; a short summary with the detail behind a tap would be a Librarian change.
- Discover has two rows of tabs in two different styles (a raised track on top, underlined tabs below). It looks deliberate; both scroll sideways and show a cut-off label as the cue.

**Not covered:** TalkBack order on every page, thumb reach, the Album and Artist pages at 200% text, and the offline banner (needs airplane mode; songs cannot be streamed offline).

## Equalizer screen (Phase E3 of the EQ contract, 2026-11-01)

Code-level review with the `/mobile-design` principles (Android, native Compose; touch targets, thumb zone, no gesture-only control, every state in words); **not run on an emulator or a phone**.

1. **Where it lives.** A full page (`EqualizerRoute`), opened from Settings, Playback section ("Equalizer", with "Off" or the preset name under it and an arrow) and from the Player view of the Now Playing sheet (a 48dp text button reading "Equalizer: off" or "Equalizer: Rock", placed under the volume note and away from "Clear queue and stop"). Opening it from the sheet closes the sheet. Back returns to where it was opened.
2. **Order, top to bottom:** the on/off switch with a sentence in words; the "Not applied to this song." or "Equalizer unavailable for this song." line when it applies; the preset button (a drop-down menu whose items are at least 48dp; the chosen item says "(selected)"); ten band rows; Headroom (automatic switch, and a manual row only when automatic is off); Reset to flat. The page scrolls.
3. **Deviation from contract section 7: horizontal rows, not ten vertical sliders.** In portrait, ten columns leave about 33dp each, which cannot hold 48dp minus and plus buttons. Each band is one block: its name ("62 Hz") on the left and its value ("+3.5 dB", with a true minus sign) on the right, then a 48dp minus button, a slider and a 48dp plus button. The text follows the system font size and wraps, so 200% text keeps the buttons usable. Landscape has no special layout (the owner dismissed landscape on 2026-11-01); the page just scrolls.
4. **No gesture-only control.** The slider is the quick way; minus and plus move 0.5 dB and stop at the limits (the button that cannot move is disabled). Sliders step in 0.5 dB, so TalkBack's increase and decrease gestures work.
5. **Off is shown, not hidden.** With the equalizer off, every control stays on screen, disabled, under the sentence "Off. Songs play as they are. Turn it on to use the controls below." State is carried by words and by disabled controls, not by colour alone.
6. **TalkBack.** A band reads "62 hertz" with the state "plus 3.5 decibels"; the buttons read "Lower 62 hertz by half a decibel" and "Raise ..."; the switches are announced as switches with their state; the preset button reads "Preset, Rock"; headings mark Bands and Headroom; the status line is a polite live region.
7. **Reset** asks first ("Reset the equalizer?"), says what it erases (the Custom curve) and what it leaves (the presets, and whether the equalizer is on).
8. **No custom animation** is added, so reduced motion needs nothing extra.

Not checked on a device: thumb reach of the Now Playing link and of the minus and plus buttons, TalkBack order and wording, 200% text, how the ten rows feel to scroll and drag, whether a slider drag is smooth (each step saves and re-aims the filter), the drop-down on a small phone.

## Equalizer: first device run over adb (2026-11-01, E4)

Run by the assistant against the signed release build of `main` (`85b379d`, then one fix) on the owner's phone (SM-G781B, Android 13, wireless debugging), by driving the app with `adb input` and reading the accessibility tree, screenshots, `dumpsys` and `logcat`. **Nothing was heard**: no audio was recorded or listened to, and the phone was on silent. The owner's listening checks are still open (contract section 16, B and C).

**Seen working**
- Settings, Playback: the Equalizer row reads "Off", then the preset name once on. The page opens; with the switch off every control is disabled and the page says why.
- The switch, the preset menu (items 48dp apart; the chosen one says "(selected)"), and Bass boost setting +6, +5, +4, +2 dB on the first four bands.
- With a song playing and the equalizer on: 12 plus taps (stops at +12 dB), fast slider drags back and forth, four preset changes and six switch toggles. Playback stayed `PLAYING`; no `FATAL EXCEPTION`, no ANR, no app error in `logcat`.
- The system audio server shows the app's track as 16-bit stereo at 44.1 kHz, not offloaded, **0 underruns** after about a minute of playback with the equalizer on and changing. (This shows a normal, healthy track. It does not prove the filter is in the path.)
- Moving a band switches to Custom; Custom survived closing the app from the task list and reopening ("Equalizer / Custom" in Settings); Reset asked first, then went to Flat with the switch left on; the switch off again, playback paused.
- The Now Playing link ("Equalizer: Custom") opens the page, and Back returns to the page the sheet was opened from.
- 200% text: the rows reflow, the sheet scrolls to the link, nothing is cut off, and the plus button disables at +12 dB.
- Touch target: a tap 8px inside the 48dp area of a minus button (outside the 24dp icon) worked; a tap 28px outside it did nothing. (`uiautomator` reports the icon's 24dp, not the button's 48dp.)

**Found and fixed in the follow-up PR:** the sliders drew all 47 step marks as dots, which cluttered every row. The tick colours are now transparent, in both the enabled and the disabled state (the first fix cleared only the enabled one; the screenshot of the disabled state showed it). Checked on the phone with the equalizer on.

**Not checked** (still the owner's): that the filter is audible and sounds right, the presets, no clicks when a setting changes, +12 dB with automatic headroom on and off, FLAC / M4A / Opus and a 24-bit file (only the current queued song, "Track 7", was played, its format not read), 128 kbps, gapless on a live album, lock screen, headset buttons, a phone call, Bluetooth, TalkBack, one-handed reach, battery, and sign-out keeping the setting (not run: it would sign the owner out). Whether any song shows "Not applied to this song" was not seen.
