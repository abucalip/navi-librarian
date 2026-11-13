# macOS Home, "Marquee" layout: implementation plan

Status: **plan only, nothing built.** The owner chose this layout on 2026-11-13 from three mockups. The owner's reason for the change: the current Home is too number-driven; Home should be artwork-driven, with only a few statistics.

The mockups are the spec: [`design/macos-home-marquee/mockups.html`](design/macos-home-marquee/mockups.html) (open in a browser, no network needed). Where this text and a mockup differ, the mockup wins, except for the corrections listed in section 9.

This plan replaces section 5.1 of [`redesign.md`](redesign.md) for the layout of Home. The design system in section 4 of that document (colour roles, type roles, spacing, controls) still applies in full.

## 1. What changes

Home today (built in M8) has eleven modules, six of them charts or figures. The new Home has four parts:

| # | Part | What it shows |
|---|---|---|
| 0 | Notice slot | Unchanged: at most one of Librarian unreachable, a failed Get, playing on the phone |
| 1 | Marquee | Today's pick, large, over its own blurred cover. The other picks as small covers |
| 2 | New on the shelf | Six covers: Gets in progress, arrived albums not played yet, songs heard on the radio, then recently added albums |
| 3 | Waiting longest | Six covers: albums that have waited longest for a play |
| 4 | Summary line | The taste headline and up to four figures, as one line of text |

The Liner note card (`LinerNoteCard`) stays at the bottom of the page, unchanged. The page header ("Home" and the date) is unchanged.

### What leaves Home and where it goes

| Module today | Goes to | How |
|---|---|---|
| Briefing band (four large figures) | Summary line | Three of its figures become words in the line. The "Waiting for you" figure is dropped: the marquee already says "1 of 7" |
| Collection over time (chart) | Insights, new section "Your collection" | Moved as it is |
| Own and play, by decade (chart) | Insights, "Your collection" | Moved as it is |
| Shelf life (histogram) | Insights, "Your collection" | Moved as it is, without the four small covers (they become "Waiting longest" on Home) |
| Your taste (headline and dumbbells) | Insights, "Your collection" | Moved as it is. Home keeps the headline sentence only |
| From the lenses (three rows) | Removed | The Insights page already is the lenses |
| Server activity | Settings, Services tab, last section | Moved as it is |
| Arrivals (rows) | "New on the shelf" | Same data, drawn as cover tiles |
| Recently added (six covers) | "New on the shelf" | Fills the row after the arrivals |

No figure is deleted from the app. Every chart is still one click away, on Insights.

## 2. Layout and measures

Sizes are points. Content is 980 wide at the 1280 window, as today. All spacing uses `CU.Space` (4, 8, 16, 24, 32). The CSS the mockups use is in [`design/macos-home-marquee/home-marquee.css`](design/macos-home-marquee/home-marquee.css); read the measures from it when this table is silent.

| Element | Measure |
|---|---|
| Page | Vertical stack, 24 between parts |
| Marquee panel | Full width, corner radius 18, padding 24, minimum height 292 |
| Marquee cover | 240 × 240, radius 12, shadow black 45%, radius 40, y 14. 160 × 160 when the content is under 860 wide |
| Marquee text column | 24 from the cover. Eyebrow, title (34 bold, tracking −0.5, two lines at most), artist line (15), reason (14, line height 1.45, four lines at most, about 52 characters wide), suggested track, then the buttons pinned to the bottom |
| Next picks | Trailing edge, bottom aligned. Eyebrow "Next picks", then covers 46 × 46, radius 6, gap 6, three per row, two rows at most |
| Shelf header | Title (17 bold), subtitle (12, secondary) on the same baseline, one text button at the trailing edge |
| Shelf grid | Six equal columns, gap 16. Three columns when the content is under 860 wide |
| Shelf tile | Square cover filling the column (about 150), radius 8, the shadow the Recently added covers use today. Under it: title (headline, one line), artist (secondary, one line), status (callout, one line) |
| Tile overlays | Stage ring 38 across, centred, over a black 50% wash. Play button 30 across, bottom right, 8 in. "Radio" tag top left, 7 in |
| Summary line | Hairline above (`CU.separator`), 16 above the text. Taste sentence (14) takes the free width; figures follow at 16 apart, number in semibold primary, label in secondary |

