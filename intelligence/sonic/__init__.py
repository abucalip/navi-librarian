"""Sonic similarity proxy (docs/ServerV2.md Phase 7): Navidrome's sonic endpoints with Librarian rules on top."""
from .neighbours import album_neighbours
from .proxy import MAX_COUNT, SonicResult, sonic_path, similar_tracks

__all__ = ["album_neighbours", "MAX_COUNT", "SonicResult", "sonic_path", "similar_tracks"]
