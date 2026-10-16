"""Authentication gate middleware, independent of application/service assembly."""
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse


PUBLIC_PATHS = frozenset({
    "/login",
    "/api/auth/status",
    "/api/auth/setup",
    "/api/auth/login",
    "/api/auth/logout",
})


def create_app_login_middleware(*, auth_configured, session_username, cookie_name):
    """Return the HTTP middleware that protects app routes when an owner is configured."""

    async def require_app_login(request: Request, call_next):
        path = request.url.path
        is_public_asset = path.startswith("/static/") or path == "/assets/cassette.png"
        if path not in PUBLIC_PATHS and not is_public_asset and auth_configured():
            username = session_username(request.cookies.get(cookie_name))
            if username:
                return await call_next(request)
        elif path in PUBLIC_PATHS or is_public_asset:
            return await call_next(request)

        # With no valid session, APIs fail closed and browser routes redirect to login.
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Authentication required."}, status_code=401)
        return RedirectResponse(url="/login", status_code=303)

    return require_app_login
