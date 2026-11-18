"""Shared mockup kit for the Bento and Index Android theme packages (docs/plans/BENTO_THEME.md, docs/plans/INDEX_THEME.md).

Design tooling only: nothing in the app imports it and no test collects it. It holds what both packages share:
the stand-in artwork (covers and artist photos drawn in CSS), the sample data every mockup shows, the icon path table,
the contrast maths PaletteTest uses, and the page wrapper that lays frames side by side and renders a PNG with Chrome.

Each theme's own `_src/build.py` imports this file and adds its components and screens.
"""
import colorsys, os, subprocess

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FRAME_W, FRAME_H = 360, 780  # dp; 1 CSS px = 1dp

# ------------------------------------------------------------------------------------------------ stand-in artwork
# Not for the app: the app shows real covers and photos. Same albums and artists in both themes so the owner
# compares layout, type and colour, not art.
COVERS = {
    "lst": "radial-gradient(ellipse 22% 26% at 50% 42%,#DB8A3E 96%,transparent 100%),linear-gradient(90deg,transparent 49.3%,#4a2f1d 49.3% 50.7%,transparent 50.7%) top/100% 80% no-repeat,linear-gradient(#E3E7EA 0 78%,#6E4A2E 78%)",
    "hex": "linear-gradient(#0a1129 0 0) bottom/100% 22% no-repeat,repeating-linear-gradient(90deg,#1f3270 0 5%,#0e1739 5% 10%)",
    "prm": "radial-gradient(circle at 64% 38%,#151515 0 4%,transparent 4.5%),linear-gradient(135deg,#F2C9B8 0 34%,#B9D4C9 34% 67%,#ECE4C8 67%)",
    "vul": "radial-gradient(circle at 50% 40%,#0c1f1d 0 17%,transparent 17.5%),radial-gradient(ellipse 36% 30% at 50% 100%,#0c1f1d 0 97%,transparent 100%),linear-gradient(160deg,#9CC8BD,#2E5E57)",
    "mor": "radial-gradient(circle at 50% 50%,#FCE9D2 0 14%,transparent 14.5%),conic-gradient(from 45deg,#F06D9B 0 25%,#F7B24A 0 50%,#F06D9B 0 75%,#F7B24A 0)",
    "spc": "radial-gradient(circle at 72% 28%,#EDE6FF 0 6%,transparent 6.5%),radial-gradient(circle at 34% 66%,#7A5CFF 0 24%,transparent 24.5%),#140F2C",
    "afr": "repeating-linear-gradient(-45deg,#E85D2A 0 14px,#1C1A17 14px 28px)",
    "hlv": "conic-gradient(from 210deg at 60% 42%,#f6b38a,#e0577e,#6c3a8e,#f6b38a)",
    "blu": "linear-gradient(90deg,transparent 44%,#D62828 44% 56%,transparent 56%),linear-gradient(transparent 44%,#D62828 44% 56%,transparent 56%),#EFEBE3",
    "tit": "radial-gradient(ellipse 30% 16% at 50% 62%,#CFE6E0 0 92%,transparent 100%),linear-gradient(#0E4C5B,#06222A)",
    "sim": "radial-gradient(circle at 50% 56%,#F2B705 0 30%,transparent 30.5%),#1B3A2E",
    "sat": "radial-gradient(circle at 50% 46%,#f7d26b 0 19%,#e08a2b 20% 44%,#7a2a14 45%)",
    "end": "radial-gradient(circle at 30% 30%,#E8E1FF 0 8%,transparent 8.5%),linear-gradient(200deg,#3B2A7A,#0E0A20)",
    "ntr": "radial-gradient(ellipse 50% 20% at 50% 80%,#F2E3C6 0 95%,transparent 100%),#3E5C76",
    "pta": "repeating-radial-gradient(circle at 50% 50%,#E9C46A 0 6px,#264653 6px 12px)",
    "uni": "linear-gradient(90deg,#D9A441 0 33%,#B5523B 33% 66%,#3B2A20 66%)",
    "ete": "conic-gradient(from 0deg at 50% 50%,#1F3B4D,#7FB7BE,#1F3B4D)",
    "ele": "radial-gradient(circle at 50% 30%,#F7F1E3 0 12%,transparent 12.5%),linear-gradient(#2C5530,#0F2412)",
    "kar": "radial-gradient(circle at 30% 70%,#F4E3B5 0 20%,transparent 20.5%),linear-gradient(#5E2B5C,#2A1230)",
    "cru": "linear-gradient(135deg,#E9B949 0 50%,#B6452C 50%)",
    "nts": "repeating-linear-gradient(90deg,#D97941 0 10px,#F3D9B1 10px 20px)",
}
PHOTOS = {  # duotone stand-ins for artist photos
    "alice": ("#F2C46B", "#A0461E"), "khru": ("#F5A9C6", "#7A3D8F"), "arooj": ("#A9CDBF", "#2D5F57"), "mdou": ("#F0A15A", "#5A2414"),
    "simz": ("#C9D96A", "#3B5A1F"), "fp": ("#A8B8F0", "#3B3F8C"), "pharoah": ("#E7D3A8", "#6B4E2A"), "nala": ("#C7B3F5", "#4A2F7A"),
    "cocteau": ("#F2B49E", "#7A2E2E"), "rashied": ("#B9D7E8", "#2F5560"), "haden": ("#D8C8B0", "#4E3B2B"), "weyes": ("#BFE0E8", "#2E5865"),
}


