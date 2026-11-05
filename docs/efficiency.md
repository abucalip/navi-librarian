# Efficiency and runtime architecture plan

Last reviewed: 2026-11-06  
Repository baseline: `main` at `9a4e717123175bca358faad29aa9deae0a324fdb`.

## Purpose and decision

This document combines the external-provider batching audit with a practical plan for improving the organisation, runtime efficiency, reliability, and future scalability of Librarian.

**Keep FastAPI. Do not rewrite the web framework.** FastAPI is already a good fit for the HTTP/API layer. The main architectural constraint is that the web process currently starts and owns several long-running background loops, while important coordination structures (locks, caches, and the owned search index) are process-local. The app needs a clearer separation between serving requests and doing scheduled work, not a different web framework.

This is a proposal and implementation sequence, not permission to increase provider traffic, change recommendation behaviour, add infrastructure, publish an image, or deploy. Each code slice still requires its own focused PR, regression tests, exact-head CI, and any required owner approval.

## Executive summary

The recommended target has four parts:

1. **A — Separate web serving from background execution.** Keep FastAPI focused on HTTP requests. Move scheduled refreshes, provider enrichment, precomputation, and long-running work into a dedicated worker process. Build on `intelligence/jobs/`; do not introduce Celery or Redis by default.
2. **B — Reduce and control external I/O.** Prefer documented batch/browse APIs, reuse HTTP connections, coalesce duplicate requests, cache carefully, and parallelize only independent work within provider limits.
3. **C — Measure before tuning.** Extend the existing `Server-Timing` foundation into endpoint, provider, cache, database, queue, and job measurements. Compare request counts and elapsed time against repeatable fixtures before claiming gains.
4. **D — Prepare for multiple web workers without enabling them prematurely.** First remove process-local ownership of background tasks and coordination. Keep one Uvicorn worker until multi-process correctness is demonstrated.

The intended outcome is a simpler responsibility split, fewer unnecessary network calls, shorter and more predictable refreshes, better failure recovery, and a safe path to scale if real demand requires it.

## Current architecture: observed constraints

The following points were checked against the current GitHub source and configuration.

### Web application

- `app/main.py` assembles the FastAPI application, authentication, middleware, and route registration.
- `app/api/` contains HTTP adapters; `app/services/` contains reusable application services.
- The Docker image starts one Uvicorn process with `uvicorn app.main:app`. It does not currently set a worker count.
- API routes include both synchronous and asynchronous handlers. Keep that mix intentional: synchronous handlers are appropriate for blocking libraries; converting every route to `async def` without converting its I/O would not make it non-blocking.
- An application-level `Server-Timing` header already measures total API handling time.

### Background work currently attached to web startup

`app/main.py` schedules `_start_discovery_background()` after a 10-second timer. That function starts several services:

- `librarian._start_discovery_scheduler()`
- `discovery.lens_service.start_daily_refresh()`
- `app.api.search.start_similar_precompute()`
- `app.services.insights_refresh.start()`

The insights refresh service starts a daemon thread that checks every six hours and uses a process-local `threading.Lock`. Similar-artist precomputation has its own long-running loop in `app/api/search.py`. The legacy discovery scheduler is another background lifecycle concern.

This arrangement is workable with one web process, but it couples scheduled work to web startup and shutdown. If multiple Uvicorn workers are started, each worker runs its startup handlers and can start its own scheduler and threads. Process-local locks do not coordinate those copies.

The `library_resync.install()` startup hook is different: it installs the import-triggered resync integration. Keep request-triggered hooks in the web application unless the implementation review shows they belong elsewhere; the goal is not to move every startup action blindly.

### Existing job foundation

`intelligence/jobs/runner.py` already provides useful primitives:

- duplicate prevention for an active `(job, scope)`;
- item/time budgets;
- saved progress checkpoints;
- cancellation;
- recovery of stale running jobs;
- visible status and last-known-good results;
- data-version bumps only after success.

