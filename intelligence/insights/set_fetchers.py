"""Provider fetchers for the blind-spot set job (Phase 3 item 2, network side).

Builds the three ``Fetch`` callables that :class:`.set_job.SetFetchers` expects. Nothing here
opens a connection itself: the caller injects ``get`` (a ``requests.get``-shaped callable), the
request headers (User-Agent), a ``sleep`` and the request budget, so the module is unwired and
adds no provider traffic until a caller builds and runs it.

Rules:

* a 404 (or an empty body) means the provider has nothing: the fetcher returns ``None``;
* any other non-200 status, a transport error or a non-JSON body raises, so the set job stops
  early and leaves the saved cards untouched (last known good);
* every request is followed by a pause (MusicBrainz 1.1 s, ListenBrainz 0.5 s) and each request
  is counted with ``record_provider_call``;
* the studio discography pages through the browse endpoint up to ``max_pages`` pages of 100; a
  longer list is truncated and the truncation is not hidden: ``release-group-count`` in the
  returned document is the provider's total, so a caller can compare.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping

from .set_job import SetFetchers

MUSICBRAINZ_RELEASE_GROUP_URL = "https://musicbrainz.org/ws/2/release-group"
MUSICBRAINZ_SERIES_URL = "https://musicbrainz.org/ws/2/series/"
LISTENBRAINZ_TOP_RELEASE_GROUPS_URL = "https://api.listenbrainz.org/1/popularity/top-release-groups-for-artist/"
MUSICBRAINZ_SPACING_SECONDS = 1.1
LISTENBRAINZ_SPACING_SECONDS = 0.5
BROWSE_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 5


def _request(
    get: Callable[..., Any], url: str, params: Mapping[str, Any], headers: Mapping[str, str],
    timeout: float, sleep: Callable[[float], Any] | None, spacing: float, provider: str, call: str,
) -> Any:
    from recommendation_run_metrics import record_provider_call

    record_provider_call(provider, call)
    try:
        response = get(url, params=dict(params), headers=dict(headers), timeout=timeout)
    finally:
        if sleep is not None:
            sleep(spacing)
    if response.status_code == 404:
        return None
    if response.status_code != 200:
        raise RuntimeError(f"{provider} {call} returned HTTP {response.status_code}")
    return response.json()


def build_set_fetchers(
    get: Callable[..., Any],
    *,
    headers: Mapping[str, str],
    sleep: Callable[[float], Any] | None = None,
    timeout: float = 30,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> SetFetchers:
    if max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    def studio(artist_mbid: str) -> Mapping[str, Any] | None:
        groups: list[Any] = []
        total = None
        for page in range(max_pages):
            body = _request(
                get, MUSICBRAINZ_RELEASE_GROUP_URL,
                {"artist": artist_mbid, "type": "album", "limit": BROWSE_PAGE_SIZE,
                 "offset": page * BROWSE_PAGE_SIZE, "fmt": "json"},
                headers, timeout, sleep, MUSICBRAINZ_SPACING_SECONDS, "musicbrainz", "release_group_browse",
            )
            if not isinstance(body, Mapping):
                if page == 0:
                    return None
                raise RuntimeError("musicbrainz release_group_browse returned an unexpected page")
            batch = body.get("release-groups")
            if not isinstance(batch, list):
                if page == 0:
                    return None
                raise RuntimeError("musicbrainz release_group_browse returned an unexpected page")
            groups.extend(batch)
            total = body.get("release-group-count", total)
            if len(batch) < BROWSE_PAGE_SIZE or (isinstance(total, int) and len(groups) >= total):
                break
        return {"release-groups": groups, "release-group-count": total if isinstance(total, int) else len(groups)}

    def listenbrainz(artist_mbid: str) -> Mapping[str, Any] | None:
        body = _request(
            get, f"{LISTENBRAINZ_TOP_RELEASE_GROUPS_URL}{artist_mbid}", {}, headers, timeout, sleep,
            LISTENBRAINZ_SPACING_SECONDS, "listenbrainz", "top_release_groups",
        )
        # The endpoint answers with a bare list; the builder reads ``payload.release_groups``.
        if isinstance(body, list):
            return {"payload": {"release_groups": body}} if body else None
        return body if isinstance(body, Mapping) else None

    def series(series_mbid: str) -> Mapping[str, Any] | None:
        body = _request(
            get, f"{MUSICBRAINZ_SERIES_URL}{series_mbid}", {"inc": "release-group-rels", "fmt": "json"},
            headers, timeout, sleep, MUSICBRAINZ_SPACING_SECONDS, "musicbrainz", "series_lookup",
        )
        return body if isinstance(body, Mapping) else None

    return SetFetchers(studio=studio, listenbrainz=listenbrainz, series=series)
