# Album page redesign: layout record and song-only Get proposal

Status: layout, `genre` and per-track `owned` are **implemented on branch `album-page-redesign`** (contract `SEARCH_CONTRACT.md` section 14.4). The song-only Get in section 3 is a **draft for owner approval; nothing of it is built**.

## 1. Layout requested by the owner

Central large cover; title below it in bold; artist below, regular and slightly smaller; genre and year below that, smaller; description; tracklist with a Get button next to tracks the library does not have; ranked similar albums; similar artists as circles; spacing and alignment as in the reference screenshot.

Decisions carried over from the artist page: no "Library" heading and no text Back button (an icon-only back button), plain-text links and "Read more", the three-line description clamp (six on a phone), numbered rows for ranked lists, one scrim-free flat layout. Owner choices for this page: genre from the library, else the artist's first tag; service links in a quiet row below the tracklist; similar albums keep the server's order with numerals.

## 2. What the page does today

- Tracks carry `owned`; owned tracks show a green check, others show nothing in that column.
- The album-level Get (or owned check) stays on the cover, as before.
- There is no Get on a track, because Get requests a whole album.

## 3. Proposal: Get a single song (not built)

The owner's direction: a Get on a track downloads only that song and imports it into the right folder, following the established protocol.

What exists: acquisition is album-based end to end. `POST /api/acquire` takes artist and album; candidates are grouped by remote folder (ACQ-05); `import_matched_album_files` stages the expected album tracks only, refuses to overwrite, and checks storage identity; dismissal deletes the album's folder (ACQ-04); the monitor shows one card per album. None of that models a single file.

What a song-only Get needs, each part to be approved before building:

1. **Request.** `POST /api/acquire/track` with artist, album, title, track number (and the album year/MBID). Server-side only, like Get today; the browser never reports success before the server confirms.
2. **Search and choice.** An slskd search for the song (artist + title, bounded query variants as in ACQ-07), candidates restricted to single audio files that match the title and the quality tiers (SET-03). Open question: choose automatically (best tier first) or show candidates for review as the album flow can.
3. **State.** One acquisition record per song, keyed by artist, album and track, with the same states (searching, downloading, completed, failed, dismissed) and one monitor card per song, grouped under its album.
4. **Import and destination.** The completed file goes to `<music root>/<artist>/<album>/` using the folder the library already uses for that album when it exists (an album with year-suffixed names, for example, must not get a second folder), else the established naming. Same safety rules as album import: canonical path under the configured root, no symlink escapes, no overwrite of an existing file, storage-identity check, rollback on partial failure (ACQ-06).
5. **Dismiss and cleanup.** Dismissing a song card deletes only that song's downloaded file, never the album folder (ACQ-04 must be restated for songs).
6. **Tests.** Safe success and unsafe refusal for each rule above, in the acquisition regression suite, plus Get/pending/requested/failed button states for rows.

Decisions needed from the owner: automatic versus reviewed candidate choice; where a song goes when the album folder does not exist yet; whether a song Get on an album the library does not have should create the album folder with that one song; and whether the album-level Get hides once any track is owned.
