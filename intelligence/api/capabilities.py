"""``/api/capabilities`` body: which intelligence features are populated (docs/ServerV2.md 8).

Clients hide absent sections instead of rendering errors, so every feature carries an
explicit state and, when it is not available, a reason. Facts about the outside world
(is ListenBrainz connected, is a sonic plugin installed) are passed in by the caller;
this module never touches the network, the filesystem or a provider.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

from ..graph.paths import SLICE_RESOURCE as PATHS_RESOURCE
from ..store import LATEST_VERSION, generations

CONTRACT_VERSION = 1

# feature name -> the resource whose data_version shows it has been populated.
FEATURES: dict[str, str] = {
    "library_health": "health",
    "unresolved_queue": "unresolved",
    "insights": "insights",
    # Discovery paths are built from the MusicBrainz slice; "available" means the slice is loaded.
    "paths": PATHS_RESOURCE,
}


@dataclass(frozen=True)
class ServerFacts:
    """Outside-world facts the store cannot know; unknown means False."""

    sonic_available: bool = False
    listenbrainz_connected: bool = False
    graph_coverage: str = "none"


GRAPH_COVERAGE_CLASSES = ("none", "partial", "broad")


def build_capabilities(db: sqlite3.Connection, facts: ServerFacts | None = None) -> dict[str, Any]:
    """Describe what this server can serve right now."""
    facts = facts or ServerFacts()
    coverage = facts.graph_coverage if facts.graph_coverage in GRAPH_COVERAGE_CLASSES else "none"
    versions = generations.data_versions(db)
    return {
        "contract_version": CONTRACT_VERSION,
        "schema_version": LATEST_VERSION,
        "generation": generations.current_generation(db),
        "cursor": generations.change_seq(db),
        "graph_coverage": coverage,
        "sonic_available": bool(facts.sonic_available),
        "listenbrainz_connected": bool(facts.listenbrainz_connected),
        "features": {name: _feature(resource, versions) for name, resource in FEATURES.items()},
        "data_versions": dict(sorted(versions.items())),
    }


def _feature(resource: str, versions: dict[str, int]) -> dict[str, Any]:
    version = versions.get(resource, 0)
    if version > 0:
        return {"available": True, "resource": resource, "data_version": version}
    return {"available": False, "resource": resource, "data_version": 0, "reason": "not_populated"}
