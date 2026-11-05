# Server V2 — Music Intelligence Layer

**Status:** Research and architectural proposal only. This document does not approve implementation, change existing requirements, or authorize new provider traffic, audio analysis, deployment, or client UI work.

**Research baseline:** GitHub main at commit e29ca45b2021ca7ad3b158efc4dec8e9c7ae5414 (2026-11-05). Re-check the repository, provider documentation, and the installed Navidrome version before turning any proposal here into an implementation contract.

## 1. Executive summary

Librarian can grow from a recommendation and acquisition service into a **Music Intelligence Layer** between Navidrome and the macOS and Android clients.

The central idea is to stop treating an album or track as a small bundle of tags. Treat it as an entity in a larger musical world: performers, composers, producers, engineers, labels, recording locations, scenes, works, versions, releases, musical characteristics, and the listener's changing relationship with the music.

Librarian would gather and reconcile source data, calculate useful derived information, preserve provenance and confidence, and expose client-neutral results through a stable API. The clients would display and navigate that knowledge; they would not independently perform matching, ranking, or recommendation calculations.

The most valuable long-term capabilities are:

1. **A musical knowledge graph** connecting artists, musicians, recordings, works, labels, people, places, and scenes.
2. **Collection intelligence** that finds forgotten favourites, collection gaps, missing discography chapters, duplicate editions, and overlooked connections.
3. **Sonic intelligence** that describes and compares the actual sound of local recordings, not only their tags.
4. **Musical context and exploration** through release histories, label histories, geographic scenes, covers, versions, influences, and discovery paths.
5. **A personal musical fingerprint** that explains how listening interests change over time.

These capabilities should be developed incrementally. The first deliverable should be a reliable identity, relationship, provenance, and caching foundation—not a large new recommendation algorithm.

## 2. Current repository baseline

### 2.1 What Librarian already does

The repository is not starting from zero. Current main already contains substantial discovery, metadata, collection, and client work.

Relevant existing capabilities include:

- ListenBrainz listening history and collaborative-filtering inputs, plus Last.fm data and cached popularity/tag information.
- MusicBrainz identifiers and metadata lookup.
- Album recommendation lists, personal discoveries, classics/collection-building, Artist Deep Dives, New Releases, and the Engine 2 daily lens framework.
- Ownership matching against the Navidrome library, including filtering owned albums from discovery results.
- Artist and album detail responses, biographies, top songs, similar artists, similar albums, album descriptions/reviews, artwork lookup, and missing-album information.
- Genre and global search, library browsing, and a background-built owned-library index.
- Discovery feedback, saved/dismissed items, acquisition status, and album- or track-level acquisition.
- Existing Discogs-related search integration and settings work; its current enabled/configured state must be checked before relying on it as a general metadata source.

Relevant implementation boundaries observed on main:

- integrations/navidrome/client.py owns the Subsonic transport and selected response-shaping helpers.
- discovery/search/ owns the owned-library index and library search/browse behavior.
- discovery/lens_service.py coordinates daily lens building and serving outside the legacy server module.
- app/api/library.py is a thin adapter over the owned index and paging logic.
- Artist and album page APIs already return useful related information consumed by the clients.
- The macOS Discair client has live library, album and artist pages, related artists/albums, discovery, acquisition, playback, lyrics, scrobbling, queue, offline caching, and other player features. The latest commit also records further artist-page and navigation improvements.
- The Android contract records dashboard, library, artist/album, discovery, search, acquisition and offline-cache work, while retaining explicit outstanding device, accessibility, and live-server verification. Its contract header still describes the contract as a proposal pending approval; do not infer release or acceptance status from implementation notes alone.

This means Server V2 should extend and consolidate existing capabilities. It should not duplicate the recommendation engine, build a second ownership matcher, or move domain logic into Swift/Kotlin.

### 2.2 Existing constraints that matter

- GitHub main is authoritative. This document is a proposal, not an implementation branch or an approval to start every idea below.
- Keep FastAPI routes thin. Domain policy, matching, ranking, provider access, persistence, and background work belong in explicit service/module boundaries.
- navidrome_server.py takes no additions (D-016). New work belongs in directly importable modules and packages with focused tests.
- Preserve the established API and client contracts. A new field or endpoint requires a documented contract and tests.
- Keep provider metadata optional. Missing, ambiguous, rate-limited, or unavailable external data must not break core library, playback, or discovery flows (D-007).
- Treat acquisitions, imports, cleanup, and filesystem paths as safety-critical. Music Intelligence must not gain authority to modify media files or tags merely because it analyses them.
- Do not assume the current recommendation weights or historical evaluation gaps are solved by adding more metadata. Evaluate each new signal separately.

## 3. What Navidrome can already provide

Navidrome's Subsonic-compatible API is a useful source of collection truth and user-specific state. It is more capable than the small subset currently copied into some Librarian response helpers.

### 3.1 Core library and playback data

The current Subsonic-compatible surface includes methods such as:

