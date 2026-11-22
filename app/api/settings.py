"""Settings API routes.

These handlers delegate configuration and connection behavior to ``settings.service``
with the librarian's settings store and music directory; this module only adapts HTTP payloads.
"""
import json
import os

import httpx

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.utils import parse_result
from integrations.slskd.client import test_connection as _test_slskd_connection
from settings.service import (
    get_listenbrainz_settings as _get_listenbrainz_settings,
    get_navidrome_settings as _get_navidrome_settings,
    get_slskd_settings as _get_slskd_settings,
    set_listenbrainz_settings as _set_listenbrainz_settings,
    set_navidrome_settings as _set_navidrome_settings,
    set_slskd_settings as _set_slskd_settings,
    test_listenbrainz_connection as _test_listenbrainz_connection,
    test_navidrome_connection as _test_navidrome_connection,
    discogs_token_and_source as _discogs_token_and_source,
    get_discogs_settings as _get_discogs_settings,
    set_discogs_settings as _set_discogs_settings,
    test_discogs_connection as _test_discogs_connection,
    get_automatic_refill_settings as _get_automatic_refill_settings,
    get_library_resync_settings as _get_library_resync_settings,
    get_discovery_mode_settings as _get_discovery_mode_settings,
    set_discovery_mode_settings as _set_discovery_mode_settings,
    get_star_seed_settings as _get_star_seed_settings,
    set_star_seed_settings as _set_star_seed_settings,
    set_library_resync_settings as _set_library_resync_settings,
    get_recommendation_diversity_settings as _get_recommendation_diversity_settings,
    set_automatic_refill_settings as _set_automatic_refill_settings,
    set_recommendation_diversity_settings as _set_recommendation_diversity_settings,
)

router = APIRouter()


@router.get("/api/settings/automatic-refill")
def get_automatic_refill_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_automatic_refill_settings(librarian._discovery_settings_read))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read automatic refill settings.")


@router.put("/api/settings/automatic-refill")
def set_automatic_refill_settings(payload: dict, librarian=Depends(get_librarian)):
    value = payload.get("automatic_refill_enabled")
    if type(value) is not bool:
        raise HTTPException(status_code=400, detail="automatic_refill_enabled must be a boolean.")
    try:
        result = parse_result(_set_automatic_refill_settings(librarian._discovery_settings_write, value))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid automatic refill setting."))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save automatic refill settings.")


@router.get("/api/settings/library-resync")
def get_library_resync_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_library_resync_settings(librarian._discovery_settings_read))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read library resync settings.")


@router.put("/api/settings/library-resync")
def set_library_resync_settings(payload: dict, librarian=Depends(get_librarian)):
    value = payload.get("library_resync_after_import")
    if type(value) is not bool:
        raise HTTPException(status_code=400, detail="library_resync_after_import must be a boolean.")
    try:
        result = parse_result(_set_library_resync_settings(librarian._discovery_settings_write, value))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid library resync setting."))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save library resync settings.")


@router.get("/api/settings/discovery-mode")
def get_discovery_mode_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_discovery_mode_settings(librarian._discovery_settings_read))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read discovery mode settings.")


@router.put("/api/settings/discovery-mode")
def set_discovery_mode_settings(payload: dict, librarian=Depends(get_librarian)):
    value = payload.get("discovery_mode")
    try:
        result = parse_result(_set_discovery_mode_settings(librarian._discovery_settings_write, value))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid discovery mode."))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save discovery mode settings.")


@router.get("/api/settings/star-seed")
def get_star_seed_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_star_seed_settings(librarian._discovery_settings_read))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read star seed settings.")


@router.put("/api/settings/star-seed")
def set_star_seed_settings(payload: dict, librarian=Depends(get_librarian)):
    value = payload.get("star_seed_enabled")
    if type(value) is not bool:
        raise HTTPException(status_code=400, detail="star_seed_enabled must be a boolean.")
    try:
        result = parse_result(_set_star_seed_settings(librarian._discovery_settings_write, value))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid star seed setting."))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save star seed settings.")


@router.get("/api/settings/recommendation-diversity")
def get_recommendation_diversity_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_recommendation_diversity_settings(librarian._discovery_settings_read))
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not read Recommendation diversity settings.",
        )


@router.put("/api/settings/recommendation-diversity")
def set_recommendation_diversity_settings(payload: dict, librarian=Depends(get_librarian)):
    value = payload.get("recommendation_diversity")
    if type(value) is not int or not 0 <= value <= 100:
        raise HTTPException(
            status_code=400,
            detail="recommendation_diversity must be an integer from 0 to 100.",
        )
    try:
        result = parse_result(
            _set_recommendation_diversity_settings(
                librarian._discovery_settings_write, value
            )
        )
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Invalid Recommendation diversity setting."),
            )
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Could not save Recommendation diversity settings.",
        )


