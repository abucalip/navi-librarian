# Discair for Mac: design

Skeleton from [`docs/MACOS_CLIENT_CONTRACT.md`](../docs/MACOS_CLIENT_CONTRACT.md) sections 2, 4 and 4.1. Mockups are the spec: `docs/design/macos-m3/mockups.html` (round 1) and `docs/design/macos-m4/mockups.html` (round 2). Nothing here is built yet (UI starts in M4). Each element below is filled in, with reasons, as it is built.

## Themes

Each theme owns its screens and window composition behind a shared set of data and actions, so a later theme is added without changing screens. Each theme fixes its own light or dark. No round 1 inheritance.

| Order | Theme | Kind | Notes |
|---|---|---|---|
| Launch | **Cupertino** | macOS, light | Bold sans titles (SF Pro Display, not serif). Glass only on controls (sidebar, toolbar pieces, centre Now Playing). Opaque white content, red-pink accent, zebra tables, Up Next as trailing inspector. |
| Launch | **Zine Spread** | Neobrut | Masthead, ticker, lead story, New this week, Classifieds, running order, A-Z index, magazine-cover artist page, centre-spread Now Playing, black player strip. Keep every detail. |
| Later | **Bento Block** | Neobrut | Colour-block panels, hard shadows, permanent player card, one-line timed lyric field, EQ as stacked bars. |
| Later | **Native Glass v2** | macOS, dark | Floating inset glass sidebar, one glass player capsule, opaque content, tint only on the primary action. |

Not built: Cassette Deck, Sheet Stack, Sticker Wall, round 1 Native Glass. Kept for every Neobrut theme: the single timed lyric line field on Now Playing.

Rules: mockups are built element by element (no light re-skins); list dropped elements in the PR; fonts bundled from the repo plus system fonts; no third-party runtime asset requests; one app and Dock icon variant per theme.

## Window

- One window with panes and fully custom borderless chrome: own traffic lights, drag region, resize.
- One floating always-on-top mini player (cover, transport, seek bar, peek at the next track).
- AppKit only where SwiftUI cannot do it (borderless chrome, floating panel).
- Visible active-profile indicator and an "unencrypted" badge for plain http profiles.

## Accessibility and legibility rules

- Gestures are never the only path: every drag has a non-gesture path. Get, Save and Not for me stay reachable with text labels.
- Honest states (pending, confirmed, failed, recoverable) differ by more than colour.
- VoiceOver labels on every control; full keyboard navigation and common hotkeys; command palette (⌘K).
- Reduce Motion is respected. Check every screen with Increase Contrast and Reduce Transparency.
- Liquid Glass is only for the functional layer above content, never content itself; no glass on glass. Hard-edged scroll effect instead of dividers under floating bars; concentric corner radii; do not hard-code control heights.
- Errors name the kind (no network, server unreachable, Tailscale not connected, unauthorised, server error) and offer retry.
- Never show a credential, token, salt or stream URL.


## M4 slice 1 (foundation) built

- **Theme layer:** `DiscairTheme` owns the whole window for the current screen; `ThemeRegistry` maps `ThemeID` to a theme. Themes read `AppState` and call `DiscairActions` (play, Get, Save, Not for me, resume); they never touch the network or audio. Zine Spread is a placeholder until its slice.
- **Window chrome:** the window stays `.titled | .resizable | .fullSizeContentView` with the system title bar and buttons hidden and the background draggable, so resize, shadow and full screen keep working; the theme draws its own traffic lights. A truly borderless window was rejected because it loses those.
- **Cupertino Home:** built from the mockup (inset glass sidebar, glass toolbar pieces and centre display, opaque white content, Continue listening card, Missing shelf with Get / Save / Not for me, Recently added). All six Cupertino screens are built.
- **Dropped or different from the mockup:** cover art is a hue gradient placeholder; the blurred pastel window backdrop is not visible because content is opaque; glass does not render in the offscreen screenshot test (it needs a live window), so screenshots show glass areas unfilled.
- **Screenshot tests:** render through `NSHostingView` in a borderless offscreen window (`ImageRenderer` cannot draw ScrollView or glass). PNGs are written to `DISCAIR_SCREENSHOT_DIR`; baseline comparison starts after the owner approves the look.

## HIG read (2026-11-03): Toolbars, Sidebars, Materials, Layout

