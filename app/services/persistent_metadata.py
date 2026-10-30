"""Optional persistent store behind the in-memory metadata route caches.

The metadata routes keep answers in process memory, which a restart empties. The app attaches the
persistent metadata cache here at assembly time; until then (and in tests) every read is a miss and
every write is dropped, so a missing store can never break a route.
"""

_get = None
_set = None

# Answers about a released album or an artist change rarely, so found values live for a month.
FOUND_TTL = 30 * 24 * 60 * 60
LINKS_TTL = 7 * 24 * 60 * 60


def attach(get, set_):
    """Use `get(key, ttl_seconds)` and `set_(key, value)` as the persistent store."""
    global _get, _set
    _get, _set = get, set_


def detach():
    attach(None, None)


def read(key, ttl_seconds=FOUND_TTL):
    """The stored value, or None on a miss or any store failure."""
    if _get is None:
        return None
    try:
        return _get(key, ttl_seconds)
    except Exception:
        return None


def write(key, value):
    if _set is None:
        return
    try:
        _set(key, value)
    except Exception:
        pass