It is not yet a complete worker service: it provides the execution wrapper, not a long-running dispatcher, durable scheduler, or registered set of job handlers. Those are the next small pieces to add.

### Provider and persistence shape

- Provider clients and discovery logic already live in dedicated integration/discovery modules. Continue to keep HTTP route adapters out of provider policy.
- Several paths already have useful batch implementations (ListenBrainz metadata and MusicBrainz album-year lookup).
- Some metadata services make query-specific searches; this audit did not establish a safe bulk endpoint for all of them.
- Server V2 has a separate `intelligence/store/` SQLite database and a persistent job table. Do not duplicate that store or introduce a second job database without a specific reason.
- The app also has persistent metadata/discovery caches. Improve their use and consistency before adding another cache service.

## Target architecture

The intended deployment is two processes built from the same application image and sharing the existing persistent data volume on one host:

```text
macOS / Android / browser clients
              |
              v
       FastAPI web process
       - authentication
       - HTTP validation and responses
       - SSE / streaming
       - short request-scoped work
              |
              v
       application services and domain logic
       - discovery / recommendations
       - provider clients
       - cache and repository interfaces
              |
       +------+-------------------------------+
       |                                      |
       v                                      v
persistent SQLite stores              external services
- metadata/discovery cache             - Navidrome
- Server V2 store and jobs             - MusicBrainz
- last-known-good results              - ListenBrainz
                                       - Last.fm / others

       Dedicated background worker
       - durable scheduler / dispatcher
       - provider enrichment
       - daily and periodic precomputation
       - insights and inventory refresh
       - bounded, resumable jobs
       - writes results to the same stores
```

The web process should enqueue work and read saved results; it should not run a long provider refresh inside a request. The worker should call the same domain and service functions as the web layer, not implement duplicate business logic.

For the current single-host deployment, the web and worker can use the same image, configuration, and mounted `/data` volume with different container commands. Keep one worker initially. This does not require Redis, Celery, RabbitMQ, Kubernetes, or PostgreSQL.

## A. Separate background work from the web server

### A1. Inventory and classify every background task

Before moving code, make a complete task inventory. For each task, record its trigger, cadence, inputs, outputs, current owner, provider budget, persistence, duplicate-prevention rule, and failure behavior.

Initial inventory from the current source:

| Work | Current location / start point | Target owner |
|---|---|---|
| Legacy discovery scheduler | `app/main.py` calls `librarian._start_discovery_scheduler()` | Worker |
| Daily lens-list refresh | `discovery/lens_service.py`, started from web startup | Worker |
| Similar-artist precompute | `app/api/search.py`, `start_similar_precompute()` | Worker |
| Insights refresh and Navidrome inventory ingest | `app/services/insights_refresh.py`, `start()` | Worker |
| Import-triggered library resync hook | `app/library_resync.py`, installed at startup | Remains web-integrated unless its request lifecycle proves otherwise |
| Search owned-index build | `discovery/search/index.py`, lazy/single-flight in-process build | Initially remains an on-demand web read model; make its process ownership explicit before multi-worker mode |

Do not move all work in one large refactor. Extract one job at a time, preserve its schedule and output contract, and compare its old and new behavior.

### A2. Complete the existing job framework with a small worker runtime

Build on `intelligence/jobs/` and the existing `job_runs` table.

Add focused modules, with final names chosen after checking current package conventions:

- a **job registry** mapping stable job names to handler functions;
- a **worker loop** that polls for queued/due jobs, claims one atomically, invokes the registered handler, records outcomes, and sleeps when idle;
- a **scheduler** that records due work durably and enqueues it, rather than relying on an in-memory `last_day` variable or a `threading.Timer`;
- a **worker entry point** that opens the same configured stores and dependencies as the web app, then runs until a graceful shutdown signal.