### The marquee's colours

The marquee is the only place on Home where text sits on artwork. It looks the same in Day and in Night.

- Background: `BlurredArtwork(album:)` with radius 44, clipped to the panel. Under it, the album's `CoverView` colour gradient, so the panel has colour while the image loads or when there is none.
- Over the artwork: a flat black wash at 55%. This is the lowest value that keeps white text at 4.5:1 over a pure white cover (the wash alone gives `#737373`, 4.7:1). Do not lower it.
- All text on the marquee is white at full opacity. Hierarchy comes from size and weight, not from opacity.
- Get: white fill, label in the Day `accentStrong` (`#C8163F`) in both modes. Save, Not for me, and the suggested track's round button: white at 20% fill, white label.
- Focus ring (keyboard): white at 60%, 3 wide, 4 outside the panel.
- `RenderMode.offscreenScreenshot` already switches the blur off for screenshot tests; nothing new is needed.

## 3. Rules for each part

The rule from M5 stays: **missing is not zero.** A figure or tile whose source is absent is left out or replaced by a sentence. Nothing is invented.

### 3.1 Marquee

- The album is `picks[pickIndex]`, as today (`state.visible(state.library.missing)`), with the same eyebrow "Today's pick · 1 of 7" (`HomeScreen.pickPosition`).
- Title, artist line, the server's reason, the suggested track, and the three buttons keep today's text, states, help text and actions (`pickButtons`, `suggestedTrack`, `act`). Only their place and colours change.
- Keys are unchanged: → Get, ↓ Save, ← Not for me, Space plays or shows the "not owned" notice. The key hints row is removed; each key is shown inside its button, as drawn. Space has no hint on screen; it stays in the button's help text.
- **Next picks** replace the two chevron buttons. They show the other picks in order, starting after the current one and wrapping round, six at most. A click shows that pick in the marquee. With one pick the block is not drawn. Each cover is a button named "Show pick 3 of 7: *title* by *artist*".
- **No pick** (`HomeScreen.pickEmpty`): the panel keeps its minimum height and becomes a plain `bg.panel` panel with no artwork, with today's three sets of sentences and buttons unchanged (`needsHistory`, `noneRightNow`, `withoutLibrarian`). See `home-marquee--no-pick`, `--first-run` and `--librarian-unreachable`.

### 3.2 New on the shelf

Up to six tiles, in this order:

1. The rows of `HomeDashboard.arrivals`, in their existing order and with the existing cap of four (Gets needing attention, moving, waiting, arrived and not played, radio songs).
2. Then recently added albums, newest first, leaving out any album already shown in step 1, until there are six tiles.

| Tile | Cover | Overlay | Status line | Click |
|---|---|---|---|---|
| Get, in progress | Colour placeholder (a Get has no artwork yet) | Ring: one, two or three quarters for Found, Downloading, Importing | "Looking for a source", "Downloading" or "Importing", in `warning` | Opens Downloads |
| Get, failed | Colour placeholder | Warning triangle icon over a black 60% wash | "Failed · " and the server's reason, in `danger` | Opens Downloads |
| Arrived, not played | The album's cover | Play button | "Arrived today", "Arrived yesterday", or "Arrived 9 November", in `accentStrong` | Cover opens the album. Play button plays it |
| Heard on the radio | Colour placeholder | "Radio" tag | "Heard on FIP · Get", in `accentStrong` | Gets the song (`state.getRadioPlay`). The tile then follows the Download states of the radio plan |
| Recently added | The album's cover | None | "Added 9 November", secondary | Opens the album |

