"""Worker prefetch of the artist and album pages' provider rows for the owned library (efficiency K3, part 1).

``run_once`` is the worker scheduler's ``owned_prefetch`` entry. It walks the owned artists and the owned
albums, one of each in turn, and builds each page's network sections exactly as the page routes do
(``artist_page`` and ``album_sections``, with a worker-built network), discarding the sections. The
provider rows those sections store (MusicBrainz, ListenBrainz, Last.fm, Discogs) are therefore the same
rows, under the same keys, that a first view would have fetched on demand; there is no second key builder
to drift. A row that is still fresh costs no request, so a repeated pass over a warm library is cheap.

Off unless the owner sets daily caps (``prefetch_state.ENV_BUDGETS``). Every request goes through
``prefetch_state.Spend``, which refuses a request past its provider's cap or to an unlisted provider. Last.fm
and Discogs without a cap are switched off for the run; MusicBrainz and ListenBrainz are used by both pages,
so a cap set without them makes those sections fail (the entity is counted ``partial``, the walk moves on).
The run ends when a cap is reached, on shutdown, after ``RUN_SECONDS``, or after one pass over both lists.
The walk resumes from a checkpoint saved after each entity, whatever its outcome, except that an entity
cut short by a cap is not passed over: it is tried again on the next day.

Part 2 adds the album page's Deezer tracklist and Apple/Wikipedia description hooks, on their own caps
(``deezer``; ``apple`` and ``wikipedia``), through ``app/services/album_page_sources.py`` (shared with the
routes; this module and its worker never import a route module). Not covered: album links and the artist image
(clients ask for those themselves, under their own keys), the album year (its MusicBrainz lookup is not counted
here), album reviews (until K4) and the artist biography. Sections that only those hooks fill stay empty here.
"""
import logging
import time

from app import worker_schedule
from app.services import album_page_sources, prefetch_state, similar_precompute
from discovery.search.album_page import album_sections
from discovery.search.artist_page import artist_page
from discovery.search.index import STATE_FRESH, IndexView
from discovery.search.network import artist_network
from discovery.search.providers import REQUEST_TIMEOUT
from integrations.listenbrainz.client import request_headers
from integrations.listenbrainz.popularity import fetch_release_group_popularity
from intelligence.store import open_store

logger = logging.getLogger(__name__)

RUN_SECONDS = 3600.0         # one run's time limit, so the hours-long precompute behind it still starts today
ENTITY_SECONDS = 45.0        # the page deadline for one entity (a page waits 8 s; MusicBrainz is paced about 1 per second)
NEW_FIRST = 50               # this many most recently added entries go first
RETRY_SECONDS = similar_precompute.RETRY_SECONDS


def order_artists(artists) -> list:
    """Newest additions first, then the rest by listens, most first. Stable for an unchanged library."""
    by_added = sorted(artists, key=lambda a: (a.get("added") or "", a["id"]), reverse=True)
    head = by_added[:NEW_FIRST]
    taken = {a["id"] for a in head}
    rest = sorted((a for a in artists if a["id"] not in taken),
                  key=lambda a: (-(a.get("plays") or 0), a["key"], a["id"]))
    return head + rest


def order_albums(albums, artists) -> list:
    """Newest additions first, then the rest by the owning artist's listens (an album has no listen count)."""
    plays = {a["id"]: a.get("plays") or 0 for a in artists}
    by_added = sorted(albums, key=lambda a: (a.get("added") or "", a["id"]), reverse=True)
    head = by_added[:NEW_FIRST]
    taken = {a["id"] for a in head}
    rest = sorted((a for a in albums if a["id"] not in taken),
                  key=lambda a: (-plays.get(a["artist_id"], 0), a["key"], a["id"]))
    return head + rest


def prefetch_network(librarian, spend):
    """The page network the worker uses: the shared arguments, requests through ``spend``, no stale serving."""
    def popularity(mbids, can_cache):
        def cache_set(key, value):
            if can_cache():
                librarian._metadata_cache_set(key, value)

        return fetch_release_group_popularity(
            spend.post, librarian._metadata_cache_get, cache_set, mbids,
            headers=request_headers(), timeout=REQUEST_TIMEOUT)

    shared = similar_precompute.network_kwargs(librarian)
    # A source with no cap is switched off, as on an instance without its key: its sections say so and send nothing,
    # instead of being refused on every entity. MusicBrainz and ListenBrainz are used by both pages, so they need caps.
    if "lastfm" not in spend.caps:
        shared["lastfm_api_key"] = ""
    if "discogs" not in spend.caps:
        shared["discogs_token"] = ""
    hooks = album_page_hooks(librarian, spend)
    return artist_network(
        popularity=popularity, bio=lambda name: None, http_get=spend.get, deadline_seconds=ENTITY_SECONDS,
        **hooks, **shared)


