"""Album artwork index (docs/artwork.md, slice 1: server index and merge)."""
from .fetchers import ArtworkFetchers, HostPacer
from .index import (
    BOOKLET_PAGES_CAP, BUILD_SECONDS, IMAGES_STORED_CAP, IMAGES_SERVED_CAP, RELEASES_CAP, SLOT_TYPES,
    GroupIndex, ImageEntry, ReleaseIndex, ReleaseInfo, best_front, build_group_index, parse_release,
    slots_view, to_response,
)

__all__ = [
    "ArtworkFetchers", "HostPacer",
    "BOOKLET_PAGES_CAP", "BUILD_SECONDS", "IMAGES_STORED_CAP", "IMAGES_SERVED_CAP", "RELEASES_CAP", "SLOT_TYPES",
    "GroupIndex", "ImageEntry", "ReleaseIndex", "ReleaseInfo", "best_front", "build_group_index",
    "parse_release", "slots_view", "to_response",
]
