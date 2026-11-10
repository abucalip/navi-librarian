# Discair upgrades — product proposal

**Status:** Proposal for owner review; no implementation is authorized by this document.  
**Research basis:** A code-level review of [Aurral](https://github.com/lklynet/aurral), compared with Discair's current GitHub `main`, macOS client, and Server V2 contracts.  
**Scope:** Potential product and client/server improvements. This is not a commitment to copy Aurral's architecture or feature set.

## Executive summary

Aurral offers several useful ideas for making music discovery more interactive: explicit recommendation feedback, a unified activity inbox, configurable discovery feeds, and regenerating playlist flows. Discair already has deeper foundations in several adjacent areas—taste profiles, a music knowledge graph, artwork exploration, acquisition, smart playlists, listening history, and native playback.

The opportunity is therefore not to reproduce Aurral. It is to connect Discair's existing capabilities into a more responsive exploration experience:

1. Let the listener explain why a recommendation is or is not useful, and use that feedback deliberately.
2. Surface meaningful developments around the listener's musical world in one **Music Radar**.
3. Turn taste, graph relationships, obscurity and library context into temporary **Listening Sessions**.
4. Make Discover more configurable once its content sections are stable.
5. Extend artist exploration and use Discair's artwork knowledge to enrich playlist identity.

The first two are the strongest candidates for investigation. Listening Sessions could become a distinctive Discair feature, but should follow a clear definition of queue generation and feedback semantics.

## What the Aurral code suggests

The review focused on Aurral's discovery and frontend code, including:

- `backend/services/discovery/recommendationPipeline.ts`
- `backend/services/discovery/feedback.ts`
- `backend/services/discovery/tasteProfile.ts`
- `frontend/src/hooks/useArtistTasteFeedback.ts`
- `frontend/src/components/InboxMenu.tsx`
- `frontend/src/pages/DiscoverPage.tsx`
- `frontend/src/pages/playlists/FlowEditor.tsx`
- Artist detail and playlist-cover components.

These are design references, not implementation dependencies. Aurral's service boundaries, data model, provider choices and ranking behavior should not be transplanted into Discair without a separate technical review.

## Proposed upgrades

### 1. Contextual recommendation feedback

**Priority: P1 — investigate first**

Give album and artist recommendations explicit, understandable feedback actions. Possible actions:

- **More like this:** request more discoveries along the musical direction represented by this item.
- **Less like this:** reduce similar recommendations.
- **Already know this:** distinguish familiarity from disinterest.
- **Not interested:** record a negative preference without permanently excluding the artist.
- **Never recommend this artist:** an explicit, reversible exclusion.

The interface should explain the scope of each action. For example, “Less like this” should not silently mean “hide this artist”, and “Already know this” should not be interpreted as a negative taste signal.

**Discair-specific design**

Feedback should be contextual and evidence-aware. Where the recommendation has known reasons—shared artists, genres, labels, eras, graph paths or taste dimensions—the UI could offer a choice between responding to the item itself and responding to the connection that led to it. Do not offer a dimension-specific action unless the server can identify that dimension reliably.

Keep feedback separate from acquisition actions (Get, Save and dismissal) and from playback skip events. A skip is not necessarily dislike; a user may simply not want to listen at that moment.

**Important existing constraint**

Discair's current macOS `FeedbackEvent` / `FeedbackOutbox` path records skip and dismiss events. Its documented contract is record-only: it does not affect ranking. This proposal does not authorize changing that behavior implicitly. Recommendation-affecting feedback needs an explicit Server V2/API contract, a defined event vocabulary, persistence and migration rules, idempotent submission, privacy review, and regression tests.

**Acceptance criteria for a future implementation**

- Each action has a precise, documented meaning and reversible behavior where appropriate.
- Feedback is attached to stable artist/album identifiers, not display strings alone.
- Offline submission is durable, bounded and idempotent; rejected events are not retried unchanged.
- The server reports what it accepted and why it rejected invalid events.
- Ranking changes are separately specified, deterministic where practical, and covered by before/after replay tests.
- “Already know”, “not interested”, “dismiss”, “skip” and “block” remain distinct concepts.
- The client never claims that ranking has changed until the server contract supports it.

### 2. Music Radar — a personal music activity feed

**Priority: P1 — investigate alongside feedback**

Create one chronological place for noteworthy events connected to the library and the listener's interests. Unlike Discover, which presents candidates to explore, Music Radar should answer: **what has changed or become newly interesting in my musical world?**

Potential event types, only where reliable data exists:

- New releases by artists represented in the library or explicitly followed.
- New discoveries surfaced by Discair, with the reason they were selected.
- Newly available knowledge about an artist, album, collaborator, label or place.
- A newly completed or changed connection in a graph/path the listener has explored.
- A relevant anniversary or historical event, when the date and association are well sourced.
- Acquisition milestones, such as a requested album becoming available or a download completing, if these are not better handled by the existing Pipeline Dock.

Each item should show its source, date, subject and a useful action (open artist, album, connection, discovery or download). Allow dismissing items and filtering by event type. Avoid turning every background data refresh into a notification.

**Discair-specific opportunity**

Use Server V2's knowledge and artwork data to make events richer than generic alerts. For example, a new collaborator connection could open the relevant Connections view; a newly indexed booklet or edition could open the album's artwork view. The event must be grounded in stored data and clearly distinguish a newly discovered fact from a newly occurring event.

**Architecture direction**

Treat the feed as a projection of durable, typed events, not a collection of client-generated guesses. Define event identity, source, timestamp, subject reference, read/dismiss state, and supported actions. Prefer existing Server V2 resources and change tracking where they fit; do not create a second source of truth for knowledge, discovery or acquisition state. Decide explicitly whether the feed is server-owned, client-local, or hybrid before implementation.

**Acceptance criteria**

- Events are stable across refreshes and do not duplicate on every app launch.
- Every factual statement has a traceable source and event time semantics.
- Unavailable or stale data is represented honestly; no fabricated “new release” or “new connection” claims.
- Dismissal is persistent and reversible if appropriate.
- Feed loading and pagination do not block playback or normal browsing.
- Existing Downloads, Timeline, Insights and Discover remain useful and are not simply duplicated.

### 3. Listening Sessions — dynamic, temporary listening queues

**Priority: P2 — high product potential**

A Listening Session is a generated queue with a clear musical intention. It is not necessarily a permanent playlist and should not require the listener to build rules manually.

Candidate sessions:

| Session | Intended selection |
|---|---|
| Forgotten Gems | Underplayed albums or tracks already in the library, subject to adequate listening evidence |
| Deep Exploration | Discoveries reached through one or more meaningful knowledge-graph connections |
| Beyond Your Comfort Zone | Less familiar artists, genres or eras, with a controlled degree of novelty |
| Regional / historical journey | A coherent place, period or scene, using sourced context |
| Artist deep dive | A balanced path through owned recordings and eligible missing albums |
| Sunday Jazz / similar mood | A user-named session built from explicit taste and library constraints |

A session should explain why its items were selected and let the listener adjust duration, familiarity, obscurity and owned-versus-missing balance where those controls are supported by real server data.

**Discair-specific design**

Combine existing taste profiles, graph relationships, obscurity classifications, sonic paths, listening history and acquisition state. Do not treat all these signals as interchangeable. A taste profile is descriptive context; it must not affect recommendation ranking unless a separate decision explicitly authorizes that. Likewise, do not invent obscurity or lens values when the server has not supplied them.

The first version should generate a temporary queue from owned tracks and clearly identified playable items. Missing albums can be offered as Get actions or as a separate discovery segment; they must not silently enter a playable queue.

**Relationship to existing features**

- Smart Playlists remain saved, editable rule sets.
- Saved Queues remain snapshots of an arranged queue.
- Listening Sessions are generated, disposable listening experiences.
- “Radio from this” remains a continuous similarity-based playback mode if/when implemented.

**Acceptance criteria**

- The session's selection logic runs in shared server/domain logic, not duplicated in SwiftUI.
- Every generated item has an explainable inclusion reason.
- The queue is playable and respects library ownership, availability and existing playback rules.
- Regeneration is explicit; it does not unexpectedly replace a queue already being played.
- Session settings and history have a defined persistence policy.
- Empty and sparse-data cases are honest and useful.

### 4. Configurable Discover dashboard

**Priority: P3 — after section definitions stabilize**

Allow the listener to choose which Discover sections appear and in what order. Potential sections include:

- For you / personal discoveries.
- Classics and collection-building.
- New releases.
- Artist deep dives.
- Connected artists and albums.
- Unexplored genres or eras.
- Missing albums from artists already in the library.
- Listening Sessions.

Start with visibility and ordering. Avoid a complex drag-and-drop page builder or arbitrary user-authored queries.

**Acceptance criteria**

- Defaults remain useful for a new installation.
- Preferences persist per client or account according to an explicit decision.
- A hidden section can still be reached through navigation or search.
- Section loading is independent; a failed section does not break the page.
- The dashboard does not introduce a second ranking implementation.

### 5. Deeper artist exploration

**Priority: P3 — incremental extension**

Aurral's artist details emphasize similar artists, videos and “Appears On” material. Discair already has richer foundations: biographies, top songs, owned-album artwork, Timeline, Connections, Atlas and MusicBrainz knowledge.

Potential additions:

- A dedicated **Appearances and contributions** view for compilation appearances, guest performances, session credits and collaborations.
- Clear distinctions between performer, composer, producer, arranger, engineer and other credit roles.
- A path from a credit to the associated recording, release and artist.
- Filters for owned recordings versus recordings missing from the library.

This should use Discair's MusicBrainz/knowledge data and preserve source attribution. Do not imply a credit exists when only an artist-name similarity is known. The UI should distinguish release-level credits from recording-level credits.

**Acceptance criteria**

- Credits are role-aware and linked to stable knowledge identifiers.
- Ambiguous matches are labelled or omitted, never silently asserted.
- Existing Connections and Timeline remain complementary rather than duplicated.

### 6. Artwork-led playlist and session identity

**Priority: P4 — visual enhancement**

Aurral's playlist-cover templates suggest a useful visual feature, but Discair has a richer source of visual material: album editions, booklet pages, liner notes, artist photographs, posters and other indexed artwork.

Explore generated compositions for playlists and Listening Sessions, for example:

- A contact sheet of the session's album covers.
- A restrained collage of selected artist photographs.
- A booklet-inspired title treatment using artwork already associated with the selected albums.
- A user-selected cover face or artwork source.

The first iteration should be deterministic composition from existing images and typography—not generative AI, image synthesis, or a new artwork-provider dependency. Keep the original artwork intact and make the composition reversible.

**Acceptance criteria**

- Every image comes from an identified, permitted artwork source.
- Composition does not alter or overwrite original library artwork.
- Fallbacks are graceful when images are missing.
- The owner can choose or restore a conventional cover.
- Generated compositions are cached and invalidated when their inputs change.

## Suggested delivery order

| Order | Work | Why |
|---|---|---|
| 1 | Define recommendation feedback semantics and API | Establishes whether and how user input can safely influence discovery |
| 2 | Music Radar event model and first useful event types | Connects existing capabilities into a coherent daily experience |
| 3 | First Listening Session using existing, reliable signals | Tests a distinctive Discair experience without building a generic playlist engine |
| 4 | More session types and controls | Add only when each signal has clear semantics and coverage |
| 5 | Configurable Discover sections | Improve navigation after the section catalogue is stable |
| 6 | Artist appearances/contributions | Extend existing knowledge views with role-aware credits |
| 7 | Artwork-led playlist/session covers | Visual polish after the underlying session model exists |

This order is a recommendation, not an approved schedule. Each item should be split into small, independently reviewable slices with its own contract and acceptance criteria.

## Product and architecture guardrails

1. **GitHub remains the source of truth.** Verify current code and contracts before each implementation; this proposal is not a substitute for source inspection.
2. **Reuse Discair's domain logic.** Recommendation, graph traversal, event creation, session selection and acquisition policy belong in existing server/domain layers, not duplicated in client views.
3. **No silent ranking changes.** Taste profiles, feedback events and new signals do not affect ranking until their semantics and tests are explicitly approved.
4. **No invented music facts.** Attribute credits, dates, release information, relationships and artwork to their sources; expose uncertainty and missing coverage.
5. **Preserve safety and ownership boundaries.** Listening queues must not trigger acquisition automatically. Get remains explicit, and no proposal here authorizes deletion, overwriting or unreviewed downloads.
6. **Keep playback independent.** Feeds, artwork and discovery refreshes must not block the audio path or interrupt an active queue.
7. **Measure usefulness, not feature count.** Define success measures before implementation: meaningful feedback usage, reduced repeated/irrelevant recommendations, useful Radar engagement, and session starts/completions—without collecting unnecessary personal data.
8. **Keep verification states separate.** Implemented, tested, CI-passed, merged, published, deployed and runtime-verified are different states. UI changes require the project's documented UI verification.

## Research references

### Aurral

- [Repository](https://github.com/lklynet/aurral)
- [Recommendation pipeline](https://github.com/lklynet/aurral/blob/main/backend/services/discovery/recommendationPipeline.ts)
- [Feedback service](https://github.com/lklynet/aurral/blob/main/backend/services/discovery/feedback.ts)
- [Taste profile service](https://github.com/lklynet/aurral/blob/main/backend/services/discovery/tasteProfile.ts)
- [Discover page](https://github.com/lklynet/aurral/blob/main/frontend/src/pages/DiscoverPage.tsx)
- [Inbox component](https://github.com/lklynet/aurral/blob/main/frontend/src/components/InboxMenu.tsx)
- [Flow editor](https://github.com/lklynet/aurral/blob/main/frontend/src/pages/playlists/FlowEditor.tsx)

### Discair

- [macOS client contract](MACOS_CLIENT_CONTRACT.md)
- [Server V2 remaining work](ServerV2.md)
- [Server V2 API contract](SERVER_V2_CONTRACT.md)
- [Requirements](REQUIREMENTS.md)
- [Architecture overview](ARCHITECTURE.md)
- [Development workflow](DEVELOPMENT_WORKFLOW.md)

## Decision requested

Review the priorities and product semantics, especially:

1. Whether recommendation feedback should eventually influence ranking, and which actions should do so.
2. Whether Music Radar should be a server-backed event feed or a client-local aggregation of existing resources.
3. Whether Listening Sessions should initially contain only owned/playable tracks, with missing albums shown separately as acquisition suggestions.

Until those decisions are made, this document remains an exploration proposal; no code or API behavior should be inferred from it.
