"""Wikidata ingest for influences, genres, origin and founding dates (Server V2 Phase 5, work item 1).

For owned artists the MusicBrainz slice already holds a Wikidata id (from URL relations). This worker
job asks Wikidata for those entities' claims, 50 ids per ``wbgetentities`` request (the batch form the
API offers), and writes only what it can state with evidence:

* ``P737`` influenced by -> an ``influenced by`` edge between two artists the store already knows by
  Wikidata id;
* ``P136`` genre -> a ``genre`` edge to a genre entity the store already knows by Wikidata id;
* ``P740`` location of formation -> a ``formed in`` edge to an area the store already knows;
* ``P571`` inception and ``P576`` dissolved -> ``artist_life_span`` begin and end dates, only when
  MusicBrainz stated none (the dump wins).

Nothing is inferred: a target the store does not know by Wikidata id is skipped and counted, never
created from a label. Every edge is ``source_explicit`` / ``exact_mbid`` (the artist is keyed by the
id the MusicBrainz URL relation gave) and its ``source_url`` is the statement URI, so a claim links to
its Wikidata statement. Deprecated statements, ``somevalue``/``novalue`` and dates coarser than a year
are ignored; a preferred statement hides normal ones for the same property.

Rules (same as ``musicbrainz.api_fill``): only owned entities; nothing runs before a MusicBrainz slice
is loaded; at most ``max_requests`` requests per run, one per ``MIN_INTERVAL`` seconds; a fetched
entity is not asked again before its ``source_state`` refresh time; three failures in a row stop the
run. The web process never calls this. Anonymous API, descriptive User-Agent.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..jobs import runner
from ..musicbrainz.api_fill import ApiError, Paced, slice_loaded
from ..store import repositories as repo
from ..store import source_state

SOURCE = "wikidata"
JOB = "wikidata_ingest"
OPERATION = "entity_claims"
BASE = "https://www.wikidata.org/w/api.php"
USER_AGENT = "Discair/1.0 (personal music discovery)"
MIN_INTERVAL = 1.0
BATCH = 50
REFRESH_TTL = 30 * 24 * 3600.0
MAX_FAILURES_IN_A_ROW = 3
DEFAULT_MAX_REQUESTS = 40
OWNER_TYPES = ("artist", "person", "group")
PROPS = {"P737": "influenced by", "P136": "genre", "P740": "formed in", "P571": "inception", "P576": "dissolved"}
_QID = re.compile(r"^Q[1-9]\d*$")
_TIME = re.compile(r"^\+(\d{4})-(\d{2})-(\d{2})T")

Fetch = Callable[[str], dict]


def http_fetch(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise ApiError(exc.code) from exc
    except Exception as exc:
        raise ApiError(None, type(exc).__name__) from exc


@dataclass
class IngestResult:
    requests: int = 0
    entities_filled: int = 0
    entities_absent: int = 0
    edges_created: int = 0
    dates_filled: int = 0
    targets_unknown: int = 0
    failures: int = 0
    pending: int = 0
    stopped: str | None = None  # no_slice | request_budget | failures

    def summary(self) -> dict[str, Any]:
        return dict(self.__dict__)


# ------------------------------------------------------------------ candidates

def pending_entities(db: sqlite3.Connection, now: float) -> list[tuple[int, str]]:
    """Owned artists with a Wikidata id that are due (never fetched, or past their refresh time)."""
    marks = ", ".join("?" for _ in OWNER_TYPES)
    rows = db.execute(
        f"SELECT id, wikidata_id FROM entities WHERE owned = 1 AND type IN ({marks}) AND wikidata_id IS NOT NULL "
        "ORDER BY id", OWNER_TYPES).fetchall()
    out = []
    for row in rows:
        qid = str(row["wikidata_id"]).upper()
        if not _QID.match(qid):
            continue
        state = source_state.get_state(db, SOURCE, OPERATION, qid)
        if state is None or (state["next_refresh_at"] is not None and state["next_refresh_at"] <= now):
            out.append((row["id"], qid))
    return out


# ------------------------------------------------------------------ parsing

def _best(statements) -> list[dict]:
    """Non-deprecated statements with a real value; preferred ones hide normal ones."""
    usable = [s for s in statements or [] if s.get("rank") in ("normal", "preferred")
              and (s.get("mainsnak") or {}).get("snaktype") == "value"]
    preferred = [s for s in usable if s["rank"] == "preferred"]
    return preferred or usable


def claims(entity: dict) -> dict[str, list[dict[str, Any]]]:
    """``{property: [{"qid" | "date", "statement"}]}`` for the properties this job keeps."""
    out: dict[str, list[dict[str, Any]]] = {}
    for prop in PROPS:
        for statement in _best((entity.get("claims") or {}).get(prop)):
            value = (statement["mainsnak"].get("datavalue") or {}).get("value")
            item: dict[str, Any] = {"statement": str(statement.get("id") or "")}
            if prop in ("P571", "P576"):
                date = year_date(value)
                if date is None:
                    continue
                item["date"] = date
            else:
                qid = str(value.get("id") or "") if isinstance(value, dict) else ""
                if not _QID.match(qid):
                    continue
                item["qid"] = qid
            out.setdefault(prop, []).append(item)
    return out


def year_date(value) -> str | None:
    """``YYYY``, ``YYYY-MM`` or ``YYYY-MM-DD`` from a Wikidata time value; None when coarser than a year."""
    if not isinstance(value, dict):
        return None
    match = _TIME.match(str(value.get("time") or ""))
    precision = value.get("precision")
    if not match or not isinstance(precision, int) or precision < 9 or int(match.group(1)) < 1:
        return None
    year, month, day = match.groups()
    if precision == 9 or month == "00":
        return year
    return f"{year}-{month}" if precision == 10 or day == "00" else f"{year}-{month}-{day}"


# ------------------------------------------------------------------ writing

def _known(db, qid: str, types: tuple[str, ...]) -> int | None:
    marks = ", ".join("?" for _ in types)
    row = db.execute(f"SELECT id FROM entities WHERE wikidata_id = ? AND type IN ({marks}) ORDER BY id LIMIT 1",
                     (qid, *types)).fetchone()
    return row["id"] if row else None


def write_entity(db: sqlite3.Connection, entity_id: int, qid: str, entity: dict, *, now: float) -> tuple[int, int, int]:
    """Store one entity's claims; returns ``(edges created, dates filled, targets skipped as unknown)``."""
    found = claims(entity)
    observation_id, _ = repo.add_observation(
        db, SOURCE, {"operation": OPERATION, "qid": qid,
                     "claims": {p: [c.get("qid") or c.get("date") for c in v] for p, v in sorted(found.items())}},
        fetched_at=now, entity_hint=qid)
    created = skipped = 0
    targets = {"P737": ("artist", "person", "group"), "P136": ("genre",), "P740": ("area",)}
    for prop, types in targets.items():
        for claim in found.get(prop, []):
            target = _known(db, claim["qid"], types)
            if target is None:
                skipped += 1
                continue
            if target == entity_id:
                continue
            _, new = repo.add_edge(
                db, entity_id, target, PROPS[prop], evidence_class="source_explicit", match_quality="exact_mbid",
                source=SOURCE, observation_id=observation_id,
                source_url=f"https://www.wikidata.org/entity/statement/{claim['statement']}" if claim["statement"]
                else f"https://www.wikidata.org/wiki/{qid}")
            created += int(new)
    begin = (found.get("P571") or [{}])[0].get("date")
    end = (found.get("P576") or [{}])[0].get("date")
    filled = 0
    if begin or end:
        with db:
            filled = db.execute(
                "INSERT INTO artist_life_span (entity_id, begin_date, end_date, ended) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (entity_id) DO NOTHING", (entity_id, begin, end, int(bool(end)))).rowcount
    return created, filled, skipped


