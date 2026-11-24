"""Published registry, authenticated web API and isolated host updater contracts."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, Thread
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import docker_update
from app.security.app_login_middleware import create_app_login_middleware
from integrations.docker_release import DockerRelease, published_release, version_key
from scripts import docker_updater

DIGEST = "sha256:" + "a" * 64
MANIFEST = "sha256:" + "b" * 64
CONFIG = "sha256:" + "c" * 64


def test_registry_resolves_version_from_published_image():
    def registry(request):
        path = request.url.path
        if path == "/token":
            assert request.url.params["scope"] == "repository:abucalip/navi-librarian:pull"
            return httpx.Response(200, json={"token": "registry-token"})
        assert request.headers["Authorization"] == "Bearer registry-token"
        if path.endswith("/manifests/latest"):
            return httpx.Response(200, headers={"Docker-Content-Digest": DIGEST}, json={
                "manifests": [
                    {"platform": {"os": "unknown"}, "digest": CONFIG},
                    {"platform": {"os": "linux", "architecture": "arm64"}, "digest": MANIFEST},
                ],
            })
        if path.endswith("/manifests/" + MANIFEST):
            return httpx.Response(200, json={"config": {"digest": CONFIG}})
        assert path.endswith("/blobs/" + CONFIG)
        return httpx.Response(200, json={"config": {"Env": ["APP_VERSION=v1.10"]}})

    with httpx.Client(transport=httpx.MockTransport(registry)) as client:
        assert published_release(client, "arm64") == DockerRelease("v1.10", DIGEST)
    assert version_key("v1.10") > version_key("v1.9.12")
    assert version_key("v1.10") == version_key("v1.10.0")
    assert not version_key("v1.10-1-g1234")


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_VERSION", "v1.9")
    monkeypatch.setattr(docker_update._registry, "get", lambda: DockerRelease("v1.10", DIGEST))
    app = FastAPI()
    app.middleware("http")(create_app_login_middleware(
        auth_configured=lambda: True, session_username=lambda token: token == "test-owner",
        cookie_name="session",
    ))
    app.include_router(docker_update.router)
    with TestClient(app) as test_client:
        yield test_client


def test_update_requires_owner_session_and_explicit_confirmation(client, monkeypatch):
    def updater(method, *, payload=None):
        assert method == "POST"
        assert payload == {"digest": DIGEST}
        return {"state": "running", "digest": DIGEST}

    monkeypatch.setattr(docker_update, "_updater", updater)
    path = "/api/docker-update/install"
    body = {"digest": DIGEST}
    headers = {"X-Discair-Update": "install"}
    assert client.get("/api/docker-update").status_code == 401
    assert client.get(path).status_code == 401
    assert client.post(path, json=body, headers=headers).status_code == 401
    client.cookies.set("session", "test-owner")
    assert client.post(path, json=body).status_code == 403
    assert client.post(path, json={"digest": "latest"}, headers=headers).status_code == 422
    different = {"digest": "sha256:" + "f" * 64}
    assert client.post(path, json=different, headers=headers).status_code == 409
    assert client.post(path, json=body, headers=headers).status_code == 202


def test_notice_works_without_updater_and_handles_old_or_unknown_build(client, monkeypatch):
    monkeypatch.delenv("DISCAIR_UPDATER_SOCKET", raising=False)
    client.cookies.set("session", "test-owner")
    assert client.get("/api/docker-update").json() == {
        "available": {"version": "v1.10", "digest": DIGEST}, "installer": None,
    }
    headers = {"X-Discair-Update": "install"}
    assert client.post("/api/docker-update/install", json={"digest": DIGEST}, headers=headers).status_code == 503
    monkeypatch.setenv("APP_VERSION", "v1.10")
    assert client.get("/api/docker-update").json()["available"] is None
    monkeypatch.setenv("APP_VERSION", "dev")
    assert client.get("/api/docker-update").json()["available"] is None


def test_socket_serves_status_during_install(monkeypatch):
    ready, finish = Event(), Event()

    def install(digest, version):
        assert (digest, version) == (DIGEST, "v1.10")
        ready.set()
        finish.wait(5)

    job = docker_updater.UpdateJob(SimpleNamespace(get=lambda: DockerRelease("v1.10", DIGEST)), install)
    with TemporaryDirectory(dir="/tmp") as directory:
        path = str(Path(directory) / "update.sock")
        monkeypatch.setenv("DISCAIR_UPDATER_SOCKET", path)
        try:
            server = docker_updater.UpdaterServer(path, job)
        except PermissionError as exc:
            pytest.skip(f"Unix socket bind unavailable: {exc}")
        with server:
            worker = Thread(target=server.serve_forever)
            worker.start()
            try:
                assert docker_update._updater("GET") == {"state": "idle"}
                assert docker_update._updater("POST", payload={"digest": DIGEST})["state"] == "running"
                assert ready.wait(2)
                assert docker_update._updater("GET")["state"] == "running"
                with pytest.raises(docker_update.HTTPException) as exc:
                    docker_update._updater("POST", payload={"digest": DIGEST})
                assert exc.value.status_code == 409
            finally:
                finish.set()
                server.shutdown()
                worker.join()


def test_deploy_pins_both_services_preserves_volumes_and_waits(monkeypatch):
    image = f"{docker_updater.IMAGE}@{DIGEST}"
    calls = []

    def docker(*args, **_):
        calls.append(args)
        if "config" in args:
            return json.dumps({"services": {
                name: {"image": f"{docker_updater.IMAGE}:latest", "healthcheck": {"test": ["CMD", "true"]}}
                for name in docker_updater.SERVICES
            }})
        if ".Config.Env" in " ".join(args):
            return '["APP_VERSION=v1.9"]'
        if "up" in args:
            override = json.loads(Path(args[args.index("up") - 1]).read_text())
            assert override == {"services": {"discair": {"image": image}, "worker": {"image": image}}}
            assert args[args.index("up"):] == (
                "up", "-d", "--no-deps", "--no-build", "--pull", "never",
                "--wait", "--wait-timeout", "240", "discair", "worker",
            )
        return "container-id"

    monkeypatch.setattr(docker_updater, "_docker", docker)
    docker_updater.deploy(("compose", "-f", "compose.yaml"), DIGEST, "v1.10")
    assert ("pull", image) in calls
    assert calls[-1] == ("image", "tag", image, f"{docker_updater.IMAGE}:latest")
    calls.clear()
    with pytest.raises(ValueError, match="older release"):
        docker_updater.deploy(("compose", "-f", "compose.yaml"), DIGEST, "v1.9")
    assert all("pull" not in call for call in calls)


def test_job_refuses_unpublished_digest_and_reports_terminal_status(monkeypatch):
    installs = []

    class ImmediateThread:
        def __init__(self, target, args):
            self.run = lambda: target(*args)

        def start(self):
            # Run when the test releases the launch lock.
            launches.append(self.run)

    launches = []
    monkeypatch.setattr(docker_updater, "Thread", ImmediateThread)
    job = docker_updater.UpdateJob(
        SimpleNamespace(get=lambda: DockerRelease("v1.10", DIGEST)),
        lambda *args: installs.append(args),
    )
    different = "sha256:" + "e" * 64
    assert job.start(different)["state"] == "running"
    assert job.start(DIGEST) is None
    launches.pop()()
    assert job.status() == {"state": "failed", "digest": different}
    assert installs == []
    assert job.start(DIGEST)["state"] == "running"
    launches.pop()()
    assert job.status() == {"state": "succeeded", "digest": DIGEST}
    assert installs == [(DIGEST, "v1.10")]
