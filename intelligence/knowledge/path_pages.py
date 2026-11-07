"""Public discovery-path page (Server V2 Phase 5): the path builders behind the knowledge reader's rules.

``path_page`` resolves the start the same way the other pages do (``mbid`` or ``navidrome_id`` plus a
type), asks :mod:`intelligence.graph.paths` for the path (cached by start, kind and generation) and
returns it in the public shape: ``mbid`` only, boolean ``owned`` flags. The only write is the path
cache in ``insights``. No provider traffic.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from .public import public
from .reader import KnowledgeReader, SLICE_SOURCE
from ..graph import paths
from ..graph.paths import PATH_KINDS, PathLimits


def path_page(db: sqlite3.Connection, *, kind: str, mbid: str | None = None, navidrome_id: str | None = None,
              type: str | None = None, limits: PathLimits = PathLimits(), refresh: bool = False
              ) -> dict[str, Any] | None:
    """The public path of ``kind`` from one artist, person or group; None when the start is unknown.

    ``ValueError`` for a kind with no builder (dropped or parked kinds say why), a missing identifier or
    a start of the wrong type.
    """
    if kind not in PATH_KINDS:
        raise ValueError(paths.NOT_BUILT.get(kind) or f"unknown path kind: {kind!r}")
    start = KnowledgeReader(db).entity(type, mbid=mbid, navidrome_id=navidrome_id)
    if start is None:
        return None
    path = paths.cached_path(db, start["id"], kind, limits=limits, refresh=refresh)
    if path is None:
        return None
    path = dict(path)
    built = path.pop("built_from", {})
    path.pop("presentation_version", None)  # cache invalidation detail, not part of the public response
    return public({**path, "sources": {SLICE_SOURCE: {"data_version": built.get(paths.SLICE_RESOURCE)}}})