The runner should remain a generic execution mechanism. Job-specific provider and domain logic belongs in separate handlers, not in the dispatcher.

Before adding tables or changing the schema, inspect the existing `intelligence/store/` migration and job schema. Reuse the current database and migration system. A durable schedule needs enough persisted information to prevent missed or duplicate daily runs after a restart (for example, a job key, next-due time, and last scheduled generation/day).

### A3. Give each job an explicit contract

Every registered job should define:

- stable name and scope key (for example, one global daily job or one job per artist);
- schedule and eligibility conditions;
- maximum items, elapsed time, and provider requests per run;
- checkpoint data needed to resume safely;
- resources/data versions changed on success;
- retry/backoff policy for transient failures;
- whether a partial result may be published or must leave last-known-good output untouched;
- cancellation points and stale-run recovery behavior.

Use the existing runner's budgets, checkpoints, duplicate prevention, cancellation, and last-known-good semantics. Do not make network requests while holding a SQLite write transaction. Keep transactions short and commit progress/results in bounded units.

### A4. Move current loops incrementally

Suggested extraction order:

1. **Insights refresh:** turn the six-hour loop in `app/services/insights_refresh.py` into a callable job handler. Preserve enabled-lens checks, the 120-request provider budget, the 40-artist ingest slice, the seven-day ingest freshness, and the rule that a failed or partial refresh does not replace saved good cards.
2. **Similar-artist precompute:** turn the daily loop in `app/api/search.py` into a handler. Preserve its cursor, daily cadence, owned-index readiness gate, cache behavior, and bounded provider work. The route module should no longer own a forever-running thread.
3. **Daily lens-list refresh:** expose the existing service operation as a handler and preserve its current schedule and result contract.
4. **Legacy discovery scheduler:** inspect the scheduler's individual tasks and migrate them one by one. Do not copy the entire legacy orchestration object into a new worker module or create a parallel implementation.
5. Remove the corresponding web-startup thread/timer only after each replacement is active and verified.

The web app's startup should be limited to web-owned resources: dependency setup, middleware/router readiness, and request-triggered integrations. The worker should not import or instantiate the FastAPI app merely to reuse domain logic.

### A5. Keep scheduling and execution safe

- Enqueue the same logical job twice and prove only one active run exists.
- Use a database-backed claim/lease or equivalent atomic transition; a process-local lock is insufficient.
- On worker restart, recover stale claims and resume from the last checkpoint.
- Make handlers idempotent: retrying a completed slice must not duplicate cards, cache rows, or inventory entries.
- Use bounded retry with backoff for transient provider/network failures; do not retry permanent 4xx responses indefinitely.
- Preserve last-known-good data on failed or incomplete runs.
- Shut down gracefully: stop claiming new jobs, allow a bounded grace period for the active unit, checkpoint, and exit.
- Keep provider pacing and request budgets global to the worker, not independently reset by each concurrent job.

### A6. Deployment shape

Initially run exactly:

- one FastAPI web process/container;
- one background worker process/container;
- one shared persistent data volume and identical provider configuration;
- one scheduler authority.

Use the same Docker image with a different command/entry point for the worker. Do not publish or deploy as part of this plan; deployment requires separate explicit authorization and the normal runtime verification.

**Acceptance criteria**

- Starting/restarting the web process does not start duplicate scheduled jobs.
- Starting/restarting the worker does not lose due work or corrupt last-known-good output.
- Each migrated job runs once per due interval, resumes after interruption, and exposes status/progress.
- A slow provider job does not occupy a web request handler or delay authentication/API startup.
- Existing API payloads, discovery results, refresh cadence, and provider budgets remain unchanged.
- Focused tests cover duplicate enqueue, atomic claim, crash recovery, cancellation, retry, partial failure, idempotency, and last-known-good behavior.

## B. Reduce and control external I/O

