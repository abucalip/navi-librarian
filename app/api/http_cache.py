"""Browser cache headers for the metadata lookups.

The server already keeps these answers; this lets the browser reuse them across page loads too.
Only an answer that found something is marked cacheable. An empty, retryable or failed answer
carries no header, so the browser asks again.
"""
import json

BROWSER_MAX_AGE = 24 * 60 * 60

# Path -> the payload key whose presence means the lookup found something.
_FOUND_KEY = {
    "/api/artwork": "artwork_url",
    "/api/artist-image": "artwork_url",
    "/api/album-details": "tracks",
    "/api/album-description": "paragraphs",
    "/api/album-reviews": "reviews",
    "/api/artist-bio": "bio",
    "/api/album-year": "year",
}


def cache_control_for(path, payload):
    """The Cache-Control value for a successful GET answer, or None to leave it uncached."""
    if not isinstance(payload, dict) or payload.get("retryable"):
        return None
    if path == "/api/album-links":
        found = bool(payload)
    elif path in _FOUND_KEY:
        found = bool(payload.get(_FOUND_KEY[path]))
    else:
        return None
    return f"private, max-age={BROWSER_MAX_AGE}" if found else None


async def add_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if request.method != "GET" or response.status_code != 200 or (
            path not in _FOUND_KEY and path != "/api/album-links"):
        return response
    body = b"".join([chunk async for chunk in response.body_iterator])
    try:
        value = cache_control_for(path, json.loads(body))
    except ValueError:
        value = None
    headers = dict(response.headers)
    headers.pop("content-length", None)
    if value:
        headers["cache-control"] = value
    from starlette.responses import Response

    return Response(content=body, status_code=200, headers=headers, media_type=response.media_type)
