# Efficiency and runtime architecture plan

Last reviewed: 2026-11-06  
Repository baseline for this revision: `main` at `db88d995bf1355a443209aedb7c5163cc119d7a9`.

## Purpose and decision

This document combines the external-provider batching audit with a practical plan for improving the organisation, runtime efficiency, reliability, and future scalability of Librarian.

**Keep FastAPI. Do not rewrite the web framework.** FastAPI is already a good fit for the HTTP/API layer. The main architectural constraint is that the web process currently starts and owns several long-running background loops, while important coordination structures (locks, caches, and the owned search index) are process-local. The app needs a clearer separation between serving requests and doing scheduled work, not a different web framework.

This is a proposal and implementation sequence, not permission to increase provider traffic, change recommendation behaviour, add infrastructure, publish an image, or deploy. Each code slice still requires its own focused PR, regression tests, exact-head CI, and any required owner approval.

## Executive summary

The recommended target has five parts:

1. **A — Separate web serving from background execution.** Keep FastAPI focused on HTTP requests. Move scheduled refreshes, provider enrichment, precomputation, and long-running work into a dedicated worker process. Build on `intelligence/jobs/`; do not introduce Celery or Redis by default.
2. **B — Reduce and control external I/O.** Prefer documented batch/browse APIs, reuse HTTP connections, coalesce duplicate requests, cache carefully, and parallelize only independent work within provider limits.
3. **C — Measure before tuning.** Extend the existing `Server-Timing` foundation into endpoint, provider, cache, database, queue, and job measurements. Compare request counts and elapsed time against repeatable fixtures before claiming gains.
4. **D — Prepare for multiple web workers without enabling them prematurely.** First remove process-local ownership of background tasks and coordination. Keep one Uvicorn worker until multi-process correctness is demonstrated.

5. **E — One knowledge store, one egress.** (Added in revision 2, see section E.) Consolidate the scattered metadata caches into the Server V2 store as a library-scoped music knowledge base that the worker builds and refreshes continuously. Every Discair service reads it; only the worker talks to external providers.

The intended outcome is a simpler responsibility split, fewer unnecessary network calls, shorter and more predictable refreshes, better failure recovery, and a safe path to scale if real demand requires it.

**Revision 2 changes the centre of gravity.** Parts A and E together do more for latency, provider load and reliability than any single batch optimisation in B, and they make several B items cheaper or moot. The roadmap is reordered accordingly (see the roadmap and the next section).

## Review: assumptions and blind spots in revision 1

These are corrections to the first version of this document. Each is checked against the repository unless marked "unverified".

1. **The plan optimises request counts where the user feels request latency.** B1 to B6 target scheduled and discovery paths. The paths a person waits on (artist bio, artwork, reviews, Wikipedia, Deezer/Apple lookups, tracklists) are treated in B7 as "coalesce and reuse connections". Coalescing makes a slow external call cheaper to share; it does not remove it from the page request. The structural fix is that no page request waits on a provider, which is section E. Without it, B7 is polish on the wrong layer.

2. **B1 (ratings browse) may cost more than it saves, and the document gives no break-even.** A browse returns every release group of an artist (singles, EPs, compilations) in pages of at most 100. For an artist with 300 release groups that is three or more requests to replace one lookup. The 80-candidate shortlist is chosen for variety, so it plausibly spans many distinct artists with one or two candidates each, where per-album lookup is already optimal. Browse only wins when candidates per artist exceed pages per artist. Before building B1: count distinct artists in a real shortlist and pages per artist (`type=album` filtering reduces pages). Also note ratings change slowly: with a long TTL the steady-state cost is already near zero and B1 only helps the cold start, which the worker (section E) absorbs off the request path. Priority downgraded from High to "Measure first".

3. **The plan ignores an accepted decision.** The Phase 0 audit records that MusicBrainz has no multi-ID lookup and that the bulk route is the dump slice (D-1, hybrid: local dump slice for bulk, API for the rest, accepted by the owner). Release-group ratings, relationships and tracklists for owned entities are exactly what a local slice answers with SQL and zero API calls. B1 and B2 should be re-evaluated against D-1 before any code is written; if the slice is built they are mostly moot. **Owner decision (2026-11-06): the dump slice is in, and it grows with the library.** B1 and B2 are therefore deferred behind it (roadmap slice 4) and may be dropped; see section E8.

