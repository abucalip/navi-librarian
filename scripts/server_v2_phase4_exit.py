"""Server V2 Phase 4 exit verification against the knowledge store holding the MusicBrainz slice.

Offline and read-only. No Navidrome, MusicBrainz or other provider traffic. The store is copied
to a temporary folder first (the copy is migrated and read, the original is never opened for
writing) and the copy is deleted afterwards. Output is aggregate counts and store ids only (no
titles, paths or credentials).

    python scripts/server_v2_phase4_exit.py --store ~/discair-mb-test/intelligence.sqlite3 \
        --import-report ~/discair-mb-test/run4.json --out phase4_exit.json

Checks (docs/ServerV2.md, Phase 4 exit):
  1. provenance: every edge names its source, evidence class and match quality, and points at a
     stored observation of the same source; slice edges carry the dump date
  2. ambiguity: homonyms (same name, different MBID) stay separate entities, a name lookup returns
     every one of them (never one picked silently), and no knowledge route resolves a bare name
  3. no unverified credit: no page lists a credit built on an inferred edge or an unmatched end;
     proven on the real slice (walks, with and without credits_only) and on a synthetic store that
     holds inferred and unmatched edges next to real ones
  4. bounded traversal: on the highest-degree entities of the real slice, depth, row, time and page
     limits hold, no entity appears twice, paging by cursor returns exactly the unpaged walk, and a
     synthetic store with cycles, parallel edges and self-loops walks without repeats
  5. kill criterion: the recorded slice import stayed inside every agreed budget
"""
from __future__ import annotations

import argparse
import inspect
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api import knowledge as knowledge_routes  # noqa: E402
from intelligence.graph import Limits, explore  # noqa: E402
from intelligence.graph.traversal import Evidence, is_credit  # noqa: E402
from intelligence.knowledge import KnowledgeReader  # noqa: E402
from intelligence.musicbrainz import job  # noqa: E402
from intelligence.store import open_store  # noqa: E402
from intelligence.store import repositories as repo  # noqa: E402

SLICE = "musicbrainz_dump"
HUBS = 25
SAMPLE = 200


def check_provenance(db) -> dict:
    q = lambda sql, *a: db.execute(sql, a).fetchone()[0]  # noqa: E731
    total = q("SELECT COUNT(*) FROM edges")
    no_source = q("SELECT COUNT(*) FROM edges WHERE source IS NULL OR TRIM(source) = ''")
    no_observation = q("SELECT COUNT(*) FROM edges WHERE observation_id IS NULL")
    dangling = q("SELECT COUNT(*) FROM edges e LEFT JOIN observations o ON o.id = e.observation_id "
                 "WHERE e.observation_id IS NOT NULL AND o.id IS NULL")
    mismatched = q("SELECT COUNT(*) FROM edges e JOIN observations o ON o.id = e.observation_id "
                   "WHERE o.source != e.source")
    dump = db.execute("SELECT value FROM meta WHERE key = 'musicbrainz_slice.dump_timestamp'").fetchone()
    slice_edges = q("SELECT COUNT(*) FROM edges WHERE source = ?", SLICE)
    slice_stamped = q("SELECT COUNT(*) FROM edges e JOIN observations o ON o.id = e.observation_id "
                      "WHERE e.source = ? AND o.payload LIKE '%' || ? || '%'", SLICE, dump["value"] if dump else "\0")
    by_source = {r["source"]: r["n"] for r in db.execute("SELECT source, COUNT(*) n FROM edges GROUP BY source")}
    ok = (total > 0 and not (no_source or no_observation or dangling or mismatched) and dump is not None
          and slice_edges == slice_stamped)
    return {"edges": total, "by_source": by_source, "without_source": no_source,
            "without_observation": no_observation, "dangling_observation": dangling,
            "observation_source_mismatch": mismatched, "slice_dump_timestamp": dump["value"] if dump else None,
            "slice_edges": slice_edges, "slice_edges_carrying_dump_date": slice_stamped, "pass": ok}


