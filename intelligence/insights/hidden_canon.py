"""Hidden canon, basic taste vs world (Phase 3 item 4).

Pure and deterministic. The caller supplies sitewide-popular release groups (for example
ListenBrainz sitewide listen counts), the owner's top genres in rank order, and the
release-group MBIDs the library owns. Nothing here fetches, writes or touches the store, so a
card can never change an ownership flag or a recommendation weight. The deeper taste
fingerprint is Phase 6.

A card states a fact: "Heard by N listeners worldwide; matches your top genre <genre>; not in
your library". It never says "you should own"; the only action is dismiss.

Rules:

* ownership is by release-group MBID only (case-insensitive); a title is never matched, and an
  owned group is never a candidate (counted in ``owned_excluded``);
* candidates with no MBID, repeated MBIDs, or a listen count under ``min_listens`` are dropped;
* only the owner's top ``top_genres`` genres count; a candidate must share at least one;
* fewer than ``min_top_genres`` known genres is sparse taste: an empty result with a reason, never a guess;
* score = popularity * genre_weight. popularity = ``log1p(listens) / log1p(max listens in pool)``;
  genre_weight = ``1 - rank / n`` for the best matching genre (rank 0 is the top genre, n the
  number of genres used). Score only ranks; it is not shown as a promise;
* at most ``max_per_artist`` cards per artist, so one artist cannot fill the list;
* dismissed keys (``hidden_canon:<group mbid>``) are dropped before ranking (suppression memory).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable

CARD_KIND = "hidden_canon"


@dataclass(frozen=True)
class WorldAlbum:
    group_mbid: str | None
    title: str
    artist: str | None = None
    year: int | None = None
    genres: tuple[str, ...] = ()
    listens: int = 0                 # sitewide listen count from the provider
    source: str = "listenbrainz"


@dataclass(frozen=True)
class CanonConfig:
    top_genres: int = 5
    min_top_genres: int = 2
    min_listens: int = 1000
    max_per_artist: int = 2
    limit: int = 20


@dataclass(frozen=True)
class CanonPick:
    album: WorldAlbum
    matched_genre: str
    genre_rank: int
    popularity: float
    genre_weight: float

    @property
    def score(self) -> float:
        return round(self.popularity * self.genre_weight, 6)

    @property
    def reasons(self) -> list[dict[str, Any]]:
        return [{"kind": "taste_vs_world", "evidence": {
            "source": self.album.source, "listens": self.album.listens,
            "matched_genre": self.matched_genre, "genre_rank": self.genre_rank + 1}}]


@dataclass(frozen=True)
class CanonResult:
    picks: tuple[CanonPick, ...] = ()
    owned_excluded: int = 0
    dropped: int = 0                 # no MBID, repeated, too few listens, or no matching genre
    suppressed: int = 0
    empty_reason: str | None = None  # "no_candidates_supplied" | "sparse_taste" | "no_candidates" | None
    config: CanonConfig = field(default_factory=CanonConfig)


def dismiss_key(group_mbid: str) -> str:
    return f"{CARD_KIND}:{group_mbid}"


def _norm(value: str | None) -> str | None:
    value = (value or "").strip().lower()
    return value or None


def find_hidden_canon(
    candidates: Iterable[WorldAlbum], owned_group_mbids: Iterable[str], taste_genres: Iterable[str],
    config: CanonConfig | None = None, dismissed: Iterable[str] = (),
) -> CanonResult:
    config = config or CanonConfig()
    pool = list(candidates)
    if not pool:
        return CanonResult(empty_reason="no_candidates_supplied", config=config)
    genres: list[str] = []
    for g in taste_genres:
        n = _norm(g)
        if n and n not in genres:
            genres.append(n)
    genres = genres[: max(config.top_genres, 0)]
    if len(genres) < max(config.min_top_genres, 1):
        return CanonResult(empty_reason="sparse_taste", config=config)
    rank_of = {g: i for i, g in enumerate(genres)}
    owned = {m for m in (_norm(x) for x in owned_group_mbids) if m}
    blocked = set(dismissed)

    seen: set[str] = set()
    eligible: list[tuple[WorldAlbum, str, str, int]] = []
    owned_excluded = dropped = suppressed = 0
    for a in pool:
        m = _norm(a.group_mbid)
        if m is None or m in seen or a.listens < config.min_listens:
            dropped += 1
            continue
        seen.add(m)
        if m in owned:
            owned_excluded += 1
            continue
        matches = [(rank_of[g], g) for g in {_norm(x) for x in a.genres} if g in rank_of]
        if not matches:
            dropped += 1
            continue
        if dismiss_key(m) in blocked:
            suppressed += 1
            continue
        rank, genre = min(matches)
        eligible.append((a, m, genre, rank))

    if not eligible:
        return CanonResult(owned_excluded=owned_excluded, dropped=dropped, suppressed=suppressed,
                           empty_reason="no_candidates", config=config)
    top = math.log1p(max(a.listens for a, *_ in eligible))
    picks = [
        CanonPick(WorldAlbum(m, a.title, a.artist, a.year, a.genres, a.listens, a.source), genre, rank,
                  round(math.log1p(a.listens) / top, 6) if top else 0.0,
                  round(1 - rank / len(genres), 6))
        for a, m, genre, rank in eligible
    ]
    picks.sort(key=lambda p: (-p.score, p.album.group_mbid))
    per_artist: dict[str, int] = {}
    kept: list[CanonPick] = []
    for p in picks:
        artist = _norm(p.album.artist) or f"mbid:{p.album.group_mbid}"
        if per_artist.get(artist, 0) >= config.max_per_artist:
            dropped += 1
            continue
        per_artist[artist] = per_artist.get(artist, 0) + 1
        kept.append(p)
    kept = kept[: max(config.limit, 0)]
    return CanonResult(
        picks=tuple(kept), owned_excluded=owned_excluded, dropped=dropped, suppressed=suppressed,
        empty_reason=None if kept else "no_candidates", config=config,
    )


def canon_card(pick: CanonPick) -> dict[str, Any]:
    """Generic insight card (docs/ServerV2.md section 8). States facts; never advice."""
    a = pick.album
    return {
        "kind": CARD_KIND,
        "title": a.title,
        "body": (f"Heard {a.listens:,} times worldwide; matches your top genre {pick.matched_genre}; "
                 "not in your library."),
        "subject": {"key": dismiss_key(a.group_mbid), "type": "release_group", "title": a.title,
                    "artist": a.artist, "group_mbid": a.group_mbid, "year": a.year},
        "actions": [{"kind": "dismiss"}],
        "reasons": pick.reasons,
        "dismissible": True,
        "score": pick.score,
    }