4. **Pacing is process-local, so the two-process split would double MusicBrainz traffic.** `integrations/musicbrainz/rating_client.py` paces with an in-process `sleep` (and other clients are similar). MusicBrainz limits by client IP, not by process. A worker pacing at 1 request/s next to a web process still pacing at 1 request/s makes 2 requests/s during the whole migration. A5 says budgets must be "global to the worker", which is true only after every call has moved. Until then the limit must be shared through the database (a per-provider `next_allowed_at` row claimed atomically) or the web process must stop calling the provider before the worker starts. This is a hard prerequisite of slice 4, not a refinement.

5. **Section D is over-weighted for this deployment.** The product is a single-owner home server with a handful of clients. Multiple Uvicorn workers answer a throughput problem nobody has measured; the real constraints are the 1 request/s provider budget and page latency. D1 to D5 are sound as a gate but should be demoted to "only if C shows API queueing". The part of D worth doing early is the process-local state inventory (D2), because the worker split already depends on it.

6. **The existing cache is weaker than the document assumes.** `metadata_cache.py` opens a new SQLite connection and runs `CREATE TABLE IF NOT EXISTS` on every `get` and every `set`. It does not enable WAL (only `intelligence/store/db.py` does) and uses a 5 s busy timeout. It stores a bare value and timestamp with no source, operation, outcome class or provenance, so it cannot distinguish "never fetched" from "fetched and absent" from "failed", and B7's rule to keep those outcomes distinct is not expressible in it. Six more SQLite files hold overlapping state (`settings/persistence.py`, `discovery/store.py`, `acquisition/state.py`, `integrations/radio/store.py`, the Navidrome discovery DB and the metadata cache). "Persistent cache audit" understates the work: the cache needs replacing, not auditing.

7. **User state and rebuildable data share a table.** In the Server V2 store, dismissals live in `insights.dismissed_state`, next to derived cards that a generation bump is designed to rebuild, and `persistence.py` deletes undismissed cards on refresh. Today that is correct, but it means the file cannot be wiped and rebuilt without losing the owner's choices, which contradicts the rationale recorded in D-026 (the file can be backed up or wiped on its own). A knowledge base that the worker may rebuild must not hold irreplaceable user decisions.

8. **No cold-start estimate.** At 1 request/s the first fill of a large library is a multi-hour job, and this is the number that decides whether "only the worker calls out" is livable. With ~730 artists (the figure in the P3 follow-ups) and an assumed 10 provider calls per artist plus 2 per album, the artist side alone is about 2 hours of MusicBrainz time before albums. The plan should state the estimate, the order of fill (what the owner sees first), and what the UI shows while a fact is still pending.

9. **Provider terms are not examined.** Storing provider data for the long term is a different act from caching it for a day. Last.fm, Deezer and Apple publish retention and caching terms, and review sites (Pitchfork, Guardian and others in `app/api/`) are copyrighted text. The document should state per provider what may be stored (facts and links versus full text), and the knowledge base should store review links and short attributed excerpts rather than articles. I have not read each provider's current terms (unverified); this is a pre-implementation check, not a conclusion.

10. **Missing acceptance numbers.** "Reduction" and "bounded" appear throughout with no targets. ServerV2.md uses exit and kill criteria per phase; this plan should too (see section E acceptance).

11. **Minor.** Slice 0 says to record baselines, but slices 1 to 2 are scheduled before the instrumentation slice 7 that would measure them. Pull the minimum (provider call counters, cache hit counters, per-route provider wait) forward into slice 0. Section A4 migrates the legacy scheduler last, but it is the most likely place for hidden provider calls; inventory it first (A1) even if it moves last.

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
- Keep provider pacing and request budgets global, not independently reset by each concurrent job. While any provider call remains in the web process, "global" means shared through the database: a per-provider row holding `next_allowed_at` and a daily counter, claimed with an atomic update before each request. A process-local `sleep` is not enough once two processes exist (review item 4).

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

**Priority: Measure first (revised from High).** Expected request shape changes from up to 80 uncached album lookups to one or more pages per distinct candidate artist, which is a reduction only when candidates per artist exceed pages per artist. Count both on a real shortlist before building, and re-check against the D-1 dump slice (see the review section, items 2 and 3).

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

**Scope note (revision 2):** this deployment is a single-owner home server. Treat D as a gate to pass only if part C shows API queueing, not as a planned slice. The process-local state inventory (D2) is the exception: the worker split depends on it, so do it early.

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

## E. Music knowledge base: one store, one egress (v2)

**Proposal.** A worker progressively builds a knowledge base for the owned library (artist and album facts, relationships, context), keeps it current as the library changes, and is the only component that calls external providers. Every other service, web routes included, reads the knowledge base. The existing scattered caches are folded into it.

**Verdict: adopt, with four amendments.** The idea is the right direction and fits Server V2 principles 1, 3, 4 and 6 and the hard rule "never inside a page request". It also removes the root cause behind B7, A5's pacing problem and most of D. The Server V2 store is already its skeleton: `observations` (append-only fetched documents with `expires_at`), `entities`, `aliases`, `edges` with evidence class, `insights`, `job_runs`, `meta` data versions. Build on it; do not create a second database or a parallel schema.

### E1. Amendments to the idea

1. **"Only the worker makes external calls" needs a defined scope.** Three categories exist:
   - *Knowledge fetches* (MusicBrainz, ListenBrainz, Last.fm, Wikipedia, Wikidata, Deezer, Apple, Discogs, review sources, artwork): worker only. Enforce with a test that fails if a web module imports a provider client (an import-boundary test), not by convention.
   - *First-party and user-initiated control traffic*: Navidrome playback, streaming and cover proxying, slskd search and downloads, radio stream relay, Last.fm authentication and scrobbling, and the Settings "Test token" buttons stay in the web process. They are not knowledge; they are either first-party or an explicit user action.
   - *Unbounded exploration* (global search for things not in the library, "not in your library" results, genre pages). The knowledge base cannot hold the world. Use three tiers, but apply the request rule by data state:
     - **Tier 1, owned library:** worker-prefetched; build useful coverage progressively during cold start.
     - **Tier 2, neighbourhood:** similar artists, recommendation and lens candidates, and history artists; prefetch ahead of need.
     - **Tier 3, long tail:** when a requested entity or field has never been fetched, the web request may enqueue an interactive-priority job and wait only up to that route's existing deadline. If it is still unavailable, return the existing partial or incomplete response with an explicit pending state. Store the result for next time.
   - **Critical distinction:** if a usable value already exists but is stale, serve that last-known-good value immediately and enqueue refresh in the background. Do not make a user wait for a refresh merely because a TTL expired. The bounded Tier 3 wait is only for a genuinely missing or unfetched value requested interactively; it is not a stale-while-revalidate exception. Cached negative results and provider failures follow the separate rules in E3.
   - This keeps a single egress without turning every metadata miss into a blocking provider call or making search unusable.

2. **Separate rebuildable knowledge from irreplaceable state.** Two files: `knowledge.sqlite3` (observations, entities, edges, profiles, freshness ledger; the worker is the only writer; web opens it read-only; can be wiped and rebuilt) and a state file (dismissals, feedback, settings, acquisition state, radio, job history the owner cares about). **Owner decision (2026-11-06): dismissals move to the separate state file**, keyed by a stable card identity (not a row id), so a generation rebuild never costs the owner a decision (review item 7). Revisit D-026 consequence 4 (path and backup handling were left open) when wiring this.

3. **Store the fetch outcome, not just the data.** Add a freshness ledger table, for example `source_state(source, operation, key, outcome, observation_id, attempts, last_attempt_at, next_refresh_at, etag, last_modified)`, where `outcome` is `ok`, `not_found`, `error`, `blocked`. This is what lets the worker choose what to refresh, back off on failures, and lets the API say "pending" versus "does not exist". Check the schema against the migration runner (append-only migrations, v2 for this addition).

