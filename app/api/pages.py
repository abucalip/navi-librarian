"""Page and bundled-asset routes, separate from application assembly."""
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse


def create_pages_router(*, page_html: str, cassette_icon_path: Path) -> APIRouter:
    """Build the static page routes using paths/content resolved by the app factory."""
    router = APIRouter()

    @router.get("/assets/cassette.png", include_in_schema=False)
    def cassette_icon():
        """Serve the bundled app icon without relying on an external image host."""
        return FileResponse(
            cassette_icon_path,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @router.get("/", response_class=HTMLResponse)
    def home():
        return HTMLResponse(page_html)

    return router
