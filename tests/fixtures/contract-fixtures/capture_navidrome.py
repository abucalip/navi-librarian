"""Record one real Subsonic response per Navidrome call the Android client uses.

Usage: NAVIDROME_URL=... NAVIDROME_USER=... NAVIDROME_PASSWORD=... \
    python android/contract-fixtures/capture_navidrome.py

Read-only calls only. The request is stored without the user, token and salt, and the
server address and signed share tokens are replaced by placeholders.
Lists are cut to a few items, as in capture.py. Standard library only.
"""
import hashlib
import json
import os
import re
import secrets
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

KEEP = 3
OUT = Path(__file__).resolve().parent / "navidrome"
API_VERSION = "1.16.1"


def cut(value):
    if isinstance(value, list):
        return [cut(v) for v in value[:KEEP]]
    if isinstance(value, dict):
        return {k: cut(v) for k, v in value.items()}
    return value


def redact(text, base):
    """Drop the private server address and signed share tokens from stored text."""
    text = text.replace(base.rstrip("/"), "https://navidrome.example.ts.net")
    return re.sub(r"/share/img/[A-Za-z0-9_.-]+", "/share/img/REDACTED", text)


def call(base, user, password, endpoint, params):
    salt = secrets.token_hex(8)
    token = hashlib.md5((password + salt).encode()).hexdigest()
    query = {"u": user, "t": token, "s": salt, "v": API_VERSION, "c": "discair", "f": "json", **params}
    url = f"{base.rstrip('/')}/rest/{endpoint}?{urllib.parse.urlencode(query)}"
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.status, resp.headers.get("Content-Type", ""), resp.read()


def record(base, user, password, fixture, endpoint, params=None):
    params = params or {}
    status, ctype, raw = call(base, user, password, endpoint, params)
    OUT.mkdir(parents=True, exist_ok=True)
    body = cut(json.loads(raw)) if ctype.startswith("application/json") else {"bytes": len(raw)}
    doc = {
        "request": {"method": "GET", "path": f"/rest/{endpoint}", "query": params},
        "response": {"status": status, "content_type": ctype.split(";")[0], "body": body},
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    text = redact(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", base)
    (OUT / f"{fixture}.json").write_text(text)
    print(f"{status} {endpoint} -> {fixture}.json")
    return json.loads(raw) if ctype.startswith("application/json") else None


def main():
    base, user, password = (os.environ[k] for k in ("NAVIDROME_URL", "NAVIDROME_USER", "NAVIDROME_PASSWORD"))
    rec = lambda *a: record(base, user, password, *a)
    rec("ping", "ping")
    artists = rec("get_artists", "getArtists")
    artist_id = artists["subsonic-response"]["artists"]["index"][0]["artist"][0]["id"]
    artist = rec("get_artist", "getArtist", {"id": artist_id})
    album_id = artist["subsonic-response"]["artist"]["album"][0]["id"]
    album = rec("get_album", "getAlbum", {"id": album_id})
    rec("get_album_list2_newest", "getAlbumList2", {"type": "newest", "size": 10})
    rec("get_album_list2_alphabetical", "getAlbumList2", {"type": "alphabeticalByName", "size": 10, "offset": 0})
    rec("get_genres", "getGenres")
    rec("search3", "search3", {"query": artist["subsonic-response"]["artist"]["name"], "artistCount": 5, "albumCount": 5, "songCount": 5})
    rec("get_cover_art", "getCoverArt", {"id": album["subsonic-response"]["album"].get("coverArt", album_id), "size": 300})


if __name__ == "__main__":
    main()
