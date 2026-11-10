"""Navidrome cover art for owned results (contract section 3.8, ``artwork_url``).

The browser asks this app, and the app signs the request to Navidrome, so the
Navidrome credential never reaches the page or its URLs.
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.artwork import get_service
from app.api.dependencies import get_librarian
from intelligence.artwork import cover
from intelligence.artwork.service import ArtworkService
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


def _headers(max_age: int) -> dict:
    return {"Cache-Control": f"private, max-age={max_age}", "X-Content-Type-Options": "nosniff"}


def _alternate(service: ArtworkService, image_id: int, pixels: int):
    """Bytes of one Librarian-held image sized for ``pixels``, or ``None`` when it cannot be served now."""
    state, body, content_type = service.image(image_id, "thumb" if pixels <= 250 else "display")
    return (body, content_type) if state == "ok" and body else None


def _album_group(librarian, album_id: str):
    """(release group id, owned release id) of an owned album, from the owned index; ``None`` when unknown."""
    from app.api.search import owned_view
    try:
        data = owned_view(librarian).data
    except Exception:
        return None                      # no owned index to read: keep the plain 404
    album = next((a for a in (data.albums if data else ()) if a["id"] == album_id), None)
    rgid = (album or {}).get("release_group_mbid")
    return (str(rgid).lower(), None) if rgid else None


@router.get(ARTWORK_PATH + "{cover_id}")
def owned_artwork(cover_id: str, size: str | None = None, librarian=Depends(get_librarian),
                  service: ArtworkService = Depends(get_service)):
    if not _ID_PATTERN.fullmatch(cover_id):
        raise HTTPException(status_code=400, detail="artwork ID is not valid.")
    pixels = _parse_size(size)
    # The owner's pick wins on every screen (docs/artwork.md slice 4).
    chosen = service.store.get_choice(cover_id)
    if chosen is not None:
        picked = _alternate(service, chosen, pixels)
        if picked:
            return Response(content=picked[0], media_type=picked[1], headers=_headers(300))
    content_type, body = None, None
    try:
        content_type, body = navidrome_client.cover_art(
            librarian._navidrome_config, cover_id, size=pixels,
        )
    except navidrome_client.CoverArtUnavailable:
        pass
    except ValueError:
        # Navidrome settings are incomplete, so no request can be signed.
        raise HTTPException(status_code=503, detail="Navidrome is not configured.")
    except Exception:
        raise HTTPException(status_code=502, detail="Could not load artwork.")
    # Grid fallback: no library cover, or a small one, uses the group's best front (never an artist photo).
    have = None if body is None else cover.long_side(body)
    if body is None or (have is not None and have < cover.SMALL_COVER_PX):
        group = _album_group(librarian, cover_id)
        better = cover.larger_front(service, group[0], group[1], have) if group else None
        alt = _alternate(service, better, pixels) if better is not None else None
        if alt:
            return Response(content=alt[0], media_type=alt[1], headers=_headers(300))
    if body is None:
        raise HTTPException(status_code=404, detail="No artwork for this item.")
    return Response(content=body, media_type=content_type, headers=_headers(3600))
