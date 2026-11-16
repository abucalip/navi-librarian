#!/usr/bin/env python3
"""Writes the Gallery theme mockups, the icon files and the generated palette CSS, and renders a PNG beside each page.

    python3 build.py              # everything
    python3 build.py home player  # named pages only

Design tooling only: nothing imports it and no test collects it. Inputs: ../tokens.json (colours, type, motion)
and ../gallery.css (component looks). Outputs: ../palettes.css, ../icons/*.svg, ../icons/GalleryIcons.kt.txt,
../pages/<name>.html and .png. PNGs need Google Chrome at its default macOS path; the HTML is written either way.
Spec: docs/GALLERY_THEME.md.
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
PAGES_DIR = os.path.join(OUT, "pages")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TOKENS = json.load(open(os.path.join(OUT, "tokens.json")))
FONTS = ("https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:ital,opsz,wght@0,9..144,300..600;"
         "1,9..144,300..600&family=Manrope:wght@400..800&display=swap")

# ------------------------------------------------------------------------------------------------ icons
# 24 by 24, stroked 1.4 with round caps and joins unless listed in FILLED. Circles are written as two arcs so
# Android's PathParser reads every icon as plain path data. Names match ui/common/ArtIcons.kt where one exists.
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
    "dl": ["M12 4v10.5M7.5 10 12 14.5 16.5 10M5 19.5h14"],
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
}
FILLED = {"play", "pause", "next", "prev", "more"}
# Gallery name -> ArtIcons property, so the Kotlin file mirrors the existing object one for one.
KOTLIN = {"home": "Home", "disc": "Disc", "lib": "Lib", "search": "Search", "play": "Play", "pause": "Pause", "next": "Next", "prev": "Previous",
          "dl": "Download", "gear": "Gear", "more": "More", "chev": "Chevron", "back": "Back", "down": "Down", "up": "Up", "radio": "Radio", "get": "Get",
          "heart": "Heart", "bookmark": "Bookmark", "check": "Check", "close": "Close", "ban": "Ban", "queue": "Queue", "qadd": "QueueAdd",
          "shuffle": "Shuffle", "repeat": "Repeat", "repeat1": "RepeatOne", "quote": "Quote", "tune": "Tune", "swap": "Swap", "sun": "Sun",
          "server": "Server", "wave": "Wave", "sort": "Sort", "plus": "Plus", "minus": "Minus", "path": "Paths", "info": "Info", "out": "SignOut",
          "warning": "Warning", "delete": "Delete", "refresh": "Refresh", "place": "Place", "album": "Album", "photos": "Photos", "note": "MusicNote"}


def ic(n, c=""):
    return f'<svg class="ic {"f " if n in FILLED else ""}{c}" viewBox="0 0 24 24" aria-hidden="true">' + "".join(f'<path d="{d}"/>' for d in ICONS[n]) + "</svg>"


def write_icons():
    d = os.path.join(OUT, "icons")
    os.makedirs(d, exist_ok=True)
    for n, paths in ICONS.items():
        attrs = 'fill="currentColor"' if n in FILLED else 'fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"'
        open(os.path.join(d, n + ".svg"), "w").write(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" {attrs}>' + "".join(f'<path d="{p}"/>' for p in paths) + "</svg>\n")
    lines = ["// Generated by docs/design/gallery/_src/build.py from the ICONS table. Copy into ui/common/GalleryIcons.kt (spec section 6).",
             "// Same builder as ArtIcons with strokeLineWidth = 1.4f; property names match ArtIcons, plus Ban, RepeatOne and MusicNote.",
             "object GalleryIcons {"]
    for n, paths in ICONS.items():
        kind = "filled" if n in FILLED else "stroked"
        lines.append(f'    val {KOTLIN[n]} = {kind}("{n}",')
        lines += [f'        "{p}",' for p in paths]
        lines.append("    )")
    lines.append("}")
    open(os.path.join(d, "GalleryIcons.kt.txt"), "w").write("\n".join(lines) + "\n")

# ------------------------------------------------------------------------------------------------ palettes css

def write_palette_css():
    out = ["/* Generated by _src/build.py from tokens.json. Do not edit by hand. Day 1 (gallery) is the default. */"]
    for p in TOKENS["palettes"]:
        sel = ":root,[data-p=\"gallery\"]" if p.get("default") else f'[data-p="{p["id"]}"]'
        roles = ["rail", "ink", "surface", "raised", "edge", "edgeStrong", "text", "textMuted", "accent", "onAccent", "control", "onControl", "mat",
                 "chartRed", "chartRedText", "ok", "caution", "info", "chart2", "chart3"]
        v = ";".join(f"--{r}:{p[r]}" for r in roles)
        s = p["shadowRgb"]
        if p["light"]:
            sh = f"--shadowL:0 1px 2px rgba({s},.08),0 26px 36px -24px rgba({s},.5);--shadowS:0 1px 2px rgba({s},.08),0 12px 18px -12px rgba({s},.45)"
        else:
            sh = "--shadowL:0 30px 40px -22px rgba(0,0,0,.9);--shadowS:0 14px 20px -12px rgba(0,0,0,.85)"
        spot = f"radial-gradient(60% 55% at 50% 45%,rgba({p['spot']}),transparent 70%)" if p.get("spot") else "none"
        out.append(f"{sel}{{{v};{sh};--spot:{spot}}}")
    open(os.path.join(OUT, "palettes.css"), "w").write("\n".join(out) + "\n")

# ------------------------------------------------------------------------------------------------ helpers

def cv(k): return f'<i class="cv c-{k}"></i>'
def pr(k, w, c=""): return f'<div class="print {c}" style="width:{w}px">{cv(k)}</div>'
def ph(k, c=""): return f'<i class="ph p-{k} {c}"></i>'
def btn(label, c="", icon=None): return f'<span class="btn {c}">{ic(icon) if icon else ""}{label}</span>'
def ghost(label, icon=None): return f'<span class="btn g">{ic(icon) if icon else ""}<u>{label}</u></span>'
def src(names, on=0): return '<div class="src">' + "".join(f'<span class="{"on" if i == on else ""}">{n}</span>' for i, n in enumerate(names)) + "</div>"
def tabs(names, on=0, style=""): return f'<div class="tabs" style="{style}">' + "".join(f'<span class="{"on" if i == on else ""}">{n}</span>' for i, n in enumerate(names)) + "</div>"
def sh(title, link=""): return f'<div class="sh"><h3>{title}</h3>{f"<a>{link}</a>" if link else ""}</div>'
def sec(title, body, link="", style=""): return f'<section class="sec" style="{style}">{sh(title, link)}{body}</section>'
def row(lead, title, sub="", trail="", work=False):
    t = f'<span class="wt s el">{title}</span>' if work else f'<b class="el">{title}</b>'
    return f'<div class="row{"" if lead else " two"}">{lead}<span class="t">{t}{f"<small class=el>{sub}</small>" if sub else ""}</span>{trail}</div>'
def lead_ic(n): return f'<span class="lead-ic">{ic(n)}</span>'
def sw(on=True): return f'<i class="sw{" on" if on else ""}"></i>'
def status(): return '<div class="status"><span>21:14</span><span>5G · 82%</span></div>'
def top(): return f'<div class="top"><span class="wm sp">discair</span><span class="ib">{ic("dl")}<b class="bdg">2</b></span><span class="ib">{ic("gear")}</span></div>'
def bar(title="", right=None):
    r = right if right is not None else f'<span class="ib">{ic("more")}</span>'
    return f'<div class="bar"><span class="ib">{ic("back")}</span><span class="eb sp">{title}</span>{r}</div>'
def head(eyebrow, title, sub=""): return f'<div class="head"><span class="eb">{eyebrow}</span><h1 class="lt">{title}</h1>{f"<p class=\'mut sm\' style=\'margin:4px 0 0\'>{sub}</p>" if sub else ""}</div>'
def steps(stage, bad=False):
    names = ["Found", "Downloading", "Importing", "In library"]
    segs = "".join(f'<i class="{"bad" if bad and i == stage else "on" if i <= stage else ""}"></i>' for i in range(4))
    return f'<div class="stp">{segs}</div><div class="stpn">' + "".join(f'<span class="eb">{n}</span>' for n in names) + "</div>"

MINI = (f'<div class="mini"><i class="prog" style="width:33%"></i><div class="print s">{cv("laughing")}</div><span class="t"><span class="wt">After the Flood</span>'
        f'<small>Talk Talk</small></span><span class="ib">{ic("pause")}</span></div>')
def nav(on=0):
    items = [("home", "Home"), ("disc", "Discover"), ("lib", "Library"), ("search", "Search")]
    return '<div class="nav">' + "".join(f'<span class="{"on" if i == on else ""}">{ic(n)}{l}</span>' for i, (n, l) in enumerate(items)) + "</div>"

def frame(caption, body, dock=0, over="", scroll=0, data_p=""):
    """dock: a tab index (0-3) draws the mini player and the bar; 'mini' the mini player only; None nothing. scroll: px the content is moved up."""
    d = "" if dock is None else f'<div class="dock">{MINI}{"" if dock == "mini" else nav(dock)}</div>'
    inner = f'<div style="margin-top:-{scroll}px">{body}</div>' if scroll else body
    dp = f' data-p="{data_p}"' if data_p else ""
    return f'<figure><figcaption>{caption}</figcaption><div class="phone"{dp}><div class="scr">{status()}{inner}</div>{d}{over}</div></figure>'

# ------------------------------------------------------------------------------------------------ Home

def pick_hero(k, eyebrow, pager, title, by, meta, acts):
    return (f'<div class="hero">{pr(k, 246)}</div><div class="plac"><div class="plac-row"><span class="eb">{eyebrow}</span>'
            f'<span class="pager">{ic("back", "s")}<span class="eb">{pager}</span>{ic("chev", "s")}</span></div>'
            f'<h2 class="wt l" style="margin-top:4px">{title}</h2><p class="by">{by}</p><p class="mut sm">{meta}</p></div><div class="acts">{acts}</div>')

PICK_ACTS = f'{btn("Get album", "", "get")}{ghost("Save", "bookmark")}<span class="ib" style="margin-left:auto">{ic("more")}</span>'
PLAY_ACTS = f'{btn("Play", "", "play")}{ghost("Shuffle", "shuffle")}<span class="ib" style="margin-left:auto">{ic("more")}</span>'

def played_lately():
    return sec("Played lately", '<div class="g2">' + "".join(
        f'<div class="cap">{pr(k, 151, "s")}<span class="wt s el">{t}</span><small>{a}</small></div>'
        for k, t, a in [("laughing", "Laughing Stock", "Talk Talk, 1991"), ("spirit", "Spirit of Eden", "Talk Talk, 1988")]) + "</div>", "All")

def artists():
    return sec("Artists you return to", '<div class="hs">' + "".join(
        f'<div class="art">{ph(k)}<b>{n}</b><span class="eb">{c}</span></div>'
        for k, n, c in [("tt", "Talk Talk", "5 albums"), ("ac", "Alice Coltrane", "6 albums"), ("bn", "The Blue Nile", "4 albums")]) + "</div>", "All")

def radio_section():
    plates = "".join(
        f'<div class="st{" on" if i == 0 else ""}"><div class="print s"><i class="logo {l}">{s}</i></div><b>{n}</b><span class="eb">{w}</span></div>'
        for i, (l, s, n, w) in enumerate([("l1", "FIP", "FIP", "Today"), ("l2", "NTS", "NTS 1", "Yesterday"), ("l3", "KEXP", "KEXP", "Friday"), ("l4", "RP", "Radio Paradise", "2 Nov")]))
    heard = ('<div style="margin-top:20px"><span class="eb">Heard on FIP this morning</span><div style="border-top:1px solid var(--edge);margin-top:6px">'
             + row(pr("heaven", 48, "s"), "Iceblink Luck", "Cocteau Twins · 08:42", '<span class="state ok">In library</span>', True)
             + row(pr("hats", 48, "s"), "The Downtown Lights", "The Blue Nile · 08:17", btn("Get", "o sm", "get"), True) + "</div></div>")
    return sec("Radio", f'<div class="stations">{plates}</div>{heard}', "All stations")

def this_week():
    body = (f'<div style="display:flex;gap:16px;align-items:flex-start">{pr("closer", 96, "s")}<div class="sp"><span class="eb acc">Anniversary</span>'
            f'<p class="wt m" style="margin-top:6px">Closer turns 45 this week</p><p class="mut sm" style="margin:4px 0 0">Joy Division · in your library, last played in March</p></div></div>'
            f'<div class="acts left" style="margin:14px 0 0">{btn("Play", "sm", "play")}{ghost("Why this?")}</div>')
    return sec("This week", body)

def arrivals():
    return sec("Arrivals", '<div style="border-top:0">' + row(pr("pyg", 48, "s"), "Pygmalion", "Slowdive · downloading, 64%", f'<span class="ib">{ic("chev")}</span>', True)
               + row(pr("hats", 48, "s"), "Hats", "The Blue Nile · in your library today", '<span class="state ok">New</span>', True) + "</div>", "Downloads")

def genres():
    return sec("Genres", '<p class="genres">Post-rock<i class="sl">/</i>Dream pop<i class="sl">/</i>Ambient<i class="sl">/</i><em>Spiritual jazz</em><i class="sl">/</i>Sophisti-pop</p>', "All")

STAT = f'<div class="stat"><span class="eb">1,284 albums · 312 artists · 46 h this month</span>{ic("chev", "s")}</div>'

def home_full(source=0):
    if source == 2:
        hero = pick_hero("laughing", "Played an hour ago", "01 / 30", "Laughing Stock", "Talk Talk, 1991", "Post-rock · 6 songs · 43 min", PLAY_ACTS)
    elif source == 1:
        hero = pick_hero("hats", "New in your library", "01 / 12", "Hats", "The Blue Nile, 1989", "Sophisti-pop · arrived today", PLAY_ACTS)
    else:
        hero = pick_hero("hex", "Pick for tonight", "01 / 12", "Hex", "Bark Psychosis, 1994", "Post-rock · not in your library", PICK_ACTS)
    return top() + src(["Picks", "New", "Played"], source) + hero + played_lately() + artists() + radio_section() + this_week() + arrivals() + genres() + STAT + '<div style="height:140px"></div>'

def home():
    states = (top() + f'<div class="banner">{ic("info")}<p>ListenBrainz is not answering. Picks may be out of date.</p><a class="lk sm">Server</a></div>'
              + src(["Picks", "New", "Played"], 0)
              + '<div class="hero"><div class="print" style="width:246px"><i class="sk" style="aspect-ratio:1"></i></div></div>'
              + '<div class="plac"><i class="sk" style="width:110px;height:12px"></i><i class="sk" style="width:150px;height:28px;margin-top:8px"></i><i class="sk" style="width:190px;height:14px;margin-top:6px"></i></div>'
              + sec("Artists you return to", '<p class="mut sm" style="margin:0">Play a few albums and the artists you come back to are hung here.</p>'))
    return [("1 · Home, first screen (Picks)", home_full(0), 0, "", 0),
            ("2 · Scrolled: Played lately, Artists you return to, Radio", home_full(0), 0, "", 600),
            ("3 · Scrolled further: Radio (new section), This week", home_full(0), 0, "", 1190),
            ("4 · End of Home: Arrivals, Genres, the library line", home_full(0), 0, "", 1640),
            ("5 · Played selected", home_full(2), 0, "", 0),
            ("6 · Picks loading, one service failing, no listening yet", states, 0, "", 0)]

# ------------------------------------------------------------------------------------------------ Album, Artist, Genre

TRACKS = [("Myrrhman", "5:33"), ("Ascension Day", "6:00"), ("After the Flood", "9:39"), ("Taphead", "7:39"), ("New Grass", "9:40"), ("Runeii", "4:58")]
BARS = '<span class="bars"><i></i><i></i><i></i></span>'

def tracklist(playing=2):
    return '<ol class="trk-list">' + "".join(
        f'<li class="{"on" if i == playing else ""}"><span class="n">{BARS if i == playing else i + 1}</span><span class="tt el">{t}</span><span class="d">{d}</span>'
        f'<span class="ib">{ic("more")}</span></li>' for i, (t, d) in enumerate(TRACKS)) + "</ol>"

def album_pages():
    owned = (bar("Album") + f'<div class="hero">{pr("laughing", 228)}</div>'
             + '<div class="plac left"><span class="eb">1991 · Verve · 6 songs · 43 min · FLAC</span><h1 class="wt xl" style="margin-top:4px">Laughing Stock</h1>'
             + '<p class="by"><a class="lk" style="color:var(--text)">Talk Talk</a> · Post-rock</p></div>'
             + f'<div class="acts left">{btn("Play", "", "play")}{ghost("Shuffle", "shuffle")}{ghost("Paths", "path")}</div>'
             + f'<div style="margin-top:24px">{tabs(["Songs", "Info", "Reviews", "Booklet"])}</div>' + tracklist()
             + sec("Similar albums", '<div class="hs">' + "".join(pr(k, 104, "s") for k in ("spirit", "hats", "hex")) + "</div>"))
    missing = (bar("Album") + f'<div class="hero">{pr("hex", 228)}</div>'
               + '<div class="plac left"><span class="eb">1994 · Circa · Post-rock</span><h1 class="wt xl" style="margin-top:4px">Hex</h1>'
               + '<p class="by"><a class="lk" style="color:var(--text)">Bark Psychosis</a></p></div>'
               + f'<div class="acts left">{btn("Get album", "", "get")}{ghost("Save", "bookmark")}{ghost("Paths", "path")}</div>'
               + f'<div class="note"><span class="ib" style="width:24px;height:24px">{ic("info")}</span><p class="sm" style="margin:0">Not in your library. Get it and its songs are listed here.</p></div>'
               + f'<div style="margin-top:20px">{tabs(["Info", "Reviews"])}</div>'
               + '<p class="sm" style="margin:14px 20px 0;max-width:300px">Recorded in a disused church in Stratford. Quiet, long-form songs that sit between jazz, dub and rock.</p>'
               + sec("Why this pick", '<p class="sm mut" style="margin:0">You play Laughing Stock, Spirit of Eden and Hats often. Listeners of all three return to Hex.</p>'))
    artist = (bar("Artist") + '<div class="hero" style="padding-top:8px"><div class="print" style="width:200px">' + ph("tt") + "</div></div>"
              + '<div class="plac left"><span class="eb">5 albums in your library · 1981 to 1991</span><h1 class="wt xl" style="margin-top:4px">Talk Talk</h1>'
              + '<p class="mut sm" style="margin:2px 0 0">Art pop, Post-rock</p></div>'
              + f'<div class="acts left">{btn("Play", "", "play")}{ghost("Shuffle", "shuffle")}{ghost("Paths", "path")}</div>'
              + sec("Top songs", '<div class="rows" style="padding:0">' + row(pr("laughing", 48, "s"), "After the Flood", "Laughing Stock", f'<span class="ib">{ic("more")}</span>', True)
                    + row(pr("spirit", 48, "s"), "I Believe in You", "Spirit of Eden", f'<span class="ib">{ic("more")}</span>', True)
                    + row(pr("colour", 48, "s"), "Life's What You Make It", "The Colour of Spring", f'<span class="ib">{ic("more")}</span>', True) + "</div>", "All top songs")
              + sec("In your library", '<div class="g2">' + "".join(f'<div class="cap">{pr(k, 151, "s")}<span class="wt s el">{t}</span><small>{y}</small></div>'
                                                                       for k, t, y in [("laughing", "Laughing Stock", "1991"), ("spirit", "Spirit of Eden", "1988")]) + "</div>"))
    genre = (bar("Genre") + head("86 albums · 41 artists in your library", "Ambient") + f'<div style="margin-top:16px">{tabs(["Albums", "Artists"])}</div>'
             + '<div class="g2" style="padding:20px 20px 0">' + "".join(f'<div class="cap">{pr(k, 151, "s")}<span class="wt s el">{t}</span><small>{a}</small></div>'
                                                                   for k, t, a in [("promises", "Promises", "Floating Points, 2021"), ("pyg", "Pygmalion", "Slowdive, 1995"),
                                                                                   ("satch", "Journey in Satchidananda", "Alice Coltrane, 1971"), ("vesp", "Vespertine", "Björk, 2001")]) + "</div>")
    return [("1 · Album, owned, third song playing", owned, "mini"), ("2 · Album, not in the library", missing, "mini"),
            ("3 · Artist", artist, "mini"), ("4 · Genre", genre, "mini")]

# ------------------------------------------------------------------------------------------------ Player

def np_head(title): return f'<div class="bar"><span class="ib">{ic("down")}</span><span class="eb sp">{title}</span><span class="ib">{ic("more")}</span></div>'
SEEK = '<div class="seek"><div class="ln"><i style="width:33%"></i><b style="left:33%"></b></div><div class="t"><span class="num mut">3:12</span><span class="num mut">−6:27</span></div></div>'
TRANS = (f'<div class="trans"><span class="ib">{ic("shuffle", "l")}</span><span class="ib">{ic("prev", "l")}</span><span class="play">{ic("pause")}</span>'
         f'<span class="ib">{ic("next", "l")}</span><span class="ib">{ic("repeat", "l")}</span></div>')
TOOLS = '<div class="tools">' + "".join(f'<span>{ic(i)}{l}</span>' for i, l in [("quote", "Lyrics"), ("queue", "Queue"), ("tune", "Equalizer"), ("swap", "Crossfade")]) + "</div>"

def player():
    np = ('<div class="npc">' + np_head("Playing from Laughing Stock") + f'<div class="hero" style="padding-top:14px">{pr("laughing", 300, "np")}</div>'
          + '<div class="np-cap"><div class="sp"><h1 class="wt l el">After the Flood</h1><p class="by">Talk Talk — <em>Laughing Stock</em></p></div><span class="tag">FLAC 16/44.1</span></div>'
          + SEEK + TRANS + TOOLS + "</div>")
    q = ('<div class="npc">' + np_head("Queue") + f'<div class="rows" style="padding-top:4px">{row(pr("laughing", 56, "s"), "After the Flood", "Talk Talk · playing, 3:12 of 9:39", BARS, True)}</div>'
         + sec("Next · 5 songs", '<div class="rows" style="padding:0">' + "".join(row(pr(k, 48, "s"), n, a, f'<span class="ib">{ic("close", "s")}</span>', True)
                                                   for k, n, a in [("laughing", "Taphead", "Talk Talk"), ("laughing", "New Grass", "Talk Talk"), ("laughing", "Runeii", "Talk Talk"),
                                                                   ("hats", "The Downtown Lights", "The Blue Nile")]) + "</div>", "Clear", "padding-top:18px")
         + f'<div class="acts left" style="margin-top:6px">{btn("Add songs that sound like this", "o", "wave")}</div>' + '<div style="margin-top:auto"></div>' + SEEK + TRANS + '<div style="height:20px"></div></div>')
    ly = ('<div class="npc">' + np_head("Lyrics") + f'<div class="rows">{row(pr("laughing", 48, "s"), "After the Flood", "Talk Talk", f"<span class=\'sm mut\' style=\'display:flex;gap:8px;align-items:center\'>Photos {sw(True)}</span>", True)}</div>'
          + '<div class="lyr"><p class="was">Stand-in line one, already sung</p><p class="was">Stand-in line two, already sung</p><p class="on">The line being sung, in italic ink</p>'
          + '<p>The next line, waiting</p><p>And the one after it</p></div><div style="margin-top:auto"></div>' + SEEK + TRANS + '<div style="height:20px"></div></div>')
    return [("1 · Now Playing", np, None), ("2 · Queue", q, None), ("3 · Lyrics (stand-in text)", ly, None)]

# ------------------------------------------------------------------------------------------------ Discover

def entry(n, k, title, artist, why, genre):
    return (f'<div style="display:grid;grid-template-columns:104px 1fr;gap:16px;align-items:start;padding:18px 0;border-bottom:1px solid var(--edge)">{pr(k, 104, "s")}'
            f'<div style="min-width:0"><span class="eb">No. {n:02d} · {genre}</span><h3 class="wt m el" style="margin-top:4px">{title}</h3><p class="sm" style="margin:2px 0 0">{artist}</p>'
            f'<p class="sm mut" style="margin:6px 0 0;font-style:italic;font-family:Fraunces,serif">{why}</p>'
            f'<div style="display:flex;align-items:center;gap:2px;margin-top:8px">{btn("Get", "sm", "get")}{ghost("Save")}<span class="ib" style="margin-left:auto">{ic("more")}</span></div></div></div>')

RANK = ('<div class="rank">' + "".join(f'<div><span class="sm">{n}</span><i class="{"on" if i == 0 else ""}" style="width:{w}%"></i><span class="num mut">{w // 5}%</span></div>'
                                       for i, (n, w) in enumerate([("Ambient", 85), ("Dream pop", 70), ("Post-rock", 55), ("Post-punk", 40)])) + "</div>")

def discover():
    lists = (head("Monday 16 November", "Discover") + src(["Recommendations", "New releases", "Personal"]) + '<div class="rows" style="margin-top:6px">'
             + entry(1, "hex", "Hex", "Bark Psychosis, 1994", "Because Laughing Stock keeps coming back.", "Post-rock")
             + entry(2, "satch", "Journey in Satchidananda", "Alice Coltrane, 1971", "Because you played Ptah, the El Daoud twice this week.", "Spiritual jazz")
             + entry(3, "loveless", "Loveless", "My Bloody Valentine, 1991", "Because Souvlaki is on repeat.", "Shoegaze") + "</div>")
    lists = lists.replace('<div class="src">', '<div style="margin-top:10px">' + tabs(["Lists", "Insights"]) + '</div><div class="src" style="padding-top:12px">', 1)
    ins = (head("Monday 16 November", "Discover") + f'<div style="margin-top:10px">{tabs(["Lists", "Insights"], 1)}</div>'
           + sec("Your taste · last 90 days", f'<p class="wt m" style="margin:0 0 14px">More ambient, less post-punk lately.</p>{RANK}'
                 + '<div class="stat" style="padding:14px 0 0"><span class="eb">1,240 listens of 48,912</span><a class="lk sm">Details</a></div>', "", "padding-top:22px")
           + this_week()
           + sec("Never played", f'<div style="display:flex;gap:16px">{pr("spirit", 96, "s")}<div><p class="wt m" style="margin:0">Spirit of Eden</p><p class="mut sm" style="margin:4px 0 0">Talk Talk · added in June</p>'
                 f'<div style="display:flex;gap:2px;margin-top:10px">{btn("Play", "sm", "play")}{ghost("Not now")}</div></div></div>'))
    sheet = ('<div class="scrim"></div><div class="sheet"><div class="handle"></div><span class="eb">Your taste</span><h3 class="wt l" style="margin:4px 0 12px">Ambient leads</h3>'
             + tabs(["30 days", "90 days", "All time"], 1, "margin:0 0 6px") + src(["Genres", "Decades", "Moods"]).replace('class="src"', 'class="src" style="padding:6px 0 14px"')
             + RANK + f'<div style="margin-top:20px">{btn("Make a playlist from Ambient", "wide", "play")}</div></div>')
    return [("1 · Discover, Lists", lists, 1), ("2 · Discover, Insights", ins, 1), ("3 · Taste sheet", ins, 1, sheet)]

# ------------------------------------------------------------------------------------------------ Library and Search

def library():
    art = (head("312 artists", "Library") + f'<div style="margin-top:12px">{tabs(["Artists", "Albums"])}</div>'
           + f'<div class="stat" style="padding:14px 20px 4px"><span class="eb" style="color:var(--textMuted)">By name</span><span class="btn g">{ic("sort", "s")}<u>Sort</u></span></div><div class="rows">'
           + "".join(row(f'<div class="print s" style="width:52px">{ph(k)}</div>', n, s, f'<span class="ib">{ic("chev", "s")}</span>')
                     for k, n, s in [("ac", "Alice Coltrane", "6 albums"), ("bp", "Bark Psychosis", "2 albums"), ("bn", "The Blue Nile", "4 albums"),
                                     ("ct", "Cocteau Twins", "5 albums"), ("ph", "Portishead", "3 albums"), ("sd", "Slowdive", "5 albums"), ("tt", "Talk Talk", "5 albums")]) + "</div>")
    alb = (head("1,284 albums", "Library") + f'<div style="margin-top:12px">{tabs(["Artists", "Albums"], 1)}</div>'
           + f'<div class="stat" style="padding:14px 20px 8px"><span class="eb" style="color:var(--textMuted)">Newest first</span><span class="btn g">{ic("sort", "s")}<u>Sort</u></span></div>'
           + '<div class="g2" style="padding:6px 20px 0">' + "".join(f'<div class="cap">{pr(k, 151, "s")}<span class="wt s el">{t}</span><small>{a}</small></div>'
                                                               for k, t, a in [("hats", "Hats", "The Blue Nile, 1989"), ("satch", "Journey in Satchidananda", "Alice Coltrane, 1971"),
                                                                               ("third", "Third", "Portishead, 2008"), ("laughing", "Laughing Stock", "Talk Talk, 1991")]) + "</div>")
    def grp(name, n): return f'<div class="sh" style="margin:22px 20px 4px"><span class="eb">{name}</span><span class="eb">{n}</span></div>'
    search = (head("Search", "What are you looking for?").replace('class="lt"', 'class="lt" style="font-size:26px;line-height:30px"')
              + f'<div class="field">{ic("search")}<span class="sp">talk</span>{ic("close", "s")}</div>'
              + grp("Artists", "1") + '<div class="rows">' + row(f'<div class="print s" style="width:52px">{ph("tt")}</div>', "Talk Talk", "5 albums in your library") + "</div>"
              + grp("Albums", "3") + '<div class="rows">'
              + row(pr("laughing", 48, "s"), "Laughing Stock", "Talk Talk, 1991", '<span class="state ok">In library</span>', True)
              + row(pr("spirit", 48, "s"), "Spirit of Eden", "Talk Talk, 1988", '<span class="state ok">In library</span>', True)
              + row(pr("colour", 48, "s"), "The Colour of Spring", "Talk Talk, 1986", btn("Get", "o sm", "get"), True) + "</div>"
              + grp("Songs", "2") + '<div class="rows">' + row(pr("laughing", 48, "s"), "After the Flood", "Talk Talk · Laughing Stock", f'<span class="ib">{ic("qadd")}</span>', True) + "</div>")
    return [("1 · Library, Artists", art, 2), ("2 · Library, Albums", alb, 2), ("3 · Search, results", search, 3)]

# ------------------------------------------------------------------------------------------------ Radio

def radio():
    st = [("l1", "FIP", "FIP", "Now: Life's What You Make It, Talk Talk", True), ("l2", "NTS", "NTS 1", "Live: Charlie Bones", False),
          ("l3", "KEXP", "KEXP", "Now: Sugar for the Pill, Slowdive", False), ("l6", "6", "BBC Radio 6 Music", "Live title not available", False),
          ("l4", "RP", "Radio Paradise", "Now: Roads, Portishead", False), ("l5", "WW", "Worldwide FM", "Now: Blue Nile, Alice Coltrane", False)]
    stations = (bar("Radio", '<a class="lk sm" style="padding-right:12px">Heard on radio</a>') + head("6 stations", "Radio") + '<div class="rows" style="margin-top:12px">'
                + "".join(row(f'<div class="print s" style="width:52px"><i class="logo {l}" style="font-size:13px">{s}</i></div>', n, sub,
                              (BARS if on else f'<span class="ib">{ic("heart")}</span>')) for l, s, n, sub, on in st) + "</div>")
    live = (np_head("Live radio") + f'<div class="hero" style="padding-top:14px"><div class="print np" style="width:300px"><i class="logo l1" style="font-size:72px">FIP</i></div></div>'
            + '<div class="plac left" style="margin-top:24px"><span class="eb acc">On air · FIP</span><h1 class="wt l" style="margin-top:4px">Life\'s What You Make It</h1><p class="by">Talk Talk — <em>The Colour of Spring</em></p></div>'
            + f'<div class="trans" style="justify-content:center;gap:34px;margin-top:22px"><span class="ib">{ic("heart", "l")}</span><span class="play">{ic("pause")}</span><span class="ib">{ic("queue", "l")}</span></div>'
            + f'<div class="acts left" style="margin-top:22px">{btn("Get this song", "", "get")}</div><p class="mut sm" style="margin:10px 20px 0">The Colour of Spring is not in your library.</p>')
    heard = (bar("Heard on radio", "") + head("Tonight", "Heard on radio", "Songs the stations played while you listened") + '<div class="rows" style="margin-top:12px">'
             + row(pr("colour", 48, "s"), "Life's What You Make It", "Talk Talk · FIP · 21:09", btn("Get", "o sm", "get"), True)
             + row(pr("third", 48, "s"), "Roads", "Portishead · Radio Paradise · 20:41", '<span class="state ok">In library</span>', True)
             + row(pr("souv", 48, "s"), "Sugar for the Pill", "Slowdive · KEXP · 19:58", '<span class="state">Requested</span>', True)
             + row(pr("satch", 48, "s"), "Blue Nile", "Alice Coltrane · Worldwide FM · 18:30", btn("Get", "o sm", "get"), True)
             + row('<div class="print s" style="width:48px"><i class="sk" style="aspect-ratio:1"></i></div>', "Untitled", "Artist not named · NTS 1 · 17:12", "", False) + "</div>")
    return [("1 · Radio, stations", stations, "mini"), ("2 · Live radio", live, None), ("3 · Heard on radio", heard, "mini")]

# ------------------------------------------------------------------------------------------------ Downloads, stats, server

def line_chart():
    pts = [(0, 96), (30, 90), (60, 86), (90, 78), (120, 74), (150, 64), (180, 58), (210, 46), (240, 40), (270, 30), (300, 22), (320, 14)]
    p = " ".join(f"{x},{y}" for x, y in pts)
    return (f'<svg class="chart" viewBox="0 0 320 120"><path d="M0 14h320M0 55h320M0 96h320" stroke="var(--edge)" stroke-width="1" fill="none"/>'
            f'<path d="M0 110h320" stroke="var(--edgeStrong)" stroke-width="1"/><polyline points="{p}" fill="none" stroke="var(--text)" stroke-width="1.5"/>'
            f'<circle cx="240" cy="40" r="4.5" fill="var(--accent)"/></svg>')

def col_chart():
    vals = [(18, 8), (34, 20), (62, 58), (88, 70), (74, 40), (52, 30), (40, 34)]
    out = ['<svg class="chart" viewBox="0 0 320 120"><path d="M0 110h320" stroke="var(--edgeStrong)" stroke-width="1"/>']
    for i, (a, b) in enumerate(vals):
        x = 8 + i * 45
        out.append(f'<rect x="{x}" y="{110 - a}" width="14" height="{a}" fill="var(--chart3)"/><rect x="{x + 16}" y="{110 - b}" width="14" height="{b}" fill="var(--accent)"/>')
    return "".join(out) + "</svg>"

def downloads():
    def job(k, title, sub, stage, state, acts, bad=False):
        return (f'<div style="padding:18px 0;border-bottom:1px solid var(--edge)"><div style="display:flex;gap:14px">{pr(k, 64, "s")}<div class="sp">'
                f'<h4 class="wt m el" style="font-size:19px;line-height:22px">{title}</h4><p class="sm mut" style="margin:2px 0 0">{sub}</p><p class="sm" style="margin:2px 0 0">{state}</p></div></div>'
                f'{steps(stage, bad)}<div style="display:flex;gap:4px;margin-top:12px">{acts}</div></div>')
    dl = (bar("Downloads", "") + head("2 in progress · 1 needs you", "Downloads") + '<div class="rows">'
          + job("pyg", "Pygmalion", "Slowdive · 1995", 1, "Downloading · 64% · 7 of 9 songs", btn("Skip this source", "o sm") + btn("Dismiss", "d sm"))
          + job("colour", "The Colour of Spring", "Talk Talk · 1986", 2, '<span class="dan">Import failed: two songs are missing</span>', btn("Try again", "sm", "refresh") + btn("Dismiss", "d sm"), True)
          + job("hats", "Hats", "The Blue Nile · 1989", 3, '<span class="ok">In your library · arrived today</span>', btn("Play", "sm", "play") + ghost("Open album")) + "</div>")
    stats = (bar("Library stats", "") + head("Library", "Library stats") + src(["12 months", "5 years", "All time"])
             + sec("Collection over time", f'<p style="margin:0 0 8px"><span class="numeral">1,241</span> <span class="mut sm">albums in September</span></p>{line_chart()}'
                   '<div style="display:flex;justify-content:space-between;margin-top:6px"><span class="num mut">Dec</span><span class="num mut">Jun</span><span class="num mut">Nov</span></div>', "", "padding-top:22px")
             + sec("Own and play, by decade", f'{col_chart()}<div style="display:flex;justify-content:space-around;margin-top:6px">'
                   + "".join(f'<span class="num mut">{d}</span>' for d in ["60s", "70s", "80s", "90s", "00s", "10s", "20s"])
                   + '</div><p class="sm mut" style="margin:8px 0 0">Pale: albums you own. Plum: albums you played this year.</p>')
             + sec("Shelf life", f'<p style="margin:0"><span class="numeral">96</span> <span class="mut sm">albums never played</span></p><div style="margin-top:12px">{btn("Play something unplayed", "", "play")}</div>'))
    def svc(name, state, c): return row(lead_ic("server"), name, f'<span class="{c}">{state}</span>')
    server = (bar("Server", "") + head("Checked a minute ago", "Server")
              + f'<div class="banner" style="margin-top:14px">{ic("warning")}<p>One service needs attention.</p>{btn("Check now", "o sm")}</div>'
              + sec("Services", '<div class="rows" style="padding:0">' + svc("Librarian", "Working", "ok") + svc("Navidrome", "Working", "ok") + svc("slskd", "Working", "ok")
                    + svc("ListenBrainz", "Not answering since 20:50", "cau") + svc("MusicBrainz", "Working", "ok") + "</div>", "", "padding-top:22px")
              + sec("Server activity", '<div class="rows" style="padding:0">' + row(lead_ic("wave"), "Lens refresh", "Finished 18:02 · next at 06:00")
                    + row(lead_ic("lib"), "Library resync", "Finished 03:10") + "</div>"))
    return [("1 · Downloads", dl, "mini"), ("2 · Library stats", stats, "mini"), ("3 · Server", server, "mini")]

# ------------------------------------------------------------------------------------------------ Settings

def settings():
    chev = f'<span class="ib">{ic("chev", "s")}</span>'
    s = (bar("Settings", "") + head("Discair 1.3", "Settings")
         + sec("Server", '<div class="rows" style="padding:0">' + row(lead_ic("server"), "Server and services", '<span class="cau">One service needs attention</span>', chev) + "</div>", "", "padding-top:22px")
         + sec("Look and sound", '<div class="rows" style="padding:0">' + row(lead_ic("sun"), "Appearance", "Gallery · White", chev)
               + row(lead_ic("tune"), "Equalizer", "On · Custom", chev) + row(lead_ic("swap"), "Crossfade", "6 seconds · albums stay gapless", chev) + "</div>")
         + sec("Listening", '<div class="rows" style="padding:0">' + row(lead_ic("radio"), "Radio", "Scrobble radio songs", chev)
               + row(lead_ic("wave"), "ListenBrainz", "Connected", chev) + row(lead_ic("lib"), "Resync the library nightly", "", sw(True)) + "</div>")
         + f'<div class="acts left" style="margin-top:24px">{btn("Sign out", "d", "out")}</div>')
    pals = TOKENS["palettes"]
    def swatch(p, on=False):
        return f'<div class="{"on" if on else ""}"><i><b style="background:linear-gradient(135deg,{p["ink"]} 0 58%,{p["control"]} 58% 79%,{p["accent"]} 79%)"></b></i>{p["name"]}</div>'
    ap = (bar("Appearance", "") + head("Theme and type", "Appearance") + f'<div style="margin-top:12px">{tabs(["Follow the phone", "One theme"])}</div>'
          + '<p class="sm mut" style="margin:12px 20px 0">Day theme when the phone is light, night theme when it is dark.</p>'
          + sec("Day", '<div class="swt">' + "".join(swatch(p, p["id"] == "gallery") for p in pals if p["light"]) + "</div>", "", "padding-top:20px")
          + sec("Night", '<div class="swt">' + "".join(swatch(p, p["id"] == "gallery_graphite") for p in pals if not p["light"]) + "</div>")
          + sec("Type", '<div class="rows" style="padding:0">' + row("", "Gallery", "Fraunces, Manrope and DM Mono", f'<span class="ib">{ic("check")}</span>')
                + row("", "Discair", "Peace Sans and Open Sans") + "</div>"))
    bands = [40, 55, 62, 50, 44, 50, 58, 66, 60, 48]
    eq = (bar("Equalizer", "") + head("Shapes everything you play here", "Equalizer")
          + '<div class="rows" style="margin-top:10px">' + row("", "Equalizer", "On", sw(True)) + "</div>"
          + sec("Preset", src(["Custom", "Flat", "Bass lift", "Vocal", "Night"]).replace('class="src"', 'class="src" style="padding:0;flex-wrap:wrap;gap:6px 18px"'), "", "padding-top:20px")
          + sec("Bands", '<div class="eq">' + "".join(f'<i style="--v:{b}%"></i>' for b in bands) + '</div><div style="display:flex;justify-content:space-between;margin-top:8px">'
                + "".join(f'<span class="num mut">{f}</span>' for f in ["31", "125", "500", "2k", "8k", "16k"]) + "</div>")
          + '<div class="rows" style="margin-top:16px">' + row("", "Headroom", "Automatic · −3.0 dB") + "</div>" + f'<div class="acts left">{btn("Reset to flat", "o")}</div>')
    cf = (bar("Crossfade", "") + head("Songs blend into each other", "Crossfade") + '<div class="rows" style="margin-top:10px">' + row("", "Crossfade", "On", sw(True)) + "</div>"
          + sec("Length", f'<div style="display:flex;align-items:center;justify-content:center;gap:28px">{btn(ic("minus"), "o")}<span class="numeral">6 s</span>{btn(ic("plus"), "o")}</div>'
                '<div class="prog" style="margin-top:20px"><i style="width:50%"></i></div><div style="display:flex;justify-content:space-between;margin-top:6px"><span class="num mut">1 s</span><span class="num mut">12 s</span></div>', "", "padding-top:20px")
          + sec("Fade", src(["Smooth", "Even", "Quick"]).replace('class="src"', 'class="src" style="padding:0"'))
          + sec("Albums", '<div class="rows" style="padding:0">' + row("", "Keep albums gapless", "No fade between songs of the same album", sw(True)) + "</div>"))
    return [("1 · Settings", s, "mini"), ("2 · Appearance (the eight Gallery palettes)", ap, "mini"), ("3 · Equalizer", eq, "mini"), ("4 · Crossfade", cf, "mini")]

# ------------------------------------------------------------------------------------------------ Sheets

def sheets():
    first = home_full(0)
    menu = (f'<div class="scrim"></div><div class="sheet"><div class="handle"></div><div class="sheet-hd">{pr("hex", 58, "s")}<div><span class="wt m" style="display:block">Hex</span><span class="eb">Bark Psychosis · 1994</span></div></div>'
            f'<div class="opt">{ic("info")}<span><b>Why this pick?</b><small>Three albums you play often lead here</small></span></div>'
            f'<div class="opt">{ic("close")}<span><b>Not this album</b><small>It leaves your picks</small></span></div>'
            f'<div class="opt">{ic("ban")}<span><b>Never suggest this artist</b><small>Bark Psychosis leaves every list</small></span></div></div>')
    song = (f'<div class="scrim"></div><div class="sheet"><div class="handle"></div><div class="sheet-hd">{pr("laughing", 58, "s")}<div><span class="wt m" style="display:block">Taphead</span><span class="eb">Talk Talk · Laughing Stock · 7:39</span></div></div>'
            + "".join(f'<div class="opt">{ic(i)}<span><b>{t}</b></span></div>' for i, t in [("play", "Play next"), ("qadd", "Add to queue"), ("wave", "Songs that sound like this"),
                                                                                            ("path", "Paths from this song"), ("album", "Go to album"), ("dl", "Keep on this phone")]) + "</div>")
    confirm = ('<div class="scrim"></div><div class="sheet"><div class="handle"></div><span class="eb">Downloads</span><h3 class="wt l" style="margin:4px 0 10px">Dismiss this download?</h3>'
               '<p class="sm" style="margin:0 0 20px">The Colour of Spring leaves the list. Files already downloaded are removed; nothing in your library changes.</p>'
               f'<div style="display:grid;gap:10px">{btn("Keep it", "o wide")}{btn("Dismiss the download", "d wide")}</div></div>')
    snack = '<div class="snack" style="bottom:134px"><span>Hex will not be suggested again.</span><u>Undo</u></div>'
    return [("1 · Pick menu (the three dots)", first, 0, menu), ("2 · Song menu", album_pages()[0][1], "mini", song),
            ("3 · Confirmation (Dismiss)", downloads()[0][1], "mini", confirm), ("4 · Snackbar with Undo, above the mini player", first, 0, snack)]

# ------------------------------------------------------------------------------------------------ Palettes (colour variations only)

def palettes():
    frames = []
    for p in TOKENS["palettes"]:
        kind = "Day" if p["light"] else "Night"
        frames.append((f'{kind} · {p["name"]} ({p["id"]})', home_full(0), 0, "", 0, p["id"]))
    for p in TOKENS["palettes"]:
        kind = "Day" if p["light"] else "Night"
        frames.append((f'{kind} · {p["name"]}, Radio section', home_full(0), 0, "", 1190, p["id"]))
    return frames

# ------------------------------------------------------------------------------------------------ Components board

def components():
    roles = ["ink", "rail", "surface", "mat", "raised", "edge", "edgeStrong", "text", "textMuted", "control", "onControl", "accent", "onAccent", "ok", "caution", "chartRedText", "info"]
    sw_ = "".join(f'<div style="display:grid;gap:4px;font-size:11px"><i style="display:block;height:38px;background:var(--{r});box-shadow:inset 0 0 0 1px rgba(127,127,127,.3)"></i>'
                  f'<b>{r}</b><span class="num mut" style="font-size:10.5px">{TOKENS["palettes"][0][r]}</span></div>' for r in roles)
    t = TOKENS["type"]
    def spec(k): v = t[k]; return f'{v["face"]} {v["weight"]}, {v["size"]}/{v["line"]}'
    type_ = ('<div style="display:grid;gap:10px">'
             f'<span class="wm">discair</span><span class="eb">wordmark · {spec("wordmark")}</span>'
             f'<span class="lt">Library</span><span class="eb">large title · {spec("largeTitle")}</span>'
             f'<span class="wt xl">Laughing Stock</span><span class="eb">work title XL · {spec("workTitleXL")}</span>'
             f'<span class="wt l">After the Flood</span><span class="eb">work title · {spec("workTitle")}</span>'
             f'<div class="sh" style="margin:0"><h3>Artists you return to</h3><a>All</a></div><span class="eb">section heading · {spec("sectionHeading")}</span>'
             f'<span class="wt s">Spirit of Eden</span><span class="eb">row work · {spec("rowWork")}</span>'
             f'<b style="font-size:15px">Row title</b><span class="eb">row title · {spec("rowTitle")}</span>'
             f'<p class="by">Body text for notes and sheets.</p><span class="eb">body · {spec("body")}</span>'
             f'<span class="eb" style="color:var(--text)">1991 · Verve · 6 songs · 43 min</span><span class="eb">catalogue · {spec("catalogue")}, caps, +0.07em</span>'
             f'<span style="font:400 19px Fraunces;font-variant-numeric:oldstyle-nums" class="mut">1 2 3 4 5 6 7 8 9 10</span><span class="eb">track numbers · old-style figures</span>'
             f'<span class="numeral">1,284</span><span class="eb">numeral · {spec("numeral")}</span></div>')
    ctr = ('<div style="display:grid;gap:16px;align-content:start">'
           f'<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">{btn("Get album", "", "get")}{ghost("Save", "bookmark")}{btn("Shuffle", "o", "shuffle")}{btn("Dismiss", "d")}</div>'
           f'<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">{btn("Get", "sm", "get")}{btn("Get", "o sm", "get")}<span class="state ok">In library</span><span class="state">Requested</span><span class="tag">FLAC 16/44.1</span><span class="tag acc">On air</span></div>'
           + src(["Picks", "New", "Played"]).replace('class="src"', 'class="src" style="padding:0"') + tabs(["Songs", "Info", "Reviews"], 0, "margin:0")
           + f'<div class="field" style="margin:0">{ic("search")}<span class="sp mut">Search your library</span></div>'
           f'<div style="display:flex;gap:14px;align-items:center">{sw(True)}{sw(False)}<span class="bars"><i></i><i></i><i></i></span><span class="bdg" style="position:static">2</span></div>'
           f'<div>{steps(1)}</div><div class="seek" style="margin:0">' + SEEK[18:]
           + f'<div class="trans" style="margin:0;justify-content:flex-start;gap:20px"><span class="ib">{ic("prev", "l")}</span><span class="play">{ic("pause")}</span><span class="ib">{ic("next", "l")}</span></div></div>')
    prints = ('<div style="display:grid;gap:16px;align-content:start"><div style="display:flex;gap:20px;align-items:flex-end;padding:10px;background:var(--spot)">'
              f'{pr("laughing", 150)}{pr("spirit", 76, "s")}{pr("hats", 48, "s")}</div><span class="eb">print · mat 11 (large) / 5 (small, under 72) · shadow L / S</span>'
              f'<div style="width:336px;position:relative;box-shadow:0 0 0 1px var(--edge)">{MINI}{nav(0)}</div><span class="eb">mini player 58 + bar 62 on the rail</span>'
              f'<div style="width:336px;position:relative;height:250px;overflow:hidden;box-shadow:0 0 0 1px var(--edge)"><div class="sheet" style="position:absolute"><div class="handle"></div>'
              f'<div class="opt">{ic("info")}<span><b>Option row</b><small>Explanation in small muted text</small></span></div><div class="opt">{ic("ban")}<span><b>Another option</b></span></div></div></div>'
              '<span class="eb">sheet · top radius 14, rows 62</span>'
              f'<div style="display:flex;flex-wrap:wrap;gap:10px;color:var(--control)">' + "".join(f'<span title="{n}">{ic(n)}</span>' for n in ICONS) + "</div>"
              f'<span class="eb">icons · 24 grid, 1.4 stroke, round · {len(ICONS)} glyphs</span></div>')
    return (f'<div class="phone" style="width:auto;height:auto;border-radius:16px;padding:28px;display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:34px;margin:18px 28px 40px;box-shadow:none">'
            f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;align-content:start">{sw_}</div>{type_}{ctr}{prints}</div>')

# ------------------------------------------------------------------------------------------------ Motion (live)

MOTION_JS = """
const M=JSON.parse(document.getElementById('motion-tokens').textContent);
const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
const bz=a=>Array.isArray(a)?`cubic-bezier(${a.join(',')})`:'linear';
const ph=document.querySelector('.live');const scr=ph.querySelector('.scr');
const S=n=>ph.querySelector(`.screen[data-s="${n}"]`);let cur='home',prev='home';
function rect(el){const s=ph.getBoundingClientRect(),r=el.getBoundingClientRect();return{x:r.left-s.left,y:r.top-s.top,w:r.width,h:r.height}}
function flip(a,b,t){if(RM||!a||!b)return;const A=rect(a),B=rect(b);const c=a.cloneNode(true);
 Object.assign(c.style,{position:'absolute',left:B.x+'px',top:B.y+'px',width:B.w+'px',margin:0,zIndex:30,transformOrigin:'0 0',pointerEvents:'none'});
 ph.appendChild(c);b.style.visibility='hidden';
 c.animate([{transform:`translate(${A.x-B.x}px,${A.y-B.y}px) scale(${A.w/B.w})`},{transform:'none'}],{duration:t.ms,easing:bz(t.curve)});setTimeout(()=>{c.remove();b.style.visibility=''},t.ms)}
