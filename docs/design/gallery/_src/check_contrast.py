#!/usr/bin/env python3
"""Checks every Gallery palette in ../tokens.json against the rules PaletteTest applies to all palettes,
plus the Gallery roles (control, onControl, mat). Prints a table and exits 1 on any failure.

    python3 check_contrast.py

Design tooling only: nothing imports it and no test collects it. The app's own PaletteTest stays the gate
once the palettes are in Palette.kt; this lets the spec be checked before any code exists.
"""
import colorsys, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOKENS = json.load(open(os.path.join(HERE, "..", "tokens.json")))


def rgb(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
def hexs(c): return "#" + "".join(f"{round(v * 255):02X}" for v in c)
def lerp(a, b, t): return tuple(x + (y - x) * t for x, y in zip(rgb(a) if isinstance(a, str) else a, rgb(b) if isinstance(b, str) else b))


def lum(c):
    c = rgb(c) if isinstance(c, str) else c
    f = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * f[0] + 0.7152 * f[1] + 0.0722 * f[2]


def ratio(a, b):
    x, y = lum(a), lum(b)
    return (max(x, y) + 0.05) / (min(x, y) + 0.05)


def pastel(tint):
    """theme/Theme.kt pastelOf: same hue, saturation x0.6 capped at 0.5, value 0.95, lightened to luminance 0.72."""
    h, s, _ = colorsys.rgb_to_hsv(*tint)
    out = colorsys.hsv_to_rgb(h, min(s * 0.6, 0.5), 0.95)
    steps = 0
    while lum(out) < 0.72 and steps < 20:
        out = lerp(out, (1, 1, 1), 0.12); steps += 1
    return out


def dims(p):
    """The …Dim roles: the colour at 10% over the surface (Palette's tint())."""
    return {k + "Dim": hexs(lerp(p["surface"], p[src], 0.10)) for k, src in
            [("accent", "accent"), ("ok", "ok"), ("caution", "caution"), ("danger", "chartRedText"), ("info", "info")]}


def checks(p):
    d = dims(p)
    out = []
    for bg_name in ("ink", "surface", "raised", "rail"):
        bg = p[bg_name]
        for role in ("text", "textMuted", "chartRedText", "caution", "ok"):
            out.append((f"{role} on {bg_name}", ratio(p[role], bg), 4.5))
        out.append((f"control (icons, links) on {bg_name}", ratio(p["control"], bg), 4.5))
    out.append(("text on mat", ratio(p["text"], p["mat"]), 4.5))
    out.append(("onAccent on accent", ratio(p["onAccent"], p["accent"]), 4.5))
    out.append(("onControl on control", ratio(p["onControl"], p["control"]), 4.5))
    out.append(("text on accentDim", ratio(p["text"], d["accentDim"]), 4.5))
    for bg_name in ("ink", "surface"):
        out.append((f"accent on {bg_name} (state, used as text)", ratio(p["accent"], p[bg_name]), 4.5))
        out.append((f"edgeStrong on {bg_name}", ratio(p["edgeStrong"], p[bg_name]), 3.0))
    if p["light"]:
        worst = min(min(ratio(p["textMuted"], pastel(colorsys.hsv_to_rgb(h / 360, 0.85, 0.4))) for h in range(0, 360, 15)), 99)
        out.append(("textMuted on every pastel wash", worst, 4.5))
    return out, d


def main():
    bad = 0
    for p in TOKENS["palettes"]:
        rows, d = checks(p)
        worst = min(rows, key=lambda r: r[1] / r[2])
        fails = [r for r in rows if r[1] < r[2]]
        bad += len(fails)
        print(f"{p['id']:<18} {len(rows)} checks, lowest {worst[0]} {worst[1]:.2f}:1 (needs {worst[2]})" + ("" if not fails else "  FAIL: " + "; ".join(f"{n} {v:.2f}" for n, v, _ in fails)))
        print("    dims: " + ", ".join(f"{k} {v}" for k, v in d.items()))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
