# Flow Home: Threads and Shelf mixer

Status: plan, approved direction. On 2026-11-15 the owner picked, from three Home proposals (A Threads, B Time, C Shelves), **A's Threads** and **C's Shelf mixer**. A's Sonic bridge and Shared hands, all of B, and C's Made in and Gaps are not part of this plan. No code yet. The steps are in section 9.

Scope: the **Flow** layout of the Android client (`Layout.Flow`, all seven Flow palettes), plus two small server additions that the Android sections need (S0a, S0b). No other theme, the web client or macOS changes. Every Android change sits behind `isFlow()`.

## 1. Files

| What | Where |
|---|---|
| This plan and design system | `docs/Home_threads_mixer.md` |
| Mockups (spec): frames T1 to T5 (Threads), M1 to M3 (Shelf mixer), K (components board) | [`design/android-art-themes/flow/home-threads-mixer/home-threads-mixer.html`](design/android-art-themes/flow/home-threads-mixer/home-threads-mixer.html) and `home-threads-mixer.png` beside it |
| Mockup generator | `design/android-art-themes/_src/build_home_threads_mixer.py` (run from the repo root; inlines `shared.css`, `flow.css` and the icon symbols of `flow/home.html`) |
| Flow tokens and components (reused) | `design/android-art-themes/flow.css`, `ui/common/FlowKit.kt`, `ui/common/FlowPages.kt`, `ui/common/ArtIcons.kt` |
| Today's Flow Home | `ui/home/FlowHome.kt`, `ui/home/FlowHomeRules.kt` |

Re-render the PNG after editing the generator: `python3 docs/design/android-art-themes/_src/build_home_threads_mixer.py`, then headless Chrome `--window-size=1680,4000 --screenshot` on the HTML. 1 CSS px = 1 dp; covers are drawn stand-ins. **The mockups are the spec**; where this text and a frame disagree, ask the owner.

All Kotlin paths below are under `android/app/src/main/kotlin/app/discair/`.

## 2. The design in one paragraph

Two new sections on Flow Home, after the Insight card and before Genres. **Threads** draws the album you played most recently as a large cover in the middle, with up to six albums you own around it on an ellipse. Each one is joined to the centre by a line whose dash says what links them (a person, a label or a studio), with a small pill naming the link. You can filter the links (All, People, Labels, Places), select one, play it, move it to the centre, or tap its line to read why the two albums connect. **Shelf mixer** is three wheels (Era, Genre, Played) that pull a set of albums you own from the server's smart-playlist engine. The set shows as a cover mosaic, and you can play it, save it (a stored smart playlist, which also appears on the Mac) or roll the dice for a new combination.

## 3. Where they sit on Home

`FlowHome`'s `modules` list becomes: Carousel, Artists, Insight card, **Threads**, **Shelf mixer**, Genres, grouped list. Both new modules are their own `LazyColumn` items, so they load only when they come near the screen. On wide screens (≥ `DashboardRules.TWO_PANE_MIN_DP`) both go in the **primary** pane after Artists, not the secondary one, because Threads needs 360 dp. Change the `items(2)` split so the primary pane takes Carousel, Artists, Threads and Shelf mixer. Spacing between modules stays 20 dp.

## 4. Design system

### 4.1 Colour roles

Use the palette roles, never hex codes, so every Flow palette follows. No new colours. The values per palette, for checking screenshots:

