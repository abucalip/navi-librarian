"""Album paths probe: how many owned albums have evidence-backed stops for each kept album path kind.

Offline, read-only measurement (docs/ALBUM_PATHS_PROPOSAL.md, "Probe plan"). The store is opened with
SQLite's read-only mode; nothing is written and there is no provider traffic. Output is aggregate counts
only, written to --out (keep it outside the repo until a decision is recorded).

    python scripts/album_path_coverage.py --store ~/discair-mb-test/intelligence.sqlite3 --out probe.json

Only credit-grade edges are used: never ``inferred``, never an end that is ``fuzzy_unconfirmed`` or
``unresolved``. Stops are owned releases other than the album itself. Each album build is capped at
``STOP_CAP`` stops and timed against ``BUILD_BOUND_SECONDS``.

Kinds measured here: ``album_crew``, ``album_guests``, ``album_works``, ``album_room``, ``album_moment``.
``album_sonic_neighbours`` needs the live Sonic routes and is not measured by this script.

The overlap figure for artist paths is a PROXY: a stop counts as already reached by the artist's five
kinds when it shares a credited artist with the album or a label with it. The exact overlap needs the
artist-path builders and is a Sonnet step (proposal work-split table).
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
import time
from pathlib import Path

STOP_CAP = 200
BUILD_BOUND_SECONDS = 2.0
PERSON_FAN_CAP = 50
MOMENT_YEARS = 2

CREDIT_GRADE = "evidence_class != 'inferred' AND match_quality NOT IN ('fuzzy_unconfirmed', 'unresolved')"
CREW = ("producer", "engineer", "mix", "mastering")
GUEST = ("instrument", "vocal", "performer")
WORK_REL = ("parts", "other version", "arrangement", "based on")
PLACE_REL = ("recorded at", "mixed at", "engineered at")

KINDS = ("album_crew", "album_guests", "album_works", "album_room", "album_moment")


def _connect(store: Path) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{store}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


class Probe:
    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.owned = {r["id"] for r in db.execute("SELECT id FROM entities WHERE type='release' AND owned=1")}
        self.edges_out: dict[tuple[int, str], set[int]] = {}
        self.edges_in: dict[tuple[int, str], set[int]] = {}
        for r in db.execute(f"SELECT from_id, to_id, relation FROM edges WHERE {CREDIT_GRADE}"):
            self.edges_out.setdefault((r["from_id"], r["relation"]), set()).add(r["to_id"])
            self.edges_in.setdefault((r["to_id"], r["relation"]), set()).add(r["from_id"])
        self.appears = {}  # release -> recordings
        for (rec, rel), rels in self.edges_out.items():
            if rel == "appears_on":
                for rl in rels:
                    self.appears.setdefault(rl, set()).add(rec)
        self.rec_releases = {}  # recording -> releases
        for rl, recs in self.appears.items():
            for rec in recs:
                self.rec_releases.setdefault(rec, set()).add(rl)
        self.labels = {}  # release -> labels
        for r in db.execute("SELECT release_id, label_id FROM release_labels WHERE label_id IS NOT NULL"):
            self.labels.setdefault(r["release_id"], set()).add(r["label_id"])
        self.label_releases = {}
        for rl, ls in self.labels.items():
            for lab in ls:
                self.label_releases.setdefault(lab, set()).add(rl)
        self.year = {}
        for r in db.execute("SELECT entity_id, MIN(date) AS d FROM release_facts WHERE date IS NOT NULL "
                            "AND LENGTH(date) >= 4 GROUP BY entity_id"):
            self.year[r["entity_id"]] = int(r["d"][:4])
        self.non_country_area = {r["entity_id"] for r in db.execute(
            "SELECT entity_id FROM area_facts WHERE LOWER(COALESCE(kind,'')) != 'country'")}
        self.artist_area = {}
        for (src, rel), tos in self.edges_out.items():
            if rel in ("area", "begin area"):
                self.artist_area.setdefault(src, set()).update(t for t in tos if t in self.non_country_area)

    def out(self, src: int, rel: str) -> set[int]:
        return self.edges_out.get((src, rel), set())

    def into(self, dst: int, rel: str) -> set[int]:
        return self.edges_in.get((dst, rel), set())

    def own_artists(self, rl: int) -> set[int]:
        return self.out(rl, "credited_to")

    def credits_on_album(self, rl: int) -> set[int]:
        return self.own_artists(rl)

    # --- kinds: each returns {stop_release: [reason codes]} for album rl ---
    def crew(self, rl: int) -> dict[int, set[str]]:
        people: set[int] = set()
        for rel in CREW:
            people |= self.into(rl, rel)
            for rec in self.appears.get(rl, ()):
                people |= self.into(rec, rel)
        stops: dict[int, set[str]] = {}
        for p in people:
            hits: set[int] = set()
            for rel in CREW:
                for target in self.out(p, rel):
                    if target in self.owned and target != rl:
                        hits.add(target)
                    for rr in self.rec_releases.get(target, ()):
                        if rr in self.owned and rr != rl:
                            hits.add(rr)
            for h in sorted(hits)[:PERSON_FAN_CAP]:
                stops.setdefault(h, set()).add("crew_on")
        return stops

    def guests(self, rl: int) -> dict[int, set[str]]:
        own = self.own_artists(rl)
        people: set[int] = set()
        for rec in self.appears.get(rl, ()):
            for rel in GUEST:
                people |= self.into(rec, rel)
        people -= own
        stops: dict[int, set[str]] = {}
        for p in people:
            hits: set[int] = set()
            for rel in GUEST:
                for rec in self.out(p, rel):
                    for rr in self.rec_releases.get(rec, ()):
                        if rr in self.owned and rr != rl:
                            hits.add(rr)
            for h in sorted(hits)[:PERSON_FAN_CAP]:
                stops.setdefault(h, set()).add("guest_on")
        return stops

    def works(self, rl: int) -> dict[int, set[str]]:
        works: set[int] = set()
        for rec in self.appears.get(rl, ()):
            works |= self.out(rec, "performance")
        related = set(works)
        for w in works:
            for rel in WORK_REL:
                related |= self.out(w, rel) | self.into(w, rel)
        stops: dict[int, set[str]] = {}
        for w in related:
            for rec in self.into(w, "performance"):
                for rr in self.rec_releases.get(rec, ()):
                    if rr in self.owned and rr != rl:
                        stops.setdefault(rr, set()).add("same_work" if w in works else "derived_work")
        return stops

    def room(self, rl: int) -> dict[int, set[str]]:
        places: set[int] = set()
        for rec in self.appears.get(rl, ()):
            for rel in PLACE_REL:
                places |= self.into(rec, rel)
        stops: dict[int, set[str]] = {}
        for pl in places:
            for rel in PLACE_REL:
                for rec in self.out(pl, rel):
                    for rr in self.rec_releases.get(rec, ()):
                        if rr in self.owned and rr != rl:
                            stops.setdefault(rr, set()).add("recorded_at")
        return stops

    def moment(self, rl: int) -> dict[int, set[str]]:
        y = self.year.get(rl)
        if y is None:
            return {}
        own_artists = self.own_artists(rl)
        own_areas = set().union(*(self.artist_area.get(a, set()) for a in own_artists)) if own_artists else set()
        own_labels = self.labels.get(rl, set())
        stops: dict[int, set[str]] = {}
        for cand in self.owned:
            if cand == rl or cand not in self.year or abs(self.year[cand] - y) > MOMENT_YEARS:
                continue
            links = set()
            if own_labels & self.labels.get(cand, set()):
                links.add("same_period_label")
            if own_artists & self.own_artists(cand) or any(
                    a in self.own_artists(cand) for a in own_artists):
                links.add("same_period_credit")
            cand_areas = set().union(*(self.artist_area.get(a, set()) for a in self.own_artists(cand))) \
                if self.own_artists(cand) else set()
            if own_areas & cand_areas:
                links.add("same_period_area")
            if links:
                stops[cand] = links
        return stops


def _measure_kind(probe: Probe, kind: str) -> dict:
    fn = {"album_crew": probe.crew, "album_guests": probe.guests, "album_works": probe.works,
          "album_room": probe.room, "album_moment": probe.moment}[kind]
    counts, times, capped, overlap_hits, total_stops, label_only = [], [], 0, 0, 0, 0
    for rl in probe.owned:
        t0 = time.monotonic()
        stops = fn(rl)
        times.append(time.monotonic() - t0)
        if len(stops) > STOP_CAP:
            capped += 1
            stops = dict(list(stops.items())[:STOP_CAP])
        counts.append(len(stops))
        total_stops += len(stops)
        own_artists = probe.own_artists(rl)
        own_labels = probe.labels.get(rl, set())
        for s in stops:
            if probe.own_artists(s) & own_artists or probe.labels.get(s, set()) & own_labels:
                overlap_hits += 1
        if kind == "album_moment":
            for links in stops.values():
                if links == {"same_period_label"}:
                    label_only += 1
    with_stop = [c for c in counts if c > 0]
    n = len(probe.owned) or 1
    coverage = len(with_stop) / n
    median = statistics.median(with_stop) if with_stop else 0
    within = sum(1 for t in times if t <= BUILD_BOUND_SECONDS) / n
    result = {
        "albums": len(probe.owned),
        "albums_with_stop": len(with_stop),
        "coverage": round(coverage, 4),
        "median_stops_where_any": median,
        "max_stops": max(counts) if counts else 0,
        "capped_albums": capped,
        "stops_total": total_stops,
        "proxy_overlap_share": round(overlap_hits / total_stops, 4) if total_stops else None,
        "within_bound_share": round(within, 4),
        "build_seconds_max": round(max(times), 4) if times else 0,
    }
    if kind == "album_moment":
        result["label_only_share"] = round(label_only / total_stops, 4) if total_stops else None
    return result


def run(store: Path, kinds: tuple[str, ...] = KINDS) -> dict:
    probe = Probe(_connect(store))
    out = {"stop_cap": STOP_CAP, "build_bound_seconds": BUILD_BOUND_SECONDS, "kinds": {}}
    for kind in kinds:
        out["kinds"][kind] = _measure_kind(probe, kind)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    result = run(args.store.expanduser())
    args.out.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
