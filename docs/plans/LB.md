# ListenBrainz discovery and playlists

**Status:** Implementation plan · 2026-11-24

Discair will automatically bring ListenBrainz Created for Me playlists and Discair-generated Troi mixes into Navidrome. In Discair, each mix shows its full track list, plays owned tracks in order, and gives each unowned track a Download action. The same server-side recording matcher will support Artist Radio. Discover will also gain personal and upcoming releases and a cover-color browser.

## Probe evidence

| Check | Result |
| --- | --- |
| Token and Created for Me | Token validation succeeded. The configured profile returned HTTP 200 with zero playlists on two reads. A separate public profile returned Daily Jams, Weekly Jams, and Weekly Exploration in the initial probe. The weekly jobs were about 93 days old when checked. |
| LB Radio | Authenticated jazz-tag, Portishead artist MBID, and personal unlistened-recommendation prompts each returned 50 JSPF tracks. An unparenthesized artist-name prompt returned 400. Use structured seeds and prefer artist MBIDs. |
| Fresh Releases | The personal 30-day query returned 38 entries (16 albums, 18 singles, 4 EPs). The global seven-day query returned 1,879 entries. Both are raw counts before deduplication or ownership matching. |
| Cover color | A blue swatch query returned 12 releases with cover art IDs, color distances, and recording data. |

