#!/usr/bin/env python3
"""Checks every Index palette in ../tokens.json against the PaletteTest rules plus Index's own tones.
Prints one line per palette and exits 1 on any failure.

    python3 docs/design/index/_src/check_contrast.py

Design tooling only: nothing imports it and no test collects it. Once the palettes are in Palette.kt, PaletteTest and
IndexTest (spec section 13) are the gate.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_kit"))
import kit  # noqa: E402

TOKENS = json.load(open(os.path.join(HERE, "..", "tokens.json")))


def index_roles(p):
    t = p["tones"]
    return [
        ("onStrip on strip", kit.ratio(t["onStrip"], t["strip"]), 4.5),
        ("stripMuted on strip", kit.ratio(t["stripMuted"], t["strip"]), 4.5),
        ("stripProgress on strip (progress line, 3:1)", kit.ratio(t["stripProgress"], t["strip"]), 3.0),
        ("onInsight on insight", kit.ratio(t["onInsight"], t["insight"]), 4.5),
        ("insightLabel on insight", kit.ratio(t["insightLabel"], t["insight"]), 4.5),
        ("accent on raised", kit.ratio(p["accent"], p["raised"]), 4.5),
    ]


if __name__ == "__main__":
    sys.exit(1 if kit.run_checks(TOKENS["palettes"], index_roles) else 0)