| Role (`Palette`) | Flow (warm white) | Forest | Raspberry | Violet | Ember | Moss | Plum | Used for |
|---|---|---|---|---|---|---|---|---|
| `rail` | `#FBFAF7` | `#F8F9F4` | `#FCF8F8` | `#F9F8FC` | `#12110F` | `#0E1311` | `#151015` | page; ring gap round the selected orbit cover; Saved sheet container |
| `surface` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#1C1A17` | `#171E1A` | `#1F181F` | label pill, wheel well, sheets, grouped rows |
| `raised` | `#EFECE5` | `#E9EDE2` | `#F1E8E9` | `#ECEAF3` | `#2A2723` | `#232C27` | `#2D232D` | selected wheel row, chips, skeletons, dice button, Save button |
| `chart3` | `#D9D4C8` | `#D0D6C6` | `#DCCFD1` | `#D3CFE0` | `#4A453E` | `#3D4A43` | `#4C3D4C` | thread lines that are not selected |
| `text` | `#15130F` | `#12150F` | `#171113` | `#13111A` | `#F5F1EA` | `#EEF5F0` | `#F7EEF5` | headings, selected wheel value, album title |
| `textMuted` | `#645F55` | `#596051` | `#6A5C5F` | `#5F5A6E` | `#A9A296` | `#9FAFA5` | `#B3A2B0` | eyebrows, pill text, wheel neighbours, meta lines |
| `accent` | `#C2410C` | `#1B7340` | `#BE2260` | `#6A3BD2` | `#FF8A4C` | `#5FD28C` | `#FF7FAE` | selected line and pill, selection ring, Play, links (Change, Saved) |
| `onAccent` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` | `#1A0F08` | `#06170D` | `#2A0A17` | text and glyphs on accent |

The one fixed colour is the "+n" veil on the last mosaic cell: `Color.Black` at 55 % alpha with white Inter 700 18 sp, on every palette, because it sits on artwork, not on the page.

### 4.2 Type (font pair `flow`, Inter)

| Use | Style |
|---|---|
| Section title ("Threads", "Shelf mixer") | 700 20/24 sp, −0.02 em (the existing `SectionHeading`) |
| Eyebrow above it ("Around Laughing Stock", "Pull from your own shelves") | 600 12/16 sp, uppercase, +0.04 em, `textMuted` (`FlowEyebrow`) |
| Header link ("Change", "Saved") | 500 14 sp, `accent` |
| Selected-link title / mosaic summary | 600 15/20 sp, `text`, 1 line, ellipsis |
| Meta line under it | 12/18 sp, `textMuted`, 1 line, ellipsis |
| Label pill | 600 10/14 sp, `textMuted` (selected: `onAccent`) |
| Wheel, selected row | 700 15 sp, `text` |
| Wheel, ±1 rows | 500 13 sp, `textMuted`, drawn at 0.86 vertical scale |
| Wheel, ±2 rows | 500 12 sp, `textMuted` at 45 % alpha, drawn at 0.7 vertical scale |
| Wheel name above the well | Eyebrow style |
| Sheet body sentence (Why they connect) | 400 15/22 sp, names in 700, centred |

### 4.3 Shape and depth

Reuse `FlowRules` and `flowDepth`: depth 1 is cards and small covers, 3 is the cover in front.

| Element | Size (dp) | Radius | Depth |
|---|---|---|---|
| Threads box | full width × 292 (design box 360 × 292, see 4.5) | – | – |
| Centre cover | 100 | 14 (`RADIUS_COVER`) | 3 |
| Orbit cover | 58 | 10 | 1 |
| Selected orbit ring | 3 gap in `rail` + 2 ring in `accent` | – | 1 |
| Label pill | auto × 18, padding 2 × 7 | full | 1 |
| Mosaic | full width − 32 × 166; 4 × 2 grid, gap 6 | big 14, others 10 | big 3, others 1 |
| Wheel well | 1/3 of width − 16 (three wheels, gap 8) × 148 | 16 | 1 |
| Wheel selected row | well width − 8 × 32 | 10 | – |
| Dice button | 44 circle, `raised` | full | – |
| Pick grid (Change sheet) | 4 columns, gap 10 | 10 | 1; selected: ring as orbit |
| Saved row mini stack | 3 covers of 36, offsets 0/8/16 × 6/3/0 | 6 | front cover 3, others 1 |

### 4.4 Icons

