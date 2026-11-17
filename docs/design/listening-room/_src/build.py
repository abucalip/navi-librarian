#!/usr/bin/env python3
"""Builds the Listening Room design package from ../tokens.json.

Writes ../tokens.css (CSS custom properties and @font-face), ../icons/<name>.svg and the sprite
../icons/icons.svg, then renders every page in ../pages to PNG with Google Chrome (default macOS
path; the PNGs are skipped when Chrome is missing). Spec: docs/LISTENING_ROOM_WEB.md.

    python3 build.py            # everything
    python3 build.py home       # tokens, icons and only pages whose name starts with "home"

Design tooling only: nothing imports it and no test collects it.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
with open(os.path.join(OUT, "tokens.json"), encoding="utf-8") as handle:
    TOKENS = json.load(handle)

# 24 x 24 grid, 1.75 stroke, round caps and joins, no fills (dots use r=1.6 circles filled by the
# sprite's currentColor). Each value is the inner SVG markup.
ICONS = {
    "home": '<path d="M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z"/>',
    "discover": '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
    "library": '<path d="M4 4v16M9 4v16M14 5l5 15"/>',
    "saved": '<path d="M6 3h12v18l-6-4-6 4z"/>',
    "radio": '<rect x="3" y="8" width="18" height="13" rx="2"/><path d="m7 3 10 5"/><circle cx="15" cy="14.5" r="2.5"/><path d="M6 13h3M6 16h3"/>',
    "acquisitions": '<path d="M12 3v12m0 0-4-4m4 4 4-4M4 17v3h16v-3"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    "get": '<path d="M12 4v11m0 0-4-4m4 4 4-4M5 20h14"/>',
    "more": '<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>',
    "prev": '<path d="m15 6-6 6 6 6"/>',
    "next": '<path d="m9 6 6 6-6 6"/>',
    "chev-down": '<path d="m6 9 6 6 6-6"/>',
    "close": '<path d="M6 6l12 12M18 6 6 18"/>',
    "check": '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/>',
    "skip": '<path d="M5 5l9 7-9 7zM19 5v14"/>',
    "lean-more": '<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>',
    "lean-less": '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
    "block": '<circle cx="12" cy="12" r="9"/><path d="m5.6 5.6 12.8 12.8"/>',
    "tag": '<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z"/><circle cx="8" cy="8" r="1.5"/>',
    "people": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.6 3.4-5.5 6.5-5.5s5.7 1.9 6.5 5.5"/><path d="M15.5 4.8a3.5 3.5 0 0 1 0 6.4M18 14.8c1.8.8 3 2.6 3.5 5.2"/>',
    "listeners": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="14" width="4" height="7" rx="1.5"/><rect x="17" y="14" width="4" height="7" rx="1.5"/>',
    "disc": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2.5"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    "repeat": '<path d="M17 2l3 3-3 3"/><path d="M4 11V9a4 4 0 0 1 4-4h12"/><path d="M7 22l-3-3 3-3"/><path d="M20 13v2a4 4 0 0 1-4 4H4"/>',
    "flame": '<path d="M12 21a7 7 0 0 0 7-7c0-4-3-6-4-10-2 2-3 4-3 6-1-1-2-2-2-4-2 2-5 5-5 8a7 7 0 0 0 7 7z"/>',
    "compass-spread": '<circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/><circle cx="12" cy="12" r="2.5"/>',
    "spark": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    "alert": '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17v.5"/>',
    "external": '<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "back": '<path d="M20 12H4m0 0 6-6m-6 6 6 6"/>',
    "filter": '<path d="M3 5h18l-7 8.5V20l-4-2v-4.5z"/>',
    "sort": '<path d="M7 4v16m0 0-3-3m3 3 3-3M17 20V4m0 0-3 3m3-3 3 3"/>',
    "grid": '<rect x="4" y="4" width="7" height="7" rx="1"/><rect x="13" y="4" width="7" height="7" rx="1"/><rect x="4" y="13" width="7" height="7" rx="1"/><rect x="13" y="13" width="7" height="7" rx="1"/>',
    "list": '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
    "quote": '<path d="M9 7H5v6h4v-1c0 2-1 4-3 5M19 7h-4v6h4v-1c0 2-1 4-3 5"/>',
    "plug": '<path d="M9 3v5M15 3v5M6 8h12v3a6 6 0 0 1-12 0zM12 17v4"/>',
    "grip": '<circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "note": '<path d="M9 18V5l11-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="17" cy="16" r="3"/>',
    "chev-up": '<path d="m6 15 6-6 6 6"/>',
    "key": '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M16 7l3 3M14 9l2 2"/>',
    "folder": '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
    "person": '<circle cx="12" cy="8" r="4"/><path d="M4 21c1-4.5 4.2-7 8-7s7 2.5 8 7"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.1 0 1.6-.9 1.2-1.8-.5-1-.1-2.2 1.1-2.2H17a4 4 0 0 0 4-4c0-5.5-4-10-9-10z"/><circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/>',
    "signal": '<circle cx="12" cy="12" r="2"/><path d="M8 8a5.7 5.7 0 0 0 0 8M16 8a5.7 5.7 0 0 1 0 8M5 5a10 10 0 0 0 0 14M19 5a10 10 0 0 1 0 14"/>',
}

FILLED_DOTS = {"more"}


def svg(name, inner):
    """One standalone icon file."""
    fill = "currentColor" if name in FILLED_DOTS else "none"
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
            f'fill="{fill}" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{inner}</svg>\n')


def write_icons():
    """icons/<name>.svg plus icons/icons.svg, a <symbol> sprite used as <use href="icons.svg#lr-name">."""
    folder = os.path.join(OUT, "icons")
    os.makedirs(folder, exist_ok=True)
    symbols = []
    for name, inner in ICONS.items():
        with open(os.path.join(folder, f"{name}.svg"), "w", encoding="utf-8") as handle:
            handle.write(svg(name, inner))
        fill = "currentColor" if name in FILLED_DOTS else "none"
        symbols.append(f'  <symbol id="lr-{name}" viewBox="0 0 24 24" fill="{fill}" stroke="currentColor" '
                       f'stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">{inner}</symbol>')
    sprite = ('<svg xmlns="http://www.w3.org/2000/svg" style="display:none">\n'
              + "\n".join(symbols) + "\n</svg>\n")
    with open(os.path.join(folder, "icons.svg"), "w", encoding="utf-8") as handle:
        handle.write(sprite)
    return sprite


def inline_sprite(sprite):
    """Put the sprite between <!--sprite--> and <!--/sprite--> in every page, so <use href="#lr-x">
    works from file:// (Chrome refuses an external sprite there)."""
    folder = os.path.join(OUT, "pages")
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".html"):
            continue
        path = os.path.join(folder, name)
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        start, end = text.find("<!--sprite-->"), text.find("<!--/sprite-->")
        if start < 0 or end < start:
            continue
        text = text[:start + len("<!--sprite-->")] + "\n" + sprite + text[end:]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