- getArtists, getArtist, getAlbum, getSong, and getGenres.
- getAlbumList2, getSongsByGenre, search3, getStarred2, and getNowPlaying.
- getCoverArt and getLyrics.
- setRating, star, unstar, and scrobble.
- getArtistInfo / getArtistInfo2, getAlbumInfo / getAlbumInfo2, getTopSongs, and getSimilarSongs where their external integration requirements are met.
- Playlist and internet-radio methods, plus scan status and other server capabilities.

The Navidrome compatibility documentation says it implements Subsonic API 1.16.1 with documented exceptions and OpenSubsonic extensions. It also notes that stream alone does not mark a song as played: scrobble with submission=true updates play history.

### 3.2 Useful song-level fields

Depending on the server version, library tags, and response type, the Subsonic/OpenSubsonic child/song response can expose:

| Field family | Examples | Potential Librarian use |
|---|---|---|
| Identity | Navidrome song ID, title, artist, album, artist ID, album ID | Stable links back to the owned item |
| Track structure | Track number, disc number, duration | Multi-disc display, sequencing, completeness |
| File properties | Suffix, content type, size, bitrate | Format and storage information |
| Hi-res properties | Bit depth, sampling rate, channel count | Accurate technical-quality display |
| Listening | Play count, played timestamp, starred timestamp, user rating | Rediscovery and personal collection analysis |
| Music identity | MusicBrainz recording ID, ISRC | Matching recordings to external metadata |
| Musical tags | Genres, moods, grouping | Better facets and descriptive profiles |
| Credits | Artist references, album-artist references, contributors/roles where populated | Personnel and relationship discovery |
| Audio adjustment | ReplayGain track/album gain and peak | Playback metadata and quality context |
| Sorting/display | Display artist, display album artist, sort name | Better identity and presentation |

Some of these fields are extensions rather than universal Subsonic guarantees. Some depend on tags being present in the actual files. An absent field is not evidence that the property does not exist.

Navidrome's current source maps fields including BPM, recording MBID, ISRC, ReplayGain, channel count, sampling rate, bit depth, genres, moods, groupings, display artist/album artist, artist and album-artist references, and contributor data into its OpenSubsonic child response. Exact availability must be checked against the owner's installed Navidrome version and real responses.

### 3.3 Sonic endpoints: investigate, do not assume

Current upstream Navidrome source registers getSonicSimilarTracks and findSonicPath handlers. These are especially interesting because they may provide server-side similarity and paths through a sonic space.

However:

- They are not ordinary baseline Subsonic methods.
- Their availability and behavior may vary by Navidrome version and extensions.
- The current installed server has not been verified against these methods in this research.
- Their output should be treated as an optional capability, not a dependency.

A small, read-only capability probe against the installed server should precede any integration proposal.

### 3.4 Navidrome API v1 is not the current integration target

Navidrome's own API v1 documentation explicitly labels the API as work in progress and not ready for implementation; its schema may change. Continue using the established Subsonic/OpenSubsonic interface for supported library data unless a later Navidrome release documents a stable API contract.

### 3.5 Immediate opportunity: preserve more of the data already returned

The current integrations/navidrome/client.py response-shaping helpers deliberately return compact subsets. For example, the album-details helper selects a small set of album fields and a small set of song fields. This keeps existing payloads simple, but means Librarian should first inventory what its current client requests receive and what it discards.

A safe first step is a field-availability matrix:

1. Method and response type.
2. Field name and OpenSubsonic extension status.
3. Whether the installed Navidrome version returns it.
4. Whether it is populated for the owner's library.
5. Whether it is user-specific, library-wide, or file-specific.
6. Whether Librarian currently retains, normalizes, caches, or discards it.
7. Which proposed feature would use it.

Do not add every available field to every API response. Retain normalized fields in the server's internal intelligence model and expose only what each client contract needs.

## 4. External inspiration and data sources

The goal is to learn from other products and open datasets, not to make Librarian dependent on proprietary services.

### 4.1 Roon: model music as an object graph

Roon's metadata model is the strongest architectural inspiration. It represents albums, tracks, performers, performances, compositions, labels, roles, periods, forms, and other entities as objects connected by relationships. Credits are categorized by role rather than flattened into one artist string.

**Lesson for Librarian:** an album is not just artist + title; it is a node connected to people, recordings, works, releases, labels, dates, places, and other albums.

Roon is an inspiration for the data model and browsing experience, not a proposed runtime dependency.

### 4.2 MusicBrainz: identity and documented relationships

MusicBrainz provides core entities including areas, artists, events, genres, instruments, labels, places, recordings, releases, release groups, series, works, and URLs. Its API supports lookups, browse/search operations, and relationship includes for many entity types.

Important distinctions:

- **Recording:** a particular recorded performance/version.
- **Work:** the underlying composition or musical work.
- **Release:** a specific issue/edition, such as a particular CD, vinyl pressing, or digital issue.
- **Release group:** the conceptual album/release family grouping related releases.

Relationships can connect artists with other artists, recordings, works, labels, places, and more. This is the backbone for verified credits, cover versions, session personnel, release families, and musical geography.

