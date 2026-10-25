"""Navidrome cover art for owned results (contract section 3.8, ``artwork_url``).

The browser asks this app, and the app signs the request to Navidrome, so the
Navidrome credential never reaches the page or its URLs.
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.dependencies import get_librarian
from discovery.search.query import ARTWORK_PATH
from integrations.navidrome import client as navidrome_client

router = APIRouter()

_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")
DEFAULT_SIZE = 300
MIN_SIZE = 64
MAX_SIZE = 1000


def _parse_size(raw: str | None) -> int:
    if raw is None:
        return DEFAULT_SIZE
    try:
        value = int(raw)
    except ValueError:
        value = 0
    if not MIN_SIZE <= value <= MAX_SIZE:
        raise HTTPException(status_code=400, detail="size must be between 64 and 1000.")
    return value


@router.get(ARTWORK_PATH + "{cover_id}")
def owned_artwork(cover_id: str, size: str | None = None, librarian=Depends(get_librarian)):
    if not _ID_PATTERN.fullmatch(cover_id):
        raise HTTPException(status_code=400, detail="artwork ID is not valid.")
    pixels = _parse_size(size)
    try:
        content_type, body = navidrome_client.cover_art(
            librarian._navidrome_config, cover_id, size=pixels,
        )
    except navidrome_client.CoverArtUnavailable:
        raise HTTPException(status_code=404, detail="No artwork for this item.")
    except ValueError:
        # Navidrome settings are incomplete, so no request can be signed.
        raise HTTPException(status_code=503, detail="Navidrome is not configured.")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not load artwork.")
    return Response(
        content=body,
        media_type=content_type,
        headers={
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )
