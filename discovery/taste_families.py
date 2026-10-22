"""Single home for the genre-family vocabulary used by discovery.

Each profile is a deliberately separate table: they differ today and the owner
decides which behavior is canonical. Do not merge profiles here. Every table is
an ordered tuple of (family, substring terms) matched against casefolded tags.
"""
from __future__ import annotations

# Recommendation categories, exploration bonus, and query labels.
CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("jazz", ("jazz", "bebop", "hard bop", "swing")),
    ("hip-hop", ("hip hop", "hip-hop", "rap")),
    ("alternative", ("alternative", "indie rock", "post-punk",
                     "art rock", "garage rock")),
    ("brazilian", ("brazilian", "samba", "bossa nova",
                   "mpb", "tropicalia", "tropicália")),
    ("african", ("african", "afrobeat", "ethiopian", "ethiopian jazz",
                 "highlife", "soukous", "senegalese", "malian", "afropop",
                 "mbalax", "desert blues")),
    ("rnb-soul", ("r&b", "rnb", "neo-soul", "soul")),
    ("electronic", ("electronic", "electronica", "electropop",
                    "downtempo", "trip hop", "trip-hop")),
    ("funk", ("funk",)),
    ("north-african-middle-eastern", (
        "middle eastern", "arabic", "raï", "rai", "north african",
        "north-african", "maghrebi", "maghreb", "chaabi",
        "gnawa", "gnaoua", "malouf", "andalusi", "andalusian",
        "algerian", "moroccan", "tunisian", "mawwal", "tarab",
        "maqam", "levantine", "khaliji", "khaleeji", "dabke",
        "oud music", "arab pop", "arabic pop", "shaabi",
    )),
)

# Deep Dives rows: first matching rule order matters only for output order.
DEEP_DIVE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("jazz", ("jazz", "bebop", "swing")),
    ("african", ("african", "afrobeat", "afrobeats", "afropop", "highlife",
                 "soukous", "malian", "tuareg", "desert blues", "ethiopian",
                 "mbalax", "senegalese")),
    ("alternative", ("alternative", "indie rock", "post-punk", "art rock",
                     "garage rock", "shoegaze")),
    ("brazilian", ("brazilian", "samba", "bossa nova", "mpb", "tropicalia",
                   "tropicália")),
    ("hip-hop", ("hip hop", "hip-hop", "rap")),
    ("rnb-soul", ("r&b", "rnb", "neo-soul", "soul")),
    ("electronic", ("electronic", "electronica", "house", "techno",
                    "trip hop", "trip-hop", "downtempo", "idm")),
    ("funk", ("funk",)),
    ("north-african-middle-eastern", (
        "arabic", "raï", "rai", "maghreb", "north african", "algerian",
        "moroccan", "tunisian", "gnawa", "gnaoua", "chaabi", "middle eastern",
        "andalusi", "malouf")),
    ("rock", ("rock", "punk", "metal", "grunge")),
    ("pop", ("pop",)),
)

# Rolling listening profile. Exclusions ("jazz rap", "electronic rock") and the
# jazz special cases stay in recommendations.recent_style_families.
RECENT_STYLE_TERMS: dict[str, tuple[str, ...]] = {
    "soul": ("soul", "r&b", "rnb", "neo-soul"),
    "rock": ("rock", "punk", "grunge", "metal", "shoegaze", "post-punk"),
    "bossa_nova_brazilian": ("bossa nova", "samba", "mpb", "tropicalia",
                             "tropicália", "brazilian"),
    "hip-hop": ("hip hop", "hip-hop", "rap"),
    "electronic": ("electronic", "electronica", "house", "techno", "edm",
                   "synth-pop", "synthpop", "idm", "trip hop", "trip-hop"),
    "african": ("african", "afrobeat", "afrobeats", "afropop", "highlife",
                "malian", "tuareg", "desert blues", "soukous", "mbalax"),
    "north_african": ("raï", "rai", "gnawa", "chaabi", "maghreb",
                      "north african", "algerian", "moroccan", "tunisian",
                      "amazigh"),
    "funk": ("funk",),
    "pop": ("pop", "dance-pop", "synthpop"),
}
RECENT_STYLE_JAZZ_EXACT = ("bebop", "swing")
RECENT_STYLE_JAZZ_EXCLUDED = "jazz rap"
RECENT_STYLE_ROCK_EXCLUDED = "electronic rock"

# primary_recent_family tie-break order and special-case tags.
PRIMARY_RECENT_PRIORITY: tuple[str, ...] = (
    "bossa_nova_brazilian", "rock", "hip-hop", "soul",
    "electronic", "african", "north_african", "funk", "pop",
)
PRIMARY_HIPHOP_TERMS = ("hip hop", "hip-hop", "rap")
PRIMARY_SPECIFIC_JAZZ_TERMS = (
    "acid jazz", "afro-jazz", "afro jazz", "jazz fusion",
    "free jazz", "latin jazz", "ethiopian jazz", "ethio-jazz",
)

# Defaults for what counts as a listener interest.
CORE_FAMILIES = frozenset({
    "jazz", "hip-hop", "alternative", "rock", "brazilian",
    "rnb-soul", "electronic", "funk",
})
EXPLORATION_FAMILIES = frozenset({"african", "north-african-middle-eastern"})

# Last-resort artist fallback, used only when a candidate has no tags.
REGIONAL_ARTIST_FAMILIES: dict[str, str] = {
    "chebmami": "north-african-middle-eastern",
    "vieuxfarkatoure": "african",
    "alifarkatoure": "african",
    "bombino": "african",
    "tinariwen": "african",
    "mdoumoctar": "african",
    "imarhan": "african",
    "khaled": "north-african-middle-eastern",
    "chebkhaled": "north-african-middle-eastern",
    "faudel": "north-african-middle-eastern",
    "rachidtaha": "north-african-middle-eastern",
    "idir": "north-african-middle-eastern",
    "souadmassi": "north-african-middle-eastern",
    "hamidelkasri": "north-african-middle-eastern",
    "takfarinas": "north-african-middle-eastern",
    "bouchenak": "north-african-middle-eastern",
    "liliboniche": "north-african-middle-eastern",
    "orchestrenationaldebarbes": "north-african-middle-eastern",
    "chebsahraoui": "north-african-middle-eastern",
    "شابصحراوي": "north-african-middle-eastern",
}

# Tags that force the "adventurous" category.
ADVENTUROUS_TAGS: tuple[str, ...] = (
    "idm", "experimental", "avant-garde", "avant garde",
    "free improvisation", "free jazz", "drone", "noise",
    "musique concrète", "musique concrete",
    "electroacoustic", "dark ambient", "glitch",
    "deconstructed club",
)

# Display labels, sent by the server so the browser keeps no copy.
FAMILY_LABELS: dict[str, str] = {
    "jazz": "Jazz", "african": "African Music", "alternative": "Alternative",
    "brazilian": "Brazilian Music", "hip-hop": "Hip-Hop",
    "rnb-soul": "R&B / Soul", "electronic": "Electronic", "funk": "Funk",
    "north-african-middle-eastern": "North African & Middle Eastern",
    "north-african": "North African",
    "bossa-nova-brazilian": "Brazilian / Bossa Nova",
    "rock": "Rock", "pop": "Pop", "other": "Other Discoveries",
}


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
