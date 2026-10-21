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
COPY --chown=librarian:librarian acquisition/ ./acquisition/
COPY --chown=librarian:librarian integrations/ ./integrations/
COPY --chown=librarian:librarian recommendation/ ./recommendation/
COPY --chown=librarian:librarian settings/ ./settings/
COPY --chown=librarian:librarian static/ ./static/
COPY --chown=librarian:librarian recommendation_run_metrics.py musicbrainz_rating_client.py server_source_redaction.py acquisition_progress_snapshots.py acquisition_progress_accounting.py discovery_new_releases.py navidrome_server.py navidrome_client.py acquisition_cleanup.py acquisition_recovery.py acquisition_import_service.py acquisition_watcher.py acquisition_watcher_startup.py acquisition_completion.py acquisition_import.py acquisition_monitor_payload.py discovery_store.py metadata_cache.py discovery_refresh.py discovery_snapshot.py discovery_candidate_gathering.py discovery_tag_queries.py discovery_lb_tag_lane.py discovery_recommendations.py discovery_mmr.py recommendation_cooldown.py recommendation_feedback.py discovery_allocation_contract.py discovery_personal_allocator.py discovery_recommendation_payload.py discovery_list_payload.py discovery_classics_ratings.py discovery_classics_genres.py discovery_classics_candidates.py discovery_deep_dive_candidates.py discovery_library_snapshot.py music_tag_audit.py cassette.png ./

USER librarian

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