function rise(el){if(RM)return;const t=M.placardRise;[...el.querySelectorAll('.hero,.plac,.acts,.tabs,.sec,.trk-list,.np-cap,.seek,.trans')].slice(0,t.maxItems).forEach((r,i)=>
 r.animate([{opacity:0,transform:`translateY(${t.dp}px)`},{opacity:1,transform:'none'}],{duration:t.ms,delay:120+i*t.staggerMs,easing:bz(t.curve),fill:'backwards'}))}
function go(to,src){
 if(to==='sheet')return sheet(true);if(to==='close')return sheet(false);
 if(to==='snack'){sheet(false);return snack()}
 if(to==='back')to=prev; else if(to!==cur&&(to==='album'||to==='player'))prev=cur;
 if(to===cur)return;const from=S(cur),tgt=S(to);tgt.hidden=false;tgt.scrollTop=0;
 const key=src&&src.closest('[data-sh]')?src.closest('[data-sh]').dataset.sh:(cur==='album'?'laughing':cur==='player'?'np':null);
 const a=key?(src&&src.closest('[data-sh]')||ph.querySelector(`.screen[data-s="${cur}"] [data-sh="${key}"]`)):null;
 const dock=ph.querySelector('.dock');const b=key?(tgt.querySelector(`[data-sh="${key}"]`)||(to!=='player'?dock.querySelector(`[data-sh="${key}"]`):null)):null;
 dock.hidden=(to==='player');let wait=RM?0:M.pageFadeOut.ms+M.pageFadeIn.ms;
 if(!RM){
  if(to==='player'){tgt.style.zIndex=5;tgt.animate([{transform:'translateY(100%)'},{transform:'none'}],{duration:M.playerRise.ms,easing:bz(M.playerRise.curve)});wait=M.playerRise.ms}
  else if(cur==='player'){from.style.zIndex=5;from.animate([{transform:'none'},{transform:'translateY(100%)'}],{duration:M.playerFall.ms,easing:bz(M.playerFall.curve),fill:'forwards'});
    dock.animate([{transform:'translateY(100%)'},{transform:'none'}],{duration:M.playerFall.ms,easing:bz(M.playerFall.curve)});wait=M.playerFall.ms}
  else{from.animate([{opacity:1},{opacity:0}],{duration:M.pageFadeOut.ms,fill:'forwards'});tgt.animate([{opacity:0},{opacity:1}],{duration:M.pageFadeIn.ms,delay:M.pageFadeIn.delayMs,fill:'backwards'});rise(tgt)}
 }
 flip(a,b,to==='player'?M.playerRise:M.sharedCover);
 const tabs=['home','disc','lib','search'];const ti=tabs.indexOf(to==='home'?'home':to);
 if(ti>=0){ph.querySelectorAll('.nav span').forEach((s,i)=>s.classList.toggle('on',i===ti))}
 cur=to;setTimeout(()=>{from.hidden=true;from.getAnimations().forEach(x=>x.cancel());from.style.zIndex=''},wait)}
