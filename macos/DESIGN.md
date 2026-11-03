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
