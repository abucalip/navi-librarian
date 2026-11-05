"""Collection intelligence as insight cards (docs/ServerV2.md Phase 3)."""
from .forgotten_gems import (
    CARD_KIND, Gem, GemsConfig, GemsResult, PlayRecord, find_forgotten_gems, gem_card,
)
from .blind_spots import (
    BlindSpot, BlindSpotsConfig, BlindSpotsResult, ComparisonSet, SetItem, blind_spot_card, find_blind_spots,
)
from .blind_spot_persistence import (
    dismiss_blind_spot, dismissed_set_keys, list_blind_spot_cards, restore_blind_spot, save_blind_spots,
)
from .set_fetchers import build_set_fetchers
from .set_job import SetFetchers, SetJobResult, owned_group_mbids, refresh_blind_spots
from .series_completion import (
    MissingRun, SeriesConfig, SeriesProgress, SeriesResult, find_series_progress, series_card,
)
from .hidden_canon import (
    CanonConfig, CanonPick, CanonResult, WorldAlbum, canon_card, find_hidden_canon,
)
from .anniversaries import (
    Anniversary, AnniversaryConfig, AnniversaryResult, DatedAlbum, DatedArtist, anniversary_card, find_anniversaries,
)
from .card_persistence import (
    dismiss_anniversary, dismiss_canon, dismiss_series, dismissed_anniversary_keys, dismissed_canon_keys,
    dismissed_series_keys, list_anniversary_cards, list_canon_cards, list_series_cards, restore_anniversary,
    restore_canon, restore_series, save_anniversaries, save_canon, save_series,
)
from .outcomes import accept_card, accepted_keys, lens_outcomes, unaccept_card
from .runtime import EmptyLibraryError, album_to_record, refresh_forgotten_gems
from .provider_runtime import BudgetSpent, compute_and_save, refresh_provider_lenses
from .scorecard import Scorecard, ScorecardConfig, score_lens
from .persistence import dismiss_gem, dismissed_keys, list_gem_cards, restore_gem, save_gems

__all__ = ["BudgetSpent", "compute_and_save", "refresh_provider_lenses", "EmptyLibraryError", "album_to_record", "refresh_forgotten_gems", "build_set_fetchers", "CARD_KIND", "Gem", "GemsConfig", "GemsResult", "PlayRecord", "find_forgotten_gems", "gem_card",
           "BlindSpot", "BlindSpotsConfig", "BlindSpotsResult", "ComparisonSet", "SetItem", "blind_spot_card",
           "find_blind_spots", "dismiss_blind_spot", "dismissed_set_keys", "list_blind_spot_cards",
           "restore_blind_spot", "save_blind_spots", "dismiss_gem", "dismissed_keys", "list_gem_cards", "restore_gem", "save_gems",
           "MissingRun", "SeriesConfig", "SeriesProgress", "SeriesResult", "find_series_progress", "series_card",
           "CanonConfig", "CanonPick", "CanonResult", "WorldAlbum", "canon_card", "find_hidden_canon",
           "Anniversary", "AnniversaryConfig", "AnniversaryResult", "DatedAlbum", "DatedArtist",
           "anniversary_card", "find_anniversaries",
           "dismiss_anniversary", "dismiss_canon", "dismiss_series", "dismissed_anniversary_keys",
           "dismissed_canon_keys", "dismissed_series_keys", "list_anniversary_cards", "list_canon_cards",
           "list_series_cards", "restore_anniversary", "restore_canon", "restore_series", "save_anniversaries",
           "save_canon", "save_series",
           "Scorecard", "ScorecardConfig", "score_lens",
           "accept_card", "accepted_keys", "lens_outcomes", "unaccept_card",
           "SetFetchers", "SetJobResult", "owned_group_mbids", "refresh_blind_spots"]
