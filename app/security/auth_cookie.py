"""Session-cookie policy, isolated from application and authentication service assembly."""


def set_auth_cookie(
    response,
    request,
    username,
    *,
    make_session_token,
    cookie_name,
    max_age,
):
    """Set the existing strict, HTTP-only session cookie on a response."""
    forwarded_proto = (
        request.headers.get("x-forwarded-proto", "")
        .split(",")[0]
        .strip()
        .lower()
    )
    response.set_cookie(
        cookie_name,
        make_session_token(username),
        max_age=max_age,
        httponly=True,
        secure=request.url.scheme == "https" or forwarded_proto == "https",
        samesite="strict",
        path="/",
    )
