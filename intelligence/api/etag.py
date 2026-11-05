"""ETag helpers built from ``data_version`` counters (docs/ServerV2.md 6.4, 8)."""
from __future__ import annotations


def etag_for(resource: str, version: int, generation: int) -> str:
    """A weak validator: the same resource, version and generation give the same tag.

    The generation is included because a matching-logic change can alter a response
    without any resource counter moving.
    """
    return f'W/"{resource}-{int(generation)}-{int(version)}"'


def not_modified(if_none_match: str | None, etag: str) -> bool:
    """True when an ``If-None-Match`` header means the client already has ``etag``.

    Uses weak comparison (RFC 9110 section 13.1.2), accepts a comma-separated list and
    the ``*`` wildcard, and treats a missing or blank header as "send the body".
    """
    if not if_none_match or not if_none_match.strip():
        return False
    if if_none_match.strip() == "*":
        return True
    wanted = _opaque(etag)
    return any(_opaque(candidate) == wanted for candidate in if_none_match.split(","))


def _opaque(tag: str) -> str:
    tag = tag.strip()
    return tag[2:] if tag.startswith("W/") else tag
