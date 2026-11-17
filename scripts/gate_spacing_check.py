#!/usr/bin/env python3
"""Live check of efficiency step R3: web and worker share one MusicBrainz gate, with no real traffic.

Starts the real worker (``python -m app.worker``) and the real web app (uvicorn) on one fresh
``DISCAIR_DATA_DIR`` (so they share ``provider_gate.sqlite3``), a fake MusicBrainz that records every
arrival time, and a tiny fake Navidrome. While the worker's auto fill asks MusicBrainz for newly
detected albums, this script drives the web routes that call MusicBrainz. It then reports the gaps
between consecutive MusicBrainz requests (arrival times at the fake, and grant times logged inside
each process) and the gate/diagnostics counters.

No real provider traffic: MusicBrainz has no configurable base URL, so a ``sitecustomize.py`` written
into the scratch directory (put on ``PYTHONPATH`` of the two launched processes only; nothing in the
repo is auto-loaded) rewrites ``https://musicbrainz.org/...`` to the local fake below
``httpx.HTTPTransport`` and ``urllib``'s ``HTTPSHandler``, and makes ``socket.getaddrinfo`` refuse every
host except loopback (logged to ``blocked.jsonl``). The processes get a minimal environment with no
provider keys. Nothing here is imported by the app.

Usage: python scripts/gate_spacing_check.py [--scratch DIR] [--seconds 120] [--port 8095]
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INTERVAL = 1.1


def analyze(records, interval: float = INTERVAL) -> dict:
    """Gap statistics for ``records``, a list of ``(timestamp, role)``; order does not matter."""
    ordered = sorted(records, key=lambda r: r[0])
    gaps = [b[0] - a[0] for a, b in zip(ordered, ordered[1:])]
    roles: dict[str, int] = {}
    for _, role in ordered:
        roles[role] = roles.get(role, 0) + 1
    total = len(ordered)
    return {
        "count": total,
        "gaps": len(gaps),
        "min_gap": min(gaps) if gaps else None,
        "median_gap": statistics.median(gaps) if gaps else None,
        "below_interval": sum(1 for g in gaps if g < interval),
        "per_role": roles,
        "share": {role: n / total for role, n in roles.items()} if total else {},
        "cross_pairs": sum(1 for a, b in zip(ordered, ordered[1:]) if a[1] != b[1]),
    }


SITECUSTOMIZE = r'''
import json, os, socket, sys, time
ROLE = os.environ.get("GATE_ROLE", "?")
LOG = os.environ.get("GATE_LOG_DIR", "")
MB_PORT = os.environ.get("GATE_MB_PORT", "")
PROC = f"{ROLE}/{os.getpid()}"

def _log(name, **row):
    row.update(t=time.time(), role=ROLE, pid=os.getpid())
    with open(os.path.join(LOG, name), "a") as f:
        f.write(json.dumps(row) + "\n")

_log("loaded.jsonl", argv=sys.argv[:3])
_real_getaddrinfo = socket.getaddrinfo
def _guarded(host, *a, **k):
    if str(host) in ("127.0.0.1", "::1", "localhost"):
        return _real_getaddrinfo(host, *a, **k)
    _log("blocked.jsonl", host=str(host))
    raise socket.gaierror(socket.EAI_NONAME, "blocked by gate_spacing_check")
socket.getaddrinfo = _guarded

def _rewrite(url):
    return "http://127.0.0.1:%s%s" % (MB_PORT, url.split("musicbrainz.org", 1)[1])

import httpx
_real_handle = httpx.HTTPTransport.handle_request
def _handle(self, request):
    if request.url.host == "musicbrainz.org":
        request.url = httpx.URL(_rewrite(str(request.url)))
        request.headers["X-Gate-Proc"] = PROC
    return _real_handle(self, request)
httpx.HTTPTransport.handle_request = _handle

import urllib.request
_real_https_open = urllib.request.HTTPSHandler.https_open
def _https_open(self, req):
    if req.host.split(":")[0] == "musicbrainz.org":
        new = urllib.request.Request(_rewrite(req.full_url), headers=dict(req.header_items()))
        new.add_header("X-Gate-Proc", PROC)
        return urllib.request.build_opener(urllib.request.HTTPHandler).open(new, timeout=req.timeout)
    return _real_https_open(self, req)
urllib.request.HTTPSHandler.https_open = _https_open

try:
    import threading
    from integrations import provider_gate
    _tl = threading.local()
    _real_init = provider_gate.ProviderGate.__init__
    def _init(self, *a, **k):
        _real_init(self, *a, **k)
        inner = self._clock
        def clock():
            _tl.now = inner()
            return _tl.now
        self._clock = clock
    provider_gate.ProviderGate.__init__ = _init
    _real_shared = provider_gate.ProviderGate._reserve_shared
    def _shared(self, provider, max_wait):
        wait = _real_shared(self, provider, max_wait)
        if wait is not None:   # slot start exactly as the gate computed it (now + wait)
            _log("slots.jsonl", provider=provider, slot=_tl.now + wait, wait=wait)
        return wait
    provider_gate.ProviderGate._reserve_shared = _shared
    _real_reserve = provider_gate.ProviderGate.reserve
    def _reserve(self, provider, max_wait):
        ok = _real_reserve(self, provider, max_wait)
        _log("grants.jsonl", provider=provider, granted=ok)
        return ok
    provider_gate.ProviderGate.reserve = _reserve
except Exception as exc:  # the repo is on PYTHONPATH; if not, the run reports no grants
    _log("loaded.jsonl", error=type(exc).__name__)
'''


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


# ------------------------------------------------------------------ fakes

def make_fake_mb(log: Path) -> ThreadingHTTPServer:
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            row = {"t": time.time(), "role": (self.headers.get("X-Gate-Proc") or "?/0").split("/")[0],
                   "proc": self.headers.get("X-Gate-Proc"), "path": self.path.split("?")[0]}
            with lock, open(log, "a") as f:
                f.write(json.dumps(row) + "\n")
            path = row["path"]
            if "/release-group" in path:
                body = {"count": 0, "release-groups": []}
            elif path.endswith("/artist/") or path.endswith("/artist"):
                body = {"count": 0, "artists": []}
            elif "/ws/2/release/" in path:
                body = {"id": path.rsplit("/", 1)[1], "relations": [], "media": []}
            elif "/recording" in path:
                body = {"count": 0, "recordings": []}
            else:
                body = {"count": 0}
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def make_fake_navidrome(port: int, state: dict) -> ThreadingHTTPServer:
    """Subsonic JSON for the few calls auto fill and the owned view make; ``state['grown']`` adds albums."""
    def albums():
        n = state["albums"]
        return [{"id": f"al{i}", "name": f"Album {i}", "title": f"Album {i}", "artist": f"Artist {i % 4}",
                 "artistId": f"ar{i % 4}", "musicBrainzId": f"00000000-0000-4000-8000-{i:012d}",
                 "songCount": 1, "year": 2000 + i % 20} for i in range(n)][::-1]  # newest first

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            from urllib.parse import parse_qs, urlsplit
            url = urlsplit(self.path)
            method = url.path.rsplit("/", 1)[-1].removesuffix(".view")
            q = {k: v[0] for k, v in parse_qs(url.query).items()}
            state["calls"][method] = state["calls"].get(method, 0) + 1
            body: dict = {}
            if method == "getScanStatus":
                body = {"scanStatus": {"scanning": False, "count": state["albums"], "lastScan": f"scan-{state['albums']}"}}
            elif method == "getAlbumList2":
                off, size = int(q.get("offset", 0)), int(q.get("size", 20))
                body = {"albumList2": {"album": albums()[off:off + size]}}
            elif method == "getAlbum":
                i = int(q["id"][2:])
                a = {k: v for k, v in albums()[state["albums"] - 1 - i].items()}
                a["song"] = [{"id": f"so{i}", "title": f"Song {i}", "artist": a["artist"], "artistId": a["artistId"],
                              "track": 1, "duration": 200}]
                body = {"album": a}
            elif method == "getArtist":
                i = int(q["id"][2:])
                body = {"artist": {"id": q["id"], "name": f"Artist {i}",
                                   "musicBrainzId": f"11111111-1111-4111-8111-{i:012d}", "album": []}}
            elif method == "getArtists":
                body = {"artists": {"index": []}}
            data = json.dumps({"subsonic-response": {"status": "ok", "version": "1.16.1", **body}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


# ------------------------------------------------------------------ run

def _env(scratch: Path, data: Path, role: str, mb_port: int, nav_port: int) -> dict:
    return {"PATH": "/usr/bin:/bin", "HOME": str(scratch / "home"), "DISCAIR_DATA_DIR": str(data),
            "PYTHONPATH": f"{scratch}{os.pathsep}{REPO}", "PYTHONDONTWRITEBYTECODE": "1",
            "NAVIDROME_URL": f"http://127.0.0.1:{nav_port}", "NAVIDROME_USER": "fake", "NAVIDROME_PASSWORD": "fake",
            "GATE_ROLE": role, "GATE_LOG_DIR": str(scratch), "GATE_MB_PORT": str(mb_port)}


def _stop(proc: subprocess.Popen, grace: float) -> str:
    if proc.poll() is not None:
        return f"already exited {proc.returncode}"
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(grace)
        return f"exited {proc.returncode} after SIGTERM"
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(10)
        return "killed after grace"


def run(scratch: Path, seconds: float, port: int) -> dict:
    import httpx
    scratch.mkdir(parents=True, exist_ok=True)
    data, run_dir = scratch / "data", scratch / "run"
    (scratch / "home").mkdir(exist_ok=True)
    run_dir.mkdir(exist_ok=True)
    data.mkdir(exist_ok=True)
    (scratch / "sitecustomize.py").write_text(SITECUSTOMIZE)
    for name in ("mb_requests.jsonl", "grants.jsonl", "slots.jsonl", "blocked.jsonl", "loaded.jsonl"):
        (scratch / name).unlink(missing_ok=True)

    mb = make_fake_mb(scratch / "mb_requests.jsonl")
    nav_port = port + 1
    state = {"albums": 2, "calls": {}}
    nav = make_fake_navidrome(nav_port, state)
    for server in (mb, nav):
        threading.Thread(target=server.serve_forever, daemon=True).start()
    mb_port = mb.server_address[1]

    # Seed the knowledge store: the API fill refuses to run until a MusicBrainz slice is marked loaded.
    seed = subprocess.run(
        [sys.executable, "-c",
         "from intelligence.store import ensure_store, open_store\nfrom app.api.insights import STORE_FILE\n"
         "import os, pathlib, time\np = pathlib.Path(os.environ['DISCAIR_DATA_DIR']) / STORE_FILE\nensure_store(p)\n"
         "db = open_store(p)\nwith db:\n    db.execute(\"INSERT OR REPLACE INTO meta (key, value) VALUES "
         "('musicbrainz_slice.loaded_at', ?)\", (str(time.time()),))\ndb.close()"],
        env=_env(scratch, data, "seed", mb_port, nav_port), cwd=run_dir, capture_output=True, text=True)
    if seed.returncode:
        raise SystemExit("seeding failed: " + seed.stderr[-500:])

    procs, result = {}, {}
    try:
        worker_log = open(scratch / "worker.log", "w")
        procs["worker"] = subprocess.Popen(
            [sys.executable, "-m", "app.worker"], env={**_env(scratch, data, "worker", mb_port, nav_port),
                                                      "NAVI_AUTO_FILL_POLL_SECONDS": "5"},
            cwd=run_dir, stdout=worker_log, stderr=subprocess.STDOUT)
        web_log = open(scratch / "web.log", "w")
        procs["web"] = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
            env=_env(scratch, data, "web", mb_port, nav_port), cwd=run_dir, stdout=web_log, stderr=subprocess.STDOUT)
        base = f"http://127.0.0.1:{port}"
        client = httpx.Client(base_url=base, timeout=60)
        for _ in range(60):
            try:
                if client.get("/api/auth/status").status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(1)
        creds = {"username": "gatecheck", "password": "throwaway-password-1", "password_confirmation": "throwaway-password-1"}
        client.post("/api/auth/setup", json=creds).raise_for_status()

        time.sleep(12)               # the worker's first poll records the 2-album baseline
        state["albums"] = 50         # 48 new albums with release and artist MBIDs: the worker now asks MusicBrainz
        stop_at = time.time() + seconds
        counter = {"n": 0}
        web_status: dict[str, dict] = {}

        def drive(name, fn):
            while time.time() < stop_at:
                counter["n"] += 1
                try:
                    code = fn(client, counter["n"])
                except Exception as exc:  # noqa: BLE001
                    code = type(exc).__name__
                web_status.setdefault(name, {}).setdefault(str(code), 0)
                web_status[name][str(code)] += 1
                time.sleep(0.2)

        def years(c, n):
            items = [{"artist": f"Gate Artist {n}-{k}", "album": f"Gate Album {n}-{k}"} for k in range(15)]
            return c.post("/api/album-years", json={"items": items}).status_code

        def year(c, n):
            return c.get("/api/album-year", params={"artist": f"Solo Artist {n}", "album": f"Solo Album {n}"}).status_code

        def search(c, n):
            r = c.get("/api/search", params={"q": f"gatecheck query {n}", "scope": "all", "limit": "5"})
            return r.status_code

        threads = [threading.Thread(target=drive, args=(n, f), daemon=True)
                   for n, f in (("POST /api/album-years", years), ("GET /api/album-year", year), ("GET /api/search", search))]
        for t in threads:
            t.start()
        for t in threads:
            t.join(seconds + 120)

        result["web_status"] = web_status
        result["worker_stop"] = _stop(procs["worker"], 40)   # saves its counters on the way out
        diag = client.get("/api/diagnostics/runtime")
        result["diagnostics_status"] = diag.status_code
        result["diagnostics"] = diag.json() if diag.status_code == 200 else None
        result["fake_navidrome_calls"] = state["calls"]
    finally:
        for name in ("worker", "web"):
            if name in procs:
                result[f"{name}_final"] = _stop(procs[name], 40)
        mb.shutdown()
        nav.shutdown()

    arrivals = read_jsonl(scratch / "mb_requests.jsonl")
    grants = [g for g in read_jsonl(scratch / "grants.jsonl") if g.get("provider") == "musicbrainz" and g.get("granted")]
    refused = [g for g in read_jsonl(scratch / "grants.jsonl") if g.get("provider") == "musicbrainz" and not g.get("granted")]
    slots = [s for s in read_jsonl(scratch / "slots.jsonl") if s.get("provider") == "musicbrainz"]
    result["slots"] = analyze([(s["slot"], s["role"]) for s in slots], INTERVAL - 1e-6)  # float rounding of now + wait
    result["arrivals"] = analyze([(r["t"], r["role"]) for r in arrivals])
    result["grants"] = analyze([(g["t"], g["role"]) for g in grants])
    result["refused_by_role"] = {r: sum(1 for g in refused if g["role"] == r) for r in {g["role"] for g in refused}}
    result["blocked_hosts"] = sorted({(b["role"], b["host"]) for b in read_jsonl(scratch / "blocked.jsonl")})
    result["sitecustomize_loaded"] = sorted({l["role"] for l in read_jsonl(scratch / "loaded.jsonl")})
    ordered = sorted(arrivals, key=lambda r: r["t"])
    result["violations"] = [
        {"gap": b["t"] - a["t"], "first": [a["role"], a["path"], a["t"]], "second": [b["role"], b["path"], b["t"]]}
        for a, b in zip(ordered, ordered[1:]) if b["t"] - a["t"] < INTERVAL]
    result["arrival_max_shortfall_ms"] = max([0.0] + [(INTERVAL - v["gap"]) * 1000 for v in result["violations"]])
    result["arrivals_below_1_0s"] = sum(1 for a, b in zip(ordered, ordered[1:]) if b["t"] - a["t"] < 1.0)
    result["violations"] = result["violations"][:5]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--scratch", type=Path, default=None, help="scratch directory (default: a new temp directory)")
    parser.add_argument("--seconds", type=float, default=120.0, help="how long the web routes are driven")
    parser.add_argument("--port", type=int, default=8095, help="web port; the fake Navidrome uses port + 1")
    args = parser.parse_args()
    scratch = args.scratch or Path(tempfile.mkdtemp(prefix="gate-spacing-"))
    out = run(scratch, args.seconds, args.port)
    print(json.dumps(out, indent=2, default=str))
    print("scratch:", scratch, file=sys.stderr)
    # Slot starts are what the gate guarantees; grant and arrival times add per-request client jitter.
    bad = out["slots"]["below_interval"] or any(host == "musicbrainz.org" for _, host in out["blocked_hosts"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