def art_css():
    out = [".cv,.ph{display:block;position:relative;overflow:hidden;background:#333;flex:none}"]
    out += [f".c-{k}{{background:{v}}}" for k, v in COVERS.items()]
    out.append(".ph{--h:rgba(18,14,12,.85);background:radial-gradient(circle at 50% 40%,var(--h) 0 16%,transparent 16.5%),"
               "radial-gradient(ellipse 34% 30% at 50% 100%,var(--h) 0 97%,transparent 100%),linear-gradient(160deg,var(--a),var(--b))}")
    out += [f".p-{k}{{--a:{a};--b:{b}}}" for k, (a, b) in PHOTOS.items()]
    return "\n".join(out)

# ------------------------------------------------------------------------------------------------ sample data

A = {  # key: title, artist, year, genre, owned
    "lst": ("Laughing Stock", "Talk Talk", 1991, "Post-rock", True),
    "hex": ("Hex", "Bark Psychosis", 1994, "Post-rock", False),
    "prm": ("Promises", "Floating Points, Pharoah Sanders", 2021, "Ambient jazz", True),
    "vul": ("Vulture Prince", "Arooj Aftab", 2021, "Ghazal", True),
    "mor": ("Mordechai", "Khruangbin", 2020, "Psychedelic soul", True),
    "spc": ("Space 1.8", "Nala Sinephro", 2021, "Spiritual jazz", True),
    "afr": ("Afrique Victime", "Mdou Moctar", 2021, "Desert blues", True),
    "hlv": ("Heaven or Las Vegas", "Cocteau Twins", 1990, "Dream pop", False),
    "blu": ("Blue Lines", "Massive Attack", 1991, "Trip hop", True),
    "tit": ("Titanic Rising", "Weyes Blood", 2019, "Chamber pop", True),
    "sim": ("Sometimes I Might Be Introvert", "Little Simz", 2021, "Hip hop", True),
    "sat": ("Journey in Satchidananda", "Alice Coltrane", 1971, "Spiritual jazz", True),
    "end": ("Endlessness", "Nala Sinephro", 2024, "Spiritual jazz", False),
    "ntr": ("Night Reign", "Arooj Aftab", 2024, "Ghazal", False),
    "pta": ("Ptah, the El Daoud", "Alice Coltrane", 1970, "Spiritual jazz", False),
    "uni": ("Universal Consciousness", "Alice Coltrane", 1971, "Spiritual jazz", True),
    "ete": ("Eternity", "Alice Coltrane", 1976, "Spiritual jazz", True),
    "ele": ("Elevation", "Pharoah Sanders", 1974, "Spiritual jazz", False),
    "kar": ("Karma", "Pharoah Sanders", 1969, "Spiritual jazz", True),
    "cru": ("Crush", "Floating Points", 2019, "Electronic", True),
}
TRACKS = [("First Class", "4:10"), ("Time (You and I)", "6:21"), ("Connaissais de Face", "3:36"), ("If There Is No Question", "4:47"),
          ("Pelota", "3:51"), ("One to Remember", "5:07"), ("Dearest Alfred", "4:39"), ("So We Won't Forget", "4:17"),
          ("Father Bird, Mother Bird", "5:17"), ("Shida", "6:03")]
