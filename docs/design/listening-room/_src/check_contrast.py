#!/usr/bin/env python3
"""Checks the Listening Room tokens: every pair under "contrast" in ../tokens.json, and the hero
panel's cover-tint clamp across the whole hue and saturation range. Prints failures and exits 1 on any.

    python3 check_contrast.py

Design tooling only: nothing imports it and no test collects it. hero_tint() is the reference for
the browser code in LISTENING_ROOM_WEB.md section 4.3; the two must give the same colour.
"""
import colorsys
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "..", "tokens.json"), encoding="utf-8") as handle:
    TOKENS = json.load(handle)


def rgb(value):
    """A #RRGGBB string as three floats in 0..1."""
    return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))


def luminance(color):
    """WCAG relative luminance of a #RRGGBB string or an rgb tuple."""
    channels = rgb(color) if isinstance(color, str) else color
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def ratio(first, second):
    """WCAG contrast ratio of two colours."""
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def over(fill, alpha, base):
    """A white or black fill at alpha composited over base (an rgb tuple)."""
    return tuple(fill * alpha + b * (1 - alpha) for b in base)


def hero_tint(sampled):
    """The hero panel colour for a sampled cover colour (rgb tuple), or the fallback for None.

    Keep the hue, cap the saturation, start at lightness_start and step the lightness down until
    the luminance is at most luminance_max, never below lightness_min.
    """
    hero = TOKENS["hero"]
    if sampled is None:
        return rgb(hero["fallback"])
    hue, light, sat = colorsys.rgb_to_hls(*sampled)
    del light
    sat = min(sat, hero["saturation_max"])
    light = hero["lightness_start"]
    color = colorsys.hls_to_rgb(hue, light, sat)
    while luminance(color) > hero["luminance_max"] and light > hero["lightness_min"]:
        light = round(light - hero["lightness_step"], 4)
        color = colorsys.hls_to_rgb(hue, light, sat)
    return color


def check_pairs(failures):
    """Every listed token pair meets its minimum."""
    colors = {name: entry["value"] for name, entry in TOKENS["color"].items()}
    for fore, back, minimum in TOKENS["contrast"]:
        got = ratio(colors[fore], colors[back])
        status = "ok " if got >= minimum else "FAIL"
        print(f"{status} {fore:>14} on {back:<14} {got:5.2f} (min {minimum})")
        if got < minimum:
            failures.append(f"{fore} on {back}")


def check_hero(failures):
    """Hero text, soft text, button labels and control edges pass on every clamped tint, both ends included."""
    hero = TOKENS["hero"]
    samples = [None, (1.0, 1.0, 1.0), (0.0, 0.0, 0.0), (1.0, 1.0, 0.0), (0.0, 1.0, 1.0)]
    samples += [colorsys.hls_to_rgb(h / 360, l / 10, s / 10)
                for h in range(0, 360, 10) for l in range(0, 11, 2) for s in range(0, 11, 2)]
    edge_alpha = float(hero["button-edge"].rstrip(")").split(",")[-1])
    worst = (99.0, None)
    for sample in samples:
        panel = hero_tint(sample)
        button = over(1.0, 0.10, panel)
        edge = over(1.0, edge_alpha, panel)
        aside = over(0.0, 0.28, panel)
        accent = TOKENS["color"]["accent"]["value"]
        checks = [(hero["text"], panel, 4.5), (hero["text-soft"], panel, 4.5), (hero["text"], button, 4.5),
                  (hero["text-soft"], aside, 4.5), (accent, panel, 3.0), (edge, panel, 3.0)]
        for fore, back, minimum in checks:
            got = ratio(fore, back)
            if minimum >= 4.5:
                worst = min(worst, (got, (fore, sample)), key=lambda item: item[0])
            if got < minimum:
                failures.append(f"hero {fore} on tint of {sample}: {got:.2f}")
    print(f"hero: {len(samples)} samples, lowest text ratio {worst[0]:.2f}")


def main():
    """Run both checks."""
    failures = []
    check_pairs(failures)
    check_hero(failures)
    if failures:
        print("\n".join(["", "Failures:"] + failures[:20]))
        return 1
    print("all pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
