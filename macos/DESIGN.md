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

## Open before M4

- Read the HIG pages for Toolbars, Sidebars, Materials and Layout directly (contract 4.1).
