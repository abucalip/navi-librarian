"""Pure response builders for Server V2: capabilities, changes feed, ETags (Phase 1 item 6)."""
from .capabilities import CONTRACT_VERSION, FEATURES, ServerFacts, build_capabilities
from .changes import ChangesError, build_changes, parse_since
from .etag import etag_for, not_modified

__all__ = [
    "CONTRACT_VERSION",
    "ChangesError",
    "FEATURES",
    "ServerFacts",
    "build_capabilities",
    "build_changes",
    "etag_for",
    "not_modified",
    "parse_since",
]
