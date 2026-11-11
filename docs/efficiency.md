# Efficiency and runtime architecture plan

Last reviewed: 2026-11-11 (revision 5, full rewrite)
Repository baseline: GitHub `main` at `b5a90bf3173abaf823e2c2f70b9d01dad07d2da9`.

This is a plan. It authorizes no provider traffic, publication, or deployment. Every step is its own focused PR with regression tests, exact-head CI, and any owner approval the workflow requires (`docs/DEVELOPMENT_WORKFLOW.md`, `docs/TEST_PLAN.md`).

**Evidence standard used in this revision.** Statements under "Verified" were read from the source at the baseline commit. Nothing was executed or measured for this revision: every performance claim below is a hypothesis until step M1 to M3 produce numbers. Items marked *unverified* must be checked before they are acted on.

## 1. What changed in this revision

Revisions 1 to 4 grew a large target design (generic job dispatcher, four priority lanes, profile read models, single provider egress, every cache folded into the Server V2 store). Checking that design against the code shows three things:

1. **The most serious problems are small, concrete, and not in the old roadmap.** A killed worker can leave a job permanently stuck; every knowledge read request opens a write transaction; MusicBrainz pacing is split across six separate pacers and several direct callers in two processes. These come first.
2. **Several cheap, certain wins were never listed.** Settings are re-read from SQLite (two connections) on every Navidrome call and every authenticated request; every Navidrome call builds a new HTTP client; eight in-memory caches never evict; the full album inventory is re-fetched inside a request.
3. **Much of the old target design is more machinery than a one-owner home server needs.** With a cross-process provider gate, "only the worker may call providers" stops being a correctness requirement. With one enforced worker instance, leases, claims and lanes are unnecessary. These parts are replaced by smaller designs or deferred behind measurements.

The roadmap is therefore reordered: correctness, then measurement, then cheap verified wins, then finishing the worker split, then evidence-gated architecture.

## 2. Verdict on the earlier proposals

