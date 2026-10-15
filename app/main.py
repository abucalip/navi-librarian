import hmac
import json
import os
import secrets
import time
from html import escape
import threading
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.api.settings import router as settings_router
from app.api.auth import (
    AUTH_LOCK, _LOGIN_ATTEMPTS, _LOGIN_MAX_ATTEMPTS,
    create_auth_router,
)
from app.security.auth import (
    AUTH_COOKIE_NAME,
    AUTH_PASSWORD_ITERATIONS,
    AUTH_SESSION_SECONDS,
    load_auth_secret,
    make_session_token as _make_session_token_impl,
    password_digest as _password_digest,
    session_username as _session_username_impl,
    valid_auth_password as _valid_auth_password,
    valid_auth_username as _valid_auth_username,
)
from app.api.acquisitions import router as acquisitions_router
from app.api.discovery import router as discovery_router
from app.api.metadata import router as metadata_router
from app.api.dashboard import router as dashboard_router

import navidrome_server as librarian


app = FastAPI(
    title="Navidrome Librarian",
    description="A read-only web interface for your music library.",
    version="0.1.0",
)

_APP_ROOT = Path(__file__).resolve().parent.parent
_STATIC_DIR = _APP_ROOT / "static"
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/assets/cassette.png", include_in_schema=False)
def cassette_icon():
    """Serve the bundled app icon without relying on an external image host."""
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cassette.png")
    return FileResponse(icon_path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})



# Authentication settings remain in the existing persistent settings store.

_AUTH_SECRET = load_auth_secret(librarian.DATA_DIR)


def _auth_settings():
    return librarian._discovery_settings_read()


def _auth_configured():
    settings = _auth_settings()
    return bool(
        settings.get("app_auth_username")
        and settings.get("app_auth_salt")
        and settings.get("app_auth_hash")
    )


def _make_session_token(username, now=None):
    return _make_session_token_impl(username, _AUTH_SECRET, now=now)


def _session_username(token, now=None):
    return _session_username_impl(token, _AUTH_SECRET, _auth_settings, now=now)


def _set_auth_cookie(response, request, username):
    response.set_cookie(
        AUTH_COOKIE_NAME,
        _make_session_token(username),
        max_age=AUTH_SESSION_SECONDS,
        httponly=True,
        secure=(
            request.url.scheme == "https"
            or request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower() == "https"
        ),
        samesite="strict",
        path="/",
    )


@app.middleware("http")
async def require_app_login(request: Request, call_next):
    path = request.url.path
    public_paths = {
        "/login",
        "/api/auth/status",
        "/api/auth/setup",
        "/api/auth/login",
        "/api/auth/logout",
    }
    is_public_asset = path.startswith("/static/") or path == "/assets/cassette.png"
    if path not in public_paths and not is_public_asset and _auth_configured():
        username = _session_username(request.cookies.get(AUTH_COOKIE_NAME))
        if username:
            return await call_next(request)
    elif path in public_paths or is_public_asset:
        return await call_next(request)

    # When no owner exists yet, only the first-run setup screen and auth
    # endpoints are reachable. Every app/API route remains closed.
    if path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required."}, status_code=401)
    return RedirectResponse(url="/login", status_code=303)


LOGIN_PAGE = (_TEMPLATE_DIR / "login.html").read_text(encoding="utf-8")


app.include_router(create_auth_router(
    settings_read=_auth_settings,
    settings_write=lambda values: librarian._discovery_settings_write(values),
    auth_configured=_auth_configured,
    session_username=lambda token: _session_username(token),
    set_auth_cookie=_set_auth_cookie,
    valid_username=_valid_auth_username,
    valid_password=_valid_auth_password,
    password_digest=lambda password, salt: _password_digest(password, salt),
    cookie_name=AUTH_COOKIE_NAME,
    login_page_html=LOGIN_PAGE,
))
app.include_router(settings_router)
app.include_router(acquisitions_router)
app.include_router(discovery_router)
app.include_router(metadata_router)
app.include_router(dashboard_router)


@app.get("/", response_class=HTMLResponse)
def home():
    return HTMLResponse(PAGE)


PAGE = (_TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")