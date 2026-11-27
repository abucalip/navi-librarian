"""Authenticated owned-first Artist Radio HTTP adapter (LB-17)."""

import os
import time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response

from app.api.dependencies import get_librarian
from app.api.search import owned_view
from app.services.similar_precompute import cache_reader
from discovery.artist_radio import build_queue, radio_artists
from discovery.search.cache import SIMILAR_TTL_SECONDS, read_cached
from discovery.search.network import LIMITER
from discovery.search.normalize import normalize_key
from integrations.listenbrainz.artist_radio import top_recordings
from integrations.listenbrainz.client import request_headers
from settings.service import listenbrainz_username

router = APIRouter()
REQUEST_BUDGET = 12.0


@router.get("/api/artist-radio")
def artist_radio(
    response: Response,
    artist_mbid: UUID,
    familiarity: Literal["familiar", "explore", "deep_cuts"] = "familiar",
    count: int = Query(default=40, ge=25, le=50),
    librarian=Depends(get_librarian),
):
    response.headers["Cache-Control"] = "no-store"
    settings = librarian._discovery_settings_read()
    token = str(settings.get("listenbrainz_token") or os.environ.get("LISTENBRAINZ_TOKEN", "")).strip()
    body = {"state": "unconfigured", "artist_mbid": str(artist_mbid), "familiarity": familiarity,
            "requested_count": count, "index_state": None, "similar_state": "unavailable",
            "popularity_state": "unavailable", "tracks": []}
    try:
        listenbrainz_username(lambda: settings)
    except ValueError:
        return body
    if not token:
        return body
    view = owned_view(librarian)
    body["index_state"] = view.state
    if view.data is None:
        return {**body, "state": "index_unavailable"}
    seed = radio_artists(view.data, str(artist_mbid), [])
    if not seed:
        return {**body, "state": "empty"}
    read = cache_reader(librarian)
    key = f"similar:{artist_mbid}:{normalize_key(seed[0]['name'])}:deezer0:listenbrainz0"
    records = read_cached(read, key, time.time(), positive_ttl=SIMILAR_TTL_SECONDS)
    body["similar_state"] = "ready" if records is not None else "unavailable"
    artists = radio_artists(view.data, str(artist_mbid), records or [])
    deadline = time.monotonic() + REQUEST_BUDGET
    rankings = {}
    complete = True
    eligible_ids = {s["artist_id"] for s in view.data.songs}
    for artist in artists:
        if artist["id"] not in eligible_ids:
            continue
        mbid = artist.get("mbid")
        rows = top_recordings(
            mbid, read=read, write=librarian._discovery_write_list,
            headers=request_headers({"LISTENBRAINZ_TOKEN": token}), limiter=LIMITER,
            remaining=lambda: deadline - time.monotonic(),
        ) if mbid else None
        complete = complete and rows is not None
        rankings[artist["id"]] = rows or []
    tracks = build_queue(view.data, artists, rankings, familiarity=familiarity, count=count)
    return {**body, "state": "ready" if tracks else "empty",
            "popularity_state": "ready" if complete else "partial", "tracks": tracks}
