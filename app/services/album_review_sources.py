"""Album review outlets, their stored answers and failure marks, shared by the route and the worker prefetch.

``app/api/metadata.py`` (``/api/album-reviews``) asks the outlets in parallel under its 6 s deadline and serves
stale answers (efficiency K2); the worker's owned prefetch (efficiency K3) asks them one after another through
its daily ``reviews`` cap. Both use the functions here, with the HTTP ``get`` and the metadata store's ``read``
and ``write`` injected, so they read and write the same rows under the same keys:

- ``album-review-source:v1:{outlet}:{artist}:{album}``: one outlet's answer, ``{"review", "checked"}``; a review
  is kept a month, "nothing there" three days;
- ``album-review-source-failed:v1:...``: an hour's failure mark (efficiency K4), never read as "no review";
- ``album-reviews:v1:{artist}:{album}``: the list, ``{"reviews": [...]}``, stored by the route only, when it has a
  review and is not partial. The worker never writes it: its outlet set can lack the Guardian (no key in its
  environment), and a stored list would hide the Guardian on the route; the route builds the list from the
  stored outlet answers without a request.

Nothing here imports a route module.
"""
import re
import time

import httpx

from app.services import album_reviews, negative_marks
from app.services.album_page_sources import APPLE_PAGE_HEADERS

REVIEW_PAGE_TIMEOUT = httpx.Timeout(4.0, connect=1.5)
WORDPRESS_REVIEW_SITES = (
    ("PopMatters", "https://www.popmatters.com"),
    ("Consequence", "https://consequence.net"),
    ("The Quietus", "https://thequietus.com"),
    ("Treble", "https://www.treblezine.com"),
    ("Angry Metal Guy", "https://www.angrymetalguy.com"),
)
SOURCE_FOUND_TTL = 30 * 24 * 60 * 60
SOURCE_MISS_TTL = 3 * 24 * 60 * 60
# Efficiency K4 (owner approval 2026-11-17): an outlet that timed out or failed for an album is not asked
# about that album again for an hour. The mark has its own key, so it never reads as "no review".
SOURCE_FAILURE_TTL = 60 * 60
GUARDIAN_TAG_TTL = 30 * 24 * 60 * 60


class OutletResting(Exception):
    """The outlet failed for this album within ``SOURCE_FAILURE_TTL``; it is skipped, so the list stays partial."""


def list_store_key(artist, album) -> str:
    return "album-reviews:v1:" + artist.casefold() + ":" + album.casefold()


def outlet_store_key(name, artist, album) -> str:
    return f"album-review-source:v1:{name}:{artist.casefold()}:{album.casefold()}"


def outlet_failure_key(store_key) -> str:
    return "album-review-source-failed:v1:" + store_key.removeprefix("album-review-source:v1:")


# --- Outlets ----------------------------------------------------------------------------------------

def pitchfork_review(get, artist, album):
    response = get(
        "https://pitchfork.com/search/", params={"q": album_reviews.search_text(artist, album)},
        headers=APPLE_PAGE_HEADERS, follow_redirects=True, timeout=REVIEW_PAGE_TIMEOUT)
    response.raise_for_status()
    return album_reviews.pick_pitchfork(album_reviews.parse_pitchfork_search(response.text), artist, album)


def guardian_get(get, api_key, path, **params):
    response = get("https://content.guardianapis.com/" + path, params={**params, "api-key": api_key},
                   timeout=REVIEW_PAGE_TIMEOUT)
    response.raise_for_status()
    return response.json()