NOW = ("mor", "Pelota", "Khruangbin", "1:37", "3:51")  # the song in every mini player
STATIONS = [("FIP", "Today"), ("FIP Groove", "Today"), ("NTS 1", "Yesterday"), ("KEXP", "Sunday"), ("Radio Nova", "12 Nov")]
GENRES = [("Spiritual jazz", 38), ("Post-rock", 64), ("Dream pop", 51), ("Trip hop", 22), ("Desert blues", 19)]
ALBUM_PATH_TABS = ["Studio crew", "Guest list", "Covers and sources", "Same year, same scene", "Same room", "Listen-through gaps", "Neighbours by ear"]
ALBUM_PATH_STEPS = [  # Promises, Studio crew: album key, server sentence
    ("kar", "Pharoah Sanders leads both records, on tenor saxophone."),
    ("ele", "Pharoah Sanders plays tenor saxophone on both."),
    ("cru", "Sam Shepherd (Floating Points) wrote and produced both."),
    ("sat", "Pharoah Sanders plays soprano saxophone on both."),
]
ARTIST_PATH_KINDS = ["Follow the musician", "Sideman", "Label", "Composition", "Scene"]
ARTIST_PATH_STEPS = [  # Alice Coltrane, Follow the musician: person, photo, sentence, owned
    ("Pharoah Sanders", "pharoah", "Soprano saxophone on Journey in Satchidananda (1971).", True),
    ("Rashied Ali", "rashied", "Drums on Universal Consciousness and Journey in Satchidananda.", False),
    ("Charlie Haden", "haden", "Bass on Journey in Satchidananda (1971).", True),
    ("Jimmy Garrison", "fp", "Bass on Ptah, the El Daoud (1970).", False),
]

# ------------------------------------------------------------------------------------------------ icons
# 24 by 24 path data. Circles are written as two arcs so Android's PathParser reads every icon as plain path data.
# Names match ui/common/ArtIcons.kt (KOTLIN table) so each theme's icon object mirrors the existing one.

def circ(cx, cy, r): return f"M{cx - r:g} {cy:g}a{r:g} {r:g} 0 1 0 {2 * r:g} 0a{r:g} {r:g} 0 1 0 {-2 * r:g} 0"


