"""slskd connectivity probe with the legacy response contract preserved."""
from __future__ import annotations

import json
from typing import Any, Callable

import httpx


def test_connection(
    config_reader: Callable[[], tuple[str, str, Any]],
    *,
    http_get: Callable[..., Any] | None = None,
) -> str:
    """Test the configured slskd API and return the established JSON result."""
    request = http_get or httpx.get
    try:
        base_url, api_key, _ = config_reader()
        response = request(
            base_url + "/api/v0/server",
            headers={"X-API-KEY": api_key},
            timeout=8,
        )
        if response.status_code in (401, 403):
            return json.dumps({
                "ok": False, "status": "authentication_failed",
                "message": "slskd rejected the API key. Check the key in Settings.",
            })
        response.raise_for_status()
        return json.dumps({
            "ok": True, "status": "connected",
            "http_status": response.status_code,
            "message": "slskd API connection succeeded.",
        })
    except (httpx.HTTPError, ValueError) as exc:
        return json.dumps({
            "ok": False, "status": "connection_failed",
            "message": str(exc),
        })
