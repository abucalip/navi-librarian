import hmac
import json
import os
import secrets
import time
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.api.dependencies import get_librarian
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
from app.api.pages import create_pages_router
from app.security.app_login_middleware import create_app_login_middleware
from app.security.auth_cookie import set_auth_cookie as _set_auth_cookie_impl
from app.security.auth_configuration import auth_is_configured
from app.security.auth_secret import AuthSecretProvider



app = FastAPI(
    title="Navidrome Librarian",
    description="A read-only web interface for your music library.",
    version="0.1.0",
)

_APP_ROOT = Path(__file__).resolve().parent.parent
_STATIC_DIR = _APP_ROOT / "static"
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


# Authentication settings remain in the existing persistent settings store.

_AUTH_SECRET = None  # Retained as a compatibility seam for auth integration tests.
_AUTH_SECRET_PROVIDER = AuthSecretProvider(
    data_dir_getter=lambda: get_librarian().DATA_DIR,
    secret_loader=load_auth_secret,
)


def _auth_secret():
    """Load the persistent signing key only when an auth operation needs it."""
    global _AUTH_SECRET
    if _AUTH_SECRET is None:
        _AUTH_SECRET = _AUTH_SECRET_PROVIDER.get()
    return _AUTH_SECRET


def _auth_settings():
    return get_librarian()._discovery_settings_read()


def _auth_configured():
    return auth_is_configured(_auth_settings())


def _make_session_token(username, now=None):
    return _make_session_token_impl(username, _auth_secret(), now=now)


def _session_username(token, now=None):
    return _session_username_impl(token, _auth_secret(), _auth_settings, now=now)


def _set_auth_cookie(response, request, username):
    _set_auth_cookie_impl(
        response,
        request,
        username,
        make_session_token=_make_session_token,
        cookie_name=AUTH_COOKIE_NAME,
        max_age=AUTH_SESSION_SECONDS,
    )


app.middleware("http")(create_app_login_middleware(
    auth_configured=_auth_configured,
    session_username=lambda token: _session_username(token),
    cookie_name=AUTH_COOKIE_NAME,
))

LOGIN_PAGE = (_TEMPLATE_DIR / "login.html").read_text(encoding="utf-8")


app.include_router(create_auth_router(
    settings_read=_auth_settings,
    settings_write=lambda values: get_librarian()._discovery_settings_write(values),
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

PAGE = (_TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")
app.include_router(create_pages_router(
    page_html=PAGE,
    cassette_icon_path=_APP_ROOT / "cassette.png",
))