def check_ambiguity(db) -> dict:
    reader = KnowledgeReader(db)
    groups = db.execute(
        "SELECT type, canonical_name, COUNT(*) n FROM entities WHERE type IN ('artist','label','work') "
        "GROUP BY type, canonical_name HAVING COUNT(*) > 1 ORDER BY n DESC, canonical_name LIMIT ?", (SAMPLE,)).fetchall()
    total_groups = db.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM entities WHERE type IN ('artist','label','work') "
        "GROUP BY type, canonical_name HAVING COUNT(*) > 1)").fetchone()[0]
    silent, missing, same_mbid = [], [], []
    for g in groups:
        ids = {r["id"] for r in db.execute("SELECT id FROM entities WHERE type = ? AND canonical_name = ?",
                                           (g["type"], g["canonical_name"]))}
        found = {e["id"] for e in reader.find_by_name(g["type"], g["canonical_name"])}
        if len(found) < 2:
            silent.append(sorted(ids)[0])
        elif not ids <= found:
            missing.append(sorted(ids)[0])
        mbids = [r["mbid"] for r in db.execute("SELECT mbid FROM entities WHERE type = ? AND canonical_name = ?",
                                               (g["type"], g["canonical_name"]))]
        if len(set(mbids)) != len(mbids) or None in mbids:
            same_mbid.append(sorted(ids)[0])
    # Routes: none may take a name; identity is an MBID or a Navidrome id.
    name_params = []
    for route in knowledge_routes.router.routes:
        params = set(inspect.signature(route.endpoint).parameters)
        if params & {"name", "title", "q", "query", "artist", "album"}:
            name_params.append(route.path)
    ok = not (silent or missing or same_mbid or name_params) and total_groups > 0
    return {"homonym_groups_in_slice": total_groups, "groups_sampled": len(groups),
            "lookup_returned_one_candidate": silent, "lookup_missing_a_candidate": missing,
            "homonyms_sharing_or_lacking_mbid": same_mbid, "routes_resolving_a_bare_name": name_params, "pass": ok}


def _uncertain(db, edge_id: int) -> bool:
    r = db.execute("SELECT evidence_class, match_quality FROM edges WHERE id = ?", (edge_id,)).fetchone()
    return r["evidence_class"] == "inferred" or r["match_quality"] in ("fuzzy_unconfirmed", "unresolved")


def check_credits_real(db, hubs) -> dict:
    """On the real slice: classify every edge, and walk the hubs with credits_only on."""
    classes = {f"{r['evidence_class']}/{r['match_quality']}": r["n"] for r in db.execute(
        "SELECT evidence_class, match_quality, COUNT(*) n FROM edges GROUP BY 1, 2")}
    uncertain_edges = sum(n for key, n in classes.items()
                          if key.startswith("inferred/") or key.split("/")[1] in ("fuzzy_unconfirmed", "unresolved"))
    leaks = 0
    credit_hops = 0
    for hub in hubs:
        page = explore(db, hub, credits_only=True, limits=Limits(max_depth=2, max_rows=200, page_size=200))
        for hop in page.hops:
            credit_hops += 1
            leaks += sum(1 for e in hop.evidence if _uncertain(db, e.edge_id))
    return {"edge_classes": classes, "uncertain_edges_in_slice": uncertain_edges, "hubs_walked": len(hubs),
            "credit_hops_checked": credit_hops, "uncertain_edges_shown_as_credit": leaks, "pass": leaks == 0}


def check_credits_synthetic() -> dict:
    """Inferred and unmatched edges beside real ones, through the explorer and all three pages."""
    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "c.sqlite3")
        mk = lambda t, n, **kw: repo.upsert_entity(db, t, n, **kw)[0]  # noqa: E731
        album_mbid = "a0000000-0000-0000-0000-000000000001"
        album = mk("release_group", "Album", mbid=album_mbid, owned=True)
        real, guessed, unmatched = (mk("artist", n, mbid=f"c0000000-0000-0000-0000-00000000000{i}")
                                    for i, n in enumerate(("Real", "Guessed", "Unmatched"), 1))
        repo.add_edge(db, real, album, "producer", source=SLICE, evidence_class="source_explicit", match_quality="exact_mbid")
        repo.add_edge(db, guessed, album, "producer", source="guess", evidence_class="inferred", match_quality="exact_mbid")
        repo.add_edge(db, unmatched, album, "producer", source=SLICE, evidence_class="source_explicit", match_quality="unresolved")
        db.commit()
        reader = KnowledgeReader(db)
        walk = explore(db, album, credits_only=True)
        walked = {h.entity_id for h in walk.hops}
        everything = {h.entity_id for h in explore(db, album).hops}
        dossier = reader.album_dossier(id=album)
        mbid_of = {who: repo.get_entity(db, who)["mbid"] for who in (real, guessed, unmatched)}
        in_dossier = {row["entity"]["mbid"] for row in dossier["people"]}
        credited = {who: mbid_of[who] in in_dossier for who in (real, guessed, unmatched)}
        listed = {who: album_mbid in json.dumps(reader.person_page(id=who), default=str) for who in (real, guessed, unmatched)}
        ok = (everything == {real, guessed, unmatched} and walked == {real}
              and credited == {real: True, guessed: False, unmatched: False}
              and listed == {real: True, guessed: False, unmatched: False})
        db.close()
    return {"plain_walk_reaches_all_three": everything == {real, guessed, unmatched},
            "credit_walk_keeps_only_the_real_one": walked == {real},
            "dossier_shows_real": credited[real], "dossier_shows_inferred": credited[guessed],
            "dossier_shows_unmatched": credited[unmatched], "person_page_lists_real": listed[real],
            "person_page_lists_inferred": listed[guessed], "person_page_lists_unmatched": listed[unmatched], "pass": ok}