function sheet(open){const L=ph.querySelector('.layer');if(open){L.hidden=false;if(RM)return;
 L.querySelector('.scrim').animate([{opacity:0},{opacity:1}],{duration:M.scrimIn.ms});L.querySelector('.sheet').animate([{transform:'translateY(100%)'},{transform:'none'}],{duration:M.sheetIn.ms,easing:bz(M.sheetIn.curve)});return}
 if(L.hidden)return;if(RM){L.hidden=true;return}
 L.querySelector('.scrim').animate([{opacity:1},{opacity:0}],{duration:M.sheetOut.ms,fill:'forwards'});
 L.querySelector('.sheet').animate([{transform:'none'},{transform:'translateY(100%)'}],{duration:M.sheetOut.ms,easing:bz(M.sheetOut.curve),fill:'forwards'});setTimeout(()=>{L.hidden=true;L.querySelectorAll('*').forEach(x=>x.getAnimations().forEach(y=>y.cancel()))},M.sheetOut.ms)}
function snack(){const s=ph.querySelector('.snack');s.hidden=false;if(!RM)s.animate([{opacity:0,transform:`translateY(${M.snackIn.dp}px)`},{opacity:1,transform:'none'}],{duration:M.snackIn.ms,easing:bz(M.snackIn.curve)});
 clearTimeout(window._st);window._st=setTimeout(()=>s.hidden=true,M.snackHoldMs)}
