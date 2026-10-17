"""Pure discovery eligibility, scoring, and diversity rules."""
from __future__ import annotations
import math
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from typing import Any

def music_key(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return "".join(c.casefold() for c in value if c.isalnum())

def artist_identity(candidate: dict[str, Any]) -> str:
    return f"mbid:{candidate['artist_mbid']}" if candidate.get("artist_mbid") else f"name:{music_key(candidate.get('primary_artist', ''))}"

def is_album_candidate(item: Any) -> bool:
    if not isinstance(item, dict): return False
    title = str(item.get("album") or item.get("title") or item.get("name") or "").strip()
    if not title: return False
    primary = item.get("primary_type") or item.get("primary-type") or item.get("album_type") or item.get("release_type")
    if primary and re.sub(r"[^a-z]+", " ", str(primary).casefold()).strip() not in {"album", "full length album"}: return False
    secondary = item.get("secondary_types") or item.get("secondary-types") or item.get("secondary_type") or []
    if isinstance(secondary, str): secondary = re.split(r"[,;/|]", secondary)
    excluded = {"compilation","soundtrack","live","remix","dj mix","dj-mix","mixtape","ep","single","karaoke","tribute"}
    excluded_norm = {re.sub(r"[^a-z]+", " ", x).strip() for x in excluded}
    if any(re.sub(r"[^a-z]+", " ", str(v).casefold()).strip() in excluded_norm for v in secondary): return False
    title_norm = re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
    patterns = (r"\bcompilations?\b",r"\bremixes?\b",r"\bremixed\b",r"\bdj\s*mix(?:es)?\b",r"\bmixtapes?\b",r"\bsoundtracks?\b",r"\bkaraoke\b",r"\btribute\b",r"\bgreatest hits\b",r"\bbest of\b",r"\banthology\b",r"\bsamplers?\b",r"\blive\b")
    return not any(re.search(p, title_norm) for p in patterns)

def exact_artist_credit_matches(credit: Any, artist_name: str) -> bool:
    if not isinstance(credit, list) or not str(artist_name or "").strip(): return False
    target = music_key(artist_name)
    for part in credit:
        if not isinstance(part, dict): continue
        credited = str(((part.get("artist") or {}).get("name") or part.get("name") or "")).strip()
        if credited and music_key(credited) == target: return True
    return False

def is_various_artists(value: Any) -> bool:
    value = re.sub(r"[^a-z]+", " ", str(value or "").casefold()).strip()
    return value in {"various artists","various artist","various","v a"}

def deep_dive_genre_families(tags: Iterable[Any]) -> list[str]:
    text = " ".join(str(t).casefold() for t in tags)
    rules = [
      ("jazz",("jazz","bebop","swing")),
      ("african",("african","afrobeat","afrobeats","afropop","highlife","soukous","malian","tuareg","desert blues","ethiopian","mbalax","senegalese")),
      ("alternative",("alternative","indie rock","post-punk","art rock","garage rock","shoegaze")),
      ("brazilian",("brazilian","samba","bossa nova","mpb","tropicalia","tropicália")),
      ("hip-hop",("hip hop","hip-hop","rap")),("rnb-soul",("r&b","rnb","neo-soul","soul")),
      ("electronic",("electronic","electronica","house","techno","trip hop","trip-hop","downtempo","idm")),
      ("funk",("funk",)),("north-african-middle-eastern",("arabic","raï","rai","maghreb","north african","algerian","moroccan","tunisian","gnawa","gnaoua","chaabi","middle eastern","andalusi","malouf")),
      ("rock",("rock","punk","metal","grunge")),("pop",("pop",))]
    return [family for family, terms in rules if any(term in text for term in terms)]

def score_classic_candidates(candidates: Iterable[dict[str, Any]], jitter: Callable[[float,float],float]) -> list[dict[str,Any]]:
    output = list(candidates)
    for item in output:
        rating=item.get("musicbrainz_rating"); votes=int(item.get("musicbrainz_rating_votes") or 0)
        critical=(float(rating)/5.0) if rating is not None and votes else 0.0
        listeners=max(0,int(item.get("lastfm_listeners") or 0)); plays=max(0,int(item.get("lastfm_playcount") or 0))
        item["critical_recognition_available"]=bool(rating is not None and votes)
        credit=0.9 if not (rating is not None and votes) else 0.0
        item["discovery_score"]=round(critical*1.6-math.log10(listeners+1)*0.55-math.log10(plays+1)*0.10+credit,4)
        item["exploration_score"]=item["discovery_score"]+jitter(-1.4,1.4)
    return output

def refresh_exploration_scores(candidates: Iterable[dict[str,Any]], jitter: Callable[[float,float],float]) -> list[dict[str,Any]]:
    output=list(candidates)
    for item in output: item["exploration_score"]=round(item["discovery_score"]+jitter(-1.4,1.4),4)
    return output

def diversify_classic_candidates(ranked: Iterable[dict[str,Any]], *, limit: int=100, per_artist: int=2, per_family: int=8) -> list[dict[str,Any]]:
    output=[]; artist_counts={}; family_counts={}; deferred=[]
    for item in ranked:
        artist=music_key(item.get("artist","")); families=item.get("genre_families") or ["other"]
        family=next((v for v in families if family_counts.get(v,0)<per_family),families[0])
        if artist_counts.get(artist,0)>=per_artist or family_counts.get(family,0)>=per_family:
            deferred.append(item); continue
        item["primary_genre_family"]=family; output.append(item)
        artist_counts[artist]=artist_counts.get(artist,0)+1; family_counts[family]=family_counts.get(family,0)+1
        if len(output)>=limit: break
    if len(output)<limit:
        for item in deferred:
            artist=music_key(item.get("artist",""))
            if artist_counts.get(artist,0)>=per_artist: continue
            output.append(item); artist_counts[artist]=artist_counts.get(artist,0)+1
            if len(output)>=limit: break
    return output


def genre_families(tags: Iterable[str]) -> set[str]:
    """Map MusicBrainz genre tags to broad recommendation families."""
    families = set()
    for tag in tags:
        g = tag.casefold()
        if any(x in g for x in ("jazz", "bebop", "hard bop", "swing")):
            families.add("jazz")
        if any(x in g for x in ("hip hop", "hip-hop", "rap")):
            families.add("hip-hop")
        if any(x in g for x in ("alternative", "indie rock", "post-punk",
                                "art rock", "garage rock")):
            families.add("alternative")
        if any(x in g for x in ("brazilian", "samba", "bossa nova",
                                "mpb", "tropicalia", "tropicália")):
            families.add("brazilian")
        if any(x in g for x in ("african", "afrobeat", "ethiopian",
                                "ethiopian jazz", "highlife", "soukous",
                                "senegalese", "malian", "afropop",
                                "mbalax", "desert blues")):
            families.add("african")
        if any(x in g for x in ("r&b", "rnb", "neo-soul", "soul")):
            families.add("rnb-soul")
        if any(x in g for x in ("electronic", "electronica", "electropop",
                                "downtempo", "trip hop", "trip-hop")):
            families.add("electronic")
        if "funk" in g:
            families.add("funk")
        if any(x in g for x in (
            "middle eastern", "arabic", "raï", "rai", "north african",
            "north-african", "maghrebi", "maghreb", "chaabi",
            "gnawa", "gnaoua", "malouf", "andalusi", "andalusian",
            "algerian", "moroccan", "tunisian", "mawwal", "tarab",
            "maqam", "levantine", "khaliji", "khaleeji", "dabke",
            "oud music", "arab pop", "arabic pop", "shaabi",
        )):
            families.add("north-african-middle-eastern")
    return families


_REGIONAL_RECOMMENDATION_ARTIST_FAMILIES = {
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

_ADVENTUROUS_RECOMMENDATION_TAGS = (
    "idm", "experimental", "avant-garde", "avant garde",
    "free improvisation", "free jazz", "drone", "noise",
    "musique concrète", "musique concrete",
    "electroacoustic", "dark ambient", "glitch",
    "deconstructed club",
)


def classify_recommendation_category(
    candidate: Mapping[str, Any],
    tags: Iterable[str],
    core_families: set[str],
    exploration_families: set[str],
    *,
    music_key_fn: Callable[[Any], str] = music_key,
) -> tuple[str, set[str]]:
    """Return the established category and family set for a recommendation candidate.

    This policy is shared by selection and diagnostic projection so regional
    overrides and adventurous-tag precedence cannot drift between the two paths.
    """
    tags = list(tags)
    families = genre_families(tags)
    families.update(candidate.get("regional_families", []))
    artist_key = music_key_fn(
        candidate.get("primary_artist") or candidate.get("artist", "")
    )
    regional_family = _REGIONAL_RECOMMENDATION_ARTIST_FAMILIES.get(artist_key)
    if regional_family:
        families.add(regional_family)

    core_overlap = families & core_families
    exploration_overlap = families & exploration_families
    adventurous_signal = any(
        signal in tag.casefold()
        for tag in tags
        for signal in _ADVENTUROUS_RECOMMENDATION_TAGS
    )

    if not tags and not families:
        category = "unclassified"
    elif adventurous_signal:
        category = "adventurous"
    elif len(core_overlap) >= 2:
        category = "cross_genre"
    elif core_overlap or exploration_overlap:
        category = "adjacent"
    else:
        category = "adventurous"
    return category, families

def recent_style_families(tags: Iterable[str]) -> set[str]:
    """Map tags to finer listening-profile families without changing categories."""
    text_tags = [tag.casefold() for tag in tags]
    result = set()
    joined = " ".join(text_tags)
    if any(
        ("jazz" in tag and "jazz rap" not in tag)
        or tag in {"bebop", "swing"}
        for tag in text_tags
    ):
        result.add("jazz")
    if any(term in joined for term in ("soul", "r&b", "rnb", "neo-soul")):
        result.add("soul")
    if any(
        any(term in tag for term in (
            "rock", "punk", "grunge", "metal", "shoegaze", "post-punk"
        ))
        and "electronic rock" not in tag
        for tag in text_tags
    ):
        result.add("rock")
    if any(term in joined for term in (
        "bossa nova", "samba", "mpb", "tropicalia", "tropicália", "brazilian"
    )):
        result.add("bossa_nova_brazilian")
    if any(term in joined for term in ("hip hop", "hip-hop", "rap")):
        result.add("hip-hop")
    if any(term in joined for term in (
        "electronic", "electronica", "house", "techno", "edm",
        "synth-pop", "synthpop", "idm", "trip hop", "trip-hop"
    )):
        result.add("electronic")
    if any(term in joined for term in (
        "african", "afrobeat", "afrobeats", "afropop", "highlife",
        "malian", "tuareg", "desert blues", "soukous", "mbalax"
    )):
        result.add("african")
    if any(term in joined for term in (
        "raï", "rai", "gnawa", "chaabi", "maghreb", "north african",
        "algerian", "moroccan", "tunisian", "amazigh"
    )):
        result.add("north_african")
    if "funk" in joined:
        result.add("funk")
    if any(term in joined for term in ("pop", "dance-pop", "synthpop")):
        result.add("pop")
    return result


def primary_recent_family(tags: Iterable[str], family_counts: Mapping[str, int]) -> str | None:
    """Choose a representative family from more album-specific tags first."""
    families = recent_style_families(tags)
    has_hiphop_tag = any(
        any(term in tag for term in ("hip hop", "hip-hop", "rap"))
        for tag in tags
    )
    has_specific_jazz_tag = any(
        any(term in tag for term in (
            "acid jazz", "afro-jazz", "afro jazz", "jazz fusion",
            "free jazz", "latin jazz", "ethiopian jazz", "ethio-jazz",
        ))
        for tag in tags
    )
    priority = ["bossa_nova_brazilian", "rock", "hip-hop", "soul",
                "electronic", "african", "north_african", "funk", "pop"]
    if "jazz" in families and (not has_hiphop_tag or has_specific_jazz_tag):
        priority.insert(1, "jazz")
    for family in priority:
        if family in families:
            return family
    return max(
        families,
        key=lambda family: family_counts.get(family, 0),
        default=None,
    )


def decayed_listen_weights(
    listens: Iterable[Mapping[str, Any]],
    *,
    half_life_days: float = 14.0,
) -> list[float]:
    """Return deterministic recency weights anchored to the newest dated listen.

    ListenBrainz timestamps are Unix seconds. Anchoring to the newest observed
    listen keeps captured recommendation replays deterministic while making
    more recent listens contribute more strongly than older listens. Undated
    legacy/test records retain equal weight; invalid half-lives are rejected.
    """
    if not math.isfinite(half_life_days) or half_life_days <= 0:
        raise ValueError("half_life_days must be a positive finite number")

    records = list(listens)
    timestamps: list[float | None] = []
    for listen in records:
        try:
            value = float(listen.get("listened_at"))
            timestamps.append(value if math.isfinite(value) else None)
        except (TypeError, ValueError, AttributeError):
            timestamps.append(None)

    dated = [value for value in timestamps if value is not None]
    if not dated:
        return [1.0] * len(records)
    reference = max(dated)
    half_life_seconds = half_life_days * 24 * 60 * 60
    return [
        1.0 if timestamp is None else
        0.5 ** (max(0.0, reference - timestamp) / half_life_seconds)
        for timestamp in timestamps
    ]


def apply_familiarity_exploration_bonus(
    candidate: dict[str, Any],
    recent_artist_count: float,
    genre_tags: Iterable[str],
    exploration_families: set[str],
) -> float:
    """Apply the established recent-familiarity and exploration score multipliers."""
    # Smoothly favor artists with a little familiarity over both extremes:
    # entirely unknown artists and artists already heard very frequently.
    # Counts may be recency-weighted floats rather than raw integer scrobbles.
    count = max(0.0, float(recent_artist_count or 0))
    familiarity_factor = 0.82 + 0.42 * math.exp(-((count - 1.5) / 3.0) ** 2)

    candidate_families = genre_families(genre_tags)
    exploration_bonus = (
        1.10 if candidate_families & exploration_families else 1.0
    )
    candidate["discovery_score"] = (
        candidate["score"] * familiarity_factor * exploration_bonus
    )
    return candidate["discovery_score"]

def apply_lastfm_popularity_bonus(
    candidates: Iterable[dict[str, Any]],
    recent_family_counts: Mapping[str, int],
    popularity_lookup: Callable[[str, str], Mapping[str, Any] | None],
) -> int:
    """Apply the existing bounded Last.fm popularity/profile adjustments in place.

    Returns the number of candidates with usable Last.fm stats, matching the
    diagnostic counter previously maintained by the legacy recommendation adapter.
    """
    checked = 0
    for candidate in sorted(
        candidates,
        key=lambda album: album["discovery_score"],
        reverse=True,
    )[:40]:
        stats = popularity_lookup(
            candidate.get("primary_artist") or candidate.get("artist", ""),
            candidate.get("album", ""),
        )
        if stats is None:
            continue

        candidate["lastfm_listeners"] = stats["listeners"]
        candidate["lastfm_playcount"] = stats["playcount"]
        candidate["lastfm_tags"] = stats.get("tags", [])
        if candidate["lastfm_tags"]:
            candidate["listening_families"] = sorted(
                recent_style_families(candidate["lastfm_tags"])
            )
            candidate["recent_profile_families"] = [
                family for family in candidate["listening_families"]
                if recent_family_counts.get(family, 0) > 0
            ]
            candidate["recent_profile_family"] = primary_recent_family(
                candidate["lastfm_tags"], recent_family_counts
            )
            old_profile_bonus = candidate.get("recent_profile_bonus", 1.0)
            matched_families = candidate["recent_profile_families"]
            if matched_families and recent_family_counts:
                max_count = max(recent_family_counts.values())
                average_count = sum(
                    recent_family_counts[family]
                    for family in matched_families
                ) / len(matched_families)
                new_profile_bonus = 1.0 + 0.25 * average_count / max_count
            else:
                new_profile_bonus = 1.0
            candidate["discovery_score"] = (
                candidate["discovery_score"]
                / old_profile_bonus
                * new_profile_bonus
            )
            candidate["recent_profile_bonus"] = new_profile_bonus

        checked += 1
        listener_signal = min(
            1.0, math.log10(stats["listeners"] + 1) / 6.0
        )
        playcount_signal = min(
            1.0, math.log10(stats["playcount"] + 1) / 7.0
        )
        candidate["lastfm_popularity_bonus"] = (
            1.0 + 0.08 * listener_signal + 0.04 * playcount_signal
        )
        candidate["discovery_score"] *= candidate["lastfm_popularity_bonus"]
    return checked

def classify_diversity_style(candidate: Mapping[str, Any], tags: Iterable[str]) -> str:
    """Assign a regional/style slot used to diversify recommendation results."""
    artist_key = music_key(
        candidate.get("primary_artist") or candidate.get("artist", "")
    )
    tag_text = " ".join(tags).casefold()
    regional_style_hints = candidate.get("regional_styles", [])
    for style_hint in (
        "north_african", "afrobeats", "afro_jazz",
        "malian_desert_blues",
    ):
        if style_hint in regional_style_hints:
            return style_hint

    north_african_names = {
        "chebmami", "khaled", "chebkhaled", "faudel", "rachidtaha",
        "idir", "souadmassi", "hamidelkasri", "takfarinas", "bouchenak",
        "liliboniche", "orchestrenationaldebarbes", "chebsahraoui",
        "شابصحراوي",
    }
    desert_blues_names = {
        "vieuxfarkatoure", "alifarkatoure", "bombino", "tinariwen",
        "mdoumoctar", "imarhan",
    }

    if (
        artist_key in north_african_names
        or any(term in tag_text for term in (
            "raï", "rai", "chaabi", "gnawa", "amazigh",
            "north african", "north-african", "maghreb", "algerian",
        ))
    ):
        return "north_african"
    if any(term in tag_text for term in (
        "afrobeats", "afro-beats", "afropop", "afro-pop",
    )):
        return "afrobeats"
    if any(term in tag_text for term in (
        "afro-jazz", "afro jazz", "african jazz", "ethio-jazz",
        "ethiojazz", "south african jazz",
    )):
        return "afro_jazz"
    if (
        artist_key in desert_blues_names
        or any(term in tag_text for term in (
            "desert blues", "malian blues", "malian guitar", "tuareg",
            "assouf", "wassoulou",
        ))
    ):
        return "malian_desert_blues"
    return "other"

def rank_and_diversify_deep_dive_candidates(
    candidates: Iterable[dict[str, Any]],
    *,
    music_key: Callable[[Any], str],
    is_album_candidate: Callable[[Any], bool],
    jitter: Callable[[float, float], float],
    limit: int = 150,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Score, rank, and diversify already-enriched deep-dive candidates."""
    import math

    output = list(candidates)
    for item in output:
        popularity = math.log10(max(0, int(item.get("lastfm_listeners") or 0)) + 1)
        playcount = math.log10(max(0, int(item.get("lastfm_playcount") or 0)) + 1)
        candidate_score = float(item.get("candidate_pool_score", 0) or 0)
        candidate_bonus = candidate_score * 2.5
        anchor_bonus = (
            min(int(item.get("anchor_album_count", 0) or 0), 15) * 0.05
            if candidate_score else 0.0
        )
        item["discovery_score"] = round(
            popularity * 0.15 + playcount * 0.03
            + float(item.get("similar_artist_score", 0)) * 2.0
            + candidate_bonus + anchor_bonus,
            4,
        )
    for item in output:
        listeners = max(0, int(item.get("lastfm_listeners") or 0))
        magnitude = math.log10(listeners + 1)
        item["exploration_score"] = round(
            item["discovery_score"] - magnitude * 0.65
            + max(0.0, 6.0 - magnitude) * 0.35, 4,
        )
    for item in output:
        item["exploration_score"] = round(
            float(item.get("exploration_score", 0) or 0) + jitter(-1.25, 1.25), 4,
        )
    ranked = sorted(
        (item for item in output if is_album_candidate(item)),
        key=lambda item: (
            item["exploration_score"],
            float(item.get("similar_artist_score", 0) or 0),
        ),
        reverse=True,
    )
    diversified: list[dict[str, Any]] = []
    artist_counts: dict[str, int] = {}
    anchor_counts: dict[str, int] = {}
    genre_counts: dict[str, int] = {}
    deferred: list[dict[str, Any]] = []
    for item in ranked:
        artist_key = music_key(item.get("artist", ""))
        anchor_key = music_key(item.get("anchor_artist", ""))
        families = item.get("genre_families") or ["other"]
        family = next((value for value in families if genre_counts.get(value, 0) < 12), families[0])
        if artist_counts.get(artist_key, 0) >= 2 or (anchor_key and anchor_counts.get(anchor_key, 0) >= 4) or genre_counts.get(family, 0) >= 12:
            deferred.append(item)
            continue
        item["primary_genre_family"] = family
        diversified.append(item)
        artist_counts[artist_key] = artist_counts.get(artist_key, 0) + 1
        genre_counts[family] = genre_counts.get(family, 0) + 1
        if anchor_key:
            anchor_counts[anchor_key] = anchor_counts.get(anchor_key, 0) + 1
        if len(diversified) >= limit:
            break
    if len(diversified) < limit:
        for item in deferred:
            artist_key = music_key(item.get("artist", ""))
            anchor_key = music_key(item.get("anchor_artist", ""))
            if artist_counts.get(artist_key, 0) >= 2 or (anchor_key and anchor_counts.get(anchor_key, 0) >= 4):
                continue
            diversified.append(item)
            artist_counts[artist_key] = artist_counts.get(artist_key, 0) + 1
            if anchor_key:
                anchor_counts[anchor_key] = anchor_counts.get(anchor_key, 0) + 1
            if len(diversified) >= limit:
                break
    return ranked, diversified



def classify_recommendation_candidates(
    albums: Mapping[str, dict[str, Any]],
    genre_cache: Mapping[str, Iterable[str]],
    core_families: set[str],
    exploration_families: set[str],
    recent_family_counts: Mapping[str, int],
    *,
    music_key_fn: Callable[[Any], str] = music_key,
) -> dict[str, list[dict[str, Any]]]:
    """Enrich recommendation candidates and group them by discovery category."""
    candidates_by_category = {
        "adjacent": [], "cross_genre": [], "adventurous": [], "unclassified": [],
    }
    for candidate in albums.values():
        tags = genre_cache.get(candidate.get("artist_mbid"), [])
        candidate["diversity_style"] = classify_diversity_style(candidate, tags)
        category, families = classify_recommendation_category(
            candidate, tags, core_families, exploration_families,
            music_key_fn=music_key_fn,
        )
        candidate["genres"] = tags
        candidate["genre_families"] = sorted(families)
        candidate["listening_families"] = sorted(recent_style_families(tags))
        candidate["recent_profile_families"] = [
            family for family in candidate["listening_families"]
            if recent_family_counts.get(family, 0) > 0
        ]
        candidate["recent_profile_family"] = primary_recent_family(
            tags, recent_family_counts
        )
        matched = candidate["recent_profile_families"]
        if matched and recent_family_counts:
            max_count = max(recent_family_counts.values())
            average = sum(recent_family_counts[family] for family in matched) / len(matched)
            bonus = 1.0 + 0.25 * (average / max_count)
            candidate["recent_profile_bonus"] = bonus
            candidate["discovery_score"] *= bonus
        else:
            candidate["recent_profile_bonus"] = 1.0
        candidate["discovery_category"] = category
        candidate["genre_metadata_available"] = bool(tags)
        candidates_by_category[category].append(candidate)
    return candidates_by_category