Efficiency should come first from doing fewer unnecessary requests, not from sending more requests concurrently. Every provider request must use a documented batch/browse form whenever one exists. A single-entity request remains valid when the provider has no suitable multi-entity operation or when a batch cannot preserve the required semantics.

### B1. MusicBrainz critical ratings — highest-priority batch opportunity

**Current path:** `discovery/classics_ratings.py` selects up to 80 candidates and calls `integrations/musicbrainz/rating_client.py` once per uncached release group. The individual lookup uses `/ws/2/release-group/{mbid}?inc=ratings`; each uncached request is paced.

**Improvement:** partition eligible candidates by artist MBID, deduplicate artist IDs, read the existing release-group cache first, and browse each artist's release groups with `inc=ratings`. Page up to the documented limit and match returned release-group MBIDs back to the shortlist. Populate the existing cache with the same key, TTL, and value shape.

Keep the individual lookup only as a bounded fallback when an artist MBID is absent, the target is not returned, or browse completeness is uncertain. Record why the fallback occurred. A partial artist browse must never be interpreted as proof that a candidate has no rating.

Preserve the 80-candidate shortlist, ordering, first-30 year enrichment, rating/vote-count semantics, pacing, and non-fatal failure behavior.

**Priority: High.** Expected request shape changes from up to 80 uncached album lookups to roughly one or more pages per distinct candidate artist. Measure the actual reduction on a fixed candidate fixture.

### B2. MusicBrainz tracklists — likely two sequential calls to one browse

**Current path:** `MusicBrainzSearch.release_group_tracks()` looks up a release group to list releases, chooses an Official release (then earliest date), and looks up that release with recordings.

**Improvement to validate:** browse releases by release-group MBID with `inc=recordings`, then apply the same Official-first/earliest-date selection to the returned releases. Parse media, track order, recording titles, and durations from the selected release.

Test single-release, multi-edition, multi-disc, unofficial-only, large-tracklist, and paginated groups. MusicBrainz browse responses have a 500-track cap and may return fewer releases than requested; advance offsets by the number actually returned. If the preferred release or complete tracklist cannot be established within a strict page bound, use the existing two-request path.

Do not switch callers until ordered tracks and durations match the old implementation on representative fixtures.

**Priority: Medium–high.** This reduces sequential round trips per release group; it is not a universal multi-album batch.

### B3. Preserve existing ListenBrainz batches

`discovery/batch_metadata.py` already batches:

| Operation | Endpoint | Current chunk |
|---|---|---:|
| Recording metadata | `/1/metadata/recording/` | 100 recording MBIDs |
| Release-group metadata | `/1/metadata/release_group/` | 50 release-group MBIDs |
| Artist genre tags | `/1/metadata/artist/` | 75 artist MBIDs |

Keep these chunk sizes until live response contracts and request budgets justify a measured change. Preserve the separate batch cache, title-marker safeguard, and bounded MusicBrainz fallback for missing or failed chunks. The batch response does not carry every field from a full MusicBrainz recording lookup.

### B4. Keep MusicBrainz album-year list lookups batched

`integrations/musicbrainz/album_year.py` already provides `lookup_album_years()`, which groups up to 15 artist/album pairs, caps results, recursively splits capped chunks, and preserves exact title/artist-credit matching and shared pacing/cache behavior.

List consumers should use the batch path (including `/api/album-years`) rather than call the single-album lookup in a loop. Keep the single-item path for genuine one-album requests.

### B5. Preserve and extend Server V2 per-artist browses

The insight provider runtime already uses paginated per-artist browse operations for release-group linking, studio discography, and series relationships. PR #802 moved series relationship discovery from one lookup per owned release group to a paged release-group browse per artist.

Artist lifespan, ListenBrainz top release groups for one artist, and MusicBrainz series details remain entity-scoped in the current audit. Do not call them batching defects without documented provider support for a suitable multi-entity request. Revisit only when a documented endpoint or an already-fetched response supplies equivalent data.

