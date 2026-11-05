"""Editions and duplicates (docs/ServerV2.md Phase 2)."""
from .advisor import AdviceReport, EditionAdvice, EditionComparison, EditionMeasures, MetricDelta, advise, edition_track_ids
from .duplicates import (
    DuplicateAlbum, DuplicateRecording, DuplicateReport, find_duplicate_albums, find_duplicate_recordings,
    find_duplicates,
)
from .grouping import (
    Edition, TrackEntry, TracklistDiff, compare_tracklists, edition_labels, group_editions,
    release_relation, tracklist,
)
from .release_groups import LinkOutcome, SweepResult, link_release_group, parse_release, sweep_owned_releases

__all__ = [
    "AdviceReport", "EditionAdvice", "EditionComparison", "EditionMeasures", "MetricDelta", "advise",
    "edition_track_ids",
    "DuplicateAlbum", "DuplicateRecording", "DuplicateReport", "find_duplicate_albums",
    "find_duplicate_recordings", "find_duplicates",
    "Edition", "LinkOutcome", "SweepResult", "TrackEntry", "TracklistDiff", "compare_tracklists",
    "edition_labels", "group_editions", "link_release_group", "parse_release", "release_relation",
    "sweep_owned_releases", "tracklist",
]