ICONS = {
    "home": ["M4 10.5 12 4l8 6.5V20h-5.5v-5.5h-5V20H4z"],
    "disc": [circ(12, 12, 8.5), "m15.2 8.8-1.9 4.5-4.5 1.9 1.9-4.5z"],
    "lib": ["M5 4.5v15M9.5 4.5v15M14 5l5 14"],
    "search": [circ(10.5, 10.5, 6), "m15 15 5 5"],
    "play": ["M8 5.5v13l10.5-6.5z"],
    "pause": ["M7 5h3.5v14H7zM13.5 5H17v14h-3.5z"],
    "next": ["M5.5 6v12l9-6zM17.3 6h1.4v12h-1.4z"],
    "prev": ["M18.5 6v12l-9-6zM5.3 6h1.4v12H5.3z"],
    "dl": ["M7 17.5a4 4 0 0 1-.6-7.95A6 6 0 0 1 18 10.5a3.5 3.5 0 0 1-.5 7", "M12 11v8.5M9 16.5l3 3 3-3"],
    "gear": ["M4 7.5h9M17 7.5h3M4 16.5h3M11 16.5h9", circ(15, 7.5, 2), circ(9, 16.5, 2)],
    "more": [circ(5.5, 12, 1.5), circ(12, 12, 1.5), circ(18.5, 12, 1.5)],
    "chev": ["m9.5 6 6 6-6 6"],
    "back": ["M14.5 5.5 8 12l6.5 6.5"],
    "down": ["M5.5 9 12 15.5 18.5 9"],
    "up": ["M5.5 15 12 8.5 18.5 15"],
    "radio": ["M5 8.5h14a1.5 1.5 0 0 1 1.5 1.5v8.5a1.5 1.5 0 0 1-1.5 1.5H5a1.5 1.5 0 0 1-1.5-1.5V10A1.5 1.5 0 0 1 5 8.5z", "M8 8.5 17 4",
              circ(9, 14.2, 2.4), "M14.5 12.5h3M14.5 16h3"],
    "get": ["M7 17.5a4 4 0 0 1-.6-7.95A6 6 0 0 1 18 10.5a3.5 3.5 0 0 1-.5 7", "M12 11v8.5M9 16.5l3 3 3-3"],
    "heart": ["M12 19.5s-7-4.2-7-9.3A3.9 3.9 0 0 1 12 8a3.9 3.9 0 0 1 7 2.2c0 5.1-7 9.3-7 9.3z"],
    "bookmark": ["M7 4.5h10v15l-5-3.5-5 3.5z"],
    "check": ["M5 12.5l4.5 4.5L19 7.5"],
    "close": ["m6.5 6.5 11 11M17.5 6.5l-11 11"],
    "ban": [circ(12, 12, 8.5), "m6 6 12 12"],
    "queue": ["M4 6.5h16M4 12h10M4 17.5h10", "M17 14.5v6l4.5-3z"],
    "qadd": ["M4 6.5h12M4 12h12M4 17.5h7M18 14v6M15 17h6"],
    "shuffle": ["M4 7h3c4.5 0 5.5 10 10 10h3M4 17h3c1.5 0 2.6-1.2 3.4-2.8M13.6 9.8C14.4 8.2 15.5 7 17 7h3M17.5 4.5 20 7l-2.5 2.5M17.5 14.5 20 17l-2.5 2.5"],
    "repeat": ["M5 11V9a2 2 0 0 1 2-2h12M16.5 4.5 19 7l-2.5 2.5M19 13v2a2 2 0 0 1-2 2H5M7.5 19.5 5 17l2.5-2.5"],
    "repeat1": ["M5 11V9a2 2 0 0 1 2-2h12M16.5 4.5 19 7l-2.5 2.5M19 13v2a2 2 0 0 1-2 2H5M7.5 19.5 5 17l2.5-2.5", "M11.2 10.6l1.3-.9v4.6"],
    "quote": ["M5 5h14v10.5H10l-4 3.5v-3.5H5z", "M8.5 9h7M8.5 12h4.5"],
    "tune": ["M6 4v16M12 4v16M18 4v16", "M4 14h4M10 8h4M16 12.5h4"],
    "swap": ["M3 17c4 0 5-10 9-10s5 10 9 10M3 7c4 0 5 10 9 10s5-10 9-10"],
    "sun": [circ(12, 12, 4), "M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"],
    "server": ["M5 4h14v7H5zM5 13h14v7H5z", "M8 7.5h.01M8 16.5h.01"],
    "wave": ["M4 12h2l2-6 3 12 3-9 2 5 1-2h3"],
    "sort": ["M7 5v14M4 16l3 3 3-3M17 19V5M14 8l3-3 3 3"],
    "plus": ["M12 5v14M5 12h14"],
    "minus": ["M5 12h14"],
    "path": [circ(6, 18, 2), circ(18, 6, 2), "M7.8 17c4-1 2-6 5-8s3.5-1.5 3.8-1.6"],
    "info": [circ(12, 12, 8.5), "M12 11v5.5M12 7.8v.2"],
    "out": ["M10 5H5v14h5M14 8l4 4-4 4M18 12H9"],
    "warning": ["M12 4 21 19.5H3z", "M12 10v4.5M12 17v.2"],
    "delete": ["M5 7h14M9.5 7V4.5h5V7M7 7l1 12.5h8L17 7"],
    "refresh": ["M19 12a7 7 0 1 1-2.05-4.95M19 4.5v4h-4"],
    "place": ["M12 20.5s6-5.3 6-10.5a6 6 0 0 0-12 0c0 5.2 6 10.5 6 10.5z", circ(12, 10, 2)],
    "album": [circ(12, 12, 8.5), circ(12, 12, 2)],
    "photos": ["M4 6h16v12H4z", "M4 15.5l4.5-4 3.5 3 3-2.5 5 4", "M14.5 9.5h.01"],
    "note": ["M9 18V6l10-2v12", circ(7, 18, 2), circ(17, 16, 2)],
    "spark": ["M12 4v4M12 16v4M4 12h4M16 12h4M7 7l2 2M15 15l2 2M7 17l2-2M15 9l2-2"],
    "grid": ["M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z"],
}
FILLED = {"play", "pause", "next", "prev", "more"}
KOTLIN = {"home": "Home", "disc": "Disc", "lib": "Lib", "search": "Search", "play": "Play", "pause": "Pause", "next": "Next", "prev": "Previous",
          "dl": "Download", "gear": "Gear", "more": "More", "chev": "Chevron", "back": "Back", "down": "Down", "up": "Up", "radio": "Radio", "get": "Get",
          "heart": "Heart", "bookmark": "Bookmark", "check": "Check", "close": "Close", "ban": "Ban", "queue": "Queue", "qadd": "QueueAdd",
          "shuffle": "Shuffle", "repeat": "Repeat", "repeat1": "RepeatOne", "quote": "Quote", "tune": "Tune", "swap": "Swap", "sun": "Sun",
          "server": "Server", "wave": "Wave", "sort": "Sort", "plus": "Plus", "minus": "Minus", "path": "Paths", "info": "Info", "out": "SignOut",
          "warning": "Warning", "delete": "Delete", "refresh": "Refresh", "place": "Place", "album": "Album", "photos": "Photos", "note": "MusicNote",
          "spark": "Spark", "grid": "Grid"}


