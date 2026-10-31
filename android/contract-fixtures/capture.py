"""Record one real response per Librarian endpoint the Android client uses.

Usage (against a local sandbox server, slskd disabled; see docs/LOCAL_UI_TESTING.md):

    python android/contract-fixtures/capture.py http://127.0.0.1:8099 USER PASSWORD

Writes one JSON file per request under android/contract-fixtures/librarian/.
Lists longer than KEEP items are cut to KEEP so the files stay small and carry
little library data; shapes are unchanged. Cookies and credentials are never written.
Standard library only.
"""
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

KEEP = 3
OUT = Path(__file__).resolve().parent / "librarian"


def cut(value):
    if isinstance(value, list):
        return [cut(v) for v in value[:KEEP]]
    if isinstance(value, dict):
        return {k: cut(v) for k, v in value.items()}
    return value


class Client:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def call(self, method, path, query=None, body=None, stream_seconds=None, timeout=90):
        url = self.base + path + ("?" + urllib.parse.urlencode(query) if query else "")
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            resp = self.opener.open(req, timeout=timeout)
        except urllib.error.HTTPError as err:
            resp = err
        status = resp.status if hasattr(resp, "status") else resp.code
        ctype = resp.headers.get("Content-Type", "")
        if ctype.startswith("text/event-stream"):
            return status, ctype, read_sse(resp, stream_seconds or 3)
        raw = resp.read()
        if ctype.startswith("application/json"):
            return status, ctype, json.loads(raw)
        return status, ctype, {"bytes": len(raw)}


def read_sse(resp, seconds):
    events, name, data, deadline = [], "message", [], time.time() + seconds
    while time.time() < deadline and len(events) < 40 and not (events and events[-1]["event"] == "done"):
        line = resp.readline().decode("utf-8", "replace").rstrip("\n")
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].strip())
        elif line == "" and data:
            joined = "\n".join(data)
            try:
                payload = json.loads(joined)
            except ValueError:
                payload = joined
            events.append({"event": name, "data": cut(payload)})
            name, data = "message", []
    resp.close()
    return {"sse_events": events}


def stored_body(body):
    """Request bodies are stored with login credentials replaced by placeholders."""
    if isinstance(body, dict) and "password" in body:
        return {**body, "username": "<username>", "password": "<password>"}
    return body


