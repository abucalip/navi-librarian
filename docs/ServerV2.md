# Server V2: Music Intelligence Plan

**Status (2026-11-06):** Phases 0 to 5 are closed on the server side; Phase 6 is in progress (slices 1 to 11b merged: time-windowed profiles, listens loader, persistence/read route, obscurity builder, batch ListenBrainz popularity fetcher, monthly snapshot builder, listening-context profiles, suppression builder and persistence/routes, plus macOS feedback client, playback skip reporting and outbox durability correction, PRs #847 to #859; slice 11c PR #860 is open) and Phase 7 is open, and Phase 7 now also carries the Phase 5 leftovers. The owner accepted D-1 to D-6, decided D-7 (own SQLite file, D-026), and opened each gate in turn; D-8 and D-9 are open. **Phase 0** (audit, see [`SERVER_V2_PHASE0_AUDIT.md`](SERVER_V2_PHASE0_AUDIT.md)) and **Phase 1** (store, resolution, jobs, Library Health) are complete. **Phase 2** (editions, duplicates, edition advisor, edition-aware ownership behind a flag) is built, PRs #770 to #774. **Phase 3** (collection intelligence as lenses) is complete: all five lenses and the `/api/insights` routes are on by default (PR #808; `NAVI_INSIGHT_LENSES` unset means all five, empty means none); Forgotten Gems stays empty until Navidrome holds 180 days of history, and card review and a full-library run were waived by the owner. **Phase 4** (dossiers, people, labels, works) is complete: the MusicBrainz dump slice was imported on the owner's Mac (752,342 entities, 1,744,255 edges, 1.1 GB, no budget breached), served through the `KnowledgeReader` facade and `/api/knowledge/*` routes, and its exit check passed on the real slice (PR #838). **Phase 5** (context, atlas, paths) is closed (owner decision, 2026-11-06): Wikidata ingest (#845), areas, places and events (#839, #844), catalogue numbers, formats and label parents (#843), and the paths builders and route for the four kept kinds (#841, #842); the exit check passed on the real store (#846, slowest build 1.6 s). Its client gate and remaining tasks moved to Phase 7.

## 1. Goal and principles

Make Librarian the single place that turns raw library, listening and provider data into prepared, explainable results that macOS and Android render without computing anything themselves.

Principles (these decide disputes):

1. **Foundation before features.** Identity, provenance and storage come first; no feature ships on guessed identities.
2. **Prove data exists before designing on it.** Every phase starts with a measurement, and a feature is cut if coverage is too low.
3. **Reuse before building.** Prefer Navidrome capabilities, existing Librarian caches, Engine 2 lenses and existing provider clients over new subsystems.
4. **Facts, derivations and opinions are stored separately** and never overwrite each other.
5. **Explainable or absent.** Every result carries `reasons[]` with evidence; if it cannot explain itself it is not shown.
6. **Optional and degradable.** Any provider, plugin or analysis job can be absent without breaking playback, browsing, discovery or acquisition (D-007).
7. **Read-only toward media.** Intelligence never modifies files, tags, or triggers acquisition/deletion/import (the existing explicit controls stay authoritative).
8. **Thin routes, no navidrome_server.py additions** (D-016). New code lives in importable packages with direct-import tests.

## 2. Scope and non-goals

In scope: server-side data model, enrichment pipeline, derived insights, API contracts, capability negotiation, test and evaluation harness, client contract fixtures.

Out of scope for this plan: client UI design (separate client plans per phase), changing recommendation weights, any cloud upload of audio, Navidrome API v1 (still unstable), automatic acquisition.

## 3. Starting position (verify in Phase 0)

Already present per the research baseline: ListenBrainz/Last.fm/MusicBrainz integration, owned-library index (discovery/search), Engine 2 daily lenses (discovery/lens_service.py), artist/album detail APIs, feedback/saved/dismissed state, acquisition lifecycle, partial Discogs integration, macOS and Android clients consuming these.

Unverified assumptions that Phase 0 must settle (no design may depend on them until then):

- Which OpenSubsonic fields the installed Navidrome returns, and how many are populated for the owner's library.
- Whether `getOpenSubsonicExtensions` advertises `sonicSimilarity` (requires a sonic plugin such as AudioMuse-AI or a Plex-analysis plugin) and which Navidrome version is installed.
- Existing SQLite files, table conventions, migration mechanism, and background job runner.
- How ListenBrainz data is currently cached and how many listens map to MBIDs.
- Current state of the Discogs integration.

## 4. Target architecture

```
Providers (MusicBrainz slice, ListenBrainz, Last.fm, Wikidata, LRCLIB, Cover Art Archive, Discogs*)
Navidrome (Subsonic/OpenSubsonic, sonic extension*)          (* optional)
        |                                  |
   ingest adapters (existing clients)   ingest adapters
        |                                  |
        v                                  v
  observations (append-only, immutable source facts)
        |
  entity resolution service (single answer to "same thing?")
        |
  entities + edges (normalized, with evidence class)
        |
  derivation jobs (versioned by generation)
        |
  insights / cards / lens candidates (explainable, dismissible)
        |
  thin API routes + capabilities endpoint  ->  macOS / Android
```

Module layout (names illustrative, to be confirmed against repo conventions in Phase 0):

- `intelligence/store/` schema, migrations, repositories (SQLite).
- `intelligence/ingest/` one adapter per source, reusing existing provider clients and rate limiters.
- `intelligence/resolution/` identity ladder, normalization, unresolved queue.
- `intelligence/derive/` pure functions from facts to insights, one module per insight kind.
- `intelligence/jobs/` job definitions on the existing background runner.
- `app/api/intelligence.py` thin adapter only.

No second scheduler unless Phase 0 shows the existing runner cannot do resumable, bounded jobs; if so, record a decision (D-0xx) first.

## 5. Capability catalogue and disposition

| Capability | Source of truth | Disposition |
|---|---|---|
| Library health report | Navidrome fields + file facts | Phase 1 (new, high value, no providers) |
| Edition and duplicate detection | Navidrome + MusicBrainz release groups | Phase 2 |
| Forgotten Gems | Navidrome play data, ListenBrainz | Phase 3, as Engine 2 lens |
| Collection blind spots, series completion | MusicBrainz series/discographies, LB popularity | Phase 3 |
| Album dossier / release family | MusicBrainz, Cover Art Archive, Discogs* | Phase 4 |
| Personnel, producer, label views | MusicBrainz slice | Phase 4, gated on coverage |
| Covers/versions/work links | MusicBrainz works | Phase 4 |
| Influences, scenes, atlas | Wikidata + MusicBrainz areas | Phase 5 |
| Discovery paths | Graph + reasons | Phase 5 |
| Taste fingerprint, taste vs world, time capsule | Navidrome + ListenBrainz sitewide | Phase 6 |
| Context profiles, skip memory | Scrobbles + client events | Phase 6 |
| Sonic similarity/paths | Navidrome sonic extension (proxy) | Phase 7, in-house analysis only if proxy impossible |
| Album sequencing analyst | Audio features | Deferred; revisit after Phase 7 |
| Anniversaries / on-this-day | MusicBrainz life-span + dates | Phase 3 add-on |
| Smart playlists | Saved queries over insights | Phase 6 |

Dropped or demoted from the draft: knowledge graph as "centre" (now an outcome of Phases 1-5, not a precondition), sample/interpolation ancestry (no reliable open source identified; revisit only if a source is found), Essentia as the default (now a fallback).

## 6. Data design

### 6.1 Storage

SQLite, in the existing database or a new file chosen in Phase 0. No graph database, no vector database. Graph traversal is bounded recursive CTEs with depth, row and time limits. If embeddings are ever stored: float16 blobs, brute-force cosine search (sub-second under ~100k tracks).

### 6.2 Tables (conceptual)

- `observations(id, source, entity_hint, payload_hash, payload, fetched_at, expires_at, generation)`: append-only, one row per fetched source document. Never edited.
- `entities(id, type, mbid, navidrome_id, discogs_id, wikidata_id, canonical_name, sort_name, owned, created_generation)` with types: artist, person, group, recording, work, release, release_group, label, area, place, series, genre.
- `entity_aliases(entity_id, alias, kind)`: matching aids only, never identity.
- `edges(id, from_id, to_id, relation, role, evidence_class, match_quality, source, source_url, observation_id, valid_from, valid_to, generation)`.
- `unresolved(id, kind, navidrome_ref, candidates_json, reason, first_seen, status)`: ambiguous matches queue; status includes `user_confirmed` and `user_rejected`.
- `insights(id, kind, subject_id, payload, reasons_json, generation, computed_at, dismissed_state)`.
- `snapshots(period, taken_at, metrics_json)`: monthly collection/taste time capsules.
- `job_runs(job, entity_scope, generation, state, progress, started_at, finished_at, error)`.

### 6.3 Evidence classes and match quality

Evidence class: `source_explicit`, `library_tag`, `user_confirmed`, `derived`, `inferred`.
Match quality: `exact_mbid`, `isrc`, `fuzzy_confirmed`, `fuzzy_unconfirmed`, `unresolved`.
No floating-point confidence anywhere. Clients show the label, never a percentage. An `inferred` edge is never rendered as a credit.

### 6.4 Generations and invalidation

Every derivation stamps a `generation`. Matching-logic changes bump it and derived tables rebuild from observations without refetching. A global `data_version` per client-visible resource enables ETags and a `/changes?since=` feed so offline caches refresh cheaply.

### 6.5 Identity resolution ladder

1. Navidrome MBID tag (recording/release/release group/artist) present: trust it, record as `library_tag`.
2. ISRC match to a unique recording.
3. MusicBrainz search using album artist + title + track count + durations within tolerance; accept only if a single candidate clears all checks.
4. Anything else goes to `unresolved` with the candidate list. Never take the first result.

Rules: release is not release group; recording is not work; credited-artist strings are not canonical identity; conflicts between sources are stored side by side and surfaced, not merged silently. The unresolved queue gets a lightweight confirm/reject action so `user_confirmed` is actually producible.

### 6.6 Source precedence

- Owned-item play counts, stars, ratings, last-played: Navidrome is authoritative.
- Cross-library history, trends, and unowned items: ListenBrainz.
- Credits, relationships, dates: MusicBrainz (+ Wikidata for influences/origin).
- Editions, catalogue numbers, formats: MusicBrainz first, Discogs optional.
- Popularity: ListenBrainz popularity API first, Last.fm as fallback.
A missing ListenBrainz value is "unknown", never zero.

## 7. Provider strategy

**MusicBrainz local slice (recommended).** Import only entities within one to two hops of owned MBIDs from the periodic data dumps (or hybrid: dump for bulk, API for gaps). Pros: no rate-limit design pressure, local SQL graph queries, repeatable. Cost: import tooling and disk. Decision D-1 in section 12. Whichever path is chosen: descriptive User-Agent, bounded rates, negative-result caching, no unbounded crawl.

**ListenBrainz.** Extend existing use with: popularity batch endpoints, sitewide stats (for taste vs world), fresh releases, listening history exports for time windows. Verify exact endpoint paths against the official docs before coding (some paths in my research came from third-party wrappers). Respect token/permission settings; similar-users data only after a privacy decision.

**Wikidata.** Join through MBID-linked IDs to get influenced-by, genre, origin, founding dates. Each claim stored with the statement reference and `source_explicit`. Query volume small and cached.

**Cover Art Archive, LRCLIB, Fanart.tv/TheAudioDB.** Optional enrichment, release- or MBID-keyed, with attribution fields stored. LRCLIB only as a lyrics fallback; check terms before use.

**Discogs.** Inspect the current integration first; use for edition/catalogue enrichment only if it provides data MusicBrainz lacks. Never required.

**Navidrome.** Primary source. Use `getOpenSubsonicExtensions` for capability detection. Consider `getPlayQueue`/bookmarks for cross-device handoff (client plans, not this server plan).

**Hard rules for every provider:** per-provider budget, timeout, bounded retries, last-known-good retention on failure, partial results on timeout, never inside a page request.

## 8. API direction

Principles unchanged from the draft (stable IDs, typed entities, explicit availability reasons, cursors, no secrets or paths, no client re-ranking). Additions:

- **`/api/capabilities`** (or extension of an existing capabilities route, decide in Phase 0): lists which intelligence features are populated, graph coverage class, sonic available, ListenBrainz connected, data versions. Clients hide absent sections instead of rendering errors.
- **Uniform entity resource**: `entities/{type}/{id}` with ownership overlay, so any credit is tappable on both clients.
- **Insight cards**: `{kind, title, body, subject, actions[], reasons[], dismissible}`. A versioned card-kind registry; clients must render unknown kinds as a generic card or skip them, so the server can ship insights without a client release.
- **`reasons[]`**: structured, e.g. `{kind: "shared_personnel", entity_ids, evidence}`; macOS shows the inspector, Android a one-line summary from the same object.
- **`/changes?since=`** and ETags for offline caches.
- Route names stay provisional until the Phase 1 contract review. Every new endpoint requires a contract document and fixtures (android/contract-fixtures, macOS equivalent) before merge.

## 9. Phased plan

Each phase has: work items, exit criteria, **kill/pivot criteria**, and a client gate. A phase only starts after the previous exit criteria are met and the owner approves.

### Phase 0: Audit and measurement (read-only, no new provider traffic)

Work items:
1. Inventory Navidrome client methods, response shapers, callers and tests; list what each discards.
2. Probe the installed Navidrome: version, `getOpenSubsonicExtensions`, field availability on a representative sample (e.g. 100 albums, 500 tracks across genres/eras/formats). Produce the field-availability matrix (method, field, extension status, returned, populated %, scope, currently kept, intended use).
3. Probe `getSonicSimilarTracks`/`findSonicPath` read-only; record 404 vs working.
4. Measure MBID coverage: share of tracks/albums/artists with recording, release, release-group, artist MBIDs and ISRCs.
5. Measure MusicBrainz relationship coverage on a 200-album sample (via the existing client with the current cache, bounded request count): % with recording-level credits, labels, work links, series membership.
6. Measure ListenBrainz mapping rate for the owner's listens.
7. Inventory existing SQLite tables, migration and job conventions; inventory Discogs integration state.
8. Snapshot current macOS/Android payloads as regression fixtures.
9. Create a golden set: ~50 albums with hand-verified editions/credits for later evaluation.

Exit: written audit report in the repo; coverage numbers; decisions D-1..D-6 answered.
Kill/pivot: if credits coverage is low, mark Phase 4 personnel/label views as deferred and keep the rest. If a sonic plugin works, Phase 7 becomes proxy-only.
Client gate: none.

### Phase 1: Foundation and Library Health

Work items:
1. Implement store, migrations, repositories with direct-import tests.
2. Implement observations/entities/edges/unresolved/job tables and generation mechanism.
3. Resolution ladder with deterministic normalization helpers; unresolved queue with confirm/reject service functions.
4. Ingest adapter for Navidrome fields (all useful fields normalized internally, only contract fields exposed).
5. Library Health report (read-only): missing MBIDs, mixed-edition albums, inconsistent album-artist spelling, missing genres, wrong/incomplete track counts and multi-disc gaps, loudness/ReplayGain gaps, suspected upsampled or transcoded files (spectral cutoff check, optional job), clipping. Output is a worklist for external tagging tools; the server never edits files.
6. `/api/capabilities` and `/changes` skeleton; ETag/data_version plumbing.
7. Job framework wrapper: idempotent, resumable, bounded, duplicate-prevented, visible state, last-known-good retention.
8. Contract documents and fixtures for the new endpoints.

Exit: bounded sample fully resolved or explicitly unresolved; health report reproducible on the real library; provider failure simulation leaves existing pages unchanged; no performance regression on existing endpoints.
Kill: if the existing store cannot be extended safely, stop and decide on a separate DB file before continuing.
Client gate: macOS gets a read-only Health view and a capabilities consumer; Android none yet.

### Phase 2: Editions and duplicates

Work items:
1. Release-group and release resolution for owned albums where MBIDs exist or the ladder resolves a unique candidate.
2. Edition grouping: original issue vs owned edition; reissue/remaster/deluxe/live relationships; tracklist differences.
3. Duplicate finder, including the same recording on different releases; suggestions only, never deletion.
4. Edition advisor using measured dynamic range, loudness and true peak per edition (optional analysis job, read-only). Wording is "measured", never "better".
5. Feed edition awareness into the ownership matcher so "do I own this?" distinguishes editions; behind a flag, with regression tests on the old behaviour.

Exit: golden-set accuracy meets a target agreed in Phase 0 (propose at least 90% correct or explicitly unresolved, 0 wrong silent merges); ownership flag shows no regressions.
Kill: if the matcher change produces any false merges on the golden set, ship edition info as display-only.
Client gate: macOS album dossier stub (editions section); Android shows a single "other editions" line.

### Phase 3: Collection intelligence as lenses

Work items:
1. **Forgotten Gems** as an Engine 2 lens. Inputs: Navidrome play count, last played, stars, ratings, repeat intensity; ListenBrainz for long-term history where mapped. Score is a "rediscovery score" with a transparent formula, per-user tunable, dismissible. Sparse history yields an empty state, never a guess. Dismissals persist and feed a per-user suppression memory.
2. **Blind spots and discography gaps** with explicit comparison sets: owned artist's studio release groups (MusicBrainz), ListenBrainz top release groups for the artist, MusicBrainz series (e.g. label catalogue series). Output is "you own 41 of 68 in this series" or "missing chapters", never "you should own".
3. **Series completion** counters for MusicBrainz series.
4. **Hidden canon / taste vs world**: unowned albums highly listened sitewide within the owner's top genres (basic version; deeper fingerprint in Phase 6).
5. **Anniversary / on-this-day** cards from release and life-span dates.
6. **Evaluation harness**: a lens scorecard (precision against the owner's accept/dismiss history, diversity, duplicate and owned-leak rate) run before enabling any lens by default.

Exit: owned/unowned correctness verified; results explainable; recommendation weights untouched; lens scorecards documented; clients render via generic insight cards.
Kill: any lens failing its scorecard stays off by default.
Client gate: both clients, via generic card renderer; macOS gets a dashboard, Android gets cards in the existing discovery surface.

### Phase 4: Releases, people, labels (gated on Phase 0 coverage)

Work items:
1. MusicBrainz local slice (or API hybrid) for entities near owned MBIDs; incremental refresh by scan events and entity generation.
2. Album dossier: dates, labels, catalogue numbers, formats, recording places/dates, credits, release family, Cover Art Archive variants with attribution.
3. Person pages: roles, albums in library, albums as leader/sideman not owned (with explanation).
4. Label pages: aliases, parent/sub-labels, owned catalogue, notable missing releases.
5. Work/cover/version links via MusicBrainz works; "a composition, five interpretations".
6. Bounded graph queries with depth/row/time limits and cursors.

**Knowledge-base alignment (added 2026-11-06, owner request; governing design: [`efficiency.md`](efficiency.md) section E and E8).** Phase 4 data is part of the one Server V2 knowledge store, never a second database. Rules for every Phase 4 slice:
1. **Same store.** The MusicBrainz slice, dossiers, person and label pages read and write the existing `observations`, `entities`, `edges` and `meta` tables through `intelligence/store/`. No slice file, no parallel schema. Slice rows are `source = musicbrainz_dump` edges and entities with the dump date as provenance, so the slice can be removed or replaced by source.
2. **Rebuildable, and no owner state in it (state split merged in PR #815).** The slice goes into the rebuildable knowledge file. Dismissals and feedback must not share a file with a 2 GB rebuildable slice (efficiency.md review item 7). The knowledge/state file split is done for card decisions, so the first real import on the server may go ahead once the owner approves the download.
3. **Worker is the only writer.** `musicbrainz.job.run_slice_import` is a worker job (efficiency.md E8). It is not called from a web route; the web process reads only.
4. **One read path (facade merged in PR #816, `intelligence/knowledge/`).** Dossier, person and label pages (and `graph.explore`) are reached through the `KnowledgeReader` facade (efficiency.md E5), not by routes querying tables directly. Request handlers make no provider calls.
5. **Freshness and last-known-good.** The import records a `source_state` ledger row (outcome `ok`, `not_found`, `error`, `blocked`) (table merged in PR #831, migration 3; the import writes it: `ok` after a load, `blocked` after a budget fallback, `error` after a rejection), and the dump date in `meta`. A newer import replaces the previous slice in the load's own transaction: dump edges it did not see are removed with the entities only they connected (not owned, no other id, no edge, no insight), and a dump that keeps under half of the previous dump edges is refused (`rejected`, previous slice untouched).
6. **Growth follows the library.** Seeds come from owned MBIDs (`owned_seeds`); a new owned MBID is filled from the API by the worker first and absorbed by the next import (E8). Bulk dump data is preferred to per-entity API calls (owner batching rule).
7. **Every field has a consumer.** Load only what a dossier, person or label view reads (efficiency.md E6).

Exit: every factual edge has provenance; ambiguous entities show as such; unverified inference never displayed as credit; bounded traversal tested for cycles and duplicates.
Kill: if the slice import exceeds agreed disk or time budgets on the real server, fall back to API-only with a tighter entity scope.
Client gate: macOS full dossier and person/label pages; Android "Who played on this?" and compact connected-musicians list.

### Phase 5: Context, atlas, paths

**Status: closed 2026-11-06 (owner decision).** Server work items 1 to 4 are built and the exit passed (PRs #839 to #846). Same-studio-different-decade was dropped as mostly empty (kill rule); sideman-to-leader is parked. The client gate and the follow-ups below were handed to Phase 7.

Work items:
1. Wikidata ingest for influences, genres, origin, founding dates; claims linked to statements.
2. Areas, places and events from MusicBrainz for a geographic and scene atlas; no nationality inferred from names, labels or single recording locations.
3. Discovery paths computed on demand: ordered stops, each with `reasons[]`, cached by (start, kind, generation), depth/time-limited.
4. Path kinds: follow-the-musician, same-studio-different-decade, label path, composition path, scene path, sideman-to-leader.

Exit: each stop explainable; no path generated without evidence; latency budget met on the real library.
Kill: if a path kind needs more than a day of precompute or yields mostly empty results, drop that kind.
Client gate: macOS graph explorer/atlas/timeline; Android paths as short lists.

### Phase 6: Taste, time and personalization

**Status (2026-11-07):** slices 1 to 11b are merged (PRs #847 to #859). The time-windowed profile builder, listens loader, profile persistence/read route, pure obscurity builder, batch ListenBrainz popularity fetcher, monthly snapshot builder, listening-context profiles, suppression builder/persistence/routes, and macOS feedback client/playback reporting exist. The popularity fetcher remains unwired: no job invokes it, no popularity data is persisted, and no client consumes the obscurity profile. **Slice 11a (PR #857), slice 11b (PR #858), and the outbox durability correction (PR #859) are merged.** The durability correction prevents sending while the queue is not safely persisted, saves settled removals before continuing, and quarantines unreadable queue files (or refuses to overwrite them if quarantine fails). PR #859's filtered Swift tests were reported 15/15 locally; all four required repository workflows passed on exact code head `ef039f745be81c43c21a8ba365c4f2ffc24578ca`. The Scrobble switch still gates skip events (owner decision). **Slice 11c (card dismissals, PR #860) is open and retargeted to `main` after #859 merged.** It queues a record-only `dismiss` event with `subject_kind: card` and the card subject key through the shared outbox. Its filtered `InsightsModelTests` are reported 6/6 locally; no required workflow run is yet reported for current head `064f765a1e67a9cac0e7a7d086daf9f5b20c028e`. The branch has now been reconciled with current `main` without force-pushing; latest main-sync commit `67c58ffcc437dfdd6eb3e6bc1cc32e7179681af8` (parented on main `358120150658166ae85a3e5f212710054016a199`). The PR diff contains only `AppState.swift`, `InsightsModel.swift` and `InsightsModelTests.swift`; #859's outbox changes and stale docs are no longer included. GitHub reports mergeable; the four required repository workflows have been triggered and are queued on this commit. Owner decisions remain open on whether dismissal events ignore the Scrobble switch and whether only card events (not additional track/album/artist events) are recorded. The outstanding owner playback-suite check remains before slice 11c proceeds. No real-server, publication, deployment or runtime verification. Keep provider traffic and runtime activation separately owner-gated. **Slice 7 (pure listening-context profiles, `intelligence/taste/context.py`, work item 4):** groups caller-supplied listens by local time in a named IANA timezone (default UTC) into two lenses, time of day (night 00-05, morning 06-11, afternoon 12-17, evening 18-23) and weekday/weekend, each profiled with `profile_window` (all values kept, low-sample flags, no shifts). Hour boundaries are fixed starting values, not measured clusters. Unit-tested only (`tests.test_intelligence_taste_context.py`); not persisted, scheduled, exposed by any route, or consumed by a client. **Slice 8 (pure suppression builder, PR #854):** `intelligence/taste/suppression.py` validates client event batches (UUID-shaped `event_id`, lowercase normalization, per-item rejection, whole-batch limit of 100, idempotent deduplication) and builds deterministic per-subject weights using the 14-day half-life and 60-day expiry, capped at 1.0. It is unwired and record-only: no route, job, client, provider traffic or ranking effect. **Slice 9 (owner-state persistence, PR #855):** migration 2 creates `state.suppression_events` in the dedicated owner-state SQLite file with unique event IDs, D-027 shape checks, a time index and an UPDATE-blocking trigger; owner-state migrations transact each migration with its version bump. `intelligence/taste/suppression_persistence.py` provides atomic batch inserts with inserted/duplicate/conflict outcomes, event retrieval and a bounded caller-clocked 180-day retention sweep. This slice is also record-only and unwired. **Slice 10 (routes, PR #856):** `POST /api/feedback/events` and `GET /api/insights/suppression` (`app/api/feedback.py`, `intelligence/api/feedback.py`), contract text and three fixtures; still record-only, with no ranking, job, provider or client effect.

**Item 5 design (owner decisions 2026-11-06, D-027).** Client events, record-only, decaying.
- **Event** (one row per report): `event_id` (client-generated UUID, makes retries idempotent), `client` (`macos`, `android`), `kind` (`skip`, `dismiss`), `subject_kind` (`track`, `album`, `artist`, `card`), `subject_id` (Navidrome id, plus `mbid` when known), `occurred_at` (epoch seconds), and for tracks `played_seconds` and `duration_seconds`. No file paths, tokens, device names or free text.
- **What counts as a skip** is decided by the client and stated in the contract, not guessed by the server: a track abandoned before 30 s or before 50 percent of its length, whichever comes first, and not at the end of a queue. These are starting values, not measured; the server stores what the client reports and never re-derives it.
- **Storage:** a new table in the Server V2 SQLite file (D-026), append-only, with a unique `event_id`. It lives with owner state, not in the rebuildable knowledge file (see the state split in Phase 4). Retention: rows older than 180 days are deleted by a bounded sweep; nothing else prunes them.
- **Suppression memory** is a derived, read-only view over events: per subject, an active weight from the existing decay (`2 ** (-age / 14 days)`, zero after 60 days), summed over events and capped at 1.0. One kind of subject never implies another: a skipped track does not suppress its album or artist in this slice.
- **Routes:** `POST /api/feedback/events` (batch of up to 100, authenticated like the other `/api` routes, partial acceptance with per-event reasons, duplicates reported as accepted) and `GET /api/insights/suppression` (active entries with weight and last event, newest first, paged). Both are additions to a new module, not to `navidrome_server.py` (D-016).
- **Effect:** none. No lens, radio, recommendation weight, insight card or playlist reads the memory. Wiring it anywhere is a separate owner decision, with the lens scorecard (Phase 3 item 6) run first.
- **Privacy:** events carry listening behaviour, so they stay on the server, are never sent to a provider, and are excluded from logs beyond counts.
- **Slices:** (8) pure builder for the suppression view plus event validation, unit-tested, unwired; (9) owner-state table, idempotent insert and bounded retention sweep, merged and unwired; (10) the two routes and a contract document with fixtures that both clients decode; (11) client reporting, which waits for the client gate. Slices 8 to 10 need no client change.
- **Exit for item 5:** replaying the same batch changes nothing; a malformed event is rejected without losing the rest; sparse or empty data reads as an empty list, not an error; the memory demonstrably changes no ranking output.


**Item 6 design (approved by the owner 2026-11-07 with the changes under "Owner decisions"; nothing below is built).** Smart playlists as saved queries, evaluated on the server.

Starting point: the macOS client already has a Smart Playlists screen (PR #746) with its own rule engine over Navidrome songs, rule sets in `UserDefaults`, and a one-shot "Save to Navidrome" that only creates new playlists. Android has none. The server has no saved queries. Item 6 therefore adds what a client cannot do alone: rules that reach insight data, re-evaluation on a schedule, and one place for rules both clients share.

- **Rule set** (one row per playlist definition): `rule_id` (server-generated UUID), `name`, `match` (`all` | `any`), `rules` (list of `{field, op, value}`), `order`, `limit` (25 to 250 or none), `created_at`, `updated_at`. Fields are the client set (artist, title, genre, format, year, plays, rating, bitrate, added days, last played days) plus insight-backed fields added one at a time, each only if its data is populated: `obscurity_band` (from the obscurity profile), `in_lens` (a Phase 3 lens key), `suppressed` (never true while the memory is record-only, so not offered until the owner wires it). A field whose data is absent makes the rule unfinished (matches everything, as on the client), reported in the result, never an error.
- **Evaluation** is a pure function over caller-supplied song rows and insight lookups, unit-tested and unwired first, mirroring the client engine's semantics (unfinished rules match everything, never-played matches "last played at least N days ago", unknown numeric values never match) so a rule set gives the same answer on both sides. Deterministic ordering with a stable tie-break on Navidrome id; `random` takes a caller seed.
- **Storage:** a new table in the owner-state SQLite file (D-026), a normal mutable table (unlike suppression events), added by migration 3. Rules are owner configuration, not rebuildable knowledge. Retention: none; deleting is explicit.
- **Scheduled re-evaluation (dropped by the owner, 2026-11-07; not built, slice 15 removed):** an opt-in per-rule flag `refresh` (off by default). A bounded job on the existing runner re-evaluates flagged rules daily and stores the last result (ids only, capped at the limit) with `evaluated_at` and `source_generation`. Without the flag a rule is evaluated only on request. No provider traffic: evaluation reads Navidrome data the server already holds plus local insight tables.
- **Routes** (new module, not `navidrome_server.py`, D-016): `GET /api/playlists/smart` (list), `PUT /api/playlists/smart/{rule_id}` (create or replace; ids client-suggested so retries are idempotent), `DELETE`, `GET .../{rule_id}/result` (cached result or evaluate now, with `unfinished` and `missing_data` reports). Contract text and fixtures that both clients decode, before merge.
- **Navidrome export (dropped from the server by the owner, 2026-11-07; it stays with the client's existing "Save to Navidrome", slice 16 removed):** optional and separate. The server would write a result into Navidrome only on an explicit owner-triggered request per rule, as a new playlist or by replacing a playlist it created itself (tracked by stored playlist id), never touching playlists it did not create. The Navidrome write path was checked read and create in M1; replace and delete are not yet checked and must be before this slice.
- **Not in this item:** BPM/key-aware ordering (no tag coverage measured; revisit after a Phase 0-style probe), changing the macOS engine, any effect on recommendation weights.
- **Slices (final):** (12) pure evaluator plus rule validation, unwired; (13) migration 3 table and CRUD persistence, unwired; (14) routes, contract and fixtures; (15) macOS migration from local `UserDefaults` rule sets to the server, which then keeps a local cache (client gate).
- **Exit for item 6:** the same rule set gives identical output server and client on shared fixtures; a rule on missing insight data degrades to "unfinished", not an error; replaying a PUT changes nothing; refresh is off unless set; nothing is written to Navidrome without an explicit request.
- **Owner decisions (2026-11-07):** (a) shape approved; (b) rule sets live on the server, clients sync and local storage becomes a cache; (c) no scheduled refresh, rules are evaluated on request only; (d) Navidrome export stays with the client, the server never writes playlists to Navidrome.

Work items:
1. Time-windowed profiles (recent, mid, all-time) across genre, era, area, label, collaborator; minimum sample sizes before any "shift" is stated.
2. Obscurity/mainstream profile versus ListenBrainz sitewide stats.
3. Monthly snapshots (time capsule) so "then vs now" survives library changes.
4. Listening-context profiles (time-of-day/day-of-week clusters) as selectable lenses.
5. Skip/dismissal signals from clients to a suppression memory; no effect on recommendation weights without a separate decision.
6. Smart playlists as saved queries over insights; scheduled re-evaluation; optional export to Navidrome playlists; BPM/key-aware ordering when tags exist.

Exit: profiles reproducible; sparse data shows honest low-sample states; profile does not alter weights.
Client gate: macOS taste views and snapshots; Android a compact taste card.

### Phase 7: Sonic, plus Phase 5 carry-over

**Inherited from Phase 5 (closed 2026-11-06).** These stay owner-gated and run in whatever order the owner picks:
- **Client gate:** macOS graph explorer, atlas and timeline; Android paths as short lists (consuming `GET /api/knowledge/paths`, `place` and `event`).
- **Wiring:** nothing calls the paths route yet. Paths are on demand and cached, so a client is the trigger; a scheduled or post-import cache warm-up is optional and unplanned (exit check projects about 10 minutes per kind for 10,000 artists).
- **Quality spot-check:** the bounded follow-the-musician and composition paths (credits per bridge and bridges per path are capped, reported as `truncated: "rows"`) have not been reviewed by hand as suggestions.
- **Sideman-to-leader:** parked; the route answers `400`. Improve with other data sources, by owner decision.
- **Unlanded checks:** the paths route test was not run locally (no fastapi), the full suite was not run (owner rule), and nothing is published or deployed.

Sonic work items:

Work items:
1. If Phase 0 found a working sonic extension: proxy `getSonicSimilarTracks` and `findSonicPath` through Librarian with ownership overlay, caching, and graceful 404 handling; expose track/album radio and sonic paths. No analysis of our own.
2. Else: time-boxed experiment with Essentia on an owner-approved sample (document CC BY-NC-SA on model weights for personal use); measure CPU, wall time, memory, disk, stability; compare with human judgment across genres and recording quality.
3. Only after a successful experiment: resumable throttled jobs, newest-first, cancel/progress visible, disabled by default.

Exit: proceed/stop decision documented with evidence. Audio never leaves the server.
Kill: stop if quality is unconvincing or the server hardware cannot sustain it.

### Deferred
Album sequencing analyst and sample/interpolation ancestry. Reconsider after Phase 7 or when a reliable source appears.

## 10. Operational requirements

- Provider and analysis work never runs in page requests; jobs idempotent, resumable, bounded, deduplicated per entity and generation.
- Event-driven refresh: Navidrome scan completion (via scan status) and new acquisitions trigger incremental enrichment; scheduled sweeps only as a safety net.
- Per-provider budgets, timeouts, bounded retries; negative results cached with a TTL; last-known-good retained on failure.
- Job state and last successful refresh exposed without credentials.
- Priority order under budget: newly added, recently viewed, then the rest.
- Memory/storage growth measured on the real library before any full-library job is enabled.
- Privacy: listening data used only through already configured sources; no audio leaves the server; no filesystem paths or tokens in payloads; similar-users data only after an explicit decision.

## 11. Testing and acceptance

Per phase, in addition to docs/TEST_PLAN.md:

- **Identity:** exact MBID/ISRC, alias and punctuation normalization, ambiguous names, release vs release group, recording vs work, conflicting provider facts, malformed/stale/partial responses, "never pick the first result".
- **Graph:** relation and role preserved, evidence class retained, depth/row/time limits, cycles, duplicate edges, inference never shown as a credit.
- **Insights:** owned/unowned correctness, multi-disc and incomplete albums, score boundaries, sparse history, dismissal persistence, behaviour with one provider down.
- **Jobs:** cancel/restart, duplicate prevention, resource limits, deterministic serialization, no media mutation (checksum before/after on a test fixture).
- **API:** fixtures for every response, partial-result reasons, pagination and stable ordering, no secrets/paths, macOS and Android decode the same fixtures, unknown card kinds handled.
- **Evaluation:** golden set for editions/credits; lens scorecards for each insight; documented sonic experiment.
- Keep implemented, tested, CI-passed, merged, published, deployed and runtime-verified as separate states. Follow docs/LOCAL_UI_TESTING.md for UI. Respect the existing filtered-test rule when running suites.

## 12. Decisions needed from the owner

| # | Decision | Recommendation |
|---|---|---|
| D-1 | MusicBrainz access: local slice from dumps, API-only, or hybrid | Hybrid, dump slice for bulk |
| D-2 | First user-facing outcome | Library Health + Forgotten Gems (both low-risk) |
| D-3 | Is Phase 0 strictly read-only with no new provider calls beyond the bounded sample | Yes |
| D-4 | Acceptable sources and request budgets (MB, ListenBrainz, Wikidata, CAA, LRCLIB, Fanart/TheAudioDB, Discogs) | Approve first five, others later |
| D-5 | Graph scope: owned-adjacent only, or plus a bounded set of discovery candidates | Owned-adjacent first |
| D-6 | Sonic: proxy if a plugin exists; in-house experiment allowed or not | Proxy first; experiment only if proxy impossible |
| D-7 | Where Server V2 data lives (existing DB vs new file) | **Decided 2026-11-05: new dedicated file with its own migration runner** (D-026) |
| D-8 | Whether ListenBrainz similar-users data may be used | Not by default |
| D-9 | Which phases get Android surfaces | Phases 3 and 4 only initially |

## 13. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Sparse MusicBrainz credits for the owner's genres | Phase 4 value collapses | Phase 0 coverage probe; kill criteria; user-confirm path |
| False identity merges | Wrong ownership/credits | Ladder, unresolved queue, golden set, no silent merges |
| Scope creep from the catalogue | Nothing ships | Phase gates; one outcome per phase |
| Storage/CPU growth | Slows other services | Budgets, measurements, bounded jobs |
| Provider policy/terms changes | Broken ingest | Optional adapters, last-known-good, re-check at gates |
| Plugin dependency for sonic | Feature may not exist | Capability negotiation; treat as optional |
| Clients diverge on contracts | Bugs | Shared fixtures and card registry |

## 14. Milestone summary

| Phase | Outcome | Depends on |
|---|---|---|
| 0 | Audit report, coverage numbers, golden set | none |
| 1 | Store, resolution, job framework, Library Health | 0 |
| 2 | Editions and duplicates | 1 |
| 3 | Forgotten Gems, blind spots, series, anniversaries (lenses) | 1, partly 2 |
| 4 | Dossiers, people, labels, works | 1, 2, coverage from 0 |
| 5 | Atlas, influences, paths (server closed; client gate moved to 7) | 4 |
| 6 | Taste, time capsule, smart playlists | 3 |
| 7 | Sonic proxy or experiment, plus Phase 5 client gate and follow-ups | 0, 5 |

Phases 3 and 7 can run in parallel with Phase 4 once Phase 1 is done.

## 15. References

Carried over from the research draft: Navidrome Subsonic compatibility docs and upstream handlers, OpenSubsonic Child response, MusicBrainz API and Cover Art Archive, ListenBrainz API/statistics/recommendations/export, Discogs API, Roon metadata model, Plex Sonic Analysis, Essentia, AcousticBrainz (collection stopped 2022).
Added: [Navidrome AudioMuse integration](https://navidrome.org/docs/usage/integration/audiomuse/), [ListenBrainz popularity](https://listenbrainz.readthedocs.io/en/latest/users/api/popularity.html), [ListenBrainz MBID mapping](https://listenbrainz.readthedocs.io/en/latest/maintainers/mapping.html), [Essentia models](https://essentia.upf.edu/models.html), [LRCLIB client](https://lrclibapi.readthedocs.io/en/stable/lrclib.html). Verify ListenBrainz sitewide/fresh-release/LB Radio paths against official pages before use.