4. **Read models, not raw observations, on the request path.** Observations are provenance; they are too granular and too many to read per request. Add derived, generation-stamped profile tables (`artist_profile`, `album_profile`: bio and source, origin, active years, tags/genres, links, tracklist, ratings with counts, review links and short attributed excerpts, artwork references) rebuilt by derivation jobs. A request is then one indexed read. Facts, derivations and opinions stay in separate tables (Server V2 principle 4).

### E2. What the knowledge base holds

For each owned artist and album, plus the Tier 2 neighbourhood:

- **Identity:** MBIDs, Navidrome id, Wikidata/Discogs ids, aliases, resolution state (reuse the resolution ladder and `unresolved` queue).
- **Facts:** dates, tracklists with durations, editions, credits, area and lifespan, genres and tags with source.
- **Relationships (edges):** members, collaborators, producers and labels, influences (Wikidata), similar artists with the shared-tag and listener evidence the search code computes today, series, scene/area. Every edge carries evidence class and match quality; nothing inferred is rendered as a credit.
- **Context:** short bio with attribution, why-it-matters links (review links, anniversary and series context), popularity as "unknown" when absent.
- **Artwork:** URLs and licence/attribution in the database; image bytes in a content-addressed directory on disk (hash name, a few size variants made once by the worker). Do not store blobs in SQLite.
- **Coverage:** per entity and per field class, a state of `complete`, `pending`, `absent_at_source`, or `failed`, so completeness is measurable.

### E3. Freshness, absence and refresh policy

The default is **stale-while-revalidate**: if a usable value exists, return it immediately, even when stale, and enqueue a refresh. A stale value is not a missing value. A refresh must never delay a page request that can be answered from last-known-good data.

Use these distinct states for each source, operation and entity/field key:

| State | Meaning | Request behaviour | Worker behaviour |
|---|---|---|---|
| Fresh | A usable observation is within its freshness window | Serve it | No work |
| Stale | A usable observation exists but is past its refresh time | Serve last-known-good immediately | Enqueue refresh; do not block the request |
| Pending / never fetched | No usable observation and no authoritative negative result exists | Return partial data with an explicit pending state; for an explicit Tier 3 lookup only, allow the bounded interactive wait in E1 | Fetch in the appropriate priority lane |
| Not found / absent at source | The provider was queried successfully and confirmed no result for this key | Report absence, not pending; do not retry until the negative TTL expires | Retry after the negative TTL, or sooner only when identity/input changes |
| Error / blocked | A request failed, was rate-limited, or cannot currently be made | Preserve and serve any last-known-good value; otherwise report unavailable, not absent | Apply provider-specific backoff; do not turn an error into a negative cache entry |

The proposed source-state ledger in E1 should retain the outcome, attempt count, last attempt, next refresh time and observation reference. Not-found must remain distinct from error, blocked and never-fetched. Entity-level coverage such as pending, absent-at-source and failed is a read model of these outcomes, not a substitute for the source ledger.

Starting freshness windows (tune from measured change rates and provider limits; these are initial maximum ages, not a promise to refresh every row exactly on schedule):

| Class | Examples | Initial refresh window |
|---|---|---|
| Stable | MB relationships, release dates, tracklists, MBIDs | 90 days, or on a relevant library/identity change |
| Slow | Ratings, genres/tags, bios | 30–90 days |
| Moving | Listener and popularity counts, similar-artist lists | 7 days |
| Daily | New releases, daily lens inputs | 1 day |
| Negative | Confirmed not found | 7 days, doubling to 90 days on repeated confirmed misses |
| Error / blocked | Timeouts, 429, 5xx, policy or authentication blocks | Provider-specific short backoff with jitter; never treated as a miss |

**Freshness determines eligibility; relevance determines order.** Among eligible stale records, schedule refreshes using a bounded relevance score based on:
- library ownership (owned entities before unowned neighbourhood entities);
- recent additions or identity changes;
- listening relevance (recency and play count, with diminishing returns so one heavily played artist cannot consume the whole budget);
- recent user access or an explicit interactive request;
- age beyond the class freshness window.

Do not let this score change recommendation ranking or infer musical preference. It only decides which metadata to refresh first. Apply a maximum-age/ageing rule and reserved budget shares so low-relevance owned entities eventually refresh rather than starving forever. Record the policy inputs and queue age so the ordering can be inspected.

