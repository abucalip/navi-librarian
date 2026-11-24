"""Read the published Discair Docker release without contacting a Docker daemon."""

from dataclasses import dataclass
import platform
import re
from time import monotonic
from threading import Lock

import httpx

REPOSITORY = "abucalip/navi-librarian"
IMAGE = f"ghcr.io/{REPOSITORY}"
_REGISTRY = f"https://ghcr.io/v2/{REPOSITORY}"
_INDEX = "application/vnd.oci.image.index.v1+json"
_MANIFEST = "application/vnd.oci.image.manifest.v1+json"


@dataclass(frozen=True)
class DockerRelease:
    """The release tag and immutable multi-platform image digest."""

    version: str
    digest: str


def version_key(version: str) -> tuple[int, ...]:
    """Order the stable vMAJOR.MINOR[.PATCH] tags supported by the release workflow."""
    if not re.fullmatch(r"v[0-9]{1,9}\.[0-9]{1,9}(?:\.[0-9]{1,9})?", version):
        return ()
    parts = tuple(map(int, version[1:].split(".")))
    return parts if len(parts) == 3 else (*parts, 0)


def valid_digest(value: str) -> bool:
    """Accept only complete SHA-256 digests."""
    return re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def _get(client: httpx.Client, url: str, **kwargs) -> httpx.Response:
    return client.get(url, **kwargs).raise_for_status()


def published_release(client: httpx.Client, architecture: str) -> DockerRelease:
    """Resolve latest through the registry index and read APP_VERSION from its image config."""
    token = _get(client, "https://ghcr.io/token", params={
        "service": "ghcr.io", "scope": f"repository:{REPOSITORY}:pull",
    }).json()["token"]
    headers = {"Authorization": f"Bearer {token}", "Accept": _INDEX}
    index = _get(client, f"{_REGISTRY}/manifests/latest", headers=headers)
    release_digest = index.headers["Docker-Content-Digest"]
    descriptor = next(
        row for row in index.json()["manifests"]
        if row.get("platform", {}).get("os") == "linux"
        and row["platform"].get("architecture") == architecture
    )
    manifest_digest = descriptor["digest"]
    if not valid_digest(release_digest) or not valid_digest(manifest_digest):
        raise ValueError("Invalid registry digest")
    headers["Accept"] = _MANIFEST
    manifest = _get(client, f"{_REGISTRY}/manifests/{manifest_digest}", headers=headers)
    config_digest = manifest.json()["config"]["digest"]
    if not valid_digest(config_digest):
        raise ValueError("Invalid image config digest")
    config = _get(client, f"{_REGISTRY}/blobs/{config_digest}", headers=headers)
    version = next(
        value.removeprefix("APP_VERSION=") for value in config.json()["config"]["Env"]
        if value.startswith("APP_VERSION=")
    )
    if not version_key(version):
        raise ValueError("The published image has no stable release version")
    return DockerRelease(version, release_digest)


class ReleaseCache:
    """Share registry results across requests and briefly back off on failures."""

    def __init__(self):
        self._lock = Lock()
        self._expires = 0.0
        self._release = None

    def get(self) -> DockerRelease | None:
        """Return the latest release, or None when the check cannot be completed."""
        with self._lock:
            if monotonic() < self._expires:
                return self._release
            architecture = {"x86_64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(
                platform.machine()
            )
            try:
                with httpx.Client(timeout=4, follow_redirects=True, max_redirects=3) as client:
                    self._release = published_release(client, architecture) if architecture else None
            except (httpx.HTTPError, AttributeError, KeyError, StopIteration, TypeError, ValueError):
                self._release = None
            self._expires = monotonic() + (1800 if self._release else 120)
            return self._release
