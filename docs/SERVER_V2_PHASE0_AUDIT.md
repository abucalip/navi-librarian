# Server V2 Phase 0 audit

**Status:** Draft for owner review. Read-only measurement; no server code, API or client contract changed.
**Baseline:** GitHub `main` at `b266b136` (2026-11-05). Measured against the owner's live Navidrome on 2026-11-05.
**Plan:** [`ServerV2.md`](ServerV2.md) section 9, Phase 0. Work items below use the plan's numbering.

## Summary

| Question | Answer |
|---|---|
| Navidrome | 0.64.2, OpenSubsonic enabled, 1,792 albums, 755 artists, 12,683 tracks |
| Sonic endpoints | `getSonicSimilarTracks` and `findSonicPath` return HTTP 404; `sonicSimilarity` is not advertised. A sonic plugin is not installed. |
| Album MBID coverage | 53.1% (release MBID). Release-group MBID is not exposed by Navidrome. |
| Track MBID coverage | 85.2% recording MBID; 66.4% of albums have an MBID on every track |
| Artist MBID coverage | 47.9% |
| MusicBrainz relationships | Good where an MBID exists (see item 5), so Phase 4 is **not** deferred for credits |
| ListenBrainz mapping | About 81% of sampled listens carry a recording MBID |

Kill/pivot outcomes from the plan: credits coverage is high enough to keep Phase 4 personnel and label views. No sonic plugin works yet, so Phase 7 is not proxy-only until one is installed (owner decision D-6).

## Method and limits

- Scripts: `scripts/server_v2_phase0_probe.py` (Navidrome fields, sonic endpoints) and `scripts/server_v2_phase0_coverage.py` (identifiers, MusicBrainz, ListenBrainz). Both read `config.env`, make read calls only, and print aggregate counts. Neither writes to Navidrome or the app databases.
- Field matrix: 100 albums and 772 tracks, chosen with a fixed random seed (0). Library-wide figures use the whole library (paged `getArtists`, `getAlbumList2` and `search3`).
- MusicBrainz sample: 200 albums chosen at random **from albums that have a release MBID** (53% of the library). Rates are therefore rates among MBID-tagged albums. Multiply by 0.531 for a whole-library ceiling. 200 requests, paced at 1.1 s, one `release` lookup each. MusicBrainz has no multi-ID lookup, so these cannot be batched; the bulk route is the dump slice (D-1).
- ListenBrainz: the most recent listens only, paged. The run stopped at 1,700 of 40,893 listens on an HTTP 429; the rate is for recent listens, not all history.
- **Not measured:** MusicBrainz ISRC coverage (the lookup did not request ISRCs; the 0% in the raw output is a script gap, not a finding). Track-level artist MBIDs read 0% in Navidrome's `artists` entries; the cause is unverified.

## 1. Navidrome client inventory

Transport: `integrations/navidrome/client.py` (`api_call`, `cover_art`, three payload shapers). `navidrome_client.py` re-exports it. Token authentication, 30 s timeout, no retry.

| Method | Callers | Kept |
|---|---|---|
| `getArtists` | `discovery/library_snapshot.py` | id, name, albumCount |
| `getAlbumList2` | library snapshot (paged, 500), dashboard shelves | id, artist, artistId, genre, name, year, songCount, coverArt, musicBrainzId (as `release_mbid`), created |
| `getAlbum` | album details | id, name, artist, year, genre, songCount; per track id, title, artist, track, duration, playCount |
| `search3` | song inventory (`discovery/search/index.py`, empty query, paged) | raw songs, then shaped by the index |
| `getArtist`, `getArtistInfo2` | `app/api/search.py`, `app/api/metadata.py` | bio and similar artists |
| `getGenres` | dashboard | genre list |
| `ping` | health, settings test | status only |
| radio calls | `integrations/radio/stations.py` | station records |
| `getCoverArt` | artwork route | raster image only |

Discarded today (populated in this library, see section 2): record labels, release types, original release date, compilation flag, edition `version`, disc titles, nested artists and contributors, ISRC, replay gain, bit depth, sampling rate, channel count, file size and format fields. Not called at all: `getOpenSubsonicExtensions`, `getSong`, `getTopSongs`, `getSimilarSongs2`, `getStarred2`, `getLyricsBySongId`, sonic endpoints.