Read in full from PDFs the owner saved from developer.apple.com (not committed; Apple's text). What applies, and where the approved mockups differ. Mockups stay the spec; each difference needs an owner decision before it is changed.

**Already followed:** glass only on the control layer, never on content; regular (not clear) glass for sidebars and text-heavy pieces; at most three toolbar groups (transport, display, search); tint only for state and the primary action; hard scroll edge effect instead of a solid bar under floating controls; content extends under the sidebar.

**To build (no conflict with the mockups):**
- Every toolbar item is also a menu bar command (macOS), because the toolbar can be hidden or customised: transport, shuffle, repeat, search, show/hide sidebar.
- A show/hide sidebar button and View menu commands (Show Sidebar, Hide Sidebar); the sidebar is shown by default.
- Sidebar: at most two levels (Library group, Playlists group is already two); row size follows the system sidebar icon size setting; items stay reorderable later.
- Clear glass only for chips over artwork (Now Playing); add a dimming layer of about 35% when the artwork behind is bright. Regular glass everywhere else.
- Back and Close use the standard symbols, never the words; titles under 15 characters and never the app name.
- Keep text-labelled actions apart from symbol actions (Get, Save, Not for me keep fixed space between them); one prominent action per bar, on the trailing side.
- Check every screen with Reduce Transparency and Increase Contrast.
- Corner radii concentric with the window and bars; no hard-coded control heights where a system control exists.

**Differences from the approved mockups (owner decided 2026-11-03):**
1. **Connection indicator and "unencrypted" badge:** moved off the bottom (HIG: people often move windows so the bottom edge is off screen). First put at the top of the sidebar; the owner then asked for the top right corner, under the search pill. Done for Cupertino; other themes place it at the top.
2. **Zine Spread black player strip at the bottom:** kept as drawn. Transport is also in the menu bar, media keys and the mini window, so playback never depends on the strip.
3. **Tinted glass** (74% light tint): kept as approved; revisit if legibility checks fail.
4. **Fixed red-pink sidebar icons:** kept fixed as part of Cupertino's identity.
5. **Custom traffic lights:** must keep close, minimise and zoom behaviour and VoiceOver labels.

## M4 slice 2: Cupertino Album

Built from `R.cupertino.album`: artwork, bold sans title, red artist name, quality and owned badges, Play / Shuffle / Get missing song (outlined) / Save, zebra track table with the playing row in the accent colour and the missing song as a dashed row with its own Get song, More by artist shelf. "Open album" on Home navigates here; the sidebar highlights Recently Added. Dropped or different: track "..." menus are text placeholders until M5; Shuffle has no action yet; runtime "41 minutes" is a sample value.

Home change (owner, after slice 2): Not for me is a labelled capsule button like Get and Save (outlined, own row under them so all three fit a 156 pt tile).

## M4 slice 3: Cupertino Now Playing

Built from `R.cupertino.now`: full-window dark backdrop, cover with shadow, title, seek bar with elapsed and remaining, transport, left-aligned bold lyrics with the current line in white and a fade mask, EQ / Crossfade / quality chips. The centre display in the toolbar opens it; Back (standard chevron symbol, no text) returns; Up Next opens the queue screen. Dropped or different: the backdrop is soft radial colour fields from the cover hues, not the blurred artwork (the blur did not render offscreen and real artwork arrives in M5); transport buttons and the seek bar do nothing yet; lyrics are the mockup's sample lines; chips use clear glass over a 30% dark layer (HIG: clear glass only over media, with dimming).

## M4 slice 4: Cupertino Queue

Built from `R.cupertino.queue`: Up Next as a trailing inspector (glass, 380 pt, full height) with Up Next / History segmented control, song count and duration, Autoplay (radio) switch, queue rows with the playing row tinted, Save queue and Clear. Opened from the Up Next chip on Now Playing; the sidebar highlights Songs. Differences from the mockup: the Albums grid and the toolbar stop short of the inspector instead of running under it, so Search and the connection indicator stay visible and no text collides with the glass (HIG: toolbar items must stay reachable); History shows one sample line; drag reorder and Save queue / Clear do nothing yet (a non-gesture path for reorder, such as move up / down, comes with M5).

## M4 slice 5: Cupertino Library

Built from `R.cupertino.library`: bold Songs title, source segmented control (Songs, Albums, Artists, Missing), view segmented control (Table, Grid, Columns), zebra table with cover thumbnails, format badges and the selected row in the accent colour. The header buttons sort for real (Title, Artist, Year, Genre, Format, Plays; click again to reverse) and a row click selects it; both are labelled for VoiceOver. Dropped or different: the Songs / Albums / Artists / Missing and Table / Grid / Columns controls change their highlight but the other views are not built yet (Miller columns are an opt-in feature in M6); Bitrate, Last played and Added are not sortable yet; the data is the mockup's twelve sample rows.

Sidebar and grid navigation (owner report: Songs was not clickable): every sidebar row and playlist row is a real button. Home, Albums, Songs and Artists navigate; New, Recently Added, Gap Radar, History, Downloads and the playlists do nothing until their screens exist (M5/M6). Album tiles in the Albums grid open the album screen. `Screen` gained `.albums` (the grid on its own; the queue screen is the same grid under the Up Next inspector).

## M4 slice 6: Cupertino Artist

Built from `R.cupertino.artist`: an edge-to-edge banner under the sidebar and toolbar with the 60 pt bold sans name, owned count and genres, Play (accent) / Shuffle / Radio (translucent white); Top songs in two columns with a Get on the missing one; Albums with the missing ones dashed at 35% and a Get button each. The banner is fixed and only the lists scroll. Sidebar "Artists" opens it. Differences: the banner is a colour field from the artwork, not the blurred cover (M5, as on Now Playing); the connection indicator turns white over the banner; Shuffle, Radio and the song times are placeholders; screenshots show the sidebar and toolbar glass untinted, so those areas look washed over the dark banner there (live they carry the 74% light tint, to be checked by the owner).

## M4 slice 7: Zine Spread (six screens)

Built from `R.zine`: masthead (dateline with the connection indicator at the top, Anton title, six section tabs, own square window controls), yellow pipeline ticker, black player strip at the bottom (opens Now Playing; its list button opens the queue), and the six pages. Home: lead story with real Get / Save / Not for me, New this week, Classifieds. Album: article headline, byline, contents box with the missing song as a dashed coupon and its own Get song. Now Playing: centre spread with halftone cover and lyrics in two columns, current line highlighted. Queue: Running Order with dotted leaders, Radio classified, saved queues. Library: A-Z margin and three-column index. Artist: cropped cover-line name, back issues (missing dashed with Get), Also in this issue. Fonts: Anton and Space Mono bundled from the repo's Android resources, and Source Serif 4 (Regular, Italic, Bold, Bold Italic statics from the owner's zip) (`Resources/Fonts`, licences alongside). Dropped or different: covers are the mockup's generated patterns, not real artwork (M5); the ticker does not scroll; the letter margin, Radio, Save queue, Clear, EQ / Crossfade / Quality chips and the reorder handle are placeholders; no non-gesture reorder yet (M5, as on Cupertino); the page scrolls when it is taller than the window. The screenshot colour check now needs 8 distinct colours because Zine is mostly ink and paper.

