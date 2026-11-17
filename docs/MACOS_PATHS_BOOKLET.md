# macOS Paths and Booklet sheets: design system and build plan

Status: **design proposed; P0 (model) merged in PR #1184 and P1 (Paths layout) in PR #1185.** Written 2026-11-17. In an earlier session the owner was shown one mockup of the Paths sheet and one of the Booklet sheet ([artifact](https://claude.ai/artifact/4SiJAn6umw5gJ4aqdp8msa)). The owner asked for a design system with exact specs and a detailed build plan, delivered as a docs PR. The owner decisions in section 8 come before P1 and B2.

The mockups are the spec:

- [`design/macos-paths-booklet/pages/mockups.html`](design/macos-paths-booklet/pages/mockups.html): open it in a browser. It needs no network and has a Day/Night switch. It covers 19 states.
- [`design/macos-paths-booklet/pages/png/`](design/macos-paths-booklet/pages/png/): one PNG per state.

When this text and a mockup differ, the mockup wins, except for the corrections in section 9. Measures come from [`components.css`](design/macos-paths-booklet/components.css). Colours, type, spacing, icons, motion and contrast come from [`tokens.json`](design/macos-paths-booklet/tokens.json). The package README lists every file.

The Cupertino design system in section 4 of [`redesign.md`](redesign.md) still applies in full: colour roles, type roles, the spacing scale and the control rules. So do the motion rules in `DEVELOPMENT_WORKFLOW.md` ("macOS client motion and CPU rules").

## 0. Read this first (implementing agent)

1. Read the package README and open `mockups.html`. Switch between Day and Night.
2. Run `python3 docs/design/macos-paths-booklet/_src/check_contrast.py`. It must report `0 failing`.
3. Read the code you will change:
   - `macos/Sources/DiscairUI/Chrome/PathsSheet.swift`
   - `Model/PathsModel.swift`
   - `Model/PathStory.swift`
   - `Chrome/PathArtwork.swift`
   - `Chrome/BookletSheet.swift`
   - `DiscairLibrarian/Artwork.swift` (`BookletView`, `bookletSpreads`, `ArtworkPicture.label`)
   - `Themes/Cupertino/CupertinoPalette.swift`
   - `Themes/Cupertino/CupertinoTheme.swift` (`CU`)
4. Read the Android Trail spec (`pathsredesign.md`, section 5). The link and grouping rules below are the same, so both clients group a path the same way.
5. Use no hex values and no pixel values in Swift. Use the `CU` roles, `CU.Space`, and the generated `CU.PathsSheet` / `CU.Booklet` constants (`swift/CUPathsBooklet.swift`).

## 1. What changes

### Paths sheet (album and artist)

| Today | New |
|---|---|
| Fixed 820 × 520 | Resizable: ideal 1040 × 680, minimum 820 × 520 (D2) |
| Title "Paths from X", then a segmented control | Header: start cover 56, the eyebrow "Paths from", the title, and the artist and year. A close button at the trailing edge |
| Segmented tabs | Text tabs 24 apart, with a 3 pt accent underline on the chosen tab and a count for tabs already loaded |
| Table: #, name with a 28 pt thumbnail, Detail, Why (cut off at 150) | **Trail**: steps grouped under their link (person, studio, work, label, place) on a rail. Each group is a row of 170 pt cover cards that wraps |
| 300 pt inspector on the right | Full-width **detail bar** at the bottom: cover 72, title line, the whole story, evidence and keys, then the actions |
| Footer: Close, "Step x of y", Play Album, Open | The actions move into the bar. Close is the header button and Escape. "Step x of y" is dropped; the tab count replaces it |
| No filter | Client-side filter: All / Not in library / In library (shown only when the answer holds both kinds) |
| Up and down arrows | ← → and ↑ ↓ move in visual order (D6); Return opens |

### Booklet sheet

| Today | New |
|---|---|
| One page at a time | **Spread** (default): the cover alone, then pairs, built from `BookletView.spreads`. **Page** keeps today's one-page reading |
| An "Another booklet" button that cycles, with a notice | A **sidebar** that lists every booklet by edition, with its page count and pixel width |
| Extras appended after the last page | An **Extras** section in the sidebar (Obi, Sticker, Poster). In the filmstrip they come after a separator |
| "Page 4 of 16 · Pinch to zoom" in the header | Title bar: album title, "Booklet · edition · Pages 4–5 of 16", Page/Spread switch, zoom − / value / + / 1:1 |
| Pinch only | Pinch, plus buttons and ⌘+ / ⌘− / ⌘0. Every gesture has another way to do it |
| Caption under the page | Three lines under the spread: where you are and the edition, the Cover Art Archive comment, then size and keys |
| Nothing | A **filmstrip** of every spread; clicking one jumps to it |

### What stays

- **Paths:** the tabs and their order, the summary sentences, and one request per tab, asked only when the tab is chosen. The answers kept in `PathsSheetModel.phases`, and the wording of every story, note, empty and failure sentence. Request update. Opening an album or artist closes the sheet. The alternate-cover cycle on hover (`PathRowThumb`) stays.
- **Booklet:** the dark ground. The full-resolution file is loaded only once a zoom past 1.25 is settled. The PDF booklet opens in PDFKit with its links left dead. The caption is plain text (no text recognition and no credit links). Escape closes.

## 2. Mockup index

