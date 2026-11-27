# Product requirements

Last updated: 2026-11-27.

Concise user-facing behavior ledger for the **server and web client** (native client requirements live in `abucalip/discair-macos` and `abucalip/discair-android`). If implementation and this document disagree, clarify intended behavior, update this ledger, and add a regression test.

## Functional requirements

| ID | Requirement | Status |
|---|---|---|
| DISC-01 | Generate new-music recommendations using shared discovery/recommendation logic. | Implemented |
| DISC-02 | Provide discovery lists for personal discoveries, classics / collection-building, and Artist Deep Dives. | Implemented |
| DISC-03 | Refresh discovery lists and preserve user feedback (save/dismiss). | Implemented |
| DISC-04 | Never recommend albums already owned in Navidrome. | Core |
| DISC-05 | Filter non-album releases and avoid false artist matches (including Various Artists and similarly named artists). | Implemented |
| DISC-06 | Show album metadata (release year, artwork) when reliable; missing external metadata must not break discovery. | Implemented |
| DISC-07 | Artist Deep Dives show at most one album per artist in a genre row. | Implemented |
| DISC-08 | New Releases focus on recent MusicBrainz release groups by artists in the library. | Implemented |
| DISC-09 | Personal picks carry `because` (`tag`: "Because you listen to {tag}"; `similar_artists`: "Shares genres with {names}") when honest, and omit it otherwise. ListenBrainz CF picks carry no seed. | Implemented |
| DISC-10 | Genre blocklist (`GET`/`POST`/`DELETE /api/discovery/blocked-genres`): never decays, applies at selection and read time, never hides owned albums/library pages; blank genre is 400. | Implemented |
| DISC-11 | Artist lean (`GET`/`POST`/`DELETE /api/discovery/artist-lean`): `more` boosts tag seed/score; `less` demotes score; neither hides anything or affects owned library. | Implemented |
| DISC-12 | Artist blocklist (`GET`/`DELETE /api/discovery/blocked-artists`): lifts read-time hide and score penalty while keeping separate album dismissals; blank artist is 400. | Implemented |
| DISC-13 | Navidrome stars seed discovery (on by default, `GET`/`PUT /api/settings/star-seed`): one cached `getStarred2` read, reorders/replaces planned tag queries without adding provider calls. | Implemented (weights pending owner approval) |
| DISC-14 | Discovery mode (`safer` / `balanced` / `deeper`, `GET`/`PUT /api/settings/discovery-mode`): scales gate-lens audience band max (`safer` 2×, `deeper` 0.5×) on next refresh. | Implemented (no client UI yet) |
| META-01 | Artist bios use Apple Music (full About page, no developer token) → identity-checked Wikipedia/Wikidata → Navidrome fallback; `/api/artist-bio` and artist page share the resolver. | Implemented |
| ACQ-01 | Requesting an album does not navigate away from the current discovery page. | Implemented |
| ACQ-02 | Clicking Get transitions to `requested` to prevent duplicate requests; failures restore usable state and show an error. | Implemented |
| ACQ-03 | Each acquisition card has a persistent Dismiss control regardless of state. | Implemented |
| ACQ-04 | Dismissing an acquisition removes its entry and deletes its download folder after canonical-root validation; ambiguous/unsafe paths fail safely. | Core |
| ACQ-05 | slskd candidates group by actual remote folder/path without merging unrelated candidates across punctuation/Unicode/editions. | Implemented |
| ACQ-06 | Acquisition/import must validate completeness and paths and never overwrite or delete unrelated library content. | Core |
| ACQ-07 | Broaden slskd queries (including wildcard-masked artist names) when an exact artist+album query returns no usable payloads; report query/response counts. | Implemented |
| ACQ-08 | Single-track Get (`POST /api/acquire/track`) downloads one matching audio file into `<music root>/<artist>/<album>/` without overwriting existing files; dismissing removes only that song's download file. | Implemented |
| RADIO-01 | Radio relay replaces station URL in Navidrome with `/radio/stream/<secret token>` (public to login gate via token), logs ICY titles heard ≥30 s in `radio.sqlite3`, and supports song-only Get via MusicBrainz. | Implemented |
| LIB-01 | Every artist, album, and genre name opens its library page; song results open their album. | Implemented |
| LIB-02 | Artist page shows photo, genres, library count, Top songs, bio, owned albums, missing albums (with Get), and similar artists. | Implemented |
| LIB-03 | Album page shows cover, metadata, Info/Reviews tabs, tracklist with owned checks, service links, similar albums, and similar artists. | Implemented |
| LIB-04 | Hash routing (`#<page>`, `#library/artist|album|genre?...`) preserves page across refresh and browser Back/Forward without storing tokens. | Implemented |
| LIB-05 | Artist/album pages show 5 random similar artists and 7 albums ("All albums" when more); unowned albums show "Not in your library". | Implemented |
| LIB-06 | Library page searches owned items (`scope=owned`) and browses Artists/Albums with persisted sort, order, list/grid, and tile size (`/api/library/artists`, `/api/library/albums`). | Implemented |
| LIB-07 | Album covers never fall back to artist photos; `/api/artwork` uses Deezer → Apple Music → Qobuz on exact artist+album match, or returns no cover. | Implemented |
| LIB-08 | Owned tracks on album pages show a quality badge (e.g. `FLAC 16/44`, `MP3 320k`); unowned/unknown tracks show none. | Implemented |
| LIB-09 | Multi-disc albums group tracks under `Disc N` headings with per-disc numbering. | Implemented |
| DASH-01 | Dashboard shows Genres grid (top 12, expandable to 60) under Recommended. | Implemented |
| DASH-02 | Dashboard shows New releases, Newly added, Recently played, and Most played shelves; Navidrome errors leave the rest usable. | Implemented |
| DASH-03 | Recommended row is a keyboard-accessible CSS/JS slider respecting reduced motion. | Implemented |
| SET-01 | Configure Navidrome, slskd, ListenBrainz, and Discogs without returning secrets to clients. | Implemented |
| SET-02 | Submitting a blank secret preserves the existing secret unless clearing is explicitly requested. | Implemented |
| SET-03 | slskd audio-quality tiers (MP3 320/193–319/192, FLAC CD/16-44.1/Hi-Res) are reorderable by drag or move buttons and persist across migrations. | Implemented |
| SET-04 | Post-import library resync (`library_resync_after_import`, default on) waits 10 s, drops cached snapshot, and rebuilds the owned index without affecting import results. | Implemented |
| AUTH-01 | First-run owner account and session-based auth protect app/API routes while allowing only required static login assets. | Core |
| DATA-01 | Persist app database and auth key under the configured `/data` volume across restarts/upgrades. | Core |
| API-01 | Validate API inputs and return clean HTTP errors without exposing internal exceptions or credentials. | Core |
| OPS-01 | Reproducible Docker builds for `linux/amd64` and `linux/arm64`; GHCR publication stays paused unless explicitly authorized. | Core |
| OPS-02 | Navidrome and slskd remain external services; the web container never bundles or starts them. | Core |

## Safety rules for acquisition and deletion

- Treat every dismiss action as destructive; validate canonical paths under configured roots before deleting.
- Reject traversal, symlink escapes, empty/root paths, and ambiguous folder matches; fail safely without guessing.
- Tests must prove both intended removal and preservation of unrelated files.

## Change process

1. Update this ledger when user-visible behavior changes.
2. Add or update focused regression tests (`pytest <file>`).
3. Smoke-test affected web UI behavior per [`LOCAL_UI_TESTING.md`](LOCAL_UI_TESTING.md).
4. Update [`PROJECT_STATUS.md`](PROJECT_STATUS.md) if the milestone changes.
