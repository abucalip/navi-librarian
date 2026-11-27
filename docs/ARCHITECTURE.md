# Architecture

Paths are relative to the repository root. Use this map to jump directly to source files and their focused `pytest` modules.

## Server

| Area | Start here | Focused tests |
| --- | --- | --- |
| HTTP and authentication | `app/main.py`, `app/api/auth.py`, `app/security/` | `tests/test_app_auth.py`, `tests/test_app_login_middleware.py` |
| Worker and scheduled jobs | `app/worker.py`, `app/worker_schedule.py`, `app/services/` | `tests/test_worker*.py` |
| Discovery, lenses, and feedback | `discovery/refresh.py`, `discovery/lenses.py`, `discovery/lens_service.py`, `discovery/pick_why.py`, `app/api/discovery.py`, `app/api/feedback.py` | `tests/test_api_discovery_injection.py`, `tests/test_api_feedback_routes.py` |
| Owned library index, search, artist/album pages | `discovery/search/`, `app/api/search.py`, `app/api/library.py` | `tests/test_api_search_routes.py`, `tests/test_album_inventory_snapshot.py` |
| Owned-first Artist Radio | `app/api/artist_radio.py`, `discovery/artist_radio.py`, `integrations/listenbrainz/artist_radio.py` | `tests/test_api_artist_radio.py`, `tests/test_artist_radio.py`, `tests/test_listenbrainz_artist_radio.py` |
| Playlist Inbox and rolling copies | `app/api/playlist_inbox.py`, `discovery/playlist_inbox.py`, `discovery/recording_match.py`, `discovery/playlist_sync.py`, `intelligence/store/playlist_editions.py` | `tests/test_api_playlist_inbox.py`, `tests/test_playlist_*.py` |
| Scheduled Playlist Inbox import | `app/services/discovery_schedule.py`, `app/services/playlist_inbox_refresh.py` | `tests/test_playlist_inbox_refresh.py` |
| Playlist Inbox downloads | `discovery/playlist_download.py`, `acquisition/track_service.py` | `tests/test_acquisition_track.py` |
| Managed playlist reconciliation | `app/services/playlist_reconcile.py` | `tests/test_playlist_reconcile.py` |
| Recommendation scoring and selection | `recommendation/listening_profile.py`, `recommendation/replay.py`, `discovery/personal_allocator.py`, `discovery/selection_policy.py` | `tests/test_recommendation*.py` |
| Acquisition, recovery, and import | `acquisition/orchestration.py`, `acquisition/lifecycle.py`, `acquisition/cleanup.py`, `acquisition/import_service.py`, `app/api/acquisitions.py` | `tests/test_acquisition_safety.py`, `tests/test_acquisition_cleanup.py`, `tests/test_acquisition_routes.py` |
| Knowledge store and enrichment | `intelligence/store/`, `intelligence/jobs/`, `intelligence/ingest/`, `intelligence/knowledge/`, `app/api/knowledge.py` | `tests/test_api_knowledge_routes.py` |
| Paths, insights, and artwork | `intelligence/graph/`, `intelligence/insights/`, `intelligence/artwork/`, `app/api/insights.py`, `app/api/artwork.py` | `tests/test_api_insights_routes.py`, `tests/test_api_artwork_routes.py` |
| Provider clients and request pacing | `integrations/provider_gate.py`, `integrations/navidrome/`, `integrations/listenbrainz/`, `integrations/musicbrainz/`, `integrations/slskd/` | `tests/test_provider_gate*.py` |
| Metadata sources and caching | `app/api/metadata.py`, `app/services/album_page_sources.py`, `app/services/album_review_sources.py`, `app/services/apple_artist_bio.py`, `app/services/layered_cache.py`, `discovery/search/cache.py` | `tests/test_album_page_sources.py`, `tests/test_album_review_sources.py`, `tests/test_apple_artist_bio.py` |
| Radio | `app/api/radio.py`, `integrations/radio/` | `tests/test_api_radio_routes.py` |
| Runtime diagnostics | `app/api/diagnostics.py`, `app/services/runtime_metrics.py`, `app/services/worker_heartbeat.py` | `tests/test_diagnostics*.py` |
| Settings | `settings/service.py`, `settings/persistence.py`, `settings/music_paths.py`, `app/api/settings.py` | `tests/test_settings*.py` |
| Docker updates | `app/api/docker_update.py`, `integrations/docker_release.py`, `scripts/docker_updater.py` | `tests/test_docker_update*.py` |
| Legacy orchestration (no additions, D-016) | `navidrome_server.py` | `tests/test_app_legacy_import_boundary.py` |

## Clients

| Area | Start here | Focused tests |
| --- | --- | --- |
| Web templates and UI | `app/templates/`, `static/app.js`, `static/radio.js`, `static/listening-room/` | `tests/test_*_ui_contract.py` |
| Web Playlist Inbox | `static/listening-room/playlist-inbox.js` | `tests/test_api_playlist_inbox.py` |
| Android app | Moved to [`abucalip/discair-android`](https://github.com/abucalip/discair-android) | — |
| macOS app | Moved to [`abucalip/discair-macos`](https://github.com/abucalip/discair-macos) | — |

## Tooling

| Area | Start here |
| --- | --- |
| Tests | `tests/` (always run focused `pytest <file>`, never full suite) |
| Store backup and sizing | `scripts/backup_stores.py`, `scripts/store_size_report.py` |
| Performance probes | `scripts/efficiency_inventory.py`, `scripts/efficiency_baseline.py`, `scripts/gate_spacing_check.py` |
| Design sources | `docs/design/` |
