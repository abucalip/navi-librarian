"""Authentication HTTP routes, isolated from application assembly."""
import secrets
import threading
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

AUTH_LOCK = threading.Lock()
_LOGIN_ATTEMPTS = {}
_LOGIN_ATTEMPTS_LOCK = threading.Lock()
_LOGIN_WINDOW_SECONDS = 15 * 60
_LOGIN_MAX_ATTEMPTS = 8


def create_auth_router(
    *,
    settings_read,
    settings_write,
    auth_configured,
    session_username,
    set_auth_cookie,
    valid_username,
    valid_password,
    password_digest,
    cookie_name,
    login_page_html,
):
    """Build auth endpoints around app-owned persistence and signing dependencies."""
    router = APIRouter()

    @router.get("/api/auth/status")
    def app_auth_status():
        return {"setup_required": not auth_configured()}

    @router.post("/api/auth/setup")
    def app_auth_setup(payload: dict, request: Request):
        username = str(payload.get("username") or "").strip()
        password = payload.get("password")
        confirmation = payload.get("password_confirmation")
        with AUTH_LOCK:
            if auth_configured():
                raise HTTPException(status_code=409, detail="App account is already configured.")
            if not valid_username(username):
                raise HTTPException(status_code=400, detail="Username must be 3–64 characters using letters, numbers, dot, underscore, or hyphen.")
            if not valid_password(password):
                raise HTTPException(status_code=400, detail="Password must be at least 12 characters.")
            if password != confirmation:
                raise HTTPException(status_code=400, detail="Passwords do not match.")
            salt = secrets.token_hex(16)
            settings_write({
                "app_auth_username": username,
                "app_auth_salt": salt,
                "app_auth_hash": password_digest(password, salt),
            })
        response = JSONResponse({"ok": True, "message": "App account created."})
        set_auth_cookie(response, request, username)
        return response

    @router.post("/api/auth/login")
    def app_auth_login(payload: dict, request: Request):
        if not auth_configured():
            raise HTTPException(status_code=409, detail="Create the app account first.")
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        # Reserve an attempt atomically before password verification. Otherwise,
        # concurrent requests can all pass the limit check before any failed
        # request records its timestamp.
        with _LOGIN_ATTEMPTS_LOCK:
            attempts = [
                stamp for stamp in _LOGIN_ATTEMPTS.get(client_ip, [])
                if now - stamp < _LOGIN_WINDOW_SECONDS
            ]
            if len(attempts) >= _LOGIN_MAX_ATTEMPTS:
                _LOGIN_ATTEMPTS[client_ip] = attempts
                raise HTTPException(
                    status_code=429,
                    detail="Too many login attempts. Try again in 15 minutes.",
                )
            attempts.append(now)
            _LOGIN_ATTEMPTS[client_ip] = attempts
        username = str(payload.get("username") or "").strip()
        password = payload.get("password")
        settings = settings_read()
        valid = (
            username == settings.get("app_auth_username")
            and isinstance(password, str)
            and 0 < len(password) <= 1024
            and bool(settings.get("app_auth_salt"))
            and bool(settings.get("app_auth_hash"))
            and __import__("hmac").compare_digest(
                password_digest(password, settings["app_auth_salt"]),
                settings["app_auth_hash"],
            )
        )
        if not valid:
            raise HTTPException(status_code=401, detail="Invalid username or password.")
        with _LOGIN_ATTEMPTS_LOCK:
            _LOGIN_ATTEMPTS.pop(client_ip, None)
        response = JSONResponse({"ok": True, "message": "Signed in."})
        set_auth_cookie(response, request, username)
        return response

    @router.post("/api/auth/logout")
    def app_auth_logout():
        response = JSONResponse({"ok": True})
        response.delete_cookie(cookie_name, path="/", httponly=True, samesite="strict")
        return response

    @router.get("/login", response_class=HTMLResponse)
    def login_page(request: Request):
        if session_username(request.cookies.get(cookie_name)):
            return RedirectResponse("/", status_code=303)
        return HTMLResponse(login_page_html, headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"})

    return router
