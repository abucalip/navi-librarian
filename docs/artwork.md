# Artwork proposal: the album as a physical object

**Status:** draft for owner review. Slice 0 (probe, then the caps, TTLs and rate limits) is done and recorded below; nothing else is built.
**Date:** 2026-11-10
**Context:** MusicBrainz and the Cover Art Archive (CAA) hold more than a front cover for many releases: backs, booklet scans, disc labels, trays, spines, obi strips, posters and studio photos. Example: <https://musicbrainz.org/release/1edd139d-4779-4057-8e12-13c783674f0d/cover-art> (Somethin' Else). This proposal adds those images to the Android and macOS clients through the Librarian server. Related: [Album paths proposal](ALBUM_PATHS_PROPOSAL.md) (path rows, Same Room), [macOS design](../macos/DESIGN.md), [Android design](../android/DESIGN.md).

## Decisions recorded (owner, 2026-11-10)

- **Cache:** up to **1.5 GB** of resized per-album images on the server. Full-resolution images are fetched **on demand** (when the owner zooms) and cached under the same budget.
- **Match:** by **MusicBrainz release group**. Use **all images of every release in the group**, not only the release in the library.
- **Per-type slots (owner, 2026-11-10):** the merged index stays the source of truth. A derived view picks one best image per type (Front, Back, Spine, Obi, Medium, Tray and so on) for the flip cover, the disc and the grid, preferring the owned release's own image and falling back to another edition only when that type is missing, labelled with the edition. **Booklet is the exception:** it is one ordered set of pages taken from a single release (the one with the most pages), never mixed across editions. See "Per-type slots" under Server design.
- **No OCR, no text recognition, no automatic credit linking.** That is LLM/ML-grade capability and is outside the Librarian's scope. Booklet pages are shown as images only. Any link from a page to a person or credit is out of scope.

## Rules (inherited)

- **No third-party runtime asset requests from clients** ([macOS design](../macos/DESIGN.md)). Clients only talk to the Librarian; the server talks to MusicBrainz and the CAA.
- Missing data is `not_loaded` or `empty`, never a statement about the album. An album with no images shows nothing extra (no placeholders, no empty tabs).
- Taste or play data must not influence which image is chosen.
- Image text (comments, types) is third-party data: show as plain text, never as markup.
- Pick the artwork by explicit rules (tag, size, approval), not by similarity or popularity.

## Data source

- **Release group to releases:** a MusicBrainz release-group lookup with its releases gives every edition (original, reissue, Japan, vinyl, deluxe).
- **Per release:** the CAA release index lists images with `types[]` (Front, Back, Booklet, Medium, Tray, Obi, Spine, Liner, Sticker, Poster, Track, Other, Raw/Unedited, Watermark), `comment`, `approved`, `front`, `back`, and thumbnails at 250, 500 and 1200 px, plus the original file.
- The CAA release-group endpoint returns only one release's images, so the aggregate is built by the server: one index fetch per release, merged.
- ~~**Not verified yet:** index completeness, size distribution, and the Somethin' Else group.~~ Measured by the probe, see "Probe results (slice 0)". The caps, TTLs and rate limits are set from those results in "Limits (set from the probe)".

