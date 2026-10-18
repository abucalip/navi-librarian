---
version: 1
slug: "app-templates-index-html"
primary_target: "app/templates/index.html"
related_targets: []
---

# Surface brief: Librarian app shell and all pages

Scope and visitor mode: Operate. The whole single-page app (`app/templates/index.html`, `static/app.css`, `static/app.js`), every page and the album modal. Login is a follow-on surface that inherits the same world.

Audience, job, task: one self-hosting collector deciding what to add next and tracking requests. Frequent, desktop-first, phone occasionally. Artwork is the dominant content; acquisition states must be trustworthy.

Constraints: API and auth contracts unchanged (no invented fields); no playback; hero banner, right rail and soft rounded cards were NOT selected by the owner; icon + label sidebar was selected. Rank numerals only where the API supplies a real order (`discovery_score`, list order).

Unresolved decisions: self-hosted fonts and icon sprite (new vendored assets); fate of the 3D dashboard ring and the goo nav blob; whether a right rail returns on wide screens for live acquisitions.

## Direction contract

THESIS: The Librarian is a weekly chart rundown for your own collection: ordered, scannable rows led by big condensed rank numerals, artwork thumbs and quiet metadata. It refuses the universal card grid and the "popular releases" carousel.

OWN-WORLD: Warm ink ground (#141211) with a darker rail; off-white type; highlighter yellow for primary action and selection; chart red for numerals, rail marker and heading rule (never the sole carrier of an error); condensed display face for page heads and numerals, humanist news-grotesque for UI, mono only for technical metadata (bitrate, format, path). Recognisable with content removed by the numeral column, the red rule under each head and the yellow selection bar.

STORY: The owner opens Discover, sees what to add in ranked order with why, taps Get, watches an honest pending then confirmed state, and later finds the request in Acquisitions as a status row with real progress.

FIRST VIEWPORT: Left rail 232px with line icons and labels in three groups (Discover, Collection, System); top bar with breadcrumb and global search; page head in the display face with a 3px red rule; below it a toolbar and a ranked list of rows (numeral, 64px artwork, album + artist, quiet metadata, Get at the right edge). Primary action Get sits at the row's right, yellow. No hero banner.

FORM: Chart rundown list as the primary composition, with artwork tiles retained for Dashboard picks and genre rows; ordered list position 1 of the grounded candidates, assigned roll position 5 of 7; seed:af93e45ae0d8c06b.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
