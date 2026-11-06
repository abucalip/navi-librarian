"""Phase 5 path coverage: for each discovery path kind, how many owned artists have usable evidence.

Read-only measurement over the knowledge store; no provider traffic and nothing is written to the
store (scratch tables are TEMP). It answers the Phase 5 kill rule with numbers before any path
builder exists (docs/ServerV2.md, Phase 5: "if a path kind needs more than a day of precompute or
yields mostly empty results, drop that kind").

A path starts at an owned artist (the anchor). A *stop* is an entity the store can reach from the
anchor by the kind's rule, using credit-grade edges only (never ``inferred``, never an unmatched
end). The rules match the Phase 5 path kinds:

``follow_the_musician``     recordings credited to a musician who is also credited on an owned recording
                            of the anchor, other than the anchor's own recordings
``sideman_to_leader``       artists who lead a release carrying a recording the anchor is credited on
``label_path``              other releases on a label (or related label) of the anchor's owned releases
``composition_path``        other recordings of a work (or related work) the anchor's recordings perform
``scene_path``              other artists with the same stated, non-country area and a start within ten
                            years of the anchor's (nationality is never inferred)
``same_studio_different_decade``  other recordings made at a studio that also made an owned recording,
                            where both release decades are known and differ

A kind is measurable only when the store holds its inputs; otherwise the verdict is
``not_measurable`` (a slice re-import is needed), never a silent ``drop``.
"""
from __future__ import annotations

import sqlite3
import statistics
import time
from dataclasses import dataclass

MIN_STOPS = 3            # a path is worth showing from 3 stops (a short list)
NONEMPTY_MIN = 0.5       # "mostly empty": fewer than half of the anchors reach even one stop
USABLE_MIN = 0.25        # fewer than a quarter of the anchors reach MIN_STOPS
DAY_SECONDS = 86_400.0
SCENE_YEARS = 10

KINDS = ("follow_the_musician", "sideman_to_leader", "label_path", "composition_path", "scene_path",
         "same_studio_different_decade")

_CREDIT_GRADE = "evidence_class != 'inferred' AND match_quality NOT IN ('fuzzy_unconfirmed', 'unresolved')"


@dataclass(frozen=True)
class Criteria:
    min_stops: int = MIN_STOPS
    nonempty_min: float = NONEMPTY_MIN
    usable_min: float = USABLE_MIN
    assumed_anchors: int = 10_000   # owned artists to extrapolate the precompute time to
    max_seconds: float = DAY_SECONDS


def _prepare(db: sqlite3.Connection) -> None:
    for name in ("cov_edge", "cov_anchor", "cov_a_rel", "cov_a_rec", "cov_stop", "cov_in", "cov_rl", "cov_rec_decade"):
        db.execute(f"DROP TABLE IF EXISTS temp.{name}")
    db.execute(f"CREATE TEMP TABLE cov_edge AS SELECT id, from_id, to_id, relation FROM edges WHERE {_CREDIT_GRADE}")
    db.execute("CREATE INDEX temp.cov_edge_from ON cov_edge (from_id, relation)")
    db.execute("CREATE INDEX temp.cov_edge_to ON cov_edge (to_id, relation)")
    db.execute("CREATE TEMP TABLE cov_anchor AS SELECT id FROM entities WHERE type = 'artist' AND owned = 1")
    db.execute("CREATE UNIQUE INDEX temp.cov_anchor_id ON cov_anchor (id)")
    # Owned releases credited to the anchor, and the owned recordings that appear on them.
    db.execute("CREATE TEMP TABLE cov_a_rel AS SELECT DISTINCT e.to_id AS a, e.from_id AS rel FROM cov_edge e "
               "JOIN cov_anchor an ON an.id = e.to_id JOIN entities r ON r.id = e.from_id AND r.type = 'release' "
               "WHERE e.relation = 'credited_to'")
    db.execute("CREATE INDEX temp.cov_a_rel_a ON cov_a_rel (a, rel)")
    db.execute("CREATE TEMP TABLE cov_a_rec AS SELECT DISTINCT ar.a AS a, e.from_id AS rec FROM cov_a_rel ar "
               "JOIN cov_edge e ON e.to_id = ar.rel AND e.relation = 'appears_on'")
    db.execute("CREATE UNIQUE INDEX temp.cov_a_rec_ar ON cov_a_rec (a, rec)")
    db.execute("CREATE INDEX temp.cov_a_rec_r ON cov_a_rec (rec)")
    db.execute("CREATE TEMP TABLE cov_stop (a INTEGER NOT NULL, stop INTEGER NOT NULL, ok INTEGER)")
    db.execute("CREATE TEMP TABLE cov_in (a INTEGER NOT NULL, x INTEGER NOT NULL)")  # anchors that have the kind's input
    db.execute("CREATE INDEX temp.cov_in_a ON cov_in (a)")
    db.execute("CREATE TEMP TABLE cov_rl AS SELECT label_id, release_id FROM release_labels WHERE label_id IS NOT NULL")
    db.execute("CREATE INDEX temp.cov_rl_label ON cov_rl (label_id)")
    # Release decade of a recording (earliest dated release it appears on).
    db.execute("CREATE TEMP TABLE cov_rec_decade AS SELECT e.from_id AS rec, MIN(SUBSTR(f.date, 1, 3)) AS decade "
               "FROM cov_edge e JOIN release_facts f ON f.entity_id = e.to_id "
               "WHERE e.relation = 'appears_on' AND f.date IS NOT NULL AND LENGTH(f.date) >= 4 GROUP BY e.from_id")
    db.execute("CREATE UNIQUE INDEX temp.cov_rec_decade_r ON cov_rec_decade (rec)")


