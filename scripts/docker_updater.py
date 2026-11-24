"""Opt-in host process that applies only a published Discair Compose update."""

import argparse
import fcntl
from http.server import BaseHTTPRequestHandler
import json
import logging
import os
from pathlib import Path
import socketserver
import stat
import subprocess
from tempfile import TemporaryDirectory
from threading import Lock, Thread

from integrations.docker_release import IMAGE, ReleaseCache, valid_digest, version_key

SERVICES = ("discair", "worker")
LOG = logging.getLogger(__name__)


def _docker(*args, timeout=30):
    return subprocess.run(
        ["docker", *args], check=True, timeout=timeout, capture_output=True, text=True,
    ).stdout.strip()


def deploy(compose: tuple[str, ...], digest: str, version: str):
    """Pull the pinned image and recreate both existing services with their volumes."""
    if not valid_digest(digest):
        raise ValueError("Invalid image digest")
    services = json.loads(_docker(*compose, "config", "--format", "json"))["services"]
    if any(services.get(name, {}).get("image") != f"{IMAGE}:latest" for name in SERVICES):
        raise ValueError("Both Compose services must track the official latest image")

    if any(not services[name].get("healthcheck") or services[name]["healthcheck"].get("disable")
           for name in SERVICES):
        raise ValueError("Both Compose services must have an enabled health check")

    container = _docker(*compose, "ps", "-q", "discair")
    env = json.loads(_docker("inspect", "--format", "{{json .Config.Env}}", container))
    current = next((value.removeprefix("APP_VERSION=") for value in env if value.startswith("APP_VERSION=")), "")
    if not version_key(current) or version_key(version) <= version_key(current):
        raise ValueError("The running service must be an older release")

    previous = _docker("inspect", "--format", "{{.Image}}", container)
    LOG.info("Previous web image ID: %s", previous)
    image = f"{IMAGE}@{digest}"
    _docker("pull", image, timeout=900)
    with TemporaryDirectory(prefix="discair-update-") as directory:
        override = Path(directory) / "image.json"
        override.write_text(json.dumps({"services": {name: {"image": image} for name in SERVICES}}))
        _docker(
            *compose, "-f", str(override), "up", "-d", "--no-deps", "--no-build",
            "--pull", "never", "--wait", "--wait-timeout", "240", *SERVICES, timeout=300,
        )
    _docker("image", "tag", image, f"{IMAGE}:latest")


class UpdateJob:
    """Keep managing the job and serving status while the web container restarts."""

    def __init__(self, registry, install):
        self._registry = registry
        self._install = install
        self._lock = Lock()
        self._status = {"state": "idle"}

    def status(self):
        """Return a snapshot the web container can poll."""
        with self._lock:
            return self._status.copy()

    def start(self, digest):
        """Queue one confirmed image while refusing concurrent installs."""
        with self._lock:
            if self._status["state"] == "running":
                return None
            self._status = {"state": "running", "digest": digest}
            Thread(target=self._run, args=(digest,)).start()
            return self._status.copy()

    def _run(self, digest):
        state = "failed"
        try:
            release = self._registry.get()
            if release is None or release.digest != digest:
                raise ValueError("The requested digest no longer matches the published release")
            self._install(digest, release.version)
            state = "succeeded"
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError) as exc:
            LOG.error("Update %s failed: %s", digest, exc)
        finally:
            with self._lock:
                self._status = {"state": state, "digest": digest}


class UpdaterServer(socketserver.UnixStreamServer):
    """Local HTTP interface reachable only through the explicitly shared socket."""

    def __init__(self, path, job):
        self.job = job
        super().__init__(path, Handler)


class Handler(BaseHTTPRequestHandler):
    """Handle local status and install requests."""

    timeout = 3

    def do_GET(self):  # pylint: disable=invalid-name
        """Read the last job."""
        if self.path == "/update":
            self._respond(200, self.server.job.status())
        else:
            self._respond(404, {})

    def do_POST(self):  # pylint: disable=invalid-name
        """Accept a bounded digest-only request."""
        if self.path != "/update":
            self._respond(404, {})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 128:
                raise ValueError("Invalid request size")
            digest = json.loads(self.rfile.read(length))["digest"]
            if not isinstance(digest, str) or not valid_digest(digest):
                raise ValueError("Invalid digest")
        except (KeyError, TypeError, ValueError):
            self._respond(400, {})
            return
        status = self.server.job.start(digest)
        self._respond(202 if status else 409, status or {})

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def address_string(self):
        """Format the local peer for the standard HTTP logger."""
        return "unix socket"


def serve(path: Path, job):
    """Allow one updater per socket and clean up only its stale socket on restart."""
    with path.with_suffix(".lock").open("a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            if not stat.S_ISSOCK(path.lstat().st_mode):
                raise ValueError(f"Refusing to replace {path}")
            path.unlink()
        except FileNotFoundError:
            pass
        with UpdaterServer(str(path), job) as server:
            os.chmod(path, 0o660)
            try:
                server.serve_forever()
            finally:
                path.unlink(missing_ok=True)


def main():
    """Read host-owned configuration and start the socket listener."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--socket", type=Path, required=True)
    parser.add_argument("--project-directory", type=Path, required=True)
    parser.add_argument("--compose-file", action="append", required=True)
    args = parser.parse_args()
    compose = ["compose", "--project-directory", str(args.project_directory.resolve())]
    for filename in args.compose_file:
        compose.extend(["-f", str(Path(filename).resolve())])
    logging.basicConfig(level=logging.INFO)
    job = UpdateJob(ReleaseCache(), lambda digest, version: deploy(tuple(compose), digest, version))
    serve(args.socket, job)


if __name__ == "__main__":
    main()