const navi=ph.querySelector('.nav');navi.querySelectorAll('span').forEach((s,i)=>{s.dataset.go=['home','home','home','home'][i];s.style.cursor='pointer';
 s.addEventListener('click',e=>{e.stopPropagation();navi.querySelectorAll('span').forEach((x,j)=>x.classList.toggle('on',j===i));if(cur!=='home')go('home')})});
ph.addEventListener('click',e=>{const g=e.target.closest('[data-go]');if(!g||g.closest('.nav'))return;go(g.dataset.go,g)});
"""

def motion():
    h = home_full(0)
    h = h.replace(f'<div class="cap">{pr("laughing", 151, "s")}', f'<div class="cap"><div class="print s" style="width:151px;cursor:pointer" data-sh="laughing" data-go="album">{cv("laughing")}</div>', 1)
    h = h.replace(f'<span class="ib" style="margin-left:auto">{ic("more")}</span>', f'<span class="ib" style="margin-left:auto;cursor:pointer" data-go="sheet">{ic("more")}</span>', 1)
    al = album_pages()[0][1].replace(f'<span class="ib">{ic("back")}</span>', f'<span class="ib" data-go="back" style="cursor:pointer">{ic("back")}</span>', 1)
    al = al.replace(f'<div class="hero">{pr("laughing", 228)}</div>', f'<div class="hero"><div class="print" style="width:228px" data-sh="laughing">{cv("laughing")}</div></div>', 1)
    pl = player()[0][1].replace(f'<span class="ib">{ic("down")}</span>', f'<span class="ib" data-go="back" style="cursor:pointer">{ic("down")}</span>', 1)
    pl = pl.replace(f'{pr("laughing", 300, "np")}', f'<div class="print np" style="width:300px" data-sh="np">{cv("laughing")}</div>', 1)
    mini = MINI.replace('<div class="mini">', '<div class="mini" data-go="player" style="cursor:pointer">').replace('<div class="print s">', '<div class="print s" data-sh="np">', 1)
    sheet = sheets()[0][3].replace('<div class="scrim">', '<div class="scrim" data-go="close">').replace('<div class="opt">', '<div class="opt" data-go="snack" style="cursor:pointer">')
    screens = "".join(f'<section class="screen" data-s="{n}" style="position:absolute;inset:0;overflow-y:auto;scrollbar-width:none;padding-top:34px;background:var(--ink)"{" hidden" if n != "home" else ""}>{b}</section>'
                      for n, b in [("home", h), ("album", al), ("player", pl)])
    phone = (f'<div class="phone live"><div class="scr" style="padding-top:0">{status()}{screens}</div><div class="dock">{mini}{nav(0)}</div>'
             f'<div class="layer" hidden style="position:absolute;inset:0;z-index:25">{sheet}</div>'
             '<div class="snack" hidden style="bottom:134px"><span>Hex will not be suggested again.</span><u>Undo</u></div></div>')
    rows = "".join(f'<tr><td>{k}</td><td>{v.get("ms", "")}</td><td>{v.get("curve", "") if not isinstance(v.get("curve"), list) else "cubic-bezier(" + ", ".join(map(str, v["curve"])) + ")"}</td></tr>'
                   for k, v in TOKENS["motion"].items() if isinstance(v, dict))
    table = ('<div style="max-width:440px;font-size:13px"><p style="margin:0 0 12px;color:#5E626A">Tap the Laughing Stock print under Played lately, the back arrow, the mini player, '
             'the down arrow, and the three dots beside Save. Values come from tokens.json. Everything stops when the phone removes animations.</p>'
             f'<table style="border-collapse:collapse;width:100%;font:12px DM Mono,monospace">{rows}</table></div>').replace("<td>", '<td style="padding:6px 10px 6px 0;border-bottom:1px solid #D5D5CF">')
    tokens = json.dumps(TOKENS["motion"])
    return (f'<div class="frames" style="gap:48px"><figure><figcaption>Live · Home, Album, Now Playing, pick menu, snackbar</figcaption>{phone}</figure>{table}</div>'
            f'<script type="application/json" id="motion-tokens">{tokens}</script><script>{MOTION_JS}</script>')

# ------------------------------------------------------------------------------------------------ write

PAGES = {
    "home": ("Home", home), "album-artist-genre": ("Album, Artist and Genre", album_pages), "player": ("Now Playing, Queue and Lyrics", player),
    "discover": ("Discover, Insights and the taste sheet", discover), "library-search": ("Library and Search", library),
    "radio": ("Radio, live radio and Heard on radio", radio), "downloads-stats-server": ("Downloads, Library stats and Server", downloads),
    "settings": ("Settings, Appearance, Equalizer and Crossfade", settings), "sheets": ("Sheets and the snackbar", sheets),
    "motion": ("Motion, live", None),
    "palettes": ("The eight palettes (colour variations of the same screens)", palettes), "components": ("Tokens and controls", components),
}

def page_html(name):
    title, fn = PAGES[name]
    if name == "components":
        body = fn()
    elif name == "motion":
        body = motion()
    else:
        body = '<div class="frames">' + "".join(frame(*f) for f in fn()) + "</div>"
    sub = ("Android, 360 × 780 dp, 1 px = 1 dp. Drawn in Day 1 (Gallery · White) unless a frame names another palette. "
           "Covers, artist photos and station logos are stand-ins. Spec: docs/GALLERY_THEME.md.")
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Gallery · {title}</title><link rel="stylesheet" href="{FONTS}"><link rel="stylesheet" href="../palettes.css"><link rel="stylesheet" href="../gallery.css"></head>'
            f'<body><div class="doc"><h1>Gallery · {title}</h1><p>{sub}</p></div>{body}</body></html>')

def write(name):
    os.makedirs(PAGES_DIR, exist_ok=True)
    html = page_html(name)
    path = os.path.join(PAGES_DIR, name + ".html")
    open(path, "w").write(html)
    if os.path.exists(CHROME):
        n = html.count("<figure>")
        w = 56 + min(n, 8) * 404 if n else 1500
        rows = (n + 7) // 8 if n > 8 else 1
        hgt = (130 + rows * 850) if n else 2000
        if n > 8:  # palettes: two rows of eight
            html_wrapped = html.replace('<div class="frames">', '<div class="frames" style="flex-wrap:wrap;width:%dpx">' % (8 * 404 - 44 + 56), 1)
            open(path, "w").write(html_wrapped)
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{hgt}", "--virtual-time-budget=6000",
                        f"--screenshot={path[:-5]}.png", "file://" + path], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

if __name__ == "__main__":
    write_icons()
    write_palette_css()
    names = [a for a in sys.argv[1:] if a in PAGES] or list(PAGES)
    for n in names:
        write(n)
        print("pages/" + n)
