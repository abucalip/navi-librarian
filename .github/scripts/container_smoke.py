#!/usr/bin/env python3
"""Smoke-test the built container's HTTP, owner setup, and persistent /data behavior."""

import json
import os
import subprocess
import time
import urllib.error
import urllib.request

BASE_URL = os.environ.get("SMOKE_BASE_URL", "http://127.0.0.1:18080").rstrip("/")
CONTAINER = os.environ.get("SMOKE_CONTAINER", "librarian-smoke")
USERNAME = "ci-smoke-owner"
PASSWORD = "CI-smoke-password-2026!"


def request(path, payload=None, cookie=None, timeout=3):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data is not None else {}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.read(), response.headers
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), exc.headers


def wait_for_app():
    deadline = time.monotonic() + 40
    last_error = "no response"
    while time.monotonic() < deadline:
        try:
            status, body, _ = request("/api/auth/status")
            if status == 200 and json.loads(body).get("setup_required") is True:
                return
            last_error = f"unexpected initial status: HTTP {status}, {body[:200]!r}"
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(1)
    raise AssertionError(f"Container did not become ready for first-run setup: {last_error}")


def session_cookie(headers):
    raw = headers.get("Set-Cookie", "")
    for part in raw.split(";"):
        if part.strip().startswith("navil_session="):
            return part.strip()
    raise AssertionError("Successful setup/login did not set the navil_session cookie")


def expect(status, expected, label, body=b""):
    if status != expected:
        raise AssertionError(f"{label}: expected HTTP {expected}, got {status}: {body[:500]!r}")


wait_for_app()

status, body, _ = request("/api/not-a-real-route")
expect(status, 401, "Unauthenticated API protection", body)

status, body, headers = request(
    "/api/auth/setup",
    {
        "username": USERNAME,
        "password": PASSWORD,
        "password_confirmation": PASSWORD,
    },
)
expect(status, 200, "First-run owner setup", body)
cookie = session_cookie(headers)
if json.loads(body).get("ok") is not True:
    raise AssertionError(f"Owner setup did not report success: {body!r}")

# The auth key must be private inside the running container.
mode = subprocess.check_output(
    ["docker", "exec", CONTAINER, "stat", "-c", "%a", "/data/app_auth.key"],
    text=True,
).strip()
if mode != "600":
    raise AssertionError(f"Expected /data/app_auth.key mode 600, got {mode!r}")

status, body, _ = request("/", cookie=cookie)
expect(status, 200, "Authenticated web UI", body)

# Recreate the process while keeping the same named /data volume.
subprocess.run(["docker", "restart", CONTAINER], check=True, capture_output=True, text=True)
deadline = time.monotonic() + 40
while time.monotonic() < deadline:
    try:
        status, body, _ = request("/api/auth/status")
        if status == 200 and json.loads(body).get("setup_required") is False:
            break
    except Exception:
        pass
    time.sleep(1)
else:
    raise AssertionError("Owner account did not persist after container restart")

status, body, headers = request(
    "/api/auth/login",
    {"username": USERNAME, "password": PASSWORD},
)
expect(status, 200, "Login after container restart", body)
cookie = session_cookie(headers)
status, body, _ = request("/", cookie=cookie)
expect(status, 200, "Authenticated UI after container restart", body)

print("PASS: container HTTP readiness, auth boundary, first-run setup, private auth-key permissions, login, and /data persistence across restart.")
