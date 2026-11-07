"""Server V2 Phase 6 exit verification against the knowledge store and the owner-state file.

Offline. No Navidrome, ListenBrainz, MusicBrainz or other provider traffic. The store and the owner-state
file are copied to a temporary folder first; every write (profile row, test events, test rule sets) goes to
the copy, and the copy is deleted afterwards. Output is aggregate counts and booleans only (no titles,
paths, ids or credentials).

    python scripts/server_v2_phase6_exit.py --store ~/discair-mb-test/intelligence.sqlite3 --out phase6_exit.json

Checks (docs/ServerV2.md, Phase 6 exit and the exit lines of items 5 and 6):
  1. profiles reproducible: listens built from the store's owned recordings give byte-identical profiles,
     monthly snapshot, listening-context profiles and obscurity profile on a repeat run and on shuffled
     input; saving the unchanged profile again writes nothing
  2. honest low-sample states: empty, tiny, below-threshold and unattributed inputs never raise, are
     flagged low-sample and state no shift; an empty month and empty contexts read as zero listens; a
     window with no popularity figures is low-sample
  3. profiles do not alter weights: no module outside the taste package, its routes and the store imports
     the taste package, so no recommendation, radio, lens or discovery code can read a profile, the
     suppression memory or a smart playlist
  4. item 5 (suppression): replaying a batch changes nothing, a malformed event is rejected without
     losing the rest, empty data reads as an empty list
  5. item 6 (smart playlists): replaying a PUT changes nothing, a rule on missing insight data is
     unfinished and reported rather than an error, the table has no refresh column, and no taste module
     can write a playlist to Navidrome
  6. owner-state coverage (reported, not a pass condition): owned artists with a saved popularity figure
"""
from __future__ import annotations

import argparse
import ast
import json
import random
import shutil
import sqlite3
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from intelligence.store import open_store  # noqa: E402
from intelligence.taste import persistence as taste_persistence  # noqa: E402
from intelligence.taste import popularity_persistence as popularity  # noqa: E402
from intelligence.taste import smart_playlist, smart_playlist_persistence as playlists  # noqa: E402
from intelligence.taste import suppression, suppression_persistence as events  # noqa: E402
from intelligence.taste.context import build_context_profiles  # noqa: E402
from intelligence.taste.loader import load_listens  # noqa: E402
from intelligence.taste.monthly import build_monthly_snapshot  # noqa: E402
from intelligence.taste.obscurity import ArtistListen, ObscurityConfig, build_obscurity  # noqa: E402
from intelligence.taste.profiles import DIMENSIONS, Listen, ProfileConfig, build_profiles  # noqa: E402

DAY = 86400.0
NOW = 1_800_000_000.0           # fixed clock: a run never depends on the day it is made
SAMPLE = 600                    # synthetic listens drawn from the store's owned recordings
TAINT = ("createPlaylist", "updatePlaylist", "deletePlaylist")


def _dump(obj) -> str:
    return json.dumps(obj, sort_keys=True, default=lambda o: o.__dict__ if hasattr(o, "__dict__") else str(o))


def _asdict(obj):
    from dataclasses import asdict
    return asdict(obj)


def _raw_listens(db) -> list[dict]:
    """ListenBrainz-shaped listens over owned recordings, spread over about two years, reproducible."""
    rows = [r[0] for r in db.execute(
        "SELECT mbid FROM entities WHERE type = 'recording' AND owned = 1 AND mbid IS NOT NULL ORDER BY mbid")]
    if not rows:
        return []
    out = []
    for i in range(SAMPLE):
        out.append({"listened_at": int(NOW - (i * 1.2) * DAY),
                    "track_metadata": {"additional_info": {"recording_mbid": rows[(i * 7) % len(rows)]}}})
    return out


def _artist_listens(db, count: int) -> list[ArtistListen]:
    mbids = popularity.owned_artist_mbids(db)
    if not mbids:
        return []
    return [ArtistListen(NOW - (i * 1.2) * DAY, mbids[(i * 5) % len(mbids)]) for i in range(count)]


def _suite(db, listens, artist_listens, figures) -> dict:
    pc = ProfileConfig(now=NOW)
    profiles = build_profiles(listens, pc)
    month = build_monthly_snapshot(listens, 2027, 1, "UTC", artist_listens=artist_listens, popularity=figures)
    context = build_context_profiles(listens, "UTC", pc)
    obscurity = build_obscurity(artist_listens, figures, ObscurityConfig(now=NOW))
    return {"profiles": _dump(_asdict(profiles)), "monthly": _dump(_asdict(month)),
            "context": _dump(_asdict(context)), "obscurity": _dump(_asdict(obscurity))}