def _not_own(table_alias: str, col: str) -> str:
    return f"NOT EXISTS (SELECT 1 FROM cov_a_rec x WHERE x.a = {table_alias}.a AND x.rec = {col})"


def _follow(db: sqlite3.Connection) -> None:
    db.execute("INSERT INTO cov_in SELECT a, rec FROM cov_a_rec")
    db.execute(
        "INSERT INTO cov_stop SELECT DISTINCT r.a, e2.to_id, 1 FROM cov_a_rec r "
        "JOIN cov_edge e1 ON e1.to_id = r.rec "
        "JOIN entities p ON p.id = e1.from_id AND p.type = 'artist' AND p.id != r.a "
        "JOIN cov_edge e2 ON e2.from_id = p.id "
        "JOIN entities q ON q.id = e2.to_id AND q.type = 'recording' "
        f"WHERE {_not_own('r', 'q.id')}")


def _sideman(db: sqlite3.Connection) -> None:
    db.execute("INSERT INTO cov_in SELECT DISTINCT an.id, e1.to_id FROM cov_anchor an "
               "JOIN cov_edge e1 ON e1.from_id = an.id JOIN entities q ON q.id = e1.to_id AND q.type = 'recording'")
    db.execute(
        "INSERT INTO cov_stop SELECT DISTINCT an.id, e3.to_id, 1 FROM cov_anchor an "
        "JOIN cov_edge e1 ON e1.from_id = an.id "
        "JOIN entities q ON q.id = e1.to_id AND q.type = 'recording' "
        "JOIN cov_edge e2 ON e2.from_id = q.id AND e2.relation = 'appears_on' "
        "JOIN cov_edge e3 ON e3.from_id = e2.to_id AND e3.relation = 'credited_to' AND e3.to_id != an.id")


def _label(db: sqlite3.Connection) -> None:
    db.execute("CREATE TEMP TABLE cov_a_label AS SELECT DISTINCT ar.a AS a, rl.label_id AS l FROM cov_a_rel ar "
               "JOIN cov_rl rl ON rl.release_id = ar.rel")
    db.execute("INSERT INTO cov_a_label SELECT al.a, e.to_id FROM cov_a_label al JOIN cov_edge e ON e.from_id = al.l "
               "JOIN entities le ON le.id = e.to_id AND le.type = 'label'")
    db.execute("INSERT INTO cov_a_label SELECT al.a, e.from_id FROM cov_a_label al JOIN cov_edge e ON e.to_id = al.l "
               "JOIN entities le ON le.id = e.from_id AND le.type = 'label'")
    db.execute("INSERT INTO cov_in SELECT DISTINCT a, l FROM cov_a_label")
    db.execute(
        "INSERT INTO cov_stop SELECT DISTINCT al.a, rl.release_id, 1 FROM cov_a_label al "
        "JOIN cov_rl rl ON rl.label_id = al.l "
        "WHERE NOT EXISTS (SELECT 1 FROM cov_a_rel x WHERE x.a = al.a AND x.rel = rl.release_id)")
    db.execute("DROP TABLE temp.cov_a_label")


def _composition(db: sqlite3.Connection) -> None:
    db.execute("CREATE TEMP TABLE cov_a_work AS SELECT DISTINCT r.a AS a, e.to_id AS w FROM cov_a_rec r "
               "JOIN cov_edge e ON e.from_id = r.rec AND e.relation = 'performance' "
               "JOIN entities w ON w.id = e.to_id AND w.type = 'work'")
    db.execute("INSERT INTO cov_in SELECT a, w FROM cov_a_work")
    db.execute("CREATE TEMP TABLE cov_a_work2 AS SELECT a, w FROM cov_a_work")
    db.execute("INSERT INTO cov_a_work2 SELECT aw.a, e.to_id FROM cov_a_work aw JOIN cov_edge e ON e.from_id = aw.w "
               "JOIN entities w ON w.id = e.to_id AND w.type = 'work'")
    db.execute("INSERT INTO cov_a_work2 SELECT aw.a, e.from_id FROM cov_a_work aw JOIN cov_edge e ON e.to_id = aw.w "
               "JOIN entities w ON w.id = e.from_id AND w.type = 'work'")
    db.execute("CREATE INDEX temp.cov_a_work2_w ON cov_a_work2 (w)")
    db.execute(
        "INSERT INTO cov_stop SELECT DISTINCT aw.a, e.from_id, 1 FROM cov_a_work2 aw "
        "JOIN cov_edge e ON e.to_id = aw.w AND e.relation = 'performance' "
        f"WHERE {_not_own('aw', 'e.from_id')}")
    db.execute("DROP TABLE temp.cov_a_work")
    db.execute("DROP TABLE temp.cov_a_work2")