24 dp grid, stroke 1.8, round caps and joins, as `ArtIcons.stroked`. Three are new; add them to `ArtIcons` (the paths below are the mockup's symbols written in the file's arc style):

| Name | Paths | Where |
|---|---|---|
| `Person` (new) | `M8.5,8a3.5,3.5 0 1,0 7,0a3.5,3.5 0 1,0 -7,0` · `M5 20c.8-3.800 3.600-6 7-6s6.200 2.200 7 6` | Why they connect: person link and "Also on n more of yours" row |
| `Label` (new) | `M4 12V5a1 1 0 0 1 1-1h7l8 8-8 8z` · `M7.2,8.5a1.3,1.3 0 1,0 2.6,0a1.3,1.3 0 1,0 -2.6,0` | Why they connect: label link and row |
| `Dice` (new) | `M7 4h10a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3z` · `M7.8,9a1.2,1.2 0 1,0 2.4,0a1.2,1.2 0 1,0 -2.4,0` · `M13.8,9a1.2,1.2 0 1,0 2.4,0a1.2,1.2 0 1,0 -2.4,0` · `M7.8,15a1.2,1.2 0 1,0 2.4,0a1.2,1.2 0 1,0 -2.4,0` · `M13.8,15a1.2,1.2 0 1,0 2.4,0a1.2,1.2 0 1,0 -2.4,0` | Shelf mixer: roll the wheels |
| `Place` (exists) | – | Why they connect: studio link and row |
| `Play`, `Plus`, `Close`, `Chevron`, `Server`, `Paths` (exist) | – | buttons and rows as drawn |

Glyph sizes: 18 dp in small buttons and rows, 20 dp in the dice button, 16 dp in the connector badge of the sheet.

### 4.5 Graphics: the Threads constellation (frame T1, board K)

Everything is defined in a **360 × 292 design box** and scaled by `width / 360`, both ways, so the drawing keeps its shape between 320 and 480 dp. Draw it with one `Canvas` for the lines plus positioned composables for the covers and pills, inside a `Box`.

- Centre point: (180, 146). Centre cover 100 dp, centred there.
- Orbit slots: on the ellipse rx 134, ry 112 at angles −150°, −90°, −30°, 30°, 90°, 150° (0° = right, positive = down). Slot 0 is top-left, then clockwise. Orbit cover 58 dp centred on the slot. A link fills the slots in order; empty slots are not drawn (frame T2).
- Lines: from the centre point to the slot centre, drawn **under** the covers (so they appear to come out from behind the centre cover). Line style by link kind:

| Kind | Server path kinds | Stroke | Colour |
|---|---|---|---|
| People | `album_crew`, `album_guests` | solid, 1.4 dp | `chart3` |
| Labels | `album_label` (new, S0b) | dash 5 dp, gap 4 dp | `chart3` |
| Places | `album_room` | dot 1.5 dp, gap 4 dp, round caps | `chart3` |
| Selected (any kind) | – | same dash, 2.2 dp | `accent` |

- Label pill: centred at 60 % of the way from the centre point to the slot. Text from 6.2; at most 12 characters, then an ellipsis. Selected link: `accent` fill, `onAccent` text. The pill is above the covers in z-order.
- One link is always selected while there are links: the first slot when the section loads, or after a filter or centre change.

### 4.6 Graphics: the Shelf mixer (frame M1, board K)

- **Mosaic:** a 4 × 2 grid, gap 6 dp, height 166 dp, 16 dp side margin. The first album takes 2 × 2 (cells 1–4), albums 2–4 take one cell each, and cell 8 shows album 5. When more than 5 albums match, cell 8 carries the 55 % veil and "+n" (n = matched albums − 4). Missing albums leave `raised` cells with no shadow (frame M3). Tap a cover to open the album.
- **Wheels:** three equal columns, gap 8 dp, 16 dp side margin. Each is a well (`surface`, radius 16, depth 1, padding 6 × 4) showing five rows: ±2, ±1, selected. The selected row is 32 dp on a `raised` pill (radius 10); the others are 26 dp. The wheel scrolls with snapping (a `LazyColumn` with a snap fling behaviour, or a draggable offset that snaps to rows). Tapping a ±1 or ±2 row selects it. The list does not loop: the first and last values show fewer neighbours.
- **Summary row** under the mosaic: "{albums} albums · {h} h {m} min" (600 15 sp) over the description sentence (6.4), with the dice button at the right.
- **Buttons:** Play (`accent`, fills the row) and Save (`raised`, `Plus` glyph), 44 dp high, as `FlowRules` capsule buttons.