def guardian_text(text: str) -> str:
    """Query text the Guardian accepts: it answers 400 to colons, brackets and similar inside a phrase."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w'’ -]+", " ", text)).strip()


def guardian_artist_tag(get, read, write, api_key, artist):
    """The Guardian's tag for an artist, remembered for a month once found.

    A collaboration ("Tony Allen & Hugh Masekela") has no tag of its own, so the first name is tried next.
    """
    store_key = "guardian-artist-tag:v1:" + artist.casefold()
    stored = read(store_key, GUARDIAN_TAG_TTL)
    if stored:
        return stored
    names = [artist] + [part for part in re.split(r"\s+(?:&|and|with|feat\.?|featuring|/)\s+|,\s*", artist)[:1]
                        if part != artist]
    for name in names:
        query = guardian_text(album_reviews.search_text(name, ""))
        tag = album_reviews.pick_guardian_tag(
            guardian_get(get, api_key, "tags", q=query, type="keyword", **{"page-size": 5}), name) if query else None
        if tag:
            write(store_key, tag)
            return tag
    return None


def guardian_review(get, read, write, api_key, artist, album):
    """The Guardian's album review: through the artist's tag when it has one, else by text search."""
    if not api_key:
        return None
    album_text = guardian_text(album_reviews.search_text("", album))
    if not album_text:
        return None
    tag = guardian_artist_tag(get, read, write, api_key, artist)
    if tag:
        query = {"tag": f"{tag},tone/albumreview", "q": f'"{album_text}"'}
    else:
        query = {"tag": "tone/albumreview",
                 "q": f'"{guardian_text(album_reviews.search_text(artist, ""))}" "{album_text}"'}
    payload = guardian_get(get, api_key, "search", **query,
                           **{"order-by": "relevance", "show-fields": "trailText", "page-size": 10})
    return album_reviews.pick_guardian(payload, artist, album)


def wordpress_review(get, name, site, artist, album):
    search = get(
        site + "/wp-json/wp/v2/search", params={
            "search": album_reviews.search_text(artist, album), "subtype": "post", "per_page": 8},
        headers={**APPLE_PAGE_HEADERS, "Accept": "application/json"}, follow_redirects=True,
        timeout=REVIEW_PAGE_TIMEOUT)
    search.raise_for_status()
    url = album_reviews.pick_wordpress_post(search.json(), artist, album)
    if not url:
        return None
    page = get(url, headers=APPLE_PAGE_HEADERS, follow_redirects=True, timeout=REVIEW_PAGE_TIMEOUT)
    page.raise_for_status()
    return album_reviews.review(name, album_reviews.page_dek(page.text), url)


def outlet_asks(get, read, write, artist, album, guardian_key=""):
    """``[(outlet, ask)]`` in display order. The Guardian is left out without a key, so a missing key is never
    stored as "no review"."""
    asks = [("Pitchfork", lambda: pitchfork_review(get, artist, album))]
    if guardian_key:
        asks.append(("The Guardian", lambda: guardian_review(get, read, write, guardian_key, artist, album)))
    asks += [(name, lambda n=name, site=site: wordpress_review(get, n, site, artist, album))
             for name, site in WORDPRESS_REVIEW_SITES]
    return asks


# --- Stored answers ---------------------------------------------------------------------------------

def ask_outlet(read, write, store_key, ask, refused=()):
    """``ask()`` and store its answer. A failure is stored only as a short failure mark, then re-raised.

    An exception of a type in `refused` (the prefetch's cap refusal: nothing was sent) is re-raised unmarked.
    """
    failure_key = outlet_failure_key(store_key)
    if negative_marks.is_live(read, failure_key, SOURCE_FAILURE_TTL):
        raise OutletResting(store_key)
    try:
        found = ask()
    except refused:
        raise
    except Exception:
        negative_marks.mark(write, failure_key)
        raise
    write(store_key, {"review": found, "checked": time.time()})
    return found


def answer_is_fresh(stored, age) -> bool:
    """A stored outlet answer within its TTL: a review for a month, "nothing there" for three days."""
    if stored["review"]:
        return age <= SOURCE_FOUND_TTL
    return time.time() - float(stored.get("checked") or 0) < SOURCE_MISS_TTL


def fresh_stored_answer(read, store_key):
    """``(True, review_or_None)`` for a fresh stored answer, else ``(False, None)``."""
    stored = read(store_key, SOURCE_FOUND_TTL)
    if isinstance(stored, dict) and "review" in stored and (
            stored["review"] or time.time() - float(stored.get("checked") or 0) < SOURCE_MISS_TTL):
        return True, stored["review"]
    return False, None


def stored_list_value(found, failed):
    """``(value, partial)``: the list the route answers from the outlets' answers (None for a failed one)."""
    value = {"reviews": album_reviews.pick_reviews(found)}
    partial = failed and len(value["reviews"]) < album_reviews.MAX_REVIEWS
    if partial:
        value["retryable"] = True
    return value, partial


# --- Worker prefetch (efficiency K3) ----------------------------------------------------------------

def prefetch_reviews(read, write, get, artist, album, guardian_key="", refused=()):
    """Ask, one after another, each outlet with no fresh stored answer, and store its answer as the route does.

    Outlet answers and failure marks are written by ``ask_outlet``; the list is not written (see the module
    docstring). A resting outlet counts as failed, as on the route. A `refused` exception (cap reached, or a
    host with no cap) ends the album: nothing is marked for it, and the remaining outlets are left for the
    first view. Returns ``True`` when every outlet has an answer (the list would not be partial).
    """
    found, failed = [], False
    for name, ask in outlet_asks(get, read, write, artist, album, guardian_key):
        store_key = outlet_store_key(name, artist, album)
        fresh, review = fresh_stored_answer(read, store_key)
        if fresh:
            found.append(review)
            continue
        try:
            found.append(ask_outlet(read, write, store_key, ask, refused))
        except refused:
            return False
        except Exception:
            found.append(None)
            failed = True
    return not stored_list_value(found, failed)[1]