# ------------------------------------------------------------------ the job

def run_wikidata_ingest(
    db: sqlite3.Connection,
    *,
    fetch: Fetch | None = None,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    require_slice: bool = True,
    clock: Callable[[], float] = time.time,
) -> runner.RunResult:
    """Ingest claims for pending owned artists within ``max_requests``; safe to repeat."""
    paced = fetch if isinstance(fetch, Paced) else Paced(fetch or http_fetch, interval=MIN_INTERVAL)

    def work(ctx: runner.JobContext) -> bool:
        result = IngestResult()
        if require_slice and not slice_loaded(db):
            result.stopped = "no_slice"
            ctx.checkpoint(result.summary())
            return True
        pending = pending_entities(db, clock())
        failures = 0
        for start in range(0, len(pending), BATCH):
            if paced.requests >= max_requests or failures >= MAX_FAILURES_IN_A_ROW or not ctx.has_budget():
                break
            chunk = {qid: entity_id for entity_id, qid in pending[start:start + BATCH]}
            try:
                body = paced(BASE + "?" + urlencode({
                    "action": "wbgetentities", "ids": "|".join(chunk), "props": "claims", "format": "json"}, safe="|"))
            except ApiError:
                failures += 1
                result.failures += 1
                for qid in chunk:
                    source_state.record_outcome(db, SOURCE, OPERATION, qid, "error", now=clock())
                continue
            failures = 0
            returned = body.get("entities") or {}
            for qid, entity_id in chunk.items():
                entity = returned.get(qid)
                if not isinstance(entity, dict) or "missing" in entity or "claims" not in entity:
                    result.entities_absent += 1
                    source_state.record_outcome(db, SOURCE, OPERATION, qid, "not_found", now=clock(), ttl=REFRESH_TTL)
                    continue
                edges, dates, skipped = write_entity(db, entity_id, qid, entity, now=clock())
                result.entities_filled += 1
                result.edges_created += edges
                result.dates_filled += dates
                result.targets_unknown += skipped
                source_state.record_outcome(db, SOURCE, OPERATION, qid, "ok", now=clock(), ttl=REFRESH_TTL)
            ctx.checkpoint(result.summary(), items=len(chunk))
        result.requests = paced.requests
        result.pending = len(pending_entities(db, clock()))
        if failures >= MAX_FAILURES_IN_A_ROW:
            result.stopped = "failures"
        elif paced.requests >= max_requests and result.pending:
            result.stopped = "request_budget"
        ctx.checkpoint(result.summary())
        return True

    return runner.run_job(db, JOB, work, clock=clock)