## 2. Field availability (sample: 100 albums, 772 tracks)

Percentages are populated values (not merely present keys).

**Albums** (from `getAlbum`)

| Field | Populated | Kept today |
|---|---|---|
| artist, artistId, artists, displayArtist, name, sortName, created, songCount, duration | 100% | partly |
| coverArt | 92% | yes |
| year | 91% | yes |
| genre / genres | 88% | yes (first genre) |
| musicBrainzId (release) | 59% (53.1% library-wide) | yes |
| recordLabels | 67% (63.2% library-wide) | no |
| originalReleaseDate | 43% | no |
| releaseDate | 40% | no |
| releaseTypes | 43% | no |
| discTitles | 12% | no |
| isCompilation | 2% | no |
| version | 1% | no |
| playCount / played | 19% | no |
| userRating, averageRating, explicitStatus, moods | 1% or less | no |

**Tracks** (from `getAlbum`)

| Field | Populated | Kept today |
|---|---|---|
| title, artist, artists, albumArtists, album, albumId, duration, bitRate, channelCount, samplingRate, size, suffix, path, contentType | 100% | partly |
| track number | 97% | yes |
| year | 97% | no |
| discNumber | 67% | no |
| musicBrainzId (recording) | 89% in sample (85.2% library-wide) | no |
| isrc | 42% (40.4% library-wide) | no |
| contributors | 38% | no |
| displayComposer | 34% | no |
| comment | 28% | no |
| bitDepth | 28% | no |
| replayGain | 10.5% | no |
| works | 6% | no |
| bpm | 2.5% | no |
| playCount | 7% | yes (album view) |
| groupings, explicitStatus, moods, movements | 4% or less | no |

Formats in the sample: mp3 558, flac 170, m4a 27, wma 15, ogg 2.

OpenSubsonic extensions advertised: `transcodeOffset`, `formPost`, `songLyrics` (v1, v2), `indexBasedQueue`, `transcoding`, `playbackReport`, `topSongsByArtistId`. No `sonicSimilarity`.

## 3. Sonic endpoints

Both `getSonicSimilarTracks` and `findSonicPath` returned 404. Navidrome serves them only while a sonic-similarity plugin is loaded. Setup (AudioMuse-AI and its Navidrome plugin) is documented at <https://www.navidrome.org/docs/usage/integration/audiomuse/>; the owner has not decided whether to install it (D-6).

## 4. Identifier coverage (whole library)

| Entity | With MBID |
|---|---|
| Artists (755) | 47.9% |
| Albums (1,792), release MBID | 53.1% |
| Albums, release-group MBID | not exposed by Navidrome |
| Tracks (12,683), recording MBID | 85.2% |
| Albums where every track has a recording MBID | 66.4% |
| Tracks with ISRC | 40.4% |

Consequence: edition and duplicate work (Phase 2) cannot lean on release-group MBIDs from Navidrome and needs MusicBrainz lookups from the release MBID. Almost half the library has no album MBID, so the identity ladder (plan 6.5) must handle name-based matching for those albums.

## 5. MusicBrainz relationship coverage (200 albums with MBIDs, 3,008 tracks)

| Measure | Result |
|---|---|
| Release found | 200 of 200 |
| Albums with a label | 94.5% |
| Albums with a catalogue number | 80.0% |
| Albums with a barcode | 74.0% |
| Albums with release-group relationships | 33.0% |
| Albums in a series | 31.5% |
| Albums with at least one recording credit | 77.5% |
| Albums with at least one work link | 85.0% |
| Albums with release-level artist relationships | 27.5% |
| Tracks with any recording relationship | 78.2% |
| Tracks with an artist credit relationship | 65.5% |
| Tracks with a work link | 72.6% |

Rates apply to the 53% of albums that have a release MBID. Whole-library ceiling is roughly 53% of these figures until MBID coverage improves.

## 6. ListenBrainz mapping

40,893 listens exist. In the 1,700 most recent that were read: 81.2% have a recording MBID, 81.1% a release MBID, 81.1% artist MBIDs. The read stopped on an HTTP 429, so this is a sample of recent listens. A full-history figure needs a paced run or the batch metadata endpoints.

