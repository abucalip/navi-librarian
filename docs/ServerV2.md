# Server V2: Music Intelligence Plan

**Status:** Phase 0 complete (2026-11-05, see [`SERVER_V2_PHASE0_AUDIT.md`](SERVER_V2_PHASE0_AUDIT.md)); the owner accepted the recommended D-1 to D-6. D-7 was decided on 2026-11-05 (new dedicated SQLite file, see D-026 in `DECISIONS.md`) and Phase 1 is complete and the owner opened the Phase 2 gate on 2026-11-05 (slice 1, release-group linking, merged in PR #770; slice 2, edition grouping and tracklist differences, merged in PR #771; slice 3, duplicate finder, merged in PR #772; slice 4, edition advisor, merged in PR #773; slice 5, edition-aware ownership behind a flag, merged in PR #774); D-8 and D-9 are open. **Phase 3 (collection intelligence as lenses) is complete (2026-11-06):** all five lenses and the served `/api/insights` routes are merged and, by owner decision, on by default (PR #808; `NAVI_INSIGHT_LENSES` unset means all five, empty means none). The exit script ran clean on the live library; Forgotten Gems is empty until Navidrome holds 180 days of history (37 days now); the blind-spots diversity gate stands (0.55 on a 12-artist sample, 1.0 at 40 artists); card review, a full-library run and further live runs were waived by the owner and are adjusted later if needed. **Phase 4 started (2026-11-06, owner request):** slice 1, bounded graph queries (`intelligence/graph/`), merged in PR #809; the MusicBrainz dump slice (D-1) is under way: the download is measured (core 7.7 GB, cover-art 163 MB), the owner approved the budgets (about 7.9 GB download, 25 GB scratch ceiling, slice under 2 GB, import under 2 hours, run on the server, loader writes into the existing Server V2 database), and the dump reader is merged in PR [#810](https://github.com/abucalip/navi-librarian/pull/810) and the resumable checksum-verified downloader in PR [#811](https://github.com/abucalip/navi-librarian/pull/811); the neighbourhood selector is merged in PR [#812](https://github.com/abucalip/navi-librarian/pull/812); the loader is merged in PR [#813](https://github.com/abucalip/navi-librarian/pull/813); the import job with budget checks is merged in PR [#814](https://github.com/abucalip/navi-librarian/pull/814) (unwired, never run on the real archive); a manual trigger and a measured server run are next. Nothing here authorizes implementation, provider traffic beyond what already exists, audio analysis, deployment, or client UI work until the relevant phase gate is approved.

**Baseline:** GitHub main at e29ca45 (2026-11-05). Re-verify the repo, provider docs, and the installed Navidrome version at each phase gate.

**Supersedes:** the research draft of docs/ServerV2.md. Its catalogue of ideas is preserved in section 5; this document adds sequencing, data design, work items, acceptance criteria and kill criteria.

---

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
5. **Freshness and last-known-good.** The import records a `source_state` ledger row (outcome `ok`, `not_found`, `error`, `blocked`) once that table exists, and the dump date in `meta`. A newer import must validate before it replaces the previous slice; the current loader is additive and removes nothing, so removal of entities and edges that left the dump is still to be built.
6. **Growth follows the library.** Seeds come from owned MBIDs (`owned_seeds`); a new owned MBID is filled from the API by the worker first and absorbed by the next import (E8). Bulk dump data is preferred to per-entity API calls (owner batching rule).
7. **Every field has a consumer.** Load only what a dossier, person or label view reads (efficiency.md E6).

Exit: every factual edge has provenance; ambiguous entities show as such; unverified inference never displayed as credit; bounded traversal tested for cycles and duplicates.
Kill: if the slice import exceeds agreed disk or time budgets on the real server, fall back to API-only with a tighter entity scope.
Client gate: macOS full dossier and person/label pages; Android "Who played on this?" and compact connected-musicians list.

### Phase 5: Context, atlas, paths

Work items:
1. Wikidata ingest for influences, genres, origin, founding dates; claims linked to statements.
2. Areas, places and events from MusicBrainz for a geographic and scene atlas; no nationality inferred from names, labels or single recording locations.
3. Discovery paths computed on demand: ordered stops, each with `reasons[]`, cached by (start, kind, generation), depth/time-limited.
4. Path kinds: follow-the-musician, same-studio-different-decade, label path, composition path, scene path, sideman-to-leader.

Exit: each stop explainable; no path generated without evidence; latency budget met on the real library.
Kill: if a path kind needs more than a day of precompute or yields mostly empty results, drop that kind.
Client gate: macOS graph explorer/atlas/timeline; Android paths as short lists.

### Phase 6: Taste, time and personalization

Work items:
1. Time-windowed profiles (recent, mid, all-time) across genre, era, area, label, collaborator; minimum sample sizes before any "shift" is stated.
2. Obscurity/mainstream profile versus ListenBrainz sitewide stats.
3. Monthly snapshots (time capsule) so "then vs now" survives library changes.
4. Listening-context profiles (time-of-day/day-of-week clusters) as selectable lenses.
5. Skip/dismissal signals from clients to a suppression memory; no effect on recommendation weights without a separate decision.
6. Smart playlists as saved queries over insights; scheduled re-evaluation; optional export to Navidrome playlists; BPM/key-aware ordering when tags exist.

Exit: profiles reproducible; sparse data shows honest low-sample states; profile does not alter weights.
Client gate: macOS taste views and snapshots; Android a compact taste card.

### Phase 7: Sonic

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
| 5 | Atlas, influences, paths | 4 |
| 6 | Taste, time capsule, smart playlists | 3 |
| 7 | Sonic proxy or experiment | 0 |

Phases 3 and 7 can run in parallel with Phase 4 once Phase 1 is done.

## 15. References

Carried over from the research draft: Navidrome Subsonic compatibility docs and upstream handlers, OpenSubsonic Child response, MusicBrainz API and Cover Art Archive, ListenBrainz API/statistics/recommendations/export, Discogs API, Roon metadata model, Plex Sonic Analysis, Essentia, AcousticBrainz (collection stopped 2022).
Added: [Navidrome AudioMuse integration](https://navidrome.org/docs/usage/integration/audiomuse/), [ListenBrainz popularity](https://listenbrainz.readthedocs.io/en/latest/users/api/popularity.html), [ListenBrainz MBID mapping](https://listenbrainz.readthedocs.io/en/latest/maintainers/mapping.html), [Essentia models](https://essentia.upf.edu/models.html), [LRCLIB client](https://lrclibapi.readthedocs.io/en/stable/lrclib.html). Verify ListenBrainz sitewide/fresh-release/LB Radio paths against official pages before use.
