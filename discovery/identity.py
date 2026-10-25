"""Persistent MusicBrainz identities for library artists and albums (background job).

Each artist and album gets one stored record, keyed by its Navidrome ID under the Navidrome
generation. A record is written once and kept: later runs resolve only items with no record.
A failed lookup writes nothing, so it is retried. A lookup that answered with no match is stored
as ``unresolved``, so it is not asked again.

Sources, in order of preference:
- Artists: the Navidrome tag (``getArtist``), then an exact-name MusicBrainz batch.
- Albums: the release MBID Navidrome tags, mapped to its release group in batches, then an
  exact artist-and-title MusicBrainz batch.

The job is injected with its providers and store, so it has no network or database of its own.
"""

from __future__ import annotations

import threading
import re
from collections.abc import Callable, Mapping
from typing import Any

from discovery.recommendations import is_various_artists
from discovery.search.index import OwnedData

UNRESOLVED = "unresolved"
NAME_CHUNK = 100
ALBUM_CHUNK = 100


IDENTITY_NAMESPACE = "identity:navidrome"
MBID_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
KINDS = ("artist", "album")


def identity_prefix(generation: Any) -> str:
    return f"identity:navidrome{generation}:"


def identity_name(generation: Any, kind: str, item_id: str) -> str:
    return f"{identity_prefix(generation)}{kind}:{item_id}"


def record_for(kind: str, mbid: str | None, source: str) -> dict[str, Any]:
    """A stored record for one item. ``mbid`` is the artist MBID, or the release-group MBID for an album."""
    return _record(kind, mbid, source)


def purge_stale_identities(delete_except: Callable[[str, str], int], generation: Any) -> int:
    """Delete identity records of every other Navidrome generation (section 5.2 cleanup).

    Records of the current generation are kept. ``delete_except(prefix, keep_prefix)`` is the
    store's prefix delete.
    """
    return delete_except(IDENTITY_NAMESPACE, identity_prefix(generation))


def load_identities(read_prefix: Callable[[str], Mapping[str, Any]], generation: Any) -> dict[str, dict[str, Any]]:
    """Stored identities for one Navidrome generation, shaped for ``build_owned_data``.

    Keys are ``artist:{id}`` and ``album:{id}``. Unresolved records load with null MBIDs.
    """
    prefix = identity_prefix(generation)
    found: dict[str, dict[str, Any]] = {}
    for name, record in read_prefix(prefix).items():
        if not isinstance(record, dict):
            continue
        item = name[len(prefix):]
        if item.startswith("artist:"):
            found[item] = {"mbid": record.get("mbid")}
        elif item.startswith("album:"):
            found[item] = {"release_group_mbid": record.get("release_group_mbid")}
    return found


def _record(kind: str, mbid: str | None, source: str) -> dict[str, Any]:
    if kind == "artist":
        return {"mbid": mbid, "source": source}
    return {"release_group_mbid": mbid, "source": source}