def _scene(db: sqlite3.Connection) -> None:
    db.execute("CREATE TEMP TABLE cov_a_area AS SELECT DISTINCT an.id AS a, e.to_id AS area FROM cov_anchor an "
               "JOIN cov_edge e ON e.from_id = an.id AND e.relation IN ('area', 'begin area') "
               "JOIN entities ar ON ar.id = e.to_id AND ar.type = 'area' "
               "LEFT JOIN area_facts f ON f.entity_id = ar.id WHERE LOWER(COALESCE(f.kind, '')) != 'country'")
    db.execute("INSERT INTO cov_in SELECT a, area FROM cov_a_area")
    db.execute(
        "INSERT INTO cov_stop SELECT DISTINCT aa.a, e.from_id, 1 FROM cov_a_area aa "
        "JOIN cov_edge e ON e.to_id = aa.area AND e.relation IN ('area', 'begin area') "
        "JOIN entities b ON b.id = e.from_id AND b.type = 'artist' AND b.id != aa.a "
        "JOIN artist_life_span la ON la.entity_id = aa.a JOIN artist_life_span lb ON lb.entity_id = b.id "
        "WHERE la.begin_date IS NOT NULL AND lb.begin_date IS NOT NULL "
        f"AND ABS(CAST(SUBSTR(la.begin_date, 1, 4) AS INTEGER) - CAST(SUBSTR(lb.begin_date, 1, 4) AS INTEGER)) <= {SCENE_YEARS}")
    db.execute("DROP TABLE temp.cov_a_area")


def _studio(db: sqlite3.Connection) -> None:
    db.execute("CREATE TEMP TABLE cov_a_place AS SELECT DISTINCT r.a AS a, p.id AS place, r.rec AS rec FROM cov_a_rec r "
               "JOIN cov_edge e ON e.to_id = r.rec AND e.relation IN ('recorded at', 'mixed at', 'engineered at') "
               "JOIN entities p ON p.id = e.from_id AND p.type = 'place' "
               "JOIN place_facts f ON f.entity_id = p.id AND LOWER(f.kind) = 'studio'")
    db.execute("INSERT INTO cov_in SELECT a, place FROM cov_a_place")
    db.execute(
        "INSERT INTO cov_stop SELECT ap.a, q.id, CASE WHEN dq.decade IS NULL OR da.decade IS NULL THEN NULL "
        "WHEN dq.decade != da.decade THEN 1 ELSE 0 END FROM cov_a_place ap "
        "JOIN cov_edge e ON e.from_id = ap.place AND e.relation IN ('recorded at', 'mixed at', 'engineered at') "
        "JOIN entities q ON q.id = e.to_id AND q.type = 'recording' "
        "LEFT JOIN cov_rec_decade da ON da.rec = ap.rec LEFT JOIN cov_rec_decade dq ON dq.rec = q.id "
        f"WHERE {_not_own('ap', 'q.id')}")
    db.execute("DROP TABLE temp.cov_a_place")


_BUILDERS = {"follow_the_musician": _follow, "sideman_to_leader": _sideman, "label_path": _label,
             "composition_path": _composition, "scene_path": _scene, "same_studio_different_decade": _studio}


def _percentile(sorted_values: list[int], q: float) -> int:
    if not sorted_values:
        return 0
    return sorted_values[min(len(sorted_values) - 1, int(q * len(sorted_values)))]


def _verdict(row: dict, c: Criteria) -> str:
    if row["anchors_with_input"] == 0:
        return "not_measurable"
    if row["projected_precompute_seconds"] > c.max_seconds:
        return "drop_precompute_too_slow"
    if row["share_with_a_stop"] < c.nonempty_min or row["share_usable"] < c.usable_min:
        return "drop_mostly_empty"
    return "keep"