| Earlier proposal (old section) | Verdict | Reason |
|---|---|---|
| Keep FastAPI, one Uvicorn process, SQLite, no Redis/Celery/RabbitMQ/PostgreSQL | **Retain** | Nothing found contradicts it. The constraints are provider budgets and avoidable per-request overhead, not framework throughput. |
| A: separate worker process, same image and volume | **Retain, modified** | Partly done (PR #898). Finish by moving the three remaining web-started loops (W2, W3). Enforce "exactly one worker" with a file lock instead of assuming it (R1). |
| A2: generic dispatcher with registry, atomic claims, leases, durable queue | **Replace** | One enforced worker makes claims and leases redundant. Use a small table-driven scheduler with persisted last-run times (W1). `intelligence/jobs/runner.py` stays the per-job execution wrapper. |
| A5: database-backed shared provider limiter | **Retain, promoted to first priority** | Still not implemented, and the split it was a prerequisite for has already shipped (R2). |
| B1, B2: MusicBrainz ratings browse, tracklist browse | **Defer** | The dump slice answers owned-entity facts locally. Re-open only if M2 shows these calls matter. |
| B3, B4, B5: existing ListenBrainz and MusicBrainz batches | **Retain as written** | Working batch paths; do not change chunk sizes without measurement. |
| B6: Navidrome ingest N+1 | **Retain, modified** | Now also a duplication question: two ingest paths exist (P5). |
| B7: coalescing, cache discipline, connection reuse | **Retain, made concrete** | Becomes steps P1 to P4 with named files. |
| B8: bounded concurrency | **Retain as a rule** | Section 9. No new work until the gate exists. |
| C: measurement | **Retain, moved earlier and shrunk** | Three small steps (M1 to M3) instead of a full metrics programme. |
| D: multiple Uvicorn workers | **Defer** | No evidence of API queueing. The state inventory is kept as one line item in M3. |
| E: single provider egress, enforced by an import-boundary test | **Replace** | The goal is "no response waits on a provider when a usable value exists" plus "one shared budget". Achieve it with the gate (R2) and stale-while-revalidate (K2). Moving every provider client into worker handlers is deferred. |
| E: fold `metadata_cache` and the discovery caches into Server V2 observations | **Remove** | Observations are append-only provenance with a uniqueness constraint; using them as a TTL cache would bloat the store and couple a rebuildable knowledge file to opaque provider blobs. Keep the key-value cache as a cache and fix it (P3). |
| E1.4: `artist_profile` / `album_profile` read models | **Defer** | `KnowledgeReader` already serves routes directly. Add a read model only for a route that M2 shows is slow on store reads. |
| E3, E4: five field states, four lanes with budget shares, relevance scoring | **Retain the states, replace the lanes** | `source_state` already implements outcome, backoff and due-ordering. Use one ordered queue (new additions, then owned by recency, then backfill) until contention is measured. |
| E8: MusicBrainz dump slice | **Retain; status corrected** | Pipeline merged and one real import done on the owner's Mac. Recurring refresh stays deferred (S3). |
| Cold-start section | **Retain, condensed** | Section 8. |

## 3. Current state (verified at the baseline commit)

### Implemented

- **Worker process.** `app/worker.py` (`python -m app.worker`, compose service `worker`) runs two daemon threads: the insights refresh loop (`app/services/insights_refresh.py`, every 6 h) and the automatic API fill (`app/services/library_enrich.py`, poll every 5 s by default). The web process no longer starts the insights writer (PR #898).
- **Job wrapper.** `intelligence/jobs/runner.py`: duplicate prevention per `(job, scope)` through a unique index, item and time budgets, checkpoints, cancellation, last-known-good, data-version bump on success.
- **Freshness ledger.** `intelligence/store/source_state.py` (migration 3): outcome per `(source, operation, key)`, exponential backoff for `error` and `blocked`, `due()` ordering. Used by the MusicBrainz API fill, auto fill, Wikidata ingest and the slice import.
- **Owner-state split.** `intelligence.state.sqlite3` is attached as schema `state` (PR #815).
- **KnowledgeReader and knowledge routes.** `/api/knowledge/*` (connections, paths, atlas, timeline and others) read through `intelligence/knowledge/reader.py`.
- **MusicBrainz dump slice.** Reader, downloader, selector, loader, job and CLI are merged (PRs #810 to #814, #819, #821, #822). One real import was measured on the owner's Mac on 2026-11-06: extract 221 s, select 50 s, load 101 s, 752,342 entities, 1,744,255 edges, 1.1 GB, no budget breached.
- **Manual update requests.** `update_requests` table (migration 6), enqueued by the web, processed by the worker.
- **Artwork store.** `intelligence/artwork/` keeps an index in SQLite and files on disk.
- **Total request timing.** `Server-Timing: app;dur=` on `/api/*`.

### Partially implemented

- **Worker split.** Three loops still start from web startup (`app/main.py::_start_discovery_background`): the legacy discovery scheduler (`navidrome_server._discovery_scheduler`, hourly), the daily lens refresh (`discovery/lens_service.py`), and the similar-artist precompute (`app/api/search.py`).
- **Single writer.** The compose comment and `app/worker.py` say the worker is the only writer of the knowledge store. It is not: web routes open the store read-write and write to it (`app/api/feedback.py`, `smart_playlists.py`, `taste_refresh.py`, `knowledge_update.py`, `paths_warm.py`, `insights.py`, `popularity.py`). This is acceptable with WAL and short transactions, but the documentation claim is wrong and the read path is not read-only (see F3).
- **Read-only web connection.** `intelligence/store/db.py::open_readonly` exists and has no caller outside tests and fixtures.

### Planned, not started

Shared provider gate; scheduler; store retention; any structured provider or database measurement.

### Unverified

- How the slice reached the server: `docs/PROJECT_STATUS.md` says it was merged into the server store by owner-local scripts that are not in the repository. That path is not reproducible from the repository.
- Real traffic shape: provider requests per day, per-route provider wait, cache hit rates, SQLite busy waits, memory.
- Backup and restore of the seven or more SQLite files under `/data`.
- Provider storage terms (Last.fm, Deezer, Apple, review sites). Unchanged from revision 2: check before storing more than facts, links and short attributed excerpts.

## 4. Findings

Each finding cites where it was read. Severity: **C** correctness or reliability, **P** performance, **M** maintainability.

**F1 (C). A killed worker can stall a job permanently.** `run_job` claims a run with `UPDATE ... WHERE state = 'queued'`. If the process dies mid-run the row stays `running`; the unique active index then makes `enqueue` return that same row, the claim matches nothing, and every later call returns `skipped`. `recover_stale` exists but is called only by `intelligence/taste/refresh.py`. The API fill, provider lenses, Forgotten Gems, Wikidata ingest, paths warm, popularity and slice import jobs have no recovery. A container restart during a fill is enough to trigger it. (Read from `intelligence/jobs/runner.py` lines 88 to 143 and a search for `recover_stale(`; reproduce with a test before fixing.)

**F2 (C). MusicBrainz pacing is not shared.** Independent pacers found: `intelligence/musicbrainz/api_fill.py::Paced` (1.1 s, a new instance per auto-fill cycle), `intelligence/insights/provider_runtime.py::_paced_json`, `integrations/musicbrainz/album_year.py` (module lock and `_last_request`), `integrations/musicbrainz/rating_client.py` (injected sleep), `discovery/search/limiter.py::SourceLimiter` (process-wide, web), `intelligence/artwork/fetchers.py::HostPacer`, plus direct callers in `discovery/` (`new_releases.py`, `artist_links.py`, `candidate_gathering.py`, `mbid_popularity.py`, `artist_tag_fallback.py`, `artist_profiles.py`) and `integrations/musicbrainz/recording_album.py`. MusicBrainz limits by client IP. Inside the worker alone, the insights thread and the fill thread pace separately; the web process adds its own. Worst case is several requests per second from one IP.

**F3 (C/P). Every knowledge read opens a write transaction.** Web routes call `open_store()` per request. That runs `PRAGMA journal_mode = WAL`, `migrate()`, `ATTACH`, a second `journal_mode` pragma, the state migration check, and `move_legacy_decisions()`, which executes `INSERT OR IGNORE ... SELECT` inside `with db:` on every call, followed by a scan of `main.insights`. A read request therefore takes the write lock on the store and can wait up to the 10 s busy timeout behind a worker write. (`intelligence/store/db.py`, `intelligence/store/state.py::attach_state`.)

**F4 (C). Worker loop lifecycle.** `insights_refresh._loop` sleeps with `time.sleep(6 h)` and ignores the stop event; the thread is a daemon, so SIGTERM kills it mid-run and produces F1. The loop also runs at once on every worker start, so each restart spends up to the 120-request provider budget regardless of when the last run finished (*unverified whether inner TTLs make that run cheap*). The module docstring says "Navidrome only; no provider traffic", which is no longer true.

**F5 (P). Settings are re-read from disk constantly.** `settings/persistence.py::read()` calls `initialize()` (connect, `CREATE TABLE IF NOT EXISTS`, commit, `chmod`) and then opens a second connection to read every row. It is called by `_navidrome_config` on every Navidrome `api_call`, by the auth middleware on every request (`AuthSettingsReader` deliberately does not cache), by the insights token lookup per ListenBrainz request, and by many service adapters. The worker's 5 s poll alone performs about 17,000 such reads a day.

**F6 (P). Every Navidrome call creates an HTTP client.** `integrations/navidrome/client.py::api_call` runs `with client_factory(...) as client:` per call: a new connection pool, TCP handshake (and TLS where configured) each time. Affects every library page, inventory paging, ingest and the 5 s poll.

**F7 (P). The legacy metadata cache is as weak as revision 2 said, and never shrinks.** `metadata_cache.py` opens a connection and runs `CREATE TABLE IF NOT EXISTS` on every `get` and `set`, uses the default rollback journal, and has no delete path at all, so the file only grows.

**F8 (P). Eight unbounded in-process caches.** `app/api/metadata.py` keeps `_artist_bio_cache`, `_artwork_cache`, `_album_details_cache`, `_artist_image_cache`, `_album_links_cache`, `_apple_url_cache`, `_album_description_cache` and `_review_cache` as plain dicts. The file contains no `pop`, `del` or `clear`: entries expire logically but are never removed. Each repeats the same three-layer lookup (memory, `persistent_metadata`, provider) by hand, with no single-flight, so concurrent identical requests each call the provider.

**F9 (P). Full inventory fetches where a snapshot would do.** `fetch_album_inventory` pages the whole library (500 per page) and is called inside a request by `/api/knowledge/paths?kind=album_gaps` (`app/api/knowledge.py::_play_records`), and by the lens refresh, candidate gathering, insights refresh and the daily auto-fill pass. The owned search index (`discovery/search/index.py`) rebuilds from a full song inventory whenever it is older than 10 minutes and is used.

**F10 (P/M). Two ingest paths.** `insights_refresh._ingest_step` walks `getArtists`, then `getArtist` per artist, then `getAlbum` per album (N+1, 40 artists per tick, 7-day freshness). `intelligence/musicbrainz/auto_fill.run_cycle` separately detects and ingests new albums and reads a full inventory daily. Both end in `ingest_album`. `library_enrich.handle_requests::find_artist` also reads the full `getArtists` index for each manual request.

**F11 (C/P). In-memory schedule state.** The similar-artist precompute keeps `last_day` in a local variable, so every web restart re-runs the day's pass (the cursor persists, the "done today" flag does not). `prune_finished` in the job runner has no caller, so `job_runs` grows without bound.

**F12 (M). Dead or obsolete code** (usage checked by search across the repository, including tests):

| Item | Evidence | Action |
|---|---|---|
| `read_only_command_policy.py` | Imported only by its own test; not copied into the image | Remove with its test |
| `navidrome_server.get_server_source` and `server_source_redaction.py` | No caller of `get_server_source` anywhere; the redaction module is imported only inside it and by its test. Remnant of the removed MCP runtime | Remove function, module, test, and the Dockerfile `COPY` entry |
| `musicbrainz_rating_client.py` (5-line shim) | Imported by `navidrome_server.py` and one test; real code is `integrations/musicbrainz/rating_client.py` | Point both importers at the real module, remove shim and `COPY` entry |
| `Dockerfile-E` | Tracked stale copy of an older Dockerfile (an editor or `sed -i` backup) | Remove |
| Private MusicBrainz pacers (F2) | Superseded once the shared gate exists | Remove inside R3, not before |
| `open_readonly` unused | Intended design never wired | Wire it (R4); do not remove |
| "Compatibility adapter" functions in `navidrome_server.py` (about 50) | Many are reached as `librarian.<name>` attributes, which a plain import search does not show | Remove only those with zero references of any form (C2); no size-only refactor |

`music_tag_audit.py`, `recommendation_run_metrics.py` and `recommendation_feedback.py` are in use and stay.

## 5. Target architecture

Two processes, one image, one `/data` volume, one host. No new services.

```text
clients ──> FastAPI web (1 Uvicorn process)
            - reads stores; short owner-state and queue writes
            - provider calls only through the shared gate,
              never blocking a response that has a usable cached value
                     │
        ┌────────────┼──────────────────────────────┐
        v            v                              v
  SQLite stores   provider gate file          external providers
  (/data)         (/data/provider_gate.sqlite3)   ^
        ^            ^                              │
        └────────────┴──── worker (exactly 1, file-locked)
                           - table-driven scheduler, persisted last-run
                           - auto fill, insights, lenses, discovery refresh,
                             similar-artist precompute, store maintenance
```

Rules that define the design:

1. **One budget, not one egress.** Any process may call a provider, but only after reserving a slot in the shared gate. Budgets are a correctness constraint.
2. **Exactly one worker,** enforced by an exclusive lock on `/data/worker.lock`. This is what makes a simple scheduler safe and makes any `running` worker job at startup provably stale.
3. **Web startup starts no periodic work.** Request-triggered hooks (`library_resync.install()`) stay in the web process.
4. **Reads do not write.** Read routes use read-only connections; migrations and one-time maintenance run once per process start, not per request.
5. **Stale is usable.** A cached value past its TTL is served and refreshed in the background. Only a value that has never been fetched may make a request wait, and only within that route's existing deadline.
6. **Stores keep their roles.** Server V2 store: modelled facts, edges, provenance, jobs. State file: owner decisions. `metadata_cache`: opaque provider answers with a TTL. Discovery, settings, acquisition, radio, artwork and waveform stores are unchanged.

## 6. Design notes for the non-obvious parts

### 6.1 Shared provider gate (steps R2, R3)

A dedicated file `/data/provider_gate.sqlite3`, separate from the knowledge store so that slot reservations never queue behind a long knowledge write and the web process needs no extra write access to the knowledge file.

```sql
CREATE TABLE gate (
  provider TEXT PRIMARY KEY,
  next_at REAL NOT NULL,          -- wall-clock time of the next free slot
  blocked_until REAL NOT NULL DEFAULT 0,
  day TEXT NOT NULL DEFAULT '',   -- local date of the counter
  day_count INTEGER NOT NULL DEFAULT 0
);
```

`reserve(provider, max_wait) -> bool`: in one `BEGIN IMMEDIATE` transaction read the row, compute `start = max(now, next_at, blocked_until)`, return False without writing if `start - now > max_wait`, otherwise set `next_at = start + interval`, bump the day counter, commit, then sleep `start - now` **outside** the transaction. `penalize(provider, seconds)` sets `blocked_until` after a 429 or 503 (use `Retry-After` when present). This is the reservation algorithm `SourceLimiter.admit` already uses in-process, moved to a shared row.

Details that matter:

- Wall clock (`time.time`), because monotonic clocks are not comparable across processes. Clamp a `next_at` that is more than 60 s in the future back to `now` so a clock step cannot freeze a provider.
- Intervals live in one table in code: MusicBrainz 1.1 s. Other providers keep their current in-process spacing until M2 shows a reason to gate them; the gate accepts any provider name.
- Web callers pass the remaining request deadline as `max_wait` and report `rate_limited` on refusal, as search does today. Worker callers pass a long wait. The worker is sequential per thread, so it never queues more than one slot per thread ahead; no priority scheme is needed at this size.
- If the gate file cannot be opened or written, fall back to an in-process pacer at twice the interval and log once. Never proceed unpaced.
- Journal mode WAL, `synchronous = NORMAL`, busy timeout 5 s; one connection per thread.

### 6.2 Worker scheduler (step W1)

Not a queue. A list of entries `(name, due(now, last_run) -> bool, run())` evaluated by one scheduler thread, with `last_run` persisted in the knowledge store's `meta` table under `schedule:<name>`. Jobs run sequentially on that thread; the auto-fill poll keeps its own thread because it must stay responsive. Each `run()` still goes through `run_job`, so status, checkpoints and last-known-good are unchanged. Daily jobs compare the local date of `last_run` with today; interval jobs compare elapsed seconds. The stop event is checked between jobs and inside loops through `JobContext.cancelled()` or a passed `stop`.

Manual triggers from the web continue to run in the web process where they do today, wrapped in `run_job` with the same job name as the scheduled run, so the unique active index prevents overlap across processes.

### 6.3 Store access (step R4)

- `ensure_store(path)`: runs `open_store` once per process and path (migrations, state attach, `move_legacy_decisions`), then closes. Called at web startup and at worker startup.
- Read routes: `open_readonly(path)`. A read-only WAL connection needs the `-shm` file; `ensure_store` guarantees it exists and `/data` is writable.
- Write routes: `open_writer(path)`, which is `connect` plus `ATTACH` with no migration and no legacy move.
- Connection reuse per thread is deliberately not included. Measure open cost in M2 first.

### 6.4 Freshness states (kept from revisions 3 and 4)

Field-level states, already representable with `source_state`: fresh, stale (serve and refresh), pending (never fetched), not found (negative TTL, 7 days doubling to 90), error or blocked (backoff, never a negative entry). Starting windows: stable facts 90 days; ratings, tags, bios 30 to 90 days; popularity and similar artists 7 days; daily inputs 1 day. A missing relationship in the slice is not proof of absence in MusicBrainz.

## 7. Roadmap

Step identifiers are stable; refer to them in PR titles. **Model** names the single implementing model and effort.

### Phase R: correctness and reliability (critical path)

#### R1. Stale-run recovery and single-worker lock

- **Objective:** a worker restart never leaves a job stuck, and two workers can never run at once.
- **Current state:** F1. No lock; nothing stops a second `python -m app.worker`.
- **Proposed changes:** (a) at worker start take a non-blocking exclusive `fcntl.flock` on `DATA_DIR/worker.lock`, hold it for the process lifetime, exit with a clear log line and non-zero status if it is held; (b) define `WORKER_JOBS` (the job names only the worker runs) and, after taking the lock and before starting threads, requeue every `running` row for those names; (c) call `prune_finished` once per day.
- **Affected components:** `app/worker.py`, `intelligence/jobs/runner.py` (add `recover_running(db, jobs)`), the `JOB` constants in `intelligence/insights/runtime.py`, `provider_runtime.py`, `intelligence/musicbrainz/api_fill.py`, `intelligence/wikidata/ingest.py`, `intelligence/taste/popularity_job.py`.
- **Implementation guidance:** requeue with `UPDATE job_runs SET state='queued' WHERE state='running' AND job IN (...)`; keep `started_at` and `progress` so the run resumes from its checkpoint. Do not touch jobs the web runs (`taste` refresh already recovers by age; give `paths_warm` the same age-based recovery with a threshold above its `max_seconds`). Do not requeue the slice import automatically; mark it `failed` with an explanatory error instead, because resuming a multi-gigabyte import needs an explicit decision.
- **Dependencies:** none.
- **Risks:** requeueing a job that is actually running. Excluded by the lock; test both orders.
- **Verification:** test that reproduces F1 (insert a `running` row, call `run_job`, assert `skipped`), then asserts recovery; test that a second worker exits; test that web-owned job rows are untouched.
- **Acceptance criteria:** after a simulated kill mid-run, the next worker start resumes the job from its checkpoint; a second worker process exits within one second; `job_runs` keeps at most 20 finished rows per job and scope.
- **Model:** Sonnet, Medium. Cross-process state and job semantics; small diff but easy to get subtly wrong.

#### R2. Shared provider gate module

- **Objective:** one reservation point for provider slots across processes and threads.
- **Current state:** F2. Not implemented.
- **Proposed changes:** add `integrations/provider_gate.py` as specified in 6.1, with `reserve`, `penalize`, `snapshot()` (for diagnostics) and injectable clock and sleep.
- **Affected components:** new module; new file `/data/provider_gate.sqlite3`. No caller changes in this step.
- **Implementation guidance:** follow 6.1 exactly. Path from `DATA_DIR`. Create the table on first open per process, not per call. Expose a process-wide default instance and allow tests to construct their own on a temporary path.
- **Dependencies:** none.
- **Risks:** a bug here throttles or unthrottles everything; hence no callers until the tests pass.
- **Verification:** unit tests for spacing, refusal past `max_wait`, `penalize`, day rollover, clock-step clamp, fallback when the file is unwritable; a multi-process test (two `multiprocessing` workers, 10 reservations each) asserting no two granted slots are closer than the interval.
- **Acceptance criteria:** the multi-process test passes 20 consecutive runs locally and in CI; no network access in tests.
- **Model:** Sonnet, High. Concurrency primitive on which a provider's terms depend.

#### R3. Route every MusicBrainz call through the gate

- **Objective:** total MusicBrainz traffic from this host never exceeds one request per 1.1 s.
- **Current state:** the pacers and direct callers listed in F2.
- **Proposed changes:** replace each private MusicBrainz pacer with `provider_gate.reserve("musicbrainz", max_wait)`; add the reservation to direct callers that have none; call `penalize` on 429 and 503. Then delete the superseded pacing code (`Paced` interval logic, `_paced_json` spacing, `album_year` lock and `_last_request`, the `musicbrainz` entry of `SourceLimiter`).
- **Affected components:** the files listed in F2.
- **Implementation guidance:** first produce the call-site inventory in the PR description (file, function, current pacing, caller's deadline). Keep each function's injected `sleep` or `pause` parameters where tests use them, defaulting to the gate. Preserve retry counts and budgets exactly; this step changes spacing only. Split into two PRs if the diff is large: worker-side (`intelligence/`) first, then web-side (`discovery/`, `integrations/`).
- **Dependencies:** R2.
- **Risks:** slower background jobs when the web is active (intended); a missed call site (mitigate with the test below).
- **Verification:** a test that fails if any module outside `integrations/provider_gate.py` contains the MusicBrainz host string without importing the gate (allow-list for URL constants only); existing provider tests still pass; request-count assertions unchanged.
- **Acceptance criteria:** search for private MusicBrainz sleeps returns none; the boundary test is in CI; with web and worker both active in a local fake-provider run, recorded request timestamps are never closer than 1.1 s.
- **Model:** Sonnet, Medium. Many call sites with differing semantics; pattern is fixed by R2.

#### R4. Read-only knowledge reads

- **Objective:** a read request performs no write and no migration.
- **Current state:** F3.
- **Proposed changes:** implement 6.3. Switch read routes in `app/api/knowledge.py`, `capabilities.py`, `insights.py` (GET), `popularity.py` (GET), `smart_playlists.py` (GET) to `open_readonly`; switch write routes to `open_writer`; call `ensure_store` at web and worker startup. Correct the "only writer" wording in `compose.yaml` and `app/worker.py` to "only writer of knowledge facts".
- **Affected components:** `intelligence/store/db.py`, `intelligence/store/__init__.py`, the `app/api/*` modules that call `open_store`, `app/main.py`, `app/worker.py`.
- **Implementation guidance:** classify each `open_store` caller as read or write by reading the handler, and list the classification in the PR. If the store file does not exist yet (fresh install, web starts before the worker), `ensure_store` creates it; keep that behaviour. Keep `open_store` for the worker and scripts.
- **Dependencies:** none (independent of R1 to R3).
- **Risks:** a route classified as read that writes will now fail loudly; a version mismatch between a newer web image and an older store is handled by `ensure_store` migrating at startup, as today.
- **Verification:** test that a read route succeeds while another connection holds `BEGIN IMMEDIATE` on the store (today it would block); test that every write route still writes; contract fixtures in `intelligence/api/fixture_set.py` unchanged.
- **Acceptance criteria:** no `INSERT`, `UPDATE`, `DELETE` or migration statement executes during any GET under `/api/knowledge/`, shown by a test using `sqlite3` `set_trace_callback`.
- **Model:** Sonnet, Medium. Database access change across several routes; classification needs care.

#### R5. Worker loop lifecycle

- **Objective:** loops stop cleanly and do not spend provider budget on every restart.
- **Current state:** F4.
- **Proposed changes:** pass the stop event into `insights_refresh`; replace `time.sleep` with `stop.wait`; persist the last successful refresh time in `meta` and skip a run that is not due; join worker threads on shutdown for a bounded grace period; fix the module docstring; add `stop_grace_period: 30s` to the worker service.
- **Affected components:** `app/services/insights_refresh.py`, `app/worker.py`, `compose.yaml`.
- **Implementation guidance:** keep `CHECK_SECONDS`, `PROVIDER_BUDGET`, `INGEST_ARTISTS_PER_TICK` and `INGEST_TTL_SECONDS` unchanged. First establish by reading `refresh_provider_lenses` whether a just-restarted run is already cheap; record the answer in the PR. If W1 lands first, the persisted cadence comes from the scheduler and this step shrinks to the stop handling.
- **Dependencies:** R1 (recovery makes a hard kill safe regardless).
- **Risks:** a refresh skipped that used to run at startup; the first run after an upgrade has no stored time and must run.
- **Verification:** tests for due and not-due starts, for stop during the wait, and for stop during a run (run ends at the next checkpoint).
- **Acceptance criteria:** worker exits within the grace period on SIGTERM with no `running` rows left; two restarts within an hour cause one refresh.
- **Model:** Sonnet, Low. Small, well-bounded change in two files.

### Phase M: measurement (start in parallel with Phase R)

#### M1. Provider and store counters

- **Objective:** know how many provider requests are made, to whom, with what outcome, and how long store operations take.
- **Current state:** only total request time is measured.
- **Proposed changes:** a tiny in-process metrics module (`app/services/runtime_metrics.py`): thread-safe counters and duration sums keyed by `(provider, outcome_class)` and by store operation. Feed it from the gate (reservations, wait time), from `httpx` response hooks on the shared clients that exist (`app/api/metadata.py::_EXTERNAL_HTTP`, the Navidrome client after P2), and from `intelligence/store/db.py` (count and time of opens; log any operation over 250 ms and any `database is locked`). Expose `GET /api/diagnostics/runtime` behind the existing auth; the worker writes its snapshot to `meta` every few minutes for the same endpoint to read.
- **Affected components:** new module, `integrations/provider_gate.py`, `app/api/metadata.py`, `intelligence/store/db.py`, one new route.
- **Implementation guidance:** labels are provider name and outcome class only (`ok`, `not_found`, `rate_limited`, `timeout`, `error`). No URLs, MBIDs, names, tokens or query strings. Map hosts to provider names with a fixed table; unknown hosts count as `other`. No new dependency; no Prometheus.
- **Dependencies:** R2 for gate counters (other parts independent).
- **Risks:** leaking private data through labels; overhead on hot paths (keep to a dict increment under a lock).
- **Verification:** unit tests for counters and redaction; a test that the endpoint requires authentication.
- **Acceptance criteria:** after a local session the endpoint reports per-provider request counts and wait totals for both processes, and store open count and time.
- **Model:** Sonnet, Medium. Touches several layers and has a privacy constraint.

#### M2. Baseline capture

- **Objective:** a repeatable before-and-after measurement for the Phase P steps.
- **Current state:** none.
- **Proposed changes:** `scripts/efficiency_baseline.py`: against a running local instance, request a fixed list of routes (library pages, one artist page, one album page, one search, `/api/knowledge/connections`, `/api/knowledge/paths` including `album_gaps`) N times, record `Server-Timing`, and diff `/api/diagnostics/runtime` before and after. Output one JSON file and a short table. Record the first result in this document's evidence log.
- **Affected components:** new script only.
- **Implementation guidance:** follow `docs/LOCAL_UI_TESTING.md` for the local instance. Warm-cache runs only by default so no new provider traffic is caused; a cold run needs the owner's approval. Report median and p95.
- **Dependencies:** M1.
- **Risks:** none to the product; results from a development machine are indicative only.
- **Verification:** script runs twice with comparable output.
- **Acceptance criteria:** a committed baseline table exists and each Phase P PR quotes its own before-and-after from this script.
- **Model:** Haiku, Medium. Bounded script with a fixed specification.

#### M3. Process-local state inventory

- **Objective:** one table of module globals, locks, caches and threads, each classified (immutable, rebuildable cache, shared mutable, singleton side effect).
- **Current state:** partial lists in this document only.
- **Proposed changes:** add the table as an appendix to this document. No code.
- **Affected components:** documentation.
- **Implementation guidance:** search for module-level dicts and locks, `threading.Thread(`, `ThreadPoolExecutor(`, `lru_cache`. Start from the thread list in F2, F8 and section 3.
- **Dependencies:** none.
- **Risks:** none.
- **Verification:** each row cites file and symbol.
- **Acceptance criteria:** the table exists and W2, W3 and K1 reference it.
- **Model:** Haiku, Medium. Mechanical survey with a fixed format.

### Phase P: high-value, low-risk performance fixes

Each step quotes M2 numbers before and after. They are independent of one another.

#### P1. Cache settings reads

- **Objective:** remove two SQLite opens and a `chmod` from every Navidrome call and every authenticated request.
- **Current state:** F5.
- **Proposed changes:** in `settings/persistence.py`: run `initialize()` once per process; keep one long-lived connection guarded by a lock; cache the decoded settings and re-read only when `PRAGMA data_version` on that connection changes or after a local `write()`.
- **Affected components:** `settings/persistence.py` and its tests. Callers unchanged.
- **Implementation guidance:** `data_version` changes when any other connection, in any process, commits to the file, so worker and web see each other's changes on the next read. Return a shallow copy so callers cannot mutate the cache. Keep the legacy-migration behaviour of `read()` exactly; run it on reload only. Open the connection with `check_same_thread=False` and serialize use with the lock.
- **Dependencies:** none.
- **Risks:** authentication and credential changes must be visible on the next read. This is the reason for `data_version` instead of a time-based cache.
- **Verification:** tests: a write through a second connection is visible on the next `read()`; password change takes effect on the next request; N reads perform one query when nothing changed.
- **Acceptance criteria:** M2 shows fewer store opens per request; auth tests unchanged and passing.
- **Model:** Sonnet, Medium. Small change, but it sits under authentication.

#### P2. Reuse the Navidrome HTTP client

- **Objective:** keep connections to Navidrome alive.
- **Current state:** F6.
- **Proposed changes:** a module-level `httpx.Client` in `integrations/navidrome/client.py`, created lazily under a lock, same timeout and `follow_redirects=False`; `client_factory` remains as a test override that bypasses the shared client.
- **Affected components:** `integrations/navidrome/client.py`, its tests.
- **Implementation guidance:** `httpx.Client` is safe to share across threads. The base URL is passed per request, so a settings change needs no client rebuild. Set explicit limits (for example 10 connections, keep-alive 30 s).
- **Dependencies:** none.
- **Risks:** a stale keep-alive connection after Navidrome restarts; `httpx` retries connection establishment, and callers already handle `HTTPError`.
- **Verification:** test that two calls reuse one client; existing client tests pass.
- **Acceptance criteria:** M2 shows lower median time for library routes; no behavioural change.
- **Model:** Haiku, Medium. Single file, clear pattern.

#### P3. Fix the legacy metadata cache

- **Objective:** remove per-operation schema work and unbounded growth.
- **Current state:** F7.
- **Proposed changes:** create the table once per process; WAL and `synchronous = NORMAL`; one connection per thread; add `prune(older_than_seconds)` and call it daily from the worker with a cutoff of 400 days (longer than the longest TTL in use, 365 days).
- **Affected components:** `metadata_cache.py`, its test, one scheduler entry (or a call in the worker loop until W1).
- **Implementation guidance:** keep the public `get(key, ttl)` and `set(key, value)` and the rule that any storage failure is a miss. Confirm the longest TTL by searching callers before fixing the cutoff. Add an index on `cached_at` for the prune.
- **Dependencies:** none; W1 optional.
- **Risks:** deleting rows a caller still wants; excluded by the cutoff check above.
- **Verification:** existing tests; new tests for prune and for failure-is-a-miss with a locked file.
- **Acceptance criteria:** no `CREATE TABLE` after the first operation in a process (trace callback test); file size stops growing in steady state.
- **Model:** Haiku, Medium. Contained module with existing tests.

#### P4. One bounded cache helper with single-flight for metadata routes

- **Objective:** bounded memory, no duplicate concurrent provider calls, one implementation of the lookup ladder.
- **Current state:** F8.
- **Proposed changes:** add `app/services/layered_cache.py`: `get_or_load(namespace, key, *, found_ttl, miss_ttl, loader)` that checks a bounded in-memory LRU (default 2,000 entries per namespace), then `persistent_metadata`, then calls `loader` under a per-key lock so concurrent callers share one result. Migrate the eight caches in `app/api/metadata.py` one at a time.
- **Affected components:** new helper, `app/api/metadata.py`, `app/services/persistent_metadata.py` (unchanged interface).
- **Implementation guidance:** preserve each cache's current TTLs, negative TTLs, key format, partial-result TTL (reviews) and the rule that timeouts and provider errors are not cached as misses. Migrate in separate commits and compare route output on fixtures after each. Do not add stale-while-revalidate here; that is K2.
- **Dependencies:** none.
- **Risks:** changed cache semantics on one of eight paths; a per-key lock held across a slow loader (bound it with the route's existing timeout).
- **Verification:** unit tests for eviction, TTLs, single-flight (two threads, one loader call) and error-not-cached; existing metadata route tests.
- **Acceptance criteria:** no module-level cache dict remains in `app/api/metadata.py`; memory entries per namespace never exceed the bound; a concurrent identical request triggers one provider call.
- **Model:** Sonnet, Medium. Refactor across an 800-line route module with differing semantics per cache.

#### P5. Inventory snapshot and ingest consolidation

- **Objective:** stop re-reading the whole library when nothing changed, and keep one ingest path.
- **Current state:** F9, F10.
- **Proposed changes:** (a) `discovery/library_snapshot.py`: a process-level cached album inventory keyed by the Navidrome scan marker (`getScanStatus` `lastScan` and `count`), revalidated at most every 30 s; use it in `app/api/knowledge.py::_play_records` first, then the other callers. (b) Investigate, then decide in the PR: is `_ingest_step` still needed now that auto fill ingests new albums and reads a full inventory daily? If its coverage is a subset, remove it; if it covers albums auto fill skips, state which and keep it bounded. (c) Replace `find_artist`'s full index read with a store lookup by MBID where the entity already carries a Navidrome id.
- **Affected components:** `discovery/library_snapshot.py`, `app/api/knowledge.py`, `app/services/insights_refresh.py`, `app/services/library_enrich.py`, `intelligence/musicbrainz/auto_fill.py` (read only).
- **Implementation guidance:** play counts and stars change without a scan. For `album_gaps`, which needs play data, either keep a short maximum age (for example 5 minutes) on the snapshot or confirm the fields used are scan-stable; state which in the PR. Apply the same question to the owned search index before changing its 10-minute TTL; do not change the index in this step.
- **Dependencies:** P2 helps but is not required.
- **Risks:** stale play data on the gaps page; losing ingest coverage for albums without an MBID.
- **Verification:** request-count test (two `album_gaps` requests cause one inventory read); ingest equivalence test on a fixture library before removing `_ingest_step`.
- **Acceptance criteria:** repeated `album_gaps` requests within the maximum age make at most one `getScanStatus` call each and no inventory paging; one documented ingest path, or a written reason for two.
- **Model:** Sonnet, Medium. Needs judgement on equivalence and data freshness.

### Phase W: finish the worker split

#### W1. Table-driven scheduler

- **Objective:** one place that decides what runs when, surviving restarts.
- **Current state:** each loop has its own thread, sleep and in-memory or ad hoc "done" state (F11).
- **Proposed changes:** implement 6.2 in `app/worker_schedule.py`; register the insights refresh and the maintenance calls (R1 prune, P3 prune) first.
- **Affected components:** `app/worker.py`, new module, `intelligence/store` `meta` access.
- **Implementation guidance:** persist `schedule:<name>` only after a run returns (success or handled failure); a run that raises logs the error type only and still records the attempt time so a broken job does not spin. Jobs run one at a time. Keep the auto-fill thread separate.
- **Dependencies:** R1, R5.
- **Risks:** a long job delaying others; acceptable because all are budgeted, and order is fixed and visible.
- **Verification:** tests with a fake clock for interval and daily entries, restart persistence, stop between jobs, raising job.
- **Acceptance criteria:** restarting the worker neither repeats a job that is not due nor skips one that is; `/api/diagnostics/runtime` lists each entry's last run.
- **Model:** Sonnet, High. Central runtime piece; correctness under restart matters more than size.

#### W2. Move similar-artist precompute to the worker

- **Objective:** no periodic loop in `app/api/search.py`.
- **Current state:** started from web startup; daily flag in memory; depends on the owned index, which is process-local.
- **Proposed changes:** register the precompute in the scheduler (daily, with its persisted cursor); remove `start_similar_precompute` from web startup.
- **Affected components:** `app/api/search.py`, `app/main.py`, `app/worker_schedule.py`.
- **Implementation guidance:** the worker builds its own owned index for the run and drops it afterwards; record its build time and peak memory in the PR. If memory is a problem, derive the artist list from the album inventory snapshot instead. Results are written through the existing list and cache stores, which the web already reads. The route adapter `artist_network_for` imports from `app.api.metadata`; move the shared parts to a service module so the worker does not import route modules.
- **Dependencies:** W1, R3 (the job calls providers).
- **Risks:** duplicate index memory in the worker; behaviour drift in what is precomputed.
- **Verification:** the existing precompute tests against the new entry point; test that web startup starts no precompute thread.
- **Acceptance criteria:** same cursor progression and output on fixtures; web process thread list no longer contains `navidrome-similar-artists`.
- **Model:** Sonnet, Medium. Cross-module move with one dependency to untangle.

#### W3. Move lens refresh and the discovery scheduler to the worker

- **Objective:** web startup starts no periodic work.
- **Current state:** `lens_service.start_daily_refresh` and `navidrome_server._start_discovery_scheduler` run in the web process; manual refreshes also run there under process-local locks.
- **Proposed changes:** register both in the scheduler with their existing cadences and due rules (`_due`, `refresh_stale_lists`, `automatic_refill_enabled`); wrap each list refresh, scheduled and manual, in `run_job` with a per-list scope so the two processes cannot refresh the same list at once; delete `_start_discovery_background` and its timer from `app/main.py`.
- **Affected components:** `app/main.py`, `navidrome_server.py` (scheduler functions), `discovery/lens_service.py`, `discovery/refresh.py`, `app/worker_schedule.py`.
- **Implementation guidance:** this touches recommendation refresh. Change where it runs and nothing else: same functions, same arguments, same origin labels (`origin="scheduler"`). `_bump_discogs_generation_at_startup` is a startup action, not a loop; keep it in the web process. When a manual refresh finds the list already running, return the existing "started" response.
- **Dependencies:** W1, R3. Do after W2 so the pattern is proven on lower-risk work.
- **Risks:** recommendation lists not refreshing if the worker is down (state it in `docs/DEPLOYMENT.md` in the same PR); double refresh during rollout if web and worker images differ in version.
- **Verification:** tests that a scheduled and a manual refresh of one list cannot overlap; that disabled automatic refill still disables scheduled runs; that web startup starts no scheduler thread. Recommendation output tests unchanged.
- **Acceptance criteria:** `app/main.py` has no background start besides `library_resync.install()` and the Discogs generation bump; list refresh cadence on a 48-hour local run matches the previous behaviour.
- **Model:** Sonnet, High. Safety-sensitive area, cross-process exclusion, legacy module.

### Phase K: knowledge and request-path latency (evidence-gated)

#### K1. Request-time provider call inventory

- **Objective:** decide from data which routes still wait on providers and how often.
- **Current state:** unknown; revision 2 assumed artist and album pages are the problem.
- **Proposed changes:** using M1 and M2 output, add a table to this document: route, providers called, cache hit rate, median and p95 provider wait, miss causes.
- **Affected components:** documentation.
- **Implementation guidance:** one week of real use by the owner, or a scripted session over 50 owned and 20 unowned entities with the owner's approval for the traffic.
- **Dependencies:** M1, M2, P4.
- **Risks:** none.
- **Verification:** numbers trace to recorded output files.
- **Acceptance criteria:** the table exists and K2 and K3 are confirmed, narrowed or cancelled in writing.
- **Model:** Sonnet, Low. Analysis and a decision, little code.

#### K2. Stale-while-revalidate for metadata routes

- **Objective:** a page never waits on a provider when any earlier answer exists.
- **Current state:** an expired entry is a miss and the request waits for the provider.
- **Proposed changes:** extend the P4 helper: when a value exists but is past its TTL, return it and schedule one background refresh (bounded pool, single-flight, through the gate). Store `fetched_at` alongside values so responses can state age where the contract allows.
- **Affected components:** `app/services/layered_cache.py`, `metadata_cache.py` (read with expiry information), `app/api/metadata.py`.
- **Implementation guidance:** needs `MetadataCache.get` to return the timestamp; add a new method, keep the old one. Hard maximum staleness per namespace (for example 10 times the TTL) after which the value is treated as missing. Background refresh failures leave the stale value and follow the existing error rules.
- **Dependencies:** P4, R3, and K1 confirming that expiry misses are a material share of provider waits.
- **Risks:** serving outdated values longer than today; unbounded background work (bound the pool and queue, drop on overflow).
- **Verification:** tests for stale hit plus one refresh, maximum staleness, refresh failure, overflow.
- **Acceptance criteria:** on the M2 warm-then-expired scenario, route time is independent of provider latency; provider request totals do not rise.
- **Model:** Sonnet, High. Concurrency plus cache semantics on user-visible data.

#### K3. Worker prefetch for owned entities (optional)

- **Objective:** remove first-view misses for the owned library.
- **Current state:** first view of an artist or album fetches on demand.
- **Proposed changes:** a scheduled, budgeted job that walks owned artists and albums in the order new additions, recently played, most played, rest, and fills the same cache keys the routes read.
- **Affected components:** new job module, scheduler entry, service functions extracted from `app/api/metadata.py`.
- **Implementation guidance:** only for namespaces K1 shows have a high first-view miss cost. Daily request budget per provider, recorded through the gate counter. Progress in job checkpoints; coverage counts in diagnostics.
- **Dependencies:** K1, K2, W1.
- **Risks:** provider traffic increase, which needs explicit owner approval; storage terms for text content (section 3, unverified).
- **Verification:** request-budget tests; resume tests.
- **Acceptance criteria:** stated coverage percentage of owned entities within a stated number of days, both set from K1.
- **Model:** Sonnet, Medium. Follows established job patterns.

### Phase S: store hygiene

#### S1. Size and growth report, then retention

- **Objective:** know what grows, then bound it.
- **Current state:** `observations` is append-only with no retention; growth is unmeasured.
- **Proposed changes:** first a read-only script reporting row counts and bytes per table for each SQLite file (`dbstat` where available). Then, only for tables shown to grow, a tested retention job: for observations, keep the newest row per `(source, entity_hint)` plus any row referenced by `source_state.observation_id`.
- **Affected components:** new script; later `intelligence/store/` and a scheduler entry.
- **Implementation guidance:** two PRs. The append-only trigger blocks `UPDATE`, not `DELETE`; deletion is deliberate and must run in bounded batches inside short transactions. Never touch the state file.
- **Dependencies:** none for the report; W1 for the job.
- **Risks:** deleting provenance still needed by a derivation. Check every reader of `observations` first and list them in the PR.
- **Verification:** retention tests proving referenced and newest rows survive.
- **Acceptance criteria:** report committed to the evidence log; if retention is built, store size is stable across two weeks.
- **Model:** Sonnet, Medium. Deletion in a provenance table is safety-sensitive.

#### S2. Backup and restore procedure

- **Objective:** a verified way to copy every store while the app runs.
- **Current state:** unverified (section 3).
- **Proposed changes:** `scripts/backup_stores.py` using `sqlite3.Connection.backup` for each file under `/data`, and a restore section in `docs/DEPLOYMENT.md`.
- **Affected components:** new script, documentation.
- **Implementation guidance:** enumerate the store files from the code constants, not a glob. The settings store contains credentials: keep mode `0o600` on its copy.
- **Dependencies:** none.
- **Risks:** none to running data; the backup API is read-only on the source.
- **Verification:** test that backs up while a writer is active and opens the copy; wipe-and-restore test showing owner decisions survive a knowledge rebuild.
- **Acceptance criteria:** documented, tested procedure covering every store.
- **Model:** Haiku, Medium. Well-specified script and documentation.

#### S3. Slice refresh semantics (deferred)

Deferred until the owner wants a second import. Before any recurring import: define pruning of entities and edges that disappeared, keep last-known-good on failure, and put the server-side merge path in the repository (today it is owner-local scripts). Model when opened: Sonnet, High.

### Phase C: cleanup

#### C1. Remove verified dead code

- **Objective:** delete the items in F12 marked "Remove".
- **Current state:** F12.
- **Proposed changes:** remove `read_only_command_policy.py` and its test; `get_server_source`, `server_source_redaction.py` and its test; the `musicbrainz_rating_client.py` shim after repointing its two importers; `Dockerfile-E`; the matching entries in the Dockerfile `COPY` line.
- **Affected components:** repository root, `navidrome_server.py`, `Dockerfile`, tests.
- **Implementation guidance:** before each deletion repeat the search for the symbol as an import, as an attribute (`librarian.<name>`, `getattr`), as a string, and in `scripts/`, `.github/` and docs. Paste the search results in the PR. One commit per item.
- **Dependencies:** none.
- **Risks:** an unseen dynamic reference; container build failure from a stale `COPY` entry (CI `container-smoke` covers it).
- **Verification:** required CI workflows on the exact head.
- **Acceptance criteria:** items gone, CI green, image builds.
- **Model:** Haiku, Low. Mechanical and already evidenced.

#### C2. Remove unreferenced compatibility adapters

- **Objective:** shrink `navidrome_server.py` only where code is provably unused.
- **Current state:** about 50 adapters; unknown how many are unreferenced.
- **Proposed changes:** produce a table (adapter, references found by import, by attribute, by string, in tests only). Remove those with no references outside tests, together with tests that exist only to exercise the adapter.
- **Affected components:** `navidrome_server.py`, tests.
- **Implementation guidance:** this is not a modularization pass; do not move or rename anything that is used. An adapter passed as a callback inside `navidrome_server.py` itself counts as used.
- **Dependencies:** W3 (removes scheduler code first and changes what is referenced).
- **Risks:** attribute access through the `librarian` object is the main trap.
- **Verification:** required CI; the reference table in the PR.
- **Acceptance criteria:** every removed symbol has a zero-reference row; no behaviour change.
- **Model:** Haiku, Medium. Mechanical but needs disciplined evidence per symbol.

#### C3. Container runtime settings

- **Objective:** basic runtime hygiene for the two services.
- **Current state:** no healthchecks, no init process, default stop timeout.
- **Proposed changes:** `init: true` on both services; a web healthcheck against an unauthenticated lightweight route; a worker healthcheck that checks the age of a heartbeat value the scheduler writes; `stop_grace_period` (from R5). Memory limits only after M2 gives real numbers.
- **Affected components:** `compose.yaml`, `DOCKER.md`, `docs/DEPLOYMENT.md`.
- **Implementation guidance:** the image has no `curl`; use a Python one-liner for healthchecks. Do not add packages.
- **Dependencies:** W1 for the worker heartbeat.
- **Risks:** a too-strict healthcheck causing restart loops; use generous intervals and `start_period`.
- **Verification:** `container-smoke` workflow; local `docker compose up` shows both healthy.
- **Acceptance criteria:** both services report healthy; killing the scheduler thread makes the worker unhealthy.
- **Model:** Haiku, Low. Configuration and documentation.

### Critical path and parallel work

```text
R1 ──> R5 ──> W1 ──> W2 ──> W3 ──> C2
R2 ──> R3 ────────────┘ (W2, W3 need R3)
R2 ──> M1 ──> M2 ──> K1 ──> K2 ──> K3
P4 ─────────────────┘ (K1, K2 need P4)
```

- **Critical path:** R1, R2, R3, R5, W1, W2, W3.
- **Independent, can start at once:** R1, R2, R4, P1, P2, P3, P4, M3, S2, C1, and the S1 report.
- **Do not start before their inputs exist:** K2 and K3 (need K1), S1 retention (needs the report), C2 (after W3), memory limits in C3 (after M2).
- **Suggested first batch:** R1, R2, R4 and C1 in parallel; then R3 and M1.

### Model assignment summary

| Step | Model | Effort | | Step | Model | Effort |
|---|---|---|---|---|---|---|
| R1 | Sonnet | Medium | | W1 | Sonnet | High |
| R2 | Sonnet | High | | W2 | Sonnet | Medium |
| R3 | Sonnet | Medium | | W3 | Sonnet | High |
| R4 | Sonnet | Medium | | K1 | Sonnet | Low |
| R5 | Sonnet | Low | | K2 | Sonnet | High |
| M1 | Sonnet | Medium | | K3 | Sonnet | Medium |
| M2 | Haiku | Medium | | S1 | Sonnet | Medium |
| M3 | Haiku | Medium | | S2 | Haiku | Medium |
| P1 | Sonnet | Medium | | S3 | Sonnet | High (deferred) |
| P2 | Haiku | Medium | | C1 | Haiku | Low |
| P3 | Haiku | Medium | | C2 | Haiku | Medium |
| P4 | Sonnet | Medium | | C3 | Haiku | Low |
| P5 | Sonnet | Medium | | | | |

## 8. Cold start and progressive coverage

Kept from revision 4, shortened. These are product rules for any step that fills data.

1. The local owned-entity baseline (Navidrome identities, the loaded slice) is available without external calls.
2. Fill order: new additions, recently played, most played, the rest of the owned library, then neighbourhood. This order schedules metadata only; it must not change recommendation ranking.
3. Publish each entity or field as soon as its own fetch succeeds; keep last-known-good visible during refresh.
4. Clients distinguish known, stale, pending, absent at source and failed. A failed lookup is never shown as absence.
5. Show an estimated completion time only from observed throughput, never from the 1 request per second limit alone.
6. After a restart, resume from checkpoints; after a knowledge rebuild, the state file is intact.

## 9. Standing rules

- FastAPI stays. One Uvicorn process stays. SQLite stays for this single-host deployment.
- No Redis, Celery, RabbitMQ, Kubernetes or PostgreSQL without a measured requirement.
- Provider limits and request budgets are correctness constraints. No provider call without a gate reservation once R3 has covered that provider. No parallelism that bypasses the gate.
- No network I/O while a SQLite write transaction is open. Keep write transactions short.
- Do not convert routes to `async` unless the whole I/O path is awaitable.
- Do not weaken exact matching, cache semantics, failure handling or safety checks to raise hit rates.
- Database migrations, owner state, acquisition, imports and deletion are safety-sensitive: regression tests are mandatory and the diff is reviewed in full.
- No size-only modularization. Extract only what a step in this plan needs.
- Every behavioural change has a regression test; every performance claim has M2 numbers.
- Metrics and logs carry no credentials, URLs with secrets, listening history, names or identifiers.
- Agents run focused tests only; the full suite runs in CI on the exact final head.
- Publication and deployment are separate decisions and are not authorized here.

## 10. Deferred until evidence justifies them

| Item | Open it when |
|---|---|
| More Uvicorn workers | M1 or M2 shows requests queueing in the web process with CPU or thread-pool saturation |
| Profile read models (`artist_profile`, `album_profile`) | A knowledge route is slow on store reads after R4 |
| Per-thread connection reuse for the knowledge store | M1 shows connection opens are a material share of request time |
| Moving every provider client behind worker handlers (strict single egress) | K2 and K3 are in place and request-time provider calls still hurt |
| Priority lanes and reserved budget shares | The single ordered queue demonstrably starves a class of work |
| B1 ratings browse, B2 tracklist browse | K1 shows these calls are frequent for entities the slice does not cover |
| Navidrome `getAlbumList2` replacing per-album detail calls in ingest | P5 keeps `_ingest_step` and it is shown to be slow |
| Owned search index rebuild on scan marker instead of a 10-minute TTL | M2 shows index rebuilds are costly and the fields that change without a scan are identified |
| ListenBrainz chunk size changes | Live response contracts and budgets justify it |
| Gating providers other than MusicBrainz across processes | M1 shows rate-limit responses from them |
| Recurring slice import (S3) | The owner asks for a refresh |

## 11. Old section labels

Code comments and older documents cite the previous structure. Mapping:

| Old label | Now |
|---|---|
| A, A1 to A6 (worker separation) | Sections 5, 6.2; steps R1, R5, W1 to W3 |
| A5 (shared limiter) | Section 6.1; steps R2, R3 |
| B1 to B8 (provider I/O) | Section 2 verdicts; steps P2 to P5; section 10 |
| C (measurement) | Steps M1 to M3 |
| D (multiple web workers) | Section 10; step M3 |
| E, E1 to E7 (knowledge store, single egress) | Sections 5, 6.3, 6.4; steps R4, K1 to K3 |
| E8 (dump slice) | Section 3; step S3 |

## 12. References

- [MusicBrainz API](https://musicbrainz.org/doc/MusicBrainz_API) and [rate limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting): limits apply per client IP.
- [SQLite WAL](https://www.sqlite.org/wal.html), [`PRAGMA data_version`](https://www.sqlite.org/pragma.html#pragma_data_version), [online backup API](https://www.sqlite.org/backup.html).
- [HTTPX clients](https://www.python-httpx.org/advanced/clients/): connection pooling and thread safety.
- [FastAPI async details](https://fastapi.tiangolo.com/async/) and [Starlette thread pool](https://www.starlette.io/threadpool/).
- [ListenBrainz API](https://listenbrainz.readthedocs.io/); batch endpoints and chunk sizes are in `discovery/batch_metadata.py`.

## 13. Change and evidence log

- 2026-11-11 (revision 5): Full rewrite against `main` at `b5a90bf3`. Adds findings F1 to F12 read from source (stuck jobs after a worker kill, unshared MusicBrainz pacing, write transaction on every knowledge read, settings and HTTP client churn, unbounded caches, duplicate ingest, dead code). Replaces the generic dispatcher, the strict single-egress rule and the cache-folding proposal with smaller designs; defers profile read models, lanes and multi-worker web. Corrects status: the worker process, `source_state`, the state-file split, `KnowledgeReader` routes and one real slice import exist; the shared limiter and scheduler do not. Adds a per-step roadmap with model assignments. Documentation only: nothing was executed or measured, and no code, tests, configuration, provider traffic, publication or deployment changed.
- 2026-11-06 (revisions 1 to 4): Combined the provider batching audit with the worker-separation plan; added the review of revision 1, the knowledge-store section, the shared-limiter requirement, the dump-slice decision (D-1), the state-file split, stale-versus-missing rules and cold-start requirements. Full text is in the git history of this file.