Library changes trigger targeted refresh: use Navidrome's change signals (getIndexes with ifModifiedSince, scan status) and the existing import-triggered resync hook to enqueue only new or changed albums, which should be filled first. An identity change invalidates only dependent observations/read models, not unrelated metadata.

### E4. Worker priority and fairness

Use one shared provider budget (database-backed, see A5) and four lanes:

1. **Interactive missing data:** an explicit request for a Tier 3 value that has never been fetched or has no usable observation. Only this lane may use the route's bounded wait; stale refreshes never do.
2. **New additions and identity changes:** newly imported albums/artists and changed MBIDs, so the library becomes useful quickly.
3. **Stale owned knowledge:** order by the relevance policy in E3 (recency, play count with diminishing returns, recent access and age beyond freshness).
4. **Neighbourhood and backfill:** Tier 2 expansion first, then the remaining long tail.

Each lane has a reserved share of the daily per-provider budget, with controlled borrowing when a lane is empty. A maximum queue-age/ageing rule prevents backfill from being starved indefinitely. The interactive lane is bounded per user/request and must not become a way to bypass provider limits.

**Cold-start ordering:** first create the local owned-entity/identity baseline without external calls; then enrich artists and albums in recent-listening order, followed by most-played entities not already covered, then the remaining owned library. New additions arriving during the backfill retain the second lane's priority. The order is a metadata scheduling policy only; it must not alter recommendation weights or visible recommendation order.

### E5. Migration, without a big bang

1. **Facade first.** Introduce one read interface (for example `KnowledgeReader.get_artist_profile(...)`, `get_album_profile(...)`) in an importable package, not in `navidrome_server.py` (D-016). Initially it reads the legacy caches and falls back to the legacy provider path.
2. **Backfill without refetching.** Import existing cache rows (`metadata_cache`, discovery and lens caches) as observations with `fetched_at` set to their original cached time. This removes most of the cold start for data already held.
3. **Worker fills the gaps.** Route by route, switch the reader to the knowledge base and move that route's provider calls into a worker handler. Remove the legacy call and the cache key only after the route's output is verified identical on fixtures. Order by user-visible latency: artist page, album page, artwork, search enrichment, recommendation enrichment, then the lens and insight providers.
4. **Retire the legacy caches** (`metadata_cache.py` and its callers) when nothing reads them. Adopting the migration runner for the remaining operational stores stays a separate decision.
5. **Fail closed on the boundary.** Add the import-boundary test only when the last web-side provider import is gone, so it can be enforced rather than waived.

### E6. Risks

- **Stale or wrong facts served confidently.** Mitigated by showing source and fetch time in the API, keeping `not_found` distinct from `pending`, and the existing rule "explainable or absent".
- **Single writer and SQLite.** One worker writer plus read-only web connections in WAL mode is a good fit; verify `busy_timeout`, short transactions, and that the worker never holds a write transaction across a network call. Plan for observation growth: add retention (keep the latest N observations per source/key; the append-only trigger blocks UPDATE, so retention is by DELETE and must be a deliberate, tested job).
- **Worker down means no fresh data, not an outage.** Reads continue from the last good data; the API and logs report knowledge age and queue depth.
- **Over-collecting.** A knowledge base invites fetching everything. Each field must have a consumer; collect only what a route, lens or insight reads (Server V2 principle 2: prove data exists before designing on it, and cut fields with low coverage).
- **Provider terms** (review item 9). Resolve before storing any text beyond facts, links and short attributed excerpts.

### E7. Acceptance and kill criteria

Targets are placeholders until slice 0 supplies baselines; set the numbers there and record them.

- Zero provider calls in web request handling for migrated routes, proven by the import-boundary test and by request-count assertions on route fixtures.
- Artist and album page knowledge reads meet a latency target set from the Phase 0 baseline, with no dependence on provider speed.
- Coverage report: percentage of owned artists and albums complete per field class, and age of the oldest stale-while-revalidate item, visible in the dashboard/logs.
- A new album added to Navidrome is fully populated, or explicitly pending with a known queue position, within a stated time.
- Wiping `knowledge.sqlite3` and rebuilding loses no owner decision.
- Aggregate provider traffic after cutover is at or below the pre-migration level on the same fixtures, with the 1 request/s MusicBrainz limit never exceeded across processes.
- **Kill or narrow** a field class if its coverage stays too low to be shown (Server V2 rule), or a route if the Tier 3 wait routinely exceeds its deadline and degrades the product.

