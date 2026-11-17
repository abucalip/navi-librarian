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
- Backup and restore of the SQLite files under `/data` (script and procedure written in S2; not run against the live host).
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

**F13 (P). Empty popularity answers are never cached, so the artist page calls ListenBrainz on every request.** `integrations/listenbrainz/popularity.py::fetch_release_group_popularity` writes `lb:popularity:release-group:{mbid}` only when ListenBrainz returns both listen and user counts. A release group with no listen data is sent again on every request, and the artist page's popularity callable (`app/api/search.py::artist_network_for`) sends all of them in one POST. Measured on the test instance (2026-11-16, M2 live run): 14 of the cold test artist's 28 release-group MBIDs had no row, and the warm artist page made exactly one ListenBrainz call per request (median 418 ms, p95 512 ms). Ruled out from the same tables: the similar-artist records and top-recordings, both of which hit the cache. The album page is fully cached when warm. Source: code read plus the local cache tables, read-only; ListenBrainz itself was not re-queried for the uncached groups.

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
- **Current state:** done, merged in PR #1133 (2026-11-16). Was F1: no lock; nothing stopped a second `python -m app.worker`.
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
- **Current state:** done, merged in PR #1134 (2026-11-16) with the clock-step fix in PR #1135: a block more than `MAX_PENALTY` ahead is capped, not cleared. No callers yet. Was F2.
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
- **Current state:** part 1 (worker side: `api_fill.Paced`, `provider_runtime`, `set_fetchers`) merged in PR #1136 (2026-11-16). Part 2 (web side: `discovery/` callers, `integrations/musicbrainz/*`, search providers, artwork `HostPacer`) merged in PR #1137 (2026-11-16); `PENDING` in `tests/test_musicbrainz_gate_boundary.py` is empty. Live web+worker check done in PR #1164 (squash `34687dc1`, `scripts/gate_spacing_check.py`, fake MusicBrainz, no real provider traffic): 129 requests (web 80, worker 49, interleaved); gate slot starts never closer than 1.1 s; arrivals at the fake server up to 13.7 ms under 1.1 s (min 1.086 s), which is grant-to-wire jitter. The owner kept the 1.1 s interval (MusicBrainz allows 1 per second; jitter does not accumulate because each slot is spaced from the previous slot) and the acceptance wording below was corrected to match. Not exercised: the 429/503 `penalize` path and the artist page route. Pacers and direct callers were listed in F2.
- **Proposed changes:** replace each private MusicBrainz pacer with `provider_gate.reserve("musicbrainz", max_wait)`; add the reservation to direct callers that have none; call `penalize` on 429 and 503. Then delete the superseded pacing code (`Paced` interval logic, `_paced_json` spacing, `album_year` lock and `_last_request`, the `musicbrainz` entry of `SourceLimiter`).
- **Affected components:** the files listed in F2.
- **Implementation guidance:** first produce the call-site inventory in the PR description (file, function, current pacing, caller's deadline). Keep each function's injected `sleep` or `pause` parameters where tests use them, defaulting to the gate. Preserve retry counts and budgets exactly; this step changes spacing only. Split into two PRs if the diff is large: worker-side (`intelligence/`) first, then web-side (`discovery/`, `integrations/`).
- **Dependencies:** R2.
- **Risks:** slower background jobs when the web is active (intended); a missed call site (mitigate with the test below).
- **Verification:** a test that fails if any module outside `integrations/provider_gate.py` contains the MusicBrainz host string without importing the gate (allow-list for URL constants only); existing provider tests still pass; request-count assertions unchanged.
- **Acceptance criteria:** search for private MusicBrainz sleeps returns none; the boundary test is in CI; with web and worker both active in a local fake-provider run, granted gate slots are never closer than 1.1 s; request arrival may vary by a few milliseconds of grant-to-wire jitter (measured at most 14 ms), so arrivals stay above MusicBrainz's 1 s limit.
- **Model:** Sonnet, Medium. Many call sites with differing semantics; pattern is fixed by R2.

#### R4. Read-only knowledge reads

- **Objective:** a read request performs no write and no migration.
- **Current state:** done. Merged in PR #1138 (2026-11-16); the path-cache deviation is closed by the follow-up PR: `GET /api/knowledge/paths` now reads through `open_readonly` and opens a writer only to save a cache miss (`save_db` on `cached_path`, `cached_album_path`, `path_page`), so no GET under `/api/knowledge/` holds a write connection for its read. Was F3.
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
- **Current state:** done, merged in PR #1140 (2026-11-16), squash `034341ea`; closes F4. The insights loop waits on the stop event, keeps its last refresh time in `meta` (`insights_refresh.last_run_at`) so a restart inside `CHECK_SECONDS` waits, and a provider tick stops before its next request on shutdown (`should_stop` in `refresh_provider_lenses`). The worker joins its loop threads within 25 s while it still holds `worker.lock` (compose `stop_grace_period: 30s`). Focused tests only; not deployed. Deviation: the due time uses `meta`, not `job_runs.last_good`, because a budget-stopped provider tick is recorded `succeeded`. The library-enrich (MusicBrainz auto-fill) job now stops mid-run too (PR #1174, squash `07f0dd96`, 2026-11-17): the stop event is checked before each fill request, `getAlbum`, search-sweep album and manual update request, and a stopped fill is left `queued` with `stopped = "shutdown"`, so the next poll resumes it. Not checked with a real SIGTERM during a live fill. CI for head `efd564d4`: `compile` and `test-and-build` were still in progress at merge (19:08 UTC) and had not concluded at 19:12 UTC.
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
- **Current state:** built and merged in PR #1141 (2026-11-16, squash `a1407e69`); first part only; only total request time was measured before. Built: `app/services/runtime_metrics.py`, `MeteredClient` on `_EXTERNAL_HTTP`, gate and store observer hooks, `GET /api/diagnostics/runtime` (web counters plus the worker snapshot from `meta`, saved every 5 minutes). Follow-up merged in PR #1142 (squash `53a8f656`): `install()` now also patches `httpx.Client.send`/`AsyncClient.send`, and `urllib.request.OpenerDirector.open`, so every httpx caller (`httpx.get`/`post`, per-call clients, radio) and every urllib caller (`urlopen`, `build_opener().open`: `api_fill`, wikidata ingest, artwork fetchers, MusicBrainz download and album-year lookups) is counted without touching `navidrome_server.py`. Per-statement store timing was added too (`_TimedConnection` in `intelligence/store/db.py` times `execute`/`executemany` by verb as `sql_select`, `sql_insert` and so on; slow statements log verb and first table name, never SQL text or values). Statement timing does not cover cursor-level calls, `executescript` or row fetching after `execute` returns. Navidrome and Last.fm labels added in PR #1173 (squash `c81bca22`, 2026-11-17): the shared Navidrome client labels its requests `navidrome` through a request event hook (`metrics_provider` extension; only known names are accepted), and `ws.audioscrobbler.com` counts as `lastfm`. PR #1177 (squash `a4804473`, merged 2026-11-17): a search found no production Navidrome call outside the shared client; the one remaining path, a caller's own `client_factory` client in `integrations/navidrome/client.py`, now sends the same `navidrome` label (`tests/test_navidrome_client.py`). The album review outlets' hosts count together as `reviews`.
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
- **Current state:** script and tests merged in PR #1143 (squash `05963eda`, 2026-11-16). Tested against a stub HTTP server, and run once against a local test instance (see the evidence log). The live runs are not warm-cache, so no baseline is recorded yet. Blocker found 2026-11-16 (read from code, see the evidence log): the artist and album pages never cache their similar-artist records while MusicBrainz tag lookups are refused at the gate, so those two routes call ListenBrainz (and Last.fm) on every request and cannot be measured warm. The owner approved the fix the same day (PR #1144, merged, squash `1c3d0af4`): the records are now cached when every provider answered, even if tag lookups were refused, and `docs/SEARCH_CONTRACT.md` says so. The warm baseline is recorded in the evidence log (2026-11-16, below). The knowledge routes have a real baseline from the owner's ingested store (2026-11-17, evidence log): on that store the owned album resolves as `type=release`, and both knowledge routes return 200 with data. The full seven-route table is recorded in the 2026-11-17 entry: all routes 200, with the artist page's ListenBrainz popularity call per request (F13) still present.
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
- **Current state:** done. Appendix A (survey at `cc14fb51`, 2026-11-17) holds the table; W2, W3 and K1 reference it.
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
- **Current state:** F5. **Merged in PR #1150 (squash `713c0949`, head `324001de`, 2026-11-17 00:23 UTC); not deployed.** `SettingsPersistence` keeps one long-lived read connection (`check_same_thread=False`, autocommit, every SELECT fully fetched so no SHARED lock stays held) under an `RLock`, and re-reads only when `PRAGMA data_version` changes or after a local `write()`. `initialize()` (table and `chmod 0600`) runs once per file and process: the read connection is reopened, and `initialize()` re-run, when the file's device/inode or the process id changes, so a replaced or deleted file is never shadowed. Writes keep their own short connection, so a multi-key write stays one commit. The legacy migrations run on reload only. Deviation from the guidance below: `read()` returns a deep copy, not a shallow one, because the dict holds lists such as `quality_priority`. Evidence: `tests/test_settings_persistence.py` (16 tests: ten unchanged reads run one SELECT; a commit from another connection and from a second instance is seen on the next read; a password change through `AuthSettingsReader` takes effect on the next read; a local write invalidates; nested mutation does not leak; the slskd migration does not deadlock; replaced and deleted files reopen; `initialize()` runs once). Local timing on a temp DB with 40 saved keys, 2,000 reads: median 313 µs before, 43 µs after. Limitations: M2 cannot show this, because its store counters hook only `intelligence/store/db.py`, not the settings file. `DISCOVERY_DB` also holds lists, genre blocks and other tables, so any commit to that file invalidates the cache. That is correct, but it lowers the hit rate in production; not measured.
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
- **Current state:** F6. **Merged in PR #1151 (squash `594b5ae2`, head `d1a8042a`, 2026-11-17 00:32 UTC); not deployed.** CI: `validate-container` passed at merge; the other four checks were still pending, so check them on `d1a8042a`. `integrations/navidrome/client.py`: `api_call` and `cover_art` share one lazily built `httpx.Client` (timeout 30 s, `follow_redirects=False`, up to 10 idle keep-alive connections kept 30 s; only keep-alive connections are capped). A caller-supplied `client_factory` keeps the per-call client. Evidence: `tests/test_navidrome_client.py` (`SharedNavidromeClientTests`; 26 OK with `test_navidrome_cover_art`), including a real loopback test that one TCP connection serves two calls. Loopback micro-timing, 300 calls per round, one threaded server: median 6.21 ms before, 0.46 ms after; 300 connections before, 1 after. M2 was not run, so the acceptance criterion is not yet shown: measure the artist page and `knowledge_paths_album_gaps` (the routes that call Navidrome) when M2 is next run. Limitations: a shared client keeps a cookie jar (per-call clients did not send cookies back; Navidrome uses token parameters); a request racing a Navidrome restart can fail once; the LAN gain is not measured.
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
- **Current state:** F7. **Merged in PR #1152 (squash `1cd9fb6e`, head `fa12f1ca`, 2026-11-17 00:43 UTC); not deployed. CI at merge was pending; check it on `1cd9fb6e`.** `metadata_cache.py` keeps one connection per thread (`threading.local`). It creates the table and the new `cached_at` index once per process, under a lock and keyed by the pid and the file's inode, and runs the file in WAL mode with `synchronous = NORMAL`. Each SELECT is read fully, so no read snapshot stays open. When the file is replaced or deleted, the next call notices the new inode, reconnects and recreates the table. `prune(older_than_seconds, batch=500)` deletes in committed batches and returns the count. The worker runs it once a day with `PRUNE_AFTER_SECONDS` = 400 days, which is longer than the longest TTL in use (365 days, `app/api/metadata.py::_YEAR_STORE_TTL`; a test pins it). The worker's daily step is `_daily_maintenance`, which isolates the job-history prune from the cache prune; a failure in either is logged by exception type only. `get` and `set` keep their signatures and the rule that any storage failure is a miss. Tests: `tests/test_metadata_cache.py` (4, unchanged); `tests/test_metadata_cache_lifecycle.py` (9: one `CREATE TABLE` per process across threads, checked with a trace callback; one connection per thread; WAL mode and the index present; prune keeps fresh rows and removes old ones, in batches; `set` is non-fatal while another connection holds the write lock; a garbage file is a miss and the cache recovers; a deleted file is recreated; the cutoff exceeds 365 days); `tests/test_worker_metadata_prune.py` (4); `tests/test_metadata_persistent_cache.py` (10, unchanged); `tests/test_worker_lock.py` and `tests/test_worker_shutdown.py` (unchanged, pass). Local micro-timing on a temp DB (200 rows; 2,000 reads and 2,000 writes; median): `get` 130 µs before, 12 µs after; `set` 533 µs before, 40 µs after. M2 cannot show this, because its counters do not cover this file. Limitations: the file does not shrink after a prune. SQLite reuses the freed pages, and VACUUM would lock the file for a long time, so 'stops growing' is by design and was not measured on a production-size file. The index is built on the first operation after the new code starts, which takes time on a large existing file. WAL adds `-wal` and `-shm` files next to the cache, so backups must use the SQLite backup API; no backup script copies this file today, and the planned S-phase backup uses that API.
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
- **Current state:** F8. **Merged in PR #1153 (squash `a05e802e`, head `2ba8438f`, merged 2026-11-17 01:13 UTC); not deployed. CI at merge: all six checks on `2ba8438f` were pending; check them on `a05e802e`.** `app/services/layered_cache.py`: `LayeredCache(namespace, max_entries=2000)` keeps an `OrderedDict` LRU with a per-entry expiry, reads `persistent_metadata` when given a `store_key` (with the caller's read TTL and an `accept_stored` check), and runs `load()` under single-flight: callers arriving while a load runs wait for it and get the same answer or exception, so even an uncached provider failure is shared; a waiter stops waiting after 30 s and asks on its own. `load()` returns `Loaded(value, memory_ttl, persist)`, so each route keeps its own rules. The signature differs from the guidance below (`found_ttl`/`miss_ttl` did not fit: details, links, descriptions and reviews have three outcomes). All eight dicts in `app/api/metadata.py` now are `LayeredCache` instances, migrated one commit each with keys, store keys, TTLs, negative TTLs, the partial-review TTL and the not-cached cases unchanged; `artist_bio_route` still puts the Navidrome bio in memory only (`put`). Evidence: `tests/test_metadata_cache_semantics.py` (17 tests; 16 written and passing against the old dicts first, then unchanged against the helper; plus one route test: two concurrent identical `artist_image` requests make one provider call), `tests/test_layered_cache.py` (11: bound and LRU order, default bound 2,000, per-answer TTL, not-cached answers, exceptions not cached and shared with waiters, store read and write, rejected stored value, single-flight, stuck-leader fallback), and the existing metadata route tests. M2 was not run; this step bounds memory and removes duplicate concurrent calls, and changes no warm-path timing by design. Limitations: expired entries are removed when read or evicted, not swept; the bound is per namespace (8 × 2,000 entries). At the owner's request P4 also bounds `integrations/musicbrainz/album_year.py::year_cache`, which `app/api/metadata.py` imports as `_musicbrainz_year_cache` and which never removed an entry: it is now a small LRU dict of at most 2,000 pairs (`YEAR_CACHE_MAX_ENTRIES`). It is not a `LayeredCache`, because `integrations/` does not import `app/`. Lookups, TTLs (180 days found, 6 h none), the gate and the not-cached refusal are unchanged; found years are also in the persistent store through the routes, so an evicted pair is read back from there. Tests: `tests/test_musicbrainz_album_year.py` (3 new: the bound, LRU order, an evicted pair is asked again; 14 OK). After P4 no module-level cache dict is left in `app/api/metadata.py` or in that import.
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
- **Current state:** F9, F10. **Merged in PR #1154 (squash `4e31c325`, head `76d92a74`, merged 2026-11-17 01:22 UTC); not deployed. CI at merge: all six checks on `76d92a74` were pending; check them on `4e31c325`. With P5, every Phase P step is merged.** (a) `discovery/library_snapshot.py::AlbumInventorySnapshot` keeps the raw inventory per process, keyed by the `getScanStatus` marker (`lastScan`, `count`); within 30 s of the last check it makes no call, after that one `getScanStatus` call keeps the copy when the marker is unchanged and no scan runs. Freshness choice: `album_gaps` reads `playCount`, `played`, `starred` and `userRating`, which change without a scan, so the copy also has a 5-minute maximum age. Failures, a running scan and an unreadable marker are not cached; callers get copies. Only `app/api/knowledge.py::_play_records` uses it: the other callers (insights gems every 6 h and the auto-fill daily safety net, both in the worker; the lens refresh and candidate gathering) read far less often than every 5 minutes, so a cached copy would not be reused, and the daily safety net must read Navidrome itself. The owned search index is unchanged. (b) Decision: `_ingest_step` stays. Its coverage is not a subset of auto fill's: auto fill's first run records the existing library as its baseline without ingesting it, and re-ingests a seen album only when it gains a release MBID; `_ingest_step` records those older albums and re-records each MBID artist's albums every 7 days, which picks up later tag edits (track MBIDs, ISRCs). It is already bounded (40 artists per 6-hour refresh, only while a provider lens is on); the reason is in its docstring. (c) `app/services/library_enrich.py::find_artist_id` takes the artist entity's Navidrome id from the store, confirms it with one `getArtist` call, and falls back to the full `getArtists` index on a miss, a changed id or a Navidrome error. Tests: `tests/test_album_inventory_snapshot.py` (10), the new route test in `tests/test_api_knowledge_paths_route.py` (two gaps requests make one `getScanStatus` and one inventory read), `tests/test_library_enrich_find_artist.py` (5). M2 was not run.
- **Proposed changes:** (a) `discovery/library_snapshot.py`: a process-level cached album inventory keyed by the Navidrome scan marker (`getScanStatus` `lastScan` and `count`), revalidated at most every 30 s; use it in `app/api/knowledge.py::_play_records` first, then the other callers. (b) Investigate, then decide in the PR: is `_ingest_step` still needed now that auto fill ingests new albums and reads a full inventory daily? If its coverage is a subset, remove it; if it covers albums auto fill skips, state which and keep it bounded. (c) Replace `find_artist`'s full index read with a store lookup by MBID where the entity already carries a Navidrome id.
- **Affected components:** `discovery/library_snapshot.py`, `app/api/knowledge.py`, `app/services/insights_refresh.py`, `app/services/library_enrich.py`, `intelligence/musicbrainz/auto_fill.py` (read only).
- **Implementation guidance:** play counts and stars change without a scan. For `album_gaps`, which needs play data, either keep a short maximum age (for example 5 minutes) on the snapshot or confirm the fields used are scan-stable; state which in the PR. Apply the same question to the owned search index before changing its 10-minute TTL; do not change the index in this step.
- **Dependencies:** P2 helps but is not required.
- **Risks:** stale play data on the gaps page; losing ingest coverage for albums without an MBID.
- **Verification:** request-count test (two `album_gaps` requests cause one inventory read); ingest equivalence test on a fixture library before removing `_ingest_step`.
- **Acceptance criteria:** repeated `album_gaps` requests within the maximum age make at most one `getScanStatus` call each and no inventory paging; one documented ingest path, or a written reason for two.
- **Model:** Sonnet, Medium. Needs judgement on equivalence and data freshness.

#### P6. Cache empty ListenBrainz popularity answers

- **Objective:** stop the artist page from re-sending release groups that ListenBrainz has no listen data for.
- **Current state:** F13 fixed. Before the fix the warm artist page made one ListenBrainz popularity POST per request (M2 live run, 2026-11-16); the album page made none when warm. **Merged in PR #1148 (squash `4860a3e7`, head `cc8be999`, 2026-11-16 23:59 UTC).** Live check: 0 ListenBrainz calls per request in 20 measured runs after the warm-up wrote the negatives (see the 2026-11-17 entry in section 13). Details: a 200 answer that leaves a release group without counts writes `{"negative": true, "at": <time>}` under the same key; the read side skips a fresh one for 1 h (`NEGATIVE_TTL_SECONDS`) and re-requests it after. Failed requests and malformed bodies write nothing. Tests: `tests/test_listenbrainz_popularity.py` (7 passed), `tests/test_recommend_new_music_characterization.py` and `tests/test_api_search_routes.py` (67 passed). Live check (2026-11-17, owner-approved provider traffic, local test instance on port 8090 with the P6 code loaded; `scripts/efficiency_baseline.py`, one unreported warm-up pass of 2 runs, then 20 measured runs, artist `beatles`): the warm-up pass made one ListenBrainz popularity POST on the artist page and wrote the negative entries; the 20 measured runs made 0 ListenBrainz calls (artist page 53 ms median, 76 ms p95, Navidrome 1 call per run). Output: `local-test/baseline-f13-after.json`. Before-change number for the same artist was not measured; the before reference is the 2026-11-17 entry (one POST per request on the earlier artist). Limitation: this artist had few uncached groups (4 negative rows in the cache after the warm-up); the knowledge routes 404 on this instance (small store). The copied owner-store instance on port 8091 had no library snapshot, so it could not run the artist page.
- **Proposed changes:** in `integrations/listenbrainz/popularity.py::fetch_release_group_popularity`, when a chunk answers 200 and a release group comes back with no counts (or is missing from the answer), write a short-lived negative entry under the same prefix (for example `{"negative": true, "at": <time>}`), with a one-hour TTL, the same as the negative TTL in `discovery/search/cache.py`. The read side treats a fresh negative entry as "no popularity" and skips it; a positive entry keeps its 30-day TTL. Do not cache a non-200 response or an exception as negative: those are failures, not "no data". The bonus formula and the `found` shape stay unchanged.
- **Affected components:** `integrations/listenbrainz/popularity.py`, its tests, and `docs/SEARCH_CONTRACT.md` if the contract states the caching rule (check before editing).
- **Implementation guidance:** keep the single batched POST per request for the groups that are not cached; keep the existing pacing and budgets. The cache write uses the existing `cache_set` callable, so no new storage.
- **Dependencies:** none. Independent of P1 to P5.
- **Risks:** a group that ListenBrainz gains data for stays "no data" for up to an hour; a failed response must not be stored as negative.
- **Verification:** unit tests: a group with no counts is not re-sent within the TTL; a group with counts is cached positive; a 500 response writes nothing; a group becomes positive after the negative entry expires. Then a live warm run with `scripts/efficiency_baseline.py` on the same targets: ListenBrainz per request should drop from 1.0 to 0 once the negative entries exist.
- **Acceptance criteria:** the warm artist page makes no ListenBrainz popularity call once the negative entries exist; the failure cases above write nothing; the PR quotes before and after from the baseline script.
- **Model:** Haiku, Medium. Small change to one module with a fixed spec; check the contract wording first.

### Phase W: finish the worker split

#### W1. Table-driven scheduler

- **Objective:** one place that decides what runs when, surviving restarts.
- **Current state:** done, merged in PR #1155 (2026-11-17), squash `87afd87e`, head `21b4805d`; CI was pending at merge. Not deployed. `app/worker_schedule.py` runs `daily_maintenance` (daily, local date) and `insights_refresh` (`CHECK_SECONDS`, lens on) in that order on one thread, persisting `schedule:<name>`; the insights entry falls back to R5's `insights_refresh.last_run_at`. Changes from before: daily maintenance now runs at the first start and then once per local day, instead of only after 24 h of uptime; an insights refresh that raises is recorded and waits its 6 h window, instead of retrying after an unrecorded 6 h wait. Before: each loop had its own thread, sleep and in-memory or ad hoc "done" state (F11).
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
- **Process-local state:** Appendix A rows for `start_similar_precompute` and the owned index.
- **Current state:** done, merged in PR #1156 (2026-11-17), squash `3e518379`, head `39d38d78`; CI was pending at merge. Not deployed. `app/services/similar_precompute.py` is the scheduler's `similar_precompute` entry (daily, last in the table, `retry_seconds` 1800): it builds its own owned index for the run (snapshot lists, song inventory, stored identities; no identity pass) and drops it afterwards, then runs `run_precompute` from the unchanged `similar-precompute-cursor` with the worker's stop event. A library that cannot be read returns `worker_schedule.NOT_READY`, which is not recorded and is retried after 30 minutes, as the old loop did. Web startup only warms its owned index once. The worker compose service gains `LASTFM_API_KEY`, since the Last.fm key's default comes from the environment. Changes from before: the done day is persisted, so a restart no longer repeats the day's run; the first worker start after upgrade runs it at once; the insights refresh can wait behind a long run (the W1 risk); a shutdown cancels the run and the cursor resumes at the artist it cut short. Limitation: Last.fm, ListenBrainz and Discogs pace through the in-process `SourceLimiter`, so during a run that the owner browses through, the worker and web each pace separately (MusicBrainz stays on the shared gate). Before: started from web startup; daily flag in memory; depended on the web's process-local owned index.
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
- **Process-local state:** Appendix A rows for the lens and scheduler threads and the `_DISCOVERY_*` guards, and finding A5.4 (resolved: acquisition guard, no move needed).
- **Current state:** merged in PR #1160 (2026-11-17), squash `c817f703`, head `a007e174`; CI was pending at merge. Not deployed; the 48-hour cadence check is not done. `app/services/discovery_schedule.py` holds two worker scheduler entries, `discovery_lists` (one pass of the old hourly loop: `refresh_stale_lists` over the five lists, none while `automatic_refill_enabled` is off, each through `_discovery_scheduler_refresh_one`, so Personal keeps `origin="scheduler"`) and `lens_lists` (`lens_service._due`, then the refresh), both `interval(3600)`, on a second scheduler thread `worker-schedule-discovery` so the 6 h similar-artist precompute cannot delay the 04:00 lens rollover. `discovery/refresh_guard.py` wraps every list refresh (scheduled, manual, manual "all" and the read-triggered Personal rebuild) in `run_job`, job `discovery_list_refresh`, scope = list name (`lens_lists` for the lenses). A busy list gets the caller's existing busy answer (`already_running`; manual non-personal refreshes still answer `started` at once). The refresh's own error is re-raised and the run stores only its type. While a refresh runs, a heartbeat moves its `started_at` forward every 60 s, so `recover_stale` (taste refresh, paths warm: no job filter, 15 min) never hands a live run to the other process; for these rows `started_at` is the last time the run was seen alive. A run its process left `running` is failed at that process's next start (rows carry `process`) or once its heartbeat is 15 min old; with no usable store the refresh runs under its in-process lock only. `app/main.py` keeps `library_resync.install()`, the Discogs generation bump and the one-shot owned-index warm-up (W2); `_start_discovery_background` and its 10 s timer are gone. `docs/DEPLOYMENT.md` states that lists do not refresh while the worker is down. The worker compose service needs no new variable: the settings defaults it reads (Navidrome, Last.fm key, ListenBrainz user) are already there; `LASTFM_USERNAME` and `LISTENBRAINZ_TOKEN` are environment fallbacks neither service passes. Changes from before: the first worker start after upgrade checks both entries at once; a restart inside the hour no longer re-checks at once (the last check is persisted); the two passes run one after the other on one thread instead of on two threads. Limitations: the listening profile refresh is scheduler-only and not guarded; a dead run's heartbeat stops, so `recover_stale` may requeue it before the guard fails it (the next caller then resumes that row, which is harmless); the 48-hour cadence run is not done. Before: both loops started from web startup; manual refreshes were excluded only by process-local locks.
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
- **Process-local state:** Appendix A2 rows for the metadata caches, `_EXTERNAL_HTTP` and the provider gate.
- **Current state:** done (2026-11-17). One owner-approved scripted session; the table and the K2/K3 decision are in "K1 results" below. Script: `scripts/efficiency_inventory.py`. Rerun on an aged copy of the live cache the same day ("K1 rerun on an aged cache"): expiry is 29% of first-view misses on owned pages, so K2's gate is met.
- **Proposed changes:** using M1 and M2 output, add a table to this document: route, providers called, cache hit rate, median and p95 provider wait, miss causes.
- **Affected components:** documentation.
- **Implementation guidance:** one week of real use by the owner, or a scripted session over 50 owned and 20 unowned entities with the owner's approval for the traffic.
- **Dependencies:** M1, M2, P4.
- **Risks:** none.
- **Verification:** numbers trace to recorded output files.
- **Acceptance criteria:** the table exists and K2 and K3 are confirmed, narrowed or cancelled in writing.
- **Model:** Sonnet, Low. Analysis and a decision, little code.

##### K1 results (2026-11-17)

**Setup.** One scripted session, approved by the owner, on the local instance at port 8091 serving the copied ingested store (`local-test/data-mb`, outside the repo). The script is `scripts/efficiency_inventory.py`. There were 70 targets: 25 owned artists, 25 owned albums, 10 unowned artists and 10 unowned albums. Each target had every route its page uses requested once cold, then 5 warm passes. Requests were strictly sequential, and each request's provider calls were read from `/api/diagnostics/runtime` before and after it. Cache rows were read (read-only) to class each miss. The 60 s quiet window before the session and the 30 s one after it showed 0 background provider calls. The session made 1,135 provider requests (cap 1,500, not reached):

| Provider | Requests |
|---|---|
| review outlets | 475 |
| Deezer | 259 |
| MusicBrainz | 121 |
| Apple | 116 |
| ListenBrainz | 83 |
| Wikipedia | 58 |
| Wikidata | 15 |
| Qobuz | 8 |

Raw output: `local-test/k1-session.json` and `k1-offline-ttl.json` (outside the repo).

**Totals.**

| Phase | Requests | With a provider call | Provider requests |
|---|---|---|---|
| Cold (pass 0) | 230 | 184 | 682 |
| Warm (passes 1 to 5) | 1,150 | 203 (18%) | 453 |

Warm passes 1 to 5 made 30, 166, 66, 33 and 158 provider requests, so the warm path did not settle to zero.

**Per route.** "Prov/req" is provider requests per request. "Hit" is the share of requests that made no provider call. Times are medians, with p95 in brackets.

| Target / route | Cold prov/req | Cold wall ms | Warm prov/req | Warm hit | Warm wall ms | Warm gate wait p95 s | Warm miss causes |
|---|---|---|---|---|---|---|---|
| owned album / album page | 5.2 | 3,749 (8,017) | 0.47 | 0.70 | 118 (6,254) | 12.3 | not cached 24, never fetched 10, failure 3, expired 1 |
| owned album / album links | 1.92 | 132 (3,851) | 0.67 | 0.62 | 3 (343) | 0 | not cached 44, failure 4 |
| owned album / album reviews | 8.12 | 4,159 (4,427) | 1.28 | 0.62 | 2 (4,252) | 0 | failure 37 (outlet timeouts), never fetched 11 |
| owned artist / artist page | 2.48 | 2,432 (4,837) | 0.18 | 0.94 | 27 (4,538) | 13.1 | never fetched 6, failure 2 |
| owned artist / artist image | 1.0 | 198 (366) | 0 | 1.0 | 2 (4) | n/a | none |
| owned artist / artist bio | 0 | 23 (94) | 0 | 1.0 | 2 (3) | n/a | none |
| unowned album / album page | 7.1 | 3,954 (8,020) | 0.60 | 0.48 | 116 (7,414) | 7.6 | not cached 23, never fetched 3 |
| unowned album / album reviews | 8.1 | 4,140 (4,244) | 0.72 | 0.78 | 2 (4,245) | 13.8 | failure 8, never fetched 3 |
| unowned album / album links | 1.6 | 141 (239) | 0.24 | 0.86 | 2 (273) | 2.0 | not cached 6, failure 1 |
| unowned album / album artwork | 1.6 | 136 (1,764) | 0.36 | 0.88 | 2 (2,156) | 0 | not cached 6 |
| unowned artist / artist page | 0 | 487 (1,208) | 0.52 | 0.84 | 494 (7,813) | 13.2 | never fetched 6, failure 2 |
| unowned artist / artist bio | 2.0 | 277 (918) | 0.12 | 0.94 | 2 (285) | 0 | never fetched 2, failure 1 |
| unowned artist / artist image | 1.0 | 215 (265) | 0 | 1.0 | 2 (4) | n/a | none |
| unowned album / album details | 0 | 2 (3) | 0 | 1.0 | 2 (4) | n/a | none |

Miss causes, from the cache rows each request wrote:
- **expired:** an existing row was rewritten.
- **never fetched:** a new row was created.
- **not cached:** the provider answered but nothing was stored.
- **failure:** a timeout or error, which is not stored by design.

**Warm misses by cause.** Across all routes there were 203 warm requests with a provider call:

| Cause | Requests |
|---|---|
| not cached | 103 |
| failure | 58 |
| never fetched | 41 |
| expired | 1 |

**Reading.**
1. **Expiry is not what makes warm pages wait in this session.** Only 1 of 203 warm misses was an expired row. This session cannot measure expiry fairly, though: every cache row was under one day old (`k1-offline-ttl.json`, max age 0.28 days), and the shortest TTLs in use are 1 to 7 days.
2. **Most warm provider calls are answers the routes deliberately do not keep.**
   - Album links and the album page re-ask Deezer and Apple when there is no match.
   - Album reviews re-ask review outlets that timed out: 141 of 160 warm outlet requests on owned albums were timeouts. Their provider time is 12 s median, while the route answers at its deadline (about 4.2 s at p95).
   - These are negative-caching gaps of the same kind as F13 and P6, not stale-while-revalidate cases.
3. **Never-fetched misses on warm passes are mostly MusicBrainz work refused at the gate on an earlier pass** (`rate_limited` outcomes; warm gate wait p95 12 to 14 s on the artist and album pages). The value is fetched on a later request.
4. **First views are slow.** Owned album page cold: 3.7 s median, 8.0 s p95, 5.2 provider requests. Owned artist page cold: 2.4 s median, 4.8 s p95.

**Decision.**
- **K2 (stale-while-revalidate): deferred, not cancelled.** This session gives no evidence for it (1 expired miss in 203), but it could not show expiry either, because the cache was hours old. Re-measure with `scripts/efficiency_inventory.py` on an instance whose cache is older than 7 days, or from a week of the owner's real use. Open K2 only if expired misses then become a material share of warm provider calls.
- **K3 (prefetch for owned entities): confirmed, narrowed.** Narrowed to the namespaces behind the owned album page and the owned artist page. Album reviews are left out until outlet failures are handled, because prefetch would only repeat timeouts. The plan lists K2 as a K3 dependency; this evidence does not support that, since prefetch fills the same keys whether or not K2 exists. The owner decides whether to drop the dependency. K3 still needs the owner's approval for its provider traffic.
- **New candidates (approved by the owner 2026-11-17 as K4 and K5, see below; not started):**
  - Short negative caching for review-outlet timeouts and errors (per outlet and album, for example 1 h, like P6).
  - Short negative caching for Deezer and Apple "no match" answers in album links and the album page.
  - Both follow the P6 pattern and would remove most of the 161 "not cached" and "failure" warm misses.

**Limitations.**
- One machine, one copied store, one session.
- The cache was hours old, so expiry is under-represented.
- Gate waits include refusals caused by the session's own earlier requests.
- The unowned artist page made 0 provider requests cold and 0.52 per request warm: its first data had probably been cached by the agent's earlier smoke run (`k1-smoke.json`). The warm calls are MusicBrainz and ListenBrainz work the gate had refused, as in point 3.
- Review-outlet timings are per outlet, summed within a request, so they exceed the route's wall time.

##### K1 rerun on an aged cache (2026-11-17)

**Why.** K1 could not measure expiry, because its cache was hours old. The rerun measures it on a copy of the live server's stores, where 69% of the 48,245 metadata-cache rows were older than 7 days. Of those, 32,297 were 7 to 30 days old and 605 were over 30 days.

**Setup.**
- The owner approved the copy and the provider traffic.
- The live stores were copied with SQLite's backup API inside the running container. The live files were only read, and the temporary copy was removed afterwards. The copy went to `local-test/data-live`, outside the repo; it holds credentials.
- The copy was served by `main` at `f8f0c191` on port 8092. Only the web process ran, without reload, with slskd unset and sandboxed music and download folders.
- There were 70 new targets with the same mix as K1: 25 owned albums, 25 owned artists, 10 unowned albums and 10 unowned artists. Each was picked from rows older than 7 days (album description, review source, details, artist bio, image). Ownership was checked against Navidrome.
- The run made one first-view pass and one repeat pass. K1's five repeat passes were not repeated, because the first view on an aged store is the new evidence. Quiet windows were 20 s before and after the session, and both showed 0 provider calls.
- The session made 537 provider requests (cap 1,000, not reached).
- Raw output: `local-test/k1r-session.json`. Targets: `local-test/k1r-targets.json`. Both are outside the repo.

**Totals, first view (pass 0, 230 requests each).** In the aged-store column, the in-memory caches are empty but the store holds the rows.

| | K1 fresh store, cold | Aged store, pass 0 | Aged store, pass 1 |
|---|---|---|---|
| Requests with a provider call | 184 | 139 | 19 |
| Provider requests | 682 | 498 | 39 |
| Expired misses (requests) | 0 | **41** | 3 |
| Never fetched | 140 | 50 | 5 |
| Not cached (answer not stored) | 31 | 37 | 9 |
| Failure | 13 | 11 | 2 |

**Expired misses on first view.**
- 41 of 139 requests with a provider call (29%) were expired misses, and so were 132 of 498 provider requests (27%).
- They took 77 s of the 319 s total wall time in pass 0.
- The rewritten rows had a median age of 9.2 days.

| Route (owned) | Expired requests (of 25) | Wall ms median (max) | Rewritten row age, median days |
|---|---|---|---|
| album reviews | 11 | 4,167 (4,233) | 7.3 |
| album links | 13 | 306 (406) | 11.7 |
| artist page | 12 | 456 (6,396) | 3.2 |
| album page | 5 | 2,031 (4,849) | 12.1 |

- Unowned routes had no expired misses. Their calls were never-fetched or not-cached answers, as in K1.
- Review rows expire after 7 days (`_REVIEWS_TTL`). An expired review list sends the route back to every outlet, and the route then answers at its deadline (about 4.2 s). That accounts for 46 s of the 77 s.
- The artist page's expired rows are 3.2 days old. They are MusicBrainz, ListenBrainz and Discogs entries with short TTLs, not metadata-route rows.

**Reading.**
1. On a week-old cache, expiry is a material share of the provider waits on first views of owned pages: 29% of requests with a provider call, 27% of provider requests and 24% of pass-0 wall time. In K1 it was 1 in 203.
2. The stored rows still help. On the album page, the aged store made 0.92 provider requests per request against K1's 5.2 on a fresh store, and the artist page made 0.96 against 2.48. The remaining wait is the expired rows.
3. Repeat views on the aged store are almost free: 19 of 230 requests had a provider call. So the cost of expiry falls on the first view after the TTL passes. That is the case stale-while-revalidate addresses.
4. The not-cached and failure misses from K1 remain: 48 requests in pass 0, mostly Deezer and Apple no-match answers. The two negative-cache candidates are still open.

**Decision.**
- **K2: the evidence gate is met. The owner opened K2 on 2026-11-17.**
- It is scoped to the namespaces with expired first views: album reviews (largest cost), album links, the album page's stored metadata, and the artist page's provider rows.
- **Maximum staleness for reviews: 70 days** (10 times the 7-day TTL), confirmed by the owner on 2026-11-17.
- The negative-cache candidates were approved the same day as K4 and K5.

**Limitations.**
- One copy of one store and one session, with one repeat pass.
- `expired` is a lower bound. An expiry-triggered re-fetch that then fails, or whose answer is not stored, is classed as `failure` or `not_cached`.
- The web process starts with empty in-memory caches, so pass 0 is a fresh process on an aged store. A long-running server may hold some values in memory past the store's rows.
- The live settings include a Discogs token, so Discogs calls appear (16 in pass 0). K1's copy made none.
- Targets were picked from aged rows, so they over-represent entities viewed more than a week ago. That is the population K2 targets.

#### K2. Stale-while-revalidate for metadata routes

- **Objective:** a page never waits on a provider when any earlier answer exists.
- **Current state:** an expired entry is a miss and the request waits for the provider. Evidence gate met by the K1 rerun (2026-11-17): 41 of 139 first-view misses on an aged cache were expired rows, mostly owned album reviews (about 4.2 s each), album links, the album page and the artist page. **Opened by the owner on 2026-11-17. Part 1 merged as PR #1166 (squash `624c9362`, 2026-11-17; not deployed, M2 acceptance not yet measured): album reviews (the list and each outlet's own answer), album links and the Apple album page address, all with a 70-day maximum staleness.** A timestamp match of the K1 rerun records against the rows they rewrote showed which keys expired: 13 album-links misses were the `apple-album-url` row (7-day TTL; the links themselves were incomplete and never stored), and every album-reviews miss was a set of outlet rows (`album-review-source`, a "no review" answer past its 3-day TTL), not the 7-day list row. So part 1 covers the outlet rows, which do not go through `LayeredCache`. **Part 2 merged as PR #1167 (squash `1fbb61c4`, 2026-11-17; not deployed, M2 acceptance not yet measured):** the artist and album pages' own provider rows. A timestamp match of the K1 rerun's 17 expired page misses against the stores showed that the rewritten rows were not metadata-cache rows behind `navidrome_server.py`'s `cache_get` callables (ListenBrainz popularity did not expire), but `search:*` rows in the discovery search cache (`navidrome_discovery.sqlite3`, read through `discovery/search/cache.py`): 12 ListenBrainz top recordings (artist page, 24 h TTL), 12 Last.fm album lists (album page, 24 h), 5 tracklists (7 days), and 8 empty Discogs-style or MusicBrainz-tag answers (1 h TTL, about 3.3 h old). Under the 10-times-TTL rule, per kind: all 8 empty answers (about 3.3 h old) and all 5 tracklists (8 to 15 days) would now be served at once, as would about 10 of the 12 ListenBrainz rows (under 10 days); most Last.fm album lists were 12 to 16 days old, past 10 times their 24 h TTL, and still wait as today. The counts are approximate: the recorded ages mix rewrites from both stores and cannot be tied to single rows. Part 2 serves such a row while one background refresh runs the same lookup (`read_or_revalidate`, own `refresh_budget` so the request's spent deadline cannot block the write) on a second pool (`stale_refresh.DISCOVERY_REFRESHER`), wired only into the page network (`artist_network_for`). Covered: the MusicBrainz artist lookup and studio albums, the seed artist's MusicBrainz tags and Discogs styles, Last.fm album lists, ListenBrainz and Last.fm top songs, tracklists. Not covered: similar-artist records (the worker precomputes them daily), candidates' tag lookups (served stale, a page could queue more lookups than it makes today), the search and genre pages, and the worker precompute. Maximum staleness follows the 10-times-TTL rule, confirmed by the owner for these rows on 2026-11-17: 10 days for 24 h rows, 70 days for tracklists, 300 days for tags and styles, 10 h for empty answers.
- **`fetched_at` (PR #1177, squash `a4804473`, merged 2026-11-17):** `LayeredCache` gains an opt-in `stale_fetched_at`. With it, a stale dict answer is a shallow copy carrying `fetched_at` (UTC ISO 8601, such as `2026-10-25T16:00:00Z`, the format the contracts use), the row's store time; the stored value and a fresh answer never carry it. `/api/album-reviews` and `/api/album-links` use it; a reviews list built from stale outlet answers states the oldest of them. A links set built with a stale Apple page address is not stamped (kept ten minutes, not stored). Additive key, documented in `docs/SEARCH_CONTRACT.md` (clients ignore unknown keys). The discovery search cache's stale page rows (artist and album page stream sections, `read_or_revalidate`) do not state it. Tests: `tests/test_stale_while_revalidate.py`.
- **Owner decisions (2026-11-17):**
  - Scope: album reviews, album links, the album page's stored metadata and the artist page's provider rows. Other namespaces keep today's expiry until evidence shows them.
  - Maximum staleness for album reviews: 70 days (10 times the 7-day TTL). Other namespaces use the plan's 10-times-TTL rule, unless a later decision changes it.
  - Provider traffic must not rise. Each background refresh goes through the gate, under today's pacing and budgets.
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
- **Current state:** **part 1 merged as PR #1168 (squash `7f86842b`, 2026-11-17), switched off; the owner approved the caps `musicbrainz=600,listenbrainz=300,lastfm=600` (Discogs off) the same day, and they take effect only when `OWNED_PREFETCH_BUDGETS` is set on a deployed worker (deployment paused). No live run or coverage measurement yet; the part 2 caps and the coverage target were set on 2026-11-17 (see "K3 part 2 caps and coverage target").** `app/services/owned_prefetch.py` (job) and `app/services/prefetch_state.py` (budgets, counting, cursor, coverage) are the worker's `owned_prefetch` entry, before `similar_precompute`. It builds each owned artist's and album's page network sections through the page routes' own builders (`artist_page`, `album_sections`) with a worker-built network, so it fills the same discovery search-cache rows and the same ListenBrainz popularity rows a first view would, under the same keys, with no second key builder. One artist and one album in turn; newest additions first (top 50), then by listens (an album has no listen count, so by its artist's; "recently played" is not in the owned index and is not used). The walk keeps a checkpoint after each entity, whatever its outcome, except that an entity cut short by a cap or by shutdown is tried again. **It does nothing unless `OWNED_PREFETCH_BUDGETS` names daily per-provider caps** (for example `musicbrainz=600,lastfm=600,listenbrainz=300`); a provider not named has a cap of zero and its request is refused before it is sent. MusicBrainz and ListenBrainz are used by both pages, so caps must name them, or those sections fail and each entity counts as partial. Last.fm and Discogs without a cap are switched off for the run (their sections say `source_disabled` and send nothing), even when a key or token is saved. A cap that is reached ends the run and the entity it cut short is tried again next day; a refusal for an unnamed provider only fails that source, and the walk moves on. The scheduler rule is false while no cap is set, so nothing is recorded and setting caps takes effect on the next tick. Spent counts are kept per local date in the knowledge store, so a restart does not reset them. Coverage (`artists`/`albums` total, next position, handled this run, outcome counts, caps, spent, why it stopped) is in `/api/diagnostics/runtime` under `prefetch`. Run limit one hour; one pass over each list per run at most. **Part 2 (merged as PR #1169, 2026-11-17; see "K3 part 2" below) now covers the album page's Deezer tracklist and Apple/Wikipedia description; the sentence that follows describes what part 1 left out.** **Not in part 1:** the Deezer, Apple and Wikipedia namespaces (album links, album details and tracklist, description, year, artist image), whose loaders and key builders are in `app/api/metadata.py`; the worker must not import a route module, so they need extracting into `app/services/` first. Until then those hooks are not given to the worker's network, so an album page prefetch leaves its Deezer tracklist, year and description sections for the first view. The "library tracklist first" in `discovery/search/album_page.py` was measured after part 2 and made permanent (see "K3 part 2 measured"). Album reviews stay out until K4, and the artist biography stays out (0 provider requests cold for owned artists in K1).
- **K3 part 2 (merged as PR #1169, squash `36b582dd`, 2026-11-17; not deployed, off):** `app/services/album_page_sources.py` now owns the Deezer album details and tracklist, Apple Music notes and page address, and Wikipedia lead loaders (HTTP `get` injected), their store keys (`album-details:v1`, `album-description:v1`, `apple-album-url:v1`), TTLs and the `Loaded` storing rule. `app/api/metadata.py` wraps them in `LayeredCache` with the same behaviour and shrinks by about 70 lines; the prefetch (`owned_prefetch.album_page_hooks`) uses the same functions with the metadata store's read and write, because the worker does not attach `persistent_metadata`. The new hooks need caps: `deezer` for the tracklist, `apple` and `wikipedia` (both) for the description; **the owner approved `deezer=600,apple=400,wikipedia=300` on 2026-11-17 (see "K3 part 2 caps and coverage target" below)**; nothing is added to `compose.yaml`. A refused or failed request is never stored: the worker stores a description only when found, and writes nothing when Apple's answer was lost to a failed request (the route keeps its older rule of storing a Wikipedia lead then). Also covered, each on its own caps: **album year** (the page's own year hook, asked only for albums with no library year; the MusicBrainz request is counted through the cap by `album_year.lookup_album_year_counted`, a failed or refused lookup stores nothing and skips the Deezer fallback, which needs a `deezer` cap), **album links** (caps `apple`, `deezer` and `musicbrainz`, or a set could never be complete; stored only when complete, under the key the clients build: the album page's artist, album and release-group id or empty) and the **artist image** (cap `deezer`, stored only when a photo is found). Not done: album reviews (K4) and the artist biography. Counting caveat: a cap counts the first request only; the Apple page fetch follows redirects uncounted. The temporary "library tracklist first" stays. `tests/test_album_page_sources.py` (25 tests) includes a parity test: the routes answer from what the prefetch stored with their HTTP client failing on any request. No live run.
- **Owner decision (2026-11-17): the proposed daily caps below are approved.** The coverage target was stated the same day (see "K3 part 2 caps and coverage target"). Original note: K1 measured cold costs of 5.2 provider requests for an owned album page and 2.5 for an owned artist page, of which part 1 covers only the MusicBrainz, ListenBrainz, Last.fm and Discogs share (the Deezer, Apple and Wikipedia share is part 2). K1 did not record the split per provider, and the owned library size is not in the repository, so days to full coverage is `(artists × 2.5 + albums × 5) ÷ daily cap` as an upper bound that the owner can compute from the library's counts. A starting proposal, to be adjusted: `musicbrainz=600,listenbrainz=300,lastfm=600`, Discogs left off (its saved token is then ignored by this job). The worker gets the value from `OWNED_PREFETCH_BUDGETS` in `compose.yaml`; empty means off. MusicBrainz is also paced by the shared gate (one slot per 1.1 s, so one hour never exceeds about 3,270), and the job's own caps count only its own requests: the auto fill, the insights refresh and the precompute keep their own budgets and share the gate. Request counts are taken from each request's URL host; Last.fm's API host (`ws.audioscrobbler.com`) is counted as `lastfm` here, although `runtime_metrics` still labels it `other` in diagnostics (labelling gap closed in PR #1173).
- **K3 part 2 caps and coverage target (owner decision 2026-11-17, on the recommendation below; merged as PR #1176 (squash `75c7728d`, head `bf5fd8b3`, merged 2026-11-17 12:55 UTC; CI pending at merge; not deployed)):**
  - **Caps:** `deezer=600,apple=400,wikipedia=300`, added to the part 1 caps. Full value: `OWNED_PREFETCH_BUDGETS=musicbrainz=600,listenbrainz=300,lastfm=600,deezer=600,apple=400,wikipedia=300` (Discogs still off). **At the owner's request this is the default in `compose.yaml`**, so the job runs on the next worker deployed from it; `OWNED_PREFETCH_BUDGETS=off` switches it off. Deployment is still paused.
  - **Inputs.** Library counts read from Navidrome on 2026-11-17: 705 artists, 1,739 albums. Cold provider requests per owned entity, measured in K1 (pass 0, 25 owned artists and 25 owned albums; album reviews excluded, they are not prefetched): artist: ListenBrainz 2.0, Deezer 1.0, MusicBrainz 0.32; album: Deezer 2.64, Apple 2.0, Wikipedia 1.16, ListenBrainz 0.68, MusicBrainz 0.64. The K1 copy made no Last.fm or Discogs requests.
  - **Why these numbers.** A run stops when any one cap is reached (`Spend.exhausted`), so the new caps must not stop it before the approved ones do. ListenBrainz binds: the walk alternates artists and albums, and one artist plus one album costs about 2.7 ListenBrainz requests, so 300 allows about 110 of each a day. Artists are walked again once their list is done, and their 24 h ListenBrainz rows have expired by then, so that rate holds for the whole album pass. At 110 pairs a day the new providers need about 400 Deezer, 220 Apple and 130 Wikipedia requests; the caps give 1.5 to 2.3 times that. MusicBrainz needs about 105 a day of its 600, and the one-hour run (`RUN_SECONDS`) is not the limit: a cold pair took about 7 s of route time in K1, so about 480 pairs would fit.
  - **Provider limits.** Within one hour, 400 Apple requests is about 7 a minute, under the about 20 a minute Apple asks for its Search API; 600 Deezer requests is about 10 a minute, far under its 50 per 5 s; Wikipedia's 300 is negligible.
  - **Coverage target:** every owned artist and album handled at least once (one full pass of both lists) within **21 days** of switching the job on, and at least **90 %** of handled entities counted `complete` (not `partial` or `failed`). The newest 50 artists and 50 albums are covered on the first day. Estimate: albums are the longer list, 1,739 ÷ about 110 a day ≈ 16 days; artists finish in about 7. The 21 days leave a margin for days a run stops early. Measured by summing each run's `prefetch` coverage in `/api/diagnostics/runtime` (or the worker's daily "Owned prefetch finished" log line): `handled` per list and the `complete`, `partial` and `failed` counts. Days to coverage is the largest of each provider's demand ÷ its cap, not one total ÷ one cap.
  - **Limitations.** The per-entity costs come from 25 entities of each kind on one store copy. Part 2 also spends MusicBrainz requests (album year, album links) that K1's route costs include but that the part 1 caps were sized without; the 600 cap still leaves room. 24 h rows that expire during the pass are refetched on the next walk, and K2 serves them stale for up to 10 days meanwhile. Raising `listenbrainz` would shorten the pass; it is unchanged because the owner approved 300.
- **Album reviews (PR #1177, squash `a4804473`, merged 2026-11-17; off until the owner names a cap):** the outlets, their stored answers and the K4 failure marks moved from `app/api/metadata.py` to `app/services/album_review_sources.py` (HTTP `get` and store `read`/`write` injected), so the worker uses them without importing a route module. The route keeps its parallel asks, 6 s deadline and K2 stale serving. With a `reviews` cap in `OWNED_PREFETCH_BUDGETS` (the outlet hosts count as `reviews`), `owned_prefetch.entity_extras` asks each outlet that has no fresh stored answer for each owned album, one after another (4 s timeout each), and stores outlet answers and failure marks exactly as the route does. It never writes the list: the compose worker has no `GUARDIAN_API_KEY`, so its outlet set lacks the Guardian, and a stored list would hide a Guardian review on the route for up to 70 days. The route builds the list from the stored outlet answers without an outlet request (plus 1 to 3 Guardian requests on a first view when the web process has the key) and stores it itself. A cap refusal marks nothing and leaves the remaining outlets for the first view. The default caps do not name `reviews`, so nothing changes until the owner approves one. Cost per album: up to 11 requests cold (Pitchfork 1, each of five WordPress outlets 1 search plus 1 page when a post matches; the Guardian 1 to 3 more with a key), none while every outlet's answer is fresh (a review a month, "nothing there" three days). Because a run stops when any cap is reached, a `reviews` cap set too low ends the whole run early. **Artist biography:** stays out; K1 measured 0 provider requests for owned artists. Tests: `tests/test_album_review_sources.py` (parity: the route answers from what the prefetch stored without sending a request).
- **K3 part 2 measured: "library tracklist first" (2026-11-17, owner-approved provider traffic):**
  - **Setup.** Two `sqlite3` backup copies of `local-test/data-live` (the aged K1-rerun store), served by the PR #1177 head on ports 8095 (A, left cold) and 8096 (B). Targets: 24 owned albums with at least 4 songs and no stored provider tracklist, a seeded random pick of the 846 such albums (`local-test/k3m-targets.json`, outside the repo).
  - **Runs.** On B, the real `owned_prefetch.run_once` ran with the approved compose caps, limited to those 24 albums and no artists: 148 provider requests, 24 handled (2 `complete`, 22 `partial`). Then one first view of each album page as an event stream, sequentially, on A and on B, with each tracks section timed from the request start.
  - **Results.**

    | | A, no prefetch | B, after prefetch |
    |---|---|---|
    | Library tracks section, median / p95 | 17 / 19 ms | 17 / 24 ms |
    | Provider tracks section, median / p95 / max | 458 / 1,178 / 2,413 ms | 21 / 870 / 3,667 ms |
    | Albums whose provider tracks took over 100 ms | 24 of 24 | 4 of 24 |
    | Provider requests, 24 first views | 215 | 85 |

  - **Read.** After a prefetch, a provider tracklist arrives about 3 ms after the library's, so the early section adds nothing for those albums. It still matters in two cases:
    1. **Albums no provider has.** 4 of 24 (17 %) had no provider tracklist on either copy. No "no tracklist" answer is kept, so every view runs the race again. These views waited 357 to 3,667 ms, and up to 7 Last.fm requests each.
    2. **Not yet prefetched.** Until coverage is complete (about 16 to 21 days after the job starts), an owned album's provider tracks wait a median 458 ms and up to 2.4 s.
  - **Decision input.** The early section costs one local read (17 ms). **Recommendation: keep it, and make it permanent instead of temporary. The owner agreed on 2026-11-17; the label is dropped in PR #1177 (merged, `a4804473`; code comment, test docstring, `docs/SEARCH_CONTRACT.md`).** Removing it would leave about one owned album in six with an empty tracklist for up to the page deadline on every view.
  - **Other finding.** B's first views still made 65 Last.fm requests (A: 115), and a second worker pass over 6 of the albums made 28 more. The prefetch does not leave the album page's Last.fm work warm. The requests were not attributed to a section; the similar-artists section and candidates' lookups (outside K2's scope) are the likely source. 22 of 24 prefetched albums were counted `partial`, but a rerun showed no section cut short, so the cause of `partial` in the first run is not pinned down.
  - **Limitations.** One machine, one store copy, 24 albums, one first view each. Wikipedia, Apple and Deezer marks from the prefetch were under an hour old at pass B.
- **Not measured:** no live run on a deployed worker, no M2 scenario, no coverage percentage. Unit tests are offline and patch `httpx`.
- **Proposed changes (original text):** a scheduled, budgeted job that walks owned artists and albums in the order new additions, recently played, most played, rest, and fills the same cache keys the routes read.
- **Affected components:** new job module, scheduler entry, service functions extracted from `app/api/metadata.py`.
- **Implementation guidance:** only for namespaces K1 shows have a high first-view miss cost. Daily request budget per provider, recorded through the gate counter. Progress in job checkpoints; coverage counts in diagnostics.
- **Dependencies:** K1, K2, W1.
- **Risks:** provider traffic increase, which needs explicit owner approval; storage terms for text content (section 3, unverified).
- **Verification:** request-budget tests; resume tests.
- **Acceptance criteria:** stated coverage percentage of owned entities within a stated number of days, both set from K1.
- **Model:** Sonnet, Medium. Follows established job patterns.

#### K4. Negative cache for review-outlet failures

- **Objective:** a warm album-reviews request does not re-ask an outlet that just timed out or failed.
- **Current state:** **merged as PR #1170 (squash `9cdc3ba3`, head `3c6e1600`, 2026-11-17 11:54 UTC; not deployed; CI pending at merge).** `_ask_outlet` in `app/api/metadata.py` writes a dated failure mark (`app/services/negative_marks.py`) under its own key `album-review-source-failed:v1:{outlet}:{artist}:{album}` when the outlet raises, in the pool thread, so an outlet that fails after the 6 s route deadline is marked too; while the mark is under 1 h old (`_SOURCE_FAILURE_TTL`) the outlet is skipped by raising `OutletResting`, so the list stays partial (`retryable`, not stored). The outlet's answer key is never written for a failure; a success writes it as before. A K2 background refresh of an outlet's stale answer sends nothing while a mark lives (it stops at the same check). Tests: `tests/test_metadata_album_info_reviews.py` (5 new, 1 changed: a failed outlet is now asked again after its hour, not at once), `tests/test_negative_marks.py` (3). Warm pass: see "K4/K5 warm pass on the aged store" below (acceptance met). Before K4: a timeout or error was not stored, so every view re-asked the outlet. In K1, 141 of 160 warm outlet requests on owned albums were timeouts, and each such request waited until the route deadline (about 4.2 s).
- **Proposed changes:** remember a failure per outlet and album for a short time (for example 1 h), following the P6 pattern. While that entry is live, skip the outlet, and report the reviews as partial, as today.
- **Affected components:** `app/api/metadata.py` (album reviews), the review-outlet fetch code it calls, and their tests.
- **Implementation guidance:** keep the entry in memory or in the store with its own short TTL. Never cache a timeout as "no review". A later success replaces the entry.
- **Dependencies:** K1 (done). It is independent of K2.
- **Risks:** a review found later by an outlet that has recovered appears up to the TTL late.
- **Verification:**
  - A failed outlet is skipped within the TTL and asked again after it.
  - A success is unaffected.
  - Partial results are still marked partial.
- **Acceptance criteria:** on a K1-style warm pass, the failure misses on album reviews fall to near zero.
- **Model:** Haiku, Medium. Follows P6.

##### K4/K5 warm pass on the aged store (2026-11-17)

Owner-approved provider traffic. Two fresh copies of `local-test/data-live` (the K1-rerun store), served side by side by `main` (`0f83b7fe`, port 8093) and the PR head (port 8094), sharing one MusicBrainz gate file so pacing stayed at one slot per 1.1 s overall. Targets: the 35 album targets of `local-test/k1r-targets.json` (K4 and K5 touch only album routes). `scripts/efficiency_inventory.py`, one first-view pass and one warm pass, then each server restarted on its store and run again (the restart's first view is the case the stored marks are for). About 1,150 provider requests in all; quiet windows clean except for one background Deezer and one MusicBrainz call in the after-window of both. Raw output in the session scratchpad (not kept).

| Album routes, 35 targets | `main` | K4/K5 |
|---|---|---|
| First view after restart: requests with a provider call | 93 | 45 |
| First view after restart: provider requests | 231 | 80 |
| First view after restart: wall time | 205 s | 38 s |
| Review-outlet requests after restart (owned + unowned) | 81 | 0 |
| Album links, unowned, after restart: provider requests | 22 | 1 |
| Warm pass, album page "not cached" misses (with the year fix) | 8 | 0 |

- **K4 met:** after a restart no review outlet was asked (failure marks and stored answers), and album reviews took 0.1 s in all instead of 141 s.
- **K5:** the first measurement left 9 Deezer requests per warm pass on the unowned album page: the album year route's Deezer fallback, which never kept a "no year" answer. A third commit gives it its own mark (`deezer-year`); the rerun shows 0 on the warm pass.
- **Not removed (outside K5's no-match rule):** owned album links still ask Deezer after a restart (18 to 20 requests): Deezer *matched*, but Apple had no match, so the set is incomplete and never stored, and the found Deezer page is not kept on its own. Wikipedia "no article" on the album description (10 after a restart) is not a Deezer or Apple answer. Both are recorded as K6.

#### K5. Negative cache for Deezer and Apple no-match answers

- **Objective:** a warm request for album links or the album page does not re-ask Deezer or Apple for an album they have just said they do not have.
- **Current state:** **merged as PR #1170 (squash `9cdc3ba3`, head `3c6e1600`, 2026-11-17 11:54 UTC; not deployed; CI pending at merge).** `app/services/album_page_sources.py` writes a dated no-match mark under its own key `album-no-match:v1:{deezer|apple}:{artist}:{album}` for 1 h (`NO_MATCH_TTL`), only after a provider answer with no exact match: Deezer's album search (`fetch_album_details_remembered`, and the links' Deezer lookup, which sends the same query and matcher, so they share one mark) and Apple's album search (`apple_search_url_remembered`, used by `_apple_album_url_state` and so by the links and the description, and by the worker's `apple_page_url`). A failed or refused request, and a Deezer error body sent with status 200 (`deezer_albums` now raises on it, so album details also no longer keeps such an answer an hour as a no-match), write nothing. The route and the worker read and write the same marks. A links set without a match is still incomplete: kept 10 minutes in memory and never stored, so a no-match lasts its hour, not the links' week. `/api/artwork` is unchanged (its chain ends at Qobuz and keeps P4's 5-minute memory-only miss). Tests: `tests/test_album_page_sources.py` (10 new, 1 changed), `tests/test_metadata_persistent_cache.py` (1 changed: a definite Deezer miss now leaves the mark row only). Warm pass: see "K4/K5 warm pass on the aged store" (album page met after the year fix; album links met for no-match answers, a found Deezer link in an incomplete set is still re-asked). Before K5: a "no match" answer was not stored. In K1, it was most of the 103 "not cached" warm misses, and 37 in the rerun's first view.
- **Proposed changes:** store a definitive no-match per provider and album with a short TTL (for example 1 h), following the P6 pattern. Errors and timeouts are not definitive and are not stored.
- **Affected components:** `app/api/metadata.py` (album links, Apple album URL, album page artwork and links lookups) and their tests.
- **Implementation guidance:** tell a definitive no-match (a 200 with no match) apart from failures. Keep the existing store keys; add a negative marker, or a separate short-lived key.
- **Dependencies:** K1 (done). It is independent of K2.
- **Risks:** a newly listed album appears up to the TTL late.
- **Verification:**
  - A no-match is skipped within the TTL and asked again after it.
  - An error is not cached.
  - A match is unaffected.
- **Acceptance criteria:** on a K1-style warm pass, the "not cached" misses on album links and the album page fall to near zero.
- **Model:** Haiku, Medium. Follows P6.

#### K6. The two provider calls K4 and K5 left on the album routes

- **Objective:** a first view after a restart (or after the in-memory caches empty) of an album makes no Deezer or Wikipedia request for an answer the server already received within the hour.
- **Current state:** merged 2026-11-17 as PR #1171 (squash `f26b1e2f`); both changes are in, with unit tests; the restart pass (acceptance) has not been run. Recorded from the K4/K5 warm pass ("K4/K5 warm pass on the aged store", above). Two calls remain on the 35 album targets after a restart:
  1. **Album links, found Deezer page re-asked (18 to 20 requests, owned albums).** Deezer matched, but Apple had no match, so the links set is incomplete; an incomplete set is kept 10 minutes in memory and never stored, and the found Deezer page is not stored on its own. Each view after that asks Deezer again.
  2. **Album description, Wikipedia "no article" re-asked (10 requests, unowned albums).** When Apple has no notes and Wikipedia has no matching article, the empty description is kept a day in memory only; after a restart Wikipedia is asked again. Not a Deezer or Apple answer, so outside K5.
- **Proposed changes:** (1) store a found Deezer album page on its own (for example `album-deezer-url:v1`, the links' 7-day TTL, like the Apple page address) and read it in `load_album_links`, so an incomplete set costs only the services without a stored answer; the set's own storing rule (complete sets only) stays. (2) A 1 h Wikipedia no-article mark (`album-no-match:v1:wikipedia:*`) through `negative_marks`, written only when the search answered and `pick_album_article` found nothing; a failure writes nothing.
- **Affected components:** `app/services/album_page_sources.py`, `app/api/metadata.py` (album links, description), `owned_prefetch` (shares the loaders), their tests.
- **Dependencies:** K4 and K5 (merged).
- **Risks:** a stored Deezer page that Deezer later removes stays up to its TTL (same risk as the Apple page address today); a Wikipedia article written later appears up to an hour late.
- **Verification:** unit tests for each (found page stored and reused; no-article marked, skipped within the hour, asked after; failures write nothing); then the same side-by-side restart pass as K4/K5.
- **Acceptance criteria:** on that restart pass, album links and the album page make no Deezer or Wikipedia request for the albums the previous pass already answered.
- **Model:** Haiku, Medium. Follows K5.

### Phase S: store hygiene

#### S1. Size and growth report, then retention

- **Objective:** know what grows, then bound it.
- **Current state:** report part merged in PR #1159 (squash `3d24c072`): `scripts/store_size_report.py`, read-only, tested. First run on a copied owner store, 2026-11-17 (evidence log, section 13): `observations` is 1,487 rows and 8.1 MB of an 863 MB knowledge file; the slice tables (`edges`, `entities` and their indexes) are about 96%. Retention not started. On this evidence it is not needed yet; re-run the report on the live store after some weeks of use and open retention only if `observations` grows materially. Growth over time is still unmeasured (one snapshot).
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
- **Current state:** merged in PR #1158 (2026-11-17), squash `340a73b1`; not run against the live host. `scripts/backup_stores.py` copies the eight stores with the backup API into a 0700 directory with 0600 files; tests in `tests/test_backup_stores.py` cover a held write transaction, a concurrent writer, modes, skipped and corrupt stores, the store list against the code, and a state-file restore after a knowledge wipe.
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
- **Current state:** done, merged in PR #1157 (2026-11-17), squash `38b2e24e`; search results are in the PR body. `container-smoke` passed on the head.
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
- **Current state:** done. PR #1162 (squash `6ccb6bcd`) removed six unreferenced adapters (`library_overview`, `search_music`, `get_album_details`, `find_missing_mbids`, `_lastfm_cached_call`, `_discovery_settings_init`), two now-unused imports and two adapter-only tests; `navidrome_server.py` 2,382 to 2,285 lines. The reference table (119 top-level symbols, whole-word search across all tracked files) is in the PR body. Follow-up PR #1163 (squash `652e72f7`, owner-approved) removed the three payload helpers in `integrations/navidrome/client.py` that only those adapters used. **Rerun (2026-11-17):** PR #1172 (squash `0391e5e0`) rebuilt the table on `52b202d1` (170 symbols, imports included) and found no unreferenced adapter. It removed three unused imports and two unused locals. With the owner's approval, it also moved the 12 Navidrome, Last.fm, ListenBrainz and slskd settings wrappers into `app/api/settings.py` (the routes now call `settings/service.py` directly), replaced six one-line forwarders with the functions they called (four in acquisition, in a commit of their own), and folded three one-call helpers into their only caller. `navidrome_server.py` went from 2,285 to 2,123 lines. New wiring tests: `tests/test_legacy_server_wiring.py`. The adapters left either bind module helpers or locks, or have several callers; they are listed in ACTIVE_WORK 2n.
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
- **Current state:** done except memory limits. PR #1161 (squash `11798294`): `init: true` on both services; web healthcheck on the public `/api/auth/status` (Python `urllib` one-liner); worker healthcheck `python -m app.services.worker_heartbeat`, which fails when `DATA_DIR/worker.heartbeat` is missing or older than 300 s. A `worker-heartbeat` thread rewrites the stamp every 30 s only while both scheduler threads are alive, so a long precompute stays healthy and a dead scheduler turns the worker unhealthy. Interval 60 s, timeout 10 s, retries 5, start period 120 s. Not verified: `docker compose up` (no Docker on the dev machine) and `container-smoke`. `restart: unless-stopped` does not restart an unhealthy container; `docs/DEPLOYMENT.md` gives the manual restart. Memory limits stay open: M2 measured time and calls, not memory.
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

## Finishing Up

Every roadmap step is merged. This is the implementation work still left (as of 2026-11-17, after PRs #1173 to #1176). Tests, measurements and acceptance runs are not listed here; each step's own entry above tracks them.

### Needs an owner decision first

- **K3 `reviews` cap:** the album reviews prefetch is built and off. It runs only when `OWNED_PREFETCH_BUDGETS` names `reviews`. Two costs to weigh:
  - **Requests:** up to 11 per cold album. A cap that runs out first stops the whole run.
  - **Time:** in K1, 141 of 160 warm outlet requests on owned albums timed out (about 4 s each). The prefetch asks the outlets one after another, and a timeout leaves only a one-hour mark, so every pass pays it again. That can add 20 to 25 s per album. The one-hour run limit could then bind before ListenBrainz's 110 pairs a day, which would put the 21-day coverage target at risk.
  - The prefetch does not check the worker's stop event between outlets, so a shutdown can wait up to about 40 s.

  See K3, "Album reviews".

### Left out of merged steps

Done in PR [#1177](https://github.com/abucalip/navi-librarian/pull/1177) (squash `a4804473`, head `1c0ace77`, merged 2026-11-17 13:31 UTC; CI queued at merge; not deployed): "library tracklist first" measured and made permanent (owner decision, K3 "K3 part 2 measured"), the K3 album reviews prefetch (off until the cap above is set), K2 `fetched_at` on stale album reviews and links, and M1's `navidrome` label on calls made outside the shared client. The artist biography stays out of K3 (K1 measured 0 provider requests). Still open, each behind its own gate:

- **K2:** outside the owner's scope, and still expiring as before: similar-artist records, candidates' tag lookups, and the search and genre pages. Extend only when evidence shows them.
- **K2:** the artist and album page stream sections served stale from the discovery search cache do not state `fetched_at`.

### Waiting on evidence

- **S1 retention:** not started. Open it only if a later size report on the live store shows `observations` growing materially.
- **C3 memory limits:** wait for real memory numbers. M2 measured time and calls, not memory.
- **S3 slice refresh:** deferred until the owner wants a second MusicBrainz dump import.
- **Section 10:** each deferred item there opens only on its stated condition.

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

- 2026-11-17 (K3 part 2 measured, owner-approved provider traffic): see K3, "K3 part 2 measured". 24 cold owned albums on two copies of the aged store. With prefetch, provider tracks arrive in a median 21 ms instead of 458 ms, but 4 of 24 albums have no provider tracklist and still wait 0.36 to 3.7 s on every view. Recommendation: keep "library tracklist first" permanently. About 450 provider requests in all (215 in pass A, 148 for the prefetch, 85 in pass B), plus 45 in one diagnostic re-run of 6 albums.
- 2026-11-17 (finishing up the items left out of merged steps; merged as PR #1177, squash `a4804473`, head `1c0ace77`, 13:31 UTC; CI queued at merge; not deployed): (1) M1: no production Navidrome call outside the shared client was found; a caller's own `client_factory` client now sends the `navidrome` label too. (2) K2: stale album reviews and album links answers carry `fetched_at` (`LayeredCache` `stale_fetched_at`); fresh and stored values never do. (3) K3: album reviews prefetch through `app/services/album_review_sources.py`, gated on a new `reviews` cap that the default does not name (owner decision needed). Left as they were: the "library tracklist first" (waits on a measurement) and K2 scope (waits on evidence). Focused tests only; no live run, no provider traffic.
- 2026-11-17 (K3 part 2 caps and coverage target, owner decision on the recommendation; PR #1176 (squash `75c7728d`, head `bf5fd8b3`, merged 2026-11-17 12:55 UTC; CI pending at merge; not deployed)): caps `deezer=600,apple=400,wikipedia=300`; target every owned artist and album handled once within 21 days, at least 90 % complete. Inputs: Navidrome counts (705 artists, 1,739 albums) and K1's per-provider cold costs per owned entity. Default in `compose.yaml` (owner's request; `off` switches it off). Test `RecommendedCapsTests` in `tests/test_owned_prefetch.py`. Not deployed, no live run.
- 2026-11-17 (follow-ups that needed no owner decision): PR #1173 (M1 labels: `lastfm` for Last.fm's API host, `navidrome` for the shared Navidrome client), PR #1174 (auto fill stops mid-run on shutdown; also fixes two `WorkerTests` that had failed on `main` since W3), PR #1175 (A5.5 per-key lock entries dropped when unused). Focused tests only (50, 68 and 96 passed); CI pending at merge on heads `d9d020fd`, `60b53896`, `52c3a1e4`. Not deployed.
- 2026-11-17 (S1 first size report, read-only): `scripts/store_size_report.py --data-dir` on the owner's copied MusicBrainz test store (`~/discair-mb-test`, outside the repo; knowledge file last written 2026-11-07, so this is the post-slice-import state, not a running server). 4 s. The main file and `-wal` were unchanged afterwards. The `-shm` mtime changed, because a WAL reader records read marks there. Only `intelligence.sqlite3` and `intelligence.state.sqlite3` are present; the other six stores are missing in that folder. Knowledge file 862.5 MB (210,582 pages × 4 KiB), empty `-wal`. By bytes: `edges` 2,434,669 rows, 397.5 MB; index `edges_unique` 140.1 MB; `entities` 858,112 rows, 78.6 MB; indexes `edges_to` 62.5 MB, `edges_from` 62.2 MB, `entities_mbid` 47.6 MB, `entities_name` 39.4 MB; `observations` 1,487 rows, 8.1 MB; `entity_identifiers` 158,357 rows, 4.7 MB; everything else under 3 MB each; `job_runs` 7 rows, `source_state` 282 rows. State file 40 KB, all owner tables empty. Read: the slice's edges and entities, with their indexes, are about 96% of the file; `observations` is under 1%, so the observation-retention job is not justified by this snapshot. Limitations: one snapshot of a test copy, not the live server, so growth rate is unknown; the settings, metadata-cache, gate, radio, artwork and waveform stores were not measured. Raw JSON: scratchpad, outside the repo.
- 2026-11-17 (M2 full baseline, owner-approved provider traffic): the knowledge-route check above is now part of the full run. Instance: port 8091 on the copied ingested store (`local-test/data-mb`, outside the repo), `scripts/efficiency_baseline.py --runs 20 --knowledge-type release` after a 2-run warm-up whose output is not used. Targets: the owned album resolved by navidrome id (used for both the path and `?id=`; `key` from the library item is not the id, and passing it 404s), its artist by key, and the library artist id. Warm-up pass (not measured): artist page ListenBrainz 1.0 per request, knowledge connections 812 ms median, album gaps 1030 ms. Measured, 20 runs, every route 200:

  | Route | Count | Status | Wall median ms | Wall p95 ms | Server median ms | Server p95 ms | Outbound per run |
  |---|---|---|---|---|---|---|---|
  | library_artists | 20 | 200 | 4.5 | 5.4 | 4.0 | 4.0 | none |
  | library_albums | 20 | 200 | 6.2 | 6.4 | 5.0 | 5.0 | none |
  | artist_page | 20 | 200 | 421.2 | 473.8 | 419.5 | 473.0 | ListenBrainz 1.0, Navidrome 1.0 |
  | album_page | 20 | 200 | 24.4 | 28.2 | 23.0 | 27.0 | none |
  | search | 20 | 200 | 9.0 | 9.3 | 2.0 | 3.0 | none |
  | knowledge_connections | 20 | 200 | 177.6 | 178.6 | 176.0 | 178.0 | none |
  | knowledge_paths_album_gaps | 20 | 200 | 1048.4 | 1095.1 | 1047.0 | 1094.0 | Navidrome 4.0 |

Findings: (1) the artist page still makes one ListenBrainz popularity call per request on the warm path, which is finding F13 (empty popularity answers are not cached; `integrations/listenbrainz/popularity.py`). This is the next Phase P candidate (P6), and the baseline now shows it. (2) The album page is warm (no outbound calls, median 24 ms). (3) `knowledge_paths_album_gaps` is the slowest route at about 1 s, with 4 Navidrome calls per request, the same count as the earlier 404 path; the connections route is 178 ms with no outbound calls. (4) The earlier provider incident (artist page ListenBrainz 3 and MusicBrainz 5 in the one-run probe) happened on cold artist caches; the measured runs had no MusicBrainz traffic. Limitations: one machine, one artist, one album, one copied store; warm-up was one pass of two runs; results are indicative only. Raw output: scratch files outside the repo.
- 2026-11-17 (M2 knowledge-route baseline): the owner's ingested knowledge store (`intelligence.sqlite3`; MusicBrainz slice dump 2026-11-04, loaded 2026-11-07; about 858k entities, 2.4M edges, 993 owned releases with edges) was copied with `sqlite3 .backup` into `local-test/data-mb` (outside the repo) and served on a second local instance at port 8091, without reload. The owner's store was not opened by any server, and the 8090 instance and its small store were left as they were. On this store an owned album is typed `release`; with `type=release_group` both knowledge routes return 404. `scripts/efficiency_baseline.py` gains `--knowledge-type` (default still `release_group`), with a unit test. Knowledge-only measurement, 20 runs after one warm-up that was not measured, sizes and times only: `knowledge_connections` 200, wall median 177.7 ms, p95 178.6 ms, no outbound calls; `knowledge_paths_album_gaps` 200, wall median 992.6 ms, p95 1336.2 ms, Navidrome 4.0 requests per run (`other`), no provider calls. Read: the album-gaps route is the slowest knowledge route, and its four Navidrome calls per request are the first target for a Phase P fix. Incident, not approved: a one-run probe of the full script against port 8091 made provider calls on the artist page (ListenBrainz 3, MusicBrainz 5 requests in that run). The artist's caches in the copied store were cold, and the probe was run without checking warmth first. No further provider traffic was run. The artist-id lookup and the album key used in that probe also failed (artist route empty id; album route 404), so the artist and album pages are not measured here. Limitations: one development machine, one owned album, one copied store; the measured routes make no provider calls.
- 2026-11-16 (M2 per-route attribution merged): PR #1146, squash `a3b9eafe`, head `7cf3a403`, merged 23:14 UTC. M2 baseline criteria are met (committed table in the log, repeatable script, per-route attribution). Open: the knowledge routes still need a test album with ingested MusicBrainz data for a real baseline. P6 is proposed and not started.
- 2026-11-16 (M2 ListenBrainz warm call, confirmed by code read and by the test instance's cache tables; no code changed): the one warm ListenBrainz call per artist-page request is the release-group popularity POST (`integrations/listenbrainz/popularity.py`, `fetch_release_group_popularity`), sent by the artist page's popularity callable (`app/api/search.py::artist_network_for`). It sends every release group that has no `lb:popularity:release-group:{mbid}` row in `navidrome_metadata_cache.sqlite3` in one chunk (chunk size 50). The row is written only when ListenBrainz returns both listen and user counts, so a group that ListenBrainz knows nothing about is sent again on every request. For the cold test artist, 14 of its 28 release-group MBIDs had a row (all with counts) and 14 had none, which matches one POST per request. Ruled out, from the same tables: the similar-artist records (`similar:<mbid>:...` row written earlier and read on the warm path), and top-recordings (`search:listenbrainz:0:artist-top:<mbid>:top-recordings:depth50`, read back through `read_cached` with 10 records). The owner-approved fix would cache empty popularity answers for a short time (the same idea as the one-hour negative TTL that `discovery/search/cache.py` already uses for empty results), so the warm call stops; not implemented here. Limitation: the 14 uncached groups were not re-queried live to confirm ListenBrainz returns no counts for them; the row-and-code evidence is consistent with that, not a direct observation.
- 2026-11-16 (M2 cold and warm provider run, owner-approved provider traffic, local test instance port 8090, a second artist and album not used before): one cold pass, then 20 warm runs on the same targets. Cold pass, requests per route (web process): artist page ListenBrainz 3, MusicBrainz 1, Navidrome 2, wall 1967 ms; album page Apple 2, Deezer 1, MusicBrainz 2, Wikipedia 2, Navidrome 7, wall 3176 ms; library, search and knowledge routes 0 provider calls (knowledge `album_gaps` 404 path: Navidrome 4). Warm 20 runs, per request: artist page ListenBrainz 1.0 and Navidrome 1.0, wall median 417.6 ms, p95 512.3 ms; album page no outbound calls, wall median 26.0 ms, p95 27.7 ms; knowledge `album_gaps` 404 path Navidrome 4.0, wall median 403.8 ms. Finding: after one cold pass the artist page still calls ListenBrainz on every warm request, so its similar-artist or popularity records are not cached when a request is served (earlier finding 2 in this log, read from `integrations/listenbrainz/popularity.py`, is the likely cause; not yet confirmed in code or in a log line). The album page is fully cached when warm. Limitations: one machine, one new artist and one album; the knowledge routes still return 404 here (no ingested data). Raw output: scratch files outside the repo.
- 2026-11-16 (M2 per-route attribution, live run on the local test instance, port 8090, `main` code plus PR #1146 script): `scripts/efficiency_baseline.py --runs 20` after a 2-run warm-up. The warm-up was not warm: it made provider calls (the owner has since approved provider traffic for this run) (ListenBrainz 2, MusicBrainz 2 with one rate-limited, Apple 2, Deezer 2) on the artist and album pages, which the Phase M rule says needs owner approval; the owner supplied the test-instance login, and the measured 20 runs had no provider traffic. Attribution, per request, from the web-process `other` bucket (Navidrome LAN server): library artists 0; library albums 0; artist page 1.0; album page 0; search 0; knowledge connections 0; knowledge paths (`album_gaps`, 404 path) 4.0. Warm wall median and p95 ms: library artists 4.0 / 5.2; library albums 6.3 / 6.5; artist page 35.6 / 53.7; album page 25.4 / 29.2; search 9.2 / 9.5; knowledge connections 3.5 / 3.9 (404); knowledge paths 381.9 / 505.1 (404). Interpretation: the warm album page makes no Navidrome calls, so its earlier 410 ms median (run c606b124) was not Navidrome time; the remaining Navidrome calls are on the artist page (one per request) and the knowledge `album_gaps` path (four per request, the 404 path only, not the real route). Limitations: one development machine, one artist and one album; a 20-run run had a transient 404 on the album route while the server reloaded (the `--reload` watcher picks up edits under the checkout), so the run was repeated and the repeat is the one recorded. The 404s on the knowledge routes mean those numbers are not the real route. Raw output: scratch files outside the repo.
- 2026-11-16 (M2 per-route attribution): `scripts/efficiency_baseline.py` now runs each route as its own block with a runtime snapshot before and after it, and writes `per_route_runtime` to the JSON; the table gains an "Outbound per run" column (requests per run by provider; `other` is the Navidrome LAN server). Routes run one after another instead of interleaved, so a delta belongs to one route. `numeric_delta` now counts a key that appears only after the block from zero (before, a provider first seen during a route was dropped). Background web threads that call a provider during a block are still counted; a no-request window is the control if that matters. Tests: `tests/test_efficiency_baseline.py`, 9 passed (stub server; the stub counts app requests, not diagnostics reads). Lint: see PROJECT_LOG. No live run in this entry: it needs the owner's test password and an artist and album key, and it is warm-only. Next live step: run the script against the local instance and fill in the per-route column before choosing a Phase P fix.
- 2026-11-16 (M2 baseline blocker, read from code, not yet seen with a log line): the per-request ListenBrainz call on the album page (and on the artist page) comes from `similar_items` in `discovery/search/artist_sections.py`. It fetches Last.fm and ListenBrainz similar artists, then MusicBrainz tags for the seed and the top candidates (`_tags_for`). A refused gate reservation makes `_tags_for` report `rate_limited`, which sets `tags_hit_deadline`, and the fetched records are written only when `not tags_hit_deadline` (line 446). With 72 refused reservations against 5 granted per run, the records are never cached, so every request fetches them again. This also explains finding (3): the same tag lookups cause the refusals. The rule is deliberate (PR #622, P3b; `docs/SEARCH_CONTRACT.md` line 482: a partial fetch writes nothing, so the previous entry stays), and a regression test covers it. Owner-approved fix in PR #1144: cache the provider records when every provider fetch completed, even if tag lookups hit the gate, because tags are cached separately and the ranking is recomputed on every request; a failed provider still writes nothing. Tests: `test_discovery_search_similar.py`, `_similar_precompute.py`, `_artist_sections.py`, `_album_page.py`, `_genre.py` (137 passed); the two new cases fail without the fix. CI note: `tests/test_efficiency_baseline.py` from PR #1143 imported pytest, which the CI `unittest discover` run does not install, so `compile` and `test-and-build` failed on `05963eda` and `e09a4adc`; the file now uses unittest only.
- 2026-11-16 (M2 live run, PR #1143, not warm-cache): run against a fresh local test instance (port 8090, isolated `local-test/data`, owner account from the local config, library of 703 artists). Seven routes, 20 requests each, warm-up not done, so the runs are cold-to-warm mixed. Run E (`baseline-valid-E.json`, outside the repo): library artists 200, median 4.8 ms, p95 5.6 ms; library albums 200, 6.8 / 9.8 ms; artist page 200, 38.7 / 728 ms; album page 200, 2015 / 3355 ms; search 200, 12.8 / 18.8 ms; knowledge connections 404, 5.5 / 6.3 ms; knowledge paths (album gaps) 404, 391 / 448 ms. The two knowledge routes return 404 on this instance because no MusicBrainz data is ingested for the album, so they measure the not-found path, not the real route. Run G repeats the same pattern, so the numbers are stable across runs, but they are not a warm baseline. Not deployed; no provider traffic was intended beyond the approved cold run.
- 2026-11-16 (M2 findings, from per-route counter diffs on the same instance): (1) ListenBrainz: the album page makes one ListenBrainz request per request, every time; the cause is not yet pinned to a function (candidate: the similar-artists lookup in `discovery/search/artist_sections.py`, unverified). (2) Read-the-code, not seen live: `integrations/listenbrainz/popularity.py` caches only release groups that come back with counts; groups with no listen data are never cached, so each request posts them again. (3) MusicBrainz gate: about 185 s of wait per full run, with 70–80 refused reservations; the route that causes them is not yet attributed. (4) The `other` bucket in `runtime_metrics` is the Navidrome server on the LAN (not a provider); the counters should label it Navidrome. (5) Knowledge paths: five non-provider outbound calls per request, even on the 404 path.
- 2026-11-16 (M2 bug fixes in PR #1143, head `9cfb05de`): the artist route matches the normalized artist name and needs the artist id; the album route needs the `id` query parameter. Both fixed and tested (8 focused tests pass). Earlier runs with wrong parameters were discarded.
- 2026-11-16 (M2 warm baseline): run on `main` at `c606b124` (includes #1143 and #1144) against the local test instance on port 8090, restarted from that checkout. Warm-up: one pass of two runs first (the cold provider calls happened there, and its runtime delta showed no provider counters), then the measured run. Measured: `scripts/efficiency_baseline.py --runs 20`, output `local-test/baseline-warm-1.json` (outside the repo). Runtime delta across the 20-run measurement: ListenBrainz 0, MusicBrainz 0, Last.fm, Apple, Deezer and Wikipedia 0 requests; `other` (the Navidrome LAN server, not a provider) 120 requests, 17.5 s total wait, about 6 per run. MusicBrainz gate: 0 reservations and 0 refusals. Store: 41 read-only opens, 0 locked or slow.

  | Route | Count | Status | Wall median ms | Wall p95 ms | Server median ms | Server p95 ms |
  |---|---|---|---|---|---|---|
  | library_artists | 20 | 200 | 5.0 | 7.1 | 4.0 | 6.0 |
  | library_albums | 20 | 200 | 6.8 | 9.2 | 6.0 | 8.0 |
  | artist_page | 20 | 200 | 36.4 | 108.5 | 35.5 | 107.0 |
  | album_page | 20 | 200 | 410.3 | 1310.9 | 409.5 | 1310.0 |
  | search | 20 | 200 | 11.0 | 13.1 | 3.0 | 4.0 |
  | knowledge_connections | 20 | 404 | 4.8 | 5.0 | 4.0 | 4.0 |
  | knowledge_paths_album_gaps | 20 | 404 | 396.5 | 458.1 | 395.5 | 457.0 |

  Findings: (1) the ListenBrainz-per-request problem from the earlier cold runs is gone on the warm path. (2) The album page is still the slowest real route at a 410 ms median and 1.3 s p95 with no provider calls, so its time is Navidrome LAN calls and local work; the script does not attribute the 120 `other` requests per route, so a per-route counter is the next measurement. (3) The knowledge routes are 404 here (no MusicBrainz data for the test album), so the `knowledge_paths_album_gaps` 396 ms median is the not-found path, which still makes about five outbound calls per request (finding 5 above); it is not a measure of the real route. Limitations: one development machine, one test library, one album and one artist; indicative only. Not deployed. No code changed in this entry.
- 2026-11-16 (M1 follow-up): Every httpx and urllib request is counted, and store statements are timed per verb, in PR #1142, squash `53a8f656`, head `af5bded8`. Focused tests only (`tests/test_runtime_metrics.py`); lint changed files 0 new findings. Not deployed. CI: `compile` and `test-and-build` had no recorded conclusion at merge. M2 is next.
- 2026-11-16 (R5): Worker loop lifecycle implemented in PR #1140, squash `034341ea`, head `efd564d4`. Persisted refresh cadence (`meta` key `insights_refresh.last_run_at`), a stop hook in the provider tick (`should_stop`), stop-aware waits and a bounded join of the loop threads before the worker lock is released; compose `stop_grace_period: 30s`. Focused tests only: 75 passed across seven files; lint changed files 0 new findings. Full suite not run locally. Not deployed. CI on the head: `compile` and `test-and-build` were still in progress at merge.
- 2026-11-11 (revision 5): Full rewrite against `main` at `b5a90bf3`. Adds findings F1 to F12 read from source (stuck jobs after a worker kill, unshared MusicBrainz pacing, write transaction on every knowledge read, settings and HTTP client churn, unbounded caches, duplicate ingest, dead code). Replaces the generic dispatcher, the strict single-egress rule and the cache-folding proposal with smaller designs; defers profile read models, lanes and multi-worker web. Corrects status: the worker process, `source_state`, the state-file split, `KnowledgeReader` routes and one real slice import exist; the shared limiter and scheduler do not. Adds a per-step roadmap with model assignments. Documentation only: nothing was executed or measured, and no code, tests, configuration, provider traffic, publication or deployment changed.
- 2026-11-06 (revisions 1 to 4): Combined the provider batching audit with the worker-separation plan; added the review of revision 1, the knowledge-store section, the shared-limiter requirement, the dump-slice decision (D-1), the state-file split, stale-versus-missing rules and cold-start requirements. Full text is in the git history of this file.

- 2026-11-17 (W2): similar-artist precompute moved to the worker, merged as PR #1156 (squash `3e518379`, head `39d38d78`). New `app/services/similar_precompute.py` (scheduler entry `similar_precompute`, daily, last, retry 1800 s); `worker_schedule.NOT_READY`; `run_precompute(stop=)`; web startup warms its owned index once and starts no precompute thread; worker compose gains `LASTFM_API_KEY`. Index build measured only on synthetic data (1,000 artists, 100,000 songs: 4.5 s, 69 MiB traced peak); the worker logs real figures per run. Focused unittest 195 + 8 OK; lint 0 new findings in 9 files; full suite, M2 and a live worker not run.
- 2026-11-17 (P3, legacy metadata cache): fixes F7, merged as PR #1152 (squash `1cd9fb6e`). Changes: `metadata_cache.py` (per-thread connections, one schema setup per process, WAL, `prune`), `app/worker.py` (daily `_daily_maintenance`), and tests. Local micro-timing on a temp DB (median): `get` 130 µs → 12 µs, `set` 533 µs → 40 µs, measured on one machine. Focused tests: `tests/test_metadata_cache.py`, `tests/test_metadata_cache_lifecycle.py`, `tests/test_metadata_persistent_cache.py`, `tests/test_worker_metadata_prune.py`, `tests/test_worker_lock.py`, `tests/test_worker_shutdown.py`. Not measured: M2 (this file is outside its counters) and the file size over time on a production-size store. Not deployed.

## Appendix A. Process-local state inventory (M3)

Survey at `main` `cc14fb51`, 2026-11-17. Documentation only; no code, tests or runtime changed. Scope: the server packages in `docs/ARCHITECTURE.md` and `navidrome_server.py`; tests excluded. Method: grep for `threading.Thread(`, `ThreadPoolExecutor(`, `threading.Lock/RLock/Event/Semaphore(`, `lru_cache` (none in server code) and module-level assignments of mutable containers, then read each hit. Line numbers are as of `cc14fb51`; cite by symbol. About 100 constant tables (labels, host maps, header dicts, tuning values) are immutable and are not listed.

Classes: **rebuildable cache** (can be dropped without losing data), **shared mutable** (state or a lock that more than one thread uses), **singleton side effect** (starts a thread, patches a global, or runs once per process). "Process" means one web or worker process: every row is per process unless it says otherwise.

### A1. Threads and pools

| Where (symbol) | Process | Starts | Class | Notes |
|---|---|---|---|---|
| `navidrome_server.py` `_start_discovery_scheduler`, `_discovery_scheduler_thread` (~2458) | web | daemon scheduler loop | singleton side effect | W3: removed; the worker's `discovery_lists` entry (`app/services/discovery_schedule.py`, thread `worker-schedule-discovery`) runs the pass. |
| `discovery/lens_service.py` `start_daily_refresh` (`navidrome-lens-lists`) | web | daily loop | singleton side effect | W3: removed; the worker's `lens_lists` entry runs it. |
| `discovery/lens_service.py` manual refresh (`navidrome-lens-lists-manual`) | web | one per request | shared mutable | Guarded by `_REFRESH_LOCK` (41) in process and, since W3, by `refresh_guard` (`run_job` scope `lens_lists`) across processes. |
| `app/api/search.py` `start_similar_precompute` (`navidrome-similar-artists`) | web | daily loop | singleton side effect | W2; reads the process-local owned index. |
| `navidrome_server.py` refresh threads (`navidrome-refresh-<list>`, ~2393) | web | one per manual refresh | shared mutable | Guarded by `_DISCOVERY_REFRESH_LOCK` (708). |
| `navidrome_server.py` import recovery (`navidrome-import-recovery`, ~1586) | web | one per watched import | shared mutable | Guarded by `_DISCOVERY_IMPORT_ACTIVE` (A3). Safety-critical (import). |
| `discovery/refresh.py` revalidation (`navidrome-revalidate-<list>`, ~416) | web | one per revalidation | shared mutable | `_revalidate_in_flight`, `_revalidate_last_start` under `_revalidate_lock` (359-361). |
| `discovery/identity.py` `_work` (~218) | web | one per run | shared mutable | `_running` under `self._lock` (207). |
| `acquisition/track_service.py` track thread (`navidrome-track-<id>`, ~294) | web | one per track request | shared mutable | `_ACTIVE` under `_ACTIVE_LOCK` (45-46). Safety-critical (acquisition). |
| `app/api/radio.py` `_scrobble_in_background` (~222) | web | one per play | one-shot | Fire and forget; no shared state. |
| `discovery/search/index.py` `_run_build` (~344) | web | one per index generation | shared mutable | Started without the lock held; `self._lock` (285). |
| `discovery/search/network.py` purge thread (~65) | web | one per scheduled purge | shared mutable | `_purge_scheduled` under `_purge_lock` (46-47). |
| `discovery/search/runner.py` per-part thread (~218) | web | one per search part | shared mutable | `_inflight` under `RLock` (49-50). |
| `app/worker.py` `insights-refresh` (`insights_refresh.start`, ~111) | worker | six-hourly loop | singleton side effect | Stop `Event` from `main` (96); joined within 25 s (R5). |
| `app/worker.py` `library-enrich` (~112) | worker | loop | singleton side effect | `_LOCK` (`library_enrich.py` 25). Does not stop mid-run (R5 limitation). |
| `app/worker.py` `_metrics_loop` (~114, line 79) | worker | every 5 min | singleton side effect | Writes the runtime snapshot to `meta`. |
| `app/api/metadata.py` `_review_pool` (473) | web | module-level pool, 8 workers | singleton side effect | Lives for the process. |
| `app/api/metadata.py` per-request pools (124, 669) | web | per request | one-shot | No shared state. |
| `discovery/search/album_page.py` (183, 336), `artist_sections.py` (586), `genre_page.py` (195), `artist_tag_fallback.py` (184), `lb_tag_lane.py` (115) | web | per request | one-shot | Per-request pools; `artist_sections.identity_lock` (542) is per request. |
| `intelligence/artwork/service.py` `_pool` (31) | per process | one worker per `ArtworkService` | singleton side effect | `_building_lock` (33); `_image_slot` semaphore of 1 (34); `_keyed` per-key locks (36, 162) grow with each key. |
| `intelligence/waveform/peaks.py` `_pool` (89), `_running` (91) | web | per `PeakService` | shared mutable | `_running` under `_lock` (90). |

### A2. Caches and registries

| Where (symbol) | Process | Class | Notes |
|---|---|---|---|
| `app/api/metadata.py` `_artist_bio_cache` (57), `_artwork_cache` (159), `_album_details_cache` (266), `_artist_image_cache` (335), `_album_links_cache` (336), `_apple_url_cache` (350), `_album_description_cache` (376), `_review_cache` (464) | web | rebuildable cache | F8. Unbounded at `cc14fb51`. P4 (PR #1153, merged) makes each a `LayeredCache` (`app/services/layered_cache.py`): 2,000 entries per namespace, single-flight per key. They are the first K1 and K2 targets. |
| `app/api/metadata.py` `_EXTERNAL_HTTP` (39) | web | singleton side effect | Shared `MeteredClient`. The process-wide patch in A4 also counts its calls. |
| `integrations/musicbrainz/album_year.py` `year_cache` (14), `_year_lock` (15) | web and worker | rebuildable cache | One lookup per pair at a time; spacing comes from the provider gate. Unbounded at `cc14fb51`; P4 (PR #1153, merged) caps it at 2,000 pairs (LRU). |
| `app/api/artwork.py` `_SERVICES` (29), `_LOCK` (30) | web | shared mutable | One `ArtworkService` per key. |
| `app/api/radio.py` `_STORES` (22), `_STORES_LOCK` (23) | web | shared mutable | One radio store per key. |
| `app/api/search.py` `_owned_index` (53), `_owned_index_lock` (53) | web | shared mutable | Process-local owned index; the reason W2 needs the worker to own similar-artist precompute. |
| `app/api/auth.py` `_LOGIN_ATTEMPTS` (10), `_LOGIN_ATTEMPTS_LOCK` (11), `AUTH_LOCK` (9) | web | shared mutable | Authentication. The lockout counter is per process, so with several web workers (D in section 10) the effective limit multiplies. |
| `integrations/provider_gate.py` `_default_lock` (226), `Gate._memory_lock` (57) | web and worker | shared mutable | The in-process half of the gate. The cross-process state is `provider_gate.sqlite3`. |
| `discovery/search/limiter.py` `SourceLimiter._next_at`, `_lock` (29) | web | shared mutable | Search-source pacing (F2). Not shared with the worker. |
| `intelligence/artwork/fetchers.py` `HostPacer._lock` (70) | web | shared mutable | The MusicBrainz host runs through the gate (R3 part 2). |
| `app/services/runtime_metrics.py` `_requests` (43), `_gate` (44), `_store` (45), `_lock` (41) | web and worker | shared mutable | Counters only. The worker saves a snapshot to `meta` every 5 min. `_HOSTS` (27) is a fixed table. |
| `integrations/lastfm/client.py` `_request_lock` (46) | per process | shared mutable | One lock per client instance unless one is injected. |
| `intelligence/store/db.py` `_ensured` (83), `_ensure_lock` (84) | web and worker | singleton side effect | One migration per store path per process; `ensure_store` runs at web and worker startup only. |
| `metadata_cache.py` `MetadataCache._local` (thread-local connection), `_schema_lock`, `_schema_ready` | web and worker | per-process connection pool | One connection per thread, kept for the thread's life and closed on a storage error, a replaced file or a new pid. The table and index are created once per process per file. Added by P3. |
| `intelligence/sonic/cache.py` `_lock` (29), `intelligence/sonic/detect.py` `_lock` (30) | per process | shared mutable | Lock around per-process cache state (contents not read in detail). |
| `intelligence/artwork/store.py` `RLock` (68) | per process | shared mutable | Lock around the artwork store handle. |
| `integrations/radio/now.py` `_connections`, `_lock` (28) | web | shared mutable | ICY relay connection state. |
| `integrations/radio/logos.py` `_LOCKS` (29), `_LOCKS_GUARD` (30) | web | shared mutable | One lock per station id; never removed, so it grows with stations. |
| `recommendation/replay.py` `_CLAIMED_CAPTURE_PATHS` (318), `_CAPTURE_CLAIM_LOCK` (317) | tooling | shared mutable | In-process claim of capture files. |
| `acquisition/import_hooks.py` `_listeners` (11) | per process | singleton side effect | Mutable listener registry, no lock. |
| `acquisition/progress_snapshots.py` `_snapshots` (14), `_lock` (15) | per process | shared mutable | Acquisition progress. |
| `discovery/library_resync.py` `_pending`, `_lock` (33) | per process | shared mutable | Timer-based resync; the timer factory is injected. |
| `discovery/refresh.py` `_revalidate_in_flight`, `_revalidate_last_start`, `_revalidate_lock` (359-361) | web | shared mutable | Revalidation guard. |
| `discovery/search/network.py` `_purge_scheduled`, `_purge_lock` (46-47) | web | shared mutable | Purge scheduling guard. |

### A3. Locks and guards in `navidrome_server.py` and the route modules

| Where (symbol) | Process | Class | Notes |
|---|---|---|---|
| `navidrome_server.py` `_DISCOVERY_IMPORT_ACTIVE` (1442), guarded by `_DISCOVERY_IMPORT_LOCK` (1438) and `_DISCOVERY_IMPORT_TRANSITION_LOCK` (1441) | web | shared mutable | Also read by the status routes (1885, 2221). |
| `navidrome_server.py` `_DISCOVERY_ACQUIRE_ACTIVE` (1443) | web | shared mutable | **Resolved 2026-11-17.** Written by `acquisition/request_coordinator.py` (through `reserve_acquisition_request` in `acquisition/orchestration.py`, which the caller guards with `_DISCOVERY_IMPORT_TRANSITION_LOCK`; the discard runs in the same guard) and by `acquisition/track_service.py` (add near line 159, discard near 164, both under `_DISCOVERY_IMPORT_TRANSITION_LOCK`). `navidrome_server.py` line 2222 only passes the set into the coordinator. An acquisition guard, not a status-route read. |
| `navidrome_server.py` `_DISCOVERY_REFRESH_LOCK` (708) | web and worker | shared mutable | In-process guard for Personal refreshes. Since W3 the cross-process guard is `discovery/refresh_guard.py` (`run_job` scope per list); the other list locks work the same way. |
| `app/api/popularity.py` `_LOCK` (35), `app/api/taste_refresh.py` `_LOCK` (22), `app/api/paths_warm.py` `_LOCK` (24), `app/api/smart_playlists.py` `_LOCK` (27), `app/api/feedback.py` `_LOCK` (24), `app/api/insights.py` `_LOCK` (49) | web | shared mutable | One lock per route module, serialising that route's in-process work. Route bodies were not read in detail. |
| `app/worker.py` `stop` `Event` (96), `worker.lock` file lock | worker | singleton side effect | Process lifecycle; R1 and R5. |

### A4. Process-wide patches

| Where (symbol) | Process | Class | Notes |
|---|---|---|---|
| `app/services/runtime_metrics.py` `install()` | web and worker | singleton side effect | Patches `httpx.Client.send`, `httpx.AsyncClient.send` and `urllib.request.OpenerDirector.open` for the whole process at startup. Any library that uses them is counted. |

### A5. Findings from the survey

1. Several daemon loops start from web startup (`navidrome_server._start_discovery_scheduler`, `lens_service.start_daily_refresh`, `search.start_similar_precompute`). This is the W2 and W3 scope. Their state (the owned index, `_REFRESH_LOCK`, `_DISCOVERY_REFRESH_LOCK`) is process-local, so moving them requires moving that state too.
2. The web process has no cross-process lock for anything in A2 or A3. The provider gate's SQLite file is the only cross-process state for provider traffic. Any second web worker (D) therefore doubles each in-memory cache and each lockout counter.
3. The eight metadata caches in A2 are unbounded and never evict. They are the first K1 and K2 targets.
4. Resolved: `_DISCOVERY_ACQUIRE_ACTIVE` is written by `acquisition/request_coordinator.py` and `acquisition/track_service.py`, both under `_DISCOVERY_IMPORT_TRANSITION_LOCK`. It is an acquisition guard, so W3 does not need to move it.
5. Resolved (PR #1175, squash `b6ff452d`, 2026-11-17): the per-key lock dictionaries (`logos._LOCKS`, `artwork/service._keyed`) now drop an entry when its last holder or waiter leaves. Before, they grew with every station and artwork key.

### A6. Cross-references

- W2 (similar-artist precompute): A1 rows for `start_similar_precompute` and the owned index in A2.
- W3 (lens refresh and discovery scheduler): A1 rows for the lens and scheduler threads, A3 rows for `_DISCOVERY_*` guards, and finding 4.
- K1 (request-time provider call inventory): A2 rows for the metadata caches, `_EXTERNAL_HTTP` and the gate.
- 2026-11-17 (M3): Process-local state inventory added as Appendix A, from a survey at `main` `cc14fb51` (grep for threads, pools, locks, `lru_cache` and module-level mutable containers, then each hit read). Documentation only; no code, tests, provider traffic, publication or deployment changed. Findings A5.1 to A5.5 recorded. The writer of `_DISCOVERY_ACQUIRE_ACTIVE` was resolved the same day (A3, A5.4). W2, W3 and K1 now reference the table.
