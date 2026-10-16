"""Subsonic-compatible Navidrome HTTP client, independent of app assembly."""

import hashlib
import secrets

import httpx


def api_call(method, config_provider, *, client_factory=None, salt_factory=None, **params):
    """Call Navidrome using token authentication and validate its response.

    Dependencies are supplied by the caller so the legacy server can retain its
    configured settings while this transport boundary remains directly testable.
    """
    base_url, username, password = config_provider()
    if client_factory is None:
        client_factory = httpx.Client
    if salt_factory is None:
        salt_factory = lambda: secrets.token_hex(12)

    salt = salt_factory()
    token = hashlib.md5((password + salt).encode("utf-8")).hexdigest()
    query = {
        "u": username,
        "t": token,
        "s": salt,
        "v": "1.16.1",
        "c": "navidrome-librarian",
        "f": "json",
        **params,
    }

    with client_factory(timeout=30, follow_redirects=False) as client:
        response = client.get(
            f"{base_url}/rest/{method}.view",
            params=query,
        )
        response.raise_for_status()
        data = response.json()

    root = data.get("subsonic-response", {})
    if root.get("status") != "ok":
        error = root.get("error", {})
        raise RuntimeError(
            f"Navidrome API error {error.get('code')}: "
            f"{error.get('message', 'Unknown error')}"
        )

    return root


def items(value):
    """Normalize an optional Subsonic collection field to a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def search_result_payload(result, category, collection_items=items):
    """Shape Subsonic search results for the legacy search_music response."""
    fields = {"artist": "artist", "album": "album", "track": "song"}
    output = {}
    for kind, key in fields.items():
        if category not in ("all", kind):
            continue
        output[key] = [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "artist": item.get("artist"),
                "album": item.get("album"),
                "year": item.get("year"),
                "duration": item.get("duration"),
                "playCount": item.get("playCount"),
            }
            for item in collection_items(result.get(key))
        ]
    return output


def album_details_payload(album, collection_items=items):
    """Shape a Subsonic album record and its tracks for get_album_details."""
    return {
        "id": album.get("id"),
        "name": album.get("name"),
        "artist": album.get("artist"),
        "year": album.get("year"),
        "genre": album.get("genre"),
        "songCount": album.get("songCount"),
        "songs": [
            {
                "id": song.get("id"),
                "title": song.get("title"),
                "artist": song.get("artist"),
                "track": song.get("track"),
                "duration": song.get("duration"),
                "playCount": song.get("playCount"),
            }
            for song in collection_items(album.get("song"))
        ],
    }