def album_page_hooks(librarian, spend) -> dict:
    """The album page's Deezer tracklist and description hooks (K3 part 2), each only when its providers have caps.

    They read and write the metadata store under the route's own keys (``app.services.album_page_sources``), so a
    first view finds the row. The description needs Apple and Wikipedia both: without either, its hook is left out
    and the page's section stays for the first view. The year hook is not given: the page asks for a year only for
    an album with none in the library, and its MusicBrainz lookup does not go through ``spend``.
    """
    read, write = librarian._metadata_cache_get, librarian._metadata_cache_set
    get = album_page_sources.counting_get(spend.get)
    hooks = {}
    if "deezer" in spend.caps:
        hooks["deezer_tracks"] = lambda artist, album: album_page_sources.prefetch_tracks(read, write, get, artist, album)
    if "apple" in spend.caps and "wikipedia" in spend.caps:
        hooks["album_description"] = lambda artist, album: album_page_sources.prefetch_description(
            read, write, get, artist, album)
    return hooks


def _warm_artist(network, view, artist) -> bool:
    """Build the artist page's sections; True when every section finished (nothing cut short by a deadline)."""
    page = artist_page(view, artist["key"], artist["id"], network=network)
    return page.status == "ok" and not page.partial


def _warm_album(network, data, album) -> bool:
    sections = list(album_sections(
        network, data, album=album, artist=album["artist"], artist_key=album["artist_key"], name=album["name"],
        year=album["year"], release_group_mbid=album["release_group_mbid"]))
    return not any(s["reason"] in ("deadline", "source_failed") for s in sections)


def run_once(librarian, store_path, stop=None, *, clock=time.monotonic, wall=time.time, environ=None,
             build_owned=similar_precompute.build_owned):
    """One bounded pass; ``NOT_READY`` when the owned library cannot be read; ``None`` when no cap is set."""
    caps = prefetch_state.budgets_from_env(environ)
    if not caps:
        return None
    date = prefetch_state.local_date(wall())
    db = open_store(store_path)
    try:
        spend = prefetch_state.Spend(caps, prefetch_state.load_spent(db, date))
        if spend.exhausted():
            return {"stopped": "budget", "spent": spend.snapshot()}
        data = build_owned(librarian)
        if data is None:
            return worker_schedule.NOT_READY
        return _walk(librarian, db, data, spend, date, stop, clock)
    finally:
        db.close()


def _walk(librarian, db, data, spend, date, stop, clock):
    artists = order_artists(data.artists)
    albums = order_albums(data.albums, data.artists)
    view = IndexView(STATE_FRESH, data, None)
    network = prefetch_network(librarian, spend)
    walks = {"artists": (artists, lambda n: _warm_artist(network, view, n)),
             "albums": (albums, lambda n: _warm_album(network, data, n))}
    cursor = prefetch_state.load_cursor(db)
    done = {name: 0 for name in walks}         # entities handled in this run, per list
    counts = {"complete": 0, "partial": 0, "failed": 0}
    stop_at = clock() + RUN_SECONDS
    stopped = "pass"
    turn = 0
    while any(done[name] < len(entries) for name, (entries, _) in walks.items()):
        if stop is not None and stop.is_set():
            stopped = "shutdown"
            break
        if spend.exhausted():
            stopped = "budget"
            break
        if clock() >= stop_at:
            stopped = "time"
            break
        name = ("artists", "albums")[turn % 2]
        turn += 1
        entries, warm = walks[name]
        if done[name] >= len(entries):
            continue
        entry = entries[cursor[name] % len(entries)]
        try:
            finished = warm(entry)
        except Exception as exc:
            logger.warning("Prefetch of one %s failed (%s)", name[:-1], type(exc).__name__)
            finished = None
        if stop is not None and stop.is_set():
            stopped = "shutdown"      # cut short by shutdown: the checkpoint is not moved
            break
        if spend.cap_reached:
            stopped = "budget"        # cut short by a cap: tried again on the next day, not passed over
            break
        counts["failed" if finished is None else "complete" if finished else "partial"] += 1
        done[name] += 1
        cursor[name] = (cursor[name] + 1) % len(entries)
        prefetch_state.save_cursor(db, cursor)
        prefetch_state.save_spent(db, date, spend.snapshot())
    prefetch_state.save_spent(db, date, spend.snapshot())
    coverage = {
        "date": date, "stopped": stopped, "caps": spend.caps, "spent": spend.snapshot(), "counts": counts,
        "artists": {"total": len(artists), "next": cursor["artists"], "handled": done["artists"]},
        "albums": {"total": len(albums), "next": cursor["albums"], "handled": done["albums"]},
    }
    prefetch_state.save_coverage(db, coverage)
    logger.info("Owned prefetch finished: %s", {k: coverage[k] for k in ("stopped", "spent", "counts")})
    return coverage