def ic(n, c=""):
    return (f'<svg class="ic {"f " if n in FILLED else ""}{c}" viewBox="0 0 24 24" aria-hidden="true">'
            + "".join(f'<path d="{d}"/>' for d in ICONS[n]) + "</svg>")


def write_icons(out_dir, obj, stroke, cap, join, note):
    """SVG files plus <obj>.kt.txt, a ready Kotlin object with the same stroked/filled builder as ArtIcons."""
    d = os.path.join(out_dir, "icons")
    os.makedirs(d, exist_ok=True)
    for n, paths in ICONS.items():
        attrs = ('fill="currentColor"' if n in FILLED else
                 f'fill="none" stroke="currentColor" stroke-width="{stroke}" stroke-linecap="{cap}" stroke-linejoin="{join}"')
        open(os.path.join(d, n + ".svg"), "w").write(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" {attrs}>'
            + "".join(f'<path d="{p}"/>' for p in paths) + "</svg>\n")
    lines = [f"// Generated by the theme's _src/build.py from docs/design/_kit/kit.py ICONS. {note}",
             f"// Builder: as ArtIcons, with strokeLineWidth = {stroke}f, StrokeCap.{cap.capitalize()}, StrokeJoin.{join.capitalize()}.",
             f"object {obj} {{"]
    for n, paths in ICONS.items():
        lines.append(f'    val {KOTLIN[n]} = {"filled" if n in FILLED else "stroked"}("{n}",')
        lines += [f'        "{p}",' for p in paths]
        lines.append("    )")
    lines.append("}")
    open(os.path.join(d, f"{obj}.kt.txt"), "w").write("\n".join(lines) + "\n")

# ------------------------------------------------------------------------------------------------ contrast (PaletteTest maths)

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
    return {k + "Dim": hexs(lerp(p["surface"], p[src], 0.10)) for k, src in
            [("accent", "accent"), ("ok", "ok"), ("caution", "caution"), ("danger", "chartRedText"), ("info", "info")]}