def measure_kind(db: sqlite3.Connection, kind: str, criteria: Criteria = Criteria()) -> dict:
    """Measure one path kind. ``_prepare`` must have run on this connection."""
    db.execute("DELETE FROM cov_stop")
    db.execute("DELETE FROM cov_in")
    started = time.monotonic()
    _BUILDERS[kind](db)
    rows = db.execute(
        "SELECT an.id AS a, COUNT(DISTINCT s.stop) AS candidates, "
        "COUNT(DISTINCT CASE WHEN s.ok = 1 THEN s.stop END) AS stops "
        "FROM cov_anchor an LEFT JOIN cov_stop s ON s.a = an.id GROUP BY an.id").fetchall()
    seconds = time.monotonic() - started
    with_input = db.execute("SELECT COUNT(DISTINCT a) FROM cov_in").fetchone()[0]
    anchors = len(rows)
    stops = sorted(r["stops"] for r in rows)
    candidates = sorted(r["candidates"] for r in rows)
    with_stop = sum(1 for n in stops if n >= 1)
    usable = sum(1 for n in stops if n >= criteria.min_stops)
    per_anchor = seconds / anchors if anchors else 0.0
    out = {
        "anchors": anchors,
        "anchors_with_input": with_input,
        "anchors_with_a_stop": with_stop,
        "anchors_usable": usable,
        "share_with_a_stop": round(with_stop / anchors, 4) if anchors else 0.0,
        "share_usable": round(usable / anchors, 4) if anchors else 0.0,
        "stops_median": int(statistics.median(stops)) if stops else 0,
        "stops_p90": _percentile(stops, 0.9),
        "stops_max": stops[-1] if stops else 0,
        "candidates_without_a_confirmed_stop": sum(candidates) - sum(stops),
        "seconds": round(seconds, 3),
        "projected_precompute_seconds": round(per_anchor * criteria.assumed_anchors, 1),
    }
    out["verdict"] = _verdict(out, criteria)
    return out


def input_coverage(db: sqlite3.Connection) -> dict:
    """What the store holds that Phase 5 reads, for the owned artists."""
    q = lambda sql: db.execute(sql).fetchone()[0]  # noqa: E731
    owned = q("SELECT COUNT(*) FROM entities WHERE type = 'artist' AND owned = 1")
    edge_artists = lambda rels: q(  # noqa: E731
        "SELECT COUNT(DISTINCT e.from_id) FROM edges e JOIN entities a ON a.id = e.from_id AND a.type = 'artist' AND a.owned = 1 "
        f"WHERE e.relation IN ({rels})")
    return {
        "owned_artists": owned,
        "owned_with_wikidata_id": q("SELECT COUNT(*) FROM entities WHERE type = 'artist' AND owned = 1 AND wikidata_id IS NOT NULL"),
        "owned_with_area": edge_artists("'area'"),
        "owned_with_begin_area": edge_artists("'begin area'"),
        "owned_with_life_span_start": q("SELECT COUNT(*) FROM artist_life_span l JOIN entities a ON a.id = l.entity_id "
                                        "WHERE a.owned = 1 AND l.begin_date IS NOT NULL"),
        "slice_areas": q("SELECT COUNT(*) FROM entities WHERE type = 'area'"),
        "slice_places": q("SELECT COUNT(*) FROM entities WHERE type = 'place'"),
        "slice_studios": q("SELECT COUNT(*) FROM place_facts WHERE LOWER(kind) = 'studio'"),
        "slice_events": q("SELECT COUNT(*) FROM entities WHERE type = 'event'"),
        "slice_release_labels": q("SELECT COUNT(*) FROM release_labels"),
        "releases_with_a_date": q("SELECT COUNT(*) FROM release_facts WHERE date IS NOT NULL"),
        "schema_version": q("PRAGMA user_version"),
    }


def measure(db: sqlite3.Connection, criteria: Criteria = Criteria(), kinds: tuple[str, ...] = KINDS) -> dict:
    """The coverage report: inputs, one block per kind, and the kinds to keep or drop."""
    _prepare(db)
    try:
        report = {"criteria": {"min_stops": criteria.min_stops, "nonempty_min": criteria.nonempty_min,
                               "usable_min": criteria.usable_min, "assumed_anchors": criteria.assumed_anchors,
                               "max_precompute_seconds": criteria.max_seconds},
                  "inputs": input_coverage(db),
                  "kinds": {k: measure_kind(db, k, criteria) for k in kinds}}
    finally:
        for name in ("cov_edge", "cov_anchor", "cov_a_rel", "cov_a_rec", "cov_stop", "cov_in", "cov_rl", "cov_rec_decade"):
            db.execute(f"DROP TABLE IF EXISTS temp.{name}")
    verdicts = {k: v["verdict"] for k, v in report["kinds"].items()}
    report["keep"] = sorted(k for k, v in verdicts.items() if v == "keep")
    report["drop"] = sorted(k for k, v in verdicts.items() if v.startswith("drop"))
    report["not_measurable"] = sorted(k for k, v in verdicts.items() if v == "not_measurable")
    return report
