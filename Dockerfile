FROM python:3.12-slim

# Shown in the page rail; pass --build-arg APP_VERSION=<tag> when building a release image.
ARG APP_VERSION=
ENV APP_VERSION=${APP_VERSION}

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
COPY --chown=librarian:librarian discovery/ ./discovery/
COPY --chown=librarian:librarian integrations/ ./integrations/
COPY --chown=librarian:librarian recommendation/ ./recommendation/
COPY --chown=librarian:librarian settings/ ./settings/
COPY --chown=librarian:librarian static/ ./static/
COPY --chown=librarian:librarian recommendation_run_metrics.py musicbrainz_rating_client.py server_source_redaction.py navidrome_server.py navidrome_client.py metadata_cache.py recommendation_feedback.py music_tag_audit.py cassette.png ./

USER librarian

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