MusicBrainz has request-rate and User-Agent requirements. Any new crawler or background enrichment must use a descriptive User-Agent, bounded request rates, caching, and incremental updates. Do not build an unbounded full-database crawler.

### 4.3 ListenBrainz: the listener's history and evolution

ListenBrainz offers listening history, exports, statistics, era activity, genre activity, recommendations, and other endpoints. Existing Librarian integration already uses listening history and collaborative-filtering information.

Potential additional uses include:

- Listening activity by era and genre.
- Artist/album/recording trajectories over different time windows.
- Long-term favourites versus recent interests.
- Rediscovery signals and dormant artists.
- Historical taste profiles.

ListenBrainz data is incomplete when recordings or MBIDs are missing, and some statistics are computed asynchronously. A missing result must not be treated as zero interest.

### 4.4 Cover Art Archive: release-specific visual evidence

The MusicBrainz Cover Art Archive can provide front, back, medium, booklet, and other release images where available. Release-group art can be useful when a specific edition has no image.

This could enrich album archaeology with back covers, labels, booklets, and physical-release context. Use release-level identity to avoid attaching artwork from the wrong edition. Respect source attribution and image licensing constraints.

### 4.5 Discogs: label, catalogue, and edition context

Discogs can be a useful optional source for:

- Record labels and catalogue numbers.
- Specific editions and formats.
- Country and release date.
- Tracklists and credits.
- Master/release relationships.
- Physical-media variants.

Librarian already has Discogs-related work in its search integration. Before expanding it, inspect the current provider contract, token handling, API limits, matching behavior, and whether the desired fields are available under the current integration. Do not make Discogs mandatory for core operation.

### 4.6 Plexamp: sonic analysis as a new dimension

Plex's Sonic Analysis is a compelling product reference. It analyses local audio with a neural model and uses the resulting high-dimensional representation to find sonically similar tracks, artists, and albums, and to create track/album radio and mixes.

The key insight is that two recordings can be close in sound even when their artist, genre, era, and popularity metadata are unrelated.

Plex's implementation is proprietary and should not be treated as a reusable library or API. Its CPU-intensive analysis model is a warning as well as an inspiration: analysis can take hours or days on a large collection and needs scheduling, progress, and resource limits.

### 4.7 Essentia and AcousticBrainz: possible audio-analysis foundations

Essentia is an open-source audio-analysis toolkit that can extract low-level and higher-level musical features. It is a candidate for a self-hosted experimental analysis pipeline.

AcousticBrainz is no longer collecting new submissions (the project stopped collection in 2022), although historical data dumps and APIs remain available. Its existing data is indexed by MusicBrainz recording ID and is CC0. It may be useful as an optional historical source where a matching recording exists, but it should not be described as an active service or assumed to cover the owner's obscure recordings.

### 4.8 Inspiration versus integration

| Product/source | Borrow the idea | Runtime dependency proposed? |
|---|---|---|
| Roon | Rich object graph and categorized credits | No |
| Plexamp | Sonic similarity, track/album radio, mixes | No; investigate self-hosted analysis |
| MusicBrainz | Entity identity and documented relationships | Yes, optional enrichment |
| ListenBrainz | Listening history and taste evolution | Existing integration; extend carefully |
| Cover Art Archive | Release-specific artwork and physical context | Optional |
| Discogs | Editions, labels, catalogue numbers, formats | Optional; inspect current integration |
| Essentia | Local audio feature extraction | Experimental optional component |
| AcousticBrainz | Historical audio features | Optional legacy dataset only |

## 5. Proposed capability catalogue

The following ideas are intentionally broader than a conventional recommendation feature. They are opportunities for the server to prepare structured information that both clients can reuse.

### 5.1 The musical knowledge graph

**Concept:** connect artists, groups, people, recordings, works, releases, labels, instruments, places, and musical scenes through typed relationships.

Potential entity types:

- Artist, group, person, and collaboration.
- Recording, work/composition, release, release group, and series.
- Label, place, area, event, studio, and instrument.
- Genre, style, mood, and musical scene.

Potential relationship types:

- Member of / former member of.
- Collaborated with / performed on.
- Main performer / guest performer / session musician.
- Composed / wrote / arranged / conducted.
- Produced / engineered / mixed / mastered.
- Released by / recorded at / performed at.
- Cover version of / based on / part of the same work.
- Influenced by / successor to / associated with a scene.

Relationships must carry a role, source, evidence, and confidence. Do not turn a vague similarity into a factual collaboration claim.

**Example discovery path:** open an album by Fela Kuti; inspect a credited saxophonist; follow that musician to a different band; find an album by that band that is not owned. The discovery is explained by the personnel connection, not an opaque similarity score.

**Client value:** an interactive graph and inspector on macOS; compact "musicians connected to this album" and "why this is related" sections on Android.

### 5.2 Session musicians and producer fingerprints

**Concept:** discover albums through the people behind the recording rather than only the headline artist.

Prepared data could include:

- Albums featuring a particular bassist, drummer, percussionist, horn player, or vocalist.
- Albums produced, engineered, mixed, or mastered by the same person.
- Collaborator networks across bands and eras.
- Musicians who moved from one scene or group to another.
- Albums connected by a studio, recording session, or label.

