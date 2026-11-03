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
- **Cupertino Home:** built from the mockup (inset glass sidebar, glass toolbar pieces and centre display, opaque white content, Continue listening card, Missing shelf with Get / Save / Not for me, Recently added). Not yet built: the other five screens, the trailing Up Next inspector.
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

**Differences from the approved mockups (owner to decide):**
1. **Connection indicator at the bottom of the sidebar** (and the "unencrypted" badge, contract section 3). HIG: people often move windows so the bottom edge is off screen; keep critical information and actions away from the bottom of sidebars and windows. Proposal: show the active profile and the unencrypted badge in the toolbar or at the top of the sidebar.
2. **Zine Spread black player strip at the bottom.** Same HIG rule for the window bottom. Proposal: keep the strip as drawn (approved "very good"), and also expose transport in the menu bar, media keys and the mini window so playback never depends on the strip being on screen.
3. **Tinted glass** (74% light tint, owner approved on 2026-11-03). HIG prefers few toolbar backgrounds and tints. Kept as approved; revisit if legibility checks fail.
4. **Fixed red-pink accent in sidebar icons.** HIG: sidebar icons follow the system accent colour unless a fixed colour has a purpose. The accent is part of the Cupertino identity, so it stays fixed for that theme.
5. **Custom traffic lights.** The system buttons are hidden and redrawn (contract decision); they must keep close, minimise and zoom behaviour and VoiceOver labels.
