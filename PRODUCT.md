# Product

<!-- impeccable:product-schema 1 -->

## Platform

A self-hosted, single-owner music-library platform with three clients:

- **Web:** responsive browser interface for discovery, library exploration, music knowledge, acquisition, settings and administration. The web client is not an audio player. Lives in `abucalip/navi-librarian` alongside the server and shared API contracts.
- **Android:** native music player and Librarian companion, including library browsing, discovery, acquisition, playback, radio and listening features. Lives in `abucalip/discair-android`.
- **macOS:** native Apple Silicon desktop player and Librarian companion, with the same core music and acquisition capabilities plus desktop-oriented navigation, queue, playback and knowledge-exploration experiences. Lives in `abucalip/discair-macos`.

The Python/FastAPI server is the shared source of truth for library-aware discovery, provider access, acquisition, radio metadata, persistent state and derived intelligence. Clients consume its APIs and Navidrome's music-server APIs; they do not independently reproduce server-side recommendation, provider or acquisition rules.

## Users and operating context

The product is designed first for one person self-hosting Navidrome and slskd, typically on a home server and accessed over a local network or private remote connection. Multi-user household accounts, public hosting and a commercial streaming service are not product goals.

The owner has an existing music collection and listening history. The product helps them:

1. Understand and explore the music they already own.
2. Discover worthwhile music that is not already in the collection.
3. Understand why an album or artist is relevant, using listening, library and music-knowledge evidence.
4. Acquire missing music through the configured Soulseek/slskd workflow, with visible and recoverable status.
5. Listen to owned music through the native clients, and explore internet radio where supported.
6. Learn more about artists, recordings, releases, labels, works, places, events and relationships represented in the collection.

The system is a companion to a self-hosted library, not a replacement for Navidrome, a general-purpose streaming catalogue, or a social music network.

## Product purpose and positioning

Librarian connects a personal music library to music discovery, contextual knowledge and controlled acquisition. It combines the practical loop of **discover → understand → acquire → listen** with tools for exploring the history and relationships behind the collection.

Unlike a generic recommendation feed, discovery is grounded in what the owner already has and listens to. Recommendations should help expand the collection rather than repeatedly surface owned albums or optimize for broad popularity. Unlike a streaming service, acquisition is directed into the owner's own library and its progress can be followed.

The product has two complementary roles:

- **Library companion:** browse and play the owner's collection, manage the listening experience, and surface useful information about the music.
- **Music intelligence and acquisition layer:** discover missing music, connect entities and historical context, identify library issues, and safely coordinate requests and imports.

## Core capabilities

The following describes functionality present in the repository. It is a product-level map, not a guarantee that every feature is enabled in every deployment or exposed identically by all clients.

### Library and music browsing

- Browse owned artists, albums, genres and tracks using Navidrome as the library source.
- Search across library entities and distinguish music already owned from music outside the collection.
- Open artist and album pages with artwork, release information, tracklists, biographies/descriptions, links, reviews and other provider-backed sections when available.
- Explore related artists, similar music, release information and the connections between music entities.
- View collection-oriented timelines, maps and relationship explorations where the underlying MusicBrainz data supports them.
- Surface library metadata health and unresolved identity information as read-only worklists; these tools do not silently rewrite tags or modify files.

### Discovery and collection building

- Personal discovery informed by ListenBrainz collaborative filtering and the owner's library/listening context.
- Dedicated discovery surfaces for personal discoveries, new releases, classics/collection-building and artist deep dives.
- Additional discovery lenses and insight cards, including forgotten gems, blind spots, series completion, hidden canon and anniversaries where enabled and supported by available data.
- Genre/lens-based exploration and controls to save, dismiss, hide an artist, block a genre, or express more/less interest in an artist.
- Discovery settings and feedback are persisted by the server and applied consistently across supported clients.
- Owned-album exclusion and artist/release identity checks are core correctness requirements. Missing provider data must degrade gracefully rather than break a list.
- Popularity and contextual metadata are sourced from supported providers such as ListenBrainz, MusicBrainz and Deezer; the product does not depend on Last.fm.

### Music knowledge and context

- A locally stored MusicBrainz knowledge dataset and relationship graph supports richer entity pages and exploration beyond the basic artist/album catalogue.
- Knowledge coverage includes entities and relationships such as artists/people, recordings, releases/release groups, labels, works, places and events, subject to the imported dataset and available links.
- Explore connections and paths between music entities, and view geographic or chronological context through the clients that expose those experiences.
- Album and artist dossiers can combine library facts, MusicBrainz data, biographies and descriptions, reviews, artwork and external links.
- Provider provenance, match quality, coverage and missing-data states should remain visible or represented honestly; the product must not turn absence of evidence into a factual claim.

### Listening insights

- Listening history from Navidrome and ListenBrainz informs discovery and can be presented as collection and taste insights.
- Taste profiles compare recent, intermediate and all-time listening windows and can show dimensions, shifts and listening-context patterns when sample sizes and attribution are sufficient.
- Insights are descriptive. They do not silently change recommendation ranking, and low-sample or incomplete data must be presented honestly.
- Radio listening history is represented separately from ordinary library playback where appropriate.

### Playback and radio

- Android and macOS are native playback clients for the owner's Navidrome library.
- Playback capabilities include queue management, gapless playback, crossfade, equalizer controls, media-key integration, Now Playing and lyrics; exact controls vary by platform.
- The macOS player is built with native Apple technologies for Apple Silicon and includes desktop-oriented playback and navigation experiences.
- Internet radio is supported in the native clients through the server's station and relay functionality. Station management includes favourites, tags and logos; clients can show live song metadata, an On Air state and a Heard history.
- A live radio song can be matched against the library and, when the server has sufficient metadata and play evidence, offered for acquisition through the normal server-side workflow.
- Radio recording is out of scope. The web client does not play music or radio.

