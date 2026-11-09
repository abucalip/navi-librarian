"""One-sentence taste headline (Phase 6, client presentation slice 1).

Pure and deterministic: reads a built ``TasteProfiles`` and returns the sentence both clients draw,
so macOS and Android never compose prose themselves. Nothing here fetches, writes or touches a
recommendation weight.

Rules (owner-approved 2026-11-09; the wording is a starting value, not measured):

* the recent window is used; when it is low-sample the mid window is used ("this past year");
  when neither is sound (or the all-time baseline is thin) there is no headline (``None``);
* the window's stated shifts are ranked by absolute share change, genre first, ties by value name;
* a genre (or other dimension) that moved both ways reads "More X, less Y lately.";
* a single mover reads "Leaning into X lately." (up) or "Drifting from Y lately." (down);
* a sound window with no stated shift reads "Your taste has held steady.".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .profiles import DIMENSIONS, Shift, TasteProfiles

_WINDOW_PHRASE = {"recent": "lately", "mid": "this past year"}
STEADY_TEXT = "Your taste has held steady."


@dataclass(frozen=True)
class Headline:
    text: str
    kind: str                       # "pair" | "up" | "down" | "steady"
    window: str                     # "recent" | "mid"
    subjects: tuple[dict[str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        return {"text": self.text, "kind": self.kind, "window": self.window,
                "subjects": [dict(s) for s in self.subjects]}


def _rank(s: Shift) -> tuple:
    return (-abs(s.to_share - s.from_share), s.value)


def _subject(s: Shift) -> dict[str, str]:
    return {"dimension": s.dimension, "value": s.value, "direction": s.direction}


def build_headline(profiles: TasteProfiles) -> Headline | None:
    """The headline for these profiles, or ``None`` when no window is sound enough to say anything."""
    if profiles.windows["all_time"].low_sample:
        return None
    window = next((w for w in ("recent", "mid") if not profiles.windows[w].low_sample), None)
    if window is None:
        return None
    phrase = _WINDOW_PHRASE[window]
    shifts = [s for s in profiles.shifts if s.window == window]
    if not shifts:
        return Headline(STEADY_TEXT, "steady", window, ())
    # Genre first; otherwise the first other dimension (in DIMENSIONS order) that has a stated shift.
    for dim in ("genre",) + tuple(d for d in DIMENSIONS if d != "genre"):
        chosen = [s for s in shifts if s.dimension == dim]
        if chosen:
            break
    ups = sorted((s for s in chosen if s.direction == "up"), key=_rank)
    downs = sorted((s for s in chosen if s.direction == "down"), key=_rank)
    if ups and downs:
        up, down = ups[0], downs[0]
        return Headline(f"More {up.value}, less {down.value} {phrase}.", "pair", window,
                        (_subject(up), _subject(down)))
    if ups:
        return Headline(f"Leaning into {ups[0].value} {phrase}.", "up", window, (_subject(ups[0]),))
    return Headline(f"Drifting from {downs[0].value} {phrase}.", "down", window, (_subject(downs[0]),))
