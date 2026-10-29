# Album page redesign: layout record and song-only Get proposal

Status: layout, `genre` and per-track `owned` are **merged in PR [#635](https://github.com/abucalip/navi-librarian/pull/635)** (contract `SEARCH_CONTRACT.md` section 14.4). The song-only Get in section 3 is **approved by the owner and built, not yet merged** (requirement ACQ-08); the owner's decisions are recorded at the end of section 3.

## 1. Layout requested by the owner

Central large cover; title below it in bold; artist below, regular and slightly smaller; genre and year below that, smaller; description; tracklist with a Get button next to tracks the library does not have; ranked similar albums; similar artists as circles; spacing and alignment as in the reference screenshot.

Decisions carried over from the artist page: no "Library" heading and no text Back button (an icon-only back button), plain-text links and "Read more", the three-line description clamp (six on a phone), numbered rows for ranked lists, one scrim-free flat layout. Owner choices for this page: genre from the library, else the artist's first tag; service links in a quiet row below the tracklist; similar albums keep the server's order with numerals.

## 2. What the page does today

- Tracks carry `owned`; owned tracks show a green check, others show nothing in that column.
- The album-level Get (or owned check) stays on the cover, as before.
- There is no Get on a track, because Get requests a whole album.

## 3. Get a single song (approved, built, not merged)

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

### Owner decisions and what was built

- **Candidate choice: automatic.** The best clear file is queued with no review step.
- **No album folder yet: create it.** `<music root>/<artist>/<album>/` is created with that one song, named as an album import names it. An existing folder is reused, including one with a year in its name; two possible folders refuse.
- **Album-level Get: hides only when all tracks are owned**, and then becomes the green check. An album the library only partly has keeps its Get.
- **Built as** `acquisition/track_search.py` (queries and the strict title match), `track_destination.py`, `track_import.py` (no-overwrite, descriptor-pinned import), `track_service.py` (request, watcher with retry and fallback sources, dismissal, restart resume, live progress), `POST /api/acquire/track`, a Get pill on each missing track, and song acquisition cards. A song is one row of the existing acquisition table whose album name is `<title> (song on <album>)`, with `kind: "track"` in its details; its candidate stores `track_file`, never `files`, so the album watcher's restart recovery cannot claim it. `navidrome_server.py` is unchanged (D-016).
- **Known limits.** (1) The album-level Get on a partly owned album starts the album flow, whose import refuses an existing album folder (`destination_exists`); it does not import only the missing songs. (2) A song's dismissal is refused (fail closed) while another download shares its remote folder name in the download directory, until that one finishes. (3) A song interrupted while `importing` is not resumed and is dismissed by the owner. (4) Nothing ran against live slskd or the owner's library, and the page was not checked in a browser.