@router.get("/api/settings/navidrome")
def get_navidrome_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_navidrome_settings(librarian._discovery_settings_read, librarian.MUSIC_DIR))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read Navidrome settings.")


@router.put("/api/settings/navidrome")
def set_navidrome_settings(payload: dict, librarian=Depends(get_librarian)):
    try:
        result = parse_result(_set_navidrome_settings(
            librarian._discovery_settings_read,
            librarian._discovery_settings_write,
            lambda: librarian.MUSIC_DIR,
            librarian._set_music_dir,
            navidrome_url=str(payload.get("navidrome_url") or ""),
            username=str(payload.get("username") or ""),
            password=str(payload.get("password") or ""),
            music_library_path=str(payload.get("music_library_path") or ""),
        ))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid settings"))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save Navidrome settings.")


@router.post("/api/settings/navidrome/test")
def test_navidrome_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_test_navidrome_connection(librarian.api_call, json.dumps))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the Navidrome connection.")


@router.get("/api/settings/listenbrainz")
def get_listenbrainz_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_listenbrainz_settings(
            librarian._discovery_settings_read, librarian._listenbrainz_username()
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read ListenBrainz settings.")


@router.put("/api/settings/listenbrainz")
def set_listenbrainz_settings(payload: dict, librarian=Depends(get_librarian)):
    try:
        result = parse_result(_set_listenbrainz_settings(
            librarian._discovery_settings_write,
            username=str(payload.get("username") or ""), token=str(payload.get("token") or "")))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid settings"))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save ListenBrainz settings.")


@router.post("/api/settings/listenbrainz/test")
def test_listenbrainz_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_test_listenbrainz_connection(librarian._listenbrainz_username, httpx.get, json.dumps))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the ListenBrainz connection.")


@router.get("/api/settings/slskd")
def get_slskd_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_slskd_settings(
            librarian._discovery_settings_read, librarian.MUSIC_DIR, librarian._DISCOVERY_SETTINGS_DEFAULTS
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read slskd settings.")


@router.put("/api/settings/slskd")
def set_slskd_settings(payload: dict, librarian=Depends(get_librarian)):
    url = str(payload.get("slskd_url") or "")
    api_key = str(payload.get("api_key") or "")
    quality = payload.get("quality_priority")
    if quality is None:
        quality = ["mp3_320", "mp3_193_319", "mp3_192", "flac_cd", "flac_16_44", "flac_hires"]
    try:
        result = parse_result(_set_slskd_settings(
            librarian._discovery_settings_read,
            librarian._discovery_settings_write,
            lambda: librarian.MUSIC_DIR,
            librarian._set_music_dir,
            librarian._DISCOVERY_SETTINGS_DEFAULTS,
            slskd_url=url,
            api_key=api_key,
            quality_priority_json=json.dumps(quality),
            slskd_downloads_path=(
                str(payload["slskd_downloads_path"]).strip()
                if "slskd_downloads_path" in payload
                else None
            ),
            music_library_path=(
                str(payload["music_library_path"]).strip()
                if "music_library_path" in payload
                else None
            ),
        ))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid settings"))
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save slskd settings.")


@router.post("/api/settings/slskd/test")
def test_slskd_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_test_slskd_connection(librarian._slskd_config))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the slskd connection.")


@router.get("/api/settings/discogs")
def get_discogs_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(_get_discogs_settings(librarian._discovery_settings_read, os.environ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read Discogs settings.")


@router.put("/api/settings/discogs")
def set_discogs_settings(payload: dict, librarian=Depends(get_librarian)):
    token = payload.get("token")
    if not isinstance(token, str):
        raise HTTPException(status_code=400, detail="token must be a string.")
    try:
        result = parse_result(_set_discogs_settings(
            librarian._discovery_settings_read, librarian._discovery_settings_write, os.environ, token,
        ))
        if isinstance(result, dict) and not result.get("ok"):
            raise HTTPException(status_code=400, detail=result.get("error", "Invalid Discogs settings."))
        return {key: result[key] for key in ("token_configured", "source")}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save Discogs settings.")


@router.post("/api/settings/discogs/test")
def test_discogs_settings(librarian=Depends(get_librarian)):
    try:
        token, _ = _discogs_token_and_source(librarian._discovery_settings_read, os.environ)
        return parse_result(_test_discogs_connection(token, httpx.get, json.dumps))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the Discogs connection.")