The owner followed `troi-bot` after the probe. Following the bot opts the account into Daily Jams. Weekly Jams and Weekly Exploration are generated automatically from listening history when upstream generation is running. Check Created for Me after the next Daily Jams run and use the real playlist to verify import if it appears. Keep the fixture for repeatable tests. [ListenBrainz update schedule](https://listenbrainz.readthedocs.io/en/latest/general/data-update-intervals.html)

These probes read upstream data only. Local match quality, Navidrome playlist writes, completed imports, and execution of a local Troi recipe still need verification.

## 1. Shared track matching and acquisition

- Parse JSPF recording identifiers, preserve source order and repeated entries, and resolve against a server-side Navidrome song index. Match recording MBIDs first. For tracks with incomplete tagging, use normalized artist credit and title with corroborating duration or release information. Treat conflicting identities and ambiguous versions as unresolved.
- Return source identity and track position, display metadata, match state (owned, missing, or ambiguous), and song ID when owned. Include the acquisition state separately. Use existing batch metadata and library snapshot code where possible, with worker-owned refresh and existing provider pacing.
- Every unowned row exposes Download. Resolve an ambiguous or incomplete recording before submission, and give the row a clear explanation if acquisition cannot safely start. Reuse the existing track-acquisition service and import checks. The server resolves the track from its stored playlist and position, and rechecks ownership when clicked. Repeated clicks reuse the active acquisition.
- After verified import and Navidrome indexing, rematch affected playlists and update their playable entries in original order. Reconcile on later scans as well, including tracks added outside Discair.

## 2. Automatic Playlist Inbox

- The server worker periodically reads the configured profile's paginated Created for Me collection and fetches details for new or changed playlists. Include Daily Jams, Weekly Jams, Weekly Exploration, and other playlists returned by that collection. The other eligible source is scheduled Discair-generated Troi mixes. The clients receive these automatically. There is no URL import or authored-playlist browser.
- Store complete source snapshots in Discair. Save the owned subset as a private, managed Navidrome playlist. Persist a mapping from source identity to Navidrome playlist ID, including the occurrence order and last successful sync. Use the upstream playlist MBID for hosted sources and the recipe plus scheduled edition for local Troi sources. Verify whether Navidrome accepts empty playlists. If it does, create one at import. Otherwise keep the complete Discair snapshot and create the Navidrome copy when the first track becomes playable.
- Make sync idempotent across retries and worker restarts. Reconcile uncertain create outcomes before creating again. Update only copies managed by Discair and leave unrelated or independently copied playlists alone. Keep previous successful snapshots during upstream failures and respect existing provider budgets. An empty successful fetch explains that ListenBrainz has yet to return a playlist and links to `troi-bot` for Daily Jams opt-in. An older snapshot remains playable and shows its generation date, including when weekly generation has stalled.
- Expose the inbox and source details in web, Android, and macOS playlist surfaces. Show source, generation date, playable count, ordered track rows, playback, and per-track Download with progress and retry. Ordinary Navidrome clients see the playable subset. Use existing queue and acquisition controls in Discair.

**Acceptance:** Sync a representative generated fixture twice and after a simulated interrupted write. Confirm a single private Navidrome copy, source order including repeats, and a visible missing track that joins the playlist after successful acquisition and indexing. Exercise zero playlists, zero owned tracks, timeouts, and stale weekly editions. Use a redacted generated-playlist fixture while the configured profile has no upstream entries.

## 3. Artist Radio

- Add Start Artist Radio on artist pages, then tag seeds in Discover. Use a finite batch and play the owned subset through the existing queue. Surface the playable count and a clear empty state. Use the configured server token and encode seeds on the server. Cache briefly per seed and mode and coalesce duplicate requests.
- Test Familiar, Explore, and Deep cuts against ListenBrainz easy, medium, and hard. Add weighted seeds, saved recipes, and Continue this mix after single-seed generation has acceptable local coverage. Check continuation using a playlist seed plus a related artist or tag seed so it can introduce tracks beyond the source mix.
- Put generated mixes under Discover or the artist page, distinct from the live internet radio player. Preserve ordinary playback, queue, and scrobbling behavior.

**Acceptance:** Test artist ID, tag, and recommendation seeds against representative library sections. Report playable coverage, ambiguous matches, artist repetition, and wrong versions. Verify empty, invalid-token, throttled, and upstream failure responses leave an existing queue intact.

## 4. Fresh Releases

- Extend the existing New Releases view with From your ListenBrainz listening and Coming soon, alongside the current library-artist results. Use the personal feed for taste-based results. Treat the broad global feed as optional discovery input and filter and page it server-side.
- Group editions by release-group MBID, preserve useful release precision and provenance, join ownership using the library index, and label Owned, Out now, or Upcoming. Offer album, EP, and single filters. Use the existing album detail and acquisition flow. Upcoming items can be browsed even when the release is unavailable.
- Cache bounded queries and retain the current library-based view when ListenBrainz is unavailable. Compare overlap and unique eligible releases with the existing MusicBrainz list. Consider a watchlist or Friday digest after evaluating coverage.

**Acceptance:** Verify duplicate editions, partial dates, dates near the local day boundary, type filters, and already-owned releases across clients.

## 5. Discair-generated Troi mixes

- Run a focused Troi evaluation in the server worker. Start with Rediscover your library, blending older favorites with neglected owned tracks. Compare coverage and variety with existing Discair selection. Pin and assess the dependency before enabling a scheduled recipe, including whether its inputs rely on experimental endpoints.
- Send successful output through the same snapshot and Navidrome sync as Created for Me, with clear source attribution. Label local editions separately from hosted ListenBrainz playlists. Keep the prior edition when generation fails or yields an unusable result. Evaluate World Trip and artist deep cuts after the first recipe passes.

**Acceptance:** With fixed recipe inputs, verify track eligibility and a repeatable edition identity. A rerun must update the same edition, and a provider outage must leave the prior playlist playable.

## 6. Browse by cover color

- Add a swatch-led Discover view on web, Android, and macOS. A server endpoint validates the color, caps the result count, caches by normalized color, and uses ListenBrainz similarity order. Show cover, album, artist, and ownership. Open owned results in the library and other results on the existing album page.
- Use named swatches, keyboard and screen-reader labels, and a visible selection indicator. Fetch on selection and show useful loading, empty, and retry states.

**Acceptance:** Verify color normalization, result bounds, missing art, navigation for owned and unowned releases, and accessible swatch selection.

## Implementation slices

Each row is one PR. Start from current main once the listed dependencies have merged. Use the listed acceptance check as the stopping point and carry any follow-on work into its own slice. Server slices use focused tests and sanitized fixtures. Client slices use the merged server contract and test one client only. Slices with no shared dependency can proceed independently.

### Playlist Inbox and shared recording matching

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-01 · Parse playlist tracks | — | Add a JSPF parser and a sanitized generated-playlist fixture. Verify recording URLs, missing identifiers, repeated tracks, order, and generation date. |
| LB-02 · Match exact recording IDs | LB-01 | Build the recording MBID lookup from Navidrome song data. Verify ordered owned and missing results, including duplicate playlist occurrences. |
| LB-03 · Match untagged tracks | LB-02 | Add conservative artist/title fallback with release or duration evidence. Fixtures must distinguish a safe match from ambiguous live, studio, and remastered versions. |
| LB-04 · Read Created for Me | LB-01 | Add the paced upstream adapter for listing and fetching generated playlists. Verify pagination, an empty account, and failed detail reads. |
| LB-05 · Store playlist editions | LB-04 | Persist full source snapshots by upstream ID, with generation and refresh times. Verify retry, repeat import, and retention of previous data after a partial refresh. |
| LB-06 · Read the Inbox | LB-03, LB-05 | Add authenticated list and detail endpoints with shared fixtures for owned, missing, ambiguous, empty, and stale results. Verify that the owned IDs retain source order. |
| LB-07 · Save private copies | LB-06 | Create the playable subset in Navidrome and record the managed ID. Check empty-playlist behavior with a disposable playlist. Verify that a retry after an uncertain create produces a single copy and never adopts an unrelated playlist. |
| LB-08 · Reconcile managed copies | LB-07 | Update the playable subset when the Navidrome library changes. Verify that a newly indexed track is inserted in source order, repeats survive, and unrelated playlists stay untouched. |
| LB-09 · Download an Inbox track | LB-06 | Add the server action for a stored track occurrence. Reuse existing acquisition and status handling. Verify current ownership, safe refusal of unresolved identity, and deduplication of simultaneous requests. |
| LB-10 · Schedule hosted import | LB-08, LB-12 | Register one worker job to refresh hosted editions and reconcile copies. Prove a manual run on a disposable Navidrome playlist, including the download-to-index-to-playlist loop. Use a real Daily Jams edition if present and the fixture for automated tests. Enable recurring import only after the live check. |
| LB-11 · Web Inbox playback | LB-06 | Add the generated shelf and track detail with source date, owned count, empty state, and ordered playback. Check a mixed and a zero-owned playlist. |
| LB-12 · Web Inbox downloads | LB-09, LB-11 | Connect per-track Download, status and retry. Verify an unresolved row explains why acquisition cannot start and a completed track becomes playable after refresh. |
| LB-13 · Android Inbox playback | LB-06 | Add the generated shelf and track detail with source date, owned count, empty state, and ordered playback. Check a mixed and a zero-owned playlist. |
| LB-14 · Android Inbox downloads | LB-09, LB-13 | Wire per-track Download, status and retry to the existing acquisition UI. Verify unresolved and newly playable rows. |
| LB-15 · macOS Inbox playback | LB-06 | Add the generated shelf and track detail with source date, owned count, empty state, and ordered playback. Check a mixed and a zero-owned playlist. |
| LB-16 · macOS Inbox downloads | LB-09, LB-15 | Wire per-track Download, status and retry to the existing acquisition UI. Verify unresolved and newly playable rows. |

### Artist Radio

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-17 · Generate owned queues | LB-03 | Add authenticated generation for artist MBID and tag seeds, typed mode, short caching, and request coalescing. Verify empty, auth, throttle, and error responses. Record coverage and wrong-version matches for representative artist, tag, and recommendation seeds before expanding the UI. |
| LB-18 · Web Artist Radio | LB-17 | Add Start Artist Radio with existing queue controls. Verify generation failure or zero playable tracks preserves the queue. |
| LB-19 · Android Artist Radio | LB-17 | Add the artist-page action and playable coverage state. Verify failure and zero matches preserve the queue. |
| LB-20 · macOS Artist Radio | LB-17 | Add the artist-page action and playable coverage state. Verify failure and zero matches preserve the queue. |
| LB-21 · Web tag and depth controls | LB-18 | Add tag seeds in Discover and the three familiarity modes. Verify seed/mode selection and playback with the same server contract. |
| LB-22 · Android tag and depth controls | LB-19 | Add tag seeds and the three modes to Android Discover. Verify selection and queue behavior. |
| LB-23 · macOS tag and depth controls | LB-20 | Add tag seeds and the three modes to macOS Discover. Verify selection and queue behavior. |
| LB-24 · Weighted prompts | LB-17 | Extend the server contract with structured weighted seeds once single-seed queues have acceptable coverage. Verify bounds, encoding, order, and a mixed artist/tag result. |
| LB-25 · Saved radio recipes | LB-24 | Persist and expose reusable validated seed combinations through the server API. Verify save, reopen, and regeneration of a queue from a recipe. |
| LB-26 · Playlist continuation | LB-24, LB-06 | Accept an Inbox edition as a continuation seed with a related artist or tag. Verify that the resulting queue can include playable tracks beyond the source playlist. |
| LB-27 · Web radio recipes | LB-21, LB-25, LB-26 | Add the recipe picker and Continue this mix. Verify both entry points use the existing queue. |
| LB-28 · Android radio recipes | LB-22, LB-25, LB-26 | Add the recipe picker and Continue this mix. Verify both entry points use the existing queue. |
| LB-29 · macOS radio recipes | LB-23, LB-25, LB-26 | Add the recipe picker and Continue this mix. Verify both entry points use the existing queue. |

### Fresh Releases

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-30 · Fetch and compare release feeds | — | Add bounded, cached personal and global reads. Capture an aggregate comparison of overlap, unique eligible entries, and dates against the existing MusicBrainz list. Keep the global feed optional. |
| LB-31 · Serve personal and upcoming releases | LB-30 | Add the Discover read model with release-group deduplication, date precision, ownership, and album/EP/single filters. Verify timezone boundaries and provider failure alongside the existing library feed. |
| LB-32 · Web Fresh Releases | LB-31 | Add personal and upcoming views to New Releases. Verify type filters, ownership, and existing album navigation. |
| LB-33 · Android Fresh Releases | LB-31 | Add the views and filters to Android Discover. Verify upcoming and owned entries open the right destination. |
| LB-34 · macOS Fresh Releases | LB-31 | Add the views and filters to macOS Discover. Verify upcoming and owned entries open the right destination. |

### Discair-generated Troi mixes

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-35 · Evaluate Rediscover your library | LB-02 | Add a reproducible, unscheduled recipe evaluation. Record dependency version, external inputs, playable coverage, and variety compared with existing Discair selection. Verify eligibility against fixed inputs. |
| LB-36 · Save Troi editions to the Inbox | LB-08, LB-35 | Route the first supported recipe through the shared snapshot and managed-copy services. Use recipe plus scheduled edition as identity. Verify retry, source labels, and reuse of the same Navidrome copy. |
| LB-37 · Schedule the first Troi mix | LB-10, LB-36 | Register the recipe in the worker with its own cadence. Verify an upstream failure or empty generation retains the last playable edition and that clients display its Troi attribution. |

### Browse by cover color

| Slice | Depends on | PR scope and acceptance |
| --- | --- | --- |
| LB-38 · Serve cover-color results | — | Add a bounded, cached server read by normalized color. Preserve similarity order, join ownership, and test missing art and malformed input. |
| LB-39 · Web cover-color browser | LB-38 | Add accessible swatches and result cards in Discover. Verify keyboard selection and owned/unowned album navigation. |
| LB-40 · Android cover-color browser | LB-38 | Add the swatches and results in Android Discover. Verify screen-reader labels, selection, and retry. |
| LB-41 · macOS cover-color browser | LB-38 | Add the swatches and results in macOS Discover. Verify keyboard and VoiceOver selection, retry, and album navigation. |

Start with LB-01. Fresh Releases and cover color can begin independently. Use the web Inbox as the first end-to-end client for the live check before enabling recurring import. World Trip, artist deep cuts, a release watchlist, and a Friday digest remain follow-up candidates to scope after the first relevant feature is evaluated.

[ListenBrainz API](https://listenbrainz.readthedocs.io/en/latest/users/api/index.html) · [Playlists](https://listenbrainz.readthedocs.io/en/latest/users/api/playlist.html) · [Fresh Releases and cover color](https://listenbrainz.readthedocs.io/en/latest/users/api/misc.html) · [Troi](https://troi.readthedocs.io/en/latest/) · [LB Radio prompts](https://troi.readthedocs.io/en/latest/lb_radio.html)
