"""Listens loader for taste profiles (Phase 6 item 1, slice 2).

Turns raw ListenBrainz-shaped listens (``listened_at`` plus ``track_metadata``, the shape
``discovery.history_fetch`` already returns) into :class:`~intelligence.taste.profiles.Listen`
values by reading the knowledge store. Read-only: it never writes the store, calls a provider or
changes a recommendation weight.

Where each dimension comes from:

* ``area``: the listen's artist entity, edge ``area`` to an area entity;
* ``era``: the earliest year in ``release_facts.date`` of the releases the recording ``appears_on``,
  as a decade (``"1970s"``);
* ``label``: label entities linked to those releases (either edge direction);
* ``collaborator``: person, artist or group entities linked to the recording, other than the
  listened artists;
* ``genre``: not stored in the knowledge store (community tags are deliberately not kept), so it
  comes only from the optional ``genres_by_recording`` map the caller passes (for example the
  Navidrome song genres). With no map the dimension is simply empty and shows as low-sample.

A listen the store cannot place keeps an empty ``attrs`` and is counted as ``unmatched``, so missing
metadata is visible in the result and never read as taste.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ..store import repositories as repo
from .profiles import Listen

REL_AREA = "area"
REL_APPEARS_ON = "appears_on"
PERSON_TYPES = ("artist", "person", "group")


@dataclass(frozen=True)
class LoadResult:
    listens: tuple[Listen, ...]
    total: int            # raw listens read
    unusable: int         # no usable timestamp; dropped
    unmatched: int        # usable, but no recording or artist in the store
    attributed: Mapping[str, int]   # dimension -> listens carrying at least one value


def load_listens(
    db: sqlite3.Connection,
    raw: Iterable[Mapping[str, Any]],
    *,
    genres_by_recording: Mapping[str, Iterable[str]] | None = None,
) -> LoadResult:
    resolver = _Resolver(db)
    genres = genres_by_recording or {}
    out: list[Listen] = []
    total = unusable = unmatched = 0
    counts = {d: 0 for d in ("genre", "era", "area", "label", "collaborator")}
    for item in raw:
        total += 1
        ts = _timestamp(item)
        if ts is None:
            unusable += 1
            continue
        recording_mbid, artist_mbids = _ids(item)
        attrs = resolver.attrs(recording_mbid, artist_mbids)
        listed = tuple(dict.fromkeys(g for g in genres.get(recording_mbid or "", ()) if g))
        if listed:
            attrs["genre"] = listed
        if not attrs:
            unmatched += 1
        for dim in attrs:
            counts[dim] += 1
        out.append(Listen(ts, attrs))
    return LoadResult(tuple(out), total, unusable, unmatched, counts)


def _timestamp(item: Mapping[str, Any]) -> float | None:
    try:
        ts = float(item.get("listened_at"))
    except (TypeError, ValueError):
        return None
    return ts if ts > 0 else None


def _ids(item: Mapping[str, Any]) -> tuple[str | None, tuple[str, ...]]:
    meta = item.get("track_metadata") if isinstance(item.get("track_metadata"), Mapping) else {}
    info = meta.get("additional_info") if isinstance(meta.get("additional_info"), Mapping) else {}
    mapping = meta.get("mbid_mapping") if isinstance(meta.get("mbid_mapping"), Mapping) else {}
    recording = mapping.get("recording_mbid") or info.get("recording_mbid") or None
    artists = mapping.get("artist_mbids") or info.get("artist_mbids") or ()
    if isinstance(artists, str):
        artists = (artists,)
    return (str(recording) if recording else None), tuple(str(a) for a in artists if a)


class _Resolver:
    """Per-run lookups with small caches; the same artist or recording recurs across many listens."""

    def __init__(self, db: sqlite3.Connection):
        self._db = db
        self._artist: dict[str, tuple[str, ...]] = {}
        self._recording: dict[str, dict[str, tuple[str, ...]]] = {}

    def attrs(self, recording_mbid: str | None, artist_mbids: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
        out: dict[str, tuple[str, ...]] = {}
        areas = tuple(dict.fromkeys(a for m in artist_mbids for a in self._areas(m)))
        if areas:
            out["area"] = areas
        if recording_mbid:
            for dim, values in self._recording_attrs(recording_mbid, artist_mbids).items():
                if values:
                    out[dim] = values
        return out

    def _areas(self, artist_mbid: str) -> tuple[str, ...]:
        if artist_mbid not in self._artist:
            names: list[str] = []
            for etype in PERSON_TYPES:
                entity = repo.find_entity(self._db, etype, mbid=artist_mbid)
                if entity:
                    for edge in repo.edges_from(self._db, entity["id"], REL_AREA):
                        area = repo.get_entity(self._db, edge["to_id"])
                        if area and area["type"] == "area" and area["canonical_name"]:
                            names.append(area["canonical_name"])
                    break
            self._artist[artist_mbid] = tuple(dict.fromkeys(names))
        return self._artist[artist_mbid]

    def _recording_attrs(self, mbid: str, artist_mbids: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
        if mbid not in self._recording:
            self._recording[mbid] = self._read_recording(mbid)
        found = self._recording[mbid]
        skip = set(artist_mbids)
        collaborators = tuple(n for m, n in zip(found.get("_collab_mbids", ()), found.get("collaborator", ()))
                              if m not in skip)
        return {"era": found.get("era", ()), "label": found.get("label", ()), "collaborator": collaborators}

    def _read_recording(self, mbid: str) -> dict[str, tuple[str, ...]]:
        db = self._db
        recording = repo.find_entity(db, "recording", mbid=mbid)
        if not recording:
            return {}
        years: list[int] = []
        labels: list[str] = []
        for edge in repo.edges_from(db, recording["id"], REL_APPEARS_ON):
            row = db.execute("SELECT date FROM release_facts WHERE entity_id = ?", (edge["to_id"],)).fetchone()
            year = _year(row["date"]) if row else None
            if year is not None:
                years.append(year)
            labels.extend(self._labels_of(edge["to_id"]))
        collab_mbids: list[str] = []
        collab_names: list[str] = []
        for edge, other_id in [(e, e["to_id"]) for e in repo.edges_from(db, recording["id"])] + \
                             [(e, e["from_id"]) for e in repo.edges_to(db, recording["id"])]:
            other = repo.get_entity(db, other_id)
            if other and other["type"] in PERSON_TYPES and other["canonical_name"] and other["mbid"] \
                    and other["mbid"] not in collab_mbids:
                collab_mbids.append(other["mbid"])
                collab_names.append(other["canonical_name"])
        return {
            "era": (f"{min(years) // 10 * 10}s",) if years else (),
            "label": tuple(dict.fromkeys(labels)),
            "collaborator": tuple(collab_names),
            "_collab_mbids": tuple(collab_mbids),
        }

    def _labels_of(self, release_id: int) -> list[str]:
        db = self._db
        names: list[str] = []
        for other_id in [e["to_id"] for e in repo.edges_from(db, release_id)] + \
                        [e["from_id"] for e in repo.edges_to(db, release_id)]:
            other = repo.get_entity(db, other_id)
            if other and other["type"] == "label" and other["canonical_name"]:
                names.append(other["canonical_name"])
        return names


def _year(date: str | None) -> int | None:
    if not date or len(date) < 4 or not date[:4].isdigit():
        return None
    year = int(date[:4])
    return year if 1000 <= year <= 2999 else None
