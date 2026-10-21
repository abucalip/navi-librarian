"""ListenBrainz batch metadata lookups for the flagged CF resolution path.

Replaces per-recording MusicBrainz calls (one per 1.1 s spacing) with one
recording batch call plus one release-group call per batch. Pure functions over
injected HTTP callables, so tests use stubs and never touch the network.

The batch endpoints return no secondary release types. Callers must therefore
enable this path only together with the batch title-marker filter; see
``discovery_candidate_supply.batch_title_marker_rejection``.
"""
from typing import Any, Callable, Mapping

LISTENBRAINZ_RECORDING_BATCH_URL = "https://api.listenbrainz.org/1/metadata/recording/"
LISTENBRAINZ_RELEASE_GROUP_URL = "https://api.listenbrainz.org/1/metadata/release_group/"
# Recordings per batch request. The live sample used 100; larger batches are unverified.
# Without "release" in inc the response has no release or release-group object.
BATCH_RECORDING_INCLUDES = "artist release"
BATCH_RECORDING_CHUNK = 100
# Release groups per GET. The endpoint answers 200 up to 80 comma-joined MBIDs and
# fails from 81 (dropped connection, then HTML 502 at 83), whichever MBIDs they are;
# 50 keeps a margin under that measured limit. See docs/RECOMMENDATION_ENGINE_IMPROVEMENTS.md.
RELEASE_GROUP_CHUNK = 50


def _chunks(values: list[str], size: int):
    for start in range(0, len(values), size):
        yield values[start:start + size]


def fetch_batch_recordings(
    post: Callable[..., Any],
    mbids: list[str],
    *,
    headers: Mapping[str, str],
    timeout: float = 30,
) -> dict[str, Mapping[str, Any]]:
    """Return {recording_mbid: metadata entry} for the given MBIDs.

    Raises on a non-200 response or a non-object body, so the caller can fall
    back to per-recording lookups. MBIDs missing from the response are omitted.
    """
    results: dict[str, Mapping[str, Any]] = {}
    for chunk in _chunks(list(dict.fromkeys(mbids)), BATCH_RECORDING_CHUNK):
        response = post(
            LISTENBRAINZ_RECORDING_BATCH_URL,
            json={"recording_mbids": chunk, "inc": BATCH_RECORDING_INCLUDES},
            headers=dict(headers),
            timeout=timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(f"batch recording lookup returned {response.status_code}")
        body = response.json()
        if not isinstance(body, dict):
            raise RuntimeError("batch recording lookup returned a non-object body")
        for mbid in chunk:
            entry = body.get(mbid)
            if isinstance(entry, dict):
                results[mbid] = entry
    return results


def fetch_release_group_metadata(
    get: Callable[..., Any],
    release_group_mbids: list[str],
    *,
    headers: Mapping[str, str],
    timeout: float = 30,
    retries: int = 0,
    sleep: Callable[[float], Any] | None = None,
    failed: set[str] | None = None,
) -> dict[str, Mapping[str, Any]]:
    """Return {release_group_mbid: {"title", "type"}} for the given release groups.

    The live response wraps fields in a ``release_group`` object and names the
    title ``name``. Only primary type is available from this endpoint. Each chunk
    is retried up to ``retries`` times (waiting 2 s per attempt through ``sleep``).
    When ``failed`` is None a chunk that still fails raises, as before. When it is
    a set, the failed chunk's MBIDs are added to it and the other chunks are kept.
    """
    results: dict[str, Mapping[str, Any]] = {}
    for chunk in _chunks(list(dict.fromkeys(release_group_mbids)), RELEASE_GROUP_CHUNK):
        for attempt in range(retries + 1):
            try:
                response = get(
                    LISTENBRAINZ_RELEASE_GROUP_URL,
                    params={"release_group_mbids": ",".join(chunk)},
                    headers=dict(headers),
                    timeout=timeout,
                )
                if response.status_code != 200:
                    raise RuntimeError(f"batch release-group lookup returned {response.status_code}")
                body = response.json()
                if not isinstance(body, dict):
                    raise RuntimeError("batch release-group lookup returned a non-object body")
                break
            except Exception:
                if attempt < retries:
                    if sleep is not None:
                        sleep(2 * (attempt + 1))
                    continue
                if failed is None:
                    raise
                failed.update(chunk)
                body = None
                break
        if body is None:
            continue
        for mbid in chunk:
            entry = body.get(mbid)
            if isinstance(entry, dict):
                group = entry.get("release_group")
                group = group if isinstance(group, dict) else entry
                results[mbid] = {
                    "title": group.get("name") or group.get("title") or "",
                    "type": group.get("type"),
                }
    return results


def synthesize_recording(
    entry: Mapping[str, Any],
    release_groups: Mapping[str, Mapping[str, Any]],
    *,
    title_rejection: Callable[[str], str | None],
) -> dict[str, Any] | None:
    """Build a MusicBrainz-shaped recording from a batch entry.

    The shape matches what the per-recording resolver produces, so downstream
    eligibility code runs unchanged. Release groups whose title carries a
    batch title marker are omitted. Returns None when the entry has no usable
    artist credit or release group.
    """
    recording = entry.get("recording") or {}
    artist_block = entry.get("artist") or {}
    credit = []
    for artist in artist_block.get("artists") or []:
        if not isinstance(artist, dict):
            continue
        name = artist.get("artist_credit_name") or artist.get("name") or ""
        credit.append({
            "name": name,
            "joinphrase": artist.get("join_phrase", ""),
            "artist": {"id": artist.get("artist_mbid")},
        })
    if not any(part["name"] for part in credit):
        return None

    releases = []
    release = entry.get("release") or {}
    rg_mbid = release.get("release_group_mbid")
    rg_meta = release_groups.get(rg_mbid) if rg_mbid else None
    if rg_meta is not None:
        title = str(rg_meta.get("title") or "").strip()
        if title and title_rejection(title) is None:
            releases.append({"release-group": {
                "id": rg_mbid,
                "title": title,
                "primary-type": rg_meta.get("type"),
                # The batch endpoints carry no secondary types. Empty here is
                # not evidence that none exist; the title filter is the safeguard.
                "secondary-types": [],
            }})
    return {
        "title": recording.get("name", ""),
        "artist-credit": credit,
        "releases": releases,
    }
