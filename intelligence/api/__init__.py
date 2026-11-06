"""Pure response builders for Server V2: capabilities, changes feed, ETags (Phase 1 item 6)."""
from .bodies import DEFAULT_PAGE, MAX_PAGE, build_health_body, build_unresolved_body
from .capabilities import CONTRACT_VERSION, FEATURES, ServerFacts, build_capabilities
from .changes import ChangesError, build_changes, parse_since
from .insights import DEFAULT_LIMIT as INSIGHTS_DEFAULT_LIMIT, LISTERS as INSIGHT_LISTERS, MAX_LIMIT as INSIGHTS_MAX_LIMIT, build_insights_body
from .taste import build_taste_body
from .feedback import (
    BatchTooLarge, DEFAULT_LIMIT as FEEDBACK_DEFAULT_LIMIT, MAX_LIMIT as FEEDBACK_MAX_LIMIT,
    build_intake_body, build_suppression_body,
)
from .etag import etag_for, not_modified

__all__ = [
    "CONTRACT_VERSION",
    "DEFAULT_PAGE",
    "MAX_PAGE",
    "INSIGHTS_DEFAULT_LIMIT",
    "INSIGHTS_MAX_LIMIT",
    "INSIGHT_LISTERS",
    "build_health_body",
    "build_insights_body",
    "build_taste_body",
    "BatchTooLarge",
    "FEEDBACK_DEFAULT_LIMIT",
    "FEEDBACK_MAX_LIMIT",
    "build_intake_body",
    "build_suppression_body",
    "build_unresolved_body",
    "ChangesError",
    "FEATURES",
    "ServerFacts",
    "build_capabilities",
    "build_changes",
    "etag_for",
    "not_modified",
    "parse_since",
]