- Header subtitle: "arriving, just arrived and heard on the radio". When every tile is a recently added album, it is "recently added".
- Header button: "All downloads".
- Empty (no arrivals and no albums): the sentence "Nothing here yet. Albums you Get appear here while they download, and new albums stay for a while after they arrive." The part is not removed.
- With Librarian unreachable the Gets and radio songs are unknown, so the row holds recently added albums only.
- The failed tile follows the rule of `redesign.md` 4.1: danger is never shown without its icon and a sentence.

### 3.3 Waiting longest

- Six albums, from `HomeDashboard.ShelfLife.longestUnplayed`, whose limit rises from four to six. The order is unchanged: never played albums, oldest added first; if there are fewer than six, albums with the oldest last play fill the row.
- Status line: "Since March 2023" (the month the album was added) for a never played album; "Last played March 2023" for the others.
- Header subtitle: "albums you own and have never played" when all six were never played, otherwise "albums you have not played for the longest time".
- Header button: "Play something unplayed" (`state.playSomethingUnplayed()`), not drawn when no album is unplayed.
- Click on a tile opens the album.
- Empty: "Nothing is waiting. Every album you own has been played." With an empty or unread library: "Albums you own and have not played yet appear here."

### 3.4 Summary line

- Left: the server's taste headline in quotation marks, only when `HomeScreen.taste` is `.ready`. In every other state nothing is drawn there; Insights explains the taste state. A click opens Insights.
- Right, in this order, each left out when its value is nil:

| Figure | Source | Words | Click |
|---|---|---|---|
| Albums | `albumCount` | "1,248 albums" | Library |
| Added | `added.last` | "14 added in 30 days" | Library |
| Listens | `listens.last` | "186 listens in 7 days". When the series is stale (`asOf` older than yesterday): "186 listens in the 7 days to 9 November" | History |
| Never played | `neverPlayed` | "312 never played" | `state.openNeverPlayedAlbums()` |

- Singular forms: "1 album", "1 listen". Numbers use tabular figures and thousands separators (`HomeScreen.count`).
- Each figure is a plain button with the same accessibility hint its stat has today ("Opens your Library", and so on).
- Under 860 wide the taste sentence takes its own line and the figures wrap below it.

### 3.5 Notice, loading, narrow

- Notice: `notice` is used as it is, above the marquee.
- Loading (`HomeScreen.page` is `.loading`): one block of 292 for the marquee, then two rows, each a 170 × 20 block and six square blocks. See `home-marquee--loading`.
- Narrow (content under 860, `HomeScreen.isStacked`): see `home-marquee--narrow`.

## 4. Code to reuse

| Need | Existing code |
|---|---|
| Figures and rows | `Model/HomeDashboard.swift` (`arrivals`, `shelfLife.longestUnplayed`, `albumCount`, `added`, `listens`, `neverPlayed`, `notice`) |
| Wording and pure rules | `Model/HomeScreen.swift` (`pickPosition`, `pickKey`, `spaceOutcome`, `pickEmpty`, `taste`, `parseDate`, `dayAndMonth`, `count`, `isStacked`, `page`) |
| The pick's buttons and actions | `CupertinoHome.swift`: `pickButtons`, `suggestedTrack`, `act`, `pickEmptyState`, `pickNoticeView` |
| Blurred cover | `Chrome/CoverView.swift`: `BlurredArtwork`, `CoverView` |
| Placeholder cover for a Get or a radio song | `CupertinoHome.placeholder(title:artist:)` |
| An owned album from its Navidrome id | `CupertinoHome.ownedItem(_:)` |
| Notice, headers, skeleton blocks | `CUNotice`, `HomeHeader`, `HomeEyebrow`, `HomeSkeletonBlock` (`CupertinoHomeParts.swift`) |
| White text on blurred artwork, as a reference | `CupertinoNowPlaying.backdrop`, `CupertinoPlayerBar` |

## 5. Slices

One PR per slice, each from current `main`. Run only the filtered tests named in the slice (`docs/DEVELOPMENT_WORKFLOW.md`, selective testing). Swift tests run locally on a Mac.

