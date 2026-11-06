"""Pure smart-playlist rule validation and evaluation (Phase 6 item 6, slice 12).

A rule set is a saved query over Navidrome song rows. This module validates a raw rule set and
evaluates it over caller-supplied song rows and insight lookups. Nothing here reads or writes a
store, calls a provider or Navidrome, defines a route, runs a job, or talks to a client. It is
unwired: persistence is slice 13, routes slice 14.

It mirrors the macOS engine (``SmartEngine`` in ``SmartPlaylist.swift``) so a rule set gives the same
answer on both sides:

* a rule with an empty value, or a numeric rule whose value is not a whole number, is *unfinished*:
  it matches every song and is reported, never an error;
* text matching is case-insensitive; ``contains`` / ``not_contains`` also ignore diacritics;
* a song with an unknown numeric value (year or bitrate of 0 or missing, never added) never matches
  a numeric rule; ``plays`` and ``rating`` default to 0 as on the client;
* *last played (days ago)* with no play date matches only ``at_least`` ("at least 30 days ago"
  catches songs never played);
* a rule set with no rules matches every song; songs without an ``id`` are dropped;
* the limit keeps the first N songs of the ordered result.

Differences, on purpose: ordering has a stable tie-break on the Navidrome id (the client sorts
unstably), ``random`` takes a caller seed, and an unknown field/operator/order is a validation
error here (the client cannot produce one).

Insight fields
--------------
``obscurity_band`` (``equals`` / ``not_equals``) reads ``insights.obscurity_band[song_id]`` and
``in_lens`` (``equals`` = is in the lens, ``not_equals`` = is not) reads ``insights.lens_members[key]``,
a set of song ids. When the lookup the field needs is absent (``None``), the rule is unfinished and
listed in ``missing_data``. A song missing from a present lookup does not match ``equals``. The
``suppressed`` field is not offered while the suppression memory is record-only.

Wire names are snake_case: operators ``contains``, ``not_contains``, ``equals``, ``at_least``,
``at_most``; orders ``random``, ``newest_added``, ``most_played``, ``least_played``,
``highest_rated``, ``title``. Times are epoch seconds and ``now`` is supplied by the caller.
"""
from __future__ import annotations

import random
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

TEXT_FIELDS = ("artist", "title", "genre", "format")
NUMERIC_FIELDS = ("year", "plays", "rating", "bitrate", "added_days_ago", "played_days_ago")
INSIGHT_FIELDS = ("obscurity_band", "in_lens")
FIELDS = TEXT_FIELDS + NUMERIC_FIELDS + INSIGHT_FIELDS

TEXT_OPS = ("contains", "not_contains", "equals")
NUMERIC_OPS = ("at_least", "at_most", "equals")
INSIGHT_OPS = ("equals", "not_equals")
ORDERS = ("random", "newest_added", "most_played", "least_played", "highest_rated", "title")
MATCHES = ("all", "any")

MIN_LIMIT = 25
MAX_LIMIT = 250
MAX_NAME_LENGTH = 100
MAX_RULES = 20
MAX_VALUE_LENGTH = 200
SECONDS_PER_DAY = 86400

_INT_RE = re.compile(r"[+-]?[0-9]+")


@dataclass(frozen=True)
class SmartRule:
    field: str
    op: str
    value: str


@dataclass(frozen=True)
class RuleSet:
    name: str
    match: str
    rules: tuple[SmartRule, ...]
    order: str
    limit: int | None


@dataclass(frozen=True)
class ValidationError:
    path: str
    reason: str


@dataclass(frozen=True)
class Evaluation:
    song_ids: tuple[str, ...]
    matched: int
    unfinished: tuple[int, ...] = field(default_factory=tuple)
    missing_data: tuple[str, ...] = field(default_factory=tuple)