def check_reproducible(db) -> dict:
    raw = _raw_listens(db)
    if not raw:
        return {"pass": False, "reason": "no owned recordings with an MBID in the store"}
    loaded = load_listens(db, raw)
    artist_listens = _artist_listens(db, SAMPLE)
    figures = popularity.load_popularity(db)
    first = _suite(db, loaded.listens, artist_listens, figures)
    second = _suite(db, loaded.listens, artist_listens, figures)
    shuffled = list(loaded.listens)
    random.Random(7).shuffle(shuffled)
    shuffled_art = list(artist_listens)
    random.Random(8).shuffle(shuffled_art)
    third = _suite(db, shuffled, shuffled_art, figures)
    reloaded = load_listens(db, list(reversed(raw)))
    fourth = _suite(db, reloaded.listens, artist_listens, figures)
    profiles = build_profiles(loaded.listens, ProfileConfig(now=NOW))
    wrote_first = taste_persistence.save_profiles(db, profiles, loaded, now=NOW)
    wrote_again = taste_persistence.save_profiles(db, profiles, loaded, now=NOW + 60)
    same = {k: first[k] == second[k] == third[k] == fourth[k] for k in first}
    return {"raw_listens": loaded.total, "usable": len(loaded.listens), "unmatched": loaded.unmatched,
            "attributed": dict(loaded.attributed), "identical_on_repeat_and_shuffle": same,
            "second_save_wrote_nothing": wrote_first is True and wrote_again is False,
            "pass": all(same.values()) and wrote_again is False}


def check_sparse(db) -> dict:
    pc = ProfileConfig(now=NOW)
    cases: dict[str, bool] = {}

    def lo(listens):
        p = build_profiles(listens, pc)
        return (not p.shifts and all(w.low_sample for w in p.windows.values()))

    cases["empty"] = lo([])
    cases["one_listen"] = lo([Listen(NOW - DAY, {"genre": ("jazz",)})])
    cases["below_threshold"] = lo([Listen(NOW - i * 60, {"genre": ("jazz",)}) for i in range(pc.min_listens - 1)])
    unattributed = build_profiles([Listen(NOW - i * 60) for i in range(200)], pc)
    cases["many_listens_no_metadata"] = (not unattributed.shifts and
                                         all(unattributed.windows["all_time"].dimension_low_sample[d] for d in DIMENSIONS))
    cases["future_listens_ignored"] = build_profiles([Listen(NOW + DAY)], pc).windows["all_time"].listens == 0
    month = build_monthly_snapshot([], 2027, 1, "UTC")
    cases["empty_month"] = month.listens == 0 and month.profile.low_sample
    ctx = build_context_profiles([], "UTC", pc)
    cases["empty_contexts"] = ctx.listens == 0 and all(p.listens == 0 for lens in ctx.lenses.values() for p in lens.values())
    ob = build_obscurity([ArtistListen(NOW - DAY, "a" * 8)], {}, ObscurityConfig(now=NOW))
    cases["no_figures_is_low_sample"] = not ob.shifts and all(w.low_sample for w in ob.windows.values())
    cases["unknown_store_ids_counted_unmatched"] = load_listens(
        db, [{"listened_at": 1, "track_metadata": {"additional_info": {"recording_mbid": str(uuid.uuid4())}}},
             {"listened_at": "x"}]).unmatched == 1
    try:
        build_context_profiles([], "No/Such_Zone", pc)
        cases["bad_timezone_refused"] = False
    except ValueError:
        cases["bad_timezone_refused"] = True
    return {"cases": cases, "pass": all(cases.values())}


def check_no_weight_effect() -> dict:
    allowed = ("intelligence/taste/", "intelligence/api/", "app/api/", "intelligence/store/", "scripts/", "tests/")
    readers: list[str] = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith((".venv", "venv", "node_modules", ".git")) or any(rel.startswith(a) for a in allowed):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            if any(n == "taste" or n.endswith(".taste") or ".taste." in n or n.startswith("intelligence.taste") for n in names):
                readers.append(rel)
                break
    return {"modules_outside_the_allowed_packages_importing_taste": readers, "pass": not readers}


def _ev(name, **kw) -> dict:
    base = {"event_id": str(uuid.uuid5(uuid.NAMESPACE_URL, name)), "client": "macos", "kind": "dismiss",
            "subject_kind": "album", "subject_id": "al-" + name, "occurred_at": NOW - 60}
    base.update(kw)
    return base