| State id (`?only=`) | What it shows |
|---|---|
| `paths-crew` | Album sheet, Crew, Day: the trail, the selected card, the capped note, the detail bar |
| `paths-crew-night` | The same sheet in Night, with the second card selected |
| `paths-filter` | Filter "Not in library": the "n of N" count, the hidden card |
| `paths-room` | Room: session photos in the bar |
| `paths-gaps` | Gaps: owned only, the play label, Play Album, the history note |
| `paths-sonic` | Sonic: flat cards, the match-count line, the skipped note |
| `paths-loading`, `paths-failed`, `paths-empty` | Phases |
| `paths-artist-musician` | Artist sheet, Follow the Musician: songs grouped by musician |
| `paths-artist-sideman` | Artist sheet, Sideman: round artist photos, Open Artist only |
| `paths-min` | 820 × 520 reflow |
| `booklet-spread` | Spread, sidebar with three editions and extras, filmstrip. The Booklet states are drawn with D1 (a): a sheet with a Done button, no window controls |
| `booklet-page` | Page mode |
| `booklet-extra` | An extra (Obi) alone |
| `booklet-single` | One booklet, no extras: no sidebar |
| `booklet-pdf` | PDF booklet in PDFKit |
| `booklet-loading` | A spread still loading |
| `booklet-min` | Under 900 wide: an edition pop-up in the bar instead of the sidebar |

## 3. Design system

The full tables are in `tokens.json`. This section is the summary that an implementation is checked against.

### 3.1 Paths colours (CU roles; Day and Night follow the mode and the accent hue)

| Use | Role | Mockup value | Match |
|---|---|---|---|
| Ground, card ground, selected filter segment | `CU.content` | #ffffff | exact |
| Titles, story, pill text | `CU.text` | #1d1d1f (pill #3a0d18) | exact (pill: substituted) |
| Secondary text | `CU.textSecondary` | #6e6e73 | substituted (#636368, per redesign 4.1) |
| Hairlines, rail | `CU.separator` | #e5e5ea | exact |
| Card hover, detail bar ground | `CU.bgPanel` | #f7f7f9 | substituted |
| Close button, filter track | `CU.bgFill` | #f2f2f5 | substituted |
| Underline, dot, primary button, focus ring | `CU.accent` | #D61F4A | exact |
| "Not in library" text, Get marker text | `CU.accentStrong` | #C8163F | exact |
| Link pill, selected card | `CU.accentTint` | #FCE8EC | exact |
| Selected card border | `CU.accent` at 35% | rgba(214,31,74,.35) | derived |
| "Not in library" border | `CU.accentStrong` at 45% | rgba(200,22,63,.45) | derived |
| Get marker ground | `CU.content` at 92% | rgba(255,255,255,.92) | derived |
| "In library" text / ground | `CU.success` / `CU.successTint` | #1f6b3a / #e6f4ea | substituted |
| Secondary button border | `CU.separatorStrong` | rgba(0,0,0,.18) | substituted |
| Artist line on the **selected** card | `CU.text` | #6e6e73 | substituted (contrast, section 9) |
| Failed sentence and icon | `CU.danger` | (today: red) | substituted |

### 3.2 Booklet colours (always dark; fixed, `CU.Booklet`)

| Role | Hex | Use |
|---|---|---|
| `ground` | #171717 | Window ground (the same as today's `Color(white: 0.09)`) |
| `bar` | #1C1C1E | Title bar strip |
| `panel` | #202022 | Sidebar |
| `ink` / `ink2` | #F5F5F7 / #9A9AA0 | Primary / secondary text, arrows at rest |
| `quote` | #C9C9CE | Caption comment |
| `rule` | #2F2F33 | Hairlines, filmstrip separator |
| `control` / `controlOn` | #2C2C2F / #4A4A4F | Segment track and zoom buttons / selected segment |
| `hover` / `arrowHover` | #2A2A2D / #262629 | Hovered row or extra / hovered arrow |
| `tag` / `tagInk` | #2F2F33 / #D6D6DB | Neutral tag (only with D4) |
| `ownedTag` / `ownedTagInk` | #1F3A2A / #9FDCB3 | "Your edition" tag (only with D3) |
| `selectedInk2` | #D6D6DB | Edition detail on the selected row |
| `stageAccent` | `CUPalette.make(.night, accentHue:).accent` | Selected filmstrip ring (2 pt), selected row edge (60%), focus ring |
| `selectedRow` | `panel` mixed with `stageAccent` at 0.18 | Selected edition row |
| spread shadow | black 60%, radius 40, y 18 | Under the spread |
| gutter | black: clear, 18%, 28%, 18%, clear, 46 wide | Over the spine of a two-page spread |

The paper colours, Georgia type and session photo in the mockup draw stand-in pages. They are not tokens.

### 3.3 Type (system font only; `CU.Font` roles)

Paths:

| Text | Role |
|---|---|
| Eyebrow | `eyebrow` |
| Start title | `title2`, one line |
| Artist and year, summary (2 lines), tabs | `body` |
| Chosen tab | `headline` |
| Tab count | `caption` medium |
| Filter, role line, count, artist line, capped note, notes | `callout` |
| Pill | `body`, with the name in `headline` weight |
| Card title | `headline`, 2 lines |
| Extra line, badges, evidence, key caps | `caption` (badges semibold, key caps monospaced) |
| Bar title | `headline`, 1 line |
| Story | `body`, 3 lines at most, 560 wide at most |
| Buttons | `headline` |

