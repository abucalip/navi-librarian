#!/usr/bin/env python3
"""Checks every contrast pair in ../tokens.json.

Paths pairs are checked in Day and Night, for the default accent and for every accent hue 0..355 in steps of 5, with the
palette built the way CUPalette.make builds it (cupalette.py). A colour with an opacity is composited over its ground; the
Get corner badge (a 92% ground over artwork) is composited over both black and white artwork and the worse one counts.
Booklet pairs use the fixed CU.Booklet values, and the stage accent (the Night accent of the hue) is swept the same way.

    python3 check_contrast.py        # prints the worst case of each pair; exit 1 when any pair fails

Design tooling only: nothing in the app or the tests imports it.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cupalette import contrast, hexs, make, mixed, over  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "tokens.json"), encoding="utf-8") as handle:
    TOKENS = json.load(handle)

HUES = [None] + list(range(0, 360, 5))
NEED = {"text": 4.5, "graphic": 3.0}
ROLE = {"CU.content": "content", "CU.text": "text", "CU.textSecondary": "textSecondary", "CU.separator": "separator",
        "CU.bgPanel": "panel", "CU.bgFill": "fill", "CU.accent": "accent", "CU.accentStrong": "accentStrong",
        "CU.accentTint": "accentTint", "CU.onAccent": "onAccent", "CU.success": "success", "CU.successTint": "successTint",
        "CU.separatorStrong": "separatorStrong", "CU.danger": "danger"}


def paths_value(name, palette, artwork=None):
    spec = TOKENS["paths_colors"][name]
    if spec["role"] == "CU.shadowInk":
        base = 0x000000
    else:
        base = palette[ROLE[spec["role"]]]
    if "opacity" in spec:
        behind = artwork if artwork is not None else palette["content"]
        return over(base, behind, spec["opacity"])
    return base


def booklet_palette(hue):
    b = {k: int(v["hex"][1:], 16) for k, v in TOKENS["booklet_colors"].items() if isinstance(v, dict) and "hex" in v}
    b["stageAccent"] = make("night", hue)["accent"]
    b["selectedRow"] = mixed(b["panel"], b["stageAccent"], 0.18)
    return b


def main():
    failures = 0
    print("Paths (Day and Night, %d accent settings each)" % len(HUES))
    for kind, fg, bg, use in TOKENS["contrast"]["paths"]:
        worst = (99.0, "")
        for mode in ("day", "night"):
            for hue in HUES:
                p = make(mode, hue)
                grounds = [None] if bg != "badgeGround" else [0x000000, 0xFFFFFF]
                for art in grounds:
                    a, b = paths_value(fg, p), paths_value(bg, p, art)
                    r = contrast(a, b)
                    if r < worst[0]:
                        worst = (r, "%s hue=%s %s on %s" % (mode, "default" if hue is None else hue, hexs(a), hexs(b)))
        ok = worst[0] >= NEED[kind]
        failures += not ok
        print("  %-4s %-7s %-13s on %-13s %5.2f  %s  (%s)" % ("ok" if ok else "FAIL", kind, fg, bg, worst[0], worst[1], use))

    print("Booklet (fixed roles; stage accent over %d hues)" % len(HUES))
    for kind, fg, bg, use in TOKENS["contrast"]["booklet"]:
        worst = (99.0, "")
        for hue in HUES:
            b = booklet_palette(hue)
            r = contrast(b[fg], b[bg])
            if r < worst[0]:
                worst = (r, "hue=%s %s on %s" % ("default" if hue is None else hue, hexs(b[fg]), hexs(b[bg])))
        ok = worst[0] >= NEED[kind]
        failures += not ok
        print("  %-4s %-7s %-13s on %-13s %5.2f  %s  (%s)" % ("ok" if ok else "FAIL", kind, fg, bg, worst[0], worst[1], use))

    # Why the Booklet does not use the mode accent: report it, not as a failure.
    mode_worst = min(contrast(make(m, h)["accent"], 0x171717) for m in ("day", "night") for h in HUES)
    print("  note: the mode accent on the Booklet ground would fall to %.2f (why stageAccent is the Night accent)" % mode_worst)
    print("%d failing" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