### E8. MusicBrainz dump slice (owner-approved, grows with the library)

The MusicBrainz database dump is the bulk source for facts about owned entities and their neighbourhood; the MusicBrainz API remains the fallback for gaps and entities newer than the last imported dump (D-1, hybrid). The import writes directly into the **existing Server V2 knowledge database**. There is no separate slice database or parallel entity/edge schema.

**Repository implementation status at the baseline of this revision (2026-11-06):**
- **PR #810 merged:** streaming reader for the MusicBrainz database dump, pinned to schema sequence 31, with checksum verification. The measured core mbdump archive is 7,701,074,497 bytes; the optional cover-art archive is about 163 MB. Other large derived/edit exports are not required by the current loader.
- **PR #811 merged:** resumable, checksum-verified downloader with free-disk reserve checks and safe partial-file handling.
- **PR #812 merged:** bounded one-to-two-hop neighbourhood selector seeded from owned artist, release-group, release and recording MBIDs. At hop two it expands only recordings, releases, release groups and works; artists and labels reached at hop one are retained but not expanded into their catalogues. The selector enforces the entity cap and reports truncation.
- **PR #813 merged:** three-pass loader into the existing entities and edges tables, with source and dump-timestamp provenance, in a transaction that rolls back on loader failure.
- **PR #814 merged:** run_slice_import composes seed discovery, download, selection and load as one resumable job and records the approved budget measurements in job progress. No seeds means no download. A pre-load budget breach falls back to API-only without loading. A breach discovered only after loading is reported as over_budget; the loaded data is retained and is not automatically rolled back.
- **PR #815 merged:** card decisions are stored in the separate intelligence.state.sqlite3 file/schema, so rebuilding the knowledge database does not erase those decisions.
- **PR #816 merged:** it adds the KnowledgeReader facade, read-only web connections to both files, and slice metadata/status reporting. No user-facing route uses the reader yet; profile tables, legacy-cache fallback and the source-state ledger are still outstanding. The four required CI workflows passed on tested head `b49cbd1ea655bfecc8e8454a729ef42708ee517e`.

**Approved limits and what is still unverified:**
- Download budget: about 7.9 GB (core plus optional cover-art allowance); the current import job does not download cover art by default.
- Scratch ceiling: 25 GB.
- Permanent imported slice: under 2 GB.
- Import time: under 2 hours.
- Neighbourhood cap: 3,000,000 entities.
- The import is intended to run on the server, not on a client machine. Refresh cadence is manual or monthly at most until real resource use is known.
- The real 7.7 GB archive has not yet been downloaded and imported by this job. Actual download duration, peak scratch use, selector pass time, selected entity counts, edge counts, final database growth and total import time therefore remain unmeasured. Passing fixture tests and CI does not validate these real-world budgets.

**Operational and data rules:**
- **Membership is library-derived.** Seeds are owned MBIDs (artist, release group, release, recording). The current selector's hop and hub rules above are the starting policy; adjust them only from measured coverage gain versus size cost.
- **Library growth is incremental.** A new owned MBID must not wait for the next full dump. The worker should use the API fallback for that entity until a later dump contains it; this event-driven fill path still needs wiring and request-budget tests.
- **One store, one model.** The loader writes source-tagged facts into Server V2 entities and edges, with observations/provenance. Do not create separate dump-only tables or a second knowledge database. PR #816 adds the musicbrainz_slice metadata keys and slice_status for dump timestamp, schema sequence, load time, age and edge count.
- **Refresh safely.** The current loader is additive and idempotent; it does not yet remove entities/edges that disappear from a later dump. Before enabling recurring imports, define and test replacement/pruning semantics that preserve last-known-good data on failure. Do not describe the current loader as an atomic whole-slice swap.
- **Keep the fallback honest.** A missing relationship in a loaded slice is not proof that the relationship does not exist in MusicBrainz. Distinguish pending, no_relationships_in_slice, confirmed API not_found, and import failed/over_budget.
- **Measure the real run.** With the owner's explicit go-ahead for the large download, run the job on the server and record archive bytes/time, free and peak scratch, selector passes and per-type counts, selected IDs, edges loaded, final database growth, import duration, budget breaches and job outcome. Preserve the logs and exact code revision. If a pre-load limit is exceeded, do not load and use the documented API-only fallback; if a post-load limit is exceeded, stop further expansion and inspect the retained result before deciding whether to keep or narrow it.