### H1 · Data and wording (no visible change)

Pure code and tests only. Suggested model: Haiku, high effort.

1. `HomeDashboard`: raise the `longestUnplayed` limit from 4 to 6 (one named constant). Add `recentlyAdded: [String]`, the Navidrome ids of the six newest albums by `created`, leaving out ids that appear in an `.arrived` row. Empty when the album list was not read.
2. `HomeScreen`, new pure functions:
   - `shelfTiles(arrivals:recentlyAdded:limit:)` returns the ordered tiles of 3.2 as an enum (`job`, `arrived`, `radio`, `added`).
   - `shelfStatus(...)` returns the status line and its colour role for a tile, including "today", "yesterday" and the full date.
   - `shelfSubtitle(tiles:)`.
   - `stageFraction(_:)`: 0.25, 0.5, 0.75 for Found, Downloading, Importing.
   - `waitingCaption(created:played:neverPlayed:)` and `waitingSubtitle(allNeverPlayed:)`. Add `monthAndYear(_:)` beside `dayAndMonth`.
   - `nextPicks(index:count:limit:)` returns the indices of 3.1, wrapping.
   - `summaryFigures(dashboard:now:)` returns the figures of 3.4 with their words and a target enum.
3. Tests, in `HomeDashboardTests` and `HomeScreenTests`: six waiting albums and the fill rule; `recentlyAdded` leaves out arrived albums; tile order and the cap of six; every status line; the three stage fractions; the wrap of `nextPicks` with 1, 2 and 8 picks; nil figures are left out; singular forms; the stale listens wording.
4. Run: `swift test --filter "HomeDashboardTests|HomeScreenTests"`.

Acceptance: the existing Home renders as before (the four small covers of Shelf life take `prefix(4)`).

### H2 · Move the charts to Insights and Server activity to Settings

Suggested model: Sonnet, medium effort.

1. Move `collectionPanel`, `decadesPanel`, `tastePanel`, `shelfPanel` (and their helpers and `@State`) out of `CupertinoHome.swift` into a new `Themes/Cupertino/CupertinoCollectionPanels.swift`, as views that take `state` and `stacked`. Move `activityPanel` into a view in the same way. No change to what they draw, except that the Shelf life panel loses its "Longest since a play" covers.
2. `CupertinoInsights`: add a section "Your collection" above "Lenses", with the four panels in two rows (collection 2:1 decades, taste 1:1 shelf life), stacking under 860. The page calls `state.refreshHomeDashboard()` in a `.task`, since it now draws those figures.
3. Settings, Services tab: add "Server activity" as the last section.
4. Home keeps showing the moved panels through the new views in this slice, so nothing disappears between two merges.
5. Tests: the existing `HomeRenderTests` still pass. Add one render test for Insights with the new section and one for the Services tab. Run: `swift test --filter "HomeRenderTests|InsightsRenderTests|ServicesRenderTests"` (use the names of the existing suites for those two pages if they already exist).

Acceptance: Insights shows the four panels with the same states as on Home; Settings shows Server activity; Home is unchanged to the eye apart from the four small covers.

### H3 · The new Home

Suggested model: Sonnet, high effort.

1. Rewrite the `page` of `CupertinoHome`: notice, marquee, New on the shelf, Waiting longest, summary line, `LinerNoteCard`. Build each part from sections 2 and 3 and the mockups.
2. Remove from Home: the briefing band, the calls to the moved panels, the lens rows, the Arrivals panel, the Recently added row, the key hints row and the chevron buttons.
3. Remove `await state.loadInsights()` from Home's tasks: Home no longer shows lens cards, so it must not request them. Keep `loadHomeFeeds`, `refreshHomeDashboard` and `reshufflePicks`.
4. Delete code that nothing uses any more, with its tests. Check each with a search before deleting: `HomeStat`, `HomeChange`, `HomeKeyHint`, `HomeSplit` (if Insights does not use it), `HomeScreen.addedLine`, `neverPlayedLine`, `listensTile`, `listensLine`, `waitingTile`, `lenses`, and `HomeDashboard.Waiting`. Keep anything the Insights panels still use.
5. Skeleton and narrow layout as in 3.5.
6. Accessibility (section 6).
7. Tests: replace the cases of `HomeRenderTests` with the seven mockup states (default, notice, no pick, first run, Librarian unreachable, loading, narrow), default in Day and in Night. Run: `swift test --filter "HomeRenderTests|HomeScreenTests|HomeDashboardTests"`.
8. Documents: rewrite `redesign.md` 5.1 to describe the built Home and point here; update `macos/DESIGN.md`, `docs/ACTIVE_WORK.md`, `docs/PROJECT_STATUS.md` and `PROJECT_LOG.md` as the workflow requires.