### B6. Navidrome inventory ingestion — first-party API opportunity

`app/services/insights_refresh.py::_ingest_step()` currently calls `getArtists`, then `getArtist` for each due artist, then `getAlbum` for each album stub.

Investigate whether `getAlbumList2` or another supported Navidrome list operation can return all fields consumed by `intelligence/ingest/navidrome.py::ingest_album()`. Compare MBIDs, artist credits, dates, genres, track counts, and any other consumed fields. Replace per-album calls only if the list response is semantically equivalent. Otherwise keep the detail calls, bounded by the existing artist slice and freshness cache.

This is a first-party Navidrome API optimization, not an external-provider batching requirement.

### B7. Metadata lookups: connection reuse, coalescing, and cache discipline

The Apple Music, Deezer, Wikipedia, review, artwork, and artist-bio services often perform query-specific searches or fetch a selected entity. The audit did not establish a general multi-album endpoint that preserves their exact matching/editorial semantics.

Improve these paths in this order:

1. **Request coalescing:** if two requests ask for the same normalized provider operation at the same time, let them share one in-flight result rather than issuing duplicate searches. Keep the coalescing scope explicit and safe across threads.
2. **Persistent cache audit:** standardize keys around provider, operation, normalized query or stable provider ID, and relevant credential/config generation. Keep positive, definitive-negative, and transient-error outcomes distinct. Use suitable TTLs; do not cache timeouts, rate limits, or transient server errors as permanent misses.
3. **Connection reuse:** where a provider client currently calls top-level `httpx.get/post`, use a long-lived provider-scoped `httpx.Client` (or `AsyncClient` only where the whole call path is async) with explicit connect/read timeouts, connection limits, and lifecycle ownership. Avoid creating a new connection pool for every item.
4. **Bounded concurrency:** parallelize independent provider operations only when their rate limits and existing pacing allow it. Use per-provider limits and timeouts. MusicBrainz's global pacing must not be bypassed by concurrent workers.
5. **Exact matching remains authoritative:** Apple multi-ID lookup is useful only after stable catalog IDs are known; it does not replace arbitrary text search. Do not combine unrelated search strings into a guessed endpoint.

Do not create a generic provider framework just to wrap every client. Add shared transport/coalescing behavior only where repeated code or measurements show a real benefit.

### B8. Controlled concurrency, not unbounded parallelism

- Parallelize independent work across different providers or operations when it reduces wall-clock time and does not violate budgets.
- Keep a per-provider concurrency/rate limiter shared by all jobs in the worker.
- Bound pending work and connection pools; do not create one thread/task per album or artist.
- Apply explicit connect/read/overall deadlines and bounded retries with jitter where provider policy permits.
- Avoid retry storms after 429s or provider outages; respect retry-after where available.
- Make cancellation stop scheduling new work and allow in-flight requests to finish or time out safely.
- Keep provider errors non-fatal where the current product contract expects partial results.

**Acceptance criteria**

- For every new batch path, a test proves deduplication and the expected bounded request count for N inputs.
- Tests cover missing identifiers, partial pages, caps, malformed responses, per-chunk failures, 429/timeouts, and fallback reasons.
- Output matching, order, cache semantics, public API shapes, and failure behavior remain unchanged.
- Fixed-fixture before/after measurements report requests, cache hits, fallbacks, and elapsed time.
- Live provider traffic remains within existing budgets and requires the same approval as today.

## C. Measure performance and bottlenecks

Do not tune worker counts, thread pools, concurrency, or caches based on intuition. The app already emits a total API `Server-Timing` value; use that as the first measurement point, then add low-overhead detail.

### C1. Request measurements

Record, at minimum:

- route template (not raw user-supplied path or query);
- total application time;
- time spent in domain/service work;
- provider wait time and provider request count by provider/operation;
- database read/write and lock-wait time where measurable;
- cache hit, miss, stale-hit, and coalesced-request counts;
- response status and whether the response is partial/deadline-limited.

