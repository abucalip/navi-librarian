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

These probes read upstream data only. Local match quality, Navidrome playlist writes, completed imports, and execution of a local Troi recipe still need verification.

## 1. Shared track matching and acquisition

- Parse JSPF recording identifiers, preserve source order and repeated entries, and resolve against a server-side Navidrome song index. Match recording MBIDs first. For tracks with incomplete tagging, use normalized artist credit and title with corroborating duration or release information. Treat conflicting identities and ambiguous versions as unresolved.
- Return source identity and track position, display metadata, match state (owned, missing, or ambiguous), and song ID when owned. Include the acquisition state separately. Use existing batch metadata and library snapshot code where possible, with worker-owned refresh and existing provider pacing.
- Every unowned row exposes Download. Resolve an ambiguous or incomplete recording before submission, and give the row a clear explanation if acquisition cannot safely start. Reuse the existing track-acquisition service and import checks. The server resolves the track from its stored playlist and position, and rechecks ownership when clicked. Repeated clicks reuse the active acquisition.
- After verified import and Navidrome indexing, rematch affected playlists and update their playable entries in original order. Reconcile on later scans as well, including tracks added outside Discair.

## 2. Automatic Playlist Inbox

- The server worker periodically reads the configured profile's paginated Created for Me collection and fetches details for new or changed playlists. Include Daily Jams, Weekly Jams, Weekly Exploration, and other playlists returned by that collection. The other eligible source is scheduled Discair-generated Troi mixes. The clients receive these automatically. There is no URL import or authored-playlist browser.
- Store complete source snapshots in Discair. Save the owned subset as a private, managed Navidrome playlist. Persist a mapping from source identity to Navidrome playlist ID, including the occurrence order and last successful sync. Use the upstream playlist MBID for hosted sources and the recipe plus scheduled edition for local Troi sources. Verify whether Navidrome accepts empty playlists. If it does, create one at import. Otherwise keep the complete Discair snapshot and create the Navidrome copy when the first track becomes playable.
- Make sync idempotent across retries and worker restarts. Reconcile uncertain create outcomes before creating again. Update only copies managed by Discair and leave unrelated or independently copied playlists alone. Keep previous successful snapshots during upstream failures and respect existing provider budgets. An empty successful fetch gets a first-run state. An older snapshot remains playable and shows its generation date, including when weekly generation has stalled.
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

## Delivery order

1. Establish the shared matcher and the automatic Inbox through one end-to-end client slice, then bring it to the other clients. Verify private Navidrome sync and the full acquisition-to-playback loop before enabling scheduled imports.
2. Add single-seed Artist Radio. Fresh Releases can proceed independently after its overlap comparison.
3. Add the first scheduled Troi mix and cover-color browsing. Expand radio recipes after measuring playable coverage.

Each slice uses focused server and client tests, shared response fixtures, and a live check with a disposable Navidrome playlist where writes are involved. Keep credentials server-side and preserve the existing worker pacing and acquisition boundaries.

[ListenBrainz API](https://listenbrainz.readthedocs.io/en/latest/users/api/index.html) · [Playlists](https://listenbrainz.readthedocs.io/en/latest/users/api/playlist.html) · [Fresh Releases and cover color](https://listenbrainz.readthedocs.io/en/latest/users/api/misc.html) · [Troi](https://troi.readthedocs.io/en/latest/) · [LB Radio prompts](https://troi.readthedocs.io/en/latest/lb_radio.html)