def check_traversal_real(db) -> dict:
    degrees = db.execute(
        "SELECT id FROM entities ORDER BY (SELECT COUNT(*) FROM edges WHERE from_id = entities.id OR to_id = entities.id) DESC, id LIMIT ?",
        (HUBS,)).fetchall()
    hubs = [r["id"] for r in degrees]
    limits = Limits(max_depth=2, max_rows=300, max_seconds=5.0, page_size=40)
    problems: list[str] = []
    slowest = 0.0
    rows_seen = 0
    truncated = 0
    for hub in hubs:
        started = time.monotonic()
        paged, cursor, pages = [], None, 0
        while True:
            page = explore(db, hub, limits=limits, cursor=cursor)
            paged.extend(page.hops)
            pages += 1
            cursor = page.next_cursor
            if cursor is None or pages > 100:
                break
        full = explore(db, hub, limits=Limits(max_depth=2, max_rows=300, max_seconds=5.0, page_size=300))
        slowest = max(slowest, time.monotonic() - started)
        ids = [h.entity_id for h in paged]
        rows_seen += len(ids)
        truncated += 1 if full.truncated else 0
        if len(ids) != len(set(ids)):
            problems.append(f"{hub}:duplicate")
        if hub in ids:
            problems.append(f"{hub}:start_returned")
        if len(ids) > limits.max_rows:
            problems.append(f"{hub}:over_row_cap")
        if any(h.depth > limits.max_depth for h in paged):
            problems.append(f"{hub}:over_depth")
        if ids != [h.entity_id for h in full.hops]:
            problems.append(f"{hub}:paging_differs_from_unpaged")
        if any(not h.evidence for h in paged):
            problems.append(f"{hub}:hop_without_evidence")
    # A zero-second budget must stop the walk early and say so, not hang or raise.
    timed = explore(db, hubs[0], limits=Limits(max_depth=2, max_rows=300, max_seconds=1e-9), clock=iter(range(10**6)).__next__)
    time_bound = timed.truncated == "time"
    return {"hubs_walked": len(hubs), "limits": {"depth": 2, "rows": 300, "seconds": 5.0, "page": 40},
            "rows_returned": rows_seen, "walks_truncated_by_row_cap": truncated,
            "slowest_hub_seconds": round(slowest, 3), "time_limit_stops_walk": time_bound,
            "problems": problems, "pass": not problems and time_bound}