For streaming/SSE routes, distinguish time to first event from total stream duration. Do not buffer streams just to measure them.

### C2. Provider measurements

Instrument the common provider transport or the narrow provider client boundaries to capture:

- operation and provider;
- request duration and outcome class (success, not-found, rate-limited, timeout, server error);
- retry count and retry-after delay;
- batch size, page count, returned item count, and truncation/incompleteness;
- cache result and fallback reason.

Never record tokens, authorization headers, full URLs containing credentials, raw listening history, or private library content. Use low-cardinality labels; do not put MBIDs, album names, user IDs, or arbitrary query strings into metric labels.

### C3. Job and database measurements

Use the existing job record as the durable source for:

- enqueue-to-start delay;
- run duration;
- state, attempts, checkpoint progress, and bounded error class;
- items processed and provider requests consumed;
- time spent waiting for provider budget;
- last successful completion and age of last-known-good output.

For SQLite, measure transaction duration and busy/locked retries. Keep network I/O outside write transactions. Track WAL growth/checkpoint behavior and database file size; do not run a checkpoint or vacuum on every request.

### C4. Establish a baseline and compare fairly

Before changing a hot path, capture a repeatable baseline:

- fixed input fixture or provider response tape;
- same library/sample size and configuration;
- same cache state (cold and warm results reported separately);
- request counts by provider/operation;
- median and p95 elapsed time where repeated samples are meaningful;
- memory/CPU only when relevant to the hypothesis.

After the change, replay the same inputs and report the delta. A reduction in Python lines, a new async function, or a successful startup is not a performance result.

### C5. Use evidence to decide what to tune

- If provider wait dominates, reduce calls through batching/cache reuse before raising concurrency.
- If CPU dominates, profile the specific transformation/ranking stage before adding processes.
- If database lock time dominates, shorten transactions and reduce write contention before replacing SQLite.
- If API queueing dominates, inspect synchronous thread-pool saturation and blocking calls before changing worker counts.
- If memory dominates, profile the owned index and caches, including duplicate per-process copies.
- If jobs are slow but do not affect API latency, tune worker budgets independently from web serving.

**Acceptance criteria**

- Every optimization PR states its hypothesis and baseline.
- The same fixture/tape produces comparable before/after request counts and output.
- Metrics are privacy-safe and do not expose credentials or listening/library details.
- The dashboard or logs make a slow endpoint distinguishable from provider wait, database contention, and worker queue delay.

## D. Prepare for multiple web workers safely

Multiple Uvicorn workers are not the first optimization. Each process has separate memory and runs its own startup lifecycle. Today, that can duplicate background loops and create independent copies of process-local locks, caches, and the owned search index.

### D1. Keep the current one-worker setting for now

Do not add `--workers` to the Docker command until the following are true:

- no scheduled/periodic job is started by web startup;
- job scheduling and claiming are coordinated through shared persistence;
- all correctness-critical cache/lock behavior is process-safe or explicitly process-local and rebuildable;
- the owned search index has a defined multi-process strategy;
- the web app can start two instances against the same data volume without duplicated side effects or inconsistent results.

### D2. Audit process-local state

Create an inventory of module globals, locks, singleton clients, in-memory caches, and background threads. Classify each as:

- immutable configuration (safe to duplicate);
- rebuildable local cache/index (safe only if reads tolerate independent copies and refreshes are coordinated);
- shared mutable state (must move to persistent/shared coordination);
- singleton side effect (must have one elected owner).

The current owned search index in `discovery/search/index.py` is process-local and single-flight only within one process. Decide whether to:
- keep a per-process read-only index rebuilt from a shared persisted snapshot/generation, with a safe invalidation mechanism; or
- move index construction/refresh into the worker and persist an immutable snapshot for web processes to read.

Choose based on measured memory, build time, freshness, and consistency requirements. Do not add Redis solely to share this index without measuring the trade-off.

