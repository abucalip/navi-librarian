"""Pure correctness checks for the Phase 3 provider lenses (blind spots, series, hidden canon, anniversaries).

No network and no store access. Each check takes the cards a lens produced and the independent inputs
they were computed from (the owned release-group set, the provider documents turned into comparison
sets, the world pool), recomputes the facts a card states, and returns a list of failure strings.
Used by ``server_v2_phase3_live_lenses.py --verify``; unit-tested offline.

A lens verdict is:
  * ``failed``    at least one check failed
  * ``no_cards``  nothing failed, but the lens produced no cards, so nothing was verified
  * ``verified``  cards were produced and every check passed
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any, Iterable, Mapping

from intelligence.insights.blind_spots import ComparisonSet, dismiss_key as blind_spot_key
from intelligence.insights.series_completion import SeriesConfig, dismiss_key as series_key

_OWN_OF = re.compile(r"You own (\d+) of (\d+)")


def _norm(value: str | None) -> str:
    return (value or "").strip().lower()


def common_failures(cards: Iterable[Mapping[str, Any]]) -> list[str]:
    """Checks every generic insight card must pass: explainable, dismissible, uniquely keyed."""
    failures: list[str] = []
    seen: set[str] = set()
    for card in cards:
        key = (card.get("subject") or {}).get("key")
        if not key:
            failures.append("card without subject.key")
            continue
        if key in seen:
            failures.append(f"duplicate key {key}")
        seen.add(key)
        if not card.get("reasons"):
            failures.append(f"{key}: no reasons")
        elif not all(r.get("kind") and r.get("evidence") for r in card["reasons"]):
            failures.append(f"{key}: reason without kind or evidence")
        if not card.get("title") or not card.get("body"):
            failures.append(f"{key}: missing title or body")
        if not card.get("dismissible") or {"kind": "dismiss"} not in (card.get("actions") or []):
            failures.append(f"{key}: not dismissible")
    return failures


def _set_by_key(sets: Iterable[ComparisonSet], make_key) -> dict[str, ComparisonSet]:
    return {make_key(s.key): s for s in sets}


def blind_spot_failures(cards: list[Mapping[str, Any]], sets: Iterable[ComparisonSet], owned: set[str]) -> list[str]:
    """Recompute owned/total from the comparison set and check every listed missing item is unowned."""
    failures: list[str] = []
    by_key = _set_by_key(sets, blind_spot_key)
    for card in cards:
        key = card["subject"]["key"]
        source = by_key.get(key)
        if source is None:
            failures.append(f"{key}: no comparison set backs this card")
            continue
        ids = [_norm(i.group_mbid) for i in source.items if _norm(i.group_mbid)]
        match = _OWN_OF.search(card.get("body") or "")
        if not match:
            failures.append(f"{key}: body states no owned/total count")
        else:
            claimed_owned, claimed_total = int(match.group(1)), int(match.group(2))
            real_owned = sum(1 for i in ids if i in owned)
            if (claimed_owned, claimed_total) != (real_owned, len(ids)):
                failures.append(f"{key}: states {claimed_owned} of {claimed_total}, recomputed {real_owned} of {len(ids)}")
        for item in card.get("missing") or []:
            mbid = _norm(item.get("group_mbid"))
            if mbid in owned:
                failures.append(f"{key}: lists owned group {mbid} as missing")
            if mbid not in set(ids):
                failures.append(f"{key}: lists {mbid} which is not in the set")
            if not (item.get("title") or "").strip():
                failures.append(f"{key}: lists {mbid} without a title")
        if card.get("missing_total", 0) != len(ids) - sum(1 for i in ids if i in owned):
            failures.append(f"{key}: missing_total does not match the set")
    return failures


def series_failures(
    cards: list[Mapping[str, Any]], sets: Iterable[ComparisonSet], owned: set[str], config: SeriesConfig | None = None,
) -> list[str]:
    config = config or SeriesConfig()
    failures: list[str] = []
    by_key = _set_by_key(sets, series_key)
    for card in cards:
        key = card["subject"]["key"]
        source = by_key.get(key)
        if source is None:
            failures.append(f"{key}: no series document backs this card")
            continue
        ids = [_norm(i.group_mbid) for i in source.items if _norm(i.group_mbid)]
        real_owned = sum(1 for i in ids if i in owned)
        if card.get("total") != len(ids) or card.get("owned") != real_owned:
            failures.append(f"{key}: states {card.get('owned')} of {card.get('total')}, recomputed {real_owned} of {len(ids)}")
        if card.get("owned", 0) + card.get("missing_total", 0) != card.get("total"):
            failures.append(f"{key}: owned plus missing is not total")
        if real_owned < config.min_owned or len(ids) < config.min_size:
            failures.append(f"{key}: below the minimum owned or size gate")
        if ids and real_owned / len(ids) < config.min_share_owned:
            failures.append(f"{key}: barely started series was not left out")
        listed_items = [i for run in card.get("missing_runs") or [] for i in run.get("items") or []]
        for item in listed_items:
            if not (item.get("title") or "").strip():
                failures.append(f"{key}: lists {item.get('group_mbid')} without a title")
        listed = [_norm(i.get("group_mbid")) for i in listed_items]
        for mbid in listed:
            if mbid in owned:
                failures.append(f"{key}: lists owned group {mbid} as missing")
            if mbid not in set(ids):
                failures.append(f"{key}: lists {mbid} which is not in the series")
    return failures


def canon_failures(
    cards: list[Mapping[str, Any]], owned: set[str], world: Iterable[Any], top_genres: Iterable[str],
) -> list[str]:
    """Hidden canon: never owned, drawn from the fetched pool, matched to one of the owner's top genres."""
    failures: list[str] = []
    pool = {_norm(a.group_mbid): a for a in world if _norm(a.group_mbid)}
    genres = {_norm(g) for g in top_genres}
    for card in cards:
        key = card["subject"]["key"]
        mbid = _norm(card["subject"].get("group_mbid"))
        if mbid in owned:
            failures.append(f"{key}: group {mbid} is owned")
        if not (card["subject"].get("artist") or "").strip():
            failures.append(f"{key}: no artist")
        album = pool.get(mbid)
        if album is None:
            failures.append(f"{key}: group {mbid} is not in the fetched world pool")
            continue
        evidence = (card.get("reasons") or [{}])[0].get("evidence") or {}
        if evidence.get("listens") != album.listens:
            failures.append(f"{key}: listens {evidence.get('listens')} differ from the document {album.listens}")
        matched = _norm(evidence.get("matched_genre"))
        if matched not in genres:
            failures.append(f"{key}: matched genre {matched!r} is not one of the owner's top genres")
        if matched not in {_norm(g) for g in album.genres}:
            failures.append(f"{key}: matched genre {matched!r} is not a genre of the album's artist")
    return failures


