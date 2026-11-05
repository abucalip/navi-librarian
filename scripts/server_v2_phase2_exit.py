"""Server V2 Phase 2 exit verification against the owner's private golden set.

Offline and read-only. No Navidrome, MusicBrainz or other provider traffic: the MusicBrainz
documents are the ones the Phase 0 golden-set capture already stored, and the lookup is a
local function over them. The intelligence store is a temporary file that is deleted afterwards.
Output is aggregate counts and golden-set row numbers only (no titles, paths or credentials).

    python scripts/server_v2_phase2_exit.py --golden ../golden-set-phase0 --out phase2_exit.json

Checks (docs/ServerV2.md, Phase 2 exit):
  1. release-group linking: every golden album is either linked to its MusicBrainz group (by an
     exact library MBID) or left explicitly unlinked; no album the owner marked as another
     edition, or not in MusicBrainz, is silently linked (wrong silent merge = 0)
  2. accuracy = correct or explicitly unresolved, target at least 90% (strict: albums the
     owner could not verify count as not correct; lenient: they count as unresolved)
  3. grouping, duplicate finder and edition labels run over the linked set without error
  4. ownership flag: off by default, never changes an owned answer, and across all pairs of
     golden albums reports another edition only when the titles match once edition words
     are set aside
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery.search.normalize import album_match_key  # noqa: E402
from intelligence.editions import (  # noqa: E402
    edition_awareness_enabled, edition_labels, edition_match, find_duplicates, group_editions,
    parse_release, sweep_owned_releases,
)
from intelligence.editions.ownership import FLAG_ENV, OTHER_EDITION, SAME_EDITION, base_key  # noqa: E402
from intelligence.store import open_store  # noqa: E402
from intelligence.store import repositories as repo  # noqa: E402

CORRECT = "match_correct"
NO_EDITION_CLAIM = {"unresolved", "other_edition", "not_in_musicbrainz"}


def load(golden: Path) -> list[dict]:
    entries = json.loads((golden / "candidates.json").read_text())["entries"]
    verdicts = json.loads((golden / "verdicts.json").read_text())
    for number, entry in enumerate(entries, 1):
        entry["n"] = number
        entry["status"] = verdicts[str(number)]["status"]
    return entries


def release_document(entry: dict) -> dict:
    """The MusicBrainz release document the Phase 0 capture stored for this album."""
    mb = entry["musicbrainz"]
    matched = mb["matched_release"]
    return {
        "id": matched["mbid"], "title": matched["title"], "date": matched["date"],
        "country": matched["country"], "status": matched["status"],
        "disambiguation": matched.get("disambiguation", ""),
        "release-group": {"id": mb["release_group_mbid"], "title": matched["title"],
                          "primary-type": "Album"},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--golden", required=True, help="folder with candidates.json and verdicts.json")
    parser.add_argument("--out")
    args = parser.parse_args()
    entries = load(Path(args.golden))
    result: dict = {"golden_albums": len(entries)}

    documents = {e["navidrome"]["release_mbid"]: release_document(e)
                 for e in entries if e["navidrome"].get("release_mbid")}
    lookups: list[str] = []

    def fetch(mbid: str):
        lookups.append(mbid)
        return documents.get(mbid)

    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "exit.sqlite3")
        release_ids: dict[int, int] = {}
        for e in entries:
            nav = e["navidrome"]
            release_ids[e["n"]] = repo.upsert_entity(
                db, "release", nav["title"], mbid=nav.get("release_mbid") or None,
                navidrome_id=nav["id"], owned=True)[0]

        sweep = sweep_owned_releases(db, fetch=fetch, now=1.0, limit=len(entries))
        again = sweep_owned_releases(db, fetch=fetch, now=2.0, limit=len(entries))

        # 1 + 2: outcome per album against the owner's verdict
        linked_group: dict[int, str | None] = {}
        for e in entries:
            edges = repo.edges_from(db, release_ids[e["n"]], "member_of")
            linked_group[e["n"]] = repo.get_entity(db, edges[0]["to_id"])["mbid"] if edges else None

        correct, unlinked_ok, unverifiable, wrong, mislinked = [], [], [], [], []
        for e in entries:
            n, status, group = e["n"], e["status"], linked_group[e["n"]]
            if status == CORRECT:
                expected = e["musicbrainz"]["release_group_mbid"]
                (correct if group == expected else mislinked).append(n)
            elif group is None:
                unlinked_ok.append(n)
            elif status == "unresolved":
                unverifiable.append(n)  # tag-asserted MBID the owner could not confirm either way
            else:
                wrong.append(n)  # linked although the owner says another edition or not in MusicBrainz
        total = len(entries)
        strict = len(correct) + len(unlinked_ok)
        result["linking"] = {
            "sweep": {k: getattr(sweep, k) for k in
                      ("looked_up", "linked", "already_linked", "conflicts", "not_found", "deferred", "invalid")},
            "second_sweep_looked_up": again.looked_up, "provider_lookups_are_local": True,
            "linked_correct": len(correct), "unlinked_explicitly_unresolved": len(unlinked_ok),
            "linked_but_owner_could_not_verify": unverifiable,
            "wrong_silent_merges": wrong, "linked_to_wrong_group": mislinked,
            "accuracy_strict": round(strict / total, 3),
            "accuracy_lenient": round((strict + len(unverifiable)) / total, 3),
        }

        # 3. grouping, labels, duplicates over what linked
        groups = {g for g in linked_group.values() if g}
        group_rows = 0
        for g in groups:
            gid = repo.find_entity(db, "release_group", mbid=g)["id"]
            editions = group_editions(db, gid)
            group_rows += len(editions)
        labelled = sum(
            1 for e in entries if e["navidrome"].get("release_mbid") and edition_labels(
                parse_release(documents[e["navidrome"]["release_mbid"]], e["navidrome"]["release_mbid"]),
                e["navidrome"]["title"]))
        dup = find_duplicates(db)
        result["grouping"] = {
            "release_groups": len(groups), "owned_editions_listed": group_rows,
            "albums_with_edition_labels": labelled,
            "duplicate_album_groups": len(dup.albums), "duplicate_recordings": len(dup.recordings),
            "owned_editions_match_linked_albums": group_rows == sum(1 for g in linked_group.values() if g),
        }
        db.close()

    # 4. ownership flag
    owned = [{"id": str(e["n"]), "name": e["navidrome"]["title"], "year": e["navidrome"].get("year")}
             for e in entries]
    same_ok = sum(
        edition_match({"name": o["name"], "year": o["year"]}, [o]).status == SAME_EDITION for o in owned)
    other_pairs = []
    for a, b in itertools.permutations(owned, 2):
        m = edition_match({"name": a["name"], "year": a["year"]}, [b])
        if m.status == OTHER_EDITION:
            other_pairs.append((a["id"], b["id"], base_key(a["name"]) == base_key(b["name"])))
    result["ownership"] = {
        "flag_off_by_default": not edition_awareness_enabled({}),
        "flag_on_with_value_1": edition_awareness_enabled({FLAG_ENV: "1"}),
        "own_album_matches_itself": f"{same_ok}/{len(owned)}",
        "pairs_reporting_other_edition": [list(p[:2]) for p in other_pairs],
        "all_such_pairs_share_base_title": all(p[2] for p in other_pairs),
        "different_titles_never_reported": all(
            base_key(a["name"]) == base_key(b["name"]) for a, b in itertools.permutations(owned, 2)
            if edition_match({"name": a["name"], "year": a["year"]}, [b]).status == OTHER_EDITION),
        "owned_flag_untouched": "edition_match returns a status only; no owned field is written",
    }

    link = result["linking"]
    result["pass"] = {
        "accuracy_at_least_90_strict": link["accuracy_strict"] >= 0.9,
        "zero_wrong_silent_merges": not link["wrong_silent_merges"] and not link["linked_to_wrong_group"],
        "sweep_repeat_is_noop": result["linking"]["second_sweep_looked_up"] == 0,
        "ownership_ok": result["ownership"]["flag_off_by_default"] and result["ownership"]["all_such_pairs_share_base_title"]
        and same_ok == len(owned),
    }
    text = json.dumps(result, indent=2, sort_keys=True)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0 if all(result["pass"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
