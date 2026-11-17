"""Optional persistent store behind the in-memory metadata route caches.

The metadata routes keep answers in process memory, which a restart empties. The app attaches the
persistent metadata cache here at assembly time; until then (and in tests) every read is a miss and
every write is dropped, so a missing store can never break a route.

`read_with_age` (efficiency K2) serves stale-while-revalidate. It works only when the store was
attached with `get_with_age`; otherwise it is always a miss and callers keep today's expiry.
"""

_get = None
_set = None
_get_with_age = None

DAY = 24 * 60 * 60
# Answers about a released album or an artist change rarely, so found values live for a month.
FOUND_TTL = 30 * DAY
LINKS_TTL = 7 * DAY


def attach(get, set_, get_with_age=None):
    """Use `get(key, ttl_seconds)` and `set_(key, value)` as the persistent store.

    `get_with_age(key, max_age_seconds)` returns `(value, age_seconds)` or None; without it, stale
    values are never served.
    """
    global _get, _set, _get_with_age
    _get, _set, _get_with_age = get, set_, get_with_age


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


def can_read_age():
    return _get_with_age is not None


def read_with_age(key, max_age_seconds):
    """`(value, age_seconds)` for a stored value no older than `max_age_seconds`, else None."""
    if _get_with_age is None:
        return None
    try:
        found = _get_with_age(key, max_age_seconds)
    except Exception:
        return None
    if found is None:
        return None
    value, age = found
    return value, float(age)


def write(key, value):
    if _set is None:
        return
    try:
        _set(key, value)
    except Exception:
        pass
