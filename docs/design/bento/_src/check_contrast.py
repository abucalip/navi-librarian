#!/usr/bin/env python3
"""Checks every Bento palette in ../tokens.json against the PaletteTest rules plus Bento's own tones.
Prints one line per palette and exits 1 on any failure.

    python3 docs/design/bento/_src/check_contrast.py

Design tooling only: nothing imports it and no test collects it. Once the palettes are in Palette.kt, PaletteTest and
BentoTest (spec section 13) are the gate; this lets the spec be checked before any code exists.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "_kit"))
import kit  # noqa: E402

TOKENS = json.load(open(os.path.join(HERE, "..", "tokens.json")))


def bento_roles(p):
    t = p["tones"]
    out = []
    for tone in TOKENS["toneOrder"]:
        out.append((f"onTone on {tone}", kit.ratio(t["onTone"], t[tone]), 4.5))
        out.append((f"onToneMuted on {tone}", kit.ratio(t["onToneMuted"], t[tone]), 4.5))
    out.append(("barIcon on bar (icons, 3:1)", kit.ratio(t["barIcon"], t["bar"]), 3.0))
    out.append(("onControl on control (active pill)", kit.ratio(p["onControl"], p["control"]), 4.5))
    out.append(("onDeep on deep", kit.ratio(t["onDeep"], t["deep"]), 4.5))
    out.append(("deepEyebrow on deep", kit.ratio(t["deepEyebrow"], t["deep"]), 4.5))
    out.append(("text on chip", kit.ratio(p["text"], t["chip"]), 4.5))
    out.append(("control on chip", kit.ratio(p["control"], t["chip"]), 4.5))
    return out


if __name__ == "__main__":
    sys.exit(1 if kit.run_checks(TOKENS["palettes"], bento_roles) else 0)
