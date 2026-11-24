"""Publish ListenBrainz Inbox editions and advance their private rolling copies."""

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from time import time

import httpx

from app.worker_schedule import NOT_READY
from discovery.playlist_sync import sync_edition
from discovery.search.index import SongInventoryError, build_owned_data, fetch_song_inventory
from discovery.search.normalize import normalize_mbid
from integrations.listenbrainz.inbox import PlaylistInboxClient
from integrations.navidrome.client import items
from integrations.navidrome.playlists import PlaylistClient, PlaylistProviderError
from intelligence.store import open_readonly, open_writer
from intelligence.store.playlist_editions import (
    PlaylistEdition, PlaylistSnapshot, get_copy_intent, get_edition, get_managed_copy,
    list_current_editions, publish_edition,
)
from settings.service import listenbrainz_username


logger = logging.getLogger(__name__)
CF_TITLE = "Discair · ListenBrainz Picks"
CF_COUNT = 25
_EARLIEST = datetime.min.replace(tzinfo=timezone.utc)
_PROVIDER_ERRORS = (httpx.HTTPError, ValueError, OverflowError)


@dataclass(frozen=True)
class Copy:
    edition_id: int
    name: str


def _publish(path, snapshot, current):
    with closing(open_writer(path)) as db:
        return publish_edition(db, snapshot, expected_current_id=current.id if current else None, fetched_at=time())


def _date(value):
    return datetime.fromisoformat(value) if value else _EARLIEST


def _hosted_copy(username, metadata, mbid):
    title = metadata.get("title") or "ListenBrainz Playlist"
    suffix = f" for {username}"
    if title.casefold().endswith(suffix.casefold()):
        title = title[:-len(suffix)].strip() or title
    source = metadata.get("source_patch") or mbid
    return f"listenbrainz:{username.casefold()}:hosted:{source}", f"Discair · {title}"


def _refresh_hosted(path, provider, username, editions):
    copies = {}
    failed = False
    try:
        listing = provider.created_for_me()
    except _PROVIDER_ERRORS as error:
        logger.warning("Playlist Inbox listing failed (%s)", type(error).__name__)
        return copies, True

    # Publish older sources first so a rolling feed advances by local edition ID.
    for row in sorted(reversed(listing), key=lambda entry: entry.generated_at or entry.last_modified_at or _EARLIEST):
        mbid = row.playlist_mbid
        current = editions.get(("hosted", mbid))
        metadata = current.snapshot.metadata if current else {}
        version = row.last_modified_at or row.generated_at or _EARLIEST
        saved_version = _date(metadata.get("last_modified_at") or metadata.get("generated_at"))
        try:
            if current is None or version > saved_version:
                snapshot = PlaylistSnapshot.from_hosted(provider.playlist_details(mbid))
                detail = snapshot.metadata
                detail_version = _date(detail.get("last_modified_at") or detail.get("generated_at"))
                if detail_version < version:
                    raise ValueError("Playlist detail is older than its listing")
                edition_id = _publish(path, snapshot, current)
                metadata = detail
            else:
                edition_id = current.id
        except _PROVIDER_ERRORS as error:
            logger.warning("Playlist Inbox detail failed (%s)", type(error).__name__)
            metadata = {"source_patch": row.source_patch or metadata.get("source_patch")}
            edition_id = None
        feed, name = _hosted_copy(username, metadata, mbid)
        if edition_id is None:
            failed = True
            copies.pop(feed, None)
        else:
            copies[feed] = Copy(edition_id, name)
    return copies, failed


def _name(value):
    return value.strip() or None if isinstance(value, str) else None


def _cf_track(position, recommendation, metadata):
    recording = metadata.get("recording") or {}
    artist = metadata.get("artist") or {}
    release = metadata.get("release") or {}
    if not all(isinstance(part, dict) for part in (recording, artist, release)):
        raise ValueError("Invalid ListenBrainz recording metadata fields")
    length, cover = recording.get("length"), release.get("caa_id")
    return {
        "position": position, "recording_mbid": recommendation.recording_mbid, "score": recommendation.score,
        "title": _name(recording.get("name")), "artist": _name(artist.get("name")),
        "album": _name(release.get("name")), "release_mbid": normalize_mbid(release.get("mbid")),
        "duration_ms": length if type(length) is int and length > 0 else None,
        "caa_id": cover if type(cover) is int and cover > 0 else None,
        "caa_release_mbid": normalize_mbid(release.get("caa_release_mbid")),
    }


