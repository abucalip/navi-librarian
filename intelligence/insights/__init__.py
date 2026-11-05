"""Collection intelligence as insight cards (docs/ServerV2.md Phase 3)."""
from .forgotten_gems import (
    CARD_KIND, Gem, GemsConfig, GemsResult, PlayRecord, find_forgotten_gems, gem_card,
)
from .persistence import dismiss_gem, dismissed_keys, list_gem_cards, restore_gem, save_gems

__all__ = ["CARD_KIND", "Gem", "GemsConfig", "GemsResult", "PlayRecord", "find_forgotten_gems", "gem_card",
           "dismiss_gem", "dismissed_keys", "list_gem_cards", "restore_gem", "save_gems"]