**Acceptance:** the server job completes on the real archive within the approved budgets; reruns are safe; the slice answers owned-entity relationships without per-entity MusicBrainz API calls on deterministic fixtures; new library additions have a bounded API fallback until the next dump; and the reader reports dump age and honest coverage. If the real slice exceeds disk/time limits or adds little coverage, reduce hop scope or use API-only for the affected data rather than weakening the safety limits.

## Cold-start experience and progressive coverage

Cold start is a product state, not merely a worker performance concern. A new or rebuilt knowledge database must become useful before the full library is enriched, and clients must never imply that partial coverage is complete.

1. **Immediate local baseline:** ingest owned Navidrome identities and locally available metadata first. This stage makes the library browsable from local data and must not require external calls.
2. **High-value enrichment:** process the recently played artists/albums first, then the most-played entities, then the rest of the owned library. Deduplicate entities reached through multiple albums. New additions and explicit interactive missing-data requests use the higher-priority lanes in E4.
3. **Neighbourhood expansion:** only after owned-entity coverage is progressing, enrich the bounded Tier 2 neighbourhood. Keep long-tail exploration as queued work, not a full-world crawl.
4. **Progressive usefulness:** publish each entity/field group as soon as its own bounded job succeeds; do not hold all results until a whole artist, album or library batch completes. Keep last-known-good values visible during refresh.
5. **Honest client states:** expose whether knowledge is ready, partial, pending or unavailable. At entity/field level distinguish known, stale, pending, absent at source and failed. A missing value must not be silently rendered as a negative fact. Clients may show partial dossiers and a concise "still enriching" state rather than a blank page or a global spinner.
6. **Coverage and progress report:** provide counts and percentages for owned artists/albums by field group (identity, relationships/credits, tracklist/editions, biography/context, artwork), plus pending, stale, confirmed absent and failed counts; show queue depth/oldest age, last successful job, last dump date/age and any budget breach. Report per-group denominators so a field that is not applicable is not counted as missing. Keep provider errors and raw identifiers out of client-facing diagnostics.
7. **Completion estimates:** show an estimated remaining time only after enough real jobs have completed to calculate a stable throughput estimate. Label it approximate and derive it from eligible queued work and observed processing rate; otherwise show counts and "estimate not available". Never infer an ETA from the 1 request/second MusicBrainz limit alone.
8. **Recovery:** after restart, resume from durable checkpoints; after a database rebuild, preserve the separate owner-state file and show the same staged progress. A failed provider or stopped worker must leave existing knowledge usable and make the paused/pending state visible.

Cold-start acceptance:
- A fresh store exposes the local owned-entity baseline before external enrichment completes.
- Recently played and most-played entities are measurably enriched before the long tail, without starvation of the rest of the owned library.
- Progress counts reconcile with eligible work and field applicability; no entity is reported complete while required fields remain pending/failed.
- The client can distinguish partial, stale, pending, absent-at-source and failed states without claiming absence from a failed lookup.
- Restart/cancel/retry tests prove progress resumes without duplicate or destructive writes.
- The real-library cold-start duration and coverage curve are measured before setting a completion-time promise.

## Prioritized implementation roadmap

The sequence separates remaining measurement, worker lifecycle, route migration and horizontal scaling. It also records which MusicBrainz groundwork is already merged so the plan does not schedule the same implementation twice.