Zine Album entry points (after slice 7): the Home lead story cover and the New this week rows, and the Artist back-issue covers (owned) and titles, open the Album screen for that album. The Album page still shows the mockup's sample article and six-song contents for every album. Queue rows do not open it (a row tap should play, which waits for M5).

Owner review fixes (Zine): Not for me on Home is a bordered button like Get and Save (no longer an underlined link). The Artist name is shown whole instead of cropped (240 pt Anton, placed from the font's ascent so the baseline sits above the rule); this departs from the mockup's cropped name, by the owner's report.

## M5 slice 1a: session and Settings

`SessionModel` (DiscairUI) owns profiles (`~/Library/Application Support/Discair/profiles.json`), the two logins (Keychain; passwords are written once and never read back or shown) and the live connection: it picks the profile (manual override, else LAN then Tailscale), checks Navidrome with `ping` and the Librarian login if saved, and exposes the clients for the data layer. The connection indicator in both themes now shows the real state (profile name, http (unencrypted) or https, or the error kind) and the app connects at launch. Error kinds are named with a Retry (contract section 3). New `Screen.settings`: Cupertino (sidebar row, grouped cards) and Zine (Settings tab, boxes). **No Settings mockup exists**; both are drawn from each theme's own parts and need the owner's design review. Not in this slice: live library data and artwork (next), other settings (quality cap, EQ, scrobbling, cache, SMB), editing a profile in place (remove and add again), the SMB login. Screenshot tests render Settings with a throwaway in-memory session.

## M5 slice 1b: live library data and artwork

`LibraryModel` (DiscairUI) holds what the screens show: the mockup's sample data until a session connects, then the owner's library. After a connect `AppState.refreshLibrary()` reads the newest 24 albums, the first 120 albums A-Z, the whole artist list and the Librarian's dashboard picks (picks already in the library are dropped). Album pages read the songs from Navidrome (`getAlbum`); a pick shows the Librarian's suggested tracks as not owned. Artist pages read `getArtist` and add picks by the same artist as missing albums. `ArtworkStore` fetches `getCoverArt` through the active profile (no redirects, memory cache only, failures remembered so a redraw does not retry) and the covers sit on top of the placeholder gradients and patterns.

Live on both themes: Home (Missing picks, Recently added; Zine lead story uses the Librarian's reason and suggested tracks), Albums grid, Album, Artist, Zine A-Z index (any letter, `#` for digits), the "Library N albums" count, the date. Album and artist names open the pages they belong to.

Honest states instead of sample data once live: no Continue listening card (needs playback history), "Nothing playing" in the Zine strip and the Cupertino display (no audio engine yet), "Pipeline: no downloads in progress" in the Zine ticker (Downloads is a later slice), no Top songs (Cupertino) and no Also in this issue box (Zine) on artist pages, because the client has no call for them yet.

Not in this slice: Get / Save / Not for me still do nothing (no Librarian acquisition client yet); the Albums grid shows only the first 120 albums; the Cupertino Songs table and both Queue screens are still sample data (no song-list call in the client); Now Playing is sample; album quality shows the file type and bit rate (Subsonic does not give bit depth or sample rate); no disk cache; artwork needs the app's App Transport Security local-networking exception when the app is bundled (a bare `swift run` binary is not subject to it). The code has not been run against the owner's real server; tests use decoded sample JSON and stub transports.

## M5 slice 2a: acquisition (Get, Save, Not for me, Undo, Never suggest)

`DiscairLibrarian` gained the acquisition calls of Android contract 5.3: `acquire` (album, `auto_queue: true`), `acquireTrack`, `acquisitions` (job list), `skipSource`, `dismissAcquisition` (deletes the job's files, so a Downloads screen must confirm first) and `feedback` (`save`, `dismiss`, `dismiss_artist`, `remove_for_me`). One re-login on a 401 now applies to every Librarian call. A refusal such as `settings_required` arrives as HTTP 200 with `ok: false`, so the result is read, never assumed.

`AcquisitionModel` (DiscairUI) drives the buttons. A Get shows Getting… until the server answers, then Requested (with the server's message) or Retry (with the reason as tooltip and VoiceOver hint); the labels differ by text, not only colour. A job the server already has shows as Requested after a restart. Save shows Saved. Not for me hides the album at once and sends the dismissal after a 6 second Undo window; the notice bar offers Undo and Never suggest <artist> (sends `dismiss_artist` and hides that artist's albums); a failed dismissal brings the album back with a notice. The app sends a waiting dismissal on quit (best effort). Song rows use `acquireTrack`. Jobs are polled every 4 s while something moves, every 30 s otherwise; the Zine ticker and the Cupertino Downloads badge read them.

Not in this slice: the Downloads screens (list, progress bars, skip source, dismiss with confirmation, retry) and the SSE stream (slice 2b); Not for me / Never suggest are lost if the app is killed inside the window; the playlist of "Saved" is not shown anywhere yet; Get on an album already partly owned asks for the whole album. Not run against the owner's Librarian or slskd; tests use recorded fixtures and stub transports.

Fixes after slice 2a (owner report): the Cupertino album track table wrapped two-digit track numbers one digit per line (the number column was 36 pt with 10 pt padding each side); the column is 52 pt and the number, time and title are single-line. The Zine queue number column got the same single-line rule. Recommendations: a failed or missing Librarian read used to leave the Missing shelf silently empty, and the Zine lead story fell back to the sample "Tago Mago" with a real Get button. Now `LibraryModel.picksNote` says why (no Librarian login with an Open Settings button, the server's error, or nothing to recommend), Cupertino Home keeps its Missing heading with that text, and Zine Home shows a "Nothing to recommend" front page with the recently added albums instead of any sample story. The Discover lists (personal, classics, new releases and so on) are still not built; only the Home picks are live.

## M5 slice 2b: Downloads screens

New `Screen.downloads`, reached from the Cupertino sidebar row and the Zine masthead tab (both were dead before). `CupertinoDownloads` (grouped cards, bold sans title, capsule buttons) and `ZineDownloads` ("The Pipeline": 3 pt boxes, mono badges, hard-shadow buttons) read `AcquisitionModel.sortedJobs` (moving, waiting, failed, other, imported; newest first). No mockup exists, so both follow their theme's rules.

State is an icon plus words, with a percent bar and "3 of 11 tracks · 1.2 MB/s" when the server reports progress. Try again is offered for failed jobs (songs re-ask for that song on its album); Use next source only while downloading (the server answers 409 otherwise and its words are shown). Dismiss (a real bordered button in both themes) only hides the card: nothing is sent to the server and no files are deleted, so there is no confirmation. "Clear N imported" hides every imported card the same way. Hidden jobs are remembered in UserDefaults with their `updated_at` and come back if the server changes the job. `dismissAcquisition` stays in the client for a later, explicit "delete files" action. A refused skip or retry shows the server's message in the notice bar.

Not in this slice: the SSE stream (polling stays: 4 s while something moves, 30 s otherwise), covers on the rows, and any run against the real Librarian or slskd. Tests: ordering, progress text, retry request body, skip body, dismiss hides without any server call and survives a restart; screenshots of both themes.


## M5 slice 3a: Discover lists

New `Screen.discover` (Cupertino sidebar row "New", Zine masthead tab "Discover", both dead before). `DiscoveryModel` loads `GET /api/discovery/{personal|classics|new_releases|for_me}` once per list and shows items in the server's order, with no client ranking. Tabs: For you, Classics, New releases, Saved. Each entry has cover, artist (opens the artist when the library has them), the Librarian's reason, up to three suggested tracks, and Get, Save and Not for me as text buttons; dismissed albums disappear through the existing hide rules. An empty list shows the server's own message with "Build this list" (`POST /api/discovery/{list}/refresh`, count 20; not offered for Saved); a failed read shows the reason and Try again.

Not in this slice: artist deep dives and the daily lens lists, "Similar to" chips, the release date column for New releases, and a run against the real Librarian. The refresh payload was never captured, so only its request is tested. Tests: client calls against the recorded `discovery_*` fixtures, model order, empty message, failure and build-then-read, plus screenshots of both themes.

## M5 slice 3b: song list for the Songs table

`NavidromeClient.songs(offset:count:)` calls `search3` with an empty query and only `songCount`/`songOffset`, which Navidrome answers by listing the library by title (up to 500 per page; the app asks for 200). `NavidromeSong` gained `playCount`, `played`, `created`, `bitDepth` and `samplingRate`. `LibraryModel.songs` holds `SongRow`s (now carrying the Navidrome song id and the album the cover comes from, so the audio engine and queue can play them). A live library never shows sample songs: rows are cleared on connect and the first page loads right after the library. Format reads "FLAC 16/44" when depth and rate are known, else "MP3 320"; Last played and Added read "Today", "Yesterday" or "Oct 30". Cupertino's Songs table shows loading, a failure with Try again, "Load more songs" and a footer saying sorting reorders only the loaded songs (a full library sort needs the server, which `search3` does not offer).

Not verified: an empty `search3` query against the owner's Navidrome (it is the documented Navidrome behaviour, and the recorded fixture only covers a real query). Zine has no Songs table (its Library is the A-Z artist index from the mockup). The queue still shows sample rows until the audio engine owns it.

## M5 slice 4a: audio engine, first playback

New package target `DiscairAudio` (no UI): `PlayQueue` (pure: shuffle that keeps the current song first, repeat off/all/one, Play next, Add to queue, button-driven reorder and remove in Up Next), `EngineOutput` (`AVAudioEngine` and one player node, whole file, with a generation number so a stopped or replaced file never reports "finished"), `URLSessionFetcher` (downloads the song to a temporary file; the stream URL carries the login token and is never logged). `PlayerModel` (DiscairUI) joins them: play from a list, pause and resume, next, previous (restarts after 3 s), seek by fraction, shuffle, repeat, and the next song starts by itself when one ends. Vorbis and WMA ask the server for opus at 192; everything else plays the original file.

Wired: Cupertino toolbar (shuffle, previous, play or pause, next, repeat with spoken state) and its now-playing display (cover, title, artist, album, time and a progress line); Zine's bottom strip the same; Songs table double-click, context menu (Play, Play Next, Add to Queue) and a Play button for the selected row; the album and artist Play buttons play an owned album from its first song. A song that fails shows the reason in the display.

Not in this slice (next slices, contract section 12): gapless and next-track preload, crossfade, EQ, starting before the download ends, output sample rate matching, resume-after-restart, queue screens driven by the player (they still show sample rows), seek bar dragging, volume, Now Playing screens, media keys and the system Now Playing widget. Tests: queue rules, the player against a fake output and fetcher, and the real engine on one second of digital silence (skipped on a machine with no audio output). Not heard by me: nothing here has played real music, so the owner's by-ear check of a first song is needed.

## M5 slice 4b: gapless, crossfade and the live queue screens

**Engine (`EngineOutput`, two player nodes).** The model downloads the song that will follow as soon as the current one plays, then hands it to the engine with a transition. *Gapless*: when the next file has the same sample rate and channel count it is scheduled on the same node right behind the current one (the spike measured this as sample-exact); the engine then reports `onAdvanced` at the join. A different format, or any crossfade, starts the next file on the other node: for a crossfade the two levels follow an equal-power curve (cos and sin) stepped every 20 ms and `onAdvanced` fires at the start of the fade; a format change without a fade starts the other node about 30 ms early, so that one join is close but not sample-exact. If the 20 ms ticker is late and the song ends first, the engine joins at that moment instead of reporting the end. If the next song was not ready in time, the old behaviour remains: the song ends and the next one loads (a short gap).

**Rules (`PlayerModel`).** Crossfade is a setting (Off, 2, 4, 6, 8, 10 s; remembered; Settings > Playback in both themes). Two songs that are consecutive tracks of one album (same album id, track n then n+1, or the last track then track 1 of the next disc) always join gapless, whatever the setting. Anything that changes what is next (Play next, Add to queue, reorder, remove, shuffle, repeat, Clear, a new crossfade value) drops the preload and fetches the right one. Repeat one does not preload (the song restarts through the normal path). Skipping, Previous and jumping drop the preload and its file. History (this session, newest first) is kept for the queue screens.

**Queue screens (live).** Cupertino: a list button in the toolbar opens the Up Next inspector; it shows the playing song, then Up Next with each song's duration and an actions menu (Play now, Move up, Move down, Remove from queue), a History tab, a summary ("5 up next · 24 min") and Clear. Zine: Running Order lists the playing song and Up Next with text buttons (Play, Up, Down, Remove), Clear, and "Earlier today" from the session history. Reordering never needs a drag. Not live yet, so hidden once a library is live: Autoplay and radio (needs a Librarian call), Save queue and Saved queues (needs persistence), and the sample History.

**Tests.** Queue rules (peek next, jump, clear), the model against a fake output (preload kinds, engine-driven advance, queue changes replacing the preload, jump and history, continuous-album rule, remembered crossfade) and the real engine on digital silence (gapless join reports one advance and one finish; a crossfade reports one advance and one finish and the position then belongs to the new song; a cancelled preload leaves the song playing to its end).

**Not heard or measured by me:** nothing here has played music, so the owner must listen for the join on a continuous album, the fade between unrelated songs, and the short gap if the next download is late. Not measured: sample-exactness of the same-node join in this build (the spike did it offline), and the fade with Bluetooth or a DAC. Not done: queue persistence across restarts, seek-bar dragging, volume, media keys, EQ.

## M5 slice 5: Now Playing, seek, volume, equalizer, saved queue, media keys

**Now Playing (live).** Cupertino and Zine show the playing song's cover, title, artist and album, a draggable position bar with elapsed and remaining time, real transport buttons (shuffle, previous, play or pause, next, repeat, each with a spoken state) and a volume bar. Lyrics are not built yet, so a live Now Playing says so instead of showing the sample lines (the sample screen still shows them). Chips and buttons are real: EQ opens the Equalizer, crossfade shows the setting, the format chip shows the file suffix. `DragBar` is the shared control: click or drag, left and right arrows, and VoiceOver increment and decrement (5% steps), so neither bar depends on a gesture. Zine's bottom strip uses it for the position too.

**Equalizer.** `Screen.equalizer` (Settings > Playback > Equalizer, or the EQ chip on Now Playing). Ten bands (31 Hz to 16 kHz, one-octave parametric `AVAudioUnitEQ`) after the mixer, so files of different formats share one chain; plus and minus buttons per band (0.5 dB steps, ±12 dB) with the value written out; nine presets with the Android numbers and a Custom slot that keeps the last hand-made curve (moving a band switches to Custom; presets are never changed); a switch (off is a true bypass and the settings are kept); automatic pre-gain (minus the largest boost) or a manual one; Reset behind a confirmation. Settings are remembered. Measured in the M2 spike at 44.1 kHz only: bands and pre-gain are accurate to 0.1 dB.

**Volume** is the app mixer's output level (the system volume is separate) and is remembered.

**Saved queue.** The queue (list as arranged, current song, shuffle, repeat) and the position are saved on every change, on pause and every 5 s while playing, and restored at launch without starting playback: the song shows as current, Play starts it and jumps to the saved position (skipped if under 3 s or within 3 s of the end). A shuffled order is not kept; shuffle starts a new one from the current song. Capped at 500 songs. Previews and screenshot tests use a throwaway settings suite, so they never read or write the real ones.

**Media keys and system Now Playing** (`SystemMedia`): play, pause, toggle, next, previous and seek from the keyboard, Control Centre and the lock screen; title, artist, album, duration, position and rate are reported. Artwork is not sent yet.

**Not heard, run or done:** no real music has played through any of this, the EQ was not re-measured in the app, and the media keys were not pressed (the system may need the app to be a bundled, signed app before it routes keys to it). Still not built: lyrics, the Now Playing blurred artwork backdrop (still gradient fields), quality cap setting, scrobbling, the output sample-rate matching, starting before the download ends.

## M5 slice 6: lyrics, blurred artwork, streaming quality cap

**Lyrics** (port of `ANDROID_LYRICS_CONTRACT.md`). `NavidromeClient.lyrics(songID:)` calls `getLyricsBySongId` (waits up to 45 s; slow lookups were measured at 4 to 12 s, some over 23 s) and `supportsLyrics()` reads `getOpenSubsonicExtensions` once per connection. `LyricsChooser` prefers a timed entry then a plain one, the phone's language then the first listed, sorts timed lines, applies an explicit `offset` (never below 0), drops lines without a start or with a negative one, strips control characters, cuts lines at 500 characters and lists at 2000, keeps empty lines as pauses, and treats equal or backward starts as plain. Subsonic code 70 (unknown song) means "no lyrics". `LyricsTimeline.currentIndex` is a binary search for the last line that started at or before the position. `LyricsModel` fetches only for the song a lyrics screen shows, answers from the cache at once, asks the server only on a miss or a copy older than a day (a "none" answer is trusted for 24 h), shows a stale copy marked "Saved copy" when the server cannot be reached, and prefetches the next song once lyrics have loaded. The cache is one small file per song under Application Support, keyed by server and user, at most 300 songs or 5 MB, and is deleted at sign-out of Navidrome (Settings). Lyrics text is never logged; tests use placeholder text. Screens: every state is written out (loading, timed, plain with "These lyrics are not timed.", none, "Your Navidrome doesn't provide lyrics.", failure with Try again). Timed lines follow the music and keep the current line centred; scrolling by hand stops following and shows "Back to the current line"; reduced motion jumps instead of animating; tapping a line does nothing (owner decision on Android). Cupertino: bold lines beside the cover, others dimmed. Zine: italic serif column with the current line highlighted yellow.

**Blurred artwork.** `BlurredArtwork` is the cover, enlarged and blurred, laid over the existing colour fields as the Cupertino Now Playing backdrop and the Cupertino Artist banner (the first owned album's cover). While the image loads, or when there is none, the gradient shows. It is decorative (hidden from VoiceOver) and is not blurred in screenshot tests, where the blur does not render and there is no artwork anyway. Zine keeps its halftone cover.

**Streaming quality cap.** Settings > Playback in both themes: Original, 320, 256, 192, 128, 96 or 64 kbps (remembered, only allowlisted values are read back). A cap is sent as `maxBitRate` for every song, so the server converts only files above it; Ogg Vorbis and WMA go as opus at the lower of 192 and the cap. It applies to songs started afterwards; changing it drops the preloaded next song. If the Mac cannot decode a file, the song is asked for once as an MP3 (at the cap, else 320), the owner is told on Now Playing, and the saved quality is not changed. Now Playing shows the setting.

**Not verified:** nothing here ran against the owner's Navidrome (lyrics call, extension list, a converted stream) or was heard or seen live; the blur and the lyrics scroll were not seen with real artwork and a playing song. The conversion format Navidrome picks for a plain `maxBitRate` is the server's default. Not built: artwork in the system Now Playing, scrobbling, sample-rate matching, starting before the download ends.

## M5 live-test fixes

Found by the owner's first live run of PR #725.

- **Librarian calls refused after a good login.** `URLSessionTransport(keepCookies: true)` replaced the ephemeral session's cookie jar with a bare `HTTPCookieStorage()`, which stores nothing, so the session cookie from `api/auth/login` was never sent back and every call got 401 ("The server refused the login"). It now keeps the ephemeral configuration's own jar. A new test runs a real `URLSession` against a local server (login sets the cookie, the next call must carry it); the fake transport used before could not catch this.
- **Dragging moved the window.** The window drags by its background, which took the mouse-down before the seek bar. Controls that read drags now sit on a view with `mouseDownCanMoveWindow = false` (`blocksWindowDrag()`), checked by a hit-test unit test. The EQ bands and the queue rows had no drag at all before (buttons and menus only); EQ bands now follow a vertical drag or click (-12 to +12 dB, 0.5 dB steps), and Up Next rows reorder by dragging a row onto another in both themes. The buttons and menus stay.
- **EQ buttons.** Plus above the band, minus below, in both themes.
- **Blurred artwork.** The blur radius was 80 on a 300 px cover with two dark overlays, which flattens any cover into a gradient. Radius is now 28 (24 on the artist banner), cover requested at 600 px, overlays lighter. Not seen with a real cover by me: blur does not render in the offscreen screenshot path.
- **Crossfade.** Consecutive tracks of one album stay gapless by contract (section 5), and Settings now says so; but the owner also heard no fade between unrelated songs. The engine and the model both ramp the levels correctly on an idle machine (new tests, incl. different sample rates and two fades in a row). One real weakness found: the fade was advanced by counting 20 ms ticks, so a busy main thread made it lag the audio and the old song could end before its level reached zero (a cut). The fade now follows the audio clock (`max(ticks, new song's position)`); a test that blocks the main thread for a second fails without it (level 0.79 instead of 1.0). Not proven to be the owner's exact cause; not heard by me.
- **The screen switched to the next song when a crossfade began.** The owner confirmed the fade is audible but the Now Playing title, position and lyrics jumped to the next song at the start of the fade. The engine now reports the old song's position and length during a fade and announces the advance (`onAdvanced`) when the fade ends, so the model, queue, title, lyrics and system Now Playing change together at the end of the old song. Gapless joins are unchanged. Two edges: a seek during a fade ends the fade and the new song carries on (the bar belonged to the song that was ending); Next pressed during a fade restarts the song that was fading in, from its start.
- **Blurred artwork was never drawn (second try).** Lowering the blur did nothing because the cover was not drawn at all: `ArtworkImage` was a `Group` that is empty until the image arrives, and the load task attached to it does not start when the view stands alone (the backdrops are the only places it has no placeholder view under it; covers in grids sit on a gradient and worked). It now sits on a clear view that carries the task. A new test hosts a standalone `BlurredArtwork` in a window with a striped cover served by a fake transport and checks the stripes are drawn; it fails without the fix. The blur itself does not render in the offscreen capture, so it was checked with `ImageRenderer` with the same modifiers (radius 28: stripes and shapes are still recognisable). Not seen by me in the real window.
- **Dragging a queue row moved the window too.** A row that is a drag source (`draggable`) gets a view of its own on top of the row, so the blocker underneath never saw the click. The blocker is now an overlay, and it only covers the part you grab to reorder (cover and title area, `RowDragSource`), not the whole row: an overlay on the whole row would sit over the Cupertino actions menu, which is an AppKit control, and take its clicks. A hit-test unit test covers a draggable row.

## M5 slice 7: scrobbling

Port of `ANDROID_PLAYER_CONTRACT.md` section 4. `NavidromeClient.scrobble(songID:time:submission:)` calls `scrobble.view` with the id, the play start time in milliseconds and `submission` (false is now-playing, true is the final scrobble) and answers `sent`, `notSent` (DNS, connect or no-network failure: nothing left the Mac) or `unknown` (timeout, reset, error status or unreadable answer: it may have arrived). `ScrobbleTracker` (pure) counts played time from the position, four readings a second: small forward steps while playing count, pauses, seeks and backward moves add nothing; the final scrobble fires at `min(length / 2, 240 s)` for songs of 30 s or more (240 s when the length is unknown; the larger of the server and engine lengths when they differ by over 10 %). `ScrobbleCoordinator` keeps one play per start of a song (a new queue entry, a repeat-one loop or the same song chosen again), sends now-playing once when the player is actually playing, and retries the final scrobble only after `notSent`, three times after 2 s, 10 s and 30 s with the original start time. An `unknown` outcome is never repeated. A restored queue begins no play until the owner presses play. Settings > Playback has the On/Off switch in both themes (remembered per Mac, on by default); off sends nothing and cancels pending retries, on mid-song counts from that moment with no backfill. Failures never touch playback.

**Tests run:** 10 tracker, 3 client and 7 coordinator tests (`swift test`, full package 249 passed). **Not verified:** no scrobble was sent to the owner's Navidrome, so the `time` and `submission` parameters are not confirmed against that server version and nothing was checked in Navidrome's play history or Last.fm.

## M5 slice 8: offline banner and saved pages

The last good answer of each read-only page is kept on disk (`PageCache`, `Application Support/Discair/pages/<hash of scope>/<hash of key>.json`, one folder per Navidrome user): Home data (newest, first 120 albums, artists, picks), each album's songs, each artist's albums and the first Songs page. A good read replaces the file; a failed read (server unreachable, no network, Tailscale off, a server error) shows the saved copy instead, and `LibraryModel.savedCopyDate` and `savedCopyReason` are set. At launch, if the connection itself fails, `SessionModel.onConnectFailed` makes `AppState` show the saved Home data. A refused login is not "offline" and still fails. Files are named by hash (a key cannot name a path), capped at 400 files or 20 MB with oldest removed first, and deleted at Navidrome sign-out together with the lyrics cache. Saved pages are keyed by the Navidrome username, not the address, so the LAN and Tailscale profiles of one library share them.

`OfflineBanner` (one per theme: a card strip in Cupertino, a yellow bordered strip in Zine) sits above the window content while a saved copy is shown: "Offline. <reason> Showing your library as saved <when>. Get, Save and Not for me need the server." with a Retry button (reconnects, or re-reads the library when the connection is fine). The next good read clears it. Get, Save and Not for me keep failing with the server's reason; nothing is queued offline.

**Not done here:** cover art is still memory-only, so offline covers show the placeholder colour until the optional disk cache slice; playback of songs not already downloaded needs the server; the Songs table saves only its first page; Discover lists and Downloads are not saved. **Tests run:** 11 new (page cache, fallbacks for Home, album, artist and Songs, refused login, sign-out, notice text and banner render); full package 260 passed. **Not seen:** the banner was not looked at in a running window.

## M5 slice 9: the optional media cache (2 GB)

`MediaCache` (`DiscairAudio`) is an on-disk copy of played songs and cover art in `~/Library/Caches/Discair/media/<hash of Navidrome user>/`. **Off by default**; the switch is remembered (`CacheModel`, Settings > Playback in both themes, with a readout such as "412 MB of 2 GB" and a Clear button). Off means nothing is read or written; files already there stay until cleared. Capped at 2 GB (2,000,000,000 bytes); after each save the least recently used files are removed until it fits, and a hit marks the file as just used. File names are a hash of the key, so a key cannot name a path. Cleared at Navidrome sign-out together with the lyrics and saved pages.

- **Songs:** `CachingFetcher` wraps the downloader. The key is the song id, the bit-rate cap and the format (never the login token or salt), so a different quality is a different entry. A hit is copied (a clone on APFS) to the player's temporary file, because the player deletes its file when done; a miss downloads, then keeps a copy. A cached song plays with the server unreachable. Songs preloaded for gapless or crossfade are cached too.
- **Covers:** `ArtworkStore` checks the memory cache, then the disk cache, then the server, and keeps the bytes it fetched. With the cache on, covers also show offline (the gap left in slice 8).
- **Metadata:** the saved pages of slice 8 stay always on (they are what makes the Offline banner work, 20 MB at most, deleted at sign-out); the Clear button here clears the media files, not those pages. This is a change from the contract wording ("audio, covers and metadata"), made so the offline view does not depend on a switch that is off by default.

**Tests run:** 8 (cache and fetcher: off by default, LRU and refresh on read, path safety, per-user isolation, token-independent hit, quality as part of the key) and 4 (switch remembered, readout and Clear, covers served from disk with the server gone, nothing kept when off); full package 272 passed. **Not done or not seen:** Settings not looked at in a running window; no real song was played through it; the 2 GB limit was tested with small limits, not filled; a song partly downloaded is not cached (nothing is kept unless the download finished).