def resolve_identities(
    data: OwnedData,
    *,
    navidrome_mbid: Callable[[str], str | None],
    musicbrainz: Any,
    read_prefix: Callable[[str], Mapping[str, Any]],
    write_many: Callable[[dict[str, Any]], None],
    remaining: Callable[[], float],
    cancelled: threading.Event,
) -> dict[str, int]:
    """Resolve and store identities for every artist and album of ``data`` that has none yet.

    Returns counts of records written: ``artists``, ``albums``, ``unresolved``.
    """
    prefix = identity_prefix(data.generation)
    stored = set(read_prefix(prefix))
    counts = {"artists": 0, "albums": 0, "unresolved": 0}

    def save(records: dict[str, dict[str, Any]], kind: str) -> None:
        if not records:
            return
        write_many({f"{prefix}{k}": v for k, v in records.items()})
        counts[kind] += len(records)
        counts["unresolved"] += sum(1 for v in records.values() if v["source"] == UNRESOLVED)

    # Artists -----------------------------------------------------------------
    todo = [a for a in data.artists if f"{prefix}artist:{a['id']}" not in stored]
    key_counts: dict[str, int] = {}
    for artist in data.artists:
        key_counts[artist["key"]] = key_counts.get(artist["key"], 0) + 1

    untagged: list[dict[str, Any]] = []
    tagged: dict[str, dict[str, Any]] = {}
    for artist in todo:
        try:
            mbid = navidrome_mbid(artist["id"])
        except Exception:
            continue  # Not recorded, so the next run asks again.
        if mbid:
            tagged[f"artist:{artist['id']}"] = _record("artist", mbid, "navidrome")
        else:
            untagged.append(artist)
    save(tagged, "artists")

    # Two library artists with one name are two different artists; a name lookup cannot tell them apart.
    unique = [a for a in untagged if key_counts[a["key"]] == 1]
    ambiguous = {f"artist:{a['id']}": _record("artist", None, UNRESOLVED) for a in untagged if key_counts[a["key"]] > 1}
    save(ambiguous, "artists")

    for start in range(0, len(unique), NAME_CHUNK):
        chunk = unique[start:start + NAME_CHUNK]
        try:
            found = musicbrainz.artist_identities(
                [a["name"] for a in chunk], remaining=remaining, cancelled=cancelled,
            )
        except Exception:
            continue  # This chunk is retried on the next run.
        records = {
            f"artist:{a['id']}": _record("artist", found.get(a["key"]), "musicbrainz" if a["key"] in found else UNRESOLVED)
            for a in chunk
        }
        save(records, "artists")

    # Albums ------------------------------------------------------------------
    albums = [al for al in data.albums if f"{prefix}album:{al['id']}" not in stored]
    with_release = [al for al in albums if al.get("release_mbid")]
    without = [al for al in albums if not al.get("release_mbid")]

    groups: dict[str, str] = {}
    if with_release:
        try:
            groups = musicbrainz.release_groups_for_releases(
                [al["release_mbid"] for al in with_release], remaining=remaining, cancelled=cancelled,
            )
        except Exception:
            return counts  # Nothing from this run is lost; the album step waits for the next run.
        for start in range(0, len(with_release), ALBUM_CHUNK):
            chunk = with_release[start:start + ALBUM_CHUNK]
            resolved = {
                f"album:{al['id']}": _record("album", groups[al["release_mbid"]], "musicbrainz")
                for al in chunk if al["release_mbid"] in groups
            }
            save(resolved, "albums")
            without.extend(al for al in chunk if al["release_mbid"] not in groups)

    for start in range(0, len(without), ALBUM_CHUNK):
        chunk = without[start:start + ALBUM_CHUNK]
        compilations = [al for al in chunk if _is_compilation(al)]
        save({f"album:{al['id']}": _record("album", None, UNRESOLVED) for al in compilations}, "albums")
        lookups = [al for al in chunk if not _is_compilation(al)]
        if not lookups:
            continue
        try:
            found = musicbrainz.album_identities(
                [(al["artist"], al["name"], al["year"]) for al in lookups],
                remaining=remaining, cancelled=cancelled,
            )
        except Exception:
            continue
        records = {}
        for al in lookups:
            key = (al["artist_key"], al["name_key"])
            if key in found:
                records[f"album:{al['id']}"] = _record("album", found[key], "musicbrainz")
            else:
                records[f"album:{al['id']}"] = _record("album", None, UNRESOLVED)
        save(records, "albums")

    return counts


def _is_compilation(album: Mapping[str, Any]) -> bool:
    return is_various_artists(album.get("artist") or "")


class IdentityJob:
    """Runs one identity pass at a time, on a background thread.

    A pass requested while one is running is not dropped: it is queued, and runs once the current
    pass finishes. Only the latest queued request is kept, since each pass reads the library it is given.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._running = False
        self._queued: tuple[Callable[[], Mapping[str, int]], Callable[[], None]] | None = None

    def start(self, run: Callable[[], Mapping[str, int]], on_changed: Callable[[], None]) -> bool:
        """Start a pass now, or queue it behind the running one. Returns True when started now."""
        with self._lock:
            if self._running:
                self._queued = (run, on_changed)
                return False
            self._running = True
        threading.Thread(target=self._work, args=(run, on_changed), daemon=True).start()
        return True

    def _work(self, run: Callable[[], Mapping[str, int]], on_changed: Callable[[], None]) -> None:
        while True:
            try:
                counts = run()
                if counts.get("artists") or counts.get("albums"):
                    on_changed()
            except Exception:
                # Identities are an enrichment. A failed pass changes nothing and is retried on the next build.
                pass
            with self._lock:
                if self._queued is None:
                    self._running = False
                    return
                run, on_changed = self._queued
                self._queued = None