This is especially promising for jazz, soul, funk, Afrobeat, Brazilian music, and other traditions where session personnel and producers are central to the sound.

The UI should distinguish a verified track-level credit from a general artist association. MusicBrainz relationship data may be incomplete, so confidence and source must remain visible.

### 5.3 Album archaeology and release family trees

**Concept:** build a dossier for an album and explain the difference between the work, the release group, and the edition owned by the user.

Possible data:

- Original release date versus the date of the owned edition.
- Release country, label, catalogue number, and format.
- Recording dates and places.
- Producer, engineer, mastering, and performance credits.
- Original issue, reissues, remasters, deluxe editions, bonus tracks, and live variants.
- Tracklist differences and missing tracks.
- Cover-art variants and back-cover/booklet images.
- Known alternate mixes or versions, where source evidence exists.

A release-family view could show the original album, later reissues, remasters, deluxe editions, and related live recordings. This also improves duplicate detection and helps answer: "Do I own this album, or a different edition of it?"

Do not declare one master or edition sonically superior from bitrate or release date alone. Mastering-quality comparisons need evidence and should remain separate from file-format badges.

### 5.4 The forgotten-gems detector

**Concept:** identify albums and artists the listener once valued but has not revisited.

Inputs could include:

- Historical play counts and last-played time.
- Recent versus long-term listening.
- Ratings and favourites.
- Repeat-listen intensity.
- Whether the artist remains present in current listening.
- Whether the album connects to a currently active musical interest.

Possible outputs:

- **Lost & Found:** historically important albums that have gone quiet.
- Artists absent from listening for a long period.
- Albums that were heavily played in a particular year.
- Forgotten albums connected to musicians the listener currently enjoys.
- Albums that deserve rediscovery because the listener's taste has since broadened.

This should be a rediscovery score, not a judgment that an album is objectively important. Explain the reason for each suggestion and allow the user to tune or dismiss the signal.

### 5.5 Collection blind spots and discography gaps

**Concept:** analyse the collection to find meaningful absences, not simply recommend more popular albums.

Potential gaps:

- Important periods in an artist's discography that are missing.
- Albums by a musician the listener already owns as a sideman.
- Underrepresented labels, countries, cities, scenes, decades, or instruments.
- Missing collaborations among musicians already in the library.
- Missing canonical or well-documented releases from a label or movement.
- Albums connected to several owned albums but absent from the collection.
- Suspected edition duplicates or incomplete multi-disc releases.

Every gap should be grounded in a defined comparison set and a clear explanation. "Only two albums from this region" is a measurable observation; "you should own more music from this region" is a value judgment and should not be presented as fact.

### 5.6 The musical atlas

**Concept:** map the places, scenes, and movements represented in the library.

Possible dimensions:

- Artist origin and associated areas.
- Recording and performance locations.
- Labels and studios associated with a city.
- Musical scenes and historical periods.
- Cross-border influences and documented artist relationships.

A user could explore a region, see artists and albums already owned, follow neighbouring scenes, and discover missing albums. A timeline could show how a scene developed and where musicians moved.

Use MusicBrainz area/place/event data and carefully sourced historical references. Do not infer an artist's nationality from a name, a single recording location, or a label's country.

### 5.7 Personal musical fingerprint and taste evolution

**Concept:** create a living, explainable profile of the listener's musical interests.

Possible dimensions:

- Genres and more specific styles.
- Regions and musical scenes.
- Decades and original release eras.
- Instruments and instrumentation.
- Producers, labels, and collaborators.
- Listening recency, intensity, and repeat behavior.
- Sonic characteristics, once available.

The profile should compare time windows, for example recent weeks, recent months, and all-time history. It could explain that listening has shifted toward modal jazz, Brazilian recordings, guitar-led West African music, or instrumental albums—only when the data supports that observation.

A particularly useful view is **your musical fingerprint then versus now**. It should show both continuity and change, avoid over-interpreting small samples, and let the listener inspect the evidence behind each observation.

### 5.8 Sonic DNA and audio similarity

**Concept:** analyse the actual local audio and prepare a feature vector or profile for each recording.

Potential features, depending on the model and validation:

- Energy, loudness, tempo, and rhythmic density.
- Acoustic/electronic character.
- Instrumentation and timbral characteristics.
- Vocal presence and broad vocal characteristics.
- Mood-like or affective descriptors.
- Harmonic and rhythmic features.
- A learned embedding for nearest-neighbour similarity.

Potential client experiences:

- "Find music that sounds like this" even when metadata is unrelated.
- Sonically similar tracks, albums, and artists.
- Track radio and album radio.
- A map of sonic clusters in the collection.
- Similar-sounding recordings from different countries, eras, and genres.
- Explanations that identify the strongest shared audio characteristics, where the model supports them.

Do not assume that every feature can be accurately inferred by a simple DSP library. Some labels require trained models and evaluation. Do not expose false precision such as an exact mood percentage without a validated meaning.