| Order | Slice | Current state and next deliverable | Why this order |
|---:|---|---|---|
| 0 | Baseline, inventories, decisions | **Partly complete.** Server V2 Phase 0 audit and MusicBrainz dump sizing are recorded. Still establish provider-call/cache counters, per-route provider wait, cold-start coverage/throughput baseline, background-task inventory and provider retention decisions. | Keeps remaining work evidence-led; the minimum counters and coverage measures are needed before tuning. |
| 1 | Shared provider limiter | **Not complete.** Implement a database-backed per-provider next_allowed_at and daily budget shared by every process; audit all provider call paths before starting a second process. | Prevents the web/worker split from multiplying provider traffic. |
| 2 | Worker foundation | **Partly complete.** intelligence/jobs has the execution runner; still add the durable dispatcher/scheduler, registry, worker entry point, atomic claims, fairness lanes, graceful shutdown and operational status. | Separates runtime responsibilities without duplicating domain logic. |
| 3 | Knowledge-store foundation | **Partly complete.** Server V2 store and entities/edges model exist; PR #815 split card decisions into intelligence.state.sqlite3. PR #816 merged the KnowledgeReader and read-only web connection; user-facing route integration remains outstanding. Still add the source-state ledger, profile/read models, legacy-cache fallback/backfill and verified backup handling for both files. | Creates one safe read path and preserves owner decisions before routes migrate. |
| 4 | Migrate background jobs | **Not complete.** Move insights, similar-artist precompute, lens refresh and legacy scheduler tasks into registered worker jobs one at a time; preserve their budgets and last-known-good semantics. | Removes web-startup side effects and improves recovery. |
| 5 | Migrate user-facing routes | **Not complete.** Migrate artist page, album page, artwork, search enrichment and recommendation enrichment to read through KnowledgeReader; move their knowledge fetches to worker handlers and remove legacy request-time provider calls only after fixture equivalence. | Takes provider latency out of page requests. |
| 6 | MusicBrainz slice and targeted batching | **Pipeline implemented; real run pending.** PRs #810–#814 merged the dump reader, downloader, neighbourhood selector, loader and orchestration job. Next: owner-authorized server run on the real archive, record all budget measurements, fix any real-data defects, define safe recurring-refresh/pruning semantics, and wire incremental API fallback for new library MBIDs. Re-evaluate B1/B2 only after measured slice coverage shows what remains uncovered. | Avoids rebuilding completed tooling and makes the remaining risk measurable. |
| 7 | Observability completion | **Not complete.** Add endpoint/provider/database/job metrics and a coverage/progress view. Pull the minimum provider counters, queue age, field coverage and cold-start measurements into slice 0 rather than waiting for this later slice. | Supports tuning, operational diagnosis and honest client progress. |
| 8 | Multi-process readiness | **Deferred gate.** Only consider additional Uvicorn workers after the shared limiter, worker ownership, read-only connections and cross-process coordination are proven and measurements show API queueing. | No demonstrated need yet; avoid premature concurrency. |

This is a proposed order, not an instruction to run provider traffic or deploy. The real MusicBrainz archive run requires the owner's explicit go-ahead. If new correctness, security, data-safety, or CI gaps appear, those take precedence.

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
- 2026-11-06 (revision 3): Records the owner's decisions that the MusicBrainz dump slice is in and grows with the library (new section E8, B1/B2 deferred behind it) and that dismissals move to a separate state file. Documentation only.
- 2026-11-06 (revision 2): Adds the review of revision 1 (assumptions and blind spots), section E (music knowledge base and single egress), a shared provider limiter requirement, a demoted section D, a downgraded B1, and a reordered roadmap. Documentation only; the repository facts cited (the metadata cache implementation, the process-local MusicBrainz pacing, `insights.dismissed_state`, D-1 and D-026) were read from the working tree at `ca72721d`, not from GitHub `main`; re-verify against `main` before acting. No application code, tests, provider traffic, publication, or deployment changed.

- 2026-11-06 (revision 4): Clarifies the stale-versus-missing request rule; makes refresh scheduling relevance-aware without changing recommendation ranking; adds progressive cold-start and measurable coverage/progress requirements; updates E8 and the roadmap to reflect merged MusicBrainz PRs #810–#816, including the still-unverified real archive run. Documentation revision only; no provider traffic, real archive download, publication or deployment.
