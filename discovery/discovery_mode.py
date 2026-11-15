"""Discovery mode: one switch over the existing selection knobs (Star Operation, S4a).

``balanced`` is exactly today's behaviour. ``safer`` and ``deeper`` move only the maximum of a
gate lens's audience band (S4b, from a replay measurement; the numbers await the owner's approval):
``safer`` doubles it (a wider, better known band) and ``deeper`` halves it. The adventurous floor
is the same in every mode: it is a floor, so lowering it cannot make a list safer, and raising it
only collapses genre spread (measured; see PROJECT_LOG.md).

The knobs reach every list built from the allocator or the lens gates: the personal list
(adventurous floor under the family-coverage policy) and the lens lists (the same floor in
Genre spread, and a scale on the audience band of the gate-based lenses). The unknown-audience
rule is not a knob: an unknown audience is never called obscure in any mode. Lens
definitions themselves do not change; the scale is applied to their approved bands at run time.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

DISCOVERY_MODE_KEY = "discovery_mode"
DEFAULT_DISCOVERY_MODE = "balanced"
DISCOVERY_MODES = ("safer", "balanced", "deeper")


@dataclass(frozen=True)
class DiscoveryKnobs:
    """The numbers one mode moves. The defaults are today's values."""
    # Adventurous floor is ``count // adventurous_floor_divisor`` (a smaller divisor, a bigger floor).
    adventurous_floor_divisor: int = 5
    # Multipliers on a gate-based lens's own audience band (1.0 leaves the approved band as is).
    audience_min_scale: float = 1.0
    audience_max_scale: float = 1.0

    def adventurous_floor(self, count: int) -> int:
        return count // self.adventurous_floor_divisor

    def audience_band(self, minimum: int, maximum: int) -> tuple[int, int]:
        """Scale a lens's band; unchanged (and the same ints) at scale 1.0."""
        if self.audience_min_scale == 1.0 and self.audience_max_scale == 1.0:
            return minimum, maximum
        return int(round(minimum * self.audience_min_scale)), int(round(maximum * self.audience_max_scale))


BALANCED = DiscoveryKnobs()
# S4b values, measured with scripts/discovery_mode_sweep.py; pending the owner's approval.
SAFER = DiscoveryKnobs(audience_max_scale=2.0)
DEEPER = DiscoveryKnobs(audience_max_scale=0.5)
MODE_KNOBS: Mapping[str, DiscoveryKnobs] = {"safer": SAFER, "balanced": BALANCED, "deeper": DEEPER}


def discovery_mode_value(settings_read: Callable[[], Mapping]) -> str:
    """The stored mode; absent, unreadable or unknown means ``balanced``."""
    try:
        value = settings_read().get(DISCOVERY_MODE_KEY, DEFAULT_DISCOVERY_MODE)
    except Exception:
        return DEFAULT_DISCOVERY_MODE
    return value if isinstance(value, str) and value in DISCOVERY_MODES else DEFAULT_DISCOVERY_MODE


def knobs_for_mode(mode: str) -> DiscoveryKnobs:
    return MODE_KNOBS.get(mode, BALANCED)


def discovery_knobs(settings_read: Callable[[], Mapping] | None) -> DiscoveryKnobs:
    """Knobs for the stored mode; no reader means ``balanced``."""
    if settings_read is None:
        return BALANCED
    return knobs_for_mode(discovery_mode_value(settings_read))