def check_suppression(db) -> dict:
    count = lambda: db.execute("SELECT COUNT(*) FROM state.suppression_events").fetchone()[0]  # noqa: E731
    before = count()
    empty = suppression.build_suppression(events.list_active_events(db, NOW + 400 * DAY), NOW + 400 * DAY) == ()
    batch = [_ev("a"), _ev("b"), _ev("bad", kind="explode"), _ev("c")]
    accepted, rejected = suppression.validate_events(batch, NOW)
    first = events.insert_events(db, accepted)
    after_first = count()
    again = events.insert_events(db, accepted)
    after_replay = count()
    result = {"empty_read_is_empty_list": empty,
              "malformed_rejected_rest_kept": len(rejected) == 1 and len(accepted) == 3,
              "first_insert_all_new": [o.status for o in first] == [events.INSERTED] * 3 and after_first == before + 3,
              "replay_changes_nothing": [o.status for o in again] == [events.DUPLICATE] * 3 and after_replay == after_first}
    result["pass"] = all(result.values())
    return result


def check_smart_playlists(db) -> dict:
    raw = {"name": "Exit check", "match": "all", "order": "title", "limit": 50,
           "rules": [{"field": "year", "op": "at_least", "value": "1985"}]}
    rid = str(uuid.uuid5(uuid.NAMESPACE_URL, "phase6-exit"))
    first = playlists.put(db, rid, raw, NOW)
    again = playlists.put(db, rid, raw, NOW + 60)
    rows = db.execute("SELECT COUNT(*) FROM state.smart_playlists WHERE rule_id = ?", (rid,)).fetchone()[0]
    stored = playlists.get(db, rid)
    rule_set, errors = smart_playlist.validate_rule_set(
        {**raw, "rules": [{"field": "obscurity_band", "op": "equals", "value": "obscure"}]})
    songs = [{"id": "s1", "title": "A", "year": 1990}, {"id": "s2", "title": "B", "year": 1970}]
    result_missing = smart_playlist.evaluate(rule_set, songs, now=NOW, insights={}) if rule_set else None
    columns = {r[1] for r in db.execute("PRAGMA state.table_info(smart_playlists)")}
    tainted = [p.name for p in sorted((ROOT / "intelligence" / "taste").glob("*.py"))
               if any(t in p.read_text(encoding="utf-8") for t in TAINT)]
    playlists.delete(db, rid)
    checks = {
        "first_put_created": first.status == playlists.CREATED,
        "replay_unchanged": again.status == playlists.UNCHANGED and rows == 1,
        "created_at_kept_updated_at_kept": stored is not None and stored.created_at == NOW,
        "missing_insight_is_unfinished_not_error": not errors and result_missing is not None
        and len(result_missing.song_ids) == len(songs) and bool(result_missing.missing_data),
        "no_refresh_column": not any("refresh" in c for c in columns),
        "no_navidrome_playlist_write_in_taste_modules": not tainted,
    }
    return {"checks": checks, "pass": all(checks.values())}


def coverage(db) -> dict:
    owned = popularity.owned_artist_mbids(db)
    saved = popularity.load_popularity(db)
    have = sum(1 for m in owned if m in saved)
    return {"owned_artists_with_mbid": len(owned), "with_a_saved_figure": have,
            "with_a_figure_value": sum(1 for m in owned if saved.get(m) is not None)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True, help="the knowledge store (intelligence.sqlite3)")
    parser.add_argument("--out")
    args = parser.parse_args()
    store = Path(args.store).expanduser()

    result: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "intelligence.sqlite3"
        shutil.copyfile(store, copy)
        state = store.with_name("intelligence.state.sqlite3")
        if state.exists():
            shutil.copyfile(state, Path(tmp) / "intelligence.state.sqlite3")
        db = open_store(copy)
        result["store"] = {t: n for t, n in db.execute("SELECT type, COUNT(*) FROM entities GROUP BY type")}
        result["1_reproducible"] = check_reproducible(db)
        result["2_low_sample_states"] = check_sparse(db)
        result["3_no_weight_effect"] = check_no_weight_effect()
        result["4_suppression"] = check_suppression(db)
        result["5_smart_playlists"] = check_smart_playlists(db)
        result["6_coverage_reported"] = coverage(db)
        db.close()
    keys = ("1_reproducible", "2_low_sample_states", "3_no_weight_effect", "4_suppression", "5_smart_playlists")
    result["exit_passed"] = all(result[k]["pass"] is True for k in keys)
    text = json.dumps(result, indent=2, sort_keys=True, default=str)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0 if result["exit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
