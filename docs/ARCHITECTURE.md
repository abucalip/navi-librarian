# Architecture

Paths are relative to the repository root.

## Server

| Area | Start here |
| --- | --- |
| HTTP and authentication | `app/main.py`, `app/api/`, `app/security/` |
| Worker and scheduled jobs | `app/worker.py`, `app/worker_schedule.py`, `app/services/` |
| Discovery, lenses, and feedback | `discovery/` |
| Owned library index, search, and artist and album pages | `discovery/search/`, `app/api/search.py`, `app/api/library.py` |
| Playlist Inbox and rolling copies | `app/api/playlist_inbox.py`, `discovery/playlist_inbox.py`, `discovery/recording_match.py`, `discovery/playlist_sync.py`, `intelligence/store/playlist_editions.py` |
| Scheduled Playlist Inbox import | `app/services/discovery_schedule.py` runs `app/services/playlist_inbox_refresh.py` to publish ListenBrainz editions and sync their private copies against an idle Navidrome inventory. |
| Playlist Inbox downloads | `discovery/playlist_download.py` verifies tracks against the current Navidrome inventory, resolves missing album metadata, and delegates to `acquisition/track_service.py`. |
| Managed playlist reconciliation | `app/services/playlist_reconcile.py` checks scan status, builds a fresh song inventory for the same Navidrome target, and uses the shared playlist sync lock and ownership checks. |
| Recommendation scoring and selection | `recommendation/` |
| Acquisition, recovery, and import | `acquisition/` |
| Knowledge store and enrichment | `intelligence/store/`, `intelligence/jobs/`, `intelligence/ingest/`, `intelligence/knowledge/` |
| Paths, insights, and artwork | `intelligence/graph/`, `intelligence/insights/`, `intelligence/artwork/` |
| Provider clients and request pacing | `integrations/`, `integrations/provider_gate.py` |
| Metadata sources and caching | `app/api/metadata.py`, `app/services/album_page_sources.py`, `app/services/album_review_sources.py`, `app/services/apple_artist_bio.py`, `app/services/layered_cache.py`, `discovery/search/cache.py` |
| Runtime diagnostics | `app/api/diagnostics.py`, `app/services/runtime_metrics.py`, `app/services/worker_heartbeat.py` |
| Settings | `settings/` |
| Docker updates | `app/api/docker_update.py`, `integrations/docker_release.py`, `scripts/docker_updater.py` |
| Legacy orchestration | `navidrome_server.py` |

## Clients

| Area | Start here |
| --- | --- |
| Web templates and UI | `app/templates/`, `static/app.js`, `static/radio.js`, `static/listening-room/` |
| Android app | `android/app/src/main/kotlin/app/discair/` |
| Android screens and themes | Under the Android app path, use `ui/<feature>/` for screens and theme variants, `ui/common/` for shared controls and shells, and `ui/theme/` for palettes and theme selection. |
| macOS app | `macos/Sources/DiscairApp/`, `macos/Sources/DiscairUI/` |
| macOS playback, models, and API clients | `macos/Sources/DiscairAudio/`, `macos/Sources/DiscairCore/`, `macos/Sources/DiscairLibrarian/`, `macos/Sources/DiscairNavidrome/` |

## Tooling

| Area | Start here |
| --- | --- |
| Tests | `tests/`, `android/app/src/test/`, `macos/Tests/` |
| Store backup and sizing | `scripts/backup_stores.py`, `scripts/store_size_report.py` |
| Performance probes | `scripts/efficiency_inventory.py`, `scripts/efficiency_baseline.py`, `scripts/gate_spacing_check.py` |
| Design sources | `docs/design/` |