def validate_rule_set(raw: Any) -> tuple[RuleSet | None, tuple[ValidationError, ...]]:
    """Validate a raw rule-set mapping. Returns ``(rule_set, ())`` or ``(None, errors)``."""
    errors: list[ValidationError] = []
    if not isinstance(raw, Mapping):
        return None, (ValidationError("", "not_an_object"),)

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append(ValidationError("name", "bad_name"))
        name = ""
    elif len(name.strip()) > MAX_NAME_LENGTH:
        errors.append(ValidationError("name", "name_too_long"))

    match = raw.get("match", "all")
    if match not in MATCHES:
        errors.append(ValidationError("match", "bad_match"))

    order = raw.get("order", "random")
    if order not in ORDERS:
        errors.append(ValidationError("order", "bad_order"))

    limit = raw.get("limit")
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or not MIN_LIMIT <= limit <= MAX_LIMIT
    ):
        errors.append(ValidationError("limit", "bad_limit"))

    rules: list[SmartRule] = []
    raw_rules = raw.get("rules", [])
    if not isinstance(raw_rules, Sequence) or isinstance(raw_rules, (str, bytes)):
        errors.append(ValidationError("rules", "bad_rules"))
        raw_rules = []
    elif len(raw_rules) > MAX_RULES:
        errors.append(ValidationError("rules", "too_many_rules"))
        raw_rules = []
    for i, item in enumerate(raw_rules):
        rule, rule_errors = _validate_rule(item, f"rules[{i}]")
        errors.extend(rule_errors)
        if rule is not None:
            rules.append(rule)

    if errors:
        return None, tuple(errors)
    return RuleSet(name.strip(), match, tuple(rules), order, limit), ()


def _validate_rule(item: Any, path: str) -> tuple[SmartRule | None, list[ValidationError]]:
    if not isinstance(item, Mapping):
        return None, [ValidationError(path, "not_an_object")]
    errors: list[ValidationError] = []
    fld, op, value = item.get("field"), item.get("op"), item.get("value", "")
    if fld not in FIELDS:
        return None, [ValidationError(f"{path}.field", "bad_field")]
    allowed = TEXT_OPS if fld in TEXT_FIELDS else NUMERIC_OPS if fld in NUMERIC_FIELDS else INSIGHT_OPS
    if op not in allowed:
        errors.append(ValidationError(f"{path}.op", "bad_op"))
    if not isinstance(value, str):
        errors.append(ValidationError(f"{path}.value", "bad_value"))
    elif len(value) > MAX_VALUE_LENGTH:
        errors.append(ValidationError(f"{path}.value", "value_too_long"))
    if errors:
        return None, errors
    return SmartRule(fld, op, value), []


def evaluate(
    rule_set: RuleSet,
    songs: Sequence[Mapping[str, Any]],
    *,
    now: float,
    insights: Mapping[str, Any] | None = None,
    seed: int | str = 0,
) -> Evaluation:
    """Songs the rule set holds at ``now``, ordered and limited.

    ``songs`` are mappings with ``id`` and optionally ``artist``, ``title``, ``genre``, ``format``,
    ``year``, ``plays``, ``rating``, ``bitrate``, ``added_at``, ``played_at`` (epoch seconds).
    ``insights`` may hold ``obscurity_band`` (song id to band) and ``lens_members`` (lens key to a
    collection of song ids); an absent entry makes the rules that need it unfinished.
    """
    insights = insights or {}
    unfinished: list[int] = []
    missing: set[str] = set()
    for i, rule in enumerate(rule_set.rules):
        reason = _unfinished_reason(rule, insights)
        if reason is not None:
            unfinished.append(i)
            if reason:
                missing.add(reason)

    rows = [s for s in songs if isinstance(s.get("id"), str) and s["id"]]
    rows.sort(key=lambda s: s["id"])
    seen: set[str] = set()
    unique = []
    for s in rows:
        if s["id"] not in seen:
            seen.add(s["id"])
            unique.append(s)

    live = [(i, r) for i, r in enumerate(rule_set.rules) if i not in unfinished]
    matched = [s for s in unique if _holds(rule_set.match, live, s, now, insights)]
    ordered = _order(matched, rule_set.order, seed)
    if rule_set.limit:
        ordered = ordered[: rule_set.limit]
    return Evaluation(
        song_ids=tuple(s["id"] for s in ordered),
        matched=len(matched),
        unfinished=tuple(unfinished),
        missing_data=tuple(sorted(missing)),
    )