**Resource policy:** analysis must be optional, incremental, resumable, and throttled. Prefer new or recently added tracks first. Make CPU limits, job progress, cancellation, and storage costs visible. Never analyse or upload audio to a third party without a separate explicit decision.

### 5.9 Covers, versions, samples, and musical ancestry

**Concept:** connect tracks through the underlying musical work.

Potential relationships:

- Original composition and cover recordings.
- Live versions, remixes, edits, and alternate arrangements.
- Documented samples and interpolations.
- Composer/songwriter connections.
- Artists who influenced a recording or movement.

This enables a path from a song to its composition, its earliest known recording, later covers, and other interpretations.

Use MusicBrainz work/recording relationships where documented. Sample relationships may require a separately evaluated source. Never claim that a track samples another merely because a model detects similar audio.

### 5.10 Album sequencing analyst

**Concept:** describe the structure and pacing of an album rather than only its genre.

Potential derived observations:

- Track duration progression.
- Tempo and energy arcs.
- Instrumentation changes.
- Instrumental/vocal transitions.
- Side A / side B or multi-disc structure.
- Long centrepieces, quiet closers, and recurring motifs where detectable.
- Albums with similar pacing despite unrelated genres.

This is experimental and depends on audio analysis. Start with descriptive measurements, not claims about artistic intention. Do not assert that an album was designed as a concept album based on sequencing alone.

### 5.11 Label archaeology

**Concept:** treat a record label as a discovery universe.

Prepared data could include:

- Label identity, aliases, parent/sub-label relationships.
- Active periods and locations.
- Catalogue-number patterns.
- Artists and releases associated with the label.
- Genres/scenes represented by its catalogue.
- Important releases missing from the user's library.
- Producers and studios recurring across the catalogue.

A label page could answer: "What else on this label might I enjoy?" and "Which albums in my collection share this label?"

### 5.12 Contextual listening and musical paths

**Concept:** use the current album or track as a doorway into a short, explainable exploration.

Examples:

- "Follow the drummer": five albums connected by one performer.
- "Same studio, different decade": recordings associated with one place.
- "From this label": a short path through a label catalogue.
- "A composition, five interpretations": cover/version exploration.
- "A scene in ten records": a curated historical path.
- "You own the sideman recordings; explore their albums as leaders."
- "An album from the same year, city, and scene."

Each path should be assembled from existing entities and explicit relationship evidence. The server prepares ordered stops and explanations; clients render the path and link each stop to an album or artist.

## 6. A shared Music Intelligence data layer

Do not implement each idea as an isolated recommendation endpoint. Build reusable server-side concepts that can feed several features.

### 6.1 Entity identity

Use stable external identifiers wherever possible:

- Navidrome IDs for items in the owned library.
- MusicBrainz MBIDs for artists, recordings, works, releases, and release groups.
- Discogs IDs where the optional provider has a verified match.
- ISRCs as supporting recording identifiers, not as a replacement for a robust identity model.

Keep the distinction between a recording, a work, a release, and a release group. Do not merge two entities because their names are similar. Store aliases and normalized names as matching aids, not as identity.

### 6.2 Typed relationships

A relationship should be structured, not represented only as free text.

Illustrative shape (not an approved API schema):

~~~json
{
  "from": {"type": "recording", "id": "mbid:..."},
  "relationship": "performed_by",
  "role": "tenor_saxophone",
  "to": {"type": "artist", "id": "mbid:..."},
  "source": "musicbrainz",
  "source_url": "https://musicbrainz.org/...",
  "confidence": 1.0,
  "evidence_kind": "explicit_credit",
  "observed_at": "2026-11-05T00:00:00Z"
}
~~~

The example's values are illustrative. A source-provided relationship should retain the source's actual relationship type and evidence; do not invent confidence values.

### 6.3 Provenance, confidence, and freshness

Every imported or derived fact should answer:

- **What is the claim?**
- **Where did it come from?**
- **When was it retrieved or calculated?**
- **Is it directly sourced, user-tagged, or inferred?**
- **How confident is the match or inference?**
- **When should it be refreshed?**
- **Can the client show a useful explanation?**

Suggested evidence classes:

1. source_explicit: directly present in a trusted provider response.
2. library_tag: read from Navidrome's indexed metadata.
3. user_confirmed: explicitly corrected or confirmed by the user.
4. derived: calculated from known facts or listening data.
5. inferred: model- or heuristic-generated and not independently confirmed.

Do not display inferred as a verified fact. Confidence should be calibrated and optional; a made-up numeric confidence is worse than a clear evidence label.

### 6.4 Separate source facts from Librarian's conclusions

Keep provider facts immutable as source observations. Store normalized entities and relationships separately from Librarian's own derived conclusions.

Examples:

- Source fact: MusicBrainz says person A performed on recording B.
- Derived conclusion: person A connects two albums in the collection.
- Recommendation: album C is a promising next discovery based on that connection.

These are three different things and should not overwrite one another.

### 6.5 Example album intelligence record

Illustrative internal model only:

