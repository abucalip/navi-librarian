"""Batch sitewide popularity fetch for the obscurity profile (Phase 6 item 2, network side).

Returns ``{mbid: total_listen_count or None}`` for a list of artist MBIDs. Nothing here opens a
connection itself: the caller injects ``post`` (a ``requests.post``-shaped callable), the request
headers, a ``sleep`` and the timeout, so the module is unwired and adds no provider traffic until a
caller runs it.

Rules:

* one batch request per chunk of :data:`POPULARITY_CHUNK_SIZE` MBIDs (``POST /1/popularity/artist``
  with body ``{"artist_mbids": [...]}``), never one request per artist. The batch limit is not
  documented, so 100 is a conservative starting value;
* MBIDs are de-duplicated in first-seen order; an empty list makes no request;
* every request is followed by a pause of :data:`LISTENBRAINZ_SPACING_SECONDS` and is counted with
  ``record_provider_call``;
* a 404, or a 200 with an empty body, means the provider has no figures: those MBIDs map to ``None``;
* any other non-200 status, a transport error, a non-JSON body or a body that is not a list raises,
  so the caller keeps the last saved data (last known good);
* every requested MBID appears in the result, with ``None`` when the provider returned nothing.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping

from .obscurity import popularity_from_response

POPULARITY_ARTIST_URL = "https://api.listenbrainz.org/1/popularity/artist"
POPULARITY_CHUNK_SIZE = 100
LISTENBRAINZ_SPACING_SECONDS = 0.5


def fetch_artist_popularity(
    artist_mbids: Iterable[str],
    *,
    post: Callable[..., Any],
    headers: Mapping[str, str],
    sleep: Callable[[float], Any] | None = None,
    timeout: float = 30,
) -> dict[str, int | None]:
    from recommendation_run_metrics import record_provider_call

    unique = list(dict.fromkeys(m for m in artist_mbids if m))
    result: dict[str, int | None] = {}
    for start in range(0, len(unique), POPULARITY_CHUNK_SIZE):
        chunk = unique[start:start + POPULARITY_CHUNK_SIZE]
        record_provider_call("listenbrainz", "popularity_artist")
        try:
            response = post(
                POPULARITY_ARTIST_URL,
                json={"artist_mbids": chunk},
                headers=dict(headers),
                timeout=timeout,
            )
        finally:
            if sleep is not None:
                sleep(LISTENBRAINZ_SPACING_SECONDS)
        figures = _figures(response)
        for mbid in chunk:
            result[mbid] = figures.get(mbid)
    return result


def _figures(response: Any) -> dict[str, int | None]:
    if response.status_code == 404:
        return {}
    if response.status_code != 200:
        raise RuntimeError(f"listenbrainz popularity_artist returned HTTP {response.status_code}")
    if not (response.text or "").strip():
        return {}
    body = response.json()
    if not isinstance(body, list):
        raise RuntimeError("listenbrainz popularity_artist returned an unexpected body")
    return popularity_from_response(body)
