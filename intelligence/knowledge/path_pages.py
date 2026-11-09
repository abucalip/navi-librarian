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
from ..graph import album_gaps, album_paths, paths
from ..graph.paths import PATH_KINDS, PathLimits

ALBUM_TYPES = ("release", "release_group")


def path_page(db: sqlite3.Connection, *, kind: str, mbid: str | None = None, navidrome_id: str | None = None,
              type: str | None = None, limits: PathLimits = PathLimits(), refresh: bool = False
              ) -> dict[str, Any] | None:
    """The public path of ``kind`` from one artist, person or group; None when the start is unknown.

    ``ValueError`` for a kind with no builder (dropped or parked kinds say why), a missing identifier or
    a start of the wrong type.
    """
    album = kind in album_paths.ALBUM_PATH_KINDS
    if not album and kind not in PATH_KINDS:
        raise ValueError(paths.NOT_BUILT.get(kind) or album_paths.NOT_BUILT.get(kind) or f"unknown path kind: {kind!r}")
    if album != (type in ALBUM_TYPES):
        raise ValueError(f"kind {kind!r} does not start at type {type!r}")
    start = KnowledgeReader(db).entity(type, mbid=mbid, navidrome_id=navidrome_id)
    if start is None:
        return None
    build = album_paths.cached_album_path if album else paths.cached_path
    path = build(db, start["id"], kind, limits=limits, refresh=refresh)
    if path is None:
        return None
    path = dict(path)
    built = path.pop("built_from", {})
    path.pop("presentation_version", None)  # cache invalidation detail, not part of the public response
    return public({**path, "sources": {SLICE_SOURCE: {"data_version": built.get(paths.SLICE_RESOURCE)}}})


def gaps_page(db: sqlite3.Connection, records, *, mbid: str | None = None, navidrome_id: str | None = None,
              type: str | None = None, limits: PathLimits = PathLimits()) -> dict[str, Any] | None:
    """Listen-through Gaps from one release in the public shape; None when the start is unknown.

    ``records`` are the caller's album play records (None when play data could not be read). Not cached:
    the result depends on play history, which changes without a new store generation.
    """
    if type not in ALBUM_TYPES:
        raise ValueError(f"kind {album_gaps.GAPS_KIND!r} does not start at type {type!r}")
    start = KnowledgeReader(db).entity(type, mbid=mbid, navidrome_id=navidrome_id)
    if start is None:
        return None
    path = album_gaps.build_gaps_path(db, start["id"], records, limits=limits)
    if path is None:
        return None
    path = dict(path)
    built = path.pop("built_from", {})
    path.pop("presentation_version", None)
    return public({**path, "sources": {SLICE_SOURCE: {"data_version": built.get(paths.SLICE_RESOURCE)}}})