~~~json
{
  "identity": {
    "navidrome_album_id": "...",
    "musicbrainz_release_group_id": "...",
    "title": "...",
    "album_artist": "..."
  },
  "release": {
    "original_date": null,
    "owned_edition": null,
    "labels": [],
    "catalogue_numbers": [],
    "formats": []
  },
  "musical_context": {
    "genres": [],
    "styles": [],
    "moods": [],
    "areas": [],
    "scenes": []
  },
  "credits": [],
  "works_and_recordings": [],
  "sonic_profile": null,
  "listening_profile": {},
  "collection_insights": [],
  "provenance": []
}
~~~

Missing values are normal. Do not fill gaps with guessed values or require every source to provide every section.

## 7. API and client contract direction

### 7.1 Server owns the intelligence

The clients should receive prepared data, not raw provider payloads that they must reconcile.

A future API family could be organized around concepts such as:

- Entity detail and context.
- Entity relationships and graph traversal.
- Collection insights and blind spots.
- Rediscovery candidates.
- Personal taste profile and time comparisons.
- Sonic profiles and similar-audio results.
- Discovery paths and curated journeys.
- Release/edition history.

Names such as /api/intelligence/... are examples only. Do not create these routes until the data model, pagination, partial-result behavior, cache semantics, and client needs have been agreed.

### 7.2 Client-neutral payload principles

- Stable IDs and explicit entity types.
- Human-readable labels and short explanations.
- Typed relationships and role names.
- Ownership state where relevant.
- Optional sections with explicit availability/reason.
- Provenance and confidence suitable for a detail inspector.
- Pagination/cursors for large graphs and discographies.
- Stable ordering prepared by the server.
- No secrets, local filesystem paths, or provider credentials.
- No client-side re-ranking or duplicate matching.

### 7.3 macOS: research and exploration workstation

The macOS client is well suited to dense, navigable information:

- Interactive graph explorer with a selected-node inspector.
- Full album dossiers and release-family trees.
- Label and producer catalogue views.
- Geographic atlas and historical timelines.
- Collection analytics and blind-spot dashboards.
- Side-by-side listening/taste comparisons.
- Sonic clusters and similarity maps.
- Multi-step discovery paths with a visible explanation for each connection.

These should complement the existing library, artist, album, player, queue, and discovery screens rather than replace them.

### 7.4 Android: contextual musical companion

The Android client should prioritize short, useful, touch-friendly information:

- "Who played on this?" while viewing an album or listening to a track.
- A compact list of connected musicians and producers.
- "Why this is related" explanations.
- Forgotten-gem cards.
- A small number of collection-gap opportunities.
- Quick paths to covers, collaborators, and related albums.
- A concise album history or recording-location note.
- A compact personal-taste insight.

The Android app should remain a thin client. It should not calculate similarity, ranking, relationship confidence, or ownership itself.

## 8. Recommended delivery sequence

The sequence below is a recommendation, not an approved roadmap. It intentionally prioritizes reusable foundations and low-cost collection intelligence before expensive audio analysis.

### Phase 0 — Audit and prove the available data

1. Inspect the current Navidrome client methods, callers, response shapers, and tests.
2. Probe the installed Navidrome version with read-only requests for the fields and optional endpoints listed in section 3.
3. Record a field-availability matrix using a representative sample of owned artists, albums, and tracks.
4. Inventory existing MusicBrainz, ListenBrainz, Last.fm, and Discogs caches and identity matching.
5. Record current API payloads used by macOS and Android so existing contracts are not accidentally changed.
6. Identify existing SQLite tables and cache conventions before proposing new persistence.

**Exit criteria:** evidence-backed data inventory; no new production writes; no new provider budget; no API changes.

### Phase 1 — Identity, relationships, and provenance foundation

1. Define entity types and identity resolution rules.
2. Define typed relationships and evidence classes.
3. Add source provenance, freshness, and confidence representation.
4. Reuse existing provider clients and cache conventions.
5. Build deterministic normalization/matching helpers with direct-import tests.
6. Preserve the old API payloads while the new internal model is populated in parallel.

**Exit criteria:** reliable identity and relationship records for a small, bounded sample; ambiguity is explicit; source failures do not break existing pages.

### Phase 2 — Collection intelligence

Start with features that can mostly reuse Navidrome and existing listening history:

1. Forgotten gems / rediscovery score.
2. Collection blind spots with explainable comparison sets.
3. Discography completeness and missing chapters.
4. Edition/release-family information where MusicBrainz matching is strong.
5. Label and collaborator discovery using existing relationship metadata.

**Exit criteria:** explainable results, ownership correctness, stable caching, no duplicated ranking logic in clients, and regression coverage for ambiguous identities.

### Phase 3 — Musical exploration

1. Artist/personnel graph traversal.
2. Producer and session musician views.
3. Label archaeology.
4. Release-family tree and album dossiers.
5. Cover/version/work relationships.
6. Geographic and scene atlas.
7. Curated, explainable discovery paths.

**Exit criteria:** every factual connection has provenance; graph traversal is bounded and paginated; clients can link back to owned and unowned entities.