def record(client, fixture, method, path, query=None, body=None, **kw):
    started = time.time()
    status, ctype, payload = client.call(method, path, query, body, **kw)
    OUT.mkdir(parents=True, exist_ok=True)
    doc = {
        "request": {"method": method, "path": path, "query": query or {}, "body": stored_body(body)},
        "response": {
            "status": status,
            "content_type": ctype.split(";")[0],
            "elapsed_seconds": round(time.time() - started, 2),
            "body": payload if "sse_events" in payload else cut(payload),
        },
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (OUT / f"{fixture}.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"{status} {method} {path} -> {fixture}.json")
    return payload


def main(base, user, password):
    c = Client(base)
    record(c, "auth_status", "GET", "/api/auth/status")
    record(c, "auth_login_bad_credentials", "POST", "/api/auth/login",
           body={"username": user, "password": "wrong-password-value"})
    record(c, "auth_login", "POST", "/api/auth/login", body={"username": user, "password": password})
    record(c, "health", "GET", "/api/health")

    # Dashboard
    record(c, "dashboard_picks", "GET", "/api/dashboard-picks", {"count": 10})
    record(c, "dashboard_genres", "GET", "/api/dashboard/genres")
    for shelf in ("newest", "recent", "frequent"):
        record(c, f"dashboard_albums_{shelf}", "GET", f"/api/dashboard/albums/{shelf}", {"count": 10})

    # Discovery
    record(c, "recommendations", "GET", "/api/recommendations", {"count": 10})
    for name in ("personal", "for_me", "classics", "artist_deep_dive", "new_releases"):
        record(c, f"discovery_{name}", "GET", f"/api/discovery/{name}", {"count": 10})
    record(c, "discovery_lens_feedback", "GET", "/api/discovery/lens-feedback")
    record(c, "discovery_unknown_list", "GET", "/api/discovery/not_a_list")

    # Library
    artists = record(c, "library_artists", "GET", "/api/library/artists")
    albums = record(c, "library_albums", "GET", "/api/library/albums")
    artist = next(a for a in artists["items"] if a.get("album_count", 0) >= 2)
    album = next(a for a in albums["items"] if a.get("song_count", 0) >= 5)

    # Search (SSE) and detail pages
    record(c, "search_all", "GET", "/api/search", {"q": artist["name"], "scope": "all"}, stream_seconds=40)
    record(c, "search_owned", "GET", "/api/search", {"q": artist["name"], "scope": "owned"}, stream_seconds=20)
    record(c, "search_bad_query", "GET", "/api/search", {"q": ""})
    record(c, "artist_page", "GET", "/api/artists/" + urllib.parse.quote(artist["key"], safe=""),
           {"id": artist["id"], "name": artist["name"]})
    record(c, "album_page", "GET",
           "/api/albums/%s/%s" % (urllib.parse.quote(album["artist_key"], safe=""),
                                  urllib.parse.quote(album["key"].split("/", 1)[1], safe="")),
           {"id": album["id"], "artist": album["artist"], "name": album["name"], "year": album.get("year")})
    genre = record(c, "dashboard_genres_for_page", "GET", "/api/dashboard/genres")["items"][0]
    record(c, "genre_page", "GET", "/api/genres/" + urllib.parse.quote(genre["tag"], safe=""))

    # Metadata
    record(c, "artist_bio", "GET", "/api/artist-bio", {"artist": artist["name"]})
    ident = {"artist": album["artist"], "album": album["name"]}
    record(c, "album_details", "GET", "/api/album-details", ident)
    record(c, "album_description", "GET", "/api/album-description", ident)
    record(c, "album_links", "GET", "/api/album-links", ident)
    record(c, "album_year", "GET", "/api/album-year", ident)
    record(c, "artwork", "GET", "/api/artwork", ident)
    record(c, "artist_image", "GET", "/api/artist-image", {"name": artist["name"]})
    record(c, "owned_artwork", "GET", album["artwork_url"])

    # Acquisitions: slskd is disabled in the sandbox, so launches report their failure shape.
    record(c, "acquisitions", "GET", "/api/acquisitions")
    record(c, "acquisitions_stream", "GET", "/api/acquisitions/stream", stream_seconds=3)
    meta = {"source": "android-contract-capture"}
    record(c, "acquire_album", "POST", "/api/acquire",
           body={"artist": "Contract Fixture Artist", "album": "Contract Fixture Album",
                 "metadata": meta, "auto_queue": True})
    record(c, "acquire_track", "POST", "/api/acquire/track",
           body={"artist": "Contract Fixture Artist", "album": "Contract Fixture Album",
                 "title": "Contract Fixture Song", "track_number": 1, "metadata": meta})
    record(c, "acquisitions_skip", "POST", "/api/acquisitions/skip",
           body={"artist": "Contract Fixture Artist", "album": "Contract Fixture Album"})
    record(c, "acquisitions_dismiss", "POST", "/api/acquisitions/dismiss",
           body={"artist": "Contract Fixture Artist", "album": "Contract Fixture Album"})

    # Feedback (writes only to the sandbox data directory)
    record(c, "discovery_feedback", "POST", "/api/discovery/feedback",
           body={"artist": "Contract Fixture Artist", "album": "Contract Fixture Album",
                 "action": "save", "metadata": meta})
    record(c, "auth_logout", "POST", "/api/auth/logout")


if __name__ == "__main__":
    main(*sys.argv[1:4])