def check_traversal_synthetic() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        db = open_store(Path(tmp) / "t.sqlite3")
        ids = [repo.upsert_entity(db, "artist", f"A{i}", mbid=f"d0000000-0000-0000-0000-{i:012d}")[0] for i in range(6)]
        edge = lambda a, b, rel="performance", role=None, src=SLICE: repo.add_edge(  # noqa: E731
            db, ids[a], ids[b], rel, role=role, source=src, evidence_class="source_explicit", match_quality="exact_mbid")
        for a, b in ((0, 1), (1, 2), (2, 0), (2, 3), (3, 4), (4, 2), (4, 5)):  # two cycles
            edge(a, b)
        edge(0, 1, role="piano")          # parallel edge, other role
        edge(0, 1, src="navidrome")       # parallel edge, other source
        edge(1, 0, "collaboration")       # reverse edge
        edge(3, 3)                        # self-loop
        db.commit()
        walk = explore(db, ids[0], limits=Limits(max_depth=6, max_rows=100, page_size=2))
        paged, cursor = [], None
        while True:
            page = explore(db, ids[0], limits=Limits(max_depth=6, max_rows=100, page_size=2), cursor=cursor)
            paged.extend(page.hops)
            cursor = page.next_cursor
            if not cursor:
                break
        got = [h.entity_id for h in paged]
        depth = {h.entity_id: h.depth for h in paged}
        capped = explore(db, ids[0], limits=Limits(max_depth=6, max_rows=2, page_size=10))
        shallow = explore(db, ids[0], limits=Limits(max_depth=1, max_rows=100, page_size=10))
        parallel = next(h for h in paged if h.entity_id == ids[1])
        ok = (sorted(got) == sorted(ids[1:]) and len(got) == len(set(got))
              and depth == {ids[1]: 1, ids[2]: 1, ids[3]: 2, ids[4]: 2, ids[5]: 3}
              and capped.truncated == "rows" and len(capped.hops) == 2
              and sorted(h.entity_id for h in shallow.hops) == sorted([ids[1], ids[2]])
              and len(parallel.evidence) == 4 and ids[0] not in got)
        db.close()
    return {"entities_reached": len(got), "duplicates": len(got) - len(set(got)), "depths": sorted(depth.values()),
            "parallel_edges_kept_on_one_hop": len(parallel.evidence), "row_cap_reports_truncation": capped.truncated == "rows",
            "pass": ok}


def check_budgets(report_path: Path | None) -> dict:
    if report_path is None:
        return {"pass": None, "note": "no import report given; budgets not checked"}
    progress = json.loads(report_path.read_text())["progress"]
    budgets = job.Budgets()
    measured = {
        "download_bytes": progress.get("archive_bytes"), "scratch_bytes": progress.get("scratch_bytes"),
        "slice_bytes": progress.get("slice_bytes"), "import_seconds": progress.get("import_seconds"),
        "max_entities": sum(progress.get("load", {}).get("by_type", {}).values()),
    }
    breaches = [k for k, v in measured.items() if v is None or v > getattr(budgets, k)]
    return {"outcome": progress.get("outcome"), "measured": measured,
            "budgets": {k: getattr(budgets, k) for k in measured}, "breaches": breaches,
            "pass": progress.get("outcome") == "loaded" and not breaches}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", required=True, help="the knowledge store (intelligence.sqlite3) holding the slice")
    parser.add_argument("--import-report", help="JSON report of the slice import (run4.json)")
    parser.add_argument("--out")
    args = parser.parse_args()
    store = Path(args.store).expanduser()
    report = Path(args.import_report).expanduser() if args.import_report else None

    result: dict = {}
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "intelligence.sqlite3"
        shutil.copyfile(store, copy)
        state = store.with_name("intelligence.state.sqlite3")
        if state.exists():
            shutil.copyfile(state, Path(tmp) / "intelligence.state.sqlite3")
        db = open_store(copy)
        hubs = [r["id"] for r in db.execute(
            "SELECT id FROM entities ORDER BY (SELECT COUNT(*) FROM edges WHERE from_id = entities.id OR to_id = entities.id) DESC, id LIMIT ?",
            (HUBS,))]
        result["store"] = {t: n for t, n in db.execute("SELECT type, COUNT(*) FROM entities GROUP BY type")}
        result["1_provenance"] = check_provenance(db)
        result["2_ambiguity"] = check_ambiguity(db)
        result["3_no_unverified_credit"] = {"real_slice": check_credits_real(db, hubs),
                                            "synthetic": check_credits_synthetic()}
        result["4_bounded_traversal"] = {"real_slice": check_traversal_real(db),
                                         "synthetic": check_traversal_synthetic()}
        db.close()
    result["5_budgets"] = check_budgets(report)
    verdicts = [result["1_provenance"]["pass"], result["2_ambiguity"]["pass"],
                result["3_no_unverified_credit"]["real_slice"]["pass"], result["3_no_unverified_credit"]["synthetic"]["pass"],
                result["4_bounded_traversal"]["real_slice"]["pass"], result["4_bounded_traversal"]["synthetic"]["pass"],
                result["5_budgets"]["pass"]]
    result["exit_passed"] = all(v is True for v in verdicts)
    text = json.dumps(result, indent=2, sort_keys=True, default=str)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n")
    return 0 if result["exit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