### Probe results (slice 0, 2026-11-10)
Sample: 30 release groups (Somethin' Else first, the rest a seeded random sample of owned releases resolved to their group). Index JSON only; no image bytes downloaded; 1 request per second per host. Probe cap of 60 releases per group never triggered. The probe script is `scripts/artwork_probe.py` (PR #944, merged).

- **Coverage:** all 30 groups have at least one image; 21 of 30 have a type other than Front. The 9 Front-only or untyped groups are small (1 to 5 releases). Groups with 6 or more releases mostly carry Back, Booklet, Medium and Spine, and the largest also Obi, Tray and Sticker.
- **Releases per group:** median 5.5, p90 23, max 59.
- **Unique images per group:** median 7.5, p90 133, max 341. Somethin' Else: 37 releases, 132 unique images.
- **Time to index a group at 1 request per second:** median 10 s, p90 71 s, max 120 s.
- **Type mix (unique images, all groups):** Booklet 564, Front 322, Medium 210, Back 167, untyped 130 (about 8%), Spine 79, Other 47, Obi 45, Tray 44, Raw/Unedited 42, Sticker 21, Matrix/Runout 19, Liner 14, Track 5, Watermark 5, Poster 4, Top 1, Bottom 1. Booklet pages are the largest share.
- **Failures:** 21.5% of release indexes were empty (404), 0.3% errored; MusicBrainz had no failures.
- **Reading:** the placeholder caps (20 releases, 80 images) would truncate about 3 of 30 groups on releases and 9 of 30 on images. Because the median group is small and the tail is large, caps should limit what is served and shown, not stop the index fetch for heavy groups. Empty results are common, so they need the shorter TTL. Untyped images must be handled by clients. The sample is small (30 groups). The final numbers are set in the next section.

### Limits (set from the probe, 2026-11-10)
These are the numbers slice 1 builds to. They come from a 30-group sample, so each is a starting value with the evidence beside it; slice 1 records real numbers in `PROJECT_LOG.md` and may move them with owner approval.

**Principle:** caps limit what is *stored and served*, never whether the index is fetched. The median group is small and the tail is large, so a heavy group is indexed in full and then trimmed on the way out.

| Limit | Value | Evidence |
|---|---|---|
| Releases fetched per group | **60** (hard ceiling, owned release first, then newest first) | Max seen 59; the probe's 60 cap never triggered. Replaces the placeholder 20, which would have cut about 3 of 30 groups. |
| Images stored per group (full index) | **400** | Max seen 341; p90 133. Entries are small JSON, so storing them all costs little. Replaces the placeholder 80, which cut 9 of 30. |
| Images served in the index response | **250**, with `truncated: true` and `truncated_reason: "served_cap"` past that | Above p90 (133) with room; only the heaviest groups trim. Kept in this order: slot winners, booklet pages, then the rest by approved, larger side, date, image id. |
| Booklet pages shown | **100** from the single best release | Booklet is the biggest type (564 of about 1,900 unique images) but pages per release were not measured; slice 1 records the real maximum. |
| Index build time bound | **180 s** per group, then stop with `truncated_reason: "time"` and keep what was fetched | Max seen 120 s at 1 request per second, p90 71 s. A time-stopped build resumes from the per-release cache, not from zero. |
| Releases per group that are skipped | Releases MusicBrainz reports with no cover art, if the release-group response carries that count; otherwise none | 21.5% of release indexes were 404. Slice 1 checks whether the batch lookup exposes the count; if it does, those requests are never sent. |

**Fetching.** Index builds run as a background job, never inside a client request. A request for an album whose index is not built returns `not_loaded` and starts (or joins) the job; the client asks again. The release list comes from one MusicBrainz release-group lookup (a batch form, per the provider-request rule). The CAA has no batch form for release indexes, so there is one request per release; that is the only single-lookup fallback here.

**Cache TTLs.** The unit cached is the per-release index, so a group rebuild after a TTL expiry or a time stop re-fetches only what is stale. The group view is derived from those.

| Result | TTL | Why |
|---|---|---|
| Release index with images | **30 days** | Uploads to existing releases are rare. |
| Release index empty (404) | **7 days** | Common (21.5%) and cheap to repeat; short enough that a new upload appears within a week. |
| Group with no images at all | **7 days** | Same reason; the group view follows its releases. |
| Time-stopped or partial group | **1 day** | Finishes on the next build from the per-release cache. |
| Error or `unavailable` (timeout, 5xx, 429) | **15 minutes**, then 1 hour after a second failure in a row | Never stored as `empty` (0.3% errored); a failure must not read as "this album has no images". |

Add up to 10% random jitter to each TTL so a first warm-up does not expire all at once.

**Rate limits.**
- **One shared queue per host at 1 request per second**, covering MusicBrainz, the CAA index host and the image hosts, and all artwork work (foreground, warm-up and zoom). This matches the existing MusicBrainz client and the probe, which ran clean at that rate (no MusicBrainz failures).
- **Priority:** an album the owner has just opened goes ahead of any warm-up work. Warm-up never delays a foreground request by more than the request in flight.
- **Image bytes:** one download at a time per host, with the same 1 request per second start rate. The probe did not download images, so this is a conservative start, not a measured limit.
- **Warm-up budget:** at most **600 provider requests per day** (about 60 median-sized groups at 10 s each, or about 8 of the p90 groups). It indexes and fetches thumbs of slot winners only; display and full sizes load on open. It stops at the 1.5 GB budget and pauses on any `unavailable` result.
- **Backoff:** on 429 or 503, honour `Retry-After` when present, otherwise wait 60 s, doubling to a 15-minute ceiling.

**Size budget (estimate, not measured).** Typical sizes are about 15 KB for a 250 px thumb and about 80 KB for a 640 px display image, so a median group (7.5 images) at display size is under 1 MB and 1.5 GB holds on the order of 2,000 such groups. Full-resolution files are much larger and are the main pressure on the budget, which is why they are fetched only on zoom and evicted first. Slice 1 measures real byte sizes and records them.

## Server design

### Image index (`artwork_index`)
For a release group, the server builds a single list: one entry per image, each with:
- `image_id` (CAA id), `release` (MBID), `edition` label (country, year, format, from MusicBrainz) so the client can say "1999 Japan CD".
- `types[]`, `comment`, `approved`, `width` and `height` if known, and `rank`.
- Duplicate collapse: the same scan attached to several releases appears once, with the list of releases it is on.

Bounds, cadence and TTLs are set in "Limits (set from the probe)": 60 releases fetched, 400 images stored, 250 served, a 180 s build bound, and a `truncated` flag with a reason (`served_cap` or `time`). Fetch cadence is 1 request per second per host. Results are cached per release, with shorter TTLs for empty and failed results.

### Choosing the "best front"
Deterministic order: approved, Front type, larger side, then release date. This feeds idea 7 (grid fallback) and replaces the fallback problem that PR #683 worked around: **never fall back to an artist photo**.

### Per-type slots
A derived view over the merged index (not a replacement for it). For each type the server picks one best image by the same deterministic order as the best front: approved, larger side, then release date; ties break on image id. Rules:
- Prefer the owned release's own image for a type; use another edition only when the owned release has none, and mark it with that edition's label.
- Booklet is a set: the ordered pages of the single release with the most Booklet pages. Pages are never mixed across releases.
- Untyped images are not in any slot; they appear only in the full index.
- Types outside the slot list (Other, Raw/Unedited, Matrix/Runout, Watermark, Liner and so on) stay available in the full index for the artist collage, liner note and similar ideas.
- Slot choice never uses taste or play data.

### Image cache and endpoints
- Resized per-album images (sizes: 250 px thumb, 640 px display; the CAA serves 250, 500 and 1200 px, so slice 1 checks whether 640 is resized by the server or the nearest CAA size is used) live in a disk cache with a **1.5 GB** budget shared with full-resolution images. Eviction is least-recently-used, with the front cover of each owned album protected from eviction until nothing else is left.
- Endpoints (names to be settled in the contract): `GET /api/artwork/index?rgid=` and `GET /api/artwork/image/{image_id}?size=thumb|display|full`. `full` is fetched on first zoom and stored; later requests are served from disk.
- The server validates the image bytes, rejects non-images and oversize responses, and never follows a redirect to a host other than the CAA and the archive.org hosts that serve its files.
- Access to the endpoints follows the existing session auth; image URLs are not public.
- A background warm-up fills the display size for owned albums slowly, in order of recent listening, and stops at the budget. Nothing is fetched for albums the owner has never opened if the budget is full.

### Owner choice store (edition picker)
A small table keyed by album: `chosen_image_id` for the cover the owner picked. Clients read it from the album payload. Changing it does not affect Navidrome's own artwork unless the owner decides to push it (see open decisions).

### Contract fixtures
Recorded fixtures for `ok`, `empty`, `unavailable` and `truncated`, so both clients decode and test the same shapes, as in the album paths work (PR #931).

## Client ideas

Each idea lists where it lives. "A" is Android, "M" is macOS.

### 1. Flip-to-back cover (A, M)
The album-page cover is a 3D card. Click (M) or swipe (A) flips it to the Back image; Tray and Spine are extra faces if present. A thin Spine strip can sit on the edge of the Zine and Cupertino album headers. With no Back image, the cover does not flip.
- Reduced motion: replace the flip with a cross-fade.

### 2. Digital booklet (A, M)
- **A:** a "Booklet" tab next to Info and Reviews. Pages in a horizontal pager with pinch-zoom (full resolution loaded on zoom). Sticker, Obi and Poster follow the pages.
- **M:** a sheet with a two-page spread, arrow-key paging and a zoom lens.
- Pages are shown in CAA order, grouped by edition when more than one edition has a booklet.
- No OCR, no credit linking, no per-page captions beyond the CAA comment.

### 3. The disc (A, M)
Medium images (vinyl label, CD face) become the Now Playing record. On the Cassette Deck and Tape Deck themes, the label spins; on Cupertino Now Playing the disc slides out from behind the sleeve. Disc label by disc number when the comment or edition identifies it; otherwise the first Medium image.
- Reduced motion: no spin.

### 4. Session slideshow behind lyrics (A, M)
The blurred-artwork Now Playing background (M5 slice 6) becomes a slow drift through the album's session and booklet photos behind the lyric lines, falling back to the blurred cover. Only images sized for display are used; the drift pauses under reduced motion and low-power mode.

### 5. Lock screen and widget (M, A)
The system Now Playing artwork (M5 slice 13) and the Notification Center widget (M6 slice 3) can show the chosen cover. **Alternate sleeves per play is an option**, off by default, because system artwork must stay stable for the player controls.

### 6. Track images (A, M)
Images tagged Track (session sheets, studio track lists) appear as a card in the queue sheet while that album plays. They are shown only when present.

### 7. Edition picker and better grid art (A, M)
- A small stack of covers on the album card shows how many alternates exist. Tapping lets the owner pick which cover the app uses; the pick is stored on the server and used on every screen.
- When no front exists or the library cover is small, the grid uses the best front by the rule above.
- The owner's choice always wins over the automatic choice.

### 8. Artist page collage (M, A)
- **M Zine:** the magazine-cover artist page is a contact-sheet collage of session and band photos from the artist's albums. **M Cupertino:** the artist hero rotates through them.
- **A:** an optional photo strip on the artist page.
- Only the Other, Raw, Liner and Poster types, plus comments that contain words like "session", "studio" or "band" (plain string match; no ML), qualify. Without enough images, the existing artist hero stays.

### 9. Discover and rows (A, M)
Recommendation and New-release rows get a "peek" of up to three thumbnails (Back, booklet page 1, Medium) on hover (M) or when the row is expanded (A). It uses the thumb size only, and fetches only when the row is expanded or hovered, so lists stay fast.

### 10. Paths (A, M)
- **Path row covers:** rows can cycle through the album's alternate covers on hover or long press (extends PR #937).
- **Same Room:** the `album_room` path shows both albums' session photos side by side. This only compares what the images are; the Librarian does not infer anything from them.

### 11. Timeline and Atlas (M)
A Timeline entry unfolds into a filmstrip of its images. Atlas album nodes can show the Medium disc.

### 12. Liner note of the day (A, M)
One cropped image per day (booklet page, session photo or label) on the home screen with "which album?" revealed on tap. The crop is a fixed centre crop chosen by rule; no face detection. Matches the Sticker Wall theme as a peel-off sticker.

### 13. Edition check in Get (A, M)
In Get and Downloads, the pipeline dock shows the covers of the release being fetched, so the owner can see which pressing it is. Read-only; it does not change the download.

### Dropped
- **Printed lyrics toggle from booklet pages:** needs recognising which page holds lyrics. Out of scope with no OCR.
- **Credits linking from the booklet:** out of scope for the same reason.

## Theme and layout notes
- Each theme owns its screens: flip, booklet, disc and collage are themed per theme (Cupertino, Zine, and the Android Brut themes), not one shared widget.
- Android follows the touch and thumb-zone rules; the booklet pager and flip use swipe, not small buttons.
- macOS keyboard and VoiceOver: arrows page the booklet; every image has a text label made from its type and edition ("Back cover, 1999 Japan CD") and the CAA comment when present.

## Slices

0. ~~**Probe (no UI):** a script that fetches the index for 30 owned release groups (Somethin' Else first) and reports releases per group, images per group, type mix, size distribution and failure rates. It sets the caps and TTLs above. No cache writes beyond the scratch folder.~~ **Done 2026-11-10, script merged in PR #944**; caps, TTLs and rate limits set from the results in "Limits (set from the probe)".
1. **Server index and cache:** index builder, image cache with the 1.5 GB budget, endpoints, fixtures, tests.
2. **Client decoders and the image store:** Android and macOS decode the index and load images through the Librarian.
3. **Flip cover, booklet, zoom:** ideas 1 and 2.
4. **Edition picker and grid fallback:** idea 7 (includes the server choice store).
5. **Now Playing:** ideas 3, 4 and 5.
6. **Artist, Discover, Paths, Timeline:** ideas 8 to 11.
7. **Fun and checks:** ideas 6, 12 and 13.

## Who does each step (model and effort)

Models: Fable 5.1, Opus 5.5, Sonnet 5.5, Haiku 5.5. Effort: low, medium, high, xhigh. These are recommendations; any step can go up one level if its tests keep failing.

| Step | Work | Model | Effort | Why |
|---|---|---|---|---|
| Owner decisions | Four open decisions above | Owner | n/a | Policy, not code. |
| ~~0. Probe~~ | ~~Script that samples about 30 release groups and prints counts~~ (done 2026-11-10) | Sonnet 5.5 | medium | One script, no UI, easy to check by reading its output. |
| ~~0. Probe~~ | ~~Reading the results and setting caps, TTLs, rate limits~~ (done 2026-11-10) | Opus 5.5 | high | Judgment from data; the numbers drive every later slice. |
| 1. Server index and merge | Release-group to releases, dedupe, best-front rule, caps, `truncated` | Opus 5.5 | high | Rate limits, partial failure and ordering rules are easy to get subtly wrong. |
| 1. Server cache and endpoints | 1.5 GB budget, eviction, protected fronts, redirect host check, byte validation, auth | Opus 5.5 | xhigh | Security-sensitive (fetching third-party bytes) and concurrency-sensitive. Review with Fable 5.1 at high. |
| 1. Fixtures and server tests | `ok`, `empty`, `unavailable`, `truncated` fixtures; unit tests | Sonnet 5.5 | medium | Mechanical once the contract is fixed. |
| Contract section | Endpoint shapes and fields in the contract docs | Opus 5.5 | high | Both clients depend on it. |
| 2. Client decoders | Android and macOS decoding of the index | Sonnet 5.5 | medium | Follows the album paths decoder pattern (PR #931). |
| 2. Image store | Loading, memory and disk behavior on each client | Sonnet 5.5 | high | Scrolling performance and cancellation matter. |
| 3. Flip cover (A, M) | 3D flip, reduced-motion fallback | Sonnet 5.5 | high | Animation and gesture detail; check on device and in a window. |
| 3. Booklet (A, M) | Pager and spread, zoom with on-demand full resolution | Sonnet 5.5 | high | Gesture and memory handling. |
| 4. Edition picker, grid fallback | Server choice store plus both clients | Opus 5.5 | high | Touches the server, the data model and every screen that shows a cover. |
| 5. Now Playing (disc, slideshow, system artwork) | Themed per theme | Sonnet 5.5 | high | Many themes, each its own layout; the mockups are the spec. Lock screen change: Opus 5.5 at medium, because it touches the player. |
| 6. Artist collage, Discover peeks, Paths, Timeline | Collage rules, rows, path covers, filmstrip | Sonnet 5.5 | medium | Existing screens with small additions. Atlas disc nodes: Sonnet 5.5 at high. |
| 7. Liner note, track images, edition check in Get | Small additions | Haiku 5.5 | medium | Small, well-specified changes; a Sonnet 5.5 review before merge. |
| Docs, log, test-plan entries | PROJECT_LOG, DESIGN files, ACTIVE_WORK | Haiku 5.5 | low | Mechanical writing from merged PRs. |
| Review of every PR | Correctness and regression review | Fable 5.1 | medium | A second model catches what the author model misses. Raise to high for slice 1. |

Rules for all steps: one slice per PR; filtered tests only; the owner's manual checks stay listed as checks, not as claims.

## Tests
- Server: index merge and dedupe, best-front ordering, caps and `truncated`, cache eviction at budget, redirect host check, non-image rejection, `empty` and `unavailable`.
- Clients: decoding of all four fixtures, chosen-cover override, no-image layouts, reduced motion paths.
- Filtered tests only, per the standing rule.

## Risks
- **Coverage:** many releases have only a front cover; most of this appears on a minority of albums. The probe measures this before any UI is built.
- **Cost:** one index fetch per release in a group is many requests for big groups; caps, caching and rate limits apply, and background warm-up is slow by design.
- **Quality:** CAA content is user-uploaded; types and comments can be wrong. Nothing here asserts facts from them.
- **Storage:** 1.5 GB is a hard limit; full-resolution images compete with thumbnails. Protect owned fronts first.
- **Copyright:** images are shown only to the authenticated owner and are not republished.

## Open decisions for the owner
1. Should the edition pick also be written to Navidrome's own artwork, or stay inside the Librarian and clients only? (Default: Librarian and clients only.)
2. Is alternate-sleeve rotation on the lock screen (idea 5) wanted at all? (Default: off.)
3. Should the warm-up run at all, or should images load only on first open? (Default: slow warm-up for recently played albums.)
4. Which themes get the disc and collage first? (Default: Cupertino and Zine on macOS, the current default theme on Android.)
