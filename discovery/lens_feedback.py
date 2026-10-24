"""Per-lens comparison of listener feedback (Engine 2, Phase 5).

Pure: no I/O, no clock, no provider call. Every lens album carries its ``lens`` name (see
``discovery.lens_lists``), so a save or dismissal made from a lens list lands in
``discovery_feedback`` with that name in its metadata. This module counts those actions per lens.

Counts are current state, not history: a save removed with "remove" or a dismissal replaced by
a later save no longer counts. Rates are shown only where there is at least one action, and no
quality claim is made from them (docs/engine2.md, Phase 5).
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# Album-scope feedback statuses written by ``navidrome_server.discovery_set_feedback``.
SAVED_STATUS = "for_me"
DISMISSED_STATUS = "not_for_me"


def _lens_of(row: Mapping[str, Any]) -> str | None:
    metadata = row.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    lens = metadata.get("lens")
    return lens if isinstance(lens, str) else None


def lens_feedback_summary(
    feedback_rows: Iterable[Mapping[str, Any]], lens_names: Iterable[str],
) -> dict[str, dict[str, Any]]:
    """Return ``{lens: {"saved", "dismissed", "actions", "save_rate"}}`` for each name in ``lens_names``.

    Only album-scope rows whose metadata names one of the given lenses count. ``save_rate`` is
    saved over actions, or None when the lens has no actions yet.
    """
    counts: dict[str, dict[str, int]] = {name: {"saved": 0, "dismissed": 0} for name in lens_names}
    for row in feedback_rows:
        if not isinstance(row, Mapping) or row.get("scope") != "album":
            continue
        lens = _lens_of(row)
        if lens not in counts:
            continue
        if row.get("status") == SAVED_STATUS:
            counts[lens]["saved"] += 1
        elif row.get("status") == DISMISSED_STATUS:
            counts[lens]["dismissed"] += 1
    summary: dict[str, dict[str, Any]] = {}
    for name, count in counts.items():
        actions = count["saved"] + count["dismissed"]
        summary[name] = {
            "saved": count["saved"],
            "dismissed": count["dismissed"],
            "actions": actions,
            "save_rate": round(count["saved"] / actions, 3) if actions else None,
        }
    return summary
