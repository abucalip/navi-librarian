"""Settings API routes.

These handlers intentionally delegate all configuration and connection behavior to
the existing librarian domain functions; this module only adapts HTTP payloads.
"""
import json

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_librarian
from app.api.utils import parse_result
from settings.service import (
    get_automatic_refill_settings as _get_automatic_refill_settings,
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
        return parse_result(librarian.discovery_get_navidrome_settings())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read Navidrome settings.")


@router.put("/api/settings/navidrome")
def set_navidrome_settings(payload: dict, librarian=Depends(get_librarian)):
    try:
        result = parse_result(librarian.discovery_set_navidrome_settings(
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
        return parse_result(librarian.discovery_test_navidrome_connection())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the Navidrome connection.")


@router.get("/api/settings/lastfm")
def get_lastfm_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(librarian.discovery_get_lastfm_settings())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read Last.fm settings.")


@router.put("/api/settings/lastfm")
def set_lastfm_settings(payload: dict, librarian=Depends(get_librarian)):
    try:
        username = payload.get("username")
        return parse_result(librarian.discovery_set_lastfm_settings(
            api_key=str(payload.get("api_key") or ""),
            username=None if username is None else str(username),
        ))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not save Last.fm settings.")


@router.post("/api/settings/lastfm/test")
def test_lastfm_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(librarian.discovery_test_lastfm_connection())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the Last.fm connection.")


@router.get("/api/settings/listenbrainz")
def get_listenbrainz_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(librarian.discovery_get_listenbrainz_settings())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read ListenBrainz settings.")


@router.put("/api/settings/listenbrainz")
def set_listenbrainz_settings(payload: dict, librarian=Depends(get_librarian)):
    try:
        result = parse_result(librarian.discovery_set_listenbrainz_settings(
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
        return parse_result(librarian.discovery_test_listenbrainz_connection())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the ListenBrainz connection.")


@router.get("/api/settings/slskd")
def get_slskd_settings(librarian=Depends(get_librarian)):
    try:
        return parse_result(librarian.discovery_get_slskd_settings())
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
        result = parse_result(librarian.discovery_set_slskd_settings(
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
        return parse_result(librarian.discovery_test_slskd_connection())
    except Exception:
        raise HTTPException(status_code=502, detail="Could not test the slskd connection.")