def anniversary_failures(
    cards: list[Mapping[str, Any]], owned: set[str], today: date, window_days: int,
    album_dates: Mapping[str, str | None],
) -> list[str]:
    """Anniversaries: the dated fact is right, today's window holds, and album cards are for owned groups."""
    failures: list[str] = []
    for card in cards:
        key = card["subject"]["key"]
        evidence = (card.get("reasons") or [{}])[0].get("evidence") or {}
        try:
            event = date.fromisoformat(evidence.get("date"))
        except (TypeError, ValueError):
            failures.append(f"{key}: no full event date in the evidence")
            continue
        years = card["subject"].get("years")
        if not isinstance(years, int) or years < 1 or years != evidence.get("years"):
            failures.append(f"{key}: years {years!r} is not a positive count matching the evidence")
        else:
            try:
                anniversary = event.replace(year=event.year + years)
            except ValueError:  # 29 February
                anniversary = event.replace(year=event.year + years, day=28)
            if abs((anniversary - today).days) > window_days:
                failures.append(
                    f"{key}: the {years}-year anniversary of {event.isoformat()} is not within {window_days} days of {today.isoformat()}")
        if card["subject"].get("event") == "album_release":
            mbid = _norm(card["subject"].get("mbid"))
            if mbid not in owned:
                failures.append(f"{key}: album {mbid} is not owned")
            source = (album_dates.get(mbid) or "")
            if source != event.isoformat():
                failures.append(f"{key}: date {event.isoformat()} differs from the document {source or 'none'}")
    return failures


def verdict(cards: list[Any], failures: list[str]) -> str:
    if failures:
        return "failed"
    return "verified" if cards else "no_cards"


def run_integrity(calls: Mapping[str, int], max_requests: int, job_failures: int = 0) -> dict[str, Any]:
    """The run itself must have finished cleanly inside its request budget, or no verdict is trustworthy."""
    total = calls.get("musicbrainz", 0) + calls.get("listenbrainz", 0)
    problems = []
    if total > max_requests:
        problems.append(f"{total} provider requests exceeded the budget of {max_requests}")
    for name in sorted(calls):
        if name in ("musicbrainz_gave_up", "series_browse_failed", "series_doc_failed") or name.startswith("status_") or (name == "network_retries" and calls[name] >= 5):
            problems.append(f"{name}={calls[name]}")
    if job_failures:
        problems.append(f"{job_failures} document fetches failed")
    return {"requests": total, "budget": max_requests, "complete": not problems, "problems": problems}
