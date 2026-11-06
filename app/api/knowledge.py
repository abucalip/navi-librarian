"""Knowledge page routes (Server V2 Phase 4, docs/SERVER_V2_CONTRACT.md).

HTTP adapters only: every body comes from ``intelligence.knowledge.KnowledgeReader`` (dossier,
person, label and work pages), which reads the Server V2 SQLite file (D-026) and nothing else.
No provider traffic, no writes, no ownership flags. An entity the store does not know answers
``404``; a store with no MusicBrainz slice loaded still answers for known entities and says so in
the page's own coverage field.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_librarian
from app.api.insights import STORE_FILE
from intelligence.graph import Limits
from intelligence.graph.paths import PATH_KINDS
from intelligence.knowledge import KnowledgeReader
from intelligence.knowledge.path_pages import path_page
from intelligence.store import open_store

router = APIRouter()

MAX_LIMIT = 500
ALBUM_TYPES = ("release", "release_group")
PERSON_TYPES = ("artist", "person", "group")


MAX_DEPTH = 3
DIRECTIONS = ("out", "in", "both")


def _read(librarian, call):
    """Run ``call(reader)`` against the store; unknown entity is 404, any other failure 502."""
    try:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            page = call(KnowledgeReader(db))
        finally:
            db.close()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read the knowledge store.")
    if page is None:
        raise HTTPException(status_code=404, detail="Unknown entity.")
    return page


def _need_id(mbid, navidrome_id=None):
    if not mbid and not navidrome_id:
        raise HTTPException(status_code=400, detail="give an mbid or a navidrome_id")


@router.get("/api/knowledge/album")
def album(mbid: str | None = None, navidrome_id: str | None = None,
          type: str = Query("release"), limit: int = Query(100, ge=1, le=MAX_LIMIT),
          librarian=Depends(get_librarian)):
    _need_id(mbid, navidrome_id)
    if type not in ALBUM_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {', '.join(ALBUM_TYPES)}")
    return _read(librarian, lambda r: r.album_dossier(mbid=mbid, navidrome_id=navidrome_id, type=type, limit=limit))


@router.get("/api/knowledge/person")
def person(mbid: str | None = None, navidrome_id: str | None = None,
           type: str = Query("artist"), limit: int = Query(200, ge=1, le=MAX_LIMIT),
           librarian=Depends(get_librarian)):
    _need_id(mbid, navidrome_id)
    if type not in PERSON_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {', '.join(PERSON_TYPES)}")
    return _read(librarian, lambda r: r.person_page(mbid=mbid, navidrome_id=navidrome_id, type=type, limit=limit))


@router.get("/api/knowledge/label")
def label(mbid: str, limit: int = Query(200, ge=1, le=MAX_LIMIT), librarian=Depends(get_librarian)):
    return _read(librarian, lambda r: r.label_page(mbid=mbid, limit=limit))


@router.get("/api/knowledge/work")
def work(mbid: str, limit: int = Query(200, ge=1, le=MAX_LIMIT), librarian=Depends(get_librarian)):
    return _read(librarian, lambda r: r.work_page(mbid=mbid, limit=limit))


@router.get("/api/knowledge/recording-works")
def recording_works(mbid: str | None = None, navidrome_id: str | None = None,
                    limit: int = Query(50, ge=1, le=MAX_LIMIT), librarian=Depends(get_librarian)):
    _need_id(mbid, navidrome_id)
    return _read(librarian, lambda r: r.works_of_recording(mbid=mbid, navidrome_id=navidrome_id, limit=limit))


@router.get("/api/knowledge/connections")
def connections(mbid: str | None = None, navidrome_id: str | None = None, type: str | None = None,
                credits_only: bool = False, relation: list[str] | None = Query(None),
                direction: str = Query("both"), depth: int = Query(1, ge=1, le=MAX_DEPTH),
                limit: int = Query(50, ge=1, le=MAX_LIMIT), cursor: str | None = None,
                librarian=Depends(get_librarian)):
    """Bounded walk (depth, rows, time) from one entity, paged with an opaque cursor."""
    _need_id(mbid, navidrome_id)
    if direction not in DIRECTIONS:
        raise HTTPException(status_code=400, detail=f"direction must be one of {', '.join(DIRECTIONS)}")
    if not type:
        raise HTTPException(status_code=400, detail="give the entity type")
    limits = Limits(max_depth=depth, max_rows=MAX_LIMIT, page_size=limit)
    return _read(librarian, lambda r: r.connections_page(
        mbid=mbid, navidrome_id=navidrome_id, type=type, credits_only=credits_only, relations=relation,
        direction=direction, limits=limits, cursor=cursor))


@router.get("/api/knowledge/paths")
def paths(kind: str, mbid: str | None = None, navidrome_id: str | None = None, type: str | None = None,
          librarian=Depends(get_librarian)):
    """Discovery path from one artist: ordered stops, each with its reasons and evidence (built on demand, cached)."""
    _need_id(mbid, navidrome_id)
    if not type:
        raise HTTPException(status_code=400, detail="give the entity type")
    if type not in PERSON_TYPES:
        raise HTTPException(status_code=400, detail=f"type must be one of {', '.join(PERSON_TYPES)}")
    try:
        db = open_store(librarian.DATA_DIR / STORE_FILE)
        try:
            page = path_page(db, kind=kind, mbid=mbid, navidrome_id=navidrome_id, type=type)
        finally:
            db.close()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:
        raise HTTPException(status_code=502, detail="Could not read the knowledge store.")
    if page is None:
        raise HTTPException(status_code=404, detail="Unknown entity.")
    return page
