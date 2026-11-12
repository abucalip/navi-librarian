# Discair redesign: macOS Cupertino and Android

Status: **proposal; M1 to M9 built and merged (audit follow-ups F1 to F13 listed under macOS, not started); M10a (drawn pages) and M10b (token-only pages) merged; M10 is done; S2 (lens refresh status, D3) is merged in PR [#987](https://github.com/abucalip/navi-librarian/pull/987), squash `67dc7dce`, 2026-11-11. S1 (listens by day, D2) is merged in PR [#986](https://github.com/abucalip/navi-librarian/pull/986), squash `41449e29`, 2026-11-11. M10b is PR [#985](https://github.com/abucalip/navi-librarian/pull/985), squash `c9a10549`, 2026-11-11.** A1 (Android palette roles and type) is merged in PR [#992](https://github.com/abucalip/navi-librarian/pull/992), squash `43436b56`, 2026-11-12. A2 (Android motion kit) is merged in PR [#993](https://github.com/abucalip/navi-librarian/pull/993), squash `339f7551`, 2026-11-12. A3 (navigation) is merged in PR [#994](https://github.com/abucalip/navi-librarian/pull/994), squash `596562d3`, 2026-11-12. A4 (Android charts) is merged in PR [#996](https://github.com/abucalip/navi-librarian/pull/996), squash `ddb669b5`, 2026-11-12. A5 (Android sheets and feedback) is merged in PR [#997](https://github.com/abucalip/navi-librarian/pull/997), squash `271d74f4`, 2026-11-12. A6 (Android dashboard) is merged in PR [#998](https://github.com/abucalip/navi-librarian/pull/998), squash `56297976`, 2026-11-12. A7 (Android stats and Server screens) is merged in PR [#999](https://github.com/abucalip/navi-librarian/pull/999), squash `519b6c75`, 2026-11-12. A8 (Android Discover, Library, Search, Downloads, Settings) is merged in PR [#1000](https://github.com/abucalip/navi-librarian/pull/1000), squash `ee3571df`, 2026-11-12; part of it is not built and is listed as A8b. (PR [#975](https://github.com/abucalip/navi-librarian/pull/975), squash `f0aba3d6`; PR [#976](https://github.com/abucalip/navi-librarian/pull/976), squash `e3e69220`; PR [#977](https://github.com/abucalip/navi-librarian/pull/977), squash `e3e63b0c`; PR [#978](https://github.com/abucalip/navi-librarian/pull/978), squash `2480b3a2`; PR [#979](https://github.com/abucalip/navi-librarian/pull/979), squash `3bf66cb2`; PR [#980](https://github.com/abucalip/navi-librarian/pull/980), squash `cf175239`; PR [#981](https://github.com/abucalip/navi-librarian/pull/981), squash `7e705614`; PR [#982](https://github.com/abucalip/navi-librarian/pull/982), squash `f9bccff8`; PR [#983](https://github.com/abucalip/navi-librarian/pull/983), squash `344252e3`; PR [#984](https://github.com/abucalip/navi-librarian/pull/984), squash `16cb3d9d`; all 2026-11-11). Every other step is not started. Nothing else here has been implemented, tested or approved by the owner.

Scope: the macOS client's Cupertino theme, and the Android client. The macOS Zine theme and the web client are out of scope and are not touched.

Mockups: [`docs/design/redesign/`](design/redesign/). Each screen is an HTML file with a PNG render beside it. The design tokens are the custom properties at the top of [`cupertino.css`](design/redesign/macos/cupertino/cupertino.css) and [`android.css`](design/redesign/android/android.css); where this document and a stylesheet disagree, the stylesheet is right.

## 0. Read this first

Four things an implementer or the owner must know before using this document.

1. **"Connections" means two things, and both are designed.** In the app, Connections is the credit graph (`GraphExplorerView`, `GET /api/knowledge/connections`). The brief describes a page about connected services, their health and configuration. No such page exists: service state is one 11 pt line at the bottom left and a card in Settings. This document redesigns the credit graph (section 5) **and** adds a Services surface in Settings with a status button in the toolbar (section 6). The owner should say if the service page was meant to replace the graph page under that name.
2. **Android has 27 palettes, not four themes.** "Day, Night, Tape, Sheet" is read as the four layout families' default palettes: Day is Sand, Night is Night, Tape is Tape · Lime, Sheet is Sheet · Violet-orange. Every other palette keeps working because the redesign adds roles to `Palette` instead of hard-coding colours.
3. **Mockup coverage is partial by the owner's instruction (2026-11-11).** macOS: Home, Connections and Services have their states drawn; the other pages have the normal state only. Android: **only Day · Sand is drawn**, normal states only. Night, Tape and Sheet are specified in words and tokens (section 7.3) and have no mockup. An implementer of those three themes works from the Day mockups plus the theme rules, and the result needs owner review.
4. **Some dashboard modules need server work that does not exist.** They are listed in section 9 and marked in each screen spec. No mockup pretends otherwise: every such module has a stated hidden or "not available" state.

## 1. Assessment of the current clients

### 1.1 macOS Cupertino

Keep: the window shell (floating glass sidebar, opaque white content, player along the bottom, artwork slot bottom left), the theme rule that each theme owns its screens, server-authored wording on taste and insight cards, evidence on every graph node, honest off and empty lens states.

Problems found in the code:

| Problem | Where | Rule broken |
|---|---|---|
| Accent `#FA2D48` is 3.79:1 on white, as text and under white button labels | `CU.accent`, every `CapsuleButtonStyle(primary:)`, eyebrows, selected sidebar row | Text contrast 4.5:1 |
| The accent is also the error colour and the "bad connection" dot | `CupertinoHome` failed phase, `CupertinoSettings` message, `CupertinoArtworkSlot` | Red means danger; errors need words and must not look like the main action |
| Every sidebar icon is accent; several filled primary buttons per view (each shelf tile has a red Get) | `CupertinoSidebar.row`, Home tiles, Gap Radar tiles, Insights cards | One accent, one primary action per view |
| Off-scale sizes and gaps: 13.5, 12.5, 10, 14, 18, 22, 26, 28 | throughout | Spacing scale 4, 8, 16, 24, 32 |
| Home is two cover shelves. It uses none of Server V2 | `CupertinoHome` | Dashboard: lead with the number that matters |
| Settings uses pairs of On and Off capsules instead of switches, and placeholders as the only label | `CupertinoSettings` | Labels stay visible |
| Service state is one line, shown only when nothing plays | `CupertinoArtworkSlot` | State must be honest and findable |
| Connections: nodes shrink to 30 pt with no label, controls are stacked, evidence is raw codes (`musicbrainz · credit · exact`), no list alternative | `GraphExplorerView` | Readability, accessibility |
| History heatmap levels are opacity steps with a hover-only tooltip and no key | `CupertinoHistory.heat` | Hover is not a control |
| Secondary text `#6E6E73` on the `#ECECF0` fill is 4.30:1 | small buttons, segmented controls | Contrast |

### 1.2 Android

Keep: the per-theme layouts (`Layout.Standard`, `TapeDeck`, `SheetStack`), 48dp targets, status as icon plus words, the Undo window before a dismissal is sent, offline as a banner, per-section loading on Home, server order on lists.

Problems found in the code:

| Problem | Where |
|---|---|
| Discover and Library are reached from a button group at the **bottom of the Home scroll** (`PageButtons`). The island holds Search, Home and the player only | `HomeScreen.kt`, `NavIsland.kt` |
| The three layouts disagree on destinations: island has 3, Tape bar has Search, Home, Library, Settings, Sheet group has Home, Search, Library, Player | `TapeDeck.kt`, `SheetStack.kt` |
| Home is seven shelves of covers in a fixed order. Taste, insights and acquisitions are elsewhere or absent | `HomeScreen.kt` |
| No animation is used anywhere outside the play meter | whole `ui` package |
| Day · Sand accent `#C04A1A` is 4.00:1 as text on the page | `Palettes.Sand` |
| `bodySmall` is 12/16, a 1.33 line height | `Theme.kt` |
| Peace Sans at −0.085em closes the gap between words in any heading longer than two words | `FontPairs.Discair` |
| Destructive Dismiss and Sign out use centred dialogs | `DownloadsScreen.kt`, `DiscairApp.kt` |
| No layout for wide screens beyond a 480dp form cap | `DiscairApp.kt` |

## 2. Philosophy

1. **Answer the collector's two questions first.** "What do I have?" and "What should I add next?" The dashboards lead with the library number and one pick. Operations sit last unless something is wrong, when they move to the top as a notice.
2. **The server's words are the content.** Taste headlines, insight titles and reasons are shown as sent. The client draws evidence under them and never composes a claim.
3. **One accent, one job.** The accent marks the main action, the selection and the one highlighted chart series. Status has its own four colours and always an icon and a word.
4. **Every number has a period and a change. Every chart has a reason.** A chart is added only where a number alone cannot say it.
5. **Missing is not zero.** Off, not loaded, not enough data, stale and failed are five different states with five different sentences.
6. **Native before novel.** macOS gets a sidebar, toolbar, popovers, switches, keyboard control. Android gets bottom sheets, a thumb-zone primary action, predictive back and motion. Neither copies the other.

What was challenged from the contract's "Home dashboard rethink":

| Contract idea | Decision | Why |
|---|---|---|
| A. Triage deck as the whole Home | Kept as **Today's pick**, one panel, same keys | Good for "what next", but as the whole page it hides the library |
| C. Almanac with a templated briefing line | Replaced by the server's **Anniversaries lens** and taste headline | The client must not write prose; "on this day in past years" needs history no route returns |
| D. Dust that grows on sleeves | Replaced by **Shelf life**: a histogram and the four longest-unplayed covers | The count and the albums are the value; a texture is decoration |
| G. Mailroom scene with parcels | Replaced by **Arrivals**: a list with a four-step tracker | A scene hides state; a tracker states it |
| J. Pick up from phone | Kept as a notice, hidden until the dependency is checked (section 9, D5) | Unverified today |

## 3. Shared rules for both platforms

- Spacing: 4, 8, 16, 24, 32. Section breaks use 32. One exception per platform is named where it occurs.
- Nested radius = outer radius − padding, never below 0.
- Status vocabulary: `Connected`, `Loaded`, `Done`, `Paused`, `Not set up`, `Not loaded`, `Unknown`, `Not updating`, `<reason> rejected`, `No answer`. Icons: check-circle (success), triangle (warning), x-circle (danger), info-circle (info), minus (unknown or off).
- Acquisition tracker: four segments named Found, Downloading, Importing, In library. Done segments are text colour, the current one is the accent, a failed one is danger with the server's reason in words beside it.
- Numbers: tabular figures, thousands separators, right-aligned in columns. Shares as whole percentages.
- Dates: "12 July 2026" in full, "9 November, 14:02" for events, relative ("2 hours ago") only for under a day.

## 4. macOS Cupertino design system

Light only. The theme fixes its colour scheme (`CupertinoTheme.colorScheme`), so no dark values are defined; a dark Cupertino would be a separate owner decision.

### 4.1 Colour

| Token | HEX | Use | Contrast |
|---|---|---|---|
| `bg.content` | `#FFFFFF` | Content ground | |
| `bg.panel` | `#F5F5F7` | Grouped panels, inspector | |
| `bg.fill` | `#ECECF0` | Neutral buttons and tracks on white | |
| `bg.fill.onPanel` | `#E6E6EB` | Neutral buttons and tracks on a panel | |
| `glass` | `rgba(246,246,249,0.74)` over blur | Sidebar, toolbar buttons only | unchanged |
| `text` | `#1D1D1F` | Primary text | 16.8:1 on white |
| `text.secondary` | `#636368` | Secondary text (was `#6E6E73`) | 5.9 white, 5.5 panel, 5.1 fill |
| `text.tertiary` | `#8E8E93` | Disabled and decorative only | 3.3, never essential text |
| `separator` | `#E5E5EA` | Hairlines, gridlines | |
| `separator.strong` | `#D1D1D6` | Field and outline-button borders | |
| `accent` | `#D61F4A` | Main action, selection, highlighted series (was `#FA2D48`) | 5.06 with white, 4.64 on panel |
| `accent.strong` | `#C8163F` | Pressed; accent text on the tint | 4.91 on tint |
| `accent.tint` | `#FCE8EC` | Selected row ground | |
| `success` / tint | `#187A48` / `#E6F4EC` | | 4.9 on panel |
| `warning` / tint | `#8A5200` / `#FFF4DC` | | 5.9 on tint |
| `danger` / tint | `#B3261E` / `#FBEAE8` | Errors, destructive labels | 5.6 on tint |
| `info` / tint | `#0B5CAD` / `#E8F1FB` | Not loaded, paused | 5.9 on tint |
| `chart.1` | `#D61F4A` | The one highlighted series | |
| `chart.2` | `#8E8E93` | Comparison line, baseline dot | 3.3 on white (graphic) |
| `chart.3` | `#C7C7CC` | Context bars | |
| `chart.ghost` | `#ECECF0` | Tracks, empty cells | |
| `chart.grid` / `chart.base` | `#E5E5EA` / `#C7C7CC` | Gridlines / zero baseline | |
| Heat steps | `#ECECF0`, `#F6C5D0`, `#EE8FA5`, `#E2537A`, `#D61F4A` | History heatmap | |

The accent stays a red-pink because it is the theme's identity and the app icon's colour. To keep "red means danger" true, danger is a different hue (brick, 4°) and is **never** shown without its icon and a sentence, and the accent is never used for an error.

### 4.2 Typography

SF Pro through the system font (`.system`), Display cut above 20 pt automatically. Tabular figures (`.monospacedDigit()`) on every number. No second typeface.

| Role | Size/line | Weight | Tracking | Use |
|---|---|---|---|---|
| `largeTitle` | 34/40 | Bold | −0.4 | Page title |
| `heroMetric` | 44/48 | Bold | −0.8 | The one lead number |
| `title1` | 24/32 | Bold | −0.3 | Server headline, pick title |
| `title2` | 20/24 | Bold | −0.2 | Panel title |
| `metric` | 24/32 | Semibold | −0.3 | Secondary numbers |
| `title3` | 17/24 | Semibold | −0.1 | Card and inspector title |
| `headline` | 13/20 | Semibold | 0 | Row title |
| `body` | 13/20 | Regular | 0 | Text, at most 62 characters wide |
| `callout` | 12/18 | Regular | 0 | Supporting line |
| `caption` | 11/16 | Regular | 0 | Chart labels, footnotes |
| `eyebrow` | 11/16 | Bold, caps | +0.06em | Short labels only |

The sizes 13.5 and 12.5 are removed.

### 4.3 Layout and components

- **Shell: unchanged geometry** (sidebar 216 wide inset 10, content from 236, toolbar at top 12, player 92 high, artwork slot 216). Changing it would ripple through every screen and the Zine-shared chrome. Content padding becomes 32 (was 28), top 66.
- Spacing exception: 12 for the horizontal padding of small buttons and the sidebar row radius (20 − 8).
- Radius: window 26, sidebar 20, panel 24 with 16 padding so covers and tiles inside are 8, popover and sheet 16, control 8, menu 12.
- Elevation: panels are tonal (`bg.panel`), never shadowed. Covers: `0 4 12 rgba(0,0,0,.16)`. Popovers, menus, sheets: system shadow. Glass on controls only.
- Sidebar: rows 32 high, radius 12, 13/20. Icons are `text.secondary`; only the selected row is accent text on `accent.tint`. Downloads keeps its accent count badge.
- Toolbar: a new **status button** left of Search (section 6.1), glass capsule 36 high.
- Buttons, capsules: large 40 (label 14 Semibold), regular 32 (13), small 24 (12). Primary: accent fill, white label, **one per view**. Secondary: `bg.fill`. Tertiary: 1 pt `separator.strong` outline, `text.secondary` label. Destructive: danger label on a neutral fill, never a red fill; the label says what is deleted.
- Segmented control: track `bg.fill` radius 8, padding 2; segment 24 high (28 in a control bar), selected white with a hairline shadow.
- Switch: system `Toggle(.switch)`, accent tint. Replaces every On and Off capsule pair.
- Field: label above (11 Semibold secondary), field 28 high (32 in a control bar), radius 8, 1 pt border; focus ring 3 pt accent at 28%; error is a danger border plus an icon and a sentence below.
- Notice: tinted strip radius 16, padding 8 by 16, icon, bold lead-in, sentence, one small button at the trailing edge.
- Popover: radius 16, padding 16. Alert: 320 wide, padding 24, the safe choice is the default button.
- Icons: SF Symbols, regular weight, 16 pt in rows and 12 in small buttons. Outline symbols; filled only for play and pause.
- Key caps: 24 high, radius 8, white with a 1 pt border.

Mockup: [`components--tokens-and-controls.png`](design/redesign/macos/cupertino/components--tokens-and-controls.png).

### 4.4 Graph rules

Mockup and specimen of every type and state: [`charts--specimens.png`](design/redesign/macos/cupertino/charts--specimens.png). Build with Swift Charts.

| Aspect | Rule |
|---|---|
| Title and subtitle | Title `title3` or `title2`, sentence case, says what is measured. Subtitle `callout` secondary: unit, source, exact period |
| Value axis | Labels only: 11 pt tabular secondary on the trailing side. No axis line, no tick marks |
| Gridlines | Horizontal only, 1 pt `chart.grid`, at most 4. Zero baseline `chart.base` |
| Time axis | 5 to 7 labels, 11 pt; first leading-aligned, last trailing-aligned |
| Zero | Bars and columns always start at zero. A line may start above zero and the subtitle then names the range |
| Colour | One accent mark. Everything else `chart.2` or `chart.3`. Never red and green for up and down: a share that rose is accent, one that fell is ink, each with an arrow |
| Comparison | The period before is a 1.5 pt dashed `chart.2` line, or a 2 pt ink tick across a column. Never a second hue |
| Legend | Only when two series exist. 11 pt, under the plot, leading-aligned |
| Annotation | At most 2. 11 pt secondary, 1 pt leader, hollow 3 pt marker |
| Selection | Click, drag or ← → (`chartXSelection`). 1 pt rule and a 5 pt accent dot with a white ring. Never hover-only |
| Tooltip | White, radius 8, popover shadow, padding 8. Value in 13 Semibold tabular, then the date in 11 secondary |
| Range control | Segmented 3M, 1Y, 5Y, All in the panel header. The subtitle restates the dates |
| Parts of a whole | More than 3 parts: sorted horizontal bars, 10 pt on a ghost track. No pies |
| Loading | A skeleton in the plot's footprint. No spinner, no shift |
| Not enough data | A dotted ghost line and one sentence naming the threshold |
| Not available | A sentence naming the missing source and a button to fix it |
| Stale or failed | Keep the last good chart at 50%, a warning notice with its date |
| Accessibility | `accessibilityChartDescriptor` on every chart; a summary sentence as the label; values reachable by keyboard; nothing depends on colour alone |
| Motion | Marks draw in over 300 ms ease-out; none when Reduce Motion is on |

## 5. macOS screens

Every mockup is in [`docs/design/redesign/macos/cupertino/`](design/redesign/macos/cupertino/).

### 5.1 Home

Mockups: `home--default-full`, `home--default`, `home--loading`, `home--first-run`, `home--degraded`, `home--librarian-unreachable`, `home--handoff`.

Content is 980 wide at the 1280 window. Rows are a 2:1 split with a 16 gap, except the taste and lens row (1:1). When the queue inspector is open or the content is under 860 wide, each row stacks into one column in reading order.

| # | Module | Content | Data | Available |
|---|---|---|---|---|
| 0 | Notice slot | At most one: Librarian unreachable, a failed job, or phone handoff | session, job status routes | yes, handoff D5 |
| 1 | Briefing band | Hero: albums owned, with added in the last 30 days against the 30 before. Then Listens last 7 days against the 7 before; Never played with change since the first of last month; Waiting (picks, unplayed arrivals) | Navidrome album list (`created`, `playCount`, `played`); listens need D2; picks and acquisitions | hero, never played, waiting: yes. Listens: D2 |
| 2 | Today's pick | Cover 232, title, artist, year, the server's reason, suggested track, Get (the view's one primary), Save, Not for me, "1 of 7". Keys: → Get, ↓ Save, ← Not for me, Space plays | `GET /api/dashboard-picks`, existing actions, `LinerNoteCard` text | yes |
| 3 | Arrivals | Active Gets with the tracker, arrived-and-unplayed albums with Play, radio plays with Get. At most 4 rows, then All downloads | acquisition model, `GET /api/radio/plays` | yes |
| 4 | Collection over time | Line of total albums, or columns of albums added per month. Range 3M, 1Y, 5Y, All | Navidrome `created` | yes |
| 5 | Own and play, by decade | Paired bars: share of albums, share of listens in the recent window. Selected row in bold | Navidrome years; taste `windows.recent.dimensions.era` | yes when taste is saved |
| 6 | Your taste | Server `headline.text`, a dumbbell per listed shift, listen counts | `GET /api/insights/taste` | yes |
| 7 | From the lenses | Top card of up to 3 enabled lenses, "n of 5 on" | `GET /api/insights` | yes |
| 8 | Shelf life | Histogram of albums by time since last play (this month, 1–6 mo, 6–12 mo, 1–2 years, 2+ years, never), the never bin in accent; four longest-unplayed covers; "Play something unplayed" | Navidrome | yes |
| 9 | Server activity | Insight lenses, taste profile, artist popularity, MusicBrainz data: state word and one line each | `updatedText`, taste and popularity status routes, capabilities | yes; the lens "next run" time is served by D3 (S2) |
| 10 | Recently added | Six covers | existing | yes |

Rules:
- The first-row stats are buttons: Library, History, a "never played" smart playlist, Discover.
- A module whose source is off or missing shows its own sentence (see `home--first-run`); it is not removed, so the page does not reshuffle. Exception: the notice slot and Arrivals collapse when empty after first use.
- With Librarian unreachable, the Navidrome modules (1 hero and never played, 8, 10) stay and the rest become one sentence. The collection chart (4) is hidden, as `home--librarian-unreachable` draws it (F5, built): the mockup is the spec where this paragraph and the mockup differ.
- Shifts are drawn only from `shifts[]`. A `null` headline shows the progress state with "n of 100 listens".
- The "then and now" month comparison is not drawn: it needs D1.

### 5.2 Connections (the credit graph)

Mockups: `connections--graph`, `connections--graph-selected`, `connections--list`, `connections--empty`, `connections--not-loaded`, `connections--truncated-error`.

- **Control bar**, one row, each control with its label above: Back (names where it returns to), Start from (the artist field with a photo), Reach (1, 2, 3 steps; "depth" is renamed), Credits only (switch), and View (Graph or List) at the trailing edge. The Discs toggle moves to the View menu.
- **Graph.** The start artist is 72 pt in the centre. Step 1 sits on a ring at 188 pt, step 2 on a dotted ring at 292 pt beside its parent. Nodes are **grouped into sectors by kind** (people, albums, place, label) with an eyebrow naming each sector. Step 1 nodes are 48 pt and always labelled; step 2 nodes are 32 pt and labelled. When a ring would need nodes under 40 pt, the page shows "Too many to draw" and switches to List instead of shrinking.
- Encodings, unchanged in meaning: people are circles, albums rounded squares, others an icon on white. In the library: colour and a solid 2 pt ink border. Not in the library: grey and a dashed border. Credit: solid line. Link that is not a credit: dashed line. The selected node has a 3 pt accent ring and its line is accent.
- **List view** (new): the same hops as a table grouped by relation, columns Name, Connection in words, Library, Steps. It is the keyboard and VoiceOver path and the fallback for dense graphs. Sorting and Load more use the same cursor.
- **Also on, in your library (F10 decision, 2026-11-12).** Kept on the client. It lists the owned albums that sit next to the selected node in the walk already read (its parent or its children), and the inspector says so under the heading. The server sends no total, so the footer and the summary line count what has been read ("so far" while the walk can go on, "of n+" when it was truncated). No server field is added.
- **Inspector**, 300 wide. Nothing selected: counts by kind and the data coverage line. Selected: name, kind, steps away; Re-centre here (primary), Open artist or Open album; "How they connect", one white card per piece of evidence: the relation, what it is on, a Credit or Link pill, then "Source: MusicBrainz · exact match" in words; "Also on, in your library" covers.
- States: no start chosen (six owned artists to start from); not loaded for this artist (info notice, Request update, then a Requested confirmation); truncated walk (warning that names the server's 200-row, 2-second limit and offers Credits only or List); failed load (danger notice, keeps what is drawn, Try again).
- Data: all existing (`connections`, `update-store`, capabilities). The words for relation and match quality are a client lookup table from the codes the body already carries.

### 5.3 Other pages

| Page | Change | Mockup |
|---|---|---|
| Insights | Lens pills move under the title with a check or "off". Taste becomes four panels: lately against always (dumbbell), top values (ranked bars with window and dimension controls), when you listen (columns), morning against night (stated, or its low-sample progress). Lens cards: one neutral action row; no filled primary | `insights--default` |
| History | Heatmap with five stepped colours, a Fewer to More key, month and weekday labels, click or arrow-key selection with a tooltip. Day lists unchanged in content | `history--default` |
| Downloads | Rows with the four-step tracker, state in words, filter (All, Active, Needs you, Arrived). A failed row carries the only primary, Try again | `downloads--default` |
| Gap Radar | Tokens only. Get on a tile is neutral; "Get n missing" is the card's primary; completeness bar in ink | `gap-radar--default` |
| Settings | Tabs: Services, Playback, Music folder, Profiles. Playback rows use switches and segmented controls | `settings--playback` |
| Library, Album, Artist, Now Playing, Queue, Equalizer, Discover, Smart Playlists, Atlas, Timeline | Token migration only (section 4): colours, type sizes, gaps, button hierarchy. No layout change, no mockup | none |

## 6. macOS Services (connected services, health and setup)

Mockups: `settings-services--healthy`, `settings-services--degraded`, `settings-services--librarian-unreachable`, `settings-services--edit-sheet`, and the popover in `home--degraded`.

### 6.1 Toolbar status button

Always visible, left of Search. Icon plus words: "All working", "1 needs attention", "2 not set up", "Librarian unreachable", "Checking…". It opens a popover that lists the services with their state, one sentence on what is affected, and two buttons: the fix (primary) and Open Services. The bottom-left connection line stays for the idle player.

### 6.2 Settings, Services tab

Top to bottom:

1. **Summary.** A 32 pt status icon, a `title2` sentence ("Everything is working", "One service needs attention", "Can't reach Librarian"), one line saying what is and is not affected and when it was checked, and Check again.
2. **How Discair is connected.** A diagram of real calls: This Mac → Librarian and This Mac → Navidrome; Librarian → Navidrome, slskd, Last.fm, ListenBrainz, Discogs, MusicBrainz data. A working line is solid grey, a failing one is dashed danger with a danger border on the node, a not-set-up or unknown one is dashed light grey. Each node has its status icon.
3. **Service list** in groups: Core (Librarian, Navidrome), Getting music (slskd), Listening history (Last.fm, ListenBrainz), Knowledge (MusicBrainz data, Sonic analysis, Discogs), On this Mac (Music folder over SMB). Each row: icon, name, role in five words, **"powers" pills** naming the app features that depend on it, the state, a disclosure chevron.
4. **Expanded row**: two columns that keep operation apart from configuration. **Status now**: answer, since, last good read, checked. **Setup**: address or username, where the secret is kept, what uses it. Then the actions (Edit, Test again, Disconnect). An error adds a danger notice above with the cause and the fix in words.
5. **Edit sheet**: labelled fields, a Test button that reports in a notice, Cancel and Save.

Rules:
- When Librarian is unreachable, everything it would report is **Unknown** (grey minus), not failed. Navidrome and the SMB folder are checked directly and keep their own state.
- A service that is not set up and optional (Discogs, SMB) shows a neutral Set up button and never counts as a problem.
- Stale data is said where it is shown: "as of 9 November" on the Home stat and the taste panel.

Data: `GET /api/settings/{navidrome,slskd,lastfm,listenbrainz,discogs}` and their `POST …/test`, `GET /api/health`, `GET /api/capabilities`, `GET /api/auth/status`, the app's own reachability. Only the ListenBrainz pair is called by the Mac app today; the rest are existing server routes that need client methods. "Since" and "last good read" times: taste has them (`refresh/status`); for the others the client records the time of its own last successful check.

## 7. Android design system

### 7.1 Navigation and structure

- **Four destinations in every layout: Home, Discover, Library, Search**, each an icon with a visible label. Settings and Downloads (with its count badge) are top-bar actions. The Home `PageButtons` group is removed.
- The player is no longer a navigation cell. A **mini player** (56dp, cover, title, artist, play or pause) sits above the navigation when a song is queued and opens Now Playing.
- Each layout draws the same four in its own form: Standard as a floating island (64dp high, 16dp margins, radius 32, 48dp cells, the current cell filled with the accent); Tape as its ruled full-width bar with four cells; Sheet as its joined group of four segments.
- Stack pages (Album, Artist, Genre, Stats, Server, Settings, Downloads) hide the navigation and show a top bar with Back.
- New screens: **Library stats** (from the dashboard) and **Server** (from Settings and from the dashboard's last row).
- Width classes: under 600dp as drawn. 600 to 839dp: a navigation rail (80dp) replaces the bottom navigation and grids gain a column. 840dp and over: rail plus two panes, primary two thirds and secondary one third (`dashboard-tablet`). Text blocks are capped at 600dp.

### 7.2 Shared component rules

- Type roles use the `FontPair` slots, so every font pair keeps working. With the default Discair pair:

| Role | Family | Size/line | Notes |
|---|---|---|---|
| `displayMetric` (new) | Big Shoulders Display 800 | 64/64 | The dashboard number |
| `numeral` | Big Shoulders Display 700 | 28/32 | Stat values |
| `headlineLarge` / `headlineMedium` / `titleLarge` | Peace Sans 400 | 32/34, 28/32, 22/24 | −0.085em tracking kept, **+0.16em word spacing added** |
| `headlineSentence` (new) | Open Sans 600 | 20/28 | Server-authored sentences: the display face is not used for sentences |
| `titleMedium` | Open Sans 600 | 16/24 | |
| `bodyLarge` / `bodyMedium` | Open Sans 400 | 16/24, 14/20 | |
| `bodySmall` | Open Sans 400 | **12/18** (was 12/16) | |
| `labelMedium` / `labelSmall` | JetBrains Mono 500 / 400 | 12/16, 11/16 | Eyebrows in caps at +0.08em, chart labels |

- Touch targets 48dp. A 32dp-tall chip or small button gets its touch area padded to 48dp.
- Buttons: 48dp high, radius 24, label 14 Semibold. Filled (accent) once per screen and at the bottom of its card. Tonal (`raised`), outlined (`edgeStrong`), and text (underlined, since it acts as a link).
- Cards: 16dp padding. List rows at least 64dp with a hairline between.
- Bottom sheets replace centred dialogs, including the Dismiss and Sign out confirmations: grab handle, title, sentence, the safe action outlined, the destructive action as a danger-labelled button below it.
- Snackbar with Undo for dismissals, 6 seconds, above the mini player.
- Charts: the macOS rules of section 4.4 with touch: drag to select, the selected value is written **above the plot** (a tooltip would sit under the finger), labels in the mono face, minimum plot height 152dp.

### 7.3 The four themes

New `Palette` roles for all palettes: `info`, the four `…Dim` containers, and `chart1`, `chart2`, `chart3`, `chartGhost`, `chartGrid`, `chartBase`. Existing values are unchanged except where marked.

| Role | Day · Sand | Night | Tape · Lime | Sheet · Violet-orange |
|---|---|---|---|---|
| `ink` (page) | `#EFE6D3` | `#141211` | `#F1EEE3` | `#15131F` |
| `rail` | `#E6DCC8` | `#0F0E0D` | `#F1EEE3` | `#15131F` |
| `surface` | `#F8F1E1` | `#1C1A18` | `#FFFDF6` | `#221F31` |
| `raised` | `#E3D8C0` | `#252220` | `#F1ECDC` | `#2E2A43` |
| `edge` / `edgeStrong` | `#CFC2A6` / `#857758` | `#34302C` / `#787168` | `#111111` | `#F4F1FF` |
| `text` | `#26201A` | `#F4EFE6` | `#111111` | `#F4F1FF` |
| `textMuted` | `#62563F` | `#B4AC9F` | `#4F4D44` | `#A8A2C4` |
| `accent` | **`#AD4016`** (was `#C04A1A`) | `#F5D33F` | `#C6F432` | `#FF6A3D` |
| `onAccent` | `#FFF8EE` | `#141211` | `#111111` | `#15131F` |
| `accentDim` | `#EFC9B0` | `#554B26` | `#E9F8B4` | `#2E2A43` |
| `ok` / dim | `#25693A` / `#D5E5CF` | `#86D39B` / `#1F3326` | `#1B6B33` / `#D3EBD9` | `#86D39B` / `#223A33` |
| `caution` / dim | `#7F4A00` / `#F1DDB4` | `#F0A640` / `#3D2E14` | `#7F4A00` / `#FBE6BF` | `#F0A640` / `#43351F` |
| `danger` / dim | `#A8300E` / `#F2CFC2` | `#FF7B62` / `#40211A` | `#B3261E` / `#F7D4D1` | `#FF8A80` / `#472A33` |
| `info` / dim (new) | `#1F5A8A` / `#CFDDE8` | `#8FB8E8` / `#1D2C3D` | `#1D4FB8` / `#D3DFFA` | `#9DB8FF` / `#2A3152` |
| `chart1` | `#AD4016` | `#F5D33F` | `#C6F432` with outline | `#FF6A3D` |
| `chart2` | `#8C7B57` | `#7A736A` | `#7C7A6E` | `#7A7499` |
| `chart3` | `#C9BB9C` | `#4A4540` | `#FFFDF6` with outline | `#35E0D0` |
| `chartGhost` | `#E3D8C0` | `#252220` | `#F1ECDC` | `#2E2A43` |
| `chartGrid` / `chartBase` | `#CFC2A6` / `#857758` | `#34302C` / `#787168` | `#111111` | `#3A3552` / `#F4F1FF` |
| Text contrast, muted on surface | 6.4 | 7.7 | 8.3 | 6.6 |
| Accent as text on page | 4.8 | 12.7 | not allowed (1.1) | 6.5 |

Identity rules. These three columns after Day have **no mockup**:

| | Day | Night | Tape | Sheet |
|---|---|---|---|---|
| Character | Warm paper, quiet | The original warm dark | A cassette deck: ruled, mechanical | Stacked sheets: soft corners, hard coloured shadows |
| Card | Radius 20, 1dp `edge`, no shadow; covers radius 4 | Same shape; elevation by tone (`surface` then `raised`), no shadow | Radius 2, 2dp ink outline, 5dp hard ink shadow; lists are ruled rows, not cards | Radius 14, 2dp outline, 4dp hard accent shadow |
| Navigation | Island in `text` colour, accent cell | Island in `raised`, accent cell with dark label | Ruled bar, current cell filled lime with ink label | Joined group, current segment filled orange |
| Section heading | Title face | Title face with the short red rule kept | Mono caps eyebrow over a 2dp rule | Title face on a tilted tag |
| Bars and columns | Rounded 3dp tops, accent and `chart3` | Same | Square, 2dp ink outline, highlight filled lime, others `surface`; columns drawn as stacked meter segments | Square with 2dp outline; highlight orange, context cyan `chart3` |
| Lines | 2dp accent, 8% area | 2dp accent, no area | 2dp ink stepped line (no curve), lime area | 3dp accent, no area |
| Tracker | 4dp rounded segments | Same | Square segments with outline | Square segments |
| Accent as text | Yes | Yes | **Never**; use ink, the fill carries the accent | Yes |
| Pressed state | Tone shift | Tone shift | Moves 5dp onto its shadow | Moves 4dp onto its shadow |

### 7.4 Motion (owner request, 2026-11-11)

Tokens, in a new `Motion` object:

| Token | Value | Use |
|---|---|---|
| `fast` | 100 ms | Press feedback, icon swaps |
| `base` | 200 ms | Fades, chip and tab selection |
| `enter` | 300 ms | Content entering, screen transitions |
| `emphasis` | 400 ms | Charts drawing, the hero number |
| `sheet` | 350 ms | Bottom sheets |
| `easeEnter` | cubic-bezier(0.05, 0.7, 0.1, 1) | Anything arriving |
| `easeExit` | cubic-bezier(0.3, 0, 0.8, 0.15) | Anything leaving, 2/3 of the enter time |
| `easeStandard` | cubic-bezier(0.2, 0, 0, 1) | Moves within the screen |
| `spring` | damping 0.8, stiffness 380 | Gestures: sheets, pager, island indicator |

| Where | Motion |
|---|---|
| Tab change (Home, Discover, Library, Search) | Fade through: old content fades out 100 ms, new fades in 200 ms with a 16dp rise. The island's accent cell slides to the new tab with `spring` |
| Push to a stack page | Shared axis X: 30dp slide plus fade, `enter`. Predictive back follows the finger |
| Cover to Album page | Shared element: the cover grows into the album header, `enter`, `easeStandard`. Falls back to shared axis when the cover is off screen |
| Screen load | Skeleton shimmer (1200 ms loop), then content cross-fades in `base`. Cards rise 16dp and fade, staggered 50 ms, first 4 only |
| Hero number | Counts up from the cached value over `emphasis`; no count on first launch |
| Charts | Columns and bars grow from the baseline, `emphasis`, staggered 30 ms; lines draw left to right; the selected value cross-fades |
| Lists | `animateItem()` for insert, remove and reorder; a dismissed row collapses in `base` |
| Get button | Cloud to spinner to check, cross-fade and scale 0.8 to 1, `base`. Failure shakes 4dp twice |
| Bottom sheet, scrim | Sheet rises with `spring`; scrim fades `base` |
| Mini player | Slides up 72dp with `enter` when a queue starts; the cover cross-fades on track change |
| Tracker | The current segment's fill animates with progress; a finished segment flips to done in `base` |
| Pull to refresh | Standard indicator in the accent |

Per theme: Day and Night as above. **Tape** is mechanical: durations at 60% of the table, linear or stepped easing, no overshoot, chart columns fill in meter steps. **Sheet** is springy: `spring` damping 0.7 on entering cards and sheets, and pressed surfaces travel onto their hard shadow.

Reduced motion: when the system animator scale is 0 (the check already in `TapeDeck.kt`), every transition becomes a 100 ms fade or nothing; no count-up, no stagger, no shimmer.

Live demo: open [`android/day/motion.html`](design/redesign/android/day/motion.html) in a browser and reload to replay. It shows the enter stagger, chart growth and the sheet; the PNG is a still.

## 8. Android screens

Mockups are in [`docs/design/redesign/android/day/`](design/redesign/android/day/), Day · Sand, normal state only.

### 8.1 Dashboard (`dashboard`, `dashboard-tablet`)

One column, in this order. Each module loads on its own, as today.

| # | Module | Content | Data |
|---|---|---|---|
| 1 | Hero | "Your library", the album count in `displayMetric`, added in the last 30 days against the 30 before | `GET /api/library/albums` total and added dates (confirm the field, D4) |
| 2 | Stat row | Side-scrolling cards: Listens 7 days (D2), Never played, Waiting. Each opens Stats or its list | as macOS |
| 3 | Today's pick | The existing pager, as a card: tag, "1 / 7", cover 112dp, title, artist and year, **Get album filled and full width at the bottom**, Save, overflow (Not this album, Never suggest artist). The reason text stays hidden on Android (owner decision in `android/DESIGN.md`) | `dashboard-picks` |
| 4 | Arrivals | Up to 2 rows with the tracker or Play; hidden when empty | `AcquisitionHub` |
| 5 | Your taste | Server headline in `headlineSentence`, dumbbell per shift, Details opens the taste sheet | taste |
| 6 | Insight | One card from an enabled lens, rotating daily; Play or Get, Why? | insights |
| 7 | Library in numbers | 12-month line, Open stats | library |
| 8 | Recently added, Recently played | Cover shelves, 112dp | existing shelves |
| 9 | Genres | Chips | existing |
| 10 | Radio, Server | Two rows: last heard station; "Server: all quiet" with the last lens refresh, opening Server | existing; job status routes |

Dropped from Home: Most played and New releases shelves (both live in Discover), and the page buttons.

A failing service puts one warning banner under the top bar, as the offline banner does today.

### 8.2 Other screens

| Screen | Change | Mockup |
|---|---|---|
| Library stats (new) | Range chips. Collection over time with the selected value above the plot; Own and play by decade; Shelf life with Play something unplayed; When you listen | `stats` |
| Discover | List names as chips in one scrolling row; two-column cards with Get on the cover; Insights tab with the taste card and lens cards | `discover` frames 1, 2 |
| Taste sheet | Bottom sheet: window segmented control, dimension chips, ranked bars with one accent bar, the filled action at the bottom | `discover` frame 3 |
| Library | Segmented Artists and Albums, count and order line, Sort; artist rows 64dp; album grid two columns | `library-search` frames 1, 2 |
| Search | Field 56dp with a focus outline, grouped results, owned state in words, Get on missing albums | `library-search` frame 3 |
| Downloads | One card per record: cover, tracker with step names, state in words, one action row | `downloads-settings-server` frame 1 |
| Settings | Grouped rows; Server and services first with its state; switches; Sign out as a danger-labelled outlined button that opens a sheet | frame 2 |
| Server (new) | Summary card, services with state words, server activity. Read only on the phone: editing addresses stays in the existing setup flow | frame 3 |
| Album, Artist, Genre, Now Playing, Radio, Equalizer, Appearance | New roles, type fixes and motion only | none |

## 9. Dependencies: what the server or clients cannot do today

| Id | Need | Today | Proposal | Blocks |
|---|---|---|---|---|
| D1 | Month-by-month "then and now" | `intelligence/taste/monthly.py` builds snapshots; nothing stores or serves them | `GET /api/insights/snapshots` contract proposal | A month comparison chart (not drawn) |
| D2 | Listens per day or week (macOS client built in PR #982; server built in PR #986 as S1, field `listens_by_day` on the taste body, not yet checked live) | Was: the server returned no counts by date | Done: `listens_by_day` (last 84 days) on the taste body | "Listens last 7 days" stat and its comparison |
| D3 | When a lens refresh last ran and will next run (macOS client built in PR #982) | Done: `GET /api/insights/refresh/status` (PR #987, S2), shaped like the taste one; `retry_after` is an estimate from the loop cadence | "next in 4 hours" on Server activity |
| D4 | Album added dates on Android | **Checked 2026-11-12 (S3): present, no server change.** `GET /api/library/albums` returns `added` on every item, an ISO-8601 instant taken from Navidrome's album `created` (`discovery/search/index.py`, `query.py`). The recorded fixture `android/contract-fixtures/librarian/library_albums.json` carries it on all three items. The Android app already reads it (`LibraryAlbum.added`, `RecentlyAdded.kt`). It can be `null` when Navidrome gives no `created`; the client must treat null as unknown, not as old | None. Android hero count and growth chart (A6) can use it | Android hero change, growth chart |
| D5 | Phone handoff (macOS side built in PR #982 from Navidrome's `getPlayQueue`; the Android app must call `savePlayQueue`) | **Done: Android slice merged in PR [#995](https://github.com/abucalip/navi-librarian/pull/995), merge commit `2fa3433b`, 2026-11-12.** Before it, no Android source file called `savePlayQueue`; the queue lived only in the device file `player_queue.json`. Now `NavidromeQueueSaver` calls `rest/savePlayQueue` with the owner's login and client name `discair-android` (the Mac ignores a queue saved under its own name, `discair`). `PlayQueueSync` sends the newest queue only: the current song and up to 100 after it, with the position in ms. It is sent on pause, on song change, on any queue edit, and every 30 s while playing. Radio stations are never sent. Unit tests pass locally; the live Navidrome check is not yet run | Live check pending: confirm Navidrome accepts the save, then the Mac's handoff notice (`home--handoff`) shows a phone's queue | Handoff notice (`home--handoff`) |
| D6 | Library health and unresolved items | Builders and fixtures exist; `GET /api/library-health` and `/api/unresolved` are not in the served routes | Serve them | Not designed here; a future "Health" row in Server activity |
| D7 | Per-service "since" time | Not returned by the settings test routes | Client keeps its own last-good time | none; client-side |
| D8 | Time-of-day counts and the morning-vs-night contrast (M10) | Already served: `context` in `GET /api/insights/taste` (`intelligence/taste/context.py`, `context_persistence.py`) carries `time_of_day` listen counts and the `contrast` with its state. The client did not read it | No server change. Client reads `context` (`TasteContext`, `TasteContrast`) | none; resolved by the client in M10 |
| D9 | "Arrived this week" on Downloads (M10) | Job `updated_at` is epoch seconds (`acquisition/state.py`) | No server change; the client counts imports changed in the last seven days | none; client-side |

Until a dependency lands, its module shows the "not available" state and the rest of the screen is built as drawn.

## 10. Mockup index

`docs/design/redesign/macos/cupertino/` (each name has `.html` and `.png`):

| Screen and state | File |
|---|---|
| Home, normal, whole page | `home--default-full` |
| Home, normal, first screen | `home--default` |
| Home, loading | `home--loading` |
| Home, first run, no history, lenses off | `home--first-run` |
| Home, one service failing, status popover open | `home--degraded` |
| Home, Librarian unreachable | `home--librarian-unreachable` |
| Home, phone handoff notice (D5) | `home--handoff` |
| Connections, graph | `connections--graph` |
| Connections, graph, node selected | `connections--graph-selected` |
| Connections, list view | `connections--list` |
| Connections, no start chosen | `connections--empty` |
| Connections, not loaded, update requested | `connections--not-loaded` |
| Connections, truncated walk and failed load | `connections--truncated-error` |
| Settings, Services, all working | `settings-services--healthy` |
| Settings, Services, one failing, row expanded | `settings-services--degraded` |
| Settings, Services, Librarian unreachable | `settings-services--librarian-unreachable` |
| Settings, Services, edit sheet | `settings-services--edit-sheet` |
| Settings, Playback | `settings--playback` |
| Insights | `insights--default` |
| History | `history--default` |
| Downloads | `downloads--default` |
| Gap Radar | `gap-radar--default` |
| Chart rules, every type and state | `charts--specimens` |
| Tokens, type, buttons, fields, notices, alert, menu | `components--tokens-and-controls` |

`docs/design/redesign/android/day/`:

| Screen | File |
|---|---|
| Dashboard, three scroll positions | `dashboard` |
| Dashboard at 840dp, rail and two panes | `dashboard-tablet` |
| Library stats, two scroll positions | `stats` |
| Discover, Insights tab, taste sheet | `discover` |
| Library artists, Library albums, Search | `library-search` |
| Downloads, Settings, Server | `downloads-settings-server` |
| Motion demo (animated HTML) | `motion` |

Not drawn: Android Night, Tape and Sheet; Android loading, empty and error states; the Android confirmation sheets and snackbar; macOS pages listed as token-only. The generator that wrote the files is in `docs/design/redesign/_src/`.

## 11. Implementation roadmap

Models: Sonnet or Haiku only. Each step is one PR from current `main`, following `DEVELOPMENT_WORKFLOW.md`: filtered tests only, no full suite, required CI on the PR head for Android, and macOS Swift tests locally with `macos/scripts/select-tests.sh`. "Visual check" means a screenshot of the built screen placed beside the named mockup; the owner approves the look.

Order: M1 → M2 → (M3, M4, M5, M6, M7, M8 and M9 done) → M10a (done) → M10b (done). S1 and S2 done. A1, A2, A3, A4, A5, A6, A7 and A8 done. → A8b → A9. The M and A tracks are independent. S1 to S3 are server proposals and can run at any time.

### macOS

| Step | Objective and instructions | Files | Depends on | Acceptance | Tests and visual check | Model, effort |
|---|---|---|---|---|---|---|
| ~~**M1** Tokens~~ **Merged** in PR #975, squash `f0aba3d6` (2026-11-11). Was: replace the `CU` values with section 4.1; add `textSecondary`, `separator`, `separatorStrong`, `accentStrong`, `accentTint`, the four semantic pairs and the chart colours. Add `CU.Font` roles from 4.2 and a `CU.Space` enum (4, 8, 16, 24, 32). Keep the old names as aliases so nothing else changes in this PR | `Themes/Cupertino/CupertinoTheme.swift` | none | No colour literal for these roles outside `CU`; a unit test asserts each text and accent pair in 4.1 reaches 4.5:1 | New `CupertinoTokensTests` (contrast). Visual: any screen still renders | Haiku, Medium |
| ~~**M2** Controls~~ **Merged** in PR #976, squash `e3e69220` (2026-11-11). Was: `CapsuleButtonStyle`: sizes 40, 32, 24, the four kinds, destructive label; fills switch to `fill.onPanel` inside a panel through an environment value. Add `CUSegmented`, `CUNotice`, `CUStatusLabel` (icon plus word), `CUField` (label above), `CUPanel` (radius 24, padding 16). Replace On and Off pairs with `Toggle` | `CupertinoHome.swift` (style), new `Themes/Cupertino/CupertinoKit.swift`, `CupertinoSettings.swift` | M1 | Matches `components--tokens-and-controls`; no view has two filled primaries | Snapshot-free unit tests of `CUStatusLabel` text for each state. Visual: components sheet | Sonnet, Medium |
| ~~**M3** Shell~~ **Merged** in PR #977, squash `e3e63b0c` (2026-11-11). Was: Sidebar rows per 4.3 (neutral icons, selected tint); errors use `danger` with an icon, not the accent; content padding 32 | `CupertinoTheme.swift` | M2 | Matches the sidebar in any mockup; accent no longer used for errors anywhere in `Themes/Cupertino` (grep) | Existing window tests. Visual: `home--default` shell | Haiku, Medium |
| ~~**M4** Charts~~ **Merged** in PR #978, squash `2480b3a2` (2026-11-11). Was: New `Chrome/CupertinoCharts.swift`: `CULineChart`, `CUColumnChart`, `CUPairedBars`, `CUDumbbell`, `CURankedBars`, `CUHeatmap`, `CUStageTracker`, each with loading, insufficient, unavailable and stale states and an `accessibilityChartDescriptor`, following 4.4. Geometry reference: the chart functions in `_src/mac_shell.py` | new file; `Package.swift` only if Swift Charts needs declaring | M1 | Every type and state in `charts--specimens` exists; keyboard selection works | Unit tests for scale and bin maths and the state chosen for each input. Visual: specimen sheet | Sonnet, High |
| ~~**M5** Home data~~ **Merged** in PR #979, squash `3bf66cb2` (2026-11-11). Was: New `Model/HomeDashboard.swift`, pure and tested: album count and 30-day change, never-played count and change, shelf-life bins, growth series by range, decade shares, arrivals rows, the notice to show. Inputs are existing models only | new model; `AppState.swift` (one property) | none | Each figure in 5.1 computed from fixtures; missing inputs yield the stated empty value, never zero | `HomeDashboardTests` covering empty library, no plays, no taste, Librarian down | Sonnet, High |
| ~~**M6** Services data~~ **Merged** in PR #980, squash `cf175239` (2026-11-11). Was: Client methods for the five settings routes, their tests and `/api/health`; `Model/ServicesModel.swift`: state per service, summary sentence, "powers" list, Unknown when Librarian is down, last-good times kept locally | `DiscairLibrarian/LibrarianClient.swift`, new model | none | Decodes recorded bodies; state table matches 6.2 for healthy, one failing, Librarian down | `ServicesModelTests`, decoder tests with fixtures | Sonnet, Medium |
| ~~**M7** Connections model~~ **Merged** in PR #981, squash `7e705614` (2026-11-11). Was: Sector assignment by kind, ring positions, the "too many to draw" threshold, relation and match-quality wording table, grouped rows for List | `Model/GraphExplorer.swift` | none | Layout is deterministic; every relation code has words or falls back to the code capitalised | `GraphExplorerTests` additions | Sonnet, Medium |
| ~~**M8** Home screen~~ **Merged** in PR #982, squash `f9bccff8` (2026-11-11). Was: Build 5.1 with M2, M4, M5: modules 0 to 10, keyboard on the pick (→ ↓ ← Space), stacking under 860 pt, all states | `CupertinoHome.swift` (rewrite), `Chrome/LinerNoteCard.swift` reuse | M2, M4, M5 | Matches the seven `home--*` mockups; one primary; VoiceOver reads each module heading and chart summary | Filtered UI tests for state selection. Visual: all seven | Sonnet, High |
| ~~**M9** Connections and Services screens~~ **Merged** in PR #983, squash `344252e3` (2026-11-11). Was: Connections per 5.2 (control bar, sectors, List, inspector, four states). Services tab, edit sheet, toolbar status button and popover per 6. The explorer is shared with Zine: pass the new layout through `GraphStyle` and leave Zine's look unchanged | `Chrome/GraphExplorerView.swift`, `CupertinoSettings.swift`, `CupertinoTheme.swift` (toolbar), new `CupertinoServices.swift` | M2, M6, M7 | Matches the six `connections--*` and four `settings-services--*` mockups and the popover; Zine screenshots unchanged | Existing graph tests plus new. Visual: all ten, plus Zine Connections before and after | Sonnet, High |
| ~~**M10a** Drawn pages~~ **Merged** in PR #984, squash `16cb3d9d` (2026-11-11). Was: Insights, History, Downloads, Gap Radar, Settings Playback per 5.3 (Playback is the Playback tab only; the other Settings tabs are not part of M10). Follow-up commit `62eb745b` on the same PR built the deviations: time-of-day columns and the morning-vs-night contrast from the server's `context` block (D8, no server change), four top-value dimensions, the weekly arrivals count (D9), the Clear confirmation, one neutral Get per Gap Radar card | `Cupertino{Insights,Taste,History,Downloads,GapRadar,Settings}.swift`, `DiscairLibrarian/Taste.swift`, `Model/TasteModel.swift`, `intelligence/api/fixture_set.py`, two context fixtures | M2, M4 | Matches the five mockups | `CupertinoPagesRenderTests` (PNGs), `TasteContextClientTests`, `TasteClientTests`, Cupertino filtered suites | Haiku, High |
| ~~**M10b** Token-only pages~~ **Merged** in PR #985, squash `c9a10549` (2026-11-11). Was: Library, Album, Artist, Now Playing, Queue, Equalizer, Discover, Smart Playlists, Atlas, Timeline: replace literals with roles, off-scale gaps with the scale, extra primaries with secondary. Also the Settings tabs other than Playback (Music folder, Profiles) and the Services tab keep their token pass here | the other `Cupertino*.swift` files | M10a | Grep finds no `13.5`, `12.5` or raw colour in `Themes/Cupertino`; one filled primary per view | Existing tests for those screens; a pass over each token-only page | Haiku, High |

### macOS follow-ups (audit of M1 to M10, 2026-11-12)

A read of the merged code and `PROJECT_LOG.md` found no missing server route: every route the Mac client calls is served, including `GET /api/insights`, `listens_by_day` (D2) and `GET /api/insights/refresh/status` (D3). What follows are gaps and deviations left by M5 to M10, each a small slice from current `main`, in the order of the table. Nothing here has been built. The gap list is from reading the code; the live-data and approval checks at the end have not been run.

| Id | From | Fix | Files | Acceptance | Model, effort |
|---|---|---|---|---|---|
| ~~**F1**~~ **Built in the F1-F4 PR.** Live check 2026-11-12: Navidrome omits `playCount` and `played` on unplayed albums only (186 of 500 albums carried both). "Never played" now reads "Not counted yet" when no album carries either field. Was: | M5 | Verify against live Navidrome whether `playCount` is omitted for unplayed albums only or for every album. If it can be missing for all, "Never played" must read "Not counted yet", not the whole library | `Model/HomeDashboard.swift`, `NavidromeAlbum` | A fixture with no `playCount` anywhere gives the not-counted state; a mixed fixture counts only the albums with no plays | Haiku, Medium |
| ~~**F2**~~ **Built in the F1-F4 PR.** Sonic analysis reads `getOpenSubsonicExtensions` directly when the Librarian is down. Was: | M6 | Add a client method for Navidrome's plugin list so Sonic analysis keeps its state when Librarian is down | `DiscairLibrarian` or the Navidrome client, `Model/ServicesModel.swift` | Librarian down: Sonic analysis shows its own state, not Unknown by default; decoder test with a fixture | Sonnet, Medium |
| ~~**F3**~~ **Built in the F1-F4 PR.** `member_of` reads "Member of <centre>" in the list. Owner decision (2026-11-12): work, recording, event and instrument nodes take the sector **Crew** (built in the F6-F12 PR). Was: | M7 | Give work, recording, event and instrument nodes a named sector instead of "Other", or record the owner's decision to keep "Other". Make `member_of` read "member of <name>" as in `connections--list` | `Model/GraphExplorer.swift` | Wording table test covers every relation code; sector list matches the owner's choice | Haiku, Medium |
| ~~**F4**~~ **Built in the F1-F4 PR.** Space on an unowned pick shows a notice. Was: | M8 | Space on a pick that is not owned does something stated (a short notice that the album is not in the library) instead of nothing | `CupertinoHome.swift`, `Model/HomeScreen.swift` | Key test: Space on an unowned pick shows the notice; on an owned pick it plays | Haiku, Medium |
| ~~**F5**~~ **Built in the F5-F10 PR.** Collection chart hidden when Librarian is down, as drawn. Was: | M8 | Align the collection chart with the mockup when Librarian is down (hide it, or record that the owner prefers it kept) | `CupertinoHome.swift` | Matches `home--librarian-unreachable`, or the difference is accepted in the PR | Haiku, Medium |
| ~~**F6**~~ **Built in the F6-F12 PR. The tile opens the Albums tab filtered to never-played albums (one shared rule, `HomeDashboard.neverPlayedIndices`), so the number and the page agree. Was:** | M8 | The "Never played" tile counts albums but opens a smart playlist of songs. Make the unit and the destination agree (count songs, or open an albums view) | `CupertinoHome.swift`, `AppState.openNeverPlayedPlaylist` | Tile number equals the number of items on the page it opens | Sonnet, Medium |
| ~~**F7**~~ **Built in the F6-F12 PR. The sheet's Test asks the service directly from this Mac with the typed values (`ServiceDraftProbe`); nothing is saved, so Cancel changes nothing. A changed address or username with an empty secret says it cannot be tested, because saved secrets are not readable. An untouched sheet still uses the server's test. Was:** | M9 | The edit sheet's Test must test the values typed in the sheet, not the saved settings | `CupertinoServices.swift`, `AppState+Services.swift` | Test with a changed address reports on that address; Cancel leaves the saved settings unchanged | Sonnet, Medium |
| ~~**F8**~~ **Built in the F5-F10 PR.** Rows without Disconnect carry a sentence saying why (Navidrome, slskd, Last.fm: the settings route clears a secret only for Discogs and ListenBrainz; Librarian and Music folder are set elsewhere). Was: | M9 | Disconnect for the services that can be cleared (Last.fm, slskd if the settings route allows it), or state in the row why there is none | `CupertinoServices.swift`, `ServiceEditSpec` | Every service row either offers a named Disconnect or says why not | Haiku, Medium |
| ~~**F9**~~ **Checked in the F5-F10 PR, not built.** `settings-services--degraded` already matches the code line for line (Answer, Since, Last good read, Checked). The Route and Server contract lines are not in the 6.2 prose; they appear only in the Librarian rows of `settings-services--healthy` and `--edit-sheet`, and need data the Services model does not hold (Tailscale route from the address, contract version and data generation from capabilities). **Owner decision (2026-11-12): add them to the Librarian row; built in the F6-F12 PR** (Route from the address, Server contract from `contract_version` and `generation` in capabilities, both only while the Librarian answers). Was: | M9 | Status now: add the Route and Server contract lines from 6.2, or remove them from section 6 if the owner agrees they add nothing | `CupertinoServices.swift` or this document | `settings-services--degraded` matches, or the difference is accepted | Haiku, Medium |
| ~~**F10**~~ **Decided and built in the F5-F10 PR.** Kept on the client; recorded in section 5.2 and the inspector and footer now say what they count. Was: | M9 | "Also on, in your library" is derived on the client from the walk. Keep it, or add a server field. Decide, then record it. The footer counts what was read, since the server sends no total; the same decision applies | `GraphExplorer.swift`, server only if chosen | The decision is written in section 5.2; the inspector and footer say what they count | Haiku, Medium |
| ~~**F11**~~ **Built in the F6-F12 PR. The aliases are gone, the backdrop and glass tint are tokens, and shell geometry is named in `CU.Shell` (the 4.3 exceptions). Larger page offsets in Now Playing, Artist and Album banners (60 to 120) are layout offsets, not gaps, and are left. Was:** | M10b | Replace the raw RGB gradient and literal sizes and gaps in the shell with tokens, then retire the old alias names (`CU.muted`, `CU.ink`, `CU.card`, `CU.fill`, `CU.hairline`) across `Themes/Cupertino`. Section 4.3 keeps the shell geometry; only values change | `CupertinoTheme.swift` and the other `Cupertino*.swift` files | Grep finds no raw colour, no off-scale gap and no alias in `Themes/Cupertino` except the named 4.3 exceptions | Haiku, High |
| ~~**F12**~~ **Built in the F6-F12 PR. `CupertinoTheme.content` switches over every `Screen`; the default branch is gone. Was:** | M10b | The `default: "not built yet"` branch in `CupertinoTheme.content` should be unreachable or show a real empty state | `CupertinoTheme.swift` | Every `Screen` case has a view; no "not built yet" string remains | Haiku, Medium |
| **F13** | Section 12 | Run the checks the log says were not run: a live-data run of Home, Connections and Services; VoiceOver and keyboard-only passes on Home, Connections List and Services; the states pass; layout at 1100 by 700, 1280 by 832 and 1600 wide with the queue open; Zine before and after M9; each M10a page and each Services state against its mockup | none unless a fix is found | Each check is recorded in `PROJECT_LOG.md`; differences from the mockups are listed and accepted by the owner | Owner with Sonnet, High |

Order: F1 to F12 are independent and can run in parallel. F13 comes last, and the platform is done only after it and the owner's approval of the look.

### Android

| Step | Objective and instructions | Files | Depends on | Acceptance | Tests and visual check | Model, effort |
|---|---|---|---|---|---|---|
| ~~**A1** Roles and type~~ **Merged** in PR [#992](https://github.com/abucalip/navi-librarian/pull/992), squash `43436b56` (2026-11-12). Was: Add the new `Palette` roles with defaults derived from existing ones, then the exact values of 7.3 for Sand, Night, Tape · Lime, Sheet · Violet. Sand accent to `#AD4016`. `bodySmall` 12/18; add `displayMetric`, `headlineSentence`; word spacing on title styles is not available in Compose, so set title tracking to −0.06em for strings containing a space through a `TitleText` helper | `theme/Palette.kt`, `theme/Theme.kt`, `common/Common.kt` | none | The palette contrast test passes for all 27 palettes with the new roles | Extend the existing palette contrast unit test | Haiku, Medium |
| ~~**A2** Motion kit~~ **Merged** in PR [#993](https://github.com/abucalip/navi-librarian/pull/993), squash `339f7551` (2026-11-12). Built as specified: `theme/Motion.kt` with the 7.4 tokens, `MotionRules` and `MotionPlans` (pure), `rememberReducedMotion` moved from `TapeDeck.kt`, and the helpers `fadeThrough`, `sharedAxisX` and `Modifier.enterStagger`. Choices: the Sticker Wall takes the standard family, since 7.4 does not cover it; reduced motion gives no animation, not the 100 ms fade (the acceptance line); Tape springs use damping 1.0 (no overshoot); Tape scales the stagger step too. Nothing calls the kit yet. Was: `theme/Motion.kt` with the tokens of 7.4, a `reducedMotion()` reader (move the check out of `TapeDeck.kt`), and per-layout scaling (Tape 0.6 and linear, Sheet spring 0.7). Helpers: `enterStagger`, `fadeThrough`, `sharedAxisX` | new file, `common/TapeDeck.kt` | none | Durations and easings equal the table; all helpers return no animation when reduced | Unit tests on the pure spec functions | Haiku, High |
| ~~**A3** Navigation~~ **Merged** in PR [#994](https://github.com/abucalip/navi-librarian/pull/994), squash `596562d3` (2026-11-12). Built with the owner's changes to the spec: no mini player on the layouts that lacked one; Discover is in the top bar, not the island, group or pill, for Standard, Sheet Stack and Sticker Wall; those keep Now Playing in the island, group or pill, and the rail's foot; Cassette Deck bar has Home, Discover, Library, Search and no Settings cell; Settings and Downloads in the top bar; Home page buttons removed. Was: Four destinations in the island, the Tape bar and the Sheet group; mini player for every layout; remove `PageButtons`; Settings and Downloads in the top bar; navigation rail from 600dp; tab and stack transitions from A2 | `NavIsland.kt`, `MainShell.kt`, `common/TapeDeck.kt`, `common/SheetStack.kt`, `home/HomeScreen.kt`, `player/MiniPlayer.kt` | A1, A2 | Every destination is one tap in every layout; back behaviour unchanged; matches the navigation in `dashboard` | Update `TapeDeckRules` and `SheetStackRules` tests; new rule tests for the rail breakpoint. Visual: Day against the mockup, the other three layouts against 7.3 | Sonnet, High |
| ~~**A4** Charts~~ **Merged** in PR [#996](https://github.com/abucalip/navi-librarian/pull/996), squash `ddb669b5` (2026-11-12). Built as two files: `common/ChartMath.kt` (pure rules: ticks, scales, slots, selection, per-family style, states, tracker stages, TalkBack summaries) and `common/Charts.kt` (`LineChart`, `ColumnChart`, `PairedBars`, `Dumbbell`, `RankedBars`, `StageTracker`, `ChartFrame`, `ChartLegend`). Tests: `ChartMathTest`, 17 passing locally. Not checked: nothing calls the kit yet, so no screen was compared with `stats`, and no device check was run; Tape and Sheet follow 7.3 in words only. Choices: the stale state uses a text triangle (no warning icon in the icon set); `PairedBars` highlights the row with the largest gap when none is chosen; column charts label every column. Was: `common/Charts.kt` on Compose `Canvas`: line, columns, paired bars, dumbbell, ranked bars, tracker; drag selection with the value above the plot; per-family drawing (Classic rounded, Brutal outlined, Tape stepped); states; semantics with a summary and values | new file | A1, A2 | Day matches `stats`; Tape and Sheet follow 7.3; TalkBack reads the summary | Unit tests for scale and bin maths. Visual: `stats` | Sonnet, High |
| ~~**A5** Sheets and feedback~~ **Merged** in PR [#997](https://github.com/abucalip/navi-librarian/pull/997), squash `271d74f4` (2026-11-12). Built: `common/ConfirmSheet.kt` (the confirmation sheet, with pure `ConfirmSpecs` and `ConfirmRules`) replaces the Dismiss and Sign out dialogs; Discover's snackbar takes the shell's bottom clearance (the shell's already did, and includes the Cassette Deck mini player); the Get button cross-fades with a 0.8 to 1 scale at `base`, and a failure shakes 4 dp twice; reduced motion gives no animation. Tests: `ConfirmSheetTest` (5), `AcquisitionHubTest` and `AcquisitionTest` (15 each), all passing. Not checked: no emulator or device run; the sheet, Get animation and snackbar position have not been seen on screen. Was: Confirmation bottom sheet replacing the Dismiss and Sign out dialogs; snackbar position above the mini player; Get button state animation | `downloads/DownloadsScreen.kt`, `DiscairApp.kt`, `common/GetButton.kt`, `common/Controls.kt` | A2 | The safe action is first and outlined; the destructive label names what is deleted; nothing is sent before confirm | Existing download tests still pass; new test for the sheet's actions | Haiku, High |
| ~~**A6** Dashboard~~ **Merged** in PR [#998](https://github.com/abucalip/navi-librarian/pull/998), squash `56297976` (2026-11-12). Built: `home/DashboardModel.kt` (pure figures and states), `home/DashboardScreen.kt` (modules), `HomeScreen.kt` rewritten with the modules in order and two panes from 840dp (primary two thirds: hero, pick, arrivals, numbers, shelves, genres, radio, server; secondary one third: stats, taste, insight). Hero, the 30-day change and the 12-month line come from one read of the library list by added date (D4); a read that cannot reach back far enough shows "not available". D2 is wired: the Listens stat reads `listens_by_day` from the taste body (last 7 days against the 7 before; fewer than 14 days or no field gives "Not available yet"). Never played has no Android source and says "Not available yet". Choices: Waiting is today's picks with a count of arrived albums; the insight card offers Open album and Why?, not Play or Get; no Open stats link and the Server row opens nothing (both belong to A7); Save and the two dismissals send at once, with no Undo snackbar; Recently added still makes its own library read; the warning banner shows when the downloads list cannot be read. Tests: `DashboardModelTest` (18) and `TasteTest` (10) pass locally. Not checked: no emulator or device run, so neither mockup was compared on screen; Night, Tape and Sheet unchecked; live `listens_by_day` unchecked. Was: Build 8.1: modules in order, each with loading, empty, unavailable; hero count-up; warning banner; two panes at 840dp. Sheet's requests section and Sticker's wall keep their own form inside modules 3 and 4 | `home/HomeScreen.kt`, `home/*.kt`, new `home/DashboardModel.kt` | A3, A4 | Matches `dashboard` and `dashboard-tablet`; D2 and D4 modules show "not available" until served | `DashboardModelTest` (figures and states). Visual: both mockups | Sonnet, High |
| ~~**A7** Stats and Server screens~~ **Merged** in PR [#999](https://github.com/abucalip/navi-librarian/pull/999), squash `519b6c75` (2026-11-12). Built: `StatsRoute` and `ServerRoute`; `ui/stats/StatsModel.kt` (pure) and `StatsScreen.kt`; `model/Server.kt` (decoders), `data/ServerRead.kt` (one request each, all at once, through `LibraryRepository.serverReads`), `ui/settings/ServerModel.kt` (state table, pure) and `ServerScreen.kt`. Stats: range chips; the collection line comes from one full read of the library list by added date (weekly for 3M, monthly for 1Y and 5Y, three-monthly past 60 buckets for All; a list too long to read back says so); decades draw listens only from a sound recent era window, otherwise albums only; When you listen reads the taste `context` time-of-day lens (new on Android, with its zone). Server: Librarian, Navidrome, slskd, Last.fm, ListenBrainz, MusicBrainz data, then Insight lenses and Artist popularity; Librarian unreachable gives Unknown, Navidrome keeps the phone's own check, a configured service not yet tested is Unknown; a test route is called only for a service that is set up. Reached from the dashboard (Open stats, the Listens and Never played cards, the Server row) and a Settings button. Choices: Shelf life says "not available" and offers no Play button, because the phone has no last-played dates; the mockup's Discogs, Sonic and SMB rows are not drawn (they are not in the Server mockup); Settings gets a plain "Server and services" button, its state-line row belongs to A8. Tests: `StatsModelTest` (18), `ServerModelTest` (18), `TasteTest` (10) and `DashboardModelTest` (11), all passing locally; required CI passed on the PR head. Not checked: no emulator or device run, so neither mockup was compared on screen; Night, Tape and Sheet unchecked; live routes unchecked; settings, test and job-status bodies are shaped from the route code, not recorded (capabilities and taste context use the server fixtures). Was: Two new routes and screens per 8.2; Server reads the settings and status routes through `Repository` | `Routes.kt`, new `stats/StatsScreen.kt`, new `settings/ServerScreen.kt`, `data/Repository.kt`, `net/LibrarianClient.kt` | A4 | Matches `stats` and frame 3 of `downloads-settings-server`; Librarian down shows Unknown, not failed | Decoder tests with recorded fixtures; state table test | Sonnet, Medium |
| ~~**A8** Discover, Library, Search, Downloads, Settings~~ **Merged** in PR [#1000](https://github.com/abucalip/navi-librarian/pull/1000), squash `ee3571df` (2026-11-12). Built: pure rules in `downloads/DownloadsModel.kt` (`DownloadsRules`: tracker step per status, the fill, the title line; `LibraryText.countLine`; `SettingsRules.serverLine`) with `DownloadsRulesTest` (7). Discover: list names are chips in one scrolling row; Get sits on the cover of an unowned card; insight cards use `animateItem`. Taste sheet: the window is a segmented control and only the leading bar is accent. Library: Artists and Albums segmented tabs, one line "733 artists · A to Z" with Sort (Reverse is in the Sort menu), albums two to a row, artists a list; the icon groups, density slider and list/grid toggle are removed. Search: rounded 56dp field, hint line, "Owned" in words, Get on missing albums. Downloads: the A4 `StageTracker` on every record (failed step in danger), the title line "1 on its way · 1 arrived today · n need you", one filled "Open album" on an arrived album (the mockup says Play; a record has no owned album id to play). Settings: "Server and services" is a row with its state in words, a hairline above each section, Sign out is an outlined danger-labelled button that opens the A5 sheet. `animateItem` on Library artist rows, Search results, Downloads records and insight cards. Tests run: `DownloadsRulesTest`, `AcquisitionHubTest`, `AcquisitionTest`, `TasteTest`, `InsightsTest`, `LibraryViewModelTest`, all passing locally; required CI passed on the PR head. Not checked: no emulator or device run, so none of the three mockups was compared on screen; Night, Tape and Sheet unchecked. What was not built is in A8b. Was: Restyle per 8.2 with the taste sheet; list motion with `animateItem` | `discover/*.kt`, `library/LibraryScreen.kt`, `search/SearchScreen.kt`, `downloads/DownloadsScreen.kt`, `DiscairApp.kt` (settings) | A3, A4, A5 | Matches `discover`, `library-search`, `downloads-settings-server` | Existing `TasteTest`, `InsightsTest`, library and search tests. Visual: three mockups | Sonnet, Medium |
| **A8b** What A8 did not build | (1) Taste sheet: the action "Make an Ambient playlist" (`discover` frame 3). The Android client has no route that creates a playlist, so this needs a server route first (new module, per the server module rule) and then the button. (2) Settings: draw the rows as in `downloads-settings-server` frame 2: a leading icon, a chevron and a state line on every row (Appearance, Streaming quality, Equalizer, Radio, ListenBrainz), with the Scrobble switch in the row; the existing controls and text keep their form today. (3) Library: the "Search your library" field is kept though the mockup does not draw it; decide with the owner whether to remove it (Search covers the whole library). (4) Downloads: the existing detail lines (quality profile, peer, updated time, byte and track counts) and the corner icon buttons are kept; the mockup shows only the tracker, the state in words and one action row. (5) Downloads: Play on an arrived album, which needs the owned album id (look it up from the library by artist and album) in place of "Open album". (6) Library: `animateItem` on the album grid, which was not added. (7) The visual check of the three mockups on a device, and Night, Tape and Sheet | `discover/TasteCard.kt`, `DiscairApp.kt` (settings), `library/LibraryScreen.kt`, `downloads/DownloadsScreen.kt`, server module for (1) | A8 | The listed items match `discover` frame 3, `library-search` and `downloads-settings-server`, or the owner accepts each difference | Existing `TasteTest`, library and download tests; new tests for any pure rule. Visual: three mockups | Sonnet, Medium; Haiku, Medium for (3), (4), (6) |
| **A9** Remaining screens and theme pass | New roles and motion on Album (shared-element cover), Artist, Genre, Now Playing, Radio; then a pass over all four default palettes and two non-default ones for contrast and identity | `album/*.kt`, `artist/*.kt`, `player/*.kt`, `radio/*.kt` | A6, A8, A8b | 7.3 identity table holds on a device for the four themes; 200% font scale holds on the dashboard | Existing tests. Visual: owner review of Night, Tape, Sheet, which have no mockup | Haiku, High for the role swaps; Sonnet, Medium for the shared-element transition |

### Server proposals

| Step | Objective | Model, effort |
|---|---|---|
| ~~**S1**~~ **Merged** in PR #986, squash `41449e29` (2026-11-11). Was: Contract proposal and route for D2 (listens by day) in a new module, with fixture and direct-import test; nothing added to `navidrome_server.py` | Sonnet, Medium |
| ~~**S2**~~ **Merged** in PR #987, squash `67dc7dce` (2026-11-11). Was: Status route for the insights refresh job (D3), read-only over `job_runs` for both lens jobs; new module `intelligence/insights/refresh_status.py`, route `app/api/insight_lens_status.py`; nothing added to `navidrome_server.py` | Haiku, High |
| ~~**S3**~~ **Done 2026-11-12 (check only, no code).** D4: the added-date field is already served, so nothing was added. D5: the Android app did not save its play queue; the answer is recorded in section 9, and the Android slice was built and merged in PR #995 (`2fa3433b`). Was: Check D4 and D5 and record the answers; add the added-date field if absent | Haiku, Medium |

## 12. Verification

None of this has been run. These are the checks to perform as steps land.

| Area | Check | Pass when |
|---|---|---|
| Visual fidelity | Screenshot at the mockup's size beside the PNG (macOS 1280 wide window, Android 360 by 780dp) | Layout, order, type roles and colours match; differences are listed in the PR and accepted by the owner |
| Guidelines | `UI_DESIGN_RULES.md` section 9 checklist per screen | Every box ticked, or the break is named in the PR |
| Colour and contrast | Unit tests over the token tables (M1, A1) | Text and text-on-accent at least 4.5:1; chart marks that carry data at least 3:1 |
| Typography | Grep for raw sizes outside the role tables | None on macOS Cupertino; Android uses `MaterialTheme.typography` roles |
| Themes | Each Android screen in Sand, Night, Tape · Lime, Sheet · Violet, plus one other light and one other dark palette | Identity table 7.3 holds; nothing unreadable |
| Layout | macOS at 1100 by 700, 1280 by 832, 1600 wide, queue open. Android at 360, 412, 600 and 840dp wide, landscape, 200% font scale | No clipped text, no horizontal scroll, stacking as specified |
| Accessibility | VoiceOver and TalkBack pass on Home, Connections List, Services, the Android dashboard and Stats; keyboard-only on macOS | Every control named, charts summarised, status never by colour alone, focus visible |
| States | Force each state with fixtures: loading, empty, off, not loaded, not enough data, stale, failed, offline | Each shows its own sentence; none shows a zero or a blank |
| Navigation | Android: every destination from every layout, back and predictive back. macOS: sidebar, status popover, ⌘K unchanged | No dead end, no changed shortcut |
| Charts | Compare each plotted value with the model's number in a test; bars start at zero | Equal; selection reads the same value |
| Motion | Android with animator scale 1 and 0 | Table 7.4 at 1; fades only at 0; no dropped frames on the dashboard on the owner's phone |
| Regression | Filtered existing tests for every touched file; Zine screenshots before and after M9 | Pass; Zine unchanged |
| Performance | Home figures computed off the main thread; the Navidrome album list read once and shared; no new request on a page that did not make one, except the routes named here | Home first content within the current time; no extra provider traffic |

Platform acceptance:

- **macOS Cupertino** is done when M1 to M10 are merged, the 24 mockups are matched or their differences accepted, no accent is used for an error, each view has one filled primary, and Zine is unchanged.
- **Android** is done when A1 to A9 are merged, the seven Day mockups are matched, the owner has reviewed Night, Tape and Sheet on a device, all four destinations are one tap away in every layout, and motion follows the table and switches off with the system setting.