Booklet:

| Text | Role |
|---|---|
| Bar title, edition name, caption line 1 | `headline` |
| Bar detail | `body` |
| Segment, zoom value | `callout`, value monospaced |
| Sidebar headings | `eyebrow` |
| Edition detail, tags, extra labels, filmstrip numbers | `caption` |
| Caption lines 2 and 3 | `callout` |

Every number uses `.monospacedDigit()`.

### 3.4 Spacing and sizes

Spacing is snapped to `CU.Space` (4, 8, 16, 24, 32). The table in `tokens.json` → `space` gives the mockup value and the snapped value for each place. Named exceptions:

- `CU.PathsSheet.railGap` = 12
- `coverGap` = 12
- `CU.Booklet.editionRowGap` = 2

Sizes are the generated constants. The main ones:

| Item | Size |
|---|---|
| Rail | Column 22, x 10, width 2 |
| Dot | 12, with a 3 pt ring in the ground colour, 5 from the top |
| Card | Minimum 170, radius 10, padding 8 |
| Cover inside a card | Radius 6 |
| Detail cover | 72 |
| Buttons | 28 high, radius 8, padding 12 |
| Booklet bar | 46 |
| Booklet sidebar | 232 (collapses below 900) |
| Edition mini | 40 |
| Extra thumbnail | 56 |
| Arrow | 32 × 56 in a 36 column |
| Filmstrip page | 30 × 38, ring 2 |

### 3.5 Icons (SF Symbols; regular weight unless stated)

| Use | Symbol | Size |
|---|---|---|
| Close (Paths) | `xmark` semibold | `CU.Icon.small`, in a 26 circle on `bgFill` |
| Get button | `arrow.down` semibold | small |
| Not in library / In library | `circle` / `checkmark` | 11 (caption) |
| Play Album | `play.fill` | small |
| Card with no cover | `opticaldisc`, `music.note`, `person.fill` (unchanged `PathStep.symbol`) | half the cover |
| Failed | `exclamationmark.triangle`, in `CU.danger` | row |
| Previous / next | `chevron.left` / `chevron.right` | 22 |
| Zoom out / in | `minus` / `plus` semibold | small |
| PDF edition mini | `doc.richtext` | row |

1:1, Page / Spread and the key hints are text, not symbols.

### 3.6 Motion

One-shot transitions only. No `TimelineView(.animation)`, no `.repeatForever`, no repeating symbol effects. Under Reduce Motion every duration is 0.

| What | Duration and curve |
|---|---|
| Hover grounds | 0.12 s ease-out |
| Scroll to the selection | 0.12 s ease-out |
| Filter fade | 0.15 s |
| Spread turn | 0.15 s cross-fade. No page curl |
| Zoom reset | 0.2 s |

The `PathRowThumb` hover cycle (one step every 1.2 s, only while hovered) is unchanged. The spinners are the system `ProgressView`.

### 3.7 Contrast

`check_contrast.py` checks 32 pairs in Day and Night, over the default accent and 72 hues. Text needs 4.5:1 and graphics 3:1. All pass. The check found three problems in the first drawing, and the tokens fix all three:

- `CU.textSecondary` on the Night accent tint falls to 3.75:1 for yellow hues. On the selected card the artist line is `CU.text`.
- `ink2` on the selected Booklet row falls to 3.34:1. The row's detail uses `selectedInk2`.
- The mode accent on the Booklet ground falls to 1.90:1. The Booklet uses `stageAccent`.

## 4. Paths sheet spec

### 4.1 Layout, top to bottom