def palette_checks(p):
    """The rules PaletteTest applies to every palette, plus control/onControl/mat (Gallery roles, already in Palette)."""
    d = dims(p)
    out = []
    for bg_name in ("ink", "surface", "raised", "rail"):
        for role in ("text", "textMuted", "chartRedText", "caution", "ok"):
            out.append((f"{role} on {bg_name}", ratio(p[role], p[bg_name]), 4.5))
        out.append((f"control on {bg_name}", ratio(p["control"], p[bg_name]), 4.5))
    out.append(("text on mat", ratio(p["text"], p["mat"]), 4.5))
    out.append(("onAccent on accent", ratio(p["onAccent"], p["accent"]), 4.5))
    out.append(("onControl on control", ratio(p["onControl"], p["control"]), 4.5))
    out.append(("text on accentDim", ratio(p["text"], d["accentDim"]), 4.5))
    for bg_name in ("ink", "surface"):
        out.append((f"accent on {bg_name} (used as text)", ratio(p["accent"], p[bg_name]), 4.5))
        out.append((f"edgeStrong on {bg_name}", ratio(p["edgeStrong"], p[bg_name]), 3.0))
    if p["light"]:
        worst = min(ratio(p["textMuted"], pastel(colorsys.hsv_to_rgb(h / 360, 0.85, 0.4))) for h in range(0, 360, 15))
        out.append(("textMuted on every pastel wash", worst, 4.5))
    return out, d


def run_checks(palettes, extra):
    """extra(p) -> list of (name, ratio, needed) for the theme's own roles. Prints a line per palette; returns failures."""
    bad = 0
    for p in palettes:
        rows, d = palette_checks(p)
        rows += extra(p)
        worst = min(rows, key=lambda r: r[1] / r[2])
        fails = [r for r in rows if r[1] < r[2]]
        bad += len(fails)
        print(f"{p['id']:<20} {len(rows)} checks, lowest {worst[0]} {worst[1]:.2f}:1 (needs {worst[2]})"
              + ("" if not fails else "  FAIL: " + "; ".join(f"{n} {v:.2f}" for n, v, _ in fails)))
        print("    dims: " + ", ".join(f"{k} {v}" for k, v in d.items()))
    return bad

# ------------------------------------------------------------------------------------------------ pages

def frame(caption, body, data_p="", cls=""):
    return (f'<figure class="fr"><figcaption>{caption}</figcaption>'
            f'<div class="scr {cls}" {f"data-p={chr(34)}{data_p}{chr(34)}" if data_p else ""}>{body}</div></figure>')


def page(title, head, frames, wide=False):
    """A board of frames, 360x780 each, left to right. head: <link>/<style> lines for the theme."""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
{head}
<style>
body{{margin:0;background:#E9E9E6;font-family:system-ui,sans-serif}}
.board{{display:flex;gap:40px;padding:56px 40px 40px;align-items:flex-start;{'flex-wrap:wrap;' if wide else ''}}}
.board>h1{{position:absolute;top:14px;left:40px;margin:0;font:600 18px system-ui;color:#222}}
.fr{{margin:0;display:flex;flex-direction:column;gap:10px}}
.fr figcaption{{font:500 13px/1.3 system-ui;color:#333;max-width:{FRAME_W}px}}
.scr{{width:{FRAME_W}px;height:{FRAME_H}px;position:relative;overflow:hidden;box-shadow:0 0 0 1px rgba(0,0,0,.12),0 20px 40px -24px rgba(0,0,0,.45);border-radius:22px}}
</style></head><body><div class="board"><h1>{title}</h1>{"".join(frames)}</div></body></html>"""


def write_page(pages_dir, name, html, n_frames, png=True, rows=1, width=None):
    os.makedirs(pages_dir, exist_ok=True)
    path = os.path.join(pages_dir, name + ".html")
    open(path, "w").write(html)
    if not png or not os.path.exists(CHROME):
        return
    w = width or (40 + n_frames * (FRAME_W + 40))
    h = 56 + rows * (FRAME_H + 70) + 20
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--virtual-time-budget=4000", f"--window-size={w},{h}", f"--screenshot={os.path.join(pages_dir, name + '.png')}",
                    "file://" + path], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
