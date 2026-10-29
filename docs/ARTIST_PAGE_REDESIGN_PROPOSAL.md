# Artist page redesign: contract proposal (draft for owner approval)

Status: **draft, not approved, nothing built.** Scope is the library artist page (`SEARCH_CONTRACT.md` section 14). Section 3.3 and 14.1 stay authoritative until the owner approves this text; on approval the additions move into the contract.

## 1. Layout requested by the owner

Top to bottom:

1. **Hero.** A large artist photo with the artist name set large above/over it. One to three genre tags under the name, in the place the reference shows "Artist". Under the tags, the line "N albums in your library" (for an artist the library lacks: "Not in your library").
2. **Top Songs**, to the right of the hero, ranked by Last.fm or ListenBrainz.
3. **Bio** below the hero.
4. **Owned albums** as cards, each with a check mark.
5. **Missing albums**, a list ranked by popularity.
6. **Similar artists** as circles.

Removed from the artist page: the "Library" heading and the "Back" button, and the "Only show albums in your library" toggle (owned and missing albums now have their own sections). Decision recorded: a small icon-only back link stays, overlaid on the photo corner, with an accessible name ("Back") and no visible text. Browser Back keeps working through the address hash (LIB-04).

Unowned artist (opened with `?name=`): same layout; the owned-albums block is hidden, not shown empty; Missing albums is the main list; the count line reads "Not in your library".

## 2. Data already available (no change)

| Need | Section | Notes |
|---|---|---|
| Name, count | `artist` | `album_count`, `owned`. |
| Genre tags | `tags` | Page shows the first three. Server already orders library genre first. |
| Bio | `bio` | Unchanged. |
| Owned album cards | `owned_albums` | Has `artwork_url`, `id`, `year`, `key`. |
| Missing albums, ranked | `missing_albums` | Sorted by listen count, capped at 50. The page shows the top ones with "Show all". |
| Similar artist circles | `similar` | Has `artwork_url`; circles reuse the existing artist-image fallback. |
| Photo | `GET /api/artist-image?name=` | Deezer photo. See open item 2. |

The `albums` section (owned and unowned together) is no longer used by the artist page. It stays in the contract for other callers.

## 3. New: `top_songs` section (needs approval)

No endpoint or section returns an artist's top songs today. Proposal:

- **Section name:** `top_songs`, same envelope as the other sections (`available`, `complete`, `reason`, `items`), streamed when final, completion order like `albums`, `tags` and `similar`.
- **Item schema:**

| Field | Type | Rule |
|---|---|---|
| `rank` | int | 1-based. |
| `name` | string | Song title. |
| `listen_count` | int or null | Count from `source`. `null` when the source gives none. |
| `source` | string | `listenbrainz` or `lastfm`. One scale per list; counts from the two sources are never mixed (the rule `albums` already follows). |
| `recording_mbid` | string or null | When the source supplies it. |
| `owned` | bool | True when the owned index has a song with the same normalized title by this artist (owned artists only; `false` for others). |
| `album` | string or null | Album name when the source supplies it. |

- **Source order:** ListenBrainz top recordings for the artist MBID first (the artist MBID is already resolved for `missing_albums`); Last.fm `artist.getTopTracks` when ListenBrainz returns nothing or there is no MBID. Both are to be confirmed against the live services before build; the contract records the result.
- **Cap:** 10 items stored, the page shows 5 with "Show all".
- **Caching:** 24 hours (same class as `missing_albums`), keyed by artist MBID or normalized name.
- **Deadline:** the existing 8 s page deadline. On expiry: `available: true, complete: false, reason: deadline` with what exists.
- **Capabilities:** `sections.top_songs` joins the vocabulary of section 3.6; reasons as for the other network sections.
- **Placement:** new module (D-016: no additions to `navidrome_server.py`), with direct-import tests: schema, ordering, source fallback, no mixed scales, `owned` matching, deadline, cache hit.
- **Song rows show** rank, title, listen count and a check mark when owned. No play button (no playback exists; `PRODUCT.md`).

## 4. Open items for the owner

1. Approve section 3 (the `top_songs` section), or amend it.
2. **Photo size.** The Deezer photo is requested at about 400 px today (`sizedArtwork(..., 400)`). A hero at desktop width needs about 1000 px. The proposal is to request Deezer's largest size for the hero only. Artists with no Deezer photo get a typographic hero (large name on a flat surface), not a placeholder image.
3. Count wording: "12 albums in your library" is taken from `artist.album_count`.

## 5. Build plan after approval

1. Backend: `top_songs` module, wiring into the artist route (only the minimal hook outside the new module), tests, contract text moved into `SEARCH_CONTRACT.md` section 14.
2. Frontend (`index.html`, `app.css`, `app.js`): new artist-page markup and styles, replacing `renderArtist` and `applyArtistSection` paths for the retired toggle and albums list; UI contract test file for the artist page (like `test_artist_deep_dive_ui_contract.py`).
3. Checks: focused tests only (owner rule), the `impeccable detect` pass on changed UI files, a Web Interface Guidelines review of the changed files, and the manual browser checklist in `LOCAL_UI_TESTING.md` at desktop and phone widths. Browser results are recorded only if actually performed.
4. Branch from `main`, PR, CI on the final head. Contract text and this proposal's closeout go to `PROJECT_STATUS.md` and `PROJECT_LOG.md`.

## 6. Departures from the archived design system (owner-directed)

The layout the owner asked for conflicts with three rules in `archive/redesign/DESIGN_SYSTEM.md`: no hero banner, no gradients, and no heading larger than the 30px page head. The artist page departs from them on purpose: a large photo hero, a large artist name (up to 6.5rem), and one dark scrim (`.artist-stage::after`) so the name stays legible on a light photo. The scrim is the only gradient in the stylesheet, and `test_flat_surfaces_ui_contract.py` allows only that one. Everything else on the page uses the existing tokens, flat surfaces, and the green check mark.