Acceptance: each of the seven states matches its mockup in Day and Night; the marquee has one primary button; no chart and no figure tile remains on Home; the pick's keys work as before.

### H4 · Owner check and fixes

The owner runs the app against the real server and compares it with the mockups (section 8). Fixes from that check go in one PR.

## 6. Accessibility

- Reading order: notice, marquee, New on the shelf, Waiting longest, summary line.
- The marquee is one container named "Today's pick, 1 of 7", as today. The blurred background is hidden from VoiceOver (it already is, in `BlurredArtwork`).
- Each shelf title is a header. Each tile is one element: "*title* by *artist*, *status line*". The Play button on an arrived tile is a separate button, "Play *title*". The radio tile is a button, "Get *title* by *artist*".
- The stage ring is decorative; the stage is in the status line.
- Colour is never the only signal: a failed Get has an icon and words, a Get in progress has its stage in words.
- The summary figures are buttons with hints. The taste sentence is a button, "Open Insights".
- Contrast: the 55% wash keeps white text at 4.5:1 or more on any cover (section 2). Status lines use `warning`, `danger` and `accentStrong`, which already pass on `bg.content` in both modes.
- Reduced motion: nothing on this page animates except the standard button states.

## 7. What this plan does not do

- No server change and no Android change. Every value comes from a model the Mac app already holds.
- No new request: Home makes one request fewer (the lens cards).
- No change to the pick's actions, to Downloads, or to how picks are chosen.
- It does not build the radio card (E7) of the radio plan. When that slice is built, the card goes between the marquee and "New on the shelf", full width, not in "Home's first row" as `RADIO_PLAYBACK_PROPOSAL.md` says.

## 8. Owner checks after H3

1. Home with a pick: the marquee shows the cover, the blurred backdrop takes the cover's colours, and the text is easy to read on a light cover and on a dark one.
2. →, ↓, ←, Space on the pick; a click on a "Next picks" cover.
3. Get an album and watch its tile go from Looking for a source to Arrived, then play it from the tile.
4. A song heard on a relayed station appears as a "Radio" tile and its Get works.
5. Waiting longest shows six albums that really have no plays.
6. Each figure in the line opens the right page.
7. Insights shows the four moved charts; Settings, Services shows Server activity.
8. Day and Night; a narrow window; the queue inspector open.

## 9. Choices made in this plan

The first mockup (2026-11-13) was a sketch. Writing the plan fixed these points; the mockups in this folder already show them. Each can be changed before H3.

1. The charts go to a new "Your collection" section on Insights, not to a new page.
2. The lens rows are removed from Home, not moved.
3. Server activity goes to Settings, Services.
4. The "Waiting for you" figure (picks and unplayed arrivals) is dropped.
5. "Next picks" covers replace the chevron buttons.
6. The figures say "in 30 days" and "in 7 days", which is what the data measures. The sketch said "this month" and "this week".
7. The marquee's wash is a flat 55% black, darker than the sketch, and its text is fully white, to keep 4.5:1 on any cover.
8. The stage ring shows the stage in quarters, not a percentage: the app knows a Get's stage, not how far a download is.
9. The arrived tiles say "Arrived today" without "unplayed": the row only ever shows arrived albums that have no plays.