### D3. Make shared SQLite usage deliberate

For a single host with one web process and one worker, the existing SQLite stores remain a reasonable starting point.

Before running multiple web workers against the same files:

- verify WAL mode and a suitable busy timeout for each relevant database;
- keep write transactions short and never hold them over provider calls;
- ensure job claims and uniqueness constraints are atomic across processes;
- test simultaneous reads/writes, cancellation, stale-job recovery, and worker restart;
- monitor lock waits, busy errors, WAL growth, and checkpoint behavior;
- confirm all processes use the same persistent mounted path and schema migration ownership.

Do not share a SQLite database over an arbitrary network filesystem or across multiple hosts. Do not let every web worker independently run migrations or one-time maintenance tasks.

### D4. Add multi-process verification before increasing workers

Run the web app with two Uvicorn workers and one worker process in an isolated test environment. Verify:

- only one scheduler authority and one active run per job/scope;
- no duplicated provider traffic or repeated refreshes;
- search index freshness and consistent API responses across requests routed to different processes;
- auth/session behavior and persistent settings;
- concurrent API reads and writes, job enqueue/cancel, and library resync;
- graceful web and worker restarts;
- no SQLite lock storms or unbounded memory duplication.

Only then compare one versus two web workers under representative concurrent requests. Increase further only if measured throughput or latency improves.

### D5. Delay larger infrastructure until evidence requires it

- **PostgreSQL:** consider only when measured concurrent write contention, multi-host operation, or multi-user requirements exceed the single-host SQLite design.
- **Redis:** consider only for a demonstrated need for cross-process ephemeral cache, distributed coordination, or a broker that the existing persistent job store cannot reasonably provide.
- **Celery/RQ/other queue:** consider only if the home-grown worker requirements outgrow the existing durable job framework (for example, multiple hosts, complex routing, high throughput, or mature operational tooling is needed). A queue migration has operational and failure-mode costs; it is not automatically more efficient.
- **More Uvicorn workers:** use only after D1–D4 are satisfied and load tests show a benefit.

## Prioritized implementation roadmap

The sequence below intentionally separates measurement, provider-call reduction, worker lifecycle, and horizontal scaling. It avoids a simultaneous framework, database, queue, and deployment migration.

| Order | Slice | Concrete deliverable | Why this order |
|---:|---|---|---|
| 0 | Baseline and task inventory | Record current route/provider/job timings and inventory every startup thread/scheduler and process-local singleton | Gives a safe baseline and exposes duplicate-work risks before changes |
| 1 | MusicBrainz ratings batch | Artist-grouped release-group browse with ratings, cache parity, bounded fallback | Highest-value remaining provider request reduction |
| 2 | Tracklist browse prototype | Browse releases with recordings; prove exact tracklist equivalence before replacing the old path | Strong sequential-call reduction with bounded scope |
| 3 | Provider transport and coalescing | Reusable provider clients, request coalescing, explicit timeout/pool/rate-limit policy where measurements justify it | Reduces connection setup and duplicate requests |
| 4 | Worker foundation | Durable scheduler, registry, worker entry point, atomic claims, graceful shutdown and status | Separates runtime responsibilities without changing domain logic |
| 5 | Migrate background jobs | Insights, similar-artist precompute, lens refresh, then legacy scheduler tasks one by one | Removes web-startup side effects and improves recovery |
| 6 | Navidrome ingestion audit | Prove whether list endpoints replace per-album detail calls; implement only if equivalent | Reduces first-party API traffic without risking field loss |
| 7 | Observability completion | Endpoint/provider/database/job metrics and repeatable before/after reports | Makes future tuning evidence-based |
| 8 | Multi-process readiness | Shared-state audit, SQLite concurrency tests, two-web-worker verification | Enables scale only when correctness is demonstrated |

This is a proposed order, not an instruction to run provider traffic or deploy. If new correctness, security, data-safety, or CI gaps appear, those take precedence.