### 4.7 Motion

No looping motion anywhere. One-shot transitions only, each 250 ms `FastOutSlowInEasing`, and none under the system's reduce-motion setting (follow the existing Flow check):
- Threads: on a centre change, the old orbit covers fade out and the new ones fade and scale in from 0.92. The selected ring and pill change colour without animation.
- Mixer: the mosaic crossfades when a new result arrives; the wheel's snap is the scroll physics, not an animation of ours.

## 5. Threads: behaviour (frames T1 to T5)

### 5.1 The centre

- Default: the first album of the Recent shelf (`repo.shelf(Shelves.Recent, 20)`, which `FlowHome` already loads) that has an `id`. If Recent is empty, the first of Frequent. If both are empty, the section is not drawn.
- **Change** opens the pick sheet (frame T4): the themed `ModalBottomSheet`, title "Start from" (700 20 sp), `FlowTabs` "Played lately | Most played" (Recent and Frequent shelves, already loaded), a 4-column grid of up to 8 covers, and the line "Threads start from an album you own. Pick one; it is remembered until you change it." Tapping a cover sets the centre and closes the sheet.
- The chosen centre is remembered in the same preferences file as the Home tab (`FlowHome`'s `PREFS`), key `threads_centre`, holding album id, name, artist and artwork URL. "Centre" on a link and "Centre here" in the sheet also store it.

### 5.2 The links

- For a centre with Navidrome album id `id`, read four album path kinds **in parallel** with `repo.albumPaths(kind, id)` and `toAlbumAnswer()`: `StudioCrew` (`album_crew`), `GuestList` (`album_guests`), `SameRoom` (`album_room`) and the new `SameLabel` (`album_label`, S0b). That is four calls per centre, made once per centre and kept in memory for the session (key = kind + album id). It never makes one call per orbit cover.
- Keep only steps with `owned == true` and a non-null `albumId`, other than the centre itself. One album reached by several kinds becomes **one link** carrying all its reasons; its kind for drawing is the first in the order People (crew, then guests), Labels, Places.
- **All:** pick up to six by round-robin across People, Labels, Places, keeping server order inside each kind, so one kind cannot fill the ring when another has links. **People / Labels / Places:** up to six of that kind in server order.
- A kind whose read fails is left out quietly when another kind succeeds. If all four fail, show the error state (5.5).
- Put the selection, the pill text and the slot geometry in `FlowThreadsRules` (pure functions) so they are tested without Compose.

### 5.3 The selected link (row under the filter, frames T1, T2)

- Title: "{album} · {artist}". Meta: the short reason (6.2), for example "Same producer: Tim Friese-Greene", "Same label: Polydor, 1994", "Recorded at Wessex Studios".
- **Centre** (text button, `accent`): makes this album the centre.
- **Play** (`accent` capsule): `PlayActions.playAlbum(albumId)`.
- Tap an orbit cover: select it. Long-press: open the album page. Tap the selected cover again: open the album page.

### 5.4 Why they connect (frame T3)

Opens on a tap on a line or a pill (give each line a 24 dp wide touch band along its length, and the pill its own target, at least 48 dp tall).
- Sheet title row: eyebrow "Why they connect", `Close`.
- The two covers (92 dp, radius 12, depth 1) joined by a 70 dp `accent` line with a 30 dp `accent` circle carrying the kind's icon (`Person`, `Label` or `Place`) in `onAccent`.
- The sentence: the first reason's `text` from the server (`AlbumStepReason.text`), names in bold where the reason gives `via` and `anchor`.
- A `FlowGroup` with one row per **other** reason between the same two albums (icon tile, the reason's eyebrow from `reasonEyebrow(code)`, the sentence, chevron). The last row is "Also on {n} more of yours" when the same `via` reaches more owned albums in that kind's answer. It opens the existing album Paths sheet on the centre album at that kind's tab.
- Buttons: **Play the thread** (`accent`): play the centre album, then queue the linked album (`playAlbum(centre)`, `queueAlbum(linked, next = false)`). **Centre here**: makes the linked album the centre and closes the sheet.

### 5.5 States (frame T5)

| State | Drawn |
|---|---|
| Loading | Centre cover drawn at once (from the shelf); six `raised` 58 dp slots, no lines, no pills; filter and row hidden |
| No links in any kind | Centre cover, the six slots, heading "No links for {album} yet", text "The store has no credits, label or studio for this album. Ask it to read them, or start from another album.", buttons **Update the store** (`repo.requestStoreUpdate("album", id, byMbid = false)`, the same call as `ui/common/RequestUpdate.kt`) and **Change** |
| Filter with no links of that kind | The centre and a one-line note under it: "No {people / label / studio} links for this album." The filter stays |
| All four reads failed | The centre, the line "Could not read the knowledge store." and **Try again** |
| Paths not available (`repo.pathsAvailable()` false, cache-only mode) | Section not drawn |

## 6. Shelf mixer: behaviour (frames M1 to M3)

### 6.1 Wheels and values

| Wheel | Values (in order) | Rule sent (none for Any) |
|---|---|---|
| Era | Any, 50s, 60s, 70s, 80s, 90s, 00s, 10s, 20s | `year at_least 1990` and `year at_most 1999` (two rules) |
| Genre | Any, then the top 8 of `FlowHomeData.genres` by `albumCount` (already loaded for the Genres module) | `genre contains <name>` |
| Played | Any, Never played, Not in a year, Rarely, Favourites | Never played: `plays equals 0`; Not in a year: `played_days_ago at_least 365`; Rarely: `plays at_most 2`; Favourites: `plays at_least 10` |

Match is `all`, order `random`, limit 250. The defaults on first use are Any, Any, Not in a year. The last wheel positions are remembered in Home's `PREFS` (key `mixer_wheels`). If a remembered genre is no longer in the top 8, fall back to Any.

### 6.2 Short reason texts (Threads pills and meta lines)

| Kind | Pill | Meta line |
|---|---|---|
| Crew | the credit role, capitalised ("Producer", "Engineer", "Mixing"), else "Crew" | "Same {role}: {via}" |
| Guests | the instrument or role ("Bass", "Vocals"), else "Guest" | "{via} plays on both" |
| Label | the label name | "Same label: {label}{, year}" |
| Room | the studio name without "Studios" | "Recorded at {studio}" |

The role comes from the reason's `credits` (`PathCreditFact.role`, else `relation`), and the name from `via.name`. Keep this table in `FlowThreadsRules.pill()` and `.meta()`.

### 6.3 Reading the result

- Every wheel change waits **350 ms** after the wheel settles, then calls the preview endpoint (S0a) once. A call still in flight is cancelled when a newer one starts.
- While a call is in flight, the previous mosaic stays at 50 % alpha. There is no spinner.
- `seed` = the day number (epoch days), so the same wheels show the same mosaic all day. The dice picks a random value on each wheel (never all Any) and a random seed.

### 6.4 The description sentence

Built in `FlowMixerRules.describe()` from the wheels. Era as "90s", genre lower-case, then the played clause:

| Played | Clause |
|---|---|
| Any | (none) |
| Never played | "you have never played" |
| Not in a year | "you have not played in a year" |
| Rarely | "you rarely play" |
| Favourites | "you play most" |

Examples: "90s post-rock you have not played in a year", "Jazz you play most", "80s albums you have never played", "Everything on your shelves" (all Any). The same sentence, cut to 100 characters, is the saved playlist's name.

### 6.5 Actions

- **Play:** play the albums in mosaic order: `playAlbum(first)`, then `queueAlbum(each next, next = false)`, at most 24 albums. Whole albums are played, including songs that did not match the Played rule (the mixer is about albums; decided by default, owner open point O1).
- **Save:** `PUT /api/playlists/smart/{new lowercase UUID}` with the rule set and the sentence as the name. The snackbar says "Saved as {name}". Store the first three cover URLs on the device under the rule id (prefs key `mixer_covers_<id>`) for the Saved sheet.
- **Saved** (header link) opens the Saved sheet (frame M2): `GET /api/playlists/smart`. Each row shows the three stored covers when the device has them, else a `FlowIconTile(Dice)`, then the name and "{n} rules · saved {date}". The round Play button runs the preview with that rule set and plays it as above. Tapping the row loads its rules onto the wheels **when they fit** the table in 6.1 exactly; otherwise it plays. Long-press offers Rename (PUT with the new name) and Delete (`DELETE`, with the themed confirm sheet). The line under the list reads: "Saved mixes are smart playlists on the server, so they also appear on the Mac."
- **Nothing matches** (frame M3): the mosaic cells turn `raised`; the heading is "Nothing on your shelves matches". One chip per entry of the server's `loosen` list that has albums, worded "{Wheel}: Any · {n} albums" (Era's two rules count as one wheel). Tapping a chip sets that wheel to Any. Play and Save are disabled at 40 % alpha.
- **Error:** the mosaic cells turn `raised`; the line "Could not read your shelves." with **Try again**.

## 7. Server additions

### 7.1 S0a: smart-playlist preview, `POST /api/playlists/smart/preview`

- Route in `app/api/smart_playlists.py`; body builder in a new `intelligence/api/smart_preview.py`, which reuses `engine.validate_rule_set`, `engine.evaluate`, `songs_from_subsonic` and `build_insights`. **Nothing is stored**, no provider call, rule content never logged (the module's existing rule). Not in `navidrome_server.py` (D-016).
- Request: the PUT body shape (`name` optional here, default "Preview"; `match`, `rules`, `order`, `limit`) plus `seed` (int, default 0) and `albums` (1 to 60, default 24).
- Evaluate over the songs, then group the matching songs by `albumId`, keeping the evaluator's order: an album's position is that of its first matching song. Answer:

```json
{
  "matched_songs": 131, "matched_albums": 14, "duration_sec": 34800,
  "albums": [{"album_id": "…", "album": "…", "artist": "…", "year": 1996,
              "songs": 9, "duration_sec": 2830, "artwork_url": "/api/owned/artwork/<coverArt>"}],
  "loosen": [{"rule": 2, "matched_albums": 6}],
  "unfinished": [], "missing_data": [], "songs_considered": 23110, "evaluated_at": 1763200000.0
}
```

  `duration_sec` sums the matching songs' Subsonic `duration`. `artwork_url` uses `discovery.search.query.ARTWORK_PATH` with the song's `coverArt` (the same form as `dashboard_sections.py`). `loosen` gives, for each rule index, the matched album count with that one rule removed, and only when the full set matched fewer than 5 albums (otherwise `[]`).
- **Song-list cache:** `_fetch_songs` pages the whole Navidrome list on every call, which is too slow for a wheel. Keep the raw `search3` song list in the route module for **120 s** (one shared copy, guarded by the existing `_LOCK` or its own lock, refreshed on expiry). The preview uses it; `result_smart` may keep reading fresh. Keep the raw items too (album name, artist, duration, coverArt are not in the evaluator rows).
- Errors: invalid rule set `400 {status: "rejected", errors}` (the PUT's shape); Navidrome failure `502 "Could not read the Navidrome song list."`; anything else `502 "Could not preview the smart playlist."`
- Tests (new `tests/test_smart_preview.py`, direct import of the builder plus the route with a fake librarian): grouping and order; `seed` repeats the same order; `albums` cap; `duration_sec`; `loosen` only under 5 albums and the right counts; no write to the store; the cache serves a second call inside 120 s without paging again and pages again after it; 400 and 502 shapes. Check whether `plays equals 0` matches songs with no `playCount` (absent value). If it does not, say so in the PR and in 6.1; do not change the evaluator in this step.
- Document the endpoint under "Smart playlists" in `docs/SERVER_V2_CONTRACT.md` and add a fixture `smart_playlist_preview.json`.

### 7.2 S0b: album path kind `album_label`

- In `intelligence/graph/album_paths.py`, add `album_label` to `ALBUM_PATH_KINDS`. Its stops are **owned albums** that share a label (or a related label, as `label_path` reads it) with the start album's releases. Stop and reason shape as `album_room`: `navidrome_id`, owned flag, year, and a reason with code `same_label` (and `related_label`), `via` = the label entity and `anchor` = the start album, sentence "Also on {label}, like {album}." Order: same label first, then by year distance from the start album. Same caps as the other album kinds.
- Reuse the `label_path` SQL in `intelligence/graph/paths.py` where it fits. Do not change `label_path` itself.
- `path_coverage.py`: add the kind if album kinds are listed there.
- Tests: next to the existing album path tests (find them from `album_paths.py`'s imports, not by grep): owned-only stops, the start album excluded, related labels, the reason shape, an album without a label gives an empty answer.
- Android must not show a new tab in the album Paths sheet for this kind (5.2 uses it only on Home). Add `AlbumPathKind.SameLabel("album_label", "Same label")` and check that `AlbumTab` does not list it.

## 8. Android code layout

| File | New or changed | Holds |
|---|---|---|
| `ui/common/ArtIcons.kt` | changed | `Person`, `Label`, `Dice` (4.4) |
| `model/AlbumPaths.kt` | changed | `AlbumPathKind.SameLabel` |
| `model/ShelfMix.kt` | new | `MixPreview`, `MixAlbum`, `MixLoosen`, `SavedMix` data classes and their parsers (`parseMixPreview`, `parseSavedMixes`) |
| `data/Repository.kt` | changed | `mixPreview(ruleSet: JsonObject): MixPreview`, `savedMixes(): List<SavedMix>`, `saveMix(id, ruleSet)`, `deleteMix(id)`; the cache-only mode throws `CacheMiss` like the other reads |
| `ui/home/FlowThreadsRules.kt` | new | link building (5.2), slot geometry (4.5), `pill()` and `meta()` (6.2), state choice (5.5) |
| `ui/home/FlowThreads.kt` | new | `FlowThreadsSection`, constellation, filter, selected row, pick sheet, Why they connect sheet |
| `ui/home/FlowMixerRules.kt` | new | wheel values, rule set from wheels and back (`fits`), `describe()`, mosaic cells, duration text |
| `ui/home/FlowMixer.kt` | new | `FlowMixerSection`, `FlowWheel`, mosaic, Saved sheet |
| `ui/home/FlowHome.kt` | changed | the two modules and the wide-screen split (3) |

All new files belong to modules that `ARCHITECTURE.md` already maps (the Android client row, `intelligence/` for the API builder), so the map does not change. If a reviewer finds otherwise, add one line.

Accessibility:
- Each orbit cover is a button described as "{album} by {artist}. {meta}. Selected" (the last word only when it is). Traversal goes centre first, then slots clockwise from the top left.
- Lines and pills are decorative to TalkBack. The sheet is reached from the selected cover's custom action "Why they connect".
- Each wheel is one adjustable element: "Era, 90s", with custom actions "Next" and "Previous", and the up and down keys move it.
- The mosaic covers are buttons ("{album} by {artist}"). The "+n" cell reads "{n} more albums".
- Touch targets are at least 48 dp. Text scales to 200 % without clipping: titles wrap to two lines at most, and the wheel rows grow.

## 9. Build steps (one PR each, in order)

Each step: branch from current `main`, Flow only on Android, other themes unchanged. **Filtered tests only.** For Python, the step's own tests plus the touched module's existing tests. For Kotlin, JDK 17: `FlowTest`, `ExistingLayoutsTest`, `FlowHomeRulesTest`, `HomeArtistsTest` plus the step's new tests. Record the PR, squash and tests in `ACTIVE_WORK.md` and `PROJECT_LOG.md`. Compare with the named frames and say plainly when nothing was seen on a device.

| Step | What | Frames | Tests | Model |
|---|---|---|---|---|
| **S0a** | Server preview endpoint and song-list cache (7.1), contract text, fixture | – | `tests/test_smart_preview.py` | Sonnet, high |
| **S0b** | Server `album_label` kind (7.2) | – | album path tests | Sonnet, high (or a stronger model if the label SQL does not reuse cleanly) |
| **H1** | Android data and rules: `ArtIcons` additions, `SameLabel`, `ShelfMix.kt`, the Repository calls, `FlowThreadsRules`, `FlowMixerRules`. No UI | – | new `FlowThreadsRulesTest` (round-robin, dedupe, owned-only, centre excluded, filter, pill and meta text, 12-character cut, slot positions) and `FlowMixerRulesTest` (each wheel value's rules, Era's two rules, `fits` both ways, `describe()` table, mosaic cells and "+n", duration text), parser tests for the preview and list JSON (from the S0a fixture) | Sonnet, medium |
| **H2** | Threads section: constellation, filter, selected row, pick sheet, states, placement on Home and the wide split | T1, T2, T4, T5 | rules tests above stay green; add any new pure helper to `FlowThreadsRulesTest` | Sonnet, high |
| **H3** | Why they connect sheet, Play the thread, Centre here, the Paths-sheet hand-off | T3 | `FlowThreadsRulesTest` (other-reasons list, "Also on n more" count) | Sonnet, medium |
| **M1** | Shelf mixer: wheels, mosaic, summary, dice, Play, nothing-matches and error states | M1, M3 | `FlowMixerRulesTest` (dice never all Any, debounce is a constant, seed = epoch day) | Sonnet, high |
| **M2** | Save, Saved sheet, rename and delete, stored covers | M2 | `FlowMixerRulesTest` (saved row subtitle, load-or-play choice) | Sonnet, medium |
| **C** | Closeout: delete anything unused, mark the plan done in `ACTIVE_WORK.md`, `PROJECT_STATUS.md` line | – | – | Haiku, medium |

Each step's acceptance:
- **S0a and S0b:** CI green, contract text updated, no change to existing responses.
- **H1:** nothing visible changes.
- **H2:** frames T1, T2, T4 and T5 on warm white and on one night palette, with four reads per centre and none per cover.
- **H3:** frame T3; the Paths sheet opens on the right tab.
- **M1:** frames M1 and M3; one preview call per settled change; the mosaic stays the same through the day.
- **M2:** frame M2; a mix saved on the phone shows in the Mac's Smart Playlists.
- **C:** the owner's phone check of both sections on two palettes.

## 10. Open points for the owner

- **O1. Play in the mixer plays whole albums.** The Played wheel matches songs, but Play queues the albums those songs are on. The alternative is to queue only the matching songs, which needs song objects for up to 250 ids. Default: whole albums.
- **O2. Favourites means 10 plays or more**, and Rarely means 2 or fewer. Default as written; the thresholds live in `FlowMixerRules`.
- **O3. The default centre** is the most recent album played (Recent shelf); the proposal mockup said "most played this week", which the app has no figure for. Default: Recent.
