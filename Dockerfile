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
COPY --chown=librarian:librarian navidrome_server.py acquisition_completion.py acquisition_import.py discovery_store.py discovery_refresh.py discovery_recommendations.py slskd_search.py slskd_quality.py cassette.png ./

USER librarian

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