### Phase 4 — Personal musical fingerprint

1. Build time-windowed listening profiles.
2. Separate long-term affinity from recent interest.
3. Detect meaningful changes only with adequate sample sizes.
4. Add era, genre, region, collaborator, and label views.
5. Generate plain-language explanations from measured differences.

**Exit criteria:** profiles are reproducible, sparse data produces honest empty/low-confidence states, and a new profile does not silently alter recommendation weights.

### Phase 5 — Sonic analysis experiment

1. Compare available Navidrome Sonic endpoints against the installed version.
2. Evaluate Essentia and candidate open models on a small, owner-approved sample.
3. Measure CPU, wall time, memory, disk use, and feature stability.
4. Compare model similarity with human judgments across varied genres and recording quality.
5. Add resumable, incremental jobs and explicit resource limits only after the experiment succeeds.
6. Keep the feature disabled by default until quality and operational costs are accepted.

**Exit criteria:** reproducible quality evidence, bounded resource use, safe cancellation/restart, and a documented decision to proceed or stop.

## 9. Operational and safety requirements

### 9.1 Background work

- Provider enrichment and audio analysis must not run inside ordinary page requests.
- Jobs should be incremental, idempotent, resumable, and bounded.
- Use existing background-work and persistence conventions after inspecting them; do not introduce a second scheduler without a clear reason.
- Avoid duplicate jobs for the same entity and generation.
- Keep the last-known-good data when a refresh fails.
- Expose job state and last successful refresh without exposing provider credentials or sensitive request details.
- Prioritize newly added or recently accessed content when resource budgets are limited.

### 9.2 Rate limits and provider failures

- Respect each provider's documented rate limits and User-Agent requirements.
- Cache negative results with a bounded lifetime to avoid hammering missing records.
- Use explicit timeouts, bounded retries, and per-provider budgets.
- A timeout or provider outage should produce a partial result, not erase previously useful metadata.
- Do not make a provider's availability a prerequisite for playback, library browsing, or acquisition.

### 9.3 Identity and false relationships

- Prefer stable identifiers to title/artist text matching.
- Do not equate a MusicBrainz release with its release group or a recording with its work.
- Treat ambiguous matches as unresolved; do not silently select the first result.
- Keep artist aliases and credited artist strings distinct from canonical identity.
- Never infer a collaboration, influence, sample, nationality, or recording location from similarity alone.
- Preserve the ability to explain why two entities are connected.

### 9.4 Privacy and local media

- Listening history is personal data. Use only the already configured sources and their documented permissions.
- Do not send local audio files to a cloud service as part of this proposal.
- Local audio analysis should read files without modifying tags or audio.
- Never expose filesystem paths, Navidrome credentials, provider tokens, or internal storage details in client payloads.
- Do not let an intelligence result trigger acquisition, deletion, or import automatically. Existing explicit acquisition controls and safety checks remain authoritative.

### 9.5 Performance

- Avoid unbounded graph expansion. Require depth, result, and time limits.
- Paginate large relationships and discographies.
- Cache normalized source observations separately from derived summaries.
- Invalidate or refresh data by entity/provider generation rather than clearing unrelated caches.
- Measure memory and storage growth on a realistic library before enabling full-library graph or audio jobs.

## 10. Testing and acceptance strategy

Use docs/TEST_PLAN.md as the baseline. Every phase should add tests for both useful results and safe failure behavior.

### Data and identity tests

- Exact MBID and ISRC matching.
- Alias and punctuation normalization.
- Ambiguous artist and album names.
- Release versus release-group distinction.
- Recording versus work distinction.
- Duplicate and conflicting provider facts.
- Missing, malformed, stale, and partial provider responses.

### Relationship tests

- Relationship type and role preservation.
- Source provenance and evidence class.
- Confidence handling without fabricated certainty.
- Graph depth and result limits.
- Cycles and duplicate edges.
- Unverified inference never rendered as a verified credit.

### Collection-intelligence tests

- Owned/unowned correctness.
- Multi-disc and incomplete-album cases.
- Rediscovery score boundaries and sparse history.
- Blind-spot comparison sets and explanation text.
- Dismissal/feedback behavior and persistence.
- Stable results when one provider is unavailable.

### Audio-analysis tests

- Unsupported/corrupt files.
- Cancellation and restart.
- Duplicate job prevention.
- CPU/memory/time limits.
- Deterministic feature serialization.
- No modification of source files or tags.
- Similarity quality evaluation on a documented, varied sample.

### API and client tests

- Contract fixtures for every new response.
- Partial-result and unavailable-reason behavior.
- Pagination and stable ordering.
- No secrets or local paths in payloads.
- macOS and Android decode the same server contract.
- UI changes follow the applicable manual testing requirements in docs/LOCAL_UI_TESTING.md and the client contracts.

Do not claim success from a passing unit suite alone. Keep implemented, tested, CI-passed, merged, published, deployed, and runtime-verified as separate states.

## 11. Prioritization

A practical initial ranking:

