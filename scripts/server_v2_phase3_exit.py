"""Server V2 Phase 3 live lens run and scorecard against the owner's live Navidrome.

Read-only. Navidrome: getAlbumList2 (paged) only; play count, last played, star and rating
come with each album. No MusicBrainz, ListenBrainz or other provider traffic. The intelligence
store is a temporary file that is deleted afterwards, so the owner's real accept/dismiss
history is not read or changed. Output is aggregate counts only (no titles, paths or credentials).

    python scripts/server_v2_phase3_exit.py --out phase3_exit.json

Checks (docs/ServerV2.md, Phase 3 exit and item 6):
  1. Forgotten Gems on the real library: states how many albums carry history, returns cards or
     an explicit empty reason, is identical across two runs and across shuffled input, and only
     ever names albums that are in the library
  2. persistence: save, list, dismiss (suppressed on refresh) and restore round-trip
  3. scorecard on the live output with the temporary store's outcomes (none), so the verdict is
     `insufficient_evidence` and the lens stays off; a labelled machinery check then feeds
     invented accept/dismiss rows for a synthetic library (so it runs even when the live lens
     returns no cards) through `lens_outcomes` into `score_lens` to prove the path
  4. the recommendation package is never imported (weights cannot move)
Blind spots, series, hidden canon and anniversaries need provider documents, which this
script does not fetch; their scorecards wait for the owner to approve provider traffic.
Environment: NAVIDROME_URL/USER/PASSWORD (or the local config.env).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server_v2_phase0_coverage import load_config_env, nd  # noqa: E402

from integrations.navidrome.client import items  # noqa: E402
from intelligence.insights import (  # noqa: E402
    CARD_KIND, GemsConfig, PlayRecord, accept_card, dismiss_gem, find_forgotten_gems, gem_card, lens_outcomes,
    list_gem_cards, restore_gem, save_gems, score_lens,
)
from intelligence.store import open_store  # noqa: E402


def fetch_albums() -> list[dict]:
    albums, off = [], 0
    while True:
        page = items(nd("getAlbumList2", type="alphabeticalByName", size=500, offset=off).get("albumList2", {}).get("album"))
        albums += page
        if len(page) < 500:
            return albums
        off += 500


def epoch(value) -> float | None:
    if not value or str(value).startswith("0001"):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def to_record(album: dict) -> PlayRecord:
    rating = album.get("userRating")
    return PlayRecord(
        key=f"album:{album['id']}", kind="album", title=album.get("name") or album.get("title") or "",
        artist=album.get("artist"), play_count=int(album.get("playCount") or 0),
        last_played=epoch(album.get("played")), starred=bool(album.get("starred")),
        rating=int(rating) if rating else None,
    )


def cards_of(result) -> list[dict]:
    return [gem_card(g) for g in result.gems]


def machinery_check(now: float) -> dict:
    """Invented library and outcomes through save_gems, lens_outcomes and score_lens in a temporary store."""
    day = 86400.0
    records = [
        PlayRecord(key=f"album:synthetic-{i}", kind="album", title=f"Synthetic {i}", artist=f"Artist {i}",
                   play_count=20, last_played=now - 400 * day)
        for i in range(40)
    ]
    synthetic = GemsConfig(now=now)
    found = find_forgotten_gems(records, synthetic)
    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "machinery.sqlite3")
        save_gems(db, found, now=1.0)
        cards = lens_outcomes(db, CARD_KIND)["cards"]
        for index, card in enumerate(cards):
            key = card["subject"]["key"]
            if index % 3 == 0:
                dismiss_gem(db, key, now=5.0)
            else:
                accept_card(db, CARD_KIND, key, now=5.0)
        fed = lens_outcomes(db, CARD_KIND)
        card = score_lens(CARD_KIND, fed["cards"], fed["accepted"], fed["dismissed"])
        db.close()
    return {
        "note": "synthetic library and invented accept/dismiss rows in a temporary store; says nothing about lens quality",
        "cards": card.cards, "accepted": card.accepted, "dismissed": card.dismissed, "unjudged": card.unjudged,
        "verdict": card.verdict,
        "path_exercised": card.cards >= 5 and card.accepted > 0 and card.dismissed > 0
        and card.accepted + card.dismissed == card.cards and card.verdict == "pass",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out")
    args = parser.parse_args()
    load_config_env()
    result: dict = {}

    t0 = time.time()
    albums = fetch_albums()
    records = [to_record(a) for a in albums]
    result["library"] = {"albums": len(albums), "fetch_seconds": round(time.time() - t0, 1)}
    config = GemsConfig(now=time.time())

    # 1. Forgotten Gems on the real library
    gems = find_forgotten_gems(records, config)
    shuffled = records[:]
    random.Random(7).shuffle(shuffled)
    library_keys = {r.key for r in records}
    result["forgotten_gems"] = {
        "records_with_history": gems.records_with_history,
        "with_plays": sum(r.play_count > 0 for r in records),
        "starred": sum(r.starred for r in records),
        "rated": sum(r.rating is not None for r in records),
        "with_last_played": sum(r.last_played is not None for r in records),
        "history_span_days": round((config.now - min(r.last_played for r in records if r.last_played)) / 86400, 1)
        if any(r.last_played for r in records) else None,
        "played_min_plays_times": sum(r.play_count >= config.min_plays for r in records),
        "dormant_at_least_min_days": sum(
            r.last_played is not None and (config.now - r.last_played) / 86400 >= config.min_dormant_days
            for r in records),
        "cards": len(gems.gems), "empty_reason": gems.empty_reason,
        "identical_across_two_runs": cards_of(gems) == cards_of(find_forgotten_gems(records, config)),
        "identical_from_shuffled_input": cards_of(gems) == cards_of(find_forgotten_gems(shuffled, config)),
        "every_card_is_a_library_album": all(g.record.key in library_keys for g in gems.gems),
        "every_card_has_reasons": all(g.reasons for g in gems.gems),
    }

    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "exit.sqlite3")

        # 2. persistence round trip
        stored = save_gems(db, gems, now=1.0)
        listed = list_gem_cards(db, limit=100)
        persistence: dict = {"stored": stored, "listed": len(listed), "listed_matches_run": [c["subject"]["key"] for c in listed] == [c["subject"]["key"] for c in cards_of(gems)]}
        if listed:
            key = listed[0]["subject"]["key"]
            persistence["dismiss_recorded"] = dismiss_gem(db, key, now=2.0)
            from intelligence.insights import dismissed_keys
            refreshed = find_forgotten_gems(records, config, dismissed=dismissed_keys(db))
            save_gems(db, refreshed, now=3.0)
            persistence["dismissed_card_gone_after_refresh"] = key not in {c["subject"]["key"] for c in list_gem_cards(db, limit=100)}
            persistence["suppressed_count"] = refreshed.suppressed
            persistence["restore_recorded"] = restore_gem(db, key)
        result["persistence"] = persistence

        # 3. scorecard on live output with this temporary store's outcomes (none)
        save_gems(db, gems, now=4.0)
        live = lens_outcomes(db, CARD_KIND)
        card = score_lens(CARD_KIND, live["cards"], live["accepted"], live["dismissed"])
        result["scorecard_live"] = card.as_dict()

        db.close()

    # machinery check only: a fixed synthetic library (not the live one, which may yield no cards)
    # with invented outcomes proves the save -> lens_outcomes -> score_lens path, not lens quality
    result["scorecard_machinery_check"] = machinery_check(config.now)

    # 4. weights cannot move: nothing in this run imported the recommendation package
    result["recommendation_untouched"] = not any(m == "recommendation" or m.startswith("recommendation.") for m in sys.modules)

    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0 if result["scorecard_machinery_check"]["path_exercised"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