## What should not change as part of this plan

- **FastAPI remains the web framework.** Litestar, Django, Flask, and Sanic do not solve the current lifecycle/coordination problem. A framework migration would rewrite adapters and deployment behavior without a demonstrated efficiency gain.
- **Keep one Uvicorn worker initially.** Multiple workers are a later verification gate, not a setting to turn on now.
- **Keep SQLite for the current single-host deployment.** Do not migrate to PostgreSQL without measured contention or a multi-host/multi-user requirement.
- **Do not add Redis, Celery, RabbitMQ, or Kubernetes pre-emptively.** First complete the worker using the persistent job foundation already in the repository.
- **Do not convert all endpoints to async.** Use async when the full I/O path is awaitable; keep blocking library calls synchronous or offload them deliberately.
- **Do not parallelize provider calls without a shared budget and rate limiter.** MusicBrainz pacing and other provider limits remain authoritative.
- **Do not weaken exact matching, cache semantics, failure handling, or safety checks to increase apparent hit rates.**
- **Do not resume size-only modularization.** Extract only boundaries needed for the worker, provider transport, or measured bottleneck.

## Cross-cutting acceptance criteria

Every implementation slice must:

1. Identify the concrete bottleneck and current behavior from source and measurements.
2. Preserve public API response shapes, recommendation semantics, ordering, cache keys/TTLs where required, and last-known-good behavior.
3. Add focused regression tests for success, partial/incomplete data, provider failures, cancellation/restart, and unsafe concurrency cases relevant to the change.
4. Demonstrate bounded work: provider request budgets, page/chunk limits, time/item budgets, retries, and concurrency.
5. Prove provider batching with request-count assertions and before/after fixtures; cite the provider's official endpoint documentation in the PR.
6. Keep HTTP adapters, domain logic, provider transport, persistence, and worker lifecycle in their respective layers.
7. Preserve Docker packaging and the supported web interface. Do not reintroduce MCP runtime.
8. Review the full diff and verify all required CI workflows on the exact final PR-head SHA. Agents run focused tests only; the full suite is run by CI and may be run manually only with explicit owner approval.
9. Keep live provider traffic within existing budgets and obtain approval where required.
10. Keep publication, deployment, and runtime verification separate; no release or deployment is authorized by this plan.

## Provider documentation and current implementation references

- [MusicBrainz Web Service API](https://musicbrainz.org/doc/MusicBrainz_API) — lookup, browse, supported relationships, `inc=` values, ratings, and paging.
- [MusicBrainz API examples](https://musicbrainz.org/doc/MusicBrainz_API/Examples) — examples of release-group lookups and included releases.
- [MusicBrainz Search API](https://musicbrainz.org/doc/MusicBrainz_API/Search) — search is distinct from browse.
- [Apple iTunes Search API](https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/) — multi-ID lookup requires known catalog IDs and does not replace arbitrary text search.
- [ListenBrainz API documentation](https://listenbrainz.readthedocs.io/) — provider API reference; repository batch endpoints and chunk sizes are captured in `discovery/batch_metadata.py`.
- [FastAPI async details](https://fastapi.tiangolo.com/async/) — sync and async path operations can coexist; blocking libraries should not be disguised as asynchronous work.
- [FastAPI deployment concepts](https://fastapi.tiangolo.com/deployment/concepts/) — worker processes have separate memory and startup lifecycle.
- [Starlette thread pool](https://www.starlette.io/threadpool/) — synchronous endpoint/dependency execution shares a bounded thread pool.

## Change and evidence log

- 2026-11-06: Replaces the provider-only audit in `docs/batching.md` with this combined efficiency and runtime architecture plan. Baseline: GitHub `main` at `9a4e717123175bca358faad29aa9deae0a324fdb`. Documentation only; no application code, tests, provider traffic, publication, or deployment changed.
