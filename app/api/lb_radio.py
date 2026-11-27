"""Authenticated ListenBrainz discovery mix read model (LB-18)."""

import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse

from app.api.dependencies import get_librarian
from app.api.search import owned_view
from app.services.similar_precompute import cache_reader
from discovery.lb_radio import mix_tracks, radio_seed
from discovery.search.network import LIMITER
from integrations.listenbrainz.client import request_headers
from integrations.listenbrainz.discovery_mix import MixClient, MixError, cache_key
from settings.service import listenbrainz_username

router = APIRouter()
_CLIENT = MixClient()
_ERROR_STATUS = {"rate_limited": 429, "timeout": 504, "upstream_error": 502, "busy": 503, "unavailable": 503}


@router.get("/api/discovery/lb-radio")
def discovery_mix(
    response: Response,
    artist_mbid: UUID | None = None,
    tag: str | None = Query(default=None, min_length=1, max_length=80),
    mode: Literal["easy", "medium", "hard"] = "easy",
    librarian=Depends(get_librarian),
):
    response.headers["Cache-Control"] = "no-store"
    try:
        seed, prompt = radio_seed(artist_mbid, tag)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    body = {"state": "unconfigured", "seed": seed, "mode": mode, "index_state": None,
            "total_count": 0, "owned_count": None, "tracks": []}
    settings = librarian._discovery_settings_read()
    token = str(settings.get("listenbrainz_token") or os.environ.get("LISTENBRAINZ_TOKEN", "")).strip()
    try:
        username = listenbrainz_username(lambda: settings)
    except ValueError:
        return body
    if not token:
        return body
    try:
        playlist = _CLIENT.fetch(
            key=cache_key(prompt, mode, username, token), prompt=prompt, mode=mode,
            read=cache_reader(librarian), write=librarian._discovery_write_list,
            headers=request_headers({"LISTENBRAINZ_TOKEN": token}), limiter=LIMITER,
        )
    except MixError as error:
        headers = {"Cache-Control": "no-store"}
        if error.code in ("rate_limited", "busy"):
            headers["Retry-After"] = "2"
        return JSONResponse({**body, "state": error.code}, status_code=_ERROR_STATUS[error.code], headers=headers)
    view = owned_view(librarian)
    return {**body, "state": "ready" if playlist.tracks else "empty", "index_state": view.state,
            **mix_tracks(playlist, view.data)}