def type_rules():
    """One .lr-type-<role> class per type role, with the phone sizes under the phone breakpoint."""
    fonts = TOKENS["font"]
    rules, phone = [], []
    for role, spec in TOKENS["type"].items():
        if role == "note":
            continue
        family = fonts[spec["family"]]
        decl = (f"font-family: '{family['family']}', {family['fallback']}; font-weight: {spec['weight']}; "
                f"font-size: {spec['size']}px; line-height: {spec['line']}px;")
        if "tracking" in spec:
            decl += f" letter-spacing: {spec['tracking']}em;"
        if spec.get("case") == "upper":
            decl += " text-transform: uppercase;"
        rules.append(f".lr-type-{role} {{ {decl} }}")
        if "phone" in spec:
            phone.append(f"  .lr-type-{role} {{ font-size: {spec['phone']['size']}px; "
                         f"line-height: {spec['phone']['line']}px; }}")
    tablet = TOKENS["breakpoints"]["tablet"]
    return "\n".join(rules) + f"\n@media (max-width: {tablet - 1}px) {{\n" + "\n".join(phone) + "\n}\n"


def write_tokens_css():
    """../tokens.css: @font-face (paths relative to this package), variables and type classes."""
    lines = ["/* Generated by _src/build.py from tokens.json. Do not edit by hand. */"]
    for key in ("display", "text"):
        font = TOKENS["font"][key]
        for weight, path in zip(font["weights"], font["files"]):
            src = path if path.startswith("fonts/") else "../../../" + path
            lines.append(f"@font-face {{ font-family: '{font['family']}'; font-style: normal; "
                         f"font-weight: {weight}; font-display: swap; src: url('{src}') format('woff2'); }}")
    lines.append(":root {")
    lines += [f"  --lr-{name}: {entry['value']};" for name, entry in TOKENS["color"].items()]
    for name, value in TOKENS["hero"].items():
        if name != "note" and isinstance(value, str):
            lines.append(f"  --lr-hero-{name}: {value};")
    lines += [f"  --lr-space-{value}: {value}px;" for value in TOKENS["space"]]
    lines += [f"  --lr-radius-{name}: {value}px;" for name, value in TOKENS["radius"].items()]
    lines += [f"  --lr-{name}: {value}px;" for name, value in TOKENS["size"].items() if name != "icon-stroke"]
    lines += [f"  --lr-shadow-{name}: {value};" for name, value in TOKENS["shadow"].items()]
    for name, spec in TOKENS["motion"].items():
        if name != "note":
            lines.append(f"  --lr-motion-{name}: {spec['ms']}ms {spec['ease']};")
    for key in ("display", "text"):
        font = TOKENS["font"][key]
        lines.append(f"  --lr-font-{key}: '{font['family']}', {font['fallback']};")
    lines.append("}")
    lines.append("@media (prefers-reduced-motion: reduce) { :root { "
                 + " ".join(f"--lr-motion-{n}: 0ms linear;" for n in TOKENS["motion"] if n != "note") + " } }")
    with open(os.path.join(OUT, "tokens.css"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n" + type_rules())


# Page name -> list of (suffix, width, height) renders.
RENDERS = {
    "home": [("", 1440, 3000), ("-phone", 390, 4600)],
    "reasons": [("", 1440, 2240)],
    "states": [("", 1440, 1960)],
}


def render(only):
    """PNG of every page (or those starting with `only`) at each listed size."""
    if not os.path.exists(CHROME):
        print("Chrome not found: PNGs skipped")
        return
    for page, sizes in RENDERS.items():
        if only and not page.startswith(only):
            continue
        path = os.path.join(OUT, "pages", f"{page}.html")
        for suffix, width, height in sizes:
            target = os.path.join(OUT, "pages", f"{page}{suffix}.png")
            source, frame = path, None
            if width < 600:
                # Headless Chrome will not open a window this narrow, so the page is drawn in an
                # iframe of the phone's width inside a wider window, and the PNG cropped to it.
                frame = os.path.join(OUT, "pages", "_frame.html")
                with open(frame, "w", encoding="utf-8") as handle:
                    handle.write(f'<!doctype html><body style="margin:0;background:#101114"><iframe src="{page}.html" '
                                 f'style="border:0;width:{width}px;height:{height}px;display:block;margin-left:{(600 - width) // 2}px">'
                                 '</iframe></body>')
                source = frame
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            f"--window-size={max(width, 600)},{height}", "--virtual-time-budget=4000",
                            f"--screenshot={target}", "file://" + source],
                           stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, check=False)
            if frame:
                os.remove(frame)
                crop(target, width)
            print("wrote", os.path.relpath(target, OUT))


def crop(target, width):
    """Cut a PNG to its middle `width` pixels with macOS sips (sips crops around the centre; the frame is centred)."""
    probe = subprocess.run(["sips", "-g", "pixelHeight", target], capture_output=True, text=True, check=False)
    height = int(probe.stdout.split()[-1])
    subprocess.run(["sips", "--cropToHeightWidth", str(height), str(width), target],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


if __name__ == "__main__":
    write_tokens_css()
    inline_sprite(write_icons())
    render(sys.argv[1] if len(sys.argv) > 1 else "")
