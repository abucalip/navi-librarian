FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NAVIDROME_LIBRARIAN_DATA_DIR=/data \
    NAVIDROME_MUSIC_DIR=/music \
    SLSKD_DOWNLOADS_DIR=/downloads

WORKDIR /app

RUN groupadd --gid 1000 librarian \
    && useradd --uid 1000 --gid 1000 --create-home librarian \
    && mkdir -p /data /music /downloads \
    && chown -R librarian:librarian /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=librarian:librarian app/ ./app/
COPY --chown=librarian:librarian integrations/ ./integrations/
COPY --chown=librarian:librarian static/ ./static/
COPY --chown=librarian:librarian recommendation_run_metrics.py musicbrainz_rating_client.py acquisition_candidate_queue.py server_source_redaction.py acquisition_progress_snapshots.py acquisition_progress_accounting.py acquisition_search_diagnostics.py discovery_new_releases.py lastfm_client.py listenbrainz_client.py listenbrainz_popularity.py navidrome_server.py navidrome_client.py data_directory.py music_paths.py acquisition_cleanup.py acquisition_recovery.py acquisition_source_switch.py acquisition_lifecycle.py acquisition_orchestration.py acquisition_import_service.py acquisition_request_coordinator.py acquisition_watcher.py acquisition_watcher_startup.py acquisition_state.py acquisition_completion.py acquisition_import.py acquisition_candidate_start.py acquisition_monitor_payload.py discovery_store.py service_settings.py settings_persistence.py metadata_cache.py discovery_refresh.py discovery_snapshot.py discovery_candidate_gathering.py discovery_tag_queries.py discovery_lb_tag_lane.py recommendation_diagnostics.py recommendation_replay.py discovery_recommendations.py discovery_mmr.py recommendation_cooldown.py recommendation_feedback.py discovery_allocation_contract.py discovery_personal_allocator.py discovery_recommendation_payload.py discovery_list_payload.py discovery_classics_ratings.py discovery_classics_genres.py discovery_classics_candidates.py discovery_deep_dive_candidates.py listening_profile.py discovery_library_snapshot.py music_tag_audit.py cassette.png ./

USER librarian

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