| Priority | Capability | Reuse / cost | Why it ranks here |
|---|---|---|---|
| 1 | Field-availability and identity audit | Low | Prevents building on fields the installed server does not actually provide |
| 2 | Provenance and relationship foundation | Medium | Unlocks most other ideas and prevents false claims |
| 3 | Forgotten gems | Low–medium | Uses existing history and owned-library data |
| 4 | Collection blind spots | Medium | High user value without audio analysis |
| 5 | Album archaeology and release families | Medium | Builds on MusicBrainz IDs and existing album detail |
| 6 | Session musicians, producers, labels | Medium | High discovery value once relationships are reliable |
| 7 | Musical atlas and discovery paths | Medium–high | Strong client experience built on the graph |
| 8 | Personal musical fingerprint | Medium | Reuses listening history but needs careful interpretation |
| 9 | Covers, versions, and sample ancestry | Medium–high | Valuable but dependent on relationship coverage |
| 10 | Sonic DNA | High | Potentially transformative, but resource-intensive and requires quality evaluation |
| 11 | Album sequencing analyst | High | Experimental and dependent on validated audio features |

## 12. Decisions required before implementation

The following are deliberately left open. This document does not answer them on the owner's behalf.

1. Which first user-facing outcome matters most: the musical graph, forgotten gems, collection blind spots, or album archaeology?
2. Should the first phase be strictly read-only and avoid all new provider requests until the Navidrome field audit is complete?
3. Which external sources are acceptable for new enrichment, and what provider request budget is acceptable?
4. Should the knowledge graph initially cover only entities connected to the owned library, or also expand to a bounded set of unowned discovery candidates?
5. Should local sonic analysis be pursued at all on the current server hardware, or remain a separate optional experiment?
6. Which parts should appear first on macOS, and which are useful enough to justify compact Android views?

## 13. Research references

The following primary documentation and product references informed this proposal. Re-check them before implementation because API support, product behavior, and provider terms can change.

### Navidrome and Subsonic

- [Navidrome Subsonic API compatibility](https://github.com/navidrome/website/blob/master/content/en/docs/developers/subsonic-api.md) — implemented endpoints and Navidrome-specific notes.
- [Navidrome API v1](https://www.navidrome.org/docs/developers/api-v1/) — explicitly work in progress and not ready for implementation.
- [Navidrome Subsonic API handlers](https://github.com/navidrome/navidrome/blob/master/server/subsonic/api.go) — upstream method registration, including Sonic-related handlers.
- [Navidrome Subsonic response helpers](https://github.com/navidrome/navidrome/blob/master/server/subsonic/helpers.go) — examples of OpenSubsonic metadata populated from media-file fields.
- [Subsonic API reference](https://www.subsonic.org/pages/api.jsp) — baseline method and response contract.
- [OpenSubsonic Child response](https://opensubsonic.netlify.app/docs/responses/child/) — optional song/child fields and extensions.

### Music identity and listening

- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) — entities, lookup/browse/search, relationships, and request behavior.
- [Cover Art Archive API](https://musicbrainz.org/doc/Cover_Art_Archive/API) — release and release-group artwork.
- [ListenBrainz API](https://listenbrainz.readthedocs.io/en/latest/users/api/) — history, statistics, metadata, and recommendations.
- [ListenBrainz statistics](https://listenbrainz.readthedocs.io/en/latest/users/api/statistics.html) — time ranges, era activity, genre activity, and other listening statistics.
- [ListenBrainz recommendations](https://listenbrainz.readthedocs.io/en/latest/users/api/recommendation.html) — collaborative-filtering recording recommendations.
- [ListenBrainz history exports](https://listenbrainz.readthedocs.io/en/latest/users/api/export.html) — bulk versus incremental history retrieval.
- [Discogs API documentation](https://www.discogs.com/developers) — optional release, master, artist, and label data.

### Product and audio-analysis inspiration

- [Roon metadata model](https://help.roonlabs.com/portal/en/kb/articles/metadata-model) — object graph, credits, performers, compositions, labels, and roles.
- [Plex Sonic Analysis](https://support.plex.tv/articles/sonic-analysis-music/) — sonic similarity, track/album radio, mixes, and operational cost.
- [Essentia](https://essentia.upf.edu/) — open-source audio-analysis toolkit.
- [AcousticBrainz](https://musicbrainz.org/doc/AcousticBrainz) — historical audio-feature project; collection of new submissions stopped in 2022.

---

## 14. Final recommendation

Build the **Music Intelligence foundation** first: stable entity identity, typed relationships, provenance, confidence, freshness, and bounded caching. Then deliver one useful collection feature—preferably Forgotten Gems or Collection Blind Spots—as the first consumer of that foundation.

The musical knowledge graph should be the long-term centre of Server V2. It unlocks personnel discovery, label archaeology, album histories, musical geography, cover/version exploration, and explainable discovery paths. Sonic analysis is potentially the biggest differentiator, but it should remain a measured experiment until its quality and resource costs are proven on the actual server.

The outcome should be a server that can tell the clients not only **what an album is**, but **how it connects to the rest of music, why it may matter to this listener, and what interesting path to explore next**.