## 7. Storage, jobs and Discogs

- **SQLite:** plain `sqlite3.connect(..., timeout=10)` calls; tables created with `CREATE TABLE IF NOT EXISTS` in `discovery/store.py`, `navidrome_server.py` (feedback, lists, acquisitions), `settings/persistence.py`, `metadata_cache.py`, `integrations/radio/store.py` and `acquisition/state.py`. No `user_version`, no migration runner, no shared connection helper. D-7 (where Server V2 data lives) is open.
- **Jobs:** bare `threading.Thread` (daily lens refresh and manual refresh in `discovery/lens_service.py`, library resync, search index build, identity work, acquisition track runs, a scheduler thread in `navidrome_server.py`). No job table or queue.
- **Server size rule:** `navidrome_server.py` takes no additions (D-016); Server V2 code goes in new modules.
- **Discogs:** used only by `DiscogsSearch` in `discovery/search/providers.py` for style browsing and artist/album search. Needs a personal access token held in settings (`discogs_token`, with a generation counter that invalidates cache on change). No MBID linking, name matching only.

## 8. Payload regression fixtures

`android/contract-fixtures/` already holds 42 librarian and 9 Navidrome payloads, checked against the served routes by `tests/test_android_contract_fixtures.py`. The macOS client uses the same server routes. No new snapshot was needed.

## 9. Golden set (50 albums, owner-verified 2026-11-05)

Candidates were generated with `scripts/server_v2_phase0_golden.py` (109 MusicBrainz requests) and every one was checked by the owner. The list names library albums and the repository is public, so the verified set is kept outside the repository; only aggregates are recorded here.

| Verdict | Albums |
|---|---|
| Matched release correct | 30 |
| Owner picked a different MusicBrainz candidate (all five were albums with no MBID) | 5 |
| Expected result "unresolved" | 10 |
| Expected result "not in MusicBrainz" | 5 |

Findings:
- **Library MBID tags are reliable where present:** of 35 albums tagged with a release MBID, 30 were confirmed correct and 5 could not be decided (several editions share the track count). None was wrong.
- **Partial copies are common:** 16 of the 35 tagged albums hold fewer tracks than the matched release (many only 1 track), so edition matching must not require a full track-list match, and a stray single track must not create a wrong edition.
- **No-MBID albums mostly cannot be matched:** of 15 (10 drawn for that group plus 5 from other groups), the owner picked a MusicBrainz search candidate for 5, 5 are not in MusicBrainz and 5 are unresolved. Placeholder names such as an unknown-album tag never resolve.
- **Stray duplicates exist:** at least one single-track album is a leftover from another edition of an album the owner holds in full; 79 probable duplicate groups exist library-wide.
- **Track counts can exceed the release:** one album holds 10 tracks against a confirmed 7-track edition.
- **Indistinguishable editions are common:** 10 albums are unresolved (5 tagged, 5 untagged) because several editions share a track count; the matcher should report unresolved here rather than guess.

Targets for later phases (proposed): at least 90% of golden-set albums either correct or explicitly unresolved, and zero wrong silent merges (plan section 9, Phase 2 exit).

## Decisions (owner, 2026-11-05: recommended options accepted)

| # | Decision |
|---|---|
| D-1 | Hybrid MusicBrainz access: local dump slice for bulk, API for the rest |
| D-2 | First user-facing outcome: Library Health and Forgotten Gems |
| D-3 | Phase 0 strictly read-only; provider calls limited to the bounded samples above |
| D-4 | Approved sources and budgets: MusicBrainz, ListenBrainz, Wikidata, Cover Art Archive, LRCLIB. Fanart/TheAudioDB and Discogs later |
| D-5 | Graph scope: owned-adjacent first |
| D-6 | Sonic: proxy first (AudioMuse-AI plugin); in-house experiment only if the proxy proves impossible |

D-7 (data location), D-8 and D-9 stay open for Phase 1. D-7 note: no migration convention exists today, so a new file or a shared migration helper must be decided before Phase 1.

## Next action

Phase 0 exit criteria are met: audit written, coverage numbers recorded, decisions D-1 to D-6 answered, golden set verified. The owner decides when to publish this audit and the three scripts, then Phase 1 can be proposed.
