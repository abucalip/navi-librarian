"""Navidrome internet-radio stations: list them and point them at, or away from, the relay."""
from __future__ import annotations

import secrets
from urllib.parse import urlsplit

from integrations.navidrome.client import items

STREAM_PATH = "/radio/stream/"


class StationError(ValueError):
    """The request cannot be applied; the message is safe to show to the owner."""


def _http_url(value: str) -> bool:
    parts = urlsplit(value or "")
    return parts.scheme in ("http", "https") and bool(parts.hostname)


def fetch_stations(api_call) -> list[dict]:
    root = api_call("getInternetRadioStations")
    rows = (root.get("internetRadioStations") or {}).get("internetRadioStation")
    return [
        {"id": str(row.get("id")), "name": str(row.get("name") or ""),
         "stream_url": str(row.get("streamUrl") or ""), "homepage_url": str(row.get("homepageUrl") or "")}
        for row in items(rows) if row.get("id") is not None
    ]


def _is_proxied(station: dict, local: dict | None) -> bool:
    return bool(local and local["enabled"] and f"{STREAM_PATH}{local['token']}" in station["stream_url"])


def list_stations(api_call, store) -> list[dict]:
    result = []
    for station in fetch_stations(api_call):
        local = store.get_station(station["id"])
        proxied = _is_proxied(station, local)
        result.append({
            "id": station["id"], "name": station["name"], "proxied": proxied,
            "stream_url": local["original_url"] if proxied else station["stream_url"],
        })
    return result


def _update(api_call, station: dict, stream_url: str) -> None:
    params = {"id": station["id"], "streamUrl": stream_url, "name": station["name"]}
    if station["homepage_url"]:
        params["homepageUrl"] = station["homepage_url"]
    api_call("updateInternetRadioStation", **params)


def _find(api_call, station_id: str) -> dict:
    found = next((s for s in fetch_stations(api_call) if s["id"] == station_id), None)
    if found is None:
        raise StationError("Navidrome has no such radio station.")
    return found


APP_URL_KEY = "app_url"


def clean_app_url(value: str) -> str:
    """A plain http(s) address for this app (no credentials, query or fragment), or ''."""
    value = (value or "").strip().rstrip("/")
    if not value:
        return ""
    parts = urlsplit(value)
    if not _http_url(value) or parts.query or parts.fragment or parts.username or parts.password:
        raise StationError("The app address must be a plain http(s) address.")
    return value


def effective_app_url(store, browser_url: str) -> str:
    """The saved app address if there is one, else the address the browser reached the app at."""
    return store.get_setting(APP_URL_KEY) or browser_url


def set_app_url(api_call, store, value: str) -> dict:
    """Save the address Navidrome clients reach this app at and move relayed stations onto it."""
    url = clean_app_url(value)
    store.set_setting(APP_URL_KEY, url)
    moved = 0
    if url:
        current = {s["id"]: s for s in fetch_stations(api_call)}
        for local in store.enabled_stations():
            station = current.get(local["station_id"])
            wanted = f"{url}{STREAM_PATH}{local['token']}"
            if station and _is_proxied(station, local) and station["stream_url"] != wanted:
                _update(api_call, station, wanted)
                moved += 1
    return {"app_url": url, "moved": moved}


def enable(api_call, store, station_id: str, base_url: str) -> dict:
    """Point the station at this app's relay. The station's own URL is kept for the way back."""
    base_url = clean_app_url(effective_app_url(store, base_url))
    if not base_url:
        raise StationError("The app address must be a plain http(s) address.")
    station = _find(api_call, station_id)
    local = store.get_station(station_id)
    if _is_proxied(station, local):
        return {"id": station_id, "proxied": True}
    if not _http_url(station["stream_url"]):
        raise StationError("This station's stream address is not an http(s) address.")
    token = secrets.token_urlsafe(24)
    # Saved first: if the Navidrome update fails the original URL is still known.
    store.save_station(station_id, token, station["name"], station["stream_url"])
    try:
        _update(api_call, station, f"{base_url}{STREAM_PATH}{token}")
    except Exception:
        store.disable_station(station_id)
        raise
    return {"id": station_id, "proxied": True}


def disable(api_call, store, station_id: str) -> dict:
    """Give the station its own stream address back."""
    station = _find(api_call, station_id)
    local = store.get_station(station_id)
    if not local:
        return {"id": station_id, "proxied": False}
    if _is_proxied(station, local):
        _update(api_call, station, local["original_url"])
    store.disable_station(station_id)
    return {"id": station_id, "proxied": False}