def _unfinished_reason(rule: SmartRule, insights: Mapping[str, Any]) -> str | None:
    """None if the rule can run; otherwise "" (empty/unreadable value) or the missing data name."""
    value = rule.value.strip()
    if not value:
        return ""
    if rule.field in NUMERIC_FIELDS and not _INT_RE.fullmatch(value):
        return ""
    if rule.field == "obscurity_band" and insights.get("obscurity_band") is None:
        return "obscurity_band"
    if rule.field == "in_lens":
        members = insights.get("lens_members")
        if members is None or value not in members:
            return "lens_members"
    return None


def _holds(match: str, live: list[tuple[int, SmartRule]], song: Mapping[str, Any], now: float,
           insights: Mapping[str, Any]) -> bool:
    if not live:
        return True
    results = (_matches(r, song, now, insights) for _, r in live)
    return all(results) if match == "all" else any(results)


def _fold(text: Any) -> str:
    stripped = "".join(c for c in unicodedata.normalize("NFKD", str(text or "")) if not unicodedata.combining(c))
    return stripped.casefold()


def _matches(rule: SmartRule, song: Mapping[str, Any], now: float, insights: Mapping[str, Any]) -> bool:
    value = rule.value.strip()
    fld = rule.field
    if fld in TEXT_FIELDS:
        text = str(song.get(fld) or "")
        if rule.op == "equals":
            return text.casefold() == value.casefold()
        found = _fold(value) in _fold(text)
        return not found if rule.op == "not_contains" else found
    if fld == "obscurity_band":
        band = insights["obscurity_band"].get(song["id"])
        same = band is not None and _fold(band) == _fold(value)
        return same if rule.op == "equals" else not same
    if fld == "in_lens":
        inside = song["id"] in insights["lens_members"][value]
        return inside if rule.op == "equals" else not inside

    target = int(value)
    actual = _numeric(fld, song, now)
    if fld == "played_days_ago" and actual is None:
        return rule.op == "at_least"
    if actual is None:
        return False
    if rule.op == "at_most":
        return actual <= target
    if rule.op == "equals":
        return actual == target
    return actual >= target


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _days(then: Any, now: float) -> int | None:
    if isinstance(then, bool) or not isinstance(then, (int, float)):
        return None
    return max(0, int((now - then) / SECONDS_PER_DAY))


def _numeric(fld: str, song: Mapping[str, Any], now: float) -> int | None:
    if fld == "year":
        n = _int(song.get("year"))
        return n if n and n > 0 else None
    if fld == "bitrate":
        n = _int(song.get("bitrate"))
        return n if n and n > 0 else None
    if fld == "plays":
        return _int(song.get("plays")) or 0
    if fld == "rating":
        return _int(song.get("rating")) or 0
    if fld == "added_days_ago":
        return _days(song.get("added_at"), now)
    return _days(song.get("played_at"), now)


def _order(songs: list[Mapping[str, Any]], order: str, seed: int | str) -> list[Mapping[str, Any]]:
    out = list(songs)  # already sorted by id, which is the tie-break for every order
    if order == "random":
        random.Random(f"{seed}").shuffle(out)
    elif order == "newest_added":
        out.sort(key=lambda s: -(s["added_at"] if isinstance(s.get("added_at"), (int, float)) else float("-inf")))
    elif order == "most_played":
        out.sort(key=lambda s: -(_int(s.get("plays")) or 0))
    elif order == "least_played":
        out.sort(key=lambda s: _int(s.get("plays")) or 0)
    elif order == "highest_rated":
        out.sort(key=lambda s: -(_int(s.get("rating")) or 0))
    else:
        out.sort(key=lambda s: _fold(s.get("title")))
    return out