1. **Header.** The start cover is 56: the album's `CoverView` on an album sheet, `ArtistPhoto(name:)` (round) on an artist sheet. Beside it sit:
   - the eyebrow "Paths from"
   - the title, `model.title`
   - the line under it: album sheet, "artist · year" (the year is new: pass the album's year into `PathsSheetModel`, and leave it out when it is 0); artist sheet, "Person", "Group" or "Artist" from the loaded answer's `startType`.

   The close button sits at the trailing edge. It calls `state.paths = nil` and has `.keyboardShortcut(.cancelAction)`.
2. **Tabs**, then a hairline.
3. **Summary** (2 lines) with the filter at its trailing edge.
4. **Trail.** It scrolls (`ScrollView` and `LazyVStack`) and holds the groups, then the loose notes.
5. **Detail bar**, with a hairline above it. Only the ready phase with at least one stop draws it.

### 4.2 Links and grouping (pure, new `Model/PathTrail.swift`)

A step's **link** comes from its **first** reason, so the grouping is stable. Steps that share the same link name and kind form one group. Groups appear in the order of their first step in the server's answer, and steps keep the server's order inside a group. A step that is not first in its group can move up to join it (as on Android, D1 there).

Album sheet:

| Tab | Link name | Link kind |
|---|---|---|
| Crew | `via.name` | From the first evidence role: "producer credit", "engineer credit", "mixing credit", "mastering credit"; "production credit" when it has none |
| Guests | `via.name` | "guest credit" |
| Covers | `via.name` (the work) | "same work" or "related work" |
| Scene | `via.name` | "same label", "same area" or "shared artist" |
| Room | `via.name` (studio or event) | "recorded at" |
| Gaps | `via.name` | `PathStepReason.eyebrow`, in lower case |
| Sonic | none | (flat: no groups, section 4.4) |

Artist sheet:

| Tab | Link name | Link kind |
|---|---|---|
| Follow the Musician | The musician (`via` of type artist, person or group) | "musician" |
| Sideman | `via.name` where `via.type == "release"` | "a record they led" |
| Label | `via.name` (the label) | "same label" |
| Composition | `via.name` (the work) | "same work" or "related work" |
| Scene | `via.name` (the place) | "same place" |

A step whose first reason has no `via` goes under a group named by the kind alone (for example "production credit").

**Role line** (beside the pill) comes from the group's anchors on the start's side (`PathReason.anchor`), collected over the group's steps:

- An anchor that is the start album, or of type `release`, gives "On the album itself".
- Track anchors give "On *A*, *B* and N more": two titles at most, distinct, in server order, in italics.
- Gaps and Crew: as above.
- Covers: "Behind *A*" for the start's track.
- Artist sheet: "Played with {artist}" (Follow the Musician) and "{artist} played on it" (Sideman). **These two are new wording**, built from the sheet's artist name. Nothing else here is new.
- Everything else: **no role line**. Nothing is invented. The mockup's "Production credit on every track" is not derivable; see section 9.

**Count** (trailing, `callout`): the group's step count with the tab's noun. The nouns are album/albums; song/songs (Follow the Musician); artist/artists (Sideman, Scene); recording/recordings (Composition). With a filter on, the count reads "n of N albums".

**Capped note:** `PathCapped` entries are kept structured in `PathAnswer.capped`; today they are flattened into `notes`. Each one whose `via` folds equal to a group's name goes under that group, as today's sentence ("4 more albums with George Avakian are not shown."). Ones that match no group go to the loose notes.

**Loose notes** (truncation, Gaps history, Sonic skipped, unmatched capped) go under the last group, indented to the cards.

New types (pure, no SwiftUI, in `DiscairUI/Model/PathTrail.swift`):

```swift
public struct PathLink: Hashable, Sendable { public let name: String; public let kind: String }
public struct PathTrailGroup: Identifiable, Equatable, Sendable {
    public let id: String            // kind + "|" + folded name
    public let link: PathLink?       // nil only for the flat Sonic answer
    public let role: [StorySpan]     // empty: no role line
    public let stepIDs: [Int]        // PathStep.id, server order
    public let cappedMore: Int?      // from PathAnswer.capped
}
public enum PathFilter: String, CaseIterable, Sendable { case all = "All", notOwned = "Not in library", owned = "In library" }
public enum PathTrail {
    static func link(album step: PathStep, tab: AlbumPathTab) -> PathLink?
    static func link(artist step: PathStep, kind: PathKind) -> PathLink?
    static func groups(_ answer: PathAnswer, links: [Int: PathLink?], start: String) -> [PathTrailGroup]
    static func visible(_ groups: [PathTrailGroup], steps: [PathStep], filter: PathFilter) -> [PathTrailGroup]   // drops empty groups
    static func order(_ groups: [PathTrailGroup]) -> [Int]   // the visual order of step ids, for the keys
    static func looseNotes(_ answer: PathAnswer, groups: [PathTrailGroup]) -> [String]
}
```

The `PathStep` additions, filled in the existing `PathAnswer` initialisers:

- `firstVia: KnowledgeEntity?`
- `firstCode: String`
- `creditRole: String?`: the relation of the first evidence credit (`producer`, `engineer`, `mix`, `mastering`; the server sends `role` null for crew)
- `anchors: [KnowledgeEntity]`: from the reasons that share the first reason's link (same code and `via`), so a role line never shows another link's anchor (owner decision, P0)

`KnowledgeEntity` is already `Hashable, Sendable`. Do not use tuples: they would break `PathStep`'s synthesized `Equatable`.

**Trap.** The dedupe at the end of `PathAnswer(artist:kind:)` (Follow the Musician and Label) rebuilds every step with a hand-listed memberwise init. Today it already drops `play` and `story`, and it would also reset the new fields, which would put every step under the no-via fallback. P0 replaces it with a copy that changes only `id` (a `with(id:)` helper). A `PathTrailTests` case checks that a Follow the Musician step keeps its link after the dedupe.

The selection stays a `PathStep.id` (a server index), as today.

### 4.3 Stop card

The card is a button. Its content, top to bottom:

1. **Cover.** A square filling the card width, radius 6. Album steps use `CoverView` through `PathRowThumb` (the hover cycle, size = card width; ask `.display` pictures above 64 pt instead of `.thumb`). Artist steps use `ArtistPhoto`, round. Steps without a cover use the `PathStep.symbol` tile.
2. **Get marker** (top right, inset 6). Only on album steps that are not owned. Its text is `acquisition.buttonLabel(for:)` ("Get", "Getting…", "Requested", "Retry"). It is a marker, not a button. Artist steps have none.
3. **Title.** `step.name`, two lines.
4. **Second line.** `step.detail`: artist; "album · album artist" on Follow the Musician; the recording on Composition. Not shown on Sideman or Scene.
5. **Extra line.** Only on two tabs: the Gaps play label (`step.play`), and on Sonic `step.why` plus " · year" when the year is sent.
6. **Ownership badge.** "✓ In library" (success) or "○ Not in library" (accentStrong outline). It uses a word and a mark, never colour alone.

States:

| State | Look |
|---|---|
| Rest | Clear ground |
| Hover | `CU.bgPanel` ground |
| Selected | `CU.accentTint` ground, 1 pt `accent` 35% border, second line in `CU.text` |
| Focus | 2 pt accent ring, offset 2 |

Click selects the card. Double-click opens it (the same as Return).

The grid is a `LazyVGrid(columns: [.adaptive(minimum: 170), spacing: 12])` inside each group, so it reflows when the sheet is resized.

### 4.4 Flat answers

Sonic answers, and any answer where **no** step has a link, draw one group without a rail, dot or pill. The cards start at the trail's leading edge. The filter is hidden there, because Sonic stops are all owned.

### 4.5 Filter

- It is shown only when the ready answer has both owned and not-owned steps.
- It is kept per sheet and starts at All each time the sheet opens (D5).
- It hides cards only. It never sends a request.
- When the selected step is hidden, the first visible step is selected.
- A group with no visible card is not drawn. Its capped note goes with it.

### 4.6 Selection and keys

- On a tab's first ready answer the first step **in visual order** is selected (today: index 0), so the bar is never empty.
- ← → and ↑ ↓ move to the previous or next step in visual order (`PathTrail.order` after the filter) and scroll it into view with a one-shot 0.12 s scroll.
- Return opens the selected step's target, as does double-click.
- Escape closes the sheet.
- Tab moves focus through the tabs, the filter, the cards and the bar's buttons.

### 4.7 Detail bar

The bar is a grid: cover 72 | text | actions.

**Title line:** name · artist (when the step has one) · year (when sent) · "In your library" or "Not in your library".

**Story:** `PathsSheet.attributed` of the step's story paragraphs, joined by a space, at most 3 lines. The whole text is in `.help` and in the VoiceOver label. When the story is empty, use the first reason's eyebrow and text, as the inspector does today.

**Evidence line:** `step.evidence` (for example "producer · MusicBrainz"), then the key hints ← → move ↩ open in caption key caps. Leave the evidence out when it is nil.

**Extra slot,** under the evidence line, by tab:

| Tab | Content |
|---|---|
| Room (album sheet, step with a cover) | `SameRoomPhotos`, unchanged, at 96 × 64 per photo |
| Gaps | A small card, eyebrow "Your listening" plus `step.play` in `headline` |
| Others | Nothing |

**Actions**, trailing, 8 apart, in this order:

1. **Open Artist** (secondary). Only when `step.artistName` is set and the target is not that artist. It closes the sheet and opens the artist.
2. **Get** (secondary, `arrow.down`). Only on a not-owned album step. It calls `state.actions.get(album:)` with the not-owned `AlbumItem` that `open(_:)` builds today. The label is `buttonLabel(for:)`, and the button is disabled when `canGet` is false. It adds no new acquisition logic. The existing action does the work.
3. **Play Album** (secondary, `play.fill`). Only when `libraryAlbum(step)` finds the album, as today.
4. **Primary:** `step.target.label` ("Open Album" or "Open Artist"). This is the default action (Return). It is disabled when the target is nil.

There is one primary per view (redesign 4.3).

### 4.8 Phases

| Phase | Look |
|---|---|
| Loading | `ProgressView("Finding the paths…")`, centred, at least 220 high. The header, tabs and summary are drawn at once. No skeleton shimmer |
| Failed | `exclamationmark.triangle` plus the failure sentence in `CU.danger`. Under it, Try Again and (when `canRequestUpdate`) Request update as secondary buttons, then `updateNote` in caption. The texts are unchanged |
| Empty | `model.emptyText`, centred, `body` secondary. No bar |

### 4.9 Accessibility

- Header title: `.isHeader`.
- Each tab: a button with `.isSelected` when chosen. The label adds ", 8 paths" when loaded.
- Group head: one element, "George Avakian, producer credit, on the album itself, 4 albums", with `.isHeader`.
- Card: one element, "Ellington at Newport, Duke Ellington, not in your library", with `.isSelected` when selected. The Get marker is in the label as "can be got" only when `canGet`.
- When the selection changes, the bar posts nothing. VoiceOver users reach it by moving to it. The bar is one element made of the title line, the story and the evidence. The buttons stay separate.
- Every colour state also has a word.

## 5. Booklet sheet spec

### 5.1 Layout

- **Title bar**, 46 high, across the full width, ground `bar`. It holds:
  - the album title (new parameter, see 5.9)
  - the detail "Booklet · {edition} · {position}"
  - on the trailing side: the Page/Spread switch, zoom − / value / + / 1:1, and (D1) a Done button
- **Sidebar**, 232 wide on `panel`, with a hairline on its right. It holds Editions, then Extras.
- **Main area:**
  - spread stage: arrow column 36, the spread, arrow column 36
  - caption
  - filmstrip, with a hairline above it

The sidebar is not drawn when there is one booklet and no extras. Below 900 wide it is replaced by an edition pop-up button in the bar. The extras stay reachable in the filmstrip and with the arrows.

### 5.2 Editions

There is one row per `BookletView`, in server order (best first).

- **Mini:** 40 × 40, radius 3, the first page as `AlbumPictureView(size: .thumb)`. A PDF booklet shows `doc.richtext` instead.
- **Name:** `edition`, or "Booklet {n}" when it is empty.
- **Detail:** "{n} pages · {w} px". Here n is the number of non-PDF pages and w is the first page's `width`; the px part is left out when the width is unknown. A PDF booklet reads "PDF".
- **Tags:** "Your edition" only with D3. A language tag only with D4.

Choosing a row:

- sets `current`
- goes back to spread or page 0 and zoom Fit
- posts the VoiceOver announcement "Booklet 2 of 3 · {edition}." (the existing `announce`, without the visual notice)

The "Another booklet" button and its notice are removed. The heading is "Editions · {n} booklet(s)".

### 5.3 Spreads and pages

- **Spread mode** (default) walks `booklet.spreads`: the cover alone, then pairs, a last odd page alone, then each extra alone.
  - A two-page spread draws both pages side by side, each fitted to the stage height.
  - Pages are not cropped, and each keeps its image aspect.
  - The gutter shade sits over the spine, and the spread shadow sits under the pair.
  - A single page or an extra is drawn alone, with no gutter.
- **Page mode** walks `booklet.spreads.flatMap { $0 }`, which is today's order.
- Switching modes keeps the current page in view. Going from page to spread lands on the spread that contains it.
- The mode is kept for the sheet's lifetime only.
- ← → and the chevrons turn one spread (or page). They are disabled at the ends.
- The turn is a 0.15 s cross-fade, or none under Reduce Motion.

**Position text** (bar and caption):

| Mode | Text |
|---|---|
| Spread | "Pages 4–5 of 16" |
| Page | "Page 4 of 16" |
| Extra | The extra's type ("Obi") |

16 is the page count (pages only, extras not counted).

### 5.4 Extras

- The sidebar's Extras section is a 3-column grid of 56 thumbnails (`AlbumPictureView .thumb`) with the type name under each.
- Choosing one jumps to its spread.
- The selected extra gets the 2 pt `stageAccent` ring.

### 5.5 Caption (under the spread, centred)

1. **Line 1** (`headline`): "{position} · Booklet, {edition}". An extra reads "{type} · {edition}".
2. **Line 2** (`callout`, `quote`, in “ ”): the page's Cover Art Archive `comment`. For a pair, both comments are joined by " / ". The line is left out when there are none.
3. **Line 3** (`callout`, `ink2`): "{w} × {h} px" (with " each" for a pair when the sizes are equal, otherwise left out), then " · ← → turn · pinch to zoom · double-click to fit".

VoiceOver reads each page's `ArtworkPicture.label`, unchanged.

### 5.6 Filmstrip

- It is a horizontal `ScrollView` with a `LazyHStack`, spacing 8.
- There is one item per spread (or per page in Page mode). Each item is its pages at 30 × 38, aspect-filled `AlbumPictureView .thumb`, 1 apart, with the number label under them ("1", "2–3", …, "16").
- After a 1 pt separator come the extras, labelled by type.
- The current item has a 2 pt `stageAccent` ring and `ink` label. It is scrolled into view with a one-shot scroll.
- Clicking an item jumps to it.
- Each item's VoiceOver label is "Pages 2 to 3" or "Obi", with `.isSelected` on the current one.

### 5.7 Zoom

- Zoom applies to the whole spread (both pages together) and stays in today's range of 1 to 6.
- − and + divide or multiply by 1.25.
- The value label reads "Fit" at 1, otherwise "{n} %".
- **1:1** sets the zoom so that one image pixel is one point: the first page's `width` divided by its fitted width, clamped to 6. That loads the full-resolution file. It is disabled when the width is unknown.
- Shortcuts: ⌘+ zooms in, ⌘− zooms out, ⌘0 fits. Double-click also fits, as today.
- Pinch and drag-to-pan stay. The full-resolution file is loaded per page once zoom is past 1.25, as today.
- The zoom resets to Fit on a turn.

### 5.8 PDF booklet

- PDFKit, one page wide, continuous, as today.
- There is no Page/Spread switch, no caption and no filmstrip.
- The zoom buttons drive the `PDFView`:
  - − / + call `zoomOut` / `zoomIn`
  - Fit sets `autoScales = true`
  - 1:1 sets `scaleFactor = 1`
  - The value label shows the scale as a percentage.
- The bar detail reads "PDF, {n} pages" once the document is loaded.
- The sidebar row uses the `doc.richtext` mini.
- Links stay dead (the existing `Coordinator`).

### 5.9 States and sizes

| State | Look |
|---|---|
| Page loading (`image == nil`, request in flight) | The page's place keeps its size and shows a `ProgressView` with "Loading pages 4–5…" in `ink2`. The spread does not jump when the image arrives |
| Page failed (`albumImage` returned nil) | "This page could not be loaded." in the same place, `ink2` |
| PDF downloading or failed | Unchanged texts |

The sheet keeps `.sheet` presentation (D1). Its frame:

- minimum 760 × 600 (today's)
- ideal 1120 × 740, clamped to the parent window minus 40 on each axis

`BookletSheet` and `BookletOpener` gain `title: String`. The three callers pass the album title:

- `CupertinoAlbum.swift` through `BookletOpener`
- `NowPlayingArtwork.swift:391`
- `RelatedGrids.swift:180`

### 5.10 Accessibility

- Bar title: `.isHeader`.
- Edition rows and extras: buttons with `.isSelected`.
- Arrows: labelled "Previous spread" and "Next spread", with help that names the key.
- Zoom buttons: labelled, with help naming the shortcut.
- The spread is one element whose label is the page labels joined.
- Focus starts on the stage, so the arrow keys work at once, as today.

## 6. Code map

| File | Change |
|---|---|
| `Themes/Cupertino/CUPathsBooklet.swift` (new) | Copy of `docs/design/macos-paths-booklet/swift/CUPathsBooklet.swift`. P1 takes `CU.PathsSheet`, B1 takes `CU.Booklet` |
| `Themes/Cupertino/CupertinoPalette.swift` | B1: a stored `var stageAccent: CURGB`, the Night accent for the same accent setting in both modes. `day` and `night` set it to `night`'s default accent (#FF7A8F); `make(_:accentHue:)` sets it to `nightAccent(hue: accentHue, panel: <night panel>).accent` when a hue is given. This matches `make("night", hue)["accent"]` in `_src/cupalette.py`, which the contrast check uses |
| `Model/PathTrail.swift` (new) | Section 4.2 types and pure functions |
| `Model/PathsModel.swift` | The `PathStep` additions. `PathAnswer.capped` stays structured: notes no longer hold capped sentences, and `PathTrail.looseNotes` adds the unmatched ones back. `PathsSheetModel` additions: `filter`, `year`, `groups` (computed), `order`, `count(for tab:)`; `move(by:)` walks `order` |
| `Model/AppState.swift` | Pass the album's year into `PathsSheetModel` (line ~559) |
| `Chrome/PathsSheet.swift` | Rewritten layout (section 4). Kept: `attributed`, `item`, `library`, `libraryAlbum`, `open`. Removed: `list`, `row`, `inspector`, `card`, `footer`. `SheetButtonStyle`: 28 high, radius 8, `headline`, border `separatorStrong` |
| `Chrome/PathTrailViews.swift` (new) | `PathGroupView`, `PathStopCard`, `PathDetailBar`, `PathFilterControl`, so `PathsSheet.swift` stays short |
| `Chrome/PathArtwork.swift` | `PathRowThumb` asks `.display` above 64 pt |
| `Model/BookletLayout.swift` (new) | Pure: the items for a mode, labels, position text, caption lines, edition detail, zoom steps, 1:1 factor, mode switch mapping |
| `Chrome/BookletSheet.swift` | Rewritten (section 5). `BookletPage` keeps its zoom and full-file logic, with the zoom lifted to the sheet; `PDFKitView` gains zoom commands. Split views into `Chrome/BookletParts.swift` (new) if the file passes about 300 lines |
| `Chrome/NowPlayingArtwork.swift`, `Chrome/RelatedGrids.swift`, `Themes/Cupertino/CupertinoAlbum.swift` | Pass `title:` |

No server change is needed except D3. No Android change. `navidrome_server.py` is untouched.

## 7. Build plan

Each slice is one PR from current `main`. Tests are filtered (CLAUDE.md: never the full suite):

```sh
cd macos && printf '%s\n' <changed files> | scripts/select-tests.sh
swift test --filter <Target>
```

Each PR body reports exactly what ran.

| Slice | Content | Tests | Visible change |
|---|---|---|---|
| **P0 Model** | `PathTrail.swift`, the `PathStep` additions (as `KnowledgeEntity`, not tuples), `with(id:)` in place of the hand-listed rebuild in the artist dedupe, structured `capped`, `PathsSheetModel.filter`, `year` and `order`, `move(by:)` over the visual order | New `PathTrailTests` (a Follow the Musician step keeps its link and story after the dedupe; each tab's link from a fixture step, the evidence-role kinds, the no-via fallback, group order, capped match and no-match, role line words, filter and empty groups, visual order, selection fallback). Extend `PathsModelTests` (`move` in visual order, `capped` no longer in notes) | None |
| **P1 Paths layout** | `CUPathsBooklet.swift` (Paths part), header, tabs with counts, summary and filter, trail, groups, cards, detail bar, actions, keys, resizable sheet | `swift test --filter PathsModelTests`, `PathTrailTests` (no render test exists for this sheet yet; P2 adds one) | Yes |
| **P2 Paths details** | Flat Sonic, Room photos, Gaps card, artist round photos and symbols, phases, min-size reflow, accessibility labels, `PathRowThumb` `.display`. New `PathsRenderTests` in the `HomeRenderTests` pattern: renders `paths-crew` Day and Night, `paths-gaps`, `paths-sonic`, `paths-failed` and `paths-artist-sideman` to `DISCAIR_SCREENSHOT_DIR`, each first checking the inputs that make it that state | `PathsRenderTests`, `PathTrailTests` | Yes |
| **B1 Booklet base** | `CUPalette.stageAccent`, the `CU.Booklet` part, `BookletLayout.swift` | `BookletLayoutTests` (new: spread and page items, labels "2–3", position text, caption lines with and without comments and sizes, edition detail including PDF and unknown width, zoom steps and 1:1 clamp, page-to-spread mapping), `BookletTests`. `AppearanceTests` or `CupertinoTokensTests`: `stageAccent` against `CU.Booklet.ground` ≥ 3:1 and `ink` against `selectedRow` ≥ 4.5:1 over hues 0–355 in steps of 5 | None |
| **B2 Booklet layout** | Bar, sidebar (editions, extras), spread stage with Page/Spread, caption, `title:` on the three callers, "Another booklet" removed, Done button (D1) | `BookletLayoutTests`, `BookletTests` | Yes |
| **B3 Booklet finish** | Filmstrip, zoom buttons and shortcuts, PDF zoom, page loading and failed states, narrow layout with the edition pop-up, accessibility. New `BookletRenderTests` (spread, page, extra, single, narrow; PDF is skipped offscreen, since `ImageRenderer` cannot draw `PDFView`, so a still stands in) | `BookletRenderTests`, `BookletLayoutTests` | Yes |
| **B4 Your edition** (only with D3) | Server: the artwork index adds `from_owned` per entry of `booklets` (true when the booklet's release is the owned release). Recorded in `SERVER_V2_CONTRACT.md` and the five artwork index fixtures. Mac: decode it and show the tag | Server `pytest` on the artwork index module only; `swift test --filter BookletTests` | Tag only |
| **Closeout** | `PROJECT_STATUS.md`, `PROJECT_LOG.md`, `ACTIVE_WORK.md` | None | None |

**CPU rule.** P1 and B2 add hover and turn transitions. Each of those PRs records Discair CPU with `top -l 4 -s 4 -pid <pid> -stats pid,cpu`, before and after, for four cases: playing on Home, playing on an album page, playing with Now Playing open, and paused. P1 adds a fifth case with the Paths sheet open, and B2 one with the Booklet open. The rules are in `DEVELOPMENT_WORKFLOW.md`.

**Owner check** after P2 and after B3: open both sheets in a real window and compare them with the PNGs.

## 8. Owner decisions (D2, D5, D6 answered 2026-11-17: the recommendations, built in P1; D1, D3, D4 still needed before B2)

| # | Question | Options | Recommendation |
|---|---|---|---|
| D1 | How does the Booklet open? | (a) `.sheet` as today, with a **Done** button at the trailing end of the bar and Escape; (b) its own window with traffic lights, as in the first mockup (a `WindowGroup(for:)` keyed by release group, so the booklets must be looked up again from the store) | **(a)**: no new window plumbing, and the same behaviour as today |
| D2 | Can the Paths sheet be resized? | (a) ideal 1040 × 680, minimum 820 × 520; (b) fixed 1040 × 680 | **(a)**: fits small screens |
| D3 | "Your edition" tag? | (a) build B4 (a server field plus the contract); (b) drop the tag | **(a)** after B3 if the owner wants it; the rest does not depend on it |
| D4 | Language tag ("Japanese")? | (a) needs a release-language field from the server; (b) drop it | **(b)**: no field today; the page count and width already help to choose |
| D5 | The Paths filter across opens | (a) back to All each time; (b) remembered | **(a)** |
| D6 | Arrow keys in Paths | (a) ← → and ↑ ↓ all move in visual order; (b) ↑ ↓ move by row of cards | **(a)**: simple and predictable with a reflowing grid |

## 9. Corrections to the first mockup

Where the first mockup ([artifact](https://claude.ai/artifact/4SiJAn6umw5gJ4aqdp8msa)) and this package differ, this package wins:

1. **Colours.** Colours are CU roles (section 3.1), so Night and the owner's accent hue work. Secondary text, hover, the chrome grey, the pill text and the "In library" greens are substituted.
2. **Type.** Sizes are snapped to `CU.Font` roles: 22 → 20, 14 → 13, 13.5 → 13, 12.5 → 13, 11.5 → 11, 10.5 and 10 → 11. Redesign 4.2 removed the off-scale sizes.
3. **Spacing.** Spacing is snapped to `CU.Space`, with three named exceptions (section 3.4).
4. **Booklet accent.** The Booklet's accent is the Night accent of the owner's setting (`stageAccent`). The Day accent on the dark ground can fall to 1.9:1.
5. **Selected items.** The second line of a selected item uses the primary ink (Paths) or `selectedInk2` (Booklet), for 4.5:1 in every hue.
6. **Owned album actions.** An owned album keeps **Open Album** as the primary button and adds **Play Album** as a secondary one. The first mockup replaced Open Album with Play Album, which broke "Return opens the album".
7. **Role line.** "Production credit on every track" cannot be derived from the answer. The role line comes from the anchors ("On the album itself", "On *A*, *B* and N more"), and is hidden when there are none.
8. **Caption.** The caption says "pinch to zoom", not "scroll or pinch". Scroll-to-zoom is not built; the buttons and shortcuts are the other way to zoom.
9. **Edition rows.** Edition rows do not show the release comment ("Back sleeve notes"). The comment belongs to images and is shown in the caption.
10. **Booklet close.** The Booklet's close is a Done button plus Escape (D1a). A sheet has no window controls.
11. **Paths footer.** The footer's "Step x of y" is dropped. The tab count holds the total.
12. **Sample sentences.** The detail-bar sentences on the artist sheet and on Sonic are samples. `PathAnswer(artist:kind:)` and `PathAnswer(album: SonicAlbumNeighbours)` build no `story`, so the bar shows the server's reason text: the section 4.7 fallback, which is the first reason's eyebrow and text. P0 to P2 do not write new story sentences for them.

## 10. Not in scope

- No new server data except D3.
- No Android change. Android has its own Trail sheets and Booklet tab.
- No text recognition on booklet pages.
- No page-curl animation.
- No change to how booklets are chosen or ordered (the server's order, best first).
