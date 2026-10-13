"""Pure discovery eligibility, scoring, and diversity rules."""
from __future__ import annotations
import math
import re
import unicodedata
from collections.abc import Callable, Iterable
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