def _refresh_cf(path, provider, username, editions):
    source = username.casefold()
    current = editions.get(("cf", source))
    page = provider.recording_recommendations(count=CF_COUNT)
    if len(page.recordings) != min(page.total_count, CF_COUNT):
        raise ValueError("Incomplete ListenBrainz CF recommendation page")
    if not page.recordings:
        return None
    version = str(page.last_updated)
    dated = datetime.fromtimestamp(page.last_updated, timezone.utc)
    if current and dated < _date(current.snapshot.metadata.get("generated_at")):
        return Copy(current.id, CF_TITLE)
    signature = tuple((row.recording_mbid, row.score) for row in page.recordings)
    if (current and current.snapshot.edition_key == version
            and signature == tuple((row["recording_mbid"], row.get("score")) for row in current.snapshot.tracks)):
        edition_id = current.id
    else:
        metadata = provider.recording_metadata(tuple(mbid for mbid, _ in signature))
        snapshot = PlaylistSnapshot(
            "cf", source, version,
            {"title": CF_TITLE, "creator": "ListenBrainz", "generated_at": dated.isoformat()},
            tuple(_cf_track(i, row, metadata.get(row.recording_mbid, {})) for i, row in enumerate(page.recordings)),
        )
        edition_id = _publish(path, snapshot, current)
    return Copy(edition_id, CF_TITLE) if edition_id is not None else NOT_READY


def _pending_copies(path, copies):
    with closing(open_readonly(path)) as db:
        for feed, copy in copies.items():
            link = get_managed_copy(db, feed)
            intent = get_copy_intent(db, feed)
            if link and (link.unlinked or (intent and intent.edition_id >= copy.edition_id)):
                continue
            if intent:
                previous = get_edition(db, intent.edition_id)
                incoming = get_edition(db, copy.edition_id)
                if (_date(previous.snapshot.metadata.get("generated_at"))
                        > _date(incoming.snapshot.metadata.get("generated_at"))):
                    continue
            yield feed, copy


def _sync_copies(librarian, path, copies):
    pending = tuple(_pending_copies(path, copies))
    if not pending:
        return None
    try:
        navidrome = PlaylistClient(librarian._navidrome_config())
    except ValueError:
        return None
    try:
        marker = navidrome.scan_marker()
        if marker is None:
            return NOT_READY
        owned = build_owned_data(
            generation=navidrome.target_key, built_at=time(), artists=(), albums=(),
            songs=fetch_song_inventory(navidrome.search_songs, items),
        )
    except (PlaylistProviderError, SongInventoryError) as error:
        logger.warning("Playlist Inbox inventory failed (%s)", type(error).__name__)
        return NOT_READY

    retry = False
    for feed, copy in pending:
        try:
            result = sync_edition(path, navidrome, feed_key=feed, edition_id=copy.edition_id,
                                  name=copy.name, owned=owned, scan_marker=marker)
        except PlaylistProviderError as error:
            logger.warning("Playlist Inbox copy failed (%s)", type(error).__name__)
            retry = True
        else:
            # The independent reconciliation job records confirmed deletions.
            retry |= result.state not in ("synced", "unlinked", "missing")
    return NOT_READY if retry else None


def refresh_once(librarian, path):
    settings = librarian._discovery_settings_read()
    try:
        username = listenbrainz_username(lambda: settings)
    except ValueError:
        return None
    token = str(settings.get("listenbrainz_token") or "").strip() or None
    with httpx.Client() as client:
        provider = PlaylistInboxClient(client, username, token=token)
        if not provider.configured:
            return None
        with closing(open_readonly(path)) as db:
            editions: dict[tuple[str, str], PlaylistEdition] = {
                (row.snapshot.source_kind, row.snapshot.source_key): row for row in list_current_editions(db)
            }
        copies, retry = _refresh_hosted(path, provider, username, editions)
        try:
            cf = _refresh_cf(path, provider, username, editions)
        except _PROVIDER_ERRORS as error:
            logger.warning("Playlist Inbox CF refresh failed (%s)", type(error).__name__)
            retry = True
        else:
            if cf is NOT_READY:
                retry = True
            elif cf is not None:
                copies[f"listenbrainz:{username.casefold()}:cf"] = cf
    sync = _sync_copies(librarian, path, copies)
    return NOT_READY if retry or sync is NOT_READY else None
