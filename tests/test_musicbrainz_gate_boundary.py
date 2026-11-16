"""Every module that calls the MusicBrainz web service must take its slots from the shared gate.

Efficiency plan R3: total MusicBrainz traffic from this host stays under one request per 1.1 s only
if no module paces (or fails to pace) on its own. ``PENDING`` lists modules still to route; R3 part 2
emptied it, so a new MusicBrainz caller must use the gate from the start.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "musicbrainz.org/ws"
SKIP_DIRS = {"tests", "scripts", ".venv", "node_modules", "android", "macos", "docs", "static"}
# Module-level URL constants only: the caller hands in a gate lane (set_fetchers) or the gate itself.
URL_ONLY = {"intelligence/insights/set_fetchers.py"}
PENDING: set[str] = set()


def _callers():
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if SKIP_DIRS & set(rel.parts[:-1]) or rel.parts[0].startswith("."):
            continue
        if HOST in path.read_text(encoding="utf-8"):
            yield rel.as_posix(), path.read_text(encoding="utf-8")


class MusicBrainzGateBoundaryTests(unittest.TestCase):
    def test_every_musicbrainz_caller_uses_the_gate(self):
        missing = {rel for rel, text in _callers()
                   if "provider_gate" not in text and rel not in URL_ONLY and rel not in PENDING}
        self.assertEqual(missing, set(), "MusicBrainz URL without the shared provider gate")

    def test_pending_list_only_names_unrouted_modules(self):
        routed = {rel for rel, text in _callers() if "provider_gate" in text}
        self.assertEqual(PENDING & routed, set(), "routed through the gate: remove from PENDING")
        self.assertEqual({rel for rel in PENDING if not (ROOT / rel).exists()}, set())
