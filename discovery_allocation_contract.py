"""Immutable interface contract for personal-recommendation shortlist allocation.

This module deliberately contains no selection loops or provider/library access.
The contract is a seam-design probe: prepared candidates carry ownership
classification, and an allocator result refers to candidates by stable IDs.
The server adapter remains responsible for converting selected candidates into
the legacy response payload.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from types import MappingProxyType
from typing import Mapping


CATEGORIES = frozenset({"adjacent", "cross_genre", "adventurous", "unclassified"})
QUOTA_CATEGORIES = frozenset({"adjacent", "cross_genre", "adventurous"})
MAX_RECOMMENDATION_COUNT = 20
MAX_CANDIDATE_CHECKS = 60


class OwnershipStatus(str, Enum):
    """Ownership result computed before allocation; no callback is required."""

    CLEAR = "clear"
    EXACT_OWNED = "exact_owned"
    TITLE_CONFLICT = "title_conflict"


@dataclass(frozen=True)
class AllocationCandidate:
    """Minimum policy inputs for one already-enriched candidate.

    `candidate_id` is unique within a request and is used to join results back
    to the original candidate without copying or mutating its response payload.
    `artist_key` and `album_key` must already be normalized by the caller.
    """

    candidate_id: str
    artist_key: str
    album_key: str
    category: str
    score: float
    source_order: int = 0
    diversity_style: str = "other"
    recent_profile_family: str | None = None
    ownership: OwnershipStatus = OwnershipStatus.CLEAR
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("candidate_id", "artist_key"):
            if not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if self.category not in CATEGORIES:
            raise ValueError(f"unsupported recommendation category: {self.category}")
        if not math.isfinite(self.score):
            raise ValueError("score must be finite")
        if not isinstance(self.source_order, int) or self.source_order < 0:
            raise ValueError("source_order must be a non-negative integer")
        if not isinstance(self.ownership, OwnershipStatus):
            raise ValueError("ownership must be an OwnershipStatus")
        if not isinstance(self.tags, tuple) or any(not isinstance(tag, str) for tag in self.tags):
            raise ValueError("tags must be a tuple of strings")


@dataclass(frozen=True)
class AllocationRequest:
    """All policy inputs, with no callbacks and no caller-owned mutable state."""

    candidates: tuple[AllocationCandidate, ...]
    count: int
    category_targets: Mapping[str, int]
    diversity_style_targets: Mapping[str, int]
    family_cap: int = 1
    max_checks: int = MAX_CANDIDATE_CHECKS
    diversity_penalty: float = 0.0

    def __post_init__(self) -> None:
        if not 1 <= self.count <= MAX_RECOMMENDATION_COUNT:
            raise ValueError("count must be between 1 and 20")
        if not isinstance(self.candidates, tuple):
            raise TypeError("candidates must be a tuple")
        candidate_ids = [candidate.candidate_id for candidate in self.candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("candidate_id values must be unique")
        if not set(self.category_targets).issubset(QUOTA_CATEGORIES):
            raise ValueError("category_targets contains an unsupported category")
        if any(not isinstance(value, int) or value < 0 for value in self.category_targets.values()):
            raise ValueError("category targets must be non-negative integers")
        if any(not isinstance(value, int) or value < 0 for value in self.diversity_style_targets.values()):
            raise ValueError("diversity style targets must be non-negative integers")
        if not isinstance(self.family_cap, int) or self.family_cap < 0:
            raise ValueError("family_cap must be a non-negative integer")
        if not isinstance(self.max_checks, int) or not 1 <= self.max_checks <= MAX_CANDIDATE_CHECKS:
            raise ValueError("max_checks must be between 1 and 60")
        if (isinstance(self.diversity_penalty, bool)
                or not isinstance(self.diversity_penalty, (int, float))
                or not math.isfinite(self.diversity_penalty)
                or not 0.0 <= self.diversity_penalty <= 1.0):
            raise ValueError("diversity_penalty must be finite and between 0 and 1")
        object.__setattr__(
            self, "category_targets", MappingProxyType(dict(self.category_targets))
        )
        object.__setattr__(
            self, "diversity_style_targets",
            MappingProxyType(dict(self.diversity_style_targets)),
        )


@dataclass(frozen=True)
class CandidateDecision:
    """Diagnostic outcome for a candidate considered by the allocation policy."""

    candidate_id: str
    status: str
    reason: str

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id must be non-empty")
        if not self.status.strip():
            raise ValueError("status must be non-empty")


@dataclass(frozen=True)
class AllocationResult:
    """Deterministic allocation output; IDs let the adapter recover payloads."""

    requested_count: int
    selected_candidate_ids: tuple[str, ...]
    ownership_review_candidate_ids: tuple[str, ...]
    decisions: tuple[CandidateDecision, ...]
    category_counts: Mapping[str, int]
    checked_count: int
    phase_diagnostics: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 1 <= self.requested_count <= MAX_RECOMMENDATION_COUNT:
            raise ValueError("requested_count must be between 1 and 20")
        if len(self.selected_candidate_ids) > self.requested_count:
            raise ValueError("selected candidates exceed requested_count")
        if len(set(self.selected_candidate_ids)) != len(self.selected_candidate_ids):
            raise ValueError("selected candidate IDs must be unique")
        if len(set(self.ownership_review_candidate_ids)) != len(self.ownership_review_candidate_ids):
            raise ValueError("ownership-review candidate IDs must be unique")
        if set(self.selected_candidate_ids) & set(self.ownership_review_candidate_ids):
            raise ValueError("selected and ownership-review candidates must be disjoint")
        if not isinstance(self.checked_count, int) or not 0 <= self.checked_count <= MAX_CANDIDATE_CHECKS:
            raise ValueError("checked_count must be between 0 and 60")
        if any(category not in CATEGORIES for category in self.category_counts):
            raise ValueError("category_counts contains an unsupported category")
        if any(not isinstance(value, int) or value < 0 for value in self.category_counts.values()):
            raise ValueError("category counts must be non-negative integers")
        object.__setattr__(
            self, "category_counts", MappingProxyType(dict(self.category_counts))
        )
        if any(not isinstance(key, str) or not isinstance(value, int) or value < 0
               for key, value in self.phase_diagnostics.items()):
            raise ValueError("phase diagnostics must map names to non-negative integers")
        object.__setattr__(
            self, "phase_diagnostics", MappingProxyType(dict(self.phase_diagnostics))
        )