### Acquisition and import

- The owner can request missing albums through the configured slskd service.
- Candidate results are grouped and assessed using album/release context and quality information; acquisition state and progress are visible in the clients.
- Downloads and imports are coordinated by the server. Clients do not independently download or move music files.
- Import and cleanup operations are safety-critical: canonical paths must remain within configured roots, ambiguous or unsafe targets must be rejected, and unrelated files must never be overwritten or deleted.
- Actions must report confirmed server state, distinguish pending/success/failure/recoverable states, and avoid duplicate requests.

### Settings, diagnostics and operation

- Configure Navidrome, Librarian and slskd connectivity, ListenBrainz integration, discovery behaviour, playback and appearance settings where supported.
- The server includes background workers for bounded refresh, enrichment and precomputation; provider work should not be duplicated on every page request.
- Diagnostics expose relevant runtime and provider activity without leaking credentials, private URLs or personal identifiers.
- Persistent application state and caches are designed to survive container restarts and upgrades.
- The product is self-hosted. Deployment, publication and runtime verification are separate from code being merged.

## External data and service boundaries

The server integrates with external music services to enrich and connect the owner's library. Current integrations include:

- **Navidrome:** library, playback and music-server interface.
- **slskd:** Soulseek search, download and acquisition workflow.
- **ListenBrainz:** listening history, collaborative-filtering recommendations, popularity and related music data.
- **MusicBrainz:** artist, recording, release, release-group, label, work, place and event metadata; the imported MusicBrainz dataset also powers local knowledge-graph exploration.
- **Discogs:** release/style information that complements MusicBrainz, including discovery and release context.
- **Deezer, Apple Music and Qobuz:** selected album, track, link and popularity/context lookups where available.
- **Wikipedia and Wikidata:** artist and music-related descriptions and structured context.
- **Album review sources:** supported editorial outlets, including Pitchfork, The Guardian (when configured) and other supported review publishers.
- **Cover Art Archive and Radio Browser:** artwork and radio-station metadata/logo discovery.

Provider availability, credentials, quotas, coverage and licensing vary. Integrations are optional where possible; failure or absence from one provider must not make the core library or discovery experience unusable. Provider requests are paced, cached and budgeted. Batch APIs are preferred whenever the provider offers them.

Last.fm is no longer an active product dependency. Discovery popularity, listening-history and radio scrobbling/love functionality have been migrated to ListenBrainz and the remaining provider-specific code and settings have been removed. Do not describe Last.fm as a current integration or require a Last.fm API key.

## Client experience and visual identity

The clients share product concepts and server-owned behaviour, but each has a platform-appropriate interface rather than being a web page wrapped in a native shell.

- The web client is a responsive single-page application served by FastAPI. It has multiple appearance themes, including the original Ink visual system, Neobrut themes and the opt-in Listening Room foundations. It remains a non-player interface.
- Android is a native Kotlin application with multiple visual themes and native playback, library and discovery flows.
- macOS is a native Swift application with distinct Cupertino and editorial/Zine-style visual systems, desktop navigation, native playback and music-knowledge exploration.
- Artwork is a primary visual element, while metadata and provenance provide supporting context.
- Interaction, accessibility, focus, reduced-motion behaviour and honest state communication are product requirements, not final polish.

## Product principles

1. **The owner's library comes first.** Discovery should expand the collection, not repeatedly recommend what is already owned.
2. **Context over popularity.** Use listening, collection and music-history evidence; do not mistake popularity for personal relevance.
3. **One server-owned truth.** Shared business rules, provider access, acquisition and persistent state belong on the server. Clients present the result and send explicit user actions.
4. **Evidence and uncertainty stay visible.** Distinguish known, inferred, incomplete and unavailable information. Never invent certainty from missing data.
5. **Safe by default.** No silent tag rewriting, unsafe file operations, hidden acquisition, or destructive guesses.
6. **Graceful degradation.** Optional providers and optional intelligence must fail independently without breaking core library use.
7. **Native where it matters.** Playback and platform-specific interaction should feel at home on each supported client.
8. **Honest state.** Pending, confirmed, failed and recoverable states are visibly different and never communicated by colour alone.
9. **Accessible and restrained.** Keyboard operation, visible focus, sufficient contrast, touch-target sizing and reduced-motion preferences are baseline requirements.

## Operating and scope constraints

- The supported deployment is a self-hosted FastAPI application with background worker(s), persistent data and configured connections to Navidrome and slskd.
- Python and FastAPI remain the default server architecture. Shared domain logic must not be duplicated in client applications.
- The web client does not play audio or radio. Playback is provided by the native Android and macOS clients.
- No multi-user account model, public social network, commercial streaming catalogue, App Store distribution or general-purpose audio-tag editor is a product goal.
- Audio analysis and recommendation features must be bounded, measurable and separated from request-time page rendering. Read-only intelligence must remain separate from acquisition, import and media mutation.
- No provider integration may bypass pacing, caching, budget or credential-handling rules.
- Do not introduce third-party runtime assets or new provider dependencies without evaluating licensing, privacy, operational cost and failure behaviour.
- Product behaviour and API contracts must be documented before clients depend on new endpoints or fields. The API and regression tests, not a client mockup, define what the server actually guarantees.

## Accessibility

The web experience targets WCAG 2.1 AA, with visible keyboard focus, keyboard-operable controls, 44 × 44 px minimum touch targets where applicable, reduced-motion support and status that is never conveyed by colour alone. Native clients must provide equivalent platform-appropriate accessibility, including VoiceOver/TalkBack semantics, adequate contrast and reduced-motion behaviour. Manual screen-reader coverage should be reported accurately rather than assumed.
