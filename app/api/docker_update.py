"""Owner-session endpoints for published Docker updates and the optional host updater."""

import os

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from integrations.docker_release import ReleaseCache, valid_digest, version_key

router = APIRouter(prefix="/api/docker-update")
_registry = ReleaseCache()


class InstallRequest(BaseModel):
    """The immutable digest shown to the owner before confirmation."""

    digest: str


def _updater(method, *, payload=None):
    path = os.environ.get("DISCAIR_UPDATER_SOCKET")
    if not path:
        return None
    try:
        transport = httpx.HTTPTransport(uds=path)
        with httpx.Client(transport=transport, timeout=3) as client:
            response = client.request(method, "http://localhost/update", json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 409:
            raise HTTPException(409, "An update is already running or the release changed.") from exc
        return None
    except (httpx.RequestError, ValueError):
        return None


@router.get("")
def update_status():
    """Return update availability and the host updater's last reported state."""
    installed = os.environ.get("APP_VERSION", "").strip()
    status = _updater("GET")
    release = _registry.get() if version_key(installed) else None
    newer = release and version_key(release.version) > version_key(installed)
    return {
        "available": {"version": release.version, "digest": release.digest} if newer else None,
        "installer": status,
    }


@router.get("/install")
def installation_status():
    """Poll the host without doing another registry check during a restart."""
    return _updater("GET")


@router.post("/install", status_code=202)
def install_update(body: InstallRequest, requested_with: str = Header(default="", alias="X-Discair-Update")):
    """Enqueue only the checked release from a same-origin owner UI request."""
    if requested_with != "install":
        raise HTTPException(403, "Update confirmation required.")
    if not valid_digest(body.digest):
        raise HTTPException(422, "Invalid image digest.")
    installed = version_key(os.environ.get("APP_VERSION", "").strip())
    release = _registry.get() if installed else None
    if not release or release.digest != body.digest or version_key(release.version) <= installed:
        raise HTTPException(409, "The checked update is no longer available.")
    result = _updater("POST", payload={"digest": release.digest})
    if not result:
        raise HTTPException(503, "The host updater is unavailable.")
    return result
