"""Single home for the genre-family vocabulary used by discovery.

The tables live in settings/taste_defaults.json, loaded once at import. The
shipped file reproduces the original hard-coded behavior exactly. Each profile
is a deliberately separate table: they differ today and the owner decides which
behavior is canonical. Do not merge profiles here. Rule tables are ordered
(family, substring terms) pairs matched against casefolded tags.
"""
from __future__ import annotations

import json
from pathlib import Path

DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "settings" / "taste_defaults.json"


def _load(path: Path = DEFAULTS_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _rules(raw) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return tuple((str(family), tuple(terms)) for family, terms in raw)


_DEFAULTS = _load()

# Recommendation categories, exploration bonus, and query labels.
CATEGORY_RULES = _rules(_DEFAULTS["category_rules"])

# Deep Dives rows: first matching rule order matters only for output order.
DEEP_DIVE_RULES = _rules(_DEFAULTS["deep_dive_rules"])

# Rolling listening profile. Exclusions ("jazz rap", "electronic rock") and the
# jazz special cases stay in recommendations.recent_style_families.
RECENT_STYLE_TERMS: dict[str, tuple[str, ...]] = {
    k: tuple(v) for k, v in _DEFAULTS["recent_style_terms"].items()
}
RECENT_STYLE_JAZZ_EXACT = tuple(_DEFAULTS["recent_style_jazz_exact"])
RECENT_STYLE_JAZZ_EXCLUDED = _DEFAULTS["recent_style_jazz_excluded"]
RECENT_STYLE_ROCK_EXCLUDED = _DEFAULTS["recent_style_rock_excluded"]

# primary_recent_family tie-break order and special-case tags.
PRIMARY_RECENT_PRIORITY: tuple[str, ...] = tuple(_DEFAULTS["primary_recent_priority"])
PRIMARY_HIPHOP_TERMS = tuple(_DEFAULTS["primary_hiphop_terms"])
PRIMARY_SPECIFIC_JAZZ_TERMS = tuple(_DEFAULTS["primary_specific_jazz_terms"])

# Defaults for what counts as a listener interest.
CORE_FAMILIES = frozenset(_DEFAULTS["core_families"])
EXPLORATION_FAMILIES = frozenset(_DEFAULTS["exploration_families"])

# Last-resort artist fallback, used only when a candidate has no tags.
REGIONAL_ARTIST_FAMILIES: dict[str, str] = dict(_DEFAULTS["regional_artist_families"])

# Tags that force the "adventurous" category.
ADVENTUROUS_TAGS: tuple[str, ...] = tuple(_DEFAULTS["adventurous_tags"])

# Display labels, sent by the server so the browser keeps no copy.
FAMILY_LABELS: dict[str, str] = dict(_DEFAULTS["family_labels"])


def family_label(key: str) -> str:
    """Display label for a family key; unknown keys are title-cased."""
    if key in FAMILY_LABELS:
        return FAMILY_LABELS[key]
    return " ".join(w[:1].upper() + w[1:] for w in key.replace("-", " ").split())


def deep_dive_row(item: dict) -> dict[str, str]:
    """Row key and label for a Deep Dives item, decided server-side."""
    families = item.get("genre_families")
    families = families if isinstance(families, list) else []
    key = next((str(f).strip() for f in families if str(f or "").strip()), "")
    if key:
        key = key.replace("_", "-").casefold()
    else:
        genres = item.get("genres")
        text = " ".join(str(g).casefold() for g in (genres if isinstance(genres, list) else []))
        key = next((f for f, terms in DEEP_DIVE_RULES if any(t in text for t in terms)), "other")
    return {"genre_row": key, "genre_row_label": family_label(key)}